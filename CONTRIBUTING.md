# Contributing

Thanks for your interest in `airwer`. This project uses the modern Astral
Python toolchain.

## Toolchain

| Concern | Tool |
|---|---|
| Environment & build | [uv](https://github.com/astral-sh/uv) + [hatchling](https://hatch.pypa.io/) |
| Lint & format | [ruff](https://github.com/astral-sh/ruff) |
| Type checking | [ty](https://github.com/astral-sh/ty) |
| Tests & coverage | [pytest](https://pytest.org) + pytest-cov |
| Task runner | [poethepoet](https://poethepoet.natn.io/) |
| Pre-commit | [pre-commit](https://pre-commit.com) |
| Releases | [release-please](https://github.com/googleapis/release-please) → PyPI Trusted Publishing |

## Setup

```bash
uv sync                 # create the venv and install all dependencies
uv run pre-commit install   # optional: run ruff on every commit
```

## Day-to-day

```bash
uv run poe check        # lint + format-check + typecheck
uv run poe fix          # auto-fix lint + format
uv run poe test         # run the unit tests with coverage
uv run poe build        # build the wheel + sdist
```

## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `chore:`, …). release-please reads them to compute the
next version and generate the changelog, so the prefix matters.

## Releases

Releases are automated. Merging to `main` lets release-please open/update a
release PR; merging that PR tags the version and publishes to PyPI via OIDC.

**One-time setup required before the first release** (maintainer, on GitHub/PyPI):

1. **PyPI Trusted Publisher** — on PyPI, add a pending publisher for the project:
   - Project name: `airwer`
   - Owner: `twangodev`, Repository: `airwer`
   - Workflow filename: `python.yml`
   - Environment name: `release`
2. **GitHub `release` environment** — repo Settings → Environments → create `release`.

No PAT is needed: the workflow uses the built-in `GITHUB_TOKEN`. The publish job
runs in the same workflow run that creates the release (gated on release-please's
`release_created` output), so the token's "doesn't trigger downstream workflows"
limitation doesn't apply. The only effect is that CI checks don't re-run on the
release PR itself — the commits were already checked on push to `main`.
