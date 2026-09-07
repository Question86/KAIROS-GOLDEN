from __future__ import annotations

import json
import os
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .errors import KickstartError


SOURCE_SUFFIXES = frozenset({".c", ".cc", ".cpp", ".cxx", ".cu"})
HEADER_SUFFIXES = frozenset({".h", ".hh", ".hpp", ".hxx", ".cuh", ".inl"})


@dataclass(frozen=True)
class CompilationUnit:
    relative_path: str
    absolute_path: Path
    directory: Path
    commands: tuple[str, ...]
    include_roots: tuple[Path, ...]


@dataclass(frozen=True)
class Survey:
    compile_commands: Path
    compile_commands_sha256: str
    units: tuple[CompilationUnit, ...]
    include_roots: tuple[Path, ...]
    ignored_external_include_roots: tuple[str, ...]
    source_kind: str
    cmake_file: Path | None = None
    cmake_sha256: str | None = None


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def reject_links(path: Path, root: Path, *, code: str = "LINKED_SOURCE_UNSUPPORTED") -> None:
    """Reject symlink/reparse components so a ledger path has one byte identity."""
    root_abs = Path(os.path.abspath(str(root)))
    candidate = Path(os.path.abspath(str(path)))
    try:
        relative = candidate.relative_to(root_abs)
    except ValueError as exc:
        raise KickstartError(code, f"path is outside the project root: {path}") from exc
    current = root_abs
    for part in relative.parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise KickstartError(code, f"cannot inspect path component: {current}") from exc
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise KickstartError(code, f"symlink or reparse component is not accepted: {current}")


def _validate_relative_for_authority(relative: str) -> None:
    # These characters would be ambiguous in the Workshop CMake list or the
    # DATAFLOW markdown table. Refusing them preserves an exact, parseable
    # source identity instead of silently escaping or rewriting a path.
    if any(char in relative for char in ("\n", "\r", "`", "|", "#")):
        raise KickstartError(
            "UNREPRESENTABLE_SOURCE_PATH",
            f"source path contains a character not representable by the authority ledgers: {relative!r}",
        )


def _normalized_relative(root: Path, path: Path) -> tuple[str, Path]:
    try:
        Path(os.path.abspath(str(path))).relative_to(Path(os.path.abspath(str(root))))
    except ValueError as exc:
        raise KickstartError(
            "SOURCE_OUTSIDE_PROJECT",
            f"compile_commands source is outside project_root: {path}",
        ) from exc
    reject_links(path, root)
    try:
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(root.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise KickstartError(
            "SOURCE_OUTSIDE_PROJECT",
            f"compile_commands source is missing or outside project_root: {path}",
        ) from exc
    if not resolved.is_file():
        raise KickstartError("SOURCE_NOT_FILE", f"compile_commands source is not a file: {resolved}")
    if resolved.suffix.casefold() not in SOURCE_SUFFIXES:
        raise KickstartError(
            "UNSUPPORTED_TRANSLATION_UNIT",
            f"unsupported translation-unit suffix for {relative}; supported: {sorted(SOURCE_SUFFIXES)}",
        )
    _validate_relative_for_authority(relative)
    return relative, resolved


def _regular_directory(path: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise KickstartError("COMPILE_DIRECTORY_MISSING", f"{label} does not exist: {path}") from exc
    if not resolved.is_dir():
        raise KickstartError("COMPILE_DIRECTORY_INVALID", f"{label} is not a directory: {resolved}")
    return resolved


def _command_tokens(entry: dict[str, Any], *, path: Path) -> list[str]:
    arguments = entry.get("arguments")
    command = entry.get("command")
    if isinstance(arguments, list):
        if not arguments or any(not isinstance(value, str) for value in arguments):
            raise KickstartError("COMPILE_COMMAND_INVALID", f"arguments must be a non-empty string array: {path}")
        return list(arguments)
    if isinstance(command, str) and command.strip():
        try:
            # CMake commonly stores a Windows command as one string. Use the
            # platform command-line parser there so quotes around paths with
            # spaces are removed without treating drive backslashes as escapes.
            if os.name == "nt":
                import ctypes

                argc = ctypes.c_int()
                parser = ctypes.windll.shell32.CommandLineToArgvW
                parser.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
                parser.restype = ctypes.POINTER(ctypes.c_wchar_p)
                argv = parser(command, ctypes.byref(argc))
                if not argv:
                    raise ValueError("CommandLineToArgvW returned no arguments")
                try:
                    return [argv[index] for index in range(argc.value)]
                finally:
                    ctypes.windll.kernel32.LocalFree(argv)
            return shlex.split(command, posix=True)
        except ValueError as exc:
            raise KickstartError("COMPILE_COMMAND_INVALID", f"cannot parse command in {path}: {exc}") from exc
    raise KickstartError("COMPILE_COMMAND_MISSING", f"entry has neither arguments nor command: {path}")


def _include_values(tokens: Iterable[str], directory: Path) -> tuple[list[Path], list[str]]:
    roots: list[Path] = []
    external: list[str] = []
    values = list(tokens)
    index = 0
    while index < len(values):
        token = values[index]
        value: str | None = None
        if token in {"-I", "/I", "-isystem", "-iquote", "/external:I"}:
            if index + 1 < len(values):
                index += 1
                value = values[index]
        elif token.startswith(("-I", "/I", "-isystem", "-iquote", "/external:I")):
            for prefix in ("-isystem", "-iquote", "/external:I", "-I", "/I"):
                if token.startswith(prefix) and len(token) > len(prefix):
                    value = token[len(prefix):]
                    break
        if value:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = directory / candidate
            try:
                resolved = candidate.resolve(strict=True)
            except OSError:
                # A missing include root is retained as evidence. The source
                # set remains intact while Workshop reports a referenced local
                # include that cannot be resolved.
                external.append(str(candidate))
            else:
                if resolved.is_dir():
                    roots.append(resolved)
                else:
                    external.append(str(resolved))
        index += 1
    return roots, external


def survey_compile_commands(
    compile_commands: Path,
    project_root: Path,
    *,
    source_kind: str = "compile_commands",
    cmake_file: Path | None = None,
    cmake_sha256: str | None = None,
) -> Survey:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise KickstartError("PROJECT_ROOT_INVALID", f"project_root is not a directory: {project_root}")
    compile_commands = compile_commands.resolve()
    if not compile_commands.is_file():
        raise KickstartError("COMPILE_COMMANDS_MISSING", f"compile_commands.json is missing: {compile_commands}")
    try:
        raw = compile_commands.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KickstartError("COMPILE_COMMANDS_INVALID", f"cannot read compile_commands.json: {compile_commands}") from exc
    if not isinstance(payload, list) or not payload:
        raise KickstartError("COMPILE_COMMANDS_EMPTY", f"compile_commands.json must be a non-empty array: {compile_commands}")

    by_relative: dict[str, dict[str, Any]] = {}
    ignored_external: set[str] = set()
    for index, item in enumerate(payload, 1):
        if not isinstance(item, dict):
            raise KickstartError("COMPILE_ENTRY_INVALID", f"compile_commands entry {index} is not an object")
        file_value = item.get("file")
        directory_value = item.get("directory")
        if not isinstance(file_value, str) or not file_value.strip():
            raise KickstartError("COMPILE_FILE_MISSING", f"compile_commands entry {index} has no file")
        if not isinstance(directory_value, str) or not directory_value.strip():
            raise KickstartError("COMPILE_DIRECTORY_MISSING", f"compile_commands entry {index} has no directory")
        directory_path = Path(directory_value)
        if not directory_path.is_absolute():
            directory_path = compile_commands.parent / directory_path
        directory = _regular_directory(directory_path, label=f"compile directory for entry {index}")
        source = Path(file_value)
        if not source.is_absolute():
            source = directory / source
        relative, absolute = _normalized_relative(project_root, source)
        tokens = _command_tokens(item, path=compile_commands)
        roots, external = _include_values(tokens, directory)
        ignored_external.update(external)
        record = by_relative.setdefault(
            relative,
            {"absolute": absolute, "directory": directory, "commands": [], "roots": set()},
        )
        record["commands"].append(" ".join(tokens))
        record["roots"].update(roots)

    units = tuple(
        CompilationUnit(
            relative_path=relative,
            absolute_path=record["absolute"],
            directory=record["directory"],
            commands=tuple(sorted(set(record["commands"]))),
            include_roots=tuple(sorted(record["roots"], key=lambda value: value.as_posix().casefold())),
        )
        for relative, record in sorted(by_relative.items(), key=lambda item: item[0].casefold())
    )
    include_roots = tuple(
        sorted(
            {
                root
                for unit in units
                for root in unit.include_roots
                if _inside(root, project_root)
            },
            key=lambda value: value.as_posix().casefold(),
        )
    )
    return Survey(
        compile_commands=compile_commands,
        compile_commands_sha256=_sha256(raw),
        units=units,
        include_roots=include_roots,
        ignored_external_include_roots=tuple(sorted(ignored_external)),
        source_kind=source_kind,
        cmake_file=cmake_file,
        cmake_sha256=cmake_sha256,
    )
