<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2022-12-21

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

- Fork from <https://github.com/adammillerio/beets-copyartifacts>

- <!-- Release Links -->

[unreleased]: https://github.com/gtronset/beets-filetote/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/gtronset/beets-filetote/releases/tag/v0.3.0
[0.2.2]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.2
[0.2.1]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.1
[0.2.0]: https://github.com/gtronset/beets-filetote/releases/tag/v0.2.0
