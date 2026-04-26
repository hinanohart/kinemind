# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a vulnerability

If you believe you have found a security vulnerability in kinemind,
please report it privately:

* GitHub: open a [security advisory](https://github.com/hinanohart/kinemind/security/advisories/new)
* Email: **runzaisongpu95@gmail.com**

Please **do not** open a public issue for security disclosures. We will
acknowledge receipt within 5 business days and aim to publish a fix
within 90 days for confirmed issues.

## Scope

* The web app accepts no network input by default; all computations run
  client-side. Any future opt-in remote logging will be document here.
* The Python CLI reads JSON from disk; we treat malformed JSON as
  user input and validate via zod-equivalent schemas in `origami_lab.io`.
* Secrets (`.env`, credentials) are not part of this repository and are
  enforced at the `.gitignore` and pre-commit layers.

## Hardening

* GitHub Actions workflows pin commit SHAs for third-party actions.
* Dependabot is enabled for `npm`, `pip`, and `github-actions`.
* CodeQL scans run on every push to `main`.
* `gitleaks` is run as a pre-merge job.
