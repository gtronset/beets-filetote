"""Vendored DummyIO for mocking stdin/stdout in beets plugin tests."""

from __future__ import annotations

import sys

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO


class InputError(Exception):
    def __init__(self, output: str | None = None):
        self.output = output

    def __str__(self) -> str:
        msg = "Attempt to read with no input provided."
        if self.output is not None:
            msg += f" Output: {self.output!r}"
        return msg


class DummyOut:
    encoding = "utf-8"

    def __init__(self) -> None:
        self.buf: list[str] = []

    def write(self, s: str | bytes) -> None:
        if isinstance(s, bytes):
            s = s.decode(self.encoding, "replace")
        self.buf.append(s)

    def get(self) -> str:
        return "".join(self.buf)

    def flush(self) -> None:
        pass

    def clear(self) -> None:
        self.buf = []


class DummyIn:
    encoding = "utf-8"

    def __init__(self, out: DummyOut | None = None):
        self.buf: list[str] = []
        self.reads: int = 0
        self.out = out

    def add(self, s: str) -> None:
        self.buf.append(f"{s}\n")

    def close(self) -> None:
        pass

    def readline(self) -> str:
        if not self.buf:
            if self.out:
                raise InputError(self.out.get())
            else:
                raise InputError()
        self.reads += 1
        return self.buf.pop(0)


class DummyIO:
    """Mocks input and output streams for testing UI code."""

    def __init__(self) -> None:
        self.stdout: DummyOut = DummyOut()
        self.stdin: DummyIn = DummyIn(self.stdout)
        self._orig_stdin: TextIO | None = None
        self._orig_stdout: TextIO | None = None

    def addinput(self, s: str) -> None:
        self.stdin.add(s)

    def getoutput(self) -> str:
        res = self.stdout.get()
        self.stdout.clear()
        return res

    def readcount(self) -> int:
        return self.stdin.reads

    def install(self) -> None:
        self._orig_stdin = sys.stdin
        self._orig_stdout = sys.stdout
        sys.stdin = self.stdin
        sys.stdout = self.stdout

    def restore(self) -> None:
        if self._orig_stdin is not None:
            sys.stdin = self._orig_stdin
        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout
