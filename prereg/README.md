# Pre-registration documents

This directory contains pre-registration YAML files for KineMind experiments.
Each file is validated against the `PreregistrationSchema` in
`packages/shared-types/src/preregistration.ts` (TypeScript) and
`python/origami_lab/src/origami_lab/preregistration.py` (Python).

## Files

| File | Study | Status |
|---|---|---|
| `h1_cell_count.yaml` | H1 pilot — coupling vs. cell count | Draft (pre-collection) |

## Validation

```bash
# Python CLI validation
python -m origami_lab.preregistration validate prereg/h1_cell_count.yaml

# OSF JSON-LD export (for upload)
python -c "
from pathlib import Path
from origami_lab.preregistration import load_preregistration, export_osf_jsonld
prereg = load_preregistration('prereg/h1_cell_count.yaml')
export_osf_jsonld(prereg, Path('prereg/h1_cell_count.jsonld'))
print('Exported to prereg/h1_cell_count.jsonld')
"
```

## Registration workflow

1. Complete all fields in the YAML (including IRB approval reference).
2. Run validation: `python -m origami_lab.preregistration validate <file.yaml>`.
3. Export JSON-LD: use the Python snippet above.
4. Upload the JSON-LD file to [OSF](https://osf.io/) as a pre-registration.
5. Record the OSF DOI in the YAML `registrationDate` and `registrationPlatform` fields.
6. **Lock the registration** before any data collection begins.

## Schema reference

- TypeScript: `packages/shared-types/src/preregistration.ts`
- Python: `python/origami_lab/src/origami_lab/preregistration.py`
