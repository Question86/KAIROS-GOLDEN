from __future__ import annotations

import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import KickstartError


@dataclass(frozen=True)
class CMakeConfigure:
    cmake_file: Path
    build_directory: Path
    compile_commands: Path
    stdout: str
    stderr: str
    temporary_build: bool


def configure_compile_commands(
    project_root: Path,
    cmake_file: Path,
    *,
    cmake_executable: str = "cmake",
    build_directory: Path | None = None,
    timeout_seconds: int = 300,
) -> CMakeConfigure:
    project_root = project_root.resolve()
    cmake_file = cmake_file.resolve()
    if not project_root.is_dir():
        raise KickstartError("PROJECT_ROOT_INVALID", f"project_root is not a directory: {project_root}")
    try:
        cmake_file.relative_to(project_root)
    except ValueError as exc:
        raise KickstartError("CMAKE_OUTSIDE_PROJECT", f"CMake file is outside project_root: {cmake_file}") from exc
    if not cmake_file.is_file():
        raise KickstartError("CMAKE_FILE_MISSING", f"CMake file is missing: {cmake_file}")

    temporary = build_directory is None
    if temporary:
        build_directory = Path(tempfile.mkdtemp(prefix="kairos-cmake-"))
    else:
        build_directory = build_directory.resolve()
        build_directory.mkdir(parents=True, exist_ok=True)
    source_directory = cmake_file.parent
    command = [
        cmake_executable,
        "-S",
        str(source_directory),
        "-B",
        str(build_directory),
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ]
    # Visual Studio generators do not emit compile_commands.json. Prefer a
    # generator with a compiler-command database when one is available, while
    # retaining the platform default as the final fallback for toolchains that
    # provide no Make/Ninja driver.
    if shutil.which("ninja"):
        command[1:1] = ["-G", "Ninja"]
    elif shutil.which("mingw32-make"):
        command[1:1] = ["-G", "MinGW Makefiles"]
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KickstartError(
            "CMAKE_CONFIGURE_FAILED",
            f"could not execute CMake configure: {exc}",
            details={"command": command},
        ) from exc
    if completed.returncode != 0:
        raise KickstartError(
            "CMAKE_CONFIGURE_FAILED",
            f"CMake configure exited with status {completed.returncode}",
            details={
                "command": command,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            },
        )
    compile_commands = build_directory / "compile_commands.json"
    if not compile_commands.is_file():
        raise KickstartError(
            "COMPILE_COMMANDS_MISSING",
            "CMake configure succeeded but did not emit compile_commands.json; "
            "the project must enable a compiler-backed source authority",
            details={"build_directory": str(build_directory)},
        )
    return CMakeConfigure(
        cmake_file=cmake_file,
        build_directory=build_directory,
        compile_commands=compile_commands,
        stdout=completed.stdout,
        stderr=completed.stderr,
        temporary_build=temporary,
    )
