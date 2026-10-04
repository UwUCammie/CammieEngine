"""Keep the exact Away3D haxelib pin verifiable without system Git."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import install_codename_3d


class InstallCodename3DTest(unittest.TestCase):
    revision = "ca30a80ca3c56f266fb3cd067fdeb43b0bb9784d"

    def test_detached_head_is_read_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder) / "away3d"
            git = library / ".git"
            git.mkdir(parents=True)
            (git / "HEAD").write_text(self.revision + "\n", encoding="ascii")
            with patch.object(install_codename_3d.shutil, "which", return_value=None):
                self.assertEqual(install_codename_3d.checkout_revision(library), self.revision)

    def test_branch_head_resolves_loose_ref_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            git = Path(folder) / "away3d" / ".git"
            (git / "refs/heads").mkdir(parents=True)
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "refs/heads/main").write_text(self.revision + "\n", encoding="ascii")
            with patch.object(install_codename_3d.shutil, "which", return_value=None):
                self.assertEqual(install_codename_3d.checkout_revision(git.parent), self.revision)

    def test_branch_head_resolves_packed_ref_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            git = Path(folder) / "away3d" / ".git"
            git.mkdir(parents=True)
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled\n"
                + self.revision + " refs/heads/main\n",
                encoding="ascii",
            )
            with patch.object(install_codename_3d.shutil, "which", return_value=None):
                self.assertEqual(install_codename_3d.checkout_revision(git.parent), self.revision)

    def test_worktree_gitfile_reads_common_packed_ref_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library = root / "worktree/lib"
            git = root / "metadata/worktrees/lib"
            library.mkdir(parents=True)
            git.mkdir(parents=True)
            (library / ".git").write_text("gitdir: ../../metadata/worktrees/lib\n", encoding="utf-8")
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "commondir").write_text("../..\n", encoding="ascii")
            common = root / "metadata"
            (common / "packed-refs").write_text(
                self.revision + " refs/heads/main\n", encoding="ascii"
            )
            with patch.object(install_codename_3d.shutil, "which", return_value=None):
                self.assertEqual(install_codename_3d.checkout_revision(library), self.revision)

    def test_unverifiable_checkout_without_git_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder) / "away3d"
            library.mkdir()
            with (
                patch.object(install_codename_3d, "selected_library_path", return_value=library),
                patch.object(install_codename_3d, "checkout_revision", return_value=None),
                patch.object(install_codename_3d, "package_version", return_value=install_codename_3d.EXPECTED_VERSION),
                patch.object(install_codename_3d.shutil, "which", return_value=None),
            ):
                with self.assertRaisesRegex(RuntimeError, "Add Git to PATH"):
                    install_codename_3d.ensure_pinned("haxelib")


if __name__ == "__main__":
    unittest.main()
