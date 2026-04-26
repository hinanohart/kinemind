"""Preregistration validation and OSF JSON-LD export for KineMind experiments.

This module provides:
  - Python dataclasses that mirror the TypeScript ``PreregistrationSchema``
  - YAML loader with structural validation
  - Validation logic returning human-readable error messages
  - OSF JSON-LD export compatible with the OSF schema.org context

CLI usage (via __main__ entry-point, not cli.py)::

    python -m origami_lab.preregistration validate prereg/h1_cell_count.yaml

"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothesis:
    """Pre-registered hypothesis.

    Attributes:
        id: Unique identifier string, e.g. 'H1'.
        statement: Full natural-language statement of the hypothesis.
        directional: True if a specific direction is predicted.
        predicted_direction: 'positive', 'negative', or 'non-zero'.
            Must be set when directional is True.
        exclusion_rule: Optional session-level exclusion condition
            specific to this hypothesis.
    """

    id: str
    statement: str
    directional: bool
    predicted_direction: str | None = None
    exclusion_rule: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Hypothesis.id must be non-empty")
        if not self.statement:
            raise ValueError(f"Hypothesis {self.id}: statement must be non-empty")
        if self.directional and self.predicted_direction is None:
            raise ValueError(
                f"Hypothesis {self.id}: predicted_direction required when directional=True"
            )
        valid_directions = {"positive", "negative", "non-zero"}
        if (
            self.predicted_direction is not None
            and self.predicted_direction not in valid_directions
        ):
            raise ValueError(
                f"Hypothesis {self.id}: predicted_direction must be one of "
                f"{valid_directions}, got {self.predicted_direction!r}"
            )


@dataclass(frozen=True)
class Analysis:
    """Pre-registered analysis plan.

    Attributes:
        type: Classification — 'primary', 'secondary', or 'exploratory'.
        description: Human-readable description of the analysis.
        model: Verbatim model formula (R lme4, Python statsmodels, or prose).
        alpha_correction: Multiple-comparison correction method.
    """

    type: str
    description: str
    model: str
    alpha_correction: str = "benjamini-hochberg"

    _VALID_TYPES = frozenset({"primary", "secondary", "exploratory"})
    _VALID_CORRECTIONS = frozenset({"none", "bonferroni-holm", "benjamini-hochberg"})

    def __post_init__(self) -> None:
        if self.type not in self._VALID_TYPES:
            raise ValueError(
                f"Analysis.type must be one of {self._VALID_TYPES}, got {self.type!r}"
            )
        if self.alpha_correction not in self._VALID_CORRECTIONS:
            raise ValueError(
                f"Analysis.alpha_correction must be one of {self._VALID_CORRECTIONS}, "
                f"got {self.alpha_correction!r}"
            )
        if not self.description:
            raise ValueError("Analysis.description must be non-empty")
        if not self.model:
            raise ValueError("Analysis.model must be non-empty")


@dataclass(frozen=True)
class ExclusionRule:
    """Session-level exclusion rule.

    Attributes:
        rule: Human-readable exclusion condition.
        threshold: Optional numeric threshold.
        justification: Scientific or ethical justification.
    """

    rule: str
    threshold: float | None = None
    justification: str = ""

    def __post_init__(self) -> None:
        if not self.rule:
            raise ValueError("ExclusionRule.rule must be non-empty")
        if not self.justification:
            raise ValueError(
                f"ExclusionRule '{self.rule}': justification must be non-empty"
            )


@dataclass(frozen=True)
class StoppingRule:
    """Data-collection stopping rule.

    Attributes:
        type: 'fixed-N' or 'sequential'.
        n: Target sample size for fixed-N designs.
        alpha_spending: Alpha-spending function name for sequential designs.
    """

    type: str
    n: int | None = None
    alpha_spending: str | None = None

    _VALID_TYPES = frozenset({"fixed-N", "sequential"})

    def __post_init__(self) -> None:
        if self.type not in self._VALID_TYPES:
            raise ValueError(
                f"StoppingRule.type must be one of {self._VALID_TYPES}, got {self.type!r}"
            )
        if self.type == "fixed-N" and self.n is None:
            raise ValueError("fixed-N stopping rule requires N to be specified")
        if self.type == "sequential" and self.alpha_spending is None:
            raise ValueError(
                "Sequential stopping rule requires alphaSpending (alpha_spending) to be specified"
            )
        if self.n is not None and self.n <= 0:
            raise ValueError(f"StoppingRule.n must be positive, got {self.n}")


@dataclass(frozen=True)
class Ethics:
    """Ethics and consent metadata.

    Attributes:
        irb_approval: IRB / ethics committee reference number.
        consent_version: Consent form version string, e.g. 'v0.2-2026-04-27'.
        data_retention_days: GDPR-required data retention period in days.
    """

    consent_version: str
    irb_approval: str | None = None
    data_retention_days: int = 3650

    def __post_init__(self) -> None:
        if not self.consent_version:
            raise ValueError("Ethics.consent_version must be non-empty")
        if self.data_retention_days <= 0:
            raise ValueError(
                f"Ethics.data_retention_days must be positive, "
                f"got {self.data_retention_days}"
            )


@dataclass(frozen=True)
class Preregistration:
    """Full pre-registration document.

    Attributes:
        study_id: Globally unique study identifier, e.g. 'kmm-h1-pilot-2026q2'.
        hypotheses: One or more pre-registered hypotheses.
        analyses: One or more pre-registered analysis plans.
        exclusion_criteria: Session-level exclusion rules.
        stopping_rule: Data-collection stopping rule.
        ethics: IRB / consent metadata.
        registration_date: ISO-8601 datetime when registration was locked.
        registration_platform: 'osf', 'aspredicted', or 'internal'.
        predicted_effect_size: Standardised effect size used for power calc.
        power: Target statistical power (0–1).
        estimated_sample_size: N required at target power and effect size.
    """

    study_id: str
    hypotheses: tuple[Hypothesis, ...]
    analyses: tuple[Analysis, ...]
    exclusion_criteria: tuple[ExclusionRule, ...]
    stopping_rule: StoppingRule
    ethics: Ethics
    registration_date: str | None = None
    registration_platform: str | None = None
    predicted_effect_size: float | None = None
    power: float | None = None
    estimated_sample_size: int | None = None

    _VALID_PLATFORMS = frozenset({"osf", "aspredicted", "internal"})

    def __post_init__(self) -> None:
        if not self.study_id:
            raise ValueError("Preregistration.study_id must be non-empty")
        if len(self.hypotheses) == 0:
            raise ValueError("Preregistration must contain at least one hypothesis")
        if len(self.analyses) == 0:
            raise ValueError("Preregistration must contain at least one analysis")
        if (
            self.registration_platform is not None
            and self.registration_platform not in self._VALID_PLATFORMS
        ):
            raise ValueError(
                f"registration_platform must be one of {self._VALID_PLATFORMS}, "
                f"got {self.registration_platform!r}"
            )
        if self.power is not None and not (0.0 <= self.power <= 1.0):
            raise ValueError(
                f"power must be in [0, 1], got {self.power}"
            )
        if self.estimated_sample_size is not None and self.estimated_sample_size <= 0:
            raise ValueError(
                f"estimated_sample_size must be positive, got {self.estimated_sample_size}"
            )


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------


def _parse_hypothesis(raw: dict[str, Any]) -> Hypothesis:
    """Parse a hypothesis dict from YAML into a Hypothesis dataclass."""
    try:
        return Hypothesis(
            id=str(raw["id"]),
            statement=str(raw["statement"]),
            directional=bool(raw["directional"]),
            predicted_direction=raw.get("predictedDirection") or raw.get("predicted_direction"),
            exclusion_rule=raw.get("exclusionRule") or raw.get("exclusion_rule"),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed hypothesis entry: {exc}") from exc


def _parse_analysis(raw: dict[str, Any]) -> Analysis:
    """Parse an analysis dict from YAML into an Analysis dataclass."""
    try:
        return Analysis(
            type=str(raw["type"]),
            description=str(raw["description"]),
            model=str(raw["model"]),
            alpha_correction=str(
                raw.get("alphaCorrection") or raw.get("alpha_correction", "benjamini-hochberg")
            ),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed analysis entry: {exc}") from exc


def _parse_exclusion_rule(raw: dict[str, Any]) -> ExclusionRule:
    """Parse an exclusion rule dict from YAML."""
    try:
        raw_threshold = raw.get("threshold")
        return ExclusionRule(
            rule=str(raw["rule"]),
            threshold=float(raw_threshold) if raw_threshold is not None else None,
            justification=str(raw.get("justification", "")),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed exclusion rule entry: {exc}") from exc


def _parse_stopping_rule(raw: dict[str, Any]) -> StoppingRule:
    """Parse a stopping rule dict from YAML."""
    try:
        raw_n = raw.get("N") or raw.get("n")
        return StoppingRule(
            type=str(raw["type"]),
            n=int(raw_n) if raw_n is not None else None,
            alpha_spending=raw.get("alphaSpending") or raw.get("alpha_spending"),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed stoppingRule entry: {exc}") from exc


def _parse_ethics(raw: dict[str, Any]) -> Ethics:
    """Parse an ethics dict from YAML."""
    try:
        return Ethics(
            consent_version=str(raw["consentVersion"] or raw.get("consent_version", "")),
            irb_approval=raw.get("irbApproval") or raw.get("irb_approval"),
            data_retention_days=int(raw.get("dataRetentionDays") or raw.get("data_retention_days", 3650)),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed ethics entry: {exc}") from exc


def load_preregistration(path: str | Path) -> Preregistration:
    """Load and parse a pre-registration document from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Validated Preregistration dataclass.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the YAML is structurally invalid.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Pre-registration file not found: {resolved}")

    logger.debug("Loading pre-registration from %s", resolved)

    with resolved.open("r", encoding="utf-8") as fh:
        try:
            raw: dict[str, Any] = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML parse error in {resolved}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Pre-registration file must be a YAML mapping, got {type(raw)}")

    try:
        hypotheses = tuple(
            _parse_hypothesis(h) for h in raw.get("hypotheses", [])
        )
        analyses = tuple(
            _parse_analysis(a) for a in raw.get("analyses", [])
        )
        exclusion_criteria = tuple(
            _parse_exclusion_rule(e) for e in raw.get("exclusionCriteria") or raw.get("exclusion_criteria", [])
        )
        stopping_rule = _parse_stopping_rule(
            raw.get("stoppingRule") or raw.get("stopping_rule", {})
        )
        ethics = _parse_ethics(raw.get("ethics", {}))

        return Preregistration(
            study_id=str(raw["studyId"] or raw.get("study_id", "")),
            hypotheses=hypotheses,
            analyses=analyses,
            exclusion_criteria=exclusion_criteria,
            stopping_rule=stopping_rule,
            ethics=ethics,
            registration_date=raw.get("registrationDate") or raw.get("registration_date"),
            registration_platform=raw.get("registrationPlatform") or raw.get("registration_platform"),
            predicted_effect_size=raw.get("predictedEffectSize") or raw.get("predicted_effect_size"),
            power=raw.get("power"),
            estimated_sample_size=raw.get("estimatedSampleSize") or raw.get("estimated_sample_size"),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed pre-registration structure in {resolved}: {exc}") from exc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_preregistration(prereg: Preregistration) -> list[str]:
    """Run semantic validation checks on a loaded pre-registration.

    Checks beyond the structural validation already performed by the dataclasses:
      - At least one primary analysis is required
      - Directional hypotheses must have a predictedDirection
      - N power / estimatedSampleSize consistency when both are provided

    Args:
        prereg: A loaded Preregistration instance.

    Returns:
        List of human-readable error/warning strings.  Empty list = valid.
    """
    errors: list[str] = []

    # 1. Require at least one primary analysis
    primary_count = sum(1 for a in prereg.analyses if a.type == "primary")
    if primary_count == 0:
        errors.append(
            "No primary analysis found. At least one analysis with type='primary' is required."
        )

    # 2. Directional hypotheses must specify predicted_direction
    for hyp in prereg.hypotheses:
        if hyp.directional and hyp.predicted_direction is None:
            errors.append(
                f"Hypothesis {hyp.id!r} is directional but missing predicted_direction."
            )

    # 3. Power / estimatedSampleSize consistency
    if prereg.power is not None and not (0.0 < prereg.power < 1.0):
        errors.append(
            f"Preregistration.power should be strictly between 0 and 1, got {prereg.power}."
        )

    # 4. fixed-N stopping rule should match estimatedSampleSize when both provided
    if (
        prereg.stopping_rule.type == "fixed-N"
        and prereg.stopping_rule.n is not None
        and prereg.estimated_sample_size is not None
        and prereg.stopping_rule.n != prereg.estimated_sample_size
    ):
        errors.append(
            f"StoppingRule.N ({prereg.stopping_rule.n}) does not match "
            f"estimatedSampleSize ({prereg.estimated_sample_size}). "
            "These should be consistent."
        )

    # 5. Hypothesis IDs must be unique
    seen_ids: set[str] = set()
    for hyp in prereg.hypotheses:
        if hyp.id in seen_ids:
            errors.append(f"Duplicate hypothesis id: {hyp.id!r}")
        seen_ids.add(hyp.id)

    logger.debug(
        "Validation of %r: %d error(s)", prereg.study_id, len(errors)
    )
    return errors


# ---------------------------------------------------------------------------
# OSF JSON-LD export
# ---------------------------------------------------------------------------

_OSF_CONTEXT = {
    "@vocab": "https://schema.org/",
    "osf": "https://api.osf.io/v2/schema/",
    "studyId": "osf:studyId",
    "hypothesis": "osf:hypothesis",
    "analysis": "osf:analysis",
}


def export_osf_jsonld(prereg: Preregistration, output: Path) -> None:
    """Export pre-registration to OSF-compatible JSON-LD format.

    The generated file is suitable for upload to OSF as a structured
    registration supplement.  Fields use schema.org / OSF vocabulary.

    Args:
        prereg: Validated Preregistration instance.
        output: Destination file path (will be created or overwritten).

    Raises:
        OSError: If the output file cannot be written.
    """
    output = Path(output)

    hypotheses_jsonld = [
        {
            "@type": "osf:Hypothesis",
            "identifier": h.id,
            "description": h.statement,
            "osf:directional": h.directional,
            "osf:predictedDirection": h.predicted_direction,
            "osf:exclusionRule": h.exclusion_rule,
        }
        for h in prereg.hypotheses
    ]

    analyses_jsonld = [
        {
            "@type": "osf:Analysis",
            "osf:analysisType": a.type,
            "description": a.description,
            "osf:modelFormula": a.model,
            "osf:alphaCorrection": a.alpha_correction,
        }
        for a in prereg.analyses
    ]

    exclusions_jsonld = [
        {
            "@type": "osf:ExclusionCriterion",
            "description": e.rule,
            "osf:threshold": e.threshold,
            "osf:justification": e.justification,
        }
        for e in prereg.exclusion_criteria
    ]

    doc: dict[str, Any] = {
        "@context": _OSF_CONTEXT,
        "@type": "osf:Registration",
        "studyId": prereg.study_id,
        "name": prereg.study_id,
        "datePublished": prereg.registration_date,
        "osf:registrationPlatform": prereg.registration_platform,
        "osf:hypotheses": hypotheses_jsonld,
        "osf:analyses": analyses_jsonld,
        "osf:exclusionCriteria": exclusions_jsonld,
        "osf:stoppingRule": {
            "@type": "osf:StoppingRule",
            "osf:stoppingType": prereg.stopping_rule.type,
            "osf:N": prereg.stopping_rule.n,
            "osf:alphaSpending": prereg.stopping_rule.alpha_spending,
        },
        "osf:ethics": {
            "@type": "osf:Ethics",
            "osf:irbApproval": prereg.ethics.irb_approval,
            "osf:consentVersion": prereg.ethics.consent_version,
            "osf:dataRetentionDays": prereg.ethics.data_retention_days,
        },
        "osf:predictedEffectSize": prereg.predicted_effect_size,
        "osf:targetPower": prereg.power,
        "osf:estimatedSampleSize": prereg.estimated_sample_size,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)

    logger.info("OSF JSON-LD written to %s", output)


# ---------------------------------------------------------------------------
# __main__ entry-point
# ---------------------------------------------------------------------------


def _main_validate(yaml_path: str) -> int:
    """Validate a pre-registration YAML file and print results.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        Exit code: 0 = valid, 1 = errors, 2 = load failure.
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        prereg = load_preregistration(yaml_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR loading {yaml_path}: {exc}", flush=True)
        return 2

    errors = validate_preregistration(prereg)

    if errors:
        print(f"Pre-registration {prereg.study_id!r} has {len(errors)} error(s):", flush=True)
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}", flush=True)
        return 1

    print(
        f"Pre-registration {prereg.study_id!r} is valid.  "
        f"{len(prereg.hypotheses)} hypothesis/es, "
        f"{len(prereg.analyses)} analysis/es, "
        f"N={prereg.stopping_rule.n or 'sequential'}.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3 or sys.argv[1] != "validate":
        print(
            "Usage: python -m origami_lab.preregistration validate <file.yaml>",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.exit(_main_validate(sys.argv[2]))
