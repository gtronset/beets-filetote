# _Filetote_ plugin for beets

[![MIT license][license image]][license link]
[![CI][ci image]][ci link]
[![GitHub release][github image]][github link]
[![PyPI][pypi_version]][pypi_link]
[![PyPI - Python Version][pypi_python_versions]][pypi_link]

A plugin that moves non-music extra files, attachments, and artifacts during
the import process for [beets](http://beets.radbox.org/), a music library
manager (and much more!).

## Installing

### Stable

The stable version of the plugin is available from PyPI and can be installed
using `pip3`:

```sh
pip3 install beets-filetote
```

If you get permission errors, try running it with `sudo`.

### Development

The development version can be installed from GitHub by using these commands:

```sh
git clone https://github.com/gtronset/beets-filetote.git
cd beets-filetote
python setup.py install
```

If you get permission errors, try running it with `sudo`.

Update the `config.yaml` to utilize the local plugin with:

```yaml
pluginpath:
  - /path/to.../beets-filetote/beetsplug
```

## Configuration

You will need to enable the plugin in beets' `config.yaml`:

```yaml
plugins: filetote
```

It can copy files by file extension:

```yaml
filetote:
  extensions: .cue .log
```

Or copy files by filename:

```yaml
filetote:
  filenames: song.log
```

Or copy all non-music files (it does this by default):

```yaml
filetote:
  extensions: .*
```

It can look for and target "pairs" (files having the same name as a matching or
"paired" media item/track):

```yaml
filetote:
  pairing: True
```

And target/include only paired files:

```yaml
filetote:
  pairing: True
  pairing_only: True
```

It can also exclude files by name:

```yaml
filetote:
  exclude: song_lyrics.nfo
```

And print what got left:

```yaml
filetote:
  print_ignored: yes
```

`exclude`-d files take precedence over other matching, meaning exclude will
trump other matches by either `extensions` or `filenames`.

### Import Operations

This plugin supports the same operations as beets:

- `copy`
- `move`
- `link` (symlink)
- `harklink`
- `reflink`

These options are mutually exclusive, and there are nuances to how beets (and
thus this plugin) behave when there multiple set. See the [beets documentation]
and [#36](https://github.com/gtronset/beets-filetote/pull/36) for more details.

[beets documentation]: https://beets.readthedocs.io/en/stable/reference/config.html#importer-options

### Renaming files

Renaming works in much the same way as beets [Path Formats](http://beets.readthedocs.org/en/stable/reference/pathformat.html).
This plugin supports the below new path queries (from least to most specific).
Each takes a single corresponding value.

- `ext:`
- `paired_ext:`
- `filename:`

Renaming has the following considerations:

- The fields available are `$artist`, `$albumartist`, `$album`, `$albumpath`,
  `$old_filename` (filename of the extra/artifcat file before its renamed),
  `$medianame_old` (filename of the item/track triggering it, _before_
  its renamed), and `$medianame_new` (filename of the item/track triggering it, _after_
  its renamed).
- The full set of
  [built in functions](http://beets.readthedocs.org/en/stable/reference/pathformat.html#functions)
  are also supported, with the exception of `%aunique` - which will
  return an empty string.
- `filename:` path query will take precedence over `paired_ext:` and `ext:` if
  a given file qualifies for them. `paired_ext:` takes precedence over `ext:`,
  but is not required.

Each template string uses a query syntax for each of the file
extensions. For example the following template string will be applied to
`.log` files by using the `ext:` query:

```yaml
paths:
  ext:.log: $albumpath/$artist - $album
```

This will rename a log file to:
`~/Music/Artist/2014 - Album/Artist - Album.log`

Or by using the `filename:` query:

```yaml
paths:
  filename:track.log: $albumpath/$artist - $album
```

This will rename the specific `track.log` log file to:
`~/Music/Artist/2014 - Album/Artist - Album.log`

> **Note:** if the rename is set and there are multiple files that qualify,
> only the first will be added to the library (new folder); other files that
> subsequently match will not be saved/renamed. To work around this,
> `$old_filename` can be used to help with adding uniqueness to the name.

### Example `config.yaml`

```yaml
plugins: filetote

paths:
  default: $albumartist/$year - $album/$track - $title
  singleton: Singletons/$artist - $title
  ext:.log: $albumpath/$artist - $album
  ext:.cue: $albumpath/$artist - $album
  paired_ext:.lrc: $albumpath/$medianame_old
  filename:cover.jpg: $albumpath/cover

filetote:
  extensions: .cue .log .jpg .lrc
  filename: "cover.jpg"
  pairing: True
  print_ignored: yes
```

## Thanks

This plugin originally was a fork from [copyartifacts3 (Adrian Sampson)] (no
longer actively maintained) to expand functionality. `beets-copyartifacts3`
itself a fork of the archived [copyartifacts (Sami Barakat)].

Filetote was built on top of the excellent work done by Sami Barakat, Adrian
Sampson, and the larger community on [beets](http://beets.radbox.org/).

Please report any issues you may have and feel free to contribute.

[copyartifacts3 (adrian sampson)]: https://github.com/adammillerio/beets-copyartifacts
[copyartifacts (sami barakat)]: https://github.com/sbarakat/beets-copyartifacts

## License

Copyright (c) 2022 Gavin Tronset
Copyright (c) 2020 Adam Miller
Copyright (c) 2015-2017 Sami Barakat

Licensed under the [MIT license][license link].

[license image]: https://img.shields.io/badge/License-MIT-blue.svg
[license link]: https://github.com/gtronset/beets-filetote/blob/main/LICENSE
[ci image]: https://github.com/gtronset/beets-filetote/actions/workflows/tox.yml/badge.svg
[ci link]: https://github.com/gtronset/beets-filetote/actions/workflows/tox.yml
[github image]: https://img.shields.io/github/release/gtronset/beets-filetote.svg
[github link]: https://github.com/gtronset/beets-filetote/releases
[pypi_version]: https://img.shields.io/pypi/v/beets-filetote
[pypi_link]: https://pypi.org/project/beets-filetote/
[pypi_python_versions]: https://img.shields.io/pypi/pyversions/beets-filetote
