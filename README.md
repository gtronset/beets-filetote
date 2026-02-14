# _Filetote_ plugin for beets

[![MIT license][license image]][license link]
[![CI][ci image]][ci link]
[![GitHub release][github image]][github link]
[![PyPI][pypi_version]][pypi_link]
[![PyPI - Python Version][pypi_python_versions]][pypi_link]

A plugin that moves non-music extra files, attachments, and artifacts during imports and
CLI file manipulation actions (`move`, `modify`, reimport, etc.) for [beets], a music
library manager (and much more!).

The most recent versions of this plugin runs on Python 3.10+ in beets `v2.4` and above
(<`v2.7`), though older versions of the plugin have additional compatibility back to `v1.6`.

[beets]: https://beets.io/

## Installing

### Stable

The stable version of the plugin is available from PyPI and can be installed using
`pip3`:

```sh
pip3 install beets-filetote
```

## Configuration

You will need to enable the plugin in beets' `config.yaml`:

```yaml
plugins: filetote
```

It can copy files by file [extension](#extension-extensions):

```yaml
filetote:
  extensions: .cue .log
```

Or copy all non-music files:

```yaml
filetote:
  extensions: .*
```

Or copy files by [filename](#filename-filenames):

```yaml
filetote:
  filenames: song.log
```

Or match based on a ["pattern"](#pattern-patterns) (via [glob pattern]):

```yaml
filetote:
  patterns:
    artworkdir:
      - "[aA]rtwork/"
```

It can look for and target ["pairs"](#pairing-pairing) (files having the same name as a
matching or "paired" media item/track):

```yaml
filetote:
  pairing:
    enabled: true
```

You can specify [pairing to happen to certain extensions](#pairing-example-configuration),
and even target/include only paired files:

```yaml
filetote:
  pairing:
    enabled: true
    pairing_only: true
    extensions: ".lrc"
```

It can also [exclude files](#excluding-files-exclude) that are otherwise matched:

```yaml
filetote:
  exclude:
    filenames: song_lyrics.nfo
```

And print what got left:

```yaml
filetote:
  print_ignored: true
```

[glob pattern]: https://docs.python.org/3/library/glob.html#module-glob

### File Handling & Renaming

In order to collect extra files and artifacts, Filetote needs to be told which types of
files it should care about. This can be done using the following:

- Extensions (`extensions:`): Specify individual extensions like `.cue` or `.log`, or
  use a catch-all for all non-music files with `.*`.
- Filenames (`filenames:`): Match specific filenames like `cover.jpg` or organize artwork
  with `[aA]rtwork/*`.
- Patterns (`patterns:`): Use flexible glob patterns for more control, like matching all
  logs in a subfolder: `CD1/*.log`.
- Pairing: Move files with the same name as imported music items, like `.lrc` lyrics or
  album logs.

#### Filetote Renaming Basics

Unless otherwise specified, the default name for artifacts and extra files is:
`$albumpath/$old_filename`. This means that by default, the file is essentially
moved/copied into destination directory of the music item it gets grabbed with. This
also means that the album folder is flattened, and any subdirectory is removed by
default. To preserve subdirectories, [see `$subpath` usage](#subpath-renaming-example).

> [!NOTE]
> To update the default renaming from `$albumpath/$old_filename`, use the
> `filetote:default` path specification.

Configuration for renaming works in much the same way as beets [Path Formats], including
the standard metadata values provided by beets along with `replace` settings. Filetote
provides the below new path queries, which each takes a single corresponding value.
These can be defined in either the top-level `paths` section of beets' config or in the
`paths` section of Filetote's config. Both of the following are equivalent:

```yaml
paths:
  ext:.log: $albumpath/$artist - $album
```

```yaml
filetote:
  paths:
    ext:.log: $albumpath/$artist - $album
```

> [!IMPORTANT]
> If you have the same path specified in both the top-level `paths` section of beets'
> config and in the `paths` section of Filetote's config, the Filetote's specification
> will take precedence. There should not be a normal scenario where this is
> intentionally utilized with Filetote's [new path queries](#new-path-queries), but it
> may be needed if there's a conflict/overlap with another plugin; this allows you to
> specify renaming rules that will _only_ impact Filetote and not other plugins.

[Path Formats]: http://beets.readthedocs.org/en/stable/reference/pathformat.html

##### New path queries

These are the new path queries added by Filetote, from _most_ to _least_ specific:

- `filename:`
- `paired_ext:`
- `pattern:`
- `ext:`

This means that the `filename:` path query will take precedence over `paired_ext:`,
`pattern:`, and `ext:` if a given file qualifies for them. This also means that
the value in `paired_ext:` will take precedence over `pattern:` and `ext:`, and
`pattern:` is higher priority than `ext:`.

> [!WARNING]
> `ext:.*` is _not_ a valid query. If you need to update the default renaming, [please
> use `filetote:default`](#filetote-renaming-basics).

##### Renaming considerations

Renaming has the following considerations:

The fields available include [the standard metadata values] of the imported item
(`$albumartist`, `$album`, `$title`, etc.), along with Filetote specific values of:

- `$albumpath`: the entire path of the new destination of the item/track (a useful
  shorthand for when the extra/artifact file will be moved alongside the item/track).
    - **Note**: beets doesn't have a strict "album" path concept. All references are
      relative to Items (the actual media files). This is especially relevant for
      multi-disc files/albums, but usually isn't a problem. [Check the section on
      multi-discs] for more details.
- `$subpath`: Represents any subdirectories under the base album path where an
  extra/artifact file resides. For use when it is desirable to preserve the directory
  hierarchy in the albums. This respects the original capitalization of directory names.
  Defaults to an empty string when no subdirectories exist.
    - **Example:** If an extra file is located in a subdirectory named `Extras` under
    the album path, `$subpath` would be set to `Extras/` (with the same casing).
- `$old_filename`: the filename of the extra/artifact file before its renamed.
- `$medianame_old`: the filename of the item/track triggering it, _before_ it's renamed.
- `$medianame_new`: the filename of the item/track triggering it, _after_ it's renamed.

> [!WARNING]
> The fields mentioned above are not usable within other plugins such as `inline`.
> That said, `inline` and other plugins should work without issue [unless otherwise
> specified here].

The full set of [built-in functions] are also supported, except for `%aunique`, which
will return an empty string.

> [!IMPORTANT]
> By default, if there are rename rules set that result with multiple files having the
> exact same filename in the destination, only the first file will be added, and subsequent
> files will be skipped to avoid overwriting. This behavior is configurable, see the
> [Handling Duplicate Artifacts] section for details on how to change this to keep or
> overwrite files.

[the standard metadata values]: https://beets.readthedocs.io/en/stable/reference/pathformat.html#available-values
[Check the section on multi-discs]: #advanced-renaming-for-multi-disc-albums
[unless otherwise specified here]: #filetote-compatibility-with-other-plugins
[built-in functions]: http://beets.readthedocs.org/en/stable/reference/pathformat.html#functions
[Handling Duplicate Artifacts]: #handling-duplicate-artifacts-duplicate_action

##### Subpath Renaming Example

The following configuration or template string will be applied to `.log` files by using
the `$subpath` and will rename log file to:
`~/Music/Artist/2014 - Album/Extras/Artist - Album.log`

This assumes that the original file is in the subdirectory (subpath) of `Extras/`. Any
other `.log` files in other subdirectories or in the root of the album will be moved
accordingly. If a more targeted approach is needed, this can be combined with the
`pattern:` query.

> [!NOTE]
> `$subpath` automatically adds in path separators, including the end one if there are
> subdirectories.

```yaml
paths:
  ext:.log: $albumpath/$subpath$artist - $album
```

#### Extension (`extensions:`)

Filename can match on the extension of the file, in a space-delimited list (i.e., a
string sequence). Use `.*` to match all file extensions.

##### Extension Example Configuration

This example will match any file which has an extension of either `.lrc` or `.log`,
across all subfolders.

```yaml
filetote:
  extensions: .lrc .log
```

##### Extension Renaming Example

The following configuration or template string will be applied to `.log` files by using
the `ext:` query and will rename log file to:
`~/Music/Artist/2014 - Album/Artist - Album.log`

```yaml
paths:
  ext:.log: $albumpath/$artist - $album
```

#### Filename (`filenames:`)

Filetote can match on the actual name (including extension) of the file, in a
space-delimited list (string sequence). `filenames:` will match across any subdirectories,
meaning targeting a filename in a specific subdirectory will not work (this functionality
_can_ be achieved using a `pattern`, however).

##### Filename Example Configuration

This example will match if the filename of the given artifact or extra file matches the
name exactly as specified, either `cover.jpg` or `artifact.nfo`.

```yaml
filetote:
  filenames: cover.jpg artifact.nfo
```

##### Filename Renaming Example

The following configuration will rename the specific `artifact.nfo` file to:
`~/Music/Artist/2014 - Album/Artist - Album.nfo`

```yaml
filetote:
  paths:
    filename:artifact.nfo: $albumpath/$artist - $album
  filenames: cover.jpg artifact.nfo
```

#### Pattern (`patterns:`)

Filetote can match on a given _pattern_ as specified using [glob patterns]. This allows
for more specific matching, like grabbing only PNG artwork files. Paths in the pattern
are relative to the root of the importing album. Hence, if there are subdirectories in
the album's folder (for multidisc setups, for instance, e.g., `albumpath/CD1`), the
album's path would be the base/root for the pattern (ex: `CD1/*.jpg`). Patterns will
work with or without the proceeding slash (`/`) (Windows users will need to
use the appropriate slash `\`).

Specifying pattern folders with a trailing slash (ex: `albumpath/`) will match every
file in that subdirectory irrespective of name or extension (it is equivalent to
`albumpath/*.*`).

Patterns are defined by a _name_ so that any customization for renaming can apply to the
pattern when specifying the path (ex: `pattern:artworkdir`; see the section on renaming
below).

> [!IMPORTANT]
> Patterns process in order from top to bottom, and once matched will determine which
> path to apply during renaming. This is important in cases where theoretically a file
> could match to multiple patterns. For example, if you have a file here:
> `albumpath/artwork/cover.jpg`, the pattern it will match to is the first (`artworkdir`)
> in the following config:
>
> ```yaml
> filetote:
>  patterns:
>    artworkdir:
>      - "[aA]rtwork/"
>    images:
>      - "*.jpg"
>      - "*.jpeg"
>      - "*.png"
> ```
>
> Thus, it will only match the pattern `path` of `pattern:artworkdir` and _not_
> `pattern:images`. Please note that irrespective if it matches a pattern, if
> there is a more specific path [per the renaming rules](#new-path-queries) it will use
> that instead.

[glob patterns]: https://docs.python.org/3/library/glob.html#module-glob

##### Pattern Example Configuration

This example will match if the filename of the given artifact or extra file matches the
name exactly as specified, either `cover.jpg` or `artifact.nfo`.

This example will match all files within the given subdirectory of either `artwork/` or
`Artwork/`. Since it's not otherwise specified, `[aA]rtwork/` will grab all non-media
files in that subdirectory irrespective of name or extension.

```yaml
filetote:
  patterns:
    artworkdir:
      - "[aA]rtwork/"
```

##### Pattern Renaming Example

The following pattern configuration will rename the file `artwork/cover.jpeg` to:
`~/Music/Artist/2014 - Album/artwork/cover.jpeg`

```yaml
filetote:
  paths:
    pattern:artworkdir: $albumpath/artwork/$old_filename
  patterns:
    artworkdir:
      - "[aA]rtwork/"
```

#### Pairing (`pairing:`)

Filetote can specially target related files like lyrics or logs with the same name as
music files ("paired" files). This keeps related files together, making your library
even more organized. When enabled, it will match and move those files having the same
name as a matching music file. Pairing can be configured to target only certain
extensions, such as `.lrc`. By default, all paired files will be targeted unless
specific extensions are specified (at which point only those extensions will be
grabbed).

> [!NOTE]
> Pairing takes precedence over other Filetote rules like filename or patterns.

##### Pairing Example Configuration

This example configuration will grab paired `.lrc` files, along with any artwork files:

```yaml
filetote:
  pairing:
    enabled: true
    extensions: ".lrc"
  patterns:
    artworkdir:
          - "[aA]rtwork/"
```

Filetote can also be configured to _only_ target paired files, which will ignore other
Filetote configurations such as filename or patterns as described above. The following
configuration would _only_ target `.lrc` files:

```yaml
filetote:
  pairing:
    enabled: true
    pairing_only: true
    extensions: ".lrc"
```

##### Pairing Renaming

To maintain the concept of "pairs" after importing, the default `path` for the paired
files will use the media files new name. This will ensure that the file remains paired
even after moving. This is equivalent to setting:

```yaml
paths:
  paired_ext:.lrc: $albumpath/$medianame_new
```

This can be updated for any specific extension, such as the following which keeps the
old filename:

```yaml
paths:
  paired_ext:.lrc: $albumpath/$old_filename
```

> [!NOTE]
> To update the default pairing renaming for _all_ paired files away from
> `$albumpath/$medianame_new`, use the `filetote-pairing:default` path specification.

### Excluding Files (`exclude:`)

Certain artifact files can be excluded/ignored by specifying settings under the
`exclude` via `filenames`, `extensions`, and/or `patterns`. For example, to always
exclude files named either `song_lyrics.nfo` or `album_description.nfo`, you can
specify:

```yaml
filetote:
  exclude:
    filenames: song_lyrics.nfo album_description.nfo
```

Likewise, to more broadly exclude extensions `.nfo` and `.lrc`, specify:

```yaml
filetote:
  exclude:
    extensions: .nfo .lrc
```

Likewise, patterns can be used to perform more specialized exclusions, such as excluding
all files in a subdirectory. For example, to exclude all artifact files in the
subdirectories `artwork` and/or `Artwork`:

```yaml
filetote:
  exclude:
    patterns:
      artworkdir:
        - "[aA]rtwork/"
```

`exclude` patterns follow the same glob rules specified the [higher-level `patterns` config](#pattern-patterns).

These can be combined to exclude any combination. For example, you can exclude by
filename and pattern:

```yaml
filetote:
  exclude:
    filenames: song_lyrics.nfo
    patterns:
      artworkdir:
        - "[aA]rtwork/"
```

> [!IMPORTANT]
> `exclude`-qualiefied files take precedence over other matching, meaning exclude will override
> other matches by either `extensions` or `filenames`.

### Handling Duplicate Artifacts (`duplicate_action:`)

When an artifact or extra file is imported, it is possible that a file with the same
name already exists in the destination directory (for example, during a re-import or
if multiple source files map to the same destination filename).

The `duplicate_action` config option controls how Filetote handles these collisions:

```yaml
filetote:
  duplicate_action: skip
```

The available options are:

- `skip` (default): The existing file in the destination is preserved, and the new
  file is ignored.
- `keep`: Both files are kept. The new file is renamed by appending a number to
  the filename (e.g., `artifact.1.log`) to make it unique, in the same way as how beets
  handles duplicate music tracks.
- `remove`: The new file overwrites the existing file. Use with caution!

It is also possible to "sidestep" collisions, `$old_filename` can be used in conjunction
with other fields to keep uniqueness in each name.

> [!IMPORTANT]
> If the source file and the destination file are actually the _same file in the same
> place_ (i.e., the source and destination paths are identical), Filetote will always do
> nothing, regardless of this setting.

### Import Operations

This plugin supports the same operations as beets:

- `copy`
- `move`
- `link` (symlink)
- `hardlink`
- `reflink`

These options are mutually exclusive, and there are nuances to how beets (and thus this
plugin) behave when there multiple set. See the [beets import documentation] and [#36]
for more details.

Reimporting has an additional nuance when copying of linking files that are already in
the library, in which files will be moved rather than duplicated. This behavior in
Filetote is identical to that of beets. See the [beets reimport documentation] for more
details.

[beets import documentation]: https://beets.readthedocs.io/en/stable/reference/config.html#importer-options
[#36]: https://github.com/gtronset/beets-filetote/pull/36
[beets reimport documentation]: https://beets.readthedocs.io/en/stable/reference/cli.html#reimporting

### Other CLI Operations

Additional commands such as `move`, `modify`, `update`, etc. will also trigger
Filetote to handle files. These commands typically work with [queries], targeting
specific files that match the supplied query. Please note that the operation executed
by beets for these commands do not use the value set in the config file under `import`,
they instead are specified as part of the CLI command.

[queries]: https://beets.readthedocs.io/en/stable/reference/query.html

### Examples of `config.yaml`

```yaml
plugins: filetote

paths:
  default: $albumartist/$year - $album/$track - $title
  singleton: Singletons/$artist - $title
  ext:.log: $albumpath/$artist - $album
  ext:.cue: $albumpath/$artist - $album
  paired_ext:.lrc: $albumpath/$medianame_new
  filename:cover.jpg: $albumpath/cover

filetote:
  extensions: .cue .log .png
  filenames: cover.jpg
  pairing:
    enabled: true
    extensions: ".lrc"
  print_ignored: true
```

Or:

```yaml
plugins: filetote

paths:
  default: $albumartist/$year - $album/$track - $title
  singleton: Singletons/$artist - $title

filetote:
  extensions: .txt .cue
  patterns:
    artworkdir:
      - "[sS]cans/"
      - "[aA]rtwork/"
  exclude:
    filenames: "copyright.txt"
  pairing:
    enabled: true
    extensions: .lrc
  paths:
    pattern:artworkdir: $albumpath/artwork
    paired_ext:.lrc: $albumpath/$medianame_old
    filename:cover.jpg: $albumpath/cover
```

## Multi-Disc and Nested Import Directories

beets imports multi-disc albums as a single unit ([see beets documentation]). By
default, this results in the media importing to a single directory in the library.
Artifacts and extra files in the initial subdirectories will be brought by Filetote to the
destination of the files they're near, resulting in them landing where one would expect.
Because of this, the files will also be moved by Filetote to any specified subdirectory
in the library if the path definition creates "Disc N" subfolders
[as described in the beets documentation].

In short, artifacts and extra files in these scenarios should simply just move/copy as
expected.

[see beets documentation]: https://beets.readthedocs.io/en/stable/faq.html#import-a-multi-disc-album
[as described in the beets documentation]: https://beets.readthedocs.io/en/stable/faq.html#create-disc-n-directories-for-multi-disc-albums

### Advanced renaming for multi-disc albums

The value for `$albumpath` is actually based on the path for the Item (music file) the
lead to the artifact to be moved. Since it's common to store multi-disc albums with
subfolders, this means that by default the artifact or extra file in question will also
be in a subfolder.

For macOS and Linux, to achieve a different location (say the media is in
`Artist/Disc 01`, but artifacts are intended to be in `Artist/Extras`), `..` can be used
to navigate to the parent directory of the `$albumpath` so that the entirety of the
media's path does not have to be recreated. For Windows, the entire media path would
need to be recreated as Windows sees `..` as an attempt to create a directory with the
name `..` within path instead of it being a path component representing the parent.

#### macOS & Linux

The following example will have the following results on macOS & Linux:

- Music: `~/Music/Artist/2014 - Album/Disc 1/media.mp3`
- Artifact: `~/Music/Artist/2014 - Album/Extras/example.log`

```yaml
plugins: filetote

paths:
  default: $albumartist/$year - $album/$track - $title
  comp: $albumartist/$year - $album/Disc $disc/$track - $title

filetote:
  extensions: .log
  paths:
    ext:log: $albumpath/../Extras/$old_filename
```

#### Windows

The following example will have the following results on Windows:

- Music: `~/Music/Artist/2014 - Album/Disc 1/media.mp3`
- Artifact: `~/Music/Artist/2014 - Album/Extras/example.log`

```yaml
plugins: filetote

paths:
  default: $albumartist/$year - $album/$track - $title
  comp: $albumartist/$year - $album/Disc $disc/$track - $title

filetote:
  extensions: .log
  paths:
    ext:log: $albumartist/$year - $album/Extras/$old_filename
```

## Filetote Compatibility with Other Plugins

Other plugins, including `inline` and `convert`, should be fully compatible with
Filetote. That said, sometimes there are small considerations. For example, the new
fields mentioned in [Renaming Considerations](#renaming-considerations) are _not_
usable by other plugins (such as `inline`). If you experience any issues with any
other plugins, [please report them].

> [!IMPORTANT]
> `convert` is only compatible with Filetote v1.0.3+. `convert` performs conversion
> very early in the import process, before other plugins. In prior versions of Filetote
> this would cause Filetote to look into the wrong location (the temporary file
> location on the newly converted media file), instead of the original source the media
> file came from. A special workaround was needed which was introduced in v1.0.3.

[please report them]: https://github.com/gtronset/beets-filetote/issues/new/choose

## Why Filetote and Not Other Similar Plugins?

Filetote serves the same core purpose as the [`copyartifacts` plugin] and the
[`extrafiles` plugin], however both have lacked in maintenance over the last few years.
There are outstanding bugs in each (though `copyartifacts` has seen some recent
activity resolving some). In addition, each are lacking in certain features and
abilities, such as hardlink/reflink support, "paired" file handling, and extending
renaming options. What's more, significant focus has been provided to Filetote around
Python3 conventions, linting, and typing in order to promote healthier code and easier
maintenance.

Filetote strives to encompass all functionality that _both_ `copyartifacts`
and `extrafiles` provide, and then some!

[`copyartifacts` plugin]: https://github.com/adammillerio/beets-copyartifacts
[`extrafiles` plugin]: https://github.com/Holzhaus/beets-extrafiles

### Migrating from `copyartifacts`

Filetote can be configured using nearly identical configuration as `copyartifacts`,
simply replacing the name of the plugin in its configuration settings. **There is one
change that's needed if all extensions are desired, as Filetote does not grab all
extensions by default (as `copyartifacts` does).** To accommodate, simply explicitly
state all extension using `.*`:

```yaml
filetote:
  extensions: .*
```

Otherwise, simply replacing the name in the config section will work. For example:

```yaml
copyartifacts:
  extensions: .cue .log
```

Would become:

```yaml
filetote:
  extensions: .cue .log
```

Path definitions can also be specified in the way that `copyfileartifacts` does,
alongside other path definitions for beets. E.g.:

```yaml
paths:
  ext:log: $albumpath/$artist - $album
```

### Migrating from `extrafiles`

Filetote can be configured using nearly identical configuration as `extrafiles`, simply
replacing the name of the plugin in its configuration settings. For example:

```yaml
extrafiles:
  patterns:
    all: "*.*"
```

Would become:

```yaml
filetote:
  patterns:
    all: "*.*"
```

Path definitions can also be specified similar to the way that `extrafiles` does;
however, unlike `extrafiles` which would implicitly append the original filename to any
path, Filetote is more explicit, and you **must** include either `$old_filename` or
`$medianame_new` in your path definition.

For example, to move all files from an artwork directory into a destination "artwork"
directory, you would change this `extrafiles` config:

```yaml
extrafiles:
  patterns:
    artworkdir:
      - "[sS]cans/"
      - "[aA]rtwork/"
  paths:
    artworkdir: $albumpath/artwork
```

To this Filetote config, explicitly adding `$old_filename`:

```yaml
filetote:
  patterns:
    artworkdir:
      - "[sS]cans/"
      - "[aA]rtwork/"
  paths:
    artworkdir: $albumpath/artwork/$old_filename
```

This helps make configuration clearer and removes any ambiguity about how files will be
named.

## Version Upgrade Instructions

Certain versions require changes to configurations as upgrades occur. Please see below
for specific steps for each version.

### `1.2.0`

#### Default renaming of paired files now matches the track's new name

Previously, paired files needed manual naming specification to remain paired. This has
been updated in version `1.2.0` to automatically use the newer file name so that paired
files remain paired after importing. That setting can be overridden as needed. See the
section on [Pairing Renaming](#pairing-renaming) for more details.

### `1.0.2`

#### Config for `exclude` now expects explicit `filenames`, `extensions`, or `patterns`

As of version `1.0.2`, Filetote now emits a deprecation warning for configurations
setting `exclude` to a simple list of filenames. Instead, Filetote now expects explicit
`filenames`, `extensions`, and/or `patterns`, e.g.:

```yaml
filetote:
  exclude:
    filenames: song_lyrics.nfo album_description.nfo
```

Contrast to the previous configuration (now deprecated):

```yaml
filetote:
  exclude: song_lyrics.nfo album_description.nfo
```

For now, the old configuration style is still supported but logged as deprecated. In a
future version this setting will no longer be backwards compatible.

### `0.4.0`

#### Default for `extensions` is now `None`

As of version `0.4.0`, Filetote no longer set the default for `extensions` to `.*`.
Instead, setting Filetote to collect all extensions needs to be explicitly defined, e.g.:

```yaml
filetote:
  extensions: .*
```

#### Pairing Config Changes

`pairing` has been converted from a boolean to an object with other like-config. Take
the following config:

```yaml
filetote:
  pairing: true
  pairing_only: false
```

These will both now be represented as individual settings within `pairing`:

```yaml
filetote:
  pairing:
    enabled: true
    pairing_only: false
    extensions: ".lrc"
```

Both remain optional and both default to `false`.

## Development & Contributing

Thank you for considering contributing to Filetote! Information on how you can
contribute, develop, or help can be found in [CONTRIBUTING.md].

[CONTRIBUTING.md]: CONTRIBUTING.md

## Thanks

This plugin originated as a hard fork from [beets-copyartifacts (copyartifacts3)].

Thank you to the original work done by Sami Barakat and Adrian Sampson, along with the
larger beets' community.

Please [report any issues] you may have and feel free to contribute.

[beets-copyartifacts (copyartifacts3)]: https://github.com/adammillerio/beets-copyartifacts
[report any issues]: https://github.com/gtronset/beets-filetote/issues/new/choose

## License

Copyright (c) 2022-2026 Gavin Tronset

Licensed under the [MIT license][license link].

[license image]: https://img.shields.io/badge/License-MIT-blue.svg
[license link]: https://github.com/gtronset/beets-filetote/blob/main/LICENSE
[ci image]: https://github.com/gtronset/beets-filetote/actions/workflows/ci-test-lint.yaml/badge.svg
[ci link]: https://github.com/gtronset/beets-filetote/actions/workflows/ci-test-lint.yaml
[github image]: https://img.shields.io/github/release/gtronset/beets-filetote.svg
[github link]: https://github.com/gtronset/beets-filetote/releases
[pypi_version]: https://img.shields.io/pypi/v/beets-filetote
[pypi_link]: https://pypi.org/project/beets-filetote/
[pypi_python_versions]: https://img.shields.io/pypi/pyversions/beets-filetote
