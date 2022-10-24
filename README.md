# _copyfileartifacts_ plugin for beets

[![MIT license][license image]][license link] [![CI][ci image]][ci link]

A plugin that moves non-music files during the import process for
[beets](http://beets.radbox.org/), a music library manager (and much more!).

This is a fork of [copyartifacts3](https://github.com/adammillerio/beets-copyartifacts)
that expands functionality. beets-copyartifacts3 itself a fork of the archived
[copyartifacts (by Sami Barakat)](https://github.com/sbarakat/beets-copyartifacts)
which includes Python 3 fixes and was been published to PyPI as beets-copyartifacts3.

## Installing

### Stable

The stable version of the plugin is available from PyPI. Installation can be
done using pip:

```sh
pip install beets-copyfileartifacts
```

If you get permission errors, try running it with `sudo`.

### Development

The development version can be installed from GitHub by using these commands:

```sh
git clone https://github.com/gtronset/beets-copyfileartifacts.git
cd beets-copyfileartifacts
python setup.py install
```

If you get permission errors, try running it with `sudo`.

## Configuration

You will need to enable the plugin in beets' `config.yaml`:

```yaml
plugins: copyfileartifacts
```

It can copy files by file extension:

```yaml
copyfileartifacts:
  extensions: .cue .log
```

Or copy files by filename:

```yaml
copyfileartifacts:
  filenames: song.log
```

Or copy all non-music files (it does this by default):

```yaml
copyfileartifacts:
  extensions: .*
```

It can also exclude files by name:

```yaml
copyfileartifacts:
  exclude: song_lyrics.nfo
```

And print what got left:

```yaml
copyfileartifacts:
  print_ignored: yes
```

d
`exclude`-d files take precedence over other matching, meaning exclude will
trump other matches by either `extensions` or `filenames`.

### Renaming files

Renaming works in much the same way as beets [Path Formats](http://beets.readthedocs.org/en/stable/reference/pathformat.html)
with the following limitations:

- The fields available are `$artist`, `$albumartist`, `$album`, `$albumpath`,
  `$old_filename` (filename of the extra/artifcat file before its renamed),
  and `$item_old_filename` (filename of the item/track triggering it, before
  its renamed).
  - The full set of
    [built in functions](http://beets.readthedocs.org/en/stable/reference/pathformat.html#functions)
    are also supported, with the exception of `%aunique` - which will
    return an empty string.

Each template string uses a query syntax for each of the file
extensions. For example the following template string will be applied to
`.log` files:

```yaml
paths:
  ext:.log: $albumpath/$artist - $album
```

This will rename a log file to:
`~/Music/Artist/2014 - Album/Artist - Album.log`

> **Note:** if the rename is set and there are multiple files that qualify,
> only the first will be added to the library (new folder); other files that
> subsequently match will not be saved/renamed. To work around this,
> `$old_filename` can be used to help with adding uniqueness to the name.

### Example `config.yaml`

```yaml
plugins: copyfileartifacts

paths:
  default: $albumartist/$year - $album/$track - $title
  singleton: Singletons/$artist - $title
  ext:.log: $albumpath/$artist - $album
  ext:.cue: $albumpath/$artist - $album
  ext:.jpg: $albumpath/cover

copyfileartifacts:
  extensions: .cue .log .jpg
  print_ignored: yes
```

## Thanks

copyfileartifacts was built on top of the hard work already done by Sami
Barakat, Adrian Sampson, and the larger community on [beets](http://beets.radbox.org/).
We have also benefited from the work of our
[contributors](https://github.com/gtronset/beets-copyfileartifacts/graphs/contributors).

This plugin was built out of necessity and to scratch an itch. It has
gained a bit of attention, so I intend to maintain it where I can,
however I doubt I will be able to spend large amount of time on it.
Please report any issues you may have and feel free to contribute.

## License

Copyright (c) 2022 Gavin Tronset
Copyright (c) 2020 Adam Miller
Copyright (c) 2015-2017 Sami Barakat

Licensed under the [MIT license][license link].

[license image]: https://img.shields.io/badge/License-MIT-blue.svg
[license link]: https://github.com/gtronset/beets-copyfileartifacts/blob/master/LICENSE
[ci image]: https://github.com/gtronset/beets-copyfileartifacts/actions/workflows/tox.yml/badge.svg
[ci link]: https://github.com/gtronset/beets-copyfileartifacts/actions/workflows/tox.yml
