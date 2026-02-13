# Development & Contributing

The development version can be installed with [Poetry], a Python dependency manager
that provides dependency isolation, reproducibility, and streamlined packaging to PyPI.
Filetote currently support Poetry `v1.8`.

Testing and linting is performed with [Tox] (`v4.12`+).

[Poetry]: https://python-poetry.org/
[Tox]: https://tox.wiki/

[Installing `pre-commit`] is also highly recommended, which will help automatically
lint before committing.

Filetote currently supports Python `3.10`+, which aligns with the target base version of
beets (`v2.6`).

For general information of working with beets plugins, see the beets' documentation
[For Developers]

[Installing `pre-commit`]: https://pre-commit.com/#install
[For Developers]: https://beets.readthedocs.io/en/stable/dev/

## Installation

**1. Install Poetry & Tox:**

```sh
python3 -m pip install poetry tox
```

**2. Clone the repository and install the plugin:**

```sh
git clone https://github.com/gtronset/beets-filetote.git
cd beets-filetote
poetry install
```

**3. Update the config.yaml to utilize the plugin:**

```yaml
pluginpath:
  - /path/to.../beets-filetote/beetsplug
```

**4. Run or test with Poetry (and Tox):**

Run beets with the following to locally develop:

```sh
poetry run beet
```

Testing can be run with Tox, ex.:

```sh
poetry run tox -e 3.13
```

For other linting environments, see `pyproject.toml`. Ex: `lint` (courtesy of `ruff`):

```sh
poetry run tox -e lint
```

Ex: `format` (courtesy of `ruff`):

```sh
poetry run tox -e format
```

Running `poetry run` before every command can be tedious. Instead, you can activate the
virtual environment in your shell with:

```sh
poetry shell
```

Configuration of Tox follows [Poetry's recommended strategy #2], which allows Poetry
to manage dependencies but still allow Tox to manage a distinct environment. Test for
all supported Python versions can be run with the base `tox` command, and can be run in
parallel via `tox -p`, i.e.:

```sh
poetry run tox -p
```

[Poetry's recommended strategy #2]: https://python-poetry.org/docs/1.8/faq/#use-case-2

**Docker:**

A Docker Compose configuration is available for running the plugin in a controlled
environment. Running the [`compose.yaml`](./compose.yaml) file for details.

## Path Handling

This plugin enforces the usage of `pathlib.Path` over other strategies (e.g., `os.path`)
to better-enforce modern practices and align with beets' developer documentation (see
[Handling Paths]).

Accessing `Path` values on library items can be accomplished via the `.filepath`
property on `Item` and `Album`, though beets (as of version `2.6.1`) still passes
bytestring values through event parameters. Thus, conversion to/from bytestring is still
needed, though should only be done on the boundaries of the plugin. Use the internal
`path_utils` module for safe conversion and path manipulation.

[Handling Paths]: https://beets.readthedocs.io/en/stable/dev/paths.html
