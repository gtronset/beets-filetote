import filecmp
import os
import sys

import beets.util
from beets import config
from beets.library import DefaultTemplateFunctions
from beets.plugins import BeetsPlugin
from beets.ui import get_path_formats
from beets.util.functemplate import Template
from mediafile import TYPES


class CopyFileArtifactsPlugin(BeetsPlugin):
    def __init__(self):
        super(CopyFileArtifactsPlugin, self).__init__()

        self.config.add(
            {
                "extensions": ".*",
                "filenames": "",
                "exclude": "",
                "print_ignored": False,
                "pairing": False,
                "pairing_only": False,
            }
        )

        self.operation = self._operation_type()

        self._process_queue = []
        self._shared_artifacts = {}
        self._dirs_seen = []

        self.extensions = self.config["extensions"].as_str_seq()
        self.filenames = self.config["filenames"].as_str_seq()
        self.exclude = self.config["exclude"].as_str_seq()
        self.print_ignored = self.config["print_ignored"].get()
        self.pairing = self.config["pairing"].get()
        self.pairing_only = self.config["pairing_only"].get()

        queries = ["filename:", "paired_ext:", "ext:"]

        self.path_formats = [
            path_format
            for path_format in beets.ui.get_path_formats()
            for query in queries
            if (path_format[0][: len(query)] == query)
        ]

        self.register_listener("import_begin", self._register_source)
        self.register_listener("item_moved", self.collect_artifacts)
        self.register_listener("item_copied", self.collect_artifacts)
        self.register_listener("item_linked", self.collect_artifacts)
        self.register_listener("item_hardlinked", self.collect_artifacts)
        self.register_listener("item_reflinked", self.collect_artifacts)
        self.register_listener("cli_exit", self.process_events)

    def _register_source(self, session):
        """ """
        self.paths = os.path.expanduser(session.paths[0])

    def _destination(self, filename, mapping, paired=False):
        """Returns a destination path a file should be moved to. The filename
        is unique to ensure files aren't overwritten. This also checks the
        config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file
        extension the original filename is used with the album path.
            - ripped from beets/library.py
        """

        full_filename = filename.decode("utf8")
        file_name_no_ext = os.path.splitext(filename)[0].decode("utf8")
        file_ext = os.path.splitext(filename)[1].decode("utf8")

        mapping["old_filename"] = file_name_no_ext

        selected_path_query = "None"
        selected_path_format = "None"

        for query, path_format in self.path_formats:
            ext_len = len("ext:")
            filename_len = len("filename:")
            paired_ext_len = len("paired_ext:")

            if (
                paired
                and query[:paired_ext_len] == "paired_ext:"
                and file_ext == ("." + query[paired_ext_len:].lstrip("."))
            ):
                # Prioritize `filename:` query selectory over `paired_ext:`
                if selected_path_query != "filename:":
                    selected_path_query = "paired_ext:"
                    selected_path_format = path_format
            elif query[:ext_len] == "ext:" and file_ext == (
                "." + query[ext_len:].lstrip(".")
            ):
                # Prioritize `filename:` and `paired_ext:` query selectory over
                # `ext:`
                if selected_path_query not in ["filename:", "paired_ext:"]:
                    selected_path_query = "ext:"
                    selected_path_format = path_format

            elif (
                query[:filename_len] == "filename:"
                and full_filename == query[filename_len:]
            ):
                selected_path_query = "filename:"
                selected_path_format = path_format

        if selected_path_query == "None":
            # No query matched; use original filename
            file_path = os.path.join(
                mapping["albumpath"], beets.util.displayable_path(filename)
            )
            return file_path

        if isinstance(selected_path_format, Template):
            subpath_tmpl = selected_path_format
        else:
            subpath_tmpl = Template(selected_path_format)

        # Get template funcs and evaluate against mapping
        funcs = DefaultTemplateFunctions().functions()
        file_path = subpath_tmpl.substitute(mapping, funcs) + file_ext

        # Sanitize filename
        filename = beets.util.sanitize_path(os.path.basename(file_path))
        dirname = os.path.dirname(file_path)
        file_path = os.path.join(dirname, filename)

        return file_path

    # XXX: may be better to use FormattedMapping class from beets/dbcore/db.py
    def _get_formatted(self, value):
        """Replace path separators in value
        - ripped from beets/dbcore/db.py
        """
        sep_repl = beets.config["path_sep_replace"].as_str()
        for sep in (os.path.sep, os.path.altsep):
            if sep:
                value = value.replace(sep, sep_repl)

        return value

    def _generate_mapping(self, item, destination):
        mapping = {
            "artist": item.artist or "None",
            "albumartist": item.albumartist or "None",
            "album": item.album or "None",
        }
        for key in mapping:
            mapping[key] = self._get_formatted(mapping[key])

        album_path = os.path.dirname(destination)
        mapping["albumpath"] = beets.util.displayable_path(album_path)

        # TODO: Retool to utilize the OS's path separator
        # pathsep = beets.config["path_sep_replace"].get(str)
        strpath_old = beets.util.displayable_path(item.path)
        filename_old, fileext = os.path.splitext(os.path.basename(strpath_old))

        strpath_new = beets.util.displayable_path(destination)
        filename_new = os.path.splitext(os.path.basename(strpath_new))[0]

        mapping["medianame_old"] = filename_old
        mapping["medianame_new"] = filename_new

        return mapping

    def collect_artifacts(self, item, source, destination):
        item_source_filename = os.path.splitext(os.path.basename(source))[0]
        item_destination_filename = os.path.splitext(
            os.path.basename(destination)
        )[0]
        source_path = os.path.dirname(source)
        dest_path = os.path.dirname(destination)

        queue_files = []

        # Check if this path has already been processed
        if source_path in self._dirs_seen:

            # Check to see if "pairing" is enabled and, if so, if there are
            # artifacts to look at
            if self.pairing and self._shared_artifacts[source_path]:

                # Iterate through shared artifacts to find paired matches
                for filepath in self._shared_artifacts[source_path]:
                    file_name, file_ext = os.path.splitext(
                        os.path.basename(filepath)
                    )
                    if file_name == item_source_filename:
                        queue_files.append({"path": filepath, "paired": True})

                        # Remove from shared artifacts, as the item-move will
                        # handle this file.
                        self._shared_artifacts[source_path].remove(filepath)

                if queue_files:
                    self._process_queue.extend(
                        [
                            {
                                "files": queue_files,
                                "mapping": self._generate_mapping(
                                    item, destination
                                ),
                                "source_path": source_path,
                            }
                        ]
                    )

            return

        non_handled_files = []
        for root, dirs, files in beets.util.sorted_walk(
            source_path, ignore=config["ignore"].as_str_seq()
        ):
            for filename in files:
                source_file = os.path.join(root, filename)

                # Skip any files extensions handled by beets
                file_name, file_ext = os.path.splitext(filename)
                if len(file_ext) > 1 and file_ext.decode("utf8")[1:] in TYPES:
                    continue

                if not self.pairing:
                    queue_files.append({"path": source_file, "paired": False})
                elif self.pairing and file_name == item_source_filename:
                    queue_files.append({"path": source_file, "paired": True})
                else:
                    non_handled_files.append(source_file)

        self._process_queue.extend(
            [
                {
                    "files": queue_files,
                    "mapping": self._generate_mapping(item, destination),
                    "source_path": source_path,
                }
            ]
        )
        self._dirs_seen.extend([source_path])

        self._shared_artifacts[source_path] = non_handled_files

    def process_events(self, lib):
        # Ensure destination library settings are accessible
        self.lib = lib
        for item in self._process_queue:
            artifacts = item["files"]

            source_path = item["source_path"]

            if not self.pairing_only:
                for shared_artifact in self._shared_artifacts[source_path]:
                    artifacts.extend(
                        [{"path": shared_artifact, "paired": False}]
                    )

            self._shared_artifacts[source_path] = []

            self.process_artifacts(artifacts, item["mapping"], False)

    def process_artifacts(self, source_files, mapping, reimport=False):
        if not source_files:
            return

        ignored_files = []

        for artifact in source_files:
            source_file = artifact["path"]

            source_path = os.path.dirname(source_file)
            # os.path.basename() not suitable here as files may be contained
            # within dir of source_path
            filename = source_file[len(source_path) + 1 :]

            dest_file = self._destination(filename, mapping, artifact["paired"])

            # Skip as another plugin or beets has already moved this file
            if not os.path.exists(source_file):
                ignored_files.append(source_file)
                continue

            # Skip if filename is explicitly in `exclude`
            if filename.decode("utf8") in self.exclude:
                ignored_files.append(source_file)
                continue

            # Skip:
            # - extensions not allowed in `extensions`
            # - filenames not explicitly in `filenames`
            file_ext = os.path.splitext(filename)[1]
            if (
                ".*" not in self.extensions
                and file_ext.decode("utf8") not in self.extensions
                and filename.decode("utf8") not in self.filenames
            ):
                ignored_files.append(source_file)
                continue

            # Skip file if it already exists in dest
            if os.path.exists(dest_file) and filecmp.cmp(
                source_file, dest_file
            ):
                ignored_files.append(source_file)
                continue

            dest_file = beets.util.unique_path(dest_file)
            beets.util.mkdirall(dest_file)
            dest_file = beets.util.bytestring_path(dest_file)

            # TODO: detect if beets was called with 'move' and override config
            # option here

            # self._log.warning(str(self._operation_type()))

            if config["import"]["move"]:
                self._move_artifact(source_file, dest_file)
            else:
                if reimport:
                    # This is a reimport
                    # files are already in the library directory
                    self._move_artifact(source_file, dest_file)
                else:
                    # A normal import, just copy
                    self._copy_artifact(source_file, dest_file)

        if self.print_ignored and ignored_files:
            self._log.warning("Ignored files:")
            for f in ignored_files:
                self._log.warning("   {0}", os.path.basename(f))

    def _operation_type(self):
        """Returns the file manipulations type."""

        if config["import"]["move"]:
            operation = beets.util.MoveOperation.MOVE
        elif config["import"]["copy"]:
            operation = beets.util.MoveOperation.COPY
        elif config["import"]["link"]:
            operation = beets.util.MoveOperation.LINK
        elif config["import"]["hardlink"]:
            operation = beets.util.MoveOperation.HARDLINK
        elif config["import"]["reflink"]:
            operation = beets.util.MoveOperation.REFLINK
        else:
            operation = None

        return operation

    def manipulate_artifacts(self, source_file, dest_file):
        """Copy, move, link, hardlink or reflink (depending on `operation`)
        the files as well as write metadata.
        NOTE: `operation` should be an instance of `beets.util.MoveOperation`.
        """

        items = self.imported_items()
        # Save the original paths of all items for deletion and pruning
        # in the next step (finalization).
        self.old_paths = [item.path for item in items]
        for item in items:
            if self.operation is not None:
                # In copy and link modes, treat re-imports specially:
                # move in-library files. (Out-of-library files are
                # copied/moved as usual).
                old_path = item.path
                if (
                    self.operation != beets.util.MoveOperation.MOVE
                    and self.replaced_items[item]
                    and session.lib.directory in util.ancestry(old_path)
                ):
                    item.move()
                    # We moved the item, so remove the
                    # now-nonexistent file from old_paths.
                    self.old_paths.remove(old_path)
                else:
                    # A normal import. Just copy files and keep track of
                    # old paths.
                    item.move(self.operation)

    def _copy_artifact(self, source_file, dest_file):
        self._log.info(
            "Copying artifact: {0}".format(
                os.path.basename(dest_file.decode("utf8"))
            )
        )
        beets.util.copy(source_file, dest_file)

    def _move_artifact(self, source_file, dest_file):
        if not os.path.exists(source_file):
            # Sanity check for other plugins moving files
            return

        self._log.info(
            "Moving artifact: {0}".format(
                os.path.basename(dest_file.decode("utf8"))
            )
        )
        beets.util.move(source_file, dest_file)

        source_path = os.path.dirname(source_file)

        library_dir = self.lib.directory

        root_path = None

        if self.paths == library_dir:
            root_path = os.path.dirname(self.paths)
        elif library_dir in beets.util.ancestry(self.paths):
            root_path = self.paths

        beets.util.prune_dirs(
            source_path,
            root=root_path,
            clutter=config["clutter"].as_str_seq(),
        )
