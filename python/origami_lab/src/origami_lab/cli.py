"""typer-based CLI for origami-lab.

Usage::

    origami-lab analyze --in trials.json --out report.json
    origami-lab kinematics --n-cells 8 --theta 0.1,0.2,0.3,0.4,0.5,0.6,0.7
    origami-lab --help
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import typer

app = typer.Typer(
    name="origami-lab",
    help="Origami strip kinematics and mental coupling analysis.",
    no_args_is_help=True,
)

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    """Configure root logger level."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command()
def analyze(
    in_path: Annotated[
        Path,
        typer.Option("--in", help="Path to trials JSON file.", show_default=False),
    ],
    out_path: Annotated[
        Path,
        typer.Option("--out", help="Path for output report JSON.", show_default=False),
    ],
    lambda_: Annotated[
        float,
        typer.Option("--lambda", help="Tikhonov regularisation coefficient."),
    ] = 0.0,
    use_v4: Annotated[
        bool,
        typer.Option("--use-v4/--no-use-v4", help="Apply V_4 symmetry projection."),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose/--quiet")] = False,
) -> None:
    """Estimate coupling matrix and run H1-H6 hypothesis tests.

    The input JSON must have fields::

        {
          "config": { "nCells": ..., "cellLengths": [...], "angleMax": ... },
          "trials": [
            { "intent": [...], "response": [...] },
            ...
          ]
        }
    """
    _setup_logging(verbose)

    from origami_lab.coupling import estimate_coupling, mirror_coupling, MentalCoupling
    from origami_lab.io import load_json, save_json, strip_config_from_dict
    from origami_lab.stats import run_all_tests

    try:
        data = load_json(in_path)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error loading {in_path}: {exc}", err=True)
        raise typer.Exit(1)

    try:
        config = strip_config_from_dict(data["config"])
        trials = data["trials"]
        intents = np.array([t["intent"] for t in trials], dtype=np.float64)
        responses = np.array([t["response"] for t in trials], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as exc:
        typer.echo(f"Error parsing trials JSON: {exc}", err=True)
        raise typer.Exit(1)

    n_hinges = config.n_hinges
    C = estimate_coupling(
        intents, responses, n_hinges=n_hinges, lambda_=lambda_, use_v4=use_v4
    )
    coupling = MentalCoupling(matrix=C, n_hinges=n_hinges, source="empirical")

    results = run_all_tests(coupling, intents=intents, responses=responses)

    report = {
        "coupling_matrix": C.tolist(),
        "n_hinges": n_hinges,
        "lambda": lambda_,
        "use_v4": use_v4,
        "hypotheses": [r.to_dict() for r in results],
    }
    save_json(out_path, report)
    typer.echo(f"Report written to {out_path}")


@app.command()
def kinematics(
    n_cells: Annotated[
        int,
        typer.Option("--n-cells", help="Number of cells (>= 2)."),
    ] = 4,
    thetas: Annotated[
        Optional[str],
        typer.Option(
            "--theta",
            help="Comma-separated hinge angles in radians (n_cells - 1 values).",
        ),
    ] = None,
    cell_length: Annotated[
        float,
        typer.Option("--cell-length", help="Uniform cell length."),
    ] = 1.0,
    verbose: Annotated[bool, typer.Option("--verbose/--quiet")] = False,
) -> None:
    """Compute forward kinematics and print cell positions."""
    _setup_logging(verbose)

    from origami_lab.kinematics import forward_kinematics
    from origami_lab.strip import StripConfig, StripState, make_uniform_strip

    config = make_uniform_strip(n_cells, cell_length=cell_length)

    if thetas is None:
        theta_vals = tuple(0.0 for _ in range(config.n_hinges))
    else:
        try:
            theta_vals = tuple(float(x) for x in thetas.split(","))
        except ValueError as exc:
            typer.echo(f"Error parsing --theta: {exc}", err=True)
            raise typer.Exit(1)

    if len(theta_vals) != config.n_hinges:
        typer.echo(
            f"Error: expected {config.n_hinges} hinge angles, "
            f"got {len(theta_vals)}",
            err=True,
        )
        raise typer.Exit(1)

    state = StripState(thetas=theta_vals)
    positions, quats = forward_kinematics(config, state)

    output = {
        "n_cells": n_cells,
        "thetas": list(theta_vals),
        "positions": positions.tolist(),
        "quats": quats.tolist(),
    }
    typer.echo(json.dumps(output, indent=2))


@app.command()
def power(
    hypothesis: Annotated[
        str,
        typer.Option("--hypothesis", help="Hypothesis identifier, e.g. H1."),
    ] = "H1",
    n: Annotated[
        int,
        typer.Option("--n", help="Number of subjects for power estimate."),
    ] = 120,
    beta: Annotated[
        float,
        typer.Option(
            "--beta",
            help="Effect size: log-odds slope on log2(N) for H1 (default 0.30).",
        ),
    ] = 0.30,
    alpha: Annotated[
        float,
        typer.Option("--alpha", help="One-sided significance threshold."),
    ] = 0.05,
    n_replicates: Annotated[
        int,
        typer.Option(
            "--reps", help="Monte Carlo replicates for power estimation."
        ),
    ] = 200,
    curve: Annotated[
        Optional[str],
        typer.Option(
            "--curve",
            help=(
                "Comma-separated sample sizes for a power curve, "
                "e.g. 60,80,100,120,140,160."
            ),
        ),
    ] = None,
    seed: Annotated[
        int,
        typer.Option("--seed", help="Random seed for reproducibility."),
    ] = 0,
    verbose: Annotated[bool, typer.Option("--verbose/--quiet")] = False,
) -> None:
    """Run a Monte Carlo power analysis for a pre-registered hypothesis.

    Supports H1 (log-binomial LMM) natively; other hypotheses raise an error.
    Use --curve to evaluate a range of sample sizes and print a power table.

    Example::

        origami-lab power --hypothesis H1 --n 120
        origami-lab power --hypothesis H1 --curve 60,80,100,120,140,160
    """
    _setup_logging(verbose)

    hypothesis = hypothesis.upper()
    _SUPPORTED = {"H1"}
    if hypothesis not in _SUPPORTED:
        typer.echo(
            f"Error: power analysis for {hypothesis!r} is not yet implemented. "
            f"Supported hypotheses: {sorted(_SUPPORTED)}",
            err=True,
        )
        raise typer.Exit(1)

    from origami_lab.power import power_curve_h1, power_h1_lmm

    if curve is not None:
        try:
            sample_sizes = [int(x.strip()) for x in curve.split(",")]
        except ValueError as exc:
            typer.echo(f"Error parsing --curve: {exc}", err=True)
            raise typer.Exit(1)

        typer.echo(
            f"Power curve for {hypothesis}  beta={beta:.3f}  alpha={alpha:.3f}  "
            f"reps={n_replicates}"
        )
        typer.echo(f"{'N':>6}  {'power':>8}  {'95% CI':>17}")
        typer.echo("-" * 40)
        results = power_curve_h1(
            sample_sizes=sample_sizes,
            beta_logn=beta,
            alpha=alpha,
            n_replicates=n_replicates,
            seed=seed,
        )
        for sample_n, res in sorted(results.items()):
            lo, hi = res.confidence_interval
            typer.echo(
                f"{sample_n:>6}  {res.power:>8.3f}  [{lo:.3f}, {hi:.3f}]"
            )
    else:
        result = power_h1_lmm(
            n_subjects=n,
            beta_logn=beta,
            alpha=alpha,
            n_replicates=n_replicates,
            seed=seed,
        )
        typer.echo(result.summary_line())


if __name__ == "__main__":
    app()
