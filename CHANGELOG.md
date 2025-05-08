<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Update Readme to fix link <https://github.com/gtronset/beets-filetote/pull/168>
- Migrate to Ruff for Code Formatting and Linting <https://github.com/gtronset/beets-filetote/pull/174>
- Move tox config to pyproject.toml & add CONTRIBUTING <https://github.com/gtronset/beets-filetote/pull/175>

## [1.0.0] - 2025-05-06

### Changed

- Update Black version to fix vulnerability <https://github.com/gtronset/beets-filetote/pull/157>
- Update Filetote to support Beets >=2.0.0 (and various cleanups) <https://github.com/gtronset/beets-filetote/pull/167>

## [0.4.9] - 2024-04-20

### Changed

- Update beets version & other dependency requirements <https://github.com/gtronset/beets-filetote/pull/155>

## [0.4.8] - 2024-01-03

### Added

- Add Security policy <https://github.com/gtronset/beets-filetote/pull/140>
- Allow for retaining path hierarchy <https://github.com/gtronset/beets-filetote/pull/144>

### Changed

- Test and ensure subdirectory with $albumpath <https://github.com/gtronset/beets-filetote/pull/141>
- Remove need for typing_extensions in plugin <https://github.com/gtronset/beets-filetote/pull/146>

## [0.4.7] - 2023-12-17

### Added

- Add tests to ensure inline plugin works <https://github.com/gtronset/beets-filetote/pull/130>
- Bugfix for Update CLI command <https://github.com/gtronset/beets-filetote/pull/133>

### Changed

- Improve README, Dev setup, & update mediafile for newer Py versions <https://github.com/gtronset/beets-filetote/pull/134>
- Various dependency updates

## [0.4.6] - 2023-12-03

### Fixed

- Fix reimport via query (IndexError bugfix) <https://github.com/gtronset/beets-filetote/pull/126>
- Refactor and Fix Pruning <https://github.com/gtronset/beets-filetote/pull/128>

## [0.4.5] - 2023-12-01

### Added

- Enable Filetote on "move" command <https://github.com/gtronset/beets-filetote/pull/124>

## [0.4.4] - 2023-11-23

### Fixed

- Reevaluate & fix types (now with stubs!) <https://github.com/gtronset/beets-filetote/pull/119>

## [0.4.3] - 2023-10-05

### Fixed

- Fix "cannot find the file specified" bug <https://github.com/gtronset/beets-filetote/pull/115>

### Changed

- Add support for Python 3.12 (py312) <https://github.com/gtronset/beets-filetote/pull/114>
- Various dependency updates

## [0.4.2] - 2023-05-19

### Changed

- Loosen Python version in Dockerfile <https://github.com/gtronset/beets-filetote/pull/92>
- Use the formatted version of Item fields <https://github.com/gtronset/beets-filetote/pull/93>

## [0.4.1] - 2023-05-15

### Changed

- Refactor fields to allow Beets Item values <https://github.com/gtronset/beets-filetote/pull/90>

## [0.4.0] - 2023-05-14

### Added

- Add tox command for doing black changes <https://github.com/gtronset/beets-filetote/pull/48>
- Add mypy <https://github.com/gtronset/beets-filetote/pull/49>
- Allow paired files to be by ext <https://github.com/gtronset/beets-filetote/pull/54>
- Add flake8-bugbear & fix errors <https://github.com/gtronset/beets-filetote/pull/55>
- Add pattern match and alternative path format config section <https://github.com/gtronset/beets-filetote/pull/62>

### Changed

- Misc. Refactors to Filetote <https://github.com/gtronset/beets-filetote/pull/51>
- Test Suite Refactoring <https://github.com/gtronset/beets-filetote/pull/57>
- Add additional, stricter mypy settings <https://github.com/gtronset/beets-filetote/pull/59>
- Add testing for nested directories / multi-disc imports <https://github.com/gtronset/beets-filetote/pull/60>
- Various dependency updates

## [0.3.3] - 2023-01-08

### Fixed

- Bugfix of mediafile types - Exclude m4a, m4b, etc. <https://github.com/gtronset/beets-filetote/pull/43>

### Changed

- Add Release Action to CI in <https://github.com/gtronset/beets-filetote/pull/40>
- Only test py11 on Ubuntu in <https://github.com/gtronset/beets-filetote/pull/41>

## [0.3.2] - 2022-12-30

### Fixed

- MoveOperation bugfix for CLI overrides <https://github.com/gtronset/beets-filetote/pull/36>

## [0.3.1] - 2022-12-26

### Added

- Add Flake8 <https://github.com/gtronset/beets-filetote/pull/26>
- Add Pylint <https://github.com/gtronset/beets-filetote/pull/27>
- Auto-update pre-commit hooks <https://github.com/gtronset/beets-filetote/pull/29>
- Add Poetry <https://github.com/gtronset/beets-filetote/pull/31>

### Changed

- Rename `master` branch to `main` <https://github.com/gtronset/beets-filetote/pull/25>

## [0.3.0] - 2022-12-21

### Added

- CHANGELOG <https://github.com/gtronset/beets-filetote/pull/24>

### Changed

- Fix py3.6 CI issue & ignore py3.11 Win fails by @gtronset in <https://github.com/gtronset/beets-filetote/pull/22>
- Bump DavidAnson/markdownlint-cli2-action from 7 to 8 by @dependabot in <https://github.com/gtronset/beets-filetote/pull/20>
- Bump python from 3.11.0-alpine to 3.11.1-alpine by @dependabot in <https://github.com/gtronset/beets-filetote/pull/21>
- Rename plugin to Filetote by @gtronset in <https://github.com/gtronset/beets-filetote/pull/23>

## [0.2.2] - 2022-11-10

### Added

- Introduce "paired" file copies by @gtronset in <https://github.com/gtronset/beets-filetote/pull/15>
- Introduce reflinks, hardlinks, and symlinks by @gtronset in <https://github.com/gtronset/beets-filetote/pull/19>

### Changed

- Small update to specifying namespace by @gtronset in <https://github.com/gtronset/beets-filetote/pull/16>
- Add tests for renaming illegal chars by @gtronset in <https://github.com/gtronset/beets-filetote/pull/17>

## [0.2.1] - 2022-11-01

### Added

- Add "filenames" and "exclude" options by @gtronset in <https://github.com/gtronset/beets-filetote/pull/9>
- Improve path/renaming options by @gtronset in <https://github.com/gtronset/beets-filetote/pull/10>

### Changed

- Smarter file renaming with `filename:` path query prioritized by @gtronset in <https://github.com/gtronset/beets-filetote/pull/11>
- Pruning and test improvements by @gtronset in <https://github.com/gtronset/beets-filetote/pull/14>
- Lock mediafile requirement to ==0.10.0 by @dependabot in <https://github.com/gtronset/beets-filetote/pull/13>
- Bump python from 3.10-alpine to 3.11.0-alpine by @dependabot in <https://github.com/gtronset/beets-filetote/pull/12>

## [0.2.0] - 2022-10-21

### Added

- Rename and modernize multiple files by @gtronset in <https://github.com/gtronset/beets-filetote/pull/1>
- Bump requests from 2.22.0 to 2.28.1 by @dependabot in <https://github.com/gtronset/beets-filetote/pull/2>
- Bump mock from 2.0.0 to 4.0.3 by @dependabot in <https://github.com/gtronset/beets-filetote/pull/3>
- Fix LICENSE and cleanup README by @gtronset in <https://github.com/gtronset/beets-filetote/pull/4>
- Add pre-commit, black, isort, updates to setup.cfg by @gtronset in <https://github.com/gtronset/beets-filetote/pull/5>
- Add typo and MD Checks by @gtronset in <https://github.com/gtronset/beets-filetote/pull/6>
- Update compose to stay-alive by @gtronset in <https://github.com/gtronset/beets-filetote/pull/8>

### Updated

- Hard Fork from <https://github.com/adammillerio/beets-copyartifacts>

<!-- Release Links -->

[unreleased]: https://github.com/gtronset/beets-filetote/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/gtronset/beets-filetote/releases/tag/v1.0.0
[0.4.9]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.9
[0.4.8]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.8
[0.4.7]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.7
[0.4.6]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.6
[0.4.5]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.5
[0.4.4]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.4
[0.4.3]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.3
[0.4.2]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.2
[0.4.1]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.1
[0.4.0]: https://github.com/gtronset/beets-filetote/releases/tag/v0.4.0
[0.3.3]: https://github.com/gtronset/beets-filetote/releases/tag/v0.3.3
[0.3.2]: https://github.com/gtronset/beets-filetote/releases/tag/v0.3.2
[0.3.1]: https://github.com/gtronset/beets-filetote/releases/tag/v0.3.1
[0.3.0]: https://github.com/gtronset/beets-filetote/releases/tag/v0.3.0
[0.2.2]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.2
[0.2.1]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.1
[0.2.0]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.0
