This is a fork of copyartifacts, which was created in its entirety by Sami
Barakat. It includes Python 3 fixes and has been published to PyPI as
beets-copyartifacts3.

copyartifacts plugin for beets
==============================

.. image:: https://travis-ci.org/adammillerio/beets-copyartifacts.svg?branch=master
    :target: https://travis-ci.org/adammmillerio/beets-copyartifacts

A plugin that moves non-music files during the import process.

This is a plugin for `beets <http://beets.radbox.org/>`__: a music
library manager and much more.

Installing
----------

Stable
~~~~~~

The stable version of the plugin is available from PyPI. Installation can be done using pip:

::

    pip install beets-copyartifacts3

If you get permission errors try running it with ``sudo``

Development
~~~~~~~~~~~

The development version can be installed from GitHub by using these commands:

::

    git clone https://github.com/adammillerio/beets-copyartifacts.git
    cd beets-copyartifacts
    python setup.py install

If you get permission errors try running it with ``sudo``

Configuration
-------------

You will need to enable the plugin in beets' config.yaml

::

    plugins: copyartifacts

It can copy files by file extenstion:

::

    copyartifacts:
        extensions: .cue .log

Or copy all non-music files (it does this by default):

::

    copyartifacts:
        extensions: .*

It can also print what got left:

::

    copyartifacts:
        print_ignored: yes

Renaming files
~~~~~~~~~~~~~~

Renaming works in much the same way as beets `Path
Formats <http://beets.readthedocs.org/en/stable/reference/pathformat.html>`__
with the following limitations: - The fields available are ``$artist``,
``$albumartist``, ``$album`` and ``$albumpath``. - The full set of
`built in
functions <http://beets.readthedocs.org/en/stable/reference/pathformat.html#functions>`__
are also supported, with the exception of ``%aunique`` - which will
return an empty string.

Each template string uses a query syntax for each of the file
extensions. For example the following template string will be applied to
``.log`` files:

::

    paths:
        ext:log: $albumpath/$artist - $album

This will rename a log file to:
``~/Music/Artist/2014 - Album/Artist - Album.log``

Example config
~~~~~~~~~~~~~~

::

    plugins: copyartifacts

    paths:
        default: $albumartist/$year - $album/$track - $title
        singleton: Singletons/$artist - $title
        ext:log: $albumpath/$artist - $album
        ext:cue: $albumpath/$artist - $album
        ext:jpg: $albumpath/cover

    copyartifacts:
        extensions: .cue .log .jpg
        print_ignored: yes

Thanks
------

copyartifacts was built in its entirety by Sami Barakat. This fork
is simply a Python 3 compatible version published to PyPI.

copyartifacts was built on top of the hard work already done by Adrian
Sampson and the larger community on
`beets <http://beets.radbox.org/>`__. We have also benefited from the
work of our
`contributors <https://github.com/adammillerio/beets-copyartifacts/graphs/contributors>`__.

This plugin was built out of necessity and to scratch an itch. It has
gained a bit of attention, so I intend to maintain it where I can,
however I doubt I will be able to spend large amount of time on it.
Please report any issues you may have and feel free to contribute.

License
-------

Copyright (c) 2015-2017 Sami Barakat
Copyright (c) 2020 Adam Miller

Licensed under the `MIT
license <https://github.com/adammillerio/beets-copyartifacts/blob/master/LICENSE>`__.
