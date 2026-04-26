"""Tests for preregistration module: loading, validation, OSF export."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml

from origami_lab.preregistration import (
    Analysis,
    Ethics,
    ExclusionRule,
    Hypothesis,
    Preregistration,
    StoppingRule,
    export_osf_jsonld,
    load_preregistration,
    validate_preregistration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_prereg() -> Preregistration:
    """Construct the smallest valid Preregistration."""
    return Preregistration(
        study_id="test-study-001",
        hypotheses=(
            Hypothesis(
                id="H1",
                statement="Coupling increases with N.",
                directional=True,
                predicted_direction="positive",
            ),
        ),
        analyses=(
            Analysis(
                type="primary",
                description="LMM on log2(N).",
                model="glmer(y ~ log2(N) + (1|s), family=binomial)",
            ),
        ),
        exclusion_criteria=(
            ExclusionRule(
                rule="attention_check_pass < 2/3",
                justification="Non-engagement.",
            ),
        ),
        stopping_rule=StoppingRule(type="fixed-N", n=120),
        ethics=Ethics(consent_version="v0.1"),
    )


# ---------------------------------------------------------------------------
# Hypothesis dataclass
# ---------------------------------------------------------------------------


class TestHypothesis:
    def test_valid_directional(self) -> None:
        h = Hypothesis(
            id="H1",
            statement="X increases with Y.",
            directional=True,
            predicted_direction="positive",
        )
        assert h.id == "H1"

    def test_nondirectional_no_direction_required(self) -> None:
        h = Hypothesis(id="H2", statement="X differs.", directional=False)
        assert h.predicted_direction is None

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            Hypothesis(id="", statement="s", directional=False)

    def test_directional_without_direction_raises(self) -> None:
        with pytest.raises(ValueError, match="predicted_direction required"):
            Hypothesis(id="H1", statement="s", directional=True)

    def test_invalid_direction_raises(self) -> None:
        with pytest.raises(ValueError, match="predicted_direction must be one of"):
            Hypothesis(
                id="H1",
                statement="s",
                directional=True,
                predicted_direction="sideways",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Analysis dataclass
# ---------------------------------------------------------------------------


class TestAnalysis:
    def test_valid_primary(self) -> None:
        a = Analysis(type="primary", description="desc", model="m ~ x")
        assert a.alpha_correction == "benjamini-hochberg"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Analysis.type"):
            Analysis(type="invalid", description="d", model="m")

    def test_invalid_correction_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha_correction"):
            Analysis(
                type="primary",
                description="d",
                model="m",
                alpha_correction="tukey",
            )


# ---------------------------------------------------------------------------
# StoppingRule dataclass
# ---------------------------------------------------------------------------


class TestStoppingRule:
    def test_fixed_n_valid(self) -> None:
        sr = StoppingRule(type="fixed-N", n=120)
        assert sr.n == 120

    def test_fixed_n_without_n_raises(self) -> None:
        with pytest.raises(ValueError, match="fixed-N stopping rule requires N"):
            StoppingRule(type="fixed-N")

    def test_sequential_without_alpha_spending_raises(self) -> None:
        with pytest.raises(ValueError, match="alphaSpending"):
            StoppingRule(type="sequential")

    def test_sequential_valid(self) -> None:
        sr = StoppingRule(type="sequential", alpha_spending="obrien-fleming")
        assert sr.alpha_spending == "obrien-fleming"

    def test_negative_n_raises(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            StoppingRule(type="fixed-N", n=-5)


# ---------------------------------------------------------------------------
# Preregistration dataclass
# ---------------------------------------------------------------------------


class TestPreregistration:
    def test_minimal_valid(self) -> None:
        prereg = _minimal_prereg()
        assert prereg.study_id == "test-study-001"

    def test_empty_study_id_raises(self) -> None:
        with pytest.raises(ValueError, match="study_id must be non-empty"):
            Preregistration(
                study_id="",
                hypotheses=(_minimal_prereg().hypotheses[0],),
                analyses=(_minimal_prereg().analyses[0],),
                exclusion_criteria=(),
                stopping_rule=StoppingRule(type="fixed-N", n=100),
                ethics=Ethics(consent_version="v1"),
            )

    def test_empty_hypotheses_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one hypothesis"):
            Preregistration(
                study_id="s",
                hypotheses=(),
                analyses=(_minimal_prereg().analyses[0],),
                exclusion_criteria=(),
                stopping_rule=StoppingRule(type="fixed-N", n=100),
                ethics=Ethics(consent_version="v1"),
            )

    def test_invalid_power_raises(self) -> None:
        with pytest.raises(ValueError, match="power must be in"):
            Preregistration(
                study_id="s",
                hypotheses=(_minimal_prereg().hypotheses[0],),
                analyses=(_minimal_prereg().analyses[0],),
                exclusion_criteria=(),
                stopping_rule=StoppingRule(type="fixed-N", n=100),
                ethics=Ethics(consent_version="v1"),
                power=1.5,
            )


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


class TestLoadPreregistration:
    def test_load_sample_yaml(self, tmp_path: Path) -> None:
        """Load the bundled h1_cell_count.yaml from the prereg/ directory."""
        # Use the canonical sample file if it exists; otherwise create inline.
        sample = Path(__file__).parent.parent.parent.parent.parent / "prereg" / "h1_cell_count.yaml"
        if not sample.exists():
            # Create a minimal inline YAML for CI
            content = textwrap.dedent("""\
                studyId: test-inline
                hypotheses:
                  - id: H1
                    statement: "X increases with Y."
                    directional: true
                    predictedDirection: positive
                    exclusionRule: "attn < 2/3"
                analyses:
                  - type: primary
                    description: "LMM"
                    model: "glmer(y ~ x + (1|s))"
                    alphaCorrection: benjamini-hochberg
                exclusionCriteria:
                  - rule: "attn_fail"
                    justification: "non-engagement"
                stoppingRule:
                  type: fixed-N
                  N: 120
                ethics:
                  consentVersion: "v0.1"
                power: 0.80
                estimatedSampleSize: 120
                predictedEffectSize: 0.30
            """)
            p = tmp_path / "test.yaml"
            p.write_text(content)
            sample = p

        prereg = load_preregistration(sample)
        assert prereg.study_id != ""
        assert len(prereg.hypotheses) >= 1
        assert prereg.stopping_rule.type == "fixed-N"

    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_preregistration("/nonexistent/path.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(": invalid: yaml: :")
        with pytest.raises(ValueError):
            load_preregistration(bad)

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            hypotheses:
              - id: H1
                statement: "x"
                directional: false
            analyses:
              - type: primary
                description: "d"
                model: "m"
            exclusionCriteria: []
            stoppingRule:
              type: fixed-N
              N: 100
            ethics:
              consentVersion: "v1"
        """)
        p = tmp_path / "missing_id.yaml"
        p.write_text(content)
        with pytest.raises((ValueError, KeyError)):
            load_preregistration(p)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidatePreregistration:
    def test_valid_prereg_no_errors(self) -> None:
        errors = validate_preregistration(_minimal_prereg())
        assert errors == []

    def test_no_primary_analysis_flagged(self) -> None:
        prereg = Preregistration(
            study_id="s",
            hypotheses=(_minimal_prereg().hypotheses[0],),
            analyses=(
                Analysis(
                    type="exploratory",
                    description="d",
                    model="m",
                ),
            ),
            exclusion_criteria=(),
            stopping_rule=StoppingRule(type="fixed-N", n=100),
            ethics=Ethics(consent_version="v1"),
        )
        errors = validate_preregistration(prereg)
        assert any("primary" in e.lower() for e in errors)

    def test_n_mismatch_flagged(self) -> None:
        prereg = Preregistration(
            study_id="s",
            hypotheses=(_minimal_prereg().hypotheses[0],),
            analyses=(_minimal_prereg().analyses[0],),
            exclusion_criteria=(),
            stopping_rule=StoppingRule(type="fixed-N", n=100),
            ethics=Ethics(consent_version="v1"),
            estimated_sample_size=120,  # does not match N=100
        )
        errors = validate_preregistration(prereg)
        assert any("consistent" in e.lower() for e in errors)

    def test_duplicate_hypothesis_ids_flagged(self) -> None:
        h = Hypothesis(
            id="H1", statement="s", directional=True, predicted_direction="positive"
        )
        prereg = Preregistration(
            study_id="s",
            hypotheses=(h, h),
            analyses=(_minimal_prereg().analyses[0],),
            exclusion_criteria=(),
            stopping_rule=StoppingRule(type="fixed-N", n=100),
            ethics=Ethics(consent_version="v1"),
        )
        errors = validate_preregistration(prereg)
        assert any("duplicate" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# OSF JSON-LD export
# ---------------------------------------------------------------------------


class TestExportOsfJsonld:
    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        prereg = _minimal_prereg()
        out = tmp_path / "out.jsonld"
        export_osf_jsonld(prereg, out)
        assert out.exists()
        doc = json.loads(out.read_text())
        assert doc["studyId"] == "test-study-001"
        assert "@context" in doc

    def test_parent_dir_created(self, tmp_path: Path) -> None:
        prereg = _minimal_prereg()
        out = tmp_path / "sub" / "dir" / "out.jsonld"
        export_osf_jsonld(prereg, out)
        assert out.exists()

    def test_hypotheses_in_output(self, tmp_path: Path) -> None:
        prereg = _minimal_prereg()
        out = tmp_path / "out.jsonld"
        export_osf_jsonld(prereg, out)
        doc = json.loads(out.read_text())
        hyp_list = doc.get("osf:hypotheses", [])
        assert len(hyp_list) == 1
        assert hyp_list[0]["identifier"] == "H1"
