"""Exception hierarchy.

Every error raised on purpose by Slicra derives from :class:`SlicraError`
and carries an ``exit_code`` that the CLI uses verbatim, so library callers and
shell scripts see the same classification.
"""

from __future__ import annotations


class SlicraError(Exception):
    """Base class for all Slicra errors."""

    exit_code = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message


class ConfigError(SlicraError):
    """The configuration (YAML, CLI options or API arguments) is invalid."""

    exit_code = 2


class DetectionError(SlicraError):
    """Detection could not produce a trustworthy list of regions."""

    exit_code = 3


class NoRegionsError(DetectionError):
    """Detection finished but found zero regions."""


class ImageLoadError(SlicraError):
    """The input image is missing, unreadable, empty or exceeds the limits."""

    exit_code = 4


class ExportError(SlicraError):
    """Writing outputs failed or would overwrite/escape something it should not."""

    exit_code = 5


class MissingDependencyError(SlicraError):
    """An optional extra (for example ``slicra[opencv]``) is not installed."""

    exit_code = 6
