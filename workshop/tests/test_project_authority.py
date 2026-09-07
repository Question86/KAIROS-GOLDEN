from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from runtime_sync_workshop.corpus import cmake_membership, header_closure
from runtime_sync_workshop.util import set_source_prefix


class ProjectAuthorityTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_source_prefix("")

    def test_cmake_membership_ignores_comments_and_keeps_quoted_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cmake = root / "authority.cmake"
            cmake.write_text(
                "set(KAIROS_TRANSLATION_UNITS\n"
                '  "src/space name.cpp"\n'
                "  # src/commented.cpp\n"
                ")\n",
                encoding="utf-8",
            )
            config = SimpleNamespace(
                cmake_file=cmake,
                cmake_source_sets=("KAIROS_TRANSLATION_UNITS",),
                cmake_extra_sources=(),
                raw={"source_authority": {"translation_unit_extensions": ["cpp"]}},
            )
            set_source_prefix("")
            self.assertEqual(cmake_membership(config), ["src/space name.cpp"])

    def test_include_closure_uses_compiler_include_roots_and_angle_includes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "include").mkdir()
            (root / "src" / "main.cpp").write_text("#include <api.hpp>\n", encoding="utf-8")
            (root / "include" / "api.hpp").write_text("#pragma once\n", encoding="utf-8")
            config = SimpleNamespace(
                codebase_root=root,
                runtime_root=root,
                include_roots=(root / "include",),
                header_extensions=frozenset({".h", ".hpp"}),
                raw={},
            )
            set_source_prefix("")
            headers, issues = header_closure(config, ["src/main.cpp"])
            self.assertEqual(headers, {"include/api.hpp"})
            self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
