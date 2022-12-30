import filecmp
import os

from beets import config, util
from beets.library import DefaultTemplateFunctions
from beets.plugins import BeetsPlugin
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES


class FiletotePlugin(BeetsPlugin):
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        super().__init__()

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

        self.operation = None

        self._process_queue = []
        self._shared_artifacts = {}
        self._dirs_seen = []

        self.extensions = self.config["extensions"].as_str_seq()
        self.filenames = self.config["filenames"].as_str_seq()
        self.exclude = self.config["exclude"].as_str_seq()
        self.print_ignored = self.config["print_ignored"].get()
        self.pairing = self.config["pairing"].get()
        self.pairing_only = self.config["pairing_only"].get()

        queries = ["ext:", "filename:", "paired_ext:"]

        self.lib = None
        self.paths = None
        self.path_formats = [
            path_format
            for path_format in get_path_formats()
            for query in queries
            if (path_format[0][: len(query)] == query)
        ]

        move_events = [
            "item_moved",
            "item_copied",
            "item_linked",
            "item_hardlinked",
            "item_reflinked",
        ]

        for move_event in move_events:
            self.register_listener(move_event, self.collect_artifacts)

        self.register_listener("import_begin", self._register_session_settings)
        self.register_listener("cli_exit", self.process_events)

    def _register_session_settings(self, session):
        """Certain settings are only available and/or finalized once the
        import session begins."""
        self.operation = self._operation_type()
        self.paths = os.path.expanduser(session.paths[0])

    def _operation_type(self):
        """Returns the file manipulations type."""

        if config["import"]["move"]:
            operation = MoveOperation.MOVE
        elif config["import"]["copy"]:
            operation = MoveOperation.COPY
        elif config["import"]["link"]:
            operation = MoveOperation.LINK
        elif config["import"]["hardlink"]:
            operation = MoveOperation.HARDLINK
        elif config["import"]["reflink"]:
            operation = MoveOperation.REFLINK
        else:
            operation = None

        return operation

    def _destination(self, filename, mapping, paired=False):
        # pylint: disable=too-many-locals
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
                mapping["albumpath"], util.displayable_path(filename)
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
        filename = util.sanitize_path(os.path.basename(file_path))
        dirname = os.path.dirname(file_path)
        file_path = os.path.join(dirname, filename)

        return file_path

    # XXX: may be better to use FormattedMapping class from beets/dbcore/db.py
    def _get_formatted(self, value):
        """Replace path separators in value
        - ripped from beets/dbcore/db.py
        """
        sep_repl = config["path_sep_replace"].as_str()
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
        mapping["albumpath"] = util.displayable_path(album_path)

        # TODO: Retool to utilize the OS's path separator
        # pathsep = config["path_sep_replace"].get(str)
        strpath_old = util.displayable_path(item.path)
        filename_old, _fileext = os.path.splitext(os.path.basename(strpath_old))

        strpath_new = util.displayable_path(destination)
        filename_new = os.path.splitext(os.path.basename(strpath_new))[0]

        mapping["medianame_old"] = filename_old
        mapping["medianame_new"] = filename_new

        return mapping

    def collect_artifacts(self, item, source, destination):
        # pylint: disable=too-many-locals
        item_source_filename = os.path.splitext(os.path.basename(source))[0]
        source_path = os.path.dirname(source)

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
        for root, _dirs, files in util.sorted_walk(
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

            self.process_artifacts(artifacts, item["mapping"])

    def process_artifacts(self, source_files, mapping):
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

            dest_file = util.unique_path(dest_file)
            util.mkdirall(dest_file)
            dest_file = util.bytestring_path(dest_file)

            self.manipulate_artifact(source_file, dest_file)

        if self.print_ignored and ignored_files:
            self._log.warning("Ignored files:")
            for filename in ignored_files:
                self._log.warning("   {0}", os.path.basename(filename))

    def manipulate_artifact(self, source_file, dest_file):
        """Copy, move, link, hardlink or reflink (depending on `operation`)
        the files as well as write metadata.
        NOTE: `operation` should be an instance of `MoveOperation`.
        """

        if not os.path.exists(source_file):
            # Sanity check for other plugins moving files
            return

        # In copy and link modes, treat reimports specially: move in-library
        # files. (Out-of-library files are copied/moved as usual).
        reimport = False

        source_path = os.path.dirname(source_file)

        library_dir = self.lib.directory

        root_path = None

        if self.paths == library_dir:
            root_path = os.path.dirname(self.paths)
            reimport = True
        elif library_dir in util.ancestry(self.paths):
            root_path = self.paths
            reimport = True

        operation_display = self.operation

        if reimport:
            operation_display = "REIMPORT"

        self._log.info(
            f"{operation_display}-ing artifact:"
            f" {os.path.basename(dest_file.decode('utf8'))}"
        )

        if reimport or self.operation == MoveOperation.MOVE:
            util.move(source_file, dest_file)

            util.prune_dirs(
                source_path,
                root=root_path,
                clutter=config["clutter"].as_str_seq(),
            )
        elif self.operation == MoveOperation.COPY:
            util.copy(source_file, dest_file)
        elif self.operation == MoveOperation.LINK:
            util.link(source_file, dest_file)
        elif self.operation == MoveOperation.HARDLINK:
            util.hardlink(source_file, dest_file)
        elif self.operation == MoveOperation.REFLINK:
            util.reflink(source_file, dest_file, fallback=False)
        elif self.operation == MoveOperation.REFLINK_AUTO:
            util.reflink(source_file, dest_file, fallback=True)
        else:
            assert False, f"unknown MoveOperation {self.operation}"
