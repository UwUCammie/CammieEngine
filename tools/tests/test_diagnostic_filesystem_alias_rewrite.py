"""Keep the mounted diagnostic's FileSystem shim rewrite narrowly scoped."""

import unittest

from tools.diagnose_example_auto_import import rewrite_diagnostic_filesystem_calls


class DiagnosticFileSystemAliasRewriteTest(unittest.TestCase):
    def test_plain_import_alias_is_rewritten_but_qualified_aliases_are_preserved(self):
        source = (
            "FileSystem.isDirectory(a); "
            "ImportFileSystem.isDirectory(b); "
            "RawFileSystem.isDirectory(c); "
            "sys.FileSystem.isDirectory(d);"
        )

        rewritten = rewrite_diagnostic_filesystem_calls(source)

        self.assertEqual(
            rewritten,
            "DiagnosticFileSystem.isDirectory(a); "
            "ImportFileSystem.isDirectory(b); "
            "RawFileSystem.isDirectory(c); "
            "sys.FileSystem.isDirectory(d);",
        )


if __name__ == "__main__":
    unittest.main()
