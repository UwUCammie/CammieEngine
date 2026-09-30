import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.inventory_nonasset_overlays import (
	build_audit,
	scan_directory_overlays,
	scan_zip_overlays,
)


class NonAssetOverlayInventoryTests(unittest.TestCase):
	def test_directory_scan_includes_root_and_mod_overlays_without_walking_assets(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			root = Path(temp_dir) / "package"
			(root / "_merge/data").mkdir(parents=True)
			(root / "mods/intro/_append/data").mkdir(parents=True)
			(root / "mods/another/_replace/images").mkdir(parents=True)
			(root / "assets/images").mkdir(parents=True)
			(root / "_merge/data/config.json").write_text("{}", encoding="utf-8")
			(root / "mods/intro/_append/data/intro.txt").write_text("+line", encoding="utf-8")
			(root / "mods/another/_replace/images/menu.png").write_bytes(b"image")
			(root / "assets/images/not-an-overlay.png").write_bytes(b"asset")

			entries = scan_directory_overlays(root)

		self.assertEqual(
			[entry["path"] for entry in entries],
			[
				"_merge/data/config.json",
				"mods/another/_replace/images/menu.png",
				"mods/intro/_append/data/intro.txt",
			],
		)
		self.assertEqual([entry["bytes"] for entry in entries], [2, 5, 5])
		self.assertTrue(all("assets/" not in entry["path"] for entry in entries))

	def test_mod_container_root_and_zip_central_directory_are_supported(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			root = Path(temp_dir) / "mods"
			(root / "alpha/_append/data").mkdir(parents=True)
			(root / "alpha/_append/data/intro.txt").write_text("tail", encoding="utf-8")
			self.assertEqual(
				[entry["path"] for entry in scan_directory_overlays(root)],
				["alpha/_append/data/intro.txt"],
			)

			archive_path = Path(temp_dir) / "package.zip"
			with zipfile.ZipFile(archive_path, "w") as archive:
				archive.writestr("wrapper/mods/intro/_append/data/introText.txt", "tail")
				archive.writestr("wrapper/_replace/data/menu.bin", b"menu")
				archive.writestr("wrapper/assets/images/large.png", b"asset")

			entries = scan_zip_overlays(archive_path)

		self.assertEqual(
			[entry["path"] for entry in entries],
			[
				"wrapper/_replace/data/menu.bin",
				"wrapper/mods/intro/_append/data/introText.txt",
			],
		)
		self.assertTrue(all(entry["entryType"] == "archiveMember" for entry in entries))

	def test_audit_resolves_relocated_roots_and_lists_unmatched_mount_entries(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			mount = Path(temp_dir) / "examples"
			current = mount / "group" / "relocated"
			(current / "mods/alpha/_append/data").mkdir(parents=True)
			(current / "mods/alpha/_append/data/intro.txt").write_text("tail", encoding="utf-8")
			unknown = mount / "unlisted-project"
			(unknown / "source_code").mkdir(parents=True)
			(mount / "unlisted-project-marker.txt").write_text("root", encoding="utf-8")

			inventory = {
				"packages": [
					{
						"group": "fixture",
						"name": "fixture package",
						"engine": "fixture",
						"sourceRoot": str(Path(temp_dir) / "old" / "relocated"),
						"sourceInventory": "fixture.json",
						"sourceFileCatalog": [],
					}
				]
			}

			audit = build_audit(inventory, mount)

		self.assertEqual(audit["packages"][0]["rootResolution"], "uniqueBasenameWithinMountRoot")
		self.assertEqual(audit["packages"][0]["resolvedRoot"], str(current))
		self.assertEqual(
			audit["packages"][0]["overlayPathsNewToBaseCatalog"],
			["mods/alpha/_append/data/intro.txt"],
		)
		candidate_paths = {
			candidate["relativeToMountRoot"] for candidate in audit["shallowMountCandidates"]
		}
		self.assertIn("unlisted-project", candidate_paths)
		self.assertIn("unlisted-project/source_code", candidate_paths)
		self.assertEqual(audit["summary"]["inventoryPackageOverlayFileCount"], 1)


if __name__ == "__main__":
	unittest.main()
