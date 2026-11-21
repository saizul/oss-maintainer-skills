# Publishing to package registries

Every publish is permanent: registries do not let you reuse a version number. Build,
inspect, then upload. Never paste tokens into chat or commit them; use CI secrets or
trusted publishing.

## PyPI (Python)

```bash
python -m pip install --upgrade build twine
python -m build                     # dist/*.whl and dist/*.tar.gz
python -m twine check dist/*        # README renders, metadata valid
python -m twine upload dist/*       # or: upload --repository testpypi dist/* first
```

Preferred: **trusted publishing** (OIDC) from GitHub Actions with
`pypa/gh-action-pypi-publish`, configured on the PyPI project page under
"Publishing". No API token is stored anywhere.

## npm (Node.js)

```bash
npm pack --dry-run                  # check which files are included
npm publish                         # add --access public for a first scoped package
npm publish --tag next              # for prereleases, so 'latest' is not moved
```

From CI, `npm publish --provenance` adds a signed provenance statement (requires
`id-token: write` permission). npm also supports trusted publishing from GitHub Actions.

## Packagist (PHP)

Packagist reads tags from the Git repository. Submit the repository once at
packagist.org, enable the GitHub hook (or the Packagist GitHub app) so new tags are
picked up automatically, and do **not** set `version` in composer.json (the tag is the
version).

## crates.io (Rust)

```bash
cargo publish --dry-run
cargo publish
```

## Docker images

Tag with the full version, the minor line and `latest` only for the newest stable:
`ghcr.io/OWNER/NAME:1.4.0`, `:1.4`, `:latest`. Build multi-arch images with
`docker/build-push-action` in CI.

## Release workflow that attaches artifacts

```yaml
name: Release
on:
  release:
    types: [published]
permissions:
  contents: write
jobs:
  assets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: make dist                 # replace with the project's build command
      - run: gh release upload "${{ github.event.release.tag_name }}" dist/* --clobber
        env:
          GH_TOKEN: ${{ github.token }}
```

## Verify

```bash
python -m venv /tmp/verify && /tmp/verify/bin/pip install "PACKAGE==1.4.0" && /tmp/verify/bin/TOOL --version
npx --yes PACKAGE@1.4.0 --version
composer create-project --no-install VENDOR/PACKAGE /tmp/verify 1.4.0
cargo install CRATE --version 1.4.0
```

## If something went wrong

- Wrong files in a release: publish a new patch version; yank (PyPI, crates.io) or
  deprecate (`npm deprecate PACKAGE@1.4.0 "use 1.4.1"`) the broken one.
- Wrong tag pushed but nothing published yet: ask the user before deleting it
  (`git push --delete origin v1.4.0`); others may already have fetched it.
