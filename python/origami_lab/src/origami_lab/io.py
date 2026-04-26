"""JSON I/O compatible with the TypeScript zod schema, plus BIDS-like writer.

The JSON schema mirrors the TypeScript ``@kinemind/core-math`` types:
- StripConfig fields use camelCase keys for TS compatibility.
- Arrays of numbers are plain JSON arrays.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from origami_lab.strip import StripConfig, StripState

logger = logging.getLogger(__name__)


# ---- Strip serialization (TS-compatible camelCase keys) ----


def strip_config_to_dict(config: StripConfig) -> dict[str, Any]:
    """Serialize StripConfig to TS-compatible JSON dict.

    Args:
        config: Strip configuration.

    Returns:
        JSON-serializable dict with camelCase keys.
    """
    return {
        "nCells": config.n_cells,
        "cellLengths": list(config.cell_lengths),
        "angleMax": config.angle_max,
    }


def strip_config_from_dict(d: dict[str, Any]) -> StripConfig:
    """Deserialize StripConfig from TS-compatible JSON dict.

    Args:
        d: Dict with camelCase keys.

    Returns:
        StripConfig instance.

    Raises:
        ValueError: if required keys are missing or values are invalid.
    """
    try:
        n_cells = int(d["nCells"])
        cell_lengths = tuple(float(x) for x in d["cellLengths"])
        angle_max = float(d.get("angleMax", np.pi))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"strip_config_from_dict: invalid data: {exc}") from exc
    return StripConfig(n_cells=n_cells, cell_lengths=cell_lengths, angle_max=angle_max)


def strip_state_to_dict(state: StripState) -> dict[str, Any]:
    """Serialize StripState to TS-compatible JSON dict.

    Args:
        state: Hinge angle state.

    Returns:
        JSON-serializable dict.
    """
    return {"thetas": list(state.thetas)}


def strip_state_from_dict(d: dict[str, Any]) -> StripState:
    """Deserialize StripState from TS-compatible JSON dict.

    Args:
        d: Dict with 'thetas' key.

    Returns:
        StripState instance.

    Raises:
        ValueError: if 'thetas' key is missing or malformed.
    """
    try:
        thetas = tuple(float(x) for x in d["thetas"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"strip_state_from_dict: invalid data: {exc}") from exc
    return StripState(thetas=thetas)


def poses_to_dict(
    positions: np.ndarray,
    quats: np.ndarray,
) -> dict[str, Any]:
    """Serialize FK result arrays to JSON-serializable dict.

    Args:
        positions: shape (N, 3) cell positions.
        quats: shape (N, 4) quaternions (w,x,y,z).

    Returns:
        Dict with 'positions' and 'quats' lists.
    """
    return {
        "positions": positions.tolist(),
        "quats": quats.tolist(),
    }


# ---- High-level JSON file I/O ----


def save_json(path: str | Path, data: Any) -> None:
    """Write JSON to file (creates parent dirs as needed).

    Args:
        path: Output path.
        data: JSON-serializable data.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    logger.warning("Saved JSON to %s", path)


def load_json(path: str | Path) -> Any:
    """Load JSON from file.

    Args:
        path: Input path.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: if path does not exist.
        ValueError: if file is not valid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"load_json: file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"load_json: invalid JSON in {path}: {exc}") from exc


# ---- BIDS-like writer ----


def write_bids_like(
    root: str | Path,
    subject: str,
    session: str,
    config: StripConfig,
    trials: list[dict[str, Any]],
) -> None:
    """Write data in a BIDS-inspired folder structure.

    Layout::

        <root>/
          sub-<subject>/
            ses-<session>/
              strip_config.json
              trials.json

    Args:
        root: Root output directory.
        subject: Subject identifier string.
        session: Session identifier string.
        config: Strip configuration to persist.
        trials: List of trial dicts (each should contain 'state' and optionally 'result').
    """
    out_dir = Path(root) / f"sub-{subject}" / f"ses-{session}"
    out_dir.mkdir(parents=True, exist_ok=True)

    config_path = out_dir / "strip_config.json"
    save_json(config_path, strip_config_to_dict(config))

    trials_path = out_dir / "trials.json"
    save_json(trials_path, {"trials": trials})

    logger.warning(
        "BIDS-like data written to %s (sub=%s, ses=%s)", out_dir, subject, session
    )
