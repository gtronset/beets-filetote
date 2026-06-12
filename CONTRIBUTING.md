# Development & Contributing

The development version can be installed with [`uv`], a Python dependency and package manager
that provides dependency isolation, reproducibility, and streamlined packaging to PyPI.

Testing and linting is performed with [`tox`] (`v4.12`+).

[`uv`]: https://docs.astral.sh/uv/
[`tox`]: https://tox.wiki/

[Installing `prek`] is also highly recommended, which will help automatically
lint before committing.

Filetote currently supports Python `3.10`+ and beets `v2.4`+.

For general information of working with beets plugins, see the beets' documentation
[For Developers].

[Installing `prek`]: https://prek.j178.dev/installation/
[For Developers]: https://beets.readthedocs.io/en/stable/dev/

## Installation

**1. Install `uv`, `tox`, and `prek`:**

```sh
pipx install uv tox prek
```

**2. Clone the repository and install the plugin:**

```sh
git clone https://github.com/gtronset/beets-filetote.git
cd beets-filetote
uv sync --active --frozen --group dev --group lint --group test
```

**3. Update the config.yaml to utilize the plugin:**

```yaml
pluginpath:
  - /path/to.../beets-filetote/beetsplug
```

**4. Run or test with `uv` (and `tox`):**

Run beets with the following to locally develop:

```sh
uv run beet
```

## Testing

Tests use [`pytest`] with isolated fixtures provided by the `pytest_beets_plugin` test
framework in `tests/pytest_beets_plugin/`. Each test gets a fully isolated beets
environment (config, library, I/O) via temporary directories.

[`pytest`]: https://docs.pytest.org/

### Running Tests

Run the full test suite directly:

```sh
uv run pytest
```

Run a specific test file or test:

```sh
uv run pytest tests/test_filename.py
uv run pytest tests/test_filename.py::TestFilename::test_filename_by_name
```

Run with verbose output:

```sh
uv run pytest -v
```

### Running Tests via `tox`

`tox` manages isolated test environments and is the primary way to run tests across
Python and beets versions. In this repository, `tox` delegates dependency syncing and
command execution to `uv` inside each `tox` environment.

Test against a specific Python version:

```sh
tox -e 3.14
```

Test against a specific beets version:

```sh
tox -e beets-2_6
```

Test against the beets' development branch:

```sh
tox -e beets-master
```

Run all supported Python and beets versions in parallel:

```sh
tox -p
```

Available `tox` environments:

| Environment                | Description                                                |
|----------------------------|------------------------------------------------------------|
| `3.10` – `3.14`            | Test against a specific Python version                     |
| `beets-2_4` – `beets-2_11` | Test with beets `~=2.4.0` through `~=2.11.0`, respectively |
| `beets-master`             | Test with beets from `master` branch                       |
| `lint`                     | Lint source code (`ruff check`)                            |
| `lint-fix`                 | Auto-fix lint issues (`ruff check --fix`)                  |
| `format`                   | Format source code (`ruff format`)                         |
| `mypy`                     | Type-check source code                                     |

### Test Structure

Tests are organized as plain pytest classes (not `unittest.TestCase`'s). The test framework
provides tiered fixtures:

- **`beets_plugin_env`** — the base fixture; provides the full test environment without
  creating any import directories. Use when you need custom setup (e.g., `move=True`,
  special media files, reimport scenarios).
- **`beets_flat_env`** — creates a flat (single-disc) import directory and configures a
  default copy session with `autotag=False`. Suitable for the majority of tests.
- **`beets_nested_env`** — creates a nested (multi-disc) import directory and configures
  a default copy session with `autotag=False`.

Example test:

```python
from tests.pytest_beets_plugin import BeetsEnvFactory


class TestExample:
    def test_extension_copied(self, beets_flat_env: BeetsEnvFactory) -> None:
        env = beets_flat_env()

        env.config["filetote"]["extensions"] = ".file"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
```

For tests requiring custom setup, use `beets_plugin_env` directly:

```python
import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture


class TestCustomSetup:
    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        self.env = beets_plugin_env

        env = self.env
        env.create_flat_import_dir(pair_subfolders=True)
        env.setup_import_session(autotag=False, move=True)

    def test_something(self) -> None:
        env = self.env
        # ...
```

### Linting & Type Checking

```sh
tox -e lint
tox -e format
tox -e mypy
```

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

**Docker:**

A Docker Compose configuration is available for running the plugin in a controlled
environment. See the [`compose.yaml`](./compose.yaml) file for details.
