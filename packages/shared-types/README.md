# @kinemind/shared-types

Zero-runtime [zod](https://zod.dev/) schemas that act as the single source
of truth for kinemind's data model. Both the web app and the Python
analysis pipeline validate against these schemas, eliminating
TypeScript ↔ Python drift.

## Schemas

* `StripSchema`, `StripStateSchema`
* `CouplingMatrixSchema`, `CouplingSourceSchema`
* `TrialResponseSchema`, `SessionDataSchema`
* `SubjectSchema`

## License

MIT
