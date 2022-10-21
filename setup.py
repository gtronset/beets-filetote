#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup for beets-copyfileartifacts."""

from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

setup(
    name="beets-copyfileartifacts",
    version="0.1.0",
    description="beets plugin to copy non-music files to import path",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Gavin Tronset",
    author_email="gtronset@gmail.com",
    url="https://github.com/gtronset/beets-copyfileartifacts",
    download_url="https://github.com/gtronset/beets-copyfileartifacts.git",
    license="MIT",
    platforms="ALL",
    packages=["beetsplug"],
    namespace_packages=["beetsplug"],
    install_requires=["beets>=1.4.7", "mediafile~=0.10.0"],
    classifiers=[
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Players :: MP3",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
