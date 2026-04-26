# Experimental Protocol — Sympathetic Mental Folding

Reference protocol for measuring **Kinematic Mental Mirroring (KMM)** on
1D origami strips. v0.1 covers self-experiment and online (Prolific)
deployments; lab fMRI extensions live in v2.0.

## Hypotheses

| ID | Statement | Pre-registration recommendation |
|---|---|---|
| H1 | Coupling rate increases with cell count $N$. | LMM with $\log N$ as fixed effect. |
| H2 | Irregular hinge spacing decreases coupling. | LMM with spacing factor. |
| H3 | The phenomenon generalises to other articulated objects (chair, arm, lamp). | Phase 2. |
| H4 | Physical manipulation experience reduces coupling. | Within-subject pre/post. |
| H5 | Coupling correlates with autistic traits / mental rotation score. | Partial correlation / SEM. |
| H6 | Reported MV polarities align with Maekawa parity. | KL divergence vs uniform null. |

## Trial structure (≈ 12 s)

1. Strip stimulus (3000 ms).
2. Instruction: "fold hinge $i$ as a mountain in your head" (3000 ms).
3. Prediction phase: click each hinge that you feel co-bend; rate confidence (0–100).
4. Reveal physical truth (rigid simulator output).
5. Optional self-rated match.

## Independent / dependent variables

| IV | Levels |
|---|---|
| Cell count $N$ | 4, 8, 16 |
| Spacing | uniform, 1:2:1, irregular |
| Mode | static, manipulable 3D |
| Target hinge | random, balanced |

| DV | Measurement |
|---|---|
| Predicted coupling set | binary per hinge |
| Reaction time | ms |
| Confidence | 0–100 |
| MV polarity | M / V / unsure |

## Sample-size justification

Effect $d = 0.5$, $\alpha = .05$, $\beta = .80$, ICC = .30, ~36 trials
per subject. `simr` simulation suggests **N = 120 subjects** for H1
power ≥ .80 (drop-out 20% included).

## Ethics

* Consent (web form, timestamped).
* Anonymisation (Prolific PID hashed; IP discarded).
* GDPR Article 16 compliant deletion endpoint.
* IRB review at the host institution.
* Pre-registration (OSF / AsPredicted) before data collection.

## Quality control

* Attention check trials (5%).
* Desktop-only (mobile excluded).
* Median completion time monitor.
* Browser support: Chrome 120+, Firefox 120+, Safari 17+.

## Schema reference

All data is validated against
[`packages/shared-types`](packages/shared-types) zod schemas before being
written to disk; the Python pipeline rejects any session that fails
validation.
