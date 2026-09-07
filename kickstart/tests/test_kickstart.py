from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kickstart.binding import initialize_project
from kickstart.errors import KickstartError
from kickstart.survey import survey_compile_commands


class KickstartSurveyTests(unittest.TestCase):
    def test_duplicate_compile_records_coalesce_and_include_roots_are_retained(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "main.cpp"
            include = root / "include"
            source.parent.mkdir()
            include.mkdir()
            source.write_text('#include "api.hpp"\nint main() { return 0; }\n', encoding="utf-8")
            (include / "api.hpp").write_text("#pragma once\n", encoding="utf-8")
            build = root / "build"
            build.mkdir()
            compile_commands = build / "compile_commands.json"
            compile_commands.write_text(
                json.dumps([
                    {"directory": str(build), "file": str(source), "arguments": ["c++", "-I", str(include), "-c", str(source)]},
                    {"directory": str(build), "file": str(source), "arguments": ["c++", "-I" + str(include), "-c", str(source)]},
                ]),
                encoding="utf-8",
            )
            survey = survey_compile_commands(compile_commands, root)
            self.assertEqual([unit.relative_path for unit in survey.units], ["src/main.cpp"])
            self.assertEqual(len(survey.units[0].commands), 2)
            self.assertEqual([path.relative_to(root).as_posix() for path in survey.include_roots], ["include"])

    def test_windows_command_string_preserves_quoted_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kairos project ") as temporary:
            root = Path(temporary)
            source = root / "src" / "main.cpp"
            include = root / "include files"
            source.parent.mkdir()
            include.mkdir()
            source.write_text('#include "api.hpp"\n', encoding="utf-8")
            (include / "api.hpp").write_text("#pragma once\n", encoding="utf-8")
            build = root / "build"
            build.mkdir()
            compile_commands = build / "compile_commands.json"
            command = f'c++ -I"{include}" -c "{source}"'
            compile_commands.write_text(
                json.dumps([{"directory": str(build), "file": str(source), "command": command}]),
                encoding="utf-8",
            )
            survey = survey_compile_commands(compile_commands, root)
            self.assertEqual(survey.units[0].relative_path, "src/main.cpp")
            self.assertEqual([path.relative_to(root).as_posix() for path in survey.include_roots], ["include files"])

    def test_source_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            outside = Path(temporary) / "outside.cpp"
            outside.write_text("int x;\n", encoding="utf-8")
            build = root / "build"
            build.mkdir()
            compile_commands = build / "compile_commands.json"
            compile_commands.write_text(
                json.dumps([{"directory": str(build), "file": str(outside), "arguments": ["c++", "-c", str(outside)]}]),
                encoding="utf-8",
            )
            with self.assertRaises(KickstartError) as raised:
                survey_compile_commands(compile_commands, root)
            self.assertEqual(raised.exception.code, "SOURCE_OUTSIDE_PROJECT")


class KickstartIntegrationTests(unittest.TestCase):
    def test_compiler_backed_project_is_promoted_and_workshop_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            (project / "src").mkdir(parents=True)
            (project / "include").mkdir()
            (project / "src" / "main.cpp").write_text('#include "api.hpp"\nint main() { return api(); }\n', encoding="utf-8")
            (project / "include" / "api.hpp").write_text("#pragma once\ninline int api() { return 0; }\n", encoding="utf-8")
            build = project / "build"
            build.mkdir()
            compile_commands = build / "compile_commands.json"
            compile_commands.write_text(
                json.dumps([{"directory": str(build), "file": str(project / "src" / "main.cpp"), "arguments": ["c++", "-I", str(project / "include"), "-c", str(project / "src" / "main.cpp")]}]),
                encoding="utf-8",
            )
            result = initialize_project(project_root=project, workspace=root / "workspace", compile_commands=compile_commands)
            self.assertTrue(result["verified"])
            self.assertTrue(result["corpus"]["verified"])
            self.assertEqual(result["corpus"]["counts"]["issues"], 0)
            self.assertEqual(result["health"]["verdict"], "PASS")
            self.assertEqual(result["translation_units"], 1)
            self.assertEqual(result["include_headers"], 1)
            self.assertTrue((root / "workspace" / ".kairos" / "project-intake.json").is_file())

    def test_root_level_translation_unit_is_represented_without_invented_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            source = project / "main.cpp"
            source.write_text("int main() { return 0; }\n", encoding="utf-8")
            build = project / "build"
            build.mkdir()
            compile_commands = build / "compile_commands.json"
            compile_commands.write_text(
                json.dumps([{"directory": str(build), "file": str(source), "arguments": ["c++", "-c", str(source)]}]),
                encoding="utf-8",
            )
            result = initialize_project(project_root=project, workspace=root / "workspace", compile_commands=compile_commands)
            self.assertTrue(result["verified"])
            self.assertEqual(result["corpus"]["authority"]["translation_units"], ["main.cpp"])

    @unittest.skipUnless(shutil.which("cmake"), "cmake is not installed")
    def test_cmake_input_uses_compiler_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            (project / "src").mkdir(parents=True)
            (project / "src" / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
            (project / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.15)\nproject(kickstart_test LANGUAGES CXX)\n"
                "set(CMAKE_CXX_STANDARD 11)\nadd_executable(kickstart_test src/main.cpp)\n",
                encoding="utf-8",
            )
            result = initialize_project(project_root=project, workspace=root / "workspace", cmake_file=project / "CMakeLists.txt")
            self.assertTrue(result["verified"])
            self.assertEqual(result["corpus"]["counts"]["issues"], 0)
            self.assertTrue(result["manifest"].endswith("project-intake.json"))


if __name__ == "__main__":
    unittest.main()
