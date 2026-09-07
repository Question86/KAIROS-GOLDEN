from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .binding import initialize_project
from .errors import KickstartError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kickstart",
        description="Bind a compiler-backed project into exact KAIROS Markdown and Workshop evidence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="discover, materialize and verify an initial project corpus")
    init.add_argument("--project-root", required=True, type=Path, help="project root containing the governed sources")
    init.add_argument("--workspace", required=True, type=Path, help="fresh or existing KAIROS project workspace")
    authority = init.add_mutually_exclusive_group(required=True)
    authority.add_argument("--compile-commands", type=Path, help="existing compiler-produced compile_commands.json")
    authority.add_argument("--cmake", type=Path, help="CMakeLists.txt; an isolated configure emits compile_commands.json")
    init.add_argument("--cmake-executable", default="cmake", help="CMake executable used with --cmake")
    init.add_argument("--build-directory", type=Path, help="optional retained CMake build directory")
    init.add_argument("--workspace-id", help="stable upper-case KAIROS workspace id for a fresh workspace")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command != "init":
        raise SystemExit(2)
    try:
        result = initialize_project(
            project_root=args.project_root,
            workspace=args.workspace,
            compile_commands=args.compile_commands,
            cmake_file=args.cmake,
            cmake_executable=args.cmake_executable,
            build_directory=args.build_directory,
            workspace_id=args.workspace_id,
        )
    except KickstartError as exc:
        print(json.dumps({"schema": "kairos-project-intake-error/v1", **exc.as_dict()}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))

