"""
Path validation utility for KiCad MCP.

Provides secure path validation to prevent path traversal attacks
and ensure file operations are restricted to safe directories.
"""

from collections.abc import Callable
import functools
import inspect
import logging
import os
import pathlib
from typing import Any

from kicad_mcp import config
from kicad_mcp.config import KICAD_EXTENSIONS

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""

    pass


class PathValidator:
    """
    Validates file paths for security and correctness.

    Prevents path traversal attacks and ensures files are within
    trusted directories with valid KiCad extensions.
    """

    def __init__(self, trusted_roots: set[str] | None = None):
        """
        Initialize path validator.

        Args:
            trusted_roots: Set of trusted root directories. If None,
                          uses current working directory.
        """
        self.trusted_roots = trusted_roots or {os.getcwd()}
        # Normalize trusted roots to absolute paths
        self.trusted_roots = {
            os.path.realpath(os.path.expanduser(root)) for root in self.trusted_roots
        }

    def add_trusted_root(self, root_path: str) -> None:
        """
        Add a trusted root directory.

        Args:
            root_path: Path to add as trusted root
        """
        normalized_root = os.path.realpath(os.path.expanduser(root_path))
        self.trusted_roots.add(normalized_root)

    def validate_path(self, file_path: str, must_exist: bool = False) -> str:
        """
        Validate a file path for security and correctness.

        Args:
            file_path: Path to validate
            must_exist: Whether the file must exist

        Returns:
            Normalized absolute path

        Raises:
            PathValidationError: If path validation fails
        """
        if not file_path or not isinstance(file_path, str):
            raise PathValidationError("Path must be a non-empty string")

        try:
            # Expand user home directory and resolve symbolic links
            normalized_path = os.path.realpath(os.path.expanduser(file_path))
        except (OSError, ValueError) as e:
            raise PathValidationError(f"Invalid path: {e}") from e

        # Check if path is within trusted roots
        if not self._is_within_trusted_roots(normalized_path):
            raise PathValidationError(f"Path '{file_path}' is outside trusted directories")

        # Check if file exists when required
        if must_exist and not os.path.exists(normalized_path):
            raise PathValidationError(f"Path does not exist: {file_path}")

        return normalized_path

    def validate_kicad_file(self, file_path: str, file_type: str, must_exist: bool = True) -> str:
        """
        Validate a KiCad file path with extension checking.

        Args:
            file_path: Path to validate
            file_type: Expected KiCad file type ('project', 'schematic', 'pcb', etc.)
            must_exist: Whether the file must exist

        Returns:
            Normalized absolute path

        Raises:
            PathValidationError: If path validation fails
        """
        # First validate the basic path
        normalized_path = self.validate_path(file_path, must_exist)

        # Check file extension
        if file_type not in KICAD_EXTENSIONS:
            raise PathValidationError(f"Unknown KiCad file type: {file_type}")

        expected_extension = KICAD_EXTENSIONS[file_type]
        if not normalized_path.endswith(expected_extension):
            raise PathValidationError(
                f"File must have {expected_extension} extension, got: {file_path}"
            )

        return normalized_path

    def validate_directory(self, dir_path: str, must_exist: bool = True) -> str:
        """
        Validate a directory path.

        Args:
            dir_path: Directory path to validate
            must_exist: Whether the directory must exist

        Returns:
            Normalized absolute directory path

        Raises:
            PathValidationError: If validation fails
        """
        normalized_path = self.validate_path(dir_path, must_exist)

        if must_exist and not os.path.isdir(normalized_path):
            raise PathValidationError(f"Path is not a directory: {dir_path}")

        return normalized_path

    def validate_project_directory(self, project_path: str) -> str:
        """
        Validate and return the directory containing a KiCad project file.

        Args:
            project_path: Path to .kicad_pro file

        Returns:
            Normalized absolute directory path

        Raises:
            PathValidationError: If validation fails
        """
        validated_project = self.validate_kicad_file(project_path, "project", must_exist=True)
        return os.path.dirname(validated_project)

    def create_safe_temp_path(self, base_name: str, extension: str = "") -> str:
        """
        Create a safe temporary file path within trusted directories.

        Args:
            base_name: Base name for the temporary file
            extension: File extension (including dot)

        Returns:
            Safe temporary file path
        """
        import tempfile

        # Use the first trusted root as temp directory base
        temp_root = next(iter(self.trusted_roots))

        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(temp_root, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Generate unique temp file path
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=extension, prefix=f"{base_name}_", dir=temp_dir
        )
        os.close(temp_fd)  # Close the file descriptor, we just need the path

        return temp_path

    def _is_within_trusted_roots(self, path: str) -> bool:
        """
        Check if a path is within any trusted root directory.

        Args:
            path: Normalized absolute path to check

        Returns:
            True if path is within trusted roots
        """
        for root in self.trusted_roots:
            try:
                # Check if path is within this root
                pathlib.Path(root).resolve()
                pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve())
                return True
            except ValueError:
                # Path is not relative to this root
                continue
        return False


# Global default validator instance
_default_validator = None


def default_trusted_roots() -> set[str]:
    """Return the directories the server is configured to work in.

    These are the same locations ``find_kicad_projects`` searches: the KiCad user
    directory plus ``config.ADDITIONAL_SEARCH_PATHS`` (``KICAD_SEARCH_PATHS`` and
    the existing default project locations). Anything ``list_projects`` returns
    therefore lies inside a trusted root.
    """
    return {config.KICAD_USER_DIR, *config.ADDITIONAL_SEARCH_PATHS}


def get_default_validator() -> PathValidator:
    """Get the default global path validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = PathValidator(default_trusted_roots())
    return _default_validator


def _default_error(message: str) -> dict[str, Any]:
    return {"success": False, "error": message}


def confine_paths(
    on_error: Callable[[str], Any] = _default_error, **params: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Confine path arguments of an MCP tool/resource to the trusted roots.

    Precondition enforced at the MCP boundary: each named argument, when not
    ``None``, must resolve (after ``~`` expansion, ``..`` normalisation and
    symlink resolution) to a location inside a trusted root. On success the
    wrapped function receives the resolved path; on failure it is not called and
    ``on_error(message)`` is returned instead, so each module keeps its own error
    shape.

    Args:
        on_error: Builds the tool's error return value from the rejection message.
        **params: Argument name -> kind. A key of ``KICAD_EXTENSIONS`` (e.g.
            ``"project"``, ``"schematic"``) also enforces that file extension;
            ``"path"`` accepts any file or directory.
    """
    for kind in params.values():
        if kind != "path" and kind not in KICAD_EXTENSIONS:
            raise ValueError(f"Unknown path kind: {kind}")

    def resolve(name: str, value: Any) -> Any:
        if value is None:
            return None
        validator = get_default_validator()
        kind = params[name]
        if kind == "path":
            return validator.validate_path(value, must_exist=False)
        return validator.validate_kicad_file(value, kind, must_exist=False)

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(fn)
        fn_name = getattr(fn, "__name__", repr(fn))
        missing = set(params) - set(signature.parameters)
        if missing:
            raise ValueError(f"{fn_name} has no parameter(s) {sorted(missing)}")

        def confine(args: tuple, kwargs: dict) -> inspect.BoundArguments | str:
            bound = signature.bind(*args, **kwargs)
            for name in params:
                if name in bound.arguments:
                    try:
                        bound.arguments[name] = resolve(name, bound.arguments[name])
                    except PathValidationError as e:
                        logger.warning("Rejected %s for %s: %s", name, fn_name, e)
                        return str(e)
            return bound

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                bound = confine(args, kwargs)
                if isinstance(bound, str):
                    return on_error(bound)
                return await fn(*bound.args, **bound.kwargs)

            wrapper = async_wrapper
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                bound = confine(args, kwargs)
                if isinstance(bound, str):
                    return on_error(bound)
                return fn(*bound.args, **bound.kwargs)

            wrapper = sync_wrapper

        # Marker read by the regression test that every path parameter is guarded.
        vars(wrapper)["__trusted_path_params__"] = dict(params)
        return wrapper

    return decorate


def validate_path(file_path: str, must_exist: bool = False) -> str:
    """Convenience function using default validator."""
    return get_default_validator().validate_path(file_path, must_exist)


def validate_kicad_file(file_path: str, file_type: str, must_exist: bool = True) -> str:
    """Convenience function using default validator."""
    return get_default_validator().validate_kicad_file(file_path, file_type, must_exist)


def validate_directory(dir_path: str, must_exist: bool = True) -> str:
    """Convenience function using default validator."""
    return get_default_validator().validate_directory(dir_path, must_exist)
