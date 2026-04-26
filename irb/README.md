# IRB / Ethics document set — KineMind v0.2

This directory contains ethics and participant-facing documents for online
deployment of the KineMind experiment on Prolific.  All documents are
templates: replace `[YOUR_INSTITUTION]`, `[PI_NAME]`, `[PI_EMAIL]`, and
related placeholders before submission to your ethics review board.

## Document inventory

| File | Purpose | Audience |
|---|---|---|
| `participant_information_sheet.md` | Study overview for potential participants | Participants |
| `consent_form.md` | Explicit opt-in consent checklist | Participants |
| `debrief.md` | Full hypothesis disclosure (shown after completion) | Participants |
| `data_management_plan.md` | GDPR / DMPonline data management plan | IRB / DPO |

## Reading level

All participant-facing documents target a Flesch-Kincaid grade level of 8
or below (verified with `textstat.flesch_kincaid_grade()`).  Plain English
is used throughout; jargon is explained on first use.

## GDPR compliance notes

- No names, emails, or IP addresses are collected.
- Prolific participant IDs are one-way hashed (SHA-256) on the client before
  transmission.
- Data are stored in the EU (Ireland, AWS eu-west-1).
- Participants may request deletion of their data at any time via the
  deletion endpoint described in the information sheet.
- Retention period: 10 years (3 650 days), as specified in the
  pre-registration.

## Consent version

Current version: `v0.2-2026-04-27`.  Any substantive change to the consent
form requires a new version string and fresh ethics approval before further
data collection.
