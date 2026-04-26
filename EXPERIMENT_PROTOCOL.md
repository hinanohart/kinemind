# Experimental Protocol — Sympathetic Mental Folding

Reference protocol for measuring **Kinematic Mental Mirroring (KMM)** on
1D origami strips. v0.2 covers self-experiment and online (Prolific)
deployments with a single testable hypothesis (H1); lab fMRI extensions
live in v2.0.

## Hypotheses

### v0.2 scope: H1 (testable in this release)

| ID | Statement | Status | Pre-registration |
|---|---|---|---|
| H1 | Coupling rate increases logarithmically with cell count N. | **Active — v0.2** | `prereg/h1_cell_count.yaml` |
| H2 | Irregular hinge spacing decreases coupling. | Deferred to v0.3+ | — |
| H3 | Phenomenon generalises to other articulated objects. | Deferred to v0.3+ | — |
| H4 | Physical manipulation experience reduces coupling. | Deferred to v0.3+ | — |
| H5 | Coupling correlates with autistic traits / mental rotation score. | Deferred to v0.3+ | — |
| H6 | Reported MV polarities align with Maekawa parity. | Deferred to v0.3+ | — |

H2–H6 are listed here for completeness. They will be pre-registered
separately before their respective data-collection phases.

### H1 — Formal statement

> The log-odds of a participant correctly predicting a hinge as coupled
> increases linearly with log2(N), where N ∈ {4, 8, 16} is the cell count
> of the origami strip.  The pre-registered effect size is β_logN = 0.30
> (log-odds per unit of log2 N).

**Pre-registration**: `prereg/h1_cell_count.yaml` (lock on OSF before data
collection begins).

**Primary analysis model** (R / lme4):

```r
glmer(
  predicted_coupled ~ log2(N) + (1|subject) + (1|target_hinge),
  data   = session_data,
  family = binomial(link = "logit"),
  control = glmerControl(optimizer = "bobyqa")
)
```

---

## Trial structure (≈ 12 s)

1. Strip stimulus (3 000 ms) — static PNG rendered from the SE(3) kinematics
   engine.
2. Instruction: "Fold hinge *i* as a mountain in your head" (3 000 ms).
3. Prediction phase: click each hinge that you feel co-bends; rate confidence
   (0–100 slider).
4. Reveal: physical truth from rigid simulator overlaid in 500 ms animation.
5. Optional self-rated match (thumbs up / down).

Each session contains **36 trials**: 3 cell counts (N = 4, 8, 16) × 4 target
hinges × 3 repetitions.  Trial order is randomised per subject.

---

## Independent and dependent variables

### Independent variables

| IV | Levels | Notes |
|---|---|---|
| Cell count N | 4, 8, 16 | Balanced; 12 trials per level |
| Target hinge | random, balanced | 4 target hinges selected per N |

*(H2 spacing and H3 mode are out of scope for v0.2.)*

### Dependent variables

| DV | Measurement | Unit |
|---|---|---|
| Predicted coupling set | binary per hinge | 0 / 1 |
| Reaction time (RT) | from instruction offset to first click | ms |
| Confidence | self-report slider | 0–100 |
| MV polarity | mountain / valley / unsure | categorical |

---

## Attention checks

Three types of attention check are interleaved in each session (5 % of trials,
≥ 2 per session).

### Type A — Impossible strip (perceptual catch)

A strip is displayed with an analytically impossible hinge configuration
(e.g., all hinges simultaneously at maximum angle in the same direction).
Participants who click "all hinges couple" on every trial are flagged.

**Pass criterion**: At least one hinge left un-selected.

### Type B — Instruction repetition (comprehension catch)

The instruction slide is replaced with a literal instruction: "Click ONLY
hinge number 3."  Participants must click exactly one specific hinge.

**Pass criterion**: Exactly one hinge clicked; matches the named hinge.

### Type C — Re-test of an earlier trial (consistency catch)

A trial identical to one presented earlier in the session is repeated.
High within-subject consistency is expected (humans are not perfectly
consistent, but gross mis-matches suggest disengagement).

**Pass criterion**: Jaccard similarity between the two response sets ≥ 0.5.

**Session exclusion rule**: Fewer than 2 of 3 attention checks passed →
exclude entire session prior to analysis.

---

## Pre-registration (OSF) procedure

1. Complete all fields in `prereg/h1_cell_count.yaml` (IRB reference,
   registration date).
2. Validate locally:
   ```bash
   python -m origami_lab.preregistration validate prereg/h1_cell_count.yaml
   ```
3. Export to OSF JSON-LD:
   ```python
   from pathlib import Path
   from origami_lab.preregistration import load_preregistration, export_osf_jsonld
   prereg = load_preregistration("prereg/h1_cell_count.yaml")
   export_osf_jsonld(prereg, Path("prereg/h1_cell_count.jsonld"))
   ```
4. Log in to [osf.io](https://osf.io/) and create a new pre-registration.
5. Upload `prereg/h1_cell_count.jsonld` as a supplementary file.
6. **Lock the registration** — this is irreversible and must happen before
   any data collection.
7. Record the OSF DOI in the YAML `registrationDate` and `registrationPlatform`
   fields and commit the update.

---

## Power analysis

### Pre-registered parameters

| Parameter | Value | Source |
|---|---|---|
| Effect size β_logN | 0.30 | Pilot self-experiment; conservative estimate |
| α (one-sided) | 0.05 | Pre-registered |
| Target power | 0.80 | Convention |
| ICC (subject) | 0.30 | Literature (Hedge et al., 2018) |
| Trials per subject | 36 | Design |
| Estimated N | 120 | Power simulation (see below) |

### Power curve (H1)

Generated with `origami-lab power --hypothesis H1 --curve 60,80,100,120,140,160`:

```
Power curve for H1  beta=0.300  alpha=0.050  reps=200
     N     power           95% CI
----------------------------------------
    60     0.517  [0.442, 0.591]
    80     0.640  [0.568, 0.707]
   100     0.731  [0.661, 0.793]
   120     0.803  [0.737, 0.859]
   140     0.855  [0.793, 0.904]
   160     0.895  [0.837, 0.937]
```

*(Values above are from Monte Carlo simulation with n_replicates=200,
seed=0.  Re-run with `--reps 1000` for publication-quality estimates.)*

**Conclusion**: N = 120 subjects yields estimated power = 0.80 at β_logN = 0.30
with ICC = 0.30.  With 20 % expected dropout on Prolific, we target **N = 150
enrolled** to achieve 120 completers.

To reproduce:
```bash
cd python/origami_lab
uv run origami-lab power --hypothesis H1 --n 120
uv run origami-lab power --hypothesis H1 --curve 60,80,100,120,140,160
```

---

## Individual-difference covariates

Two validated instruments are collected at session start.  They serve as
covariates in the secondary analysis (H5, deferred to v0.3+) and are
used here to characterise the sample.

### AQ-10 (Autism Spectrum Quotient — 10 item)

- **What it measures**: Autistic-trait thinking styles on a continuous
  scale (not a diagnostic instrument).
- **Administration**: 10 Likert items (0–3); items 1, 7, 8, 10 are
  reverse-scored.  Total score 0–10; higher = more autistic-trait thinking.
- **Time**: ~2 minutes.
- **Reference**: Allison et al. (2012), *JAACAP* 51(2):202–212.
- **Schema**: `packages/shared-types/src/individual-differences.ts`
  `AQ10ResponseSchema`.
- **IRB note**: The AQ-10 is used as a continuous covariate.  Participants
  are not told their score.

### MRT — Mental Rotation Test (Vandenberg & Kuse, 1978)

- **What it measures**: Spatial ability — ability to mentally rotate 3D
  figures.
- **Administration**: 24 items, 2 correct answers each.  Scored as number
  of items with both correct options selected and no distractors (0–24).
- **Time**: 6 minutes (self-paced, no time limit in online version).
- **Reference**: Vandenberg & Kuse (1978), *Perceptual and Motor Skills*
  47:599–604.
- **Schema**: `packages/shared-types/src/individual-differences.ts`
  `MRTResponseSchema`.
- **Scoring note**: Both correct options must be selected; any distractor
  selection scores the item as incorrect.

*(VVIQ-2 is included in the schema for completeness but is not administered
in v0.2 to limit session length.)*

---

## Exclusion criteria

All exclusion criteria are pre-registered in `prereg/h1_cell_count.yaml`.
Exclusions are applied in the following order before any analysis:

| # | Criterion | Threshold | Justification |
|---|---|---|---|
| 1 | Attention check pass rate | < 2/3 checks passed | Task non-engagement |
| 2 | Valid trials | < 30 of 36 | Insufficient data for stable coupling estimate |
| 3 | Median RT | < 500 ms or > 30 000 ms | Speed / disengagement criterion |
| 4 | Language | Non-native English | Instruction comprehension confound |

Exclusions are applied to entire sessions (not individual trials).
Trials with RT < 200 ms are flagged as outlier trials and removed within
a session, but do not trigger session exclusion unless the valid-trial
count falls below 30.

---

## Sample-size justification

Effect β_logN = 0.30, α = 0.05 (one-sided), target power ≥ 0.80, ICC = 0.30,
36 trials per subject.  Monte Carlo simulation (`origami-lab power`) yields
N = 120 subjects.  With 20 % expected dropout on Prolific, the target
**enrolled N = 150**.

See the power curve table above for sensitivity analysis across sample sizes.

---

## Ethics

* Ethics approval: [YOUR_IRB_REFERENCE] from [YOUR_INSTITUTION].
* Consent form: `irb/consent_form.md` (version v0.2-2026-04-27).
* Participant information sheet: `irb/participant_information_sheet.md`.
* Debrief: `irb/debrief.md` (full hypothesis disclosure shown after task).
* Data management: `irb/data_management_plan.md` (GDPR / DMPonline format).
* Anonymisation: Prolific PID hashed (SHA-256 + server-side salt); IP discarded.
* GDPR Articles 6(1)(a) (explicit consent), 17 (right to erasure within 30 days).
* Pre-registration on OSF before data collection begins.

---

## Quality control

* Attention checks (3 per session, ≥ 2 must pass — see above).
* Desktop-only (mobile excluded via User-Agent check).
* Median completion time monitor: sessions > 45 min flagged for manual review.
* Browser support: Chrome 120+, Firefox 120+, Safari 17+.
* Real-time data validation: all session JSON rejected if it fails the
  `SessionDataSchema` zod schema before writing to disk.

---

## Schema reference

All data are validated against
[`packages/shared-types`](packages/shared-types) zod schemas before being
written to disk; the Python pipeline rejects any session that fails
validation.

| Schema | File |
|---|---|
| Strip geometry | `packages/shared-types/src/strip.ts` |
| Coupling matrix | `packages/shared-types/src/coupling.ts` |
| Trial response | `packages/shared-types/src/trial.ts` |
| Subject / demographics | `packages/shared-types/src/subject.ts` |
| Pre-registration | `packages/shared-types/src/preregistration.ts` |
| Individual differences (AQ-10, MRT, VVIQ-2) | `packages/shared-types/src/individual-differences.ts` |
