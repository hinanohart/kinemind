# Data Management Plan

**Project**: KineMind — Mental Folding Study (v0.2)
**Institution**: [YOUR_INSTITUTION]
**Principal investigator**: [PI_NAME]
**Data Protection Officer contact**: [DPO_EMAIL]
**Plan version**: v0.2-2026-04-27
**Format**: DMPonline compatible

---

## 1. Data description

### 1.1 What data will be collected?

| Data type | Format | Approx. size |
|---|---|---|
| Trial response records (clicks, reaction times) | JSON | ~5 KB / session |
| Questionnaire responses (AQ-10, MRT, VVIQ-2) | JSON | ~2 KB / session |
| Session metadata (browser, viewport, timestamp) | JSON | ~1 KB / session |
| Pre-registration document | YAML + JSON-LD | ~10 KB |

Total for 120 participants: approximately 1 MB raw data.

### 1.2 What data will NOT be collected?

- Names, email addresses, or any other direct identifiers.
- IP addresses (discarded at the API gateway level).
- Audio, video, or image data.

### 1.3 Pseudonymisation

Prolific participant IDs are one-way hashed (SHA-256 with a server-side
salt) on the backend before storage.  The mapping between Prolific IDs and
hash values is stored separately and will be deleted after the 30-day
withdrawal window closes.

---

## 2. Data collection and documentation

### 2.1 Standards

All data are validated against the `SessionDataSchema` zod schema
(`packages/shared-types/src/trial.ts`) before writing to disk.  Invalid
sessions are rejected at ingestion.

### 2.2 Documentation

- Pre-registration (hypotheses, analysis plan, exclusion criteria): `prereg/h1_cell_count.yaml`
- Experiment protocol: `EXPERIMENT_PROTOCOL.md`
- Code and analysis scripts: versioned on GitHub (to be made public after
  data collection).

---

## 3. Ethics and legal compliance

### 3.1 Legal basis for processing (GDPR Article 6)

Processing is based on **explicit consent** (Article 6(1)(a)) collected via
the online consent form (version v0.2-2026-04-27).

### 3.2 Special category data

No special category data (Article 9) are collected.

The AQ-10 questionnaire measures autistic traits on a continuous scale and
is used as a covariate; it does not constitute a clinical diagnosis and is
not stored as health data.

### 3.3 Data subject rights

- **Access**: Participants may request a copy of their pseudonymised data.
- **Erasure**: Participants may request deletion within 30 days of
  completing the study (contact [PI_EMAIL]).  After 30 days, data are part
  of the anonymised dataset and individual deletion is not possible.
- **Portability**: Pseudonymised data provided in JSON format on request.

### 3.4 Data transfers

Data are stored in the EU (AWS eu-west-1, Ireland).  No transfer outside
the EU/EEA is planned.  If open data are published on OSF, only fully
anonymised aggregates and individual-level records (with no re-identification
risk) will be included.

---

## 4. Storage and security

### 4.1 Storage locations

| Environment | Location | Access control |
|---|---|---|
| Live collection | AWS S3 (eu-west-1), encrypted at rest (AES-256) | PI + IRB-approved team only |
| Analysis workstations | Encrypted local drives at [YOUR_INSTITUTION] | PI only |
| Open data repository | OSF (public, anonymised only) | Public (post-publication) |

### 4.2 Backup

Daily automated backups to a separate AWS S3 bucket in eu-west-1.
Backups are retained for 90 days.

### 4.3 Access management

- Multi-factor authentication required for AWS console access.
- API keys rotated every 90 days.
- No third-party analytics or tracking scripts on the experiment web app.

---

## 5. Retention and disposal

| Data type | Retention period | Disposal method |
|---|---|---|
| Raw session JSON | 10 years (3 650 days) from collection date | Secure deletion (AWS S3 lifecycle policy) |
| Prolific ID hash mapping | 30 days from session completion | Secure deletion |
| Anonymised analysis dataset | Indefinite (open data) | — |
| Code and pre-registration | Indefinite (version controlled) | — |

---

## 6. Data sharing and open science

Following completion of the study:

1. **Pre-registration**: OSF registration locked before data collection.
2. **Analysis code**: GitHub repository made public on submission.
3. **Anonymised dataset**: Uploaded to OSF with a CC0 licence after
   peer review acceptance.
4. **Aggregated results**: Published in the manuscript; raw individual-level
   data shared only if re-identification risk is assessed as negligible.

---

## 7. Roles and responsibilities

| Role | Responsibility |
|---|---|
| [PI_NAME] (PI) | Overall data governance, IRB liaison |
| [DATA_ENGINEER_NAME] | Secure infrastructure, backup monitoring |
| [DPO_EMAIL] (DPO) | GDPR compliance review |

---

*This plan will be reviewed and updated before each new phase of data collection.*
