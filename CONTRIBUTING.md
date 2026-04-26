# Contributing

Thanks for thinking about contributing to kinemind.

## Ground rules

* By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
* Open an issue before starting work on a non-trivial change so we can
  align on direction.
* Every PR must keep CI green:
  * `pnpm lint && pnpm typecheck && pnpm test && pnpm build`
  * `cd python/origami_lab && uv run pytest`

## Local setup

```bash
git clone https://github.com/hinanohart/kinemind.git
cd kinemind
pnpm install
pnpm -F @kinemind/core-math test    # 45 unit + property tests
pnpm dev                            # http://localhost:5173/kinemind/

cd python/origami_lab
uv venv --python 3.12
uv pip install -e ".[test]"
uv run pytest
```

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(core-math): add SE(3) twist exponential
fix(web-app): correct StripViewer3D rotation order
docs(MATH): clarify Reynolds projection
test(python): add hypothesis property test for SE(3) inverse
```

A `kinemind:` scope is reserved for cross-package changes.

## Reviews

PRs need at least one approval and all CI jobs green. Maintainers will
batch independent fixes into a single Changeset for release notes.

## Reporting bugs / experimental observations

Use the issue templates in `.github/ISSUE_TEMPLATE/`. For experimental
observations, the **Experiment Proposal** template captures hypotheses,
pre-registration plan, and sample size up front so we can give helpful
feedback early.
