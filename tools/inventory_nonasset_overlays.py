#!/usr/bin/env python3
"""Add a bounded inventory of package operation folders to an existing catalog.

The scanner only descends into recognized underscore operation directories
(`_append`, `_merge`, etc.). For each mount candidate it enumerates at most
the mount root and its direct children, plus package roots already named in
the input inventory. It does not walk or open package asset trees. ZIP sources
are inspected through their central directory only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


OVERLAY_DIRECTORY = re.compile(r"^_[A-Za-z0-9][A-Za-z0-9_-]*$")
MAX_MOUNT_CANDIDATES = 1000
MAX_OVERLAY_FILES = 50000
MAX_OVERLAY_DEPTH = 32
MAX_ARCHIVE_MEMBERS = 250000


def _is_real_directory(path: Path) -> bool:
	try:
		return path.is_dir() and not path.is_symlink()
	except OSError:
		return False


def _sorted_child_directories(path: Path) -> list[Path]:
	if not _is_real_directory(path):
		return []
	try:
		with os.scandir(path) as scan:
			return [
				Path(entry.path)
				for entry in sorted(scan, key=lambda item: item.name.casefold())
				if entry.is_dir(follow_symlinks=False)
			]
	except OSError:
		return []


def discover_mount_candidates(mount_root: Path) -> list[dict[str, Any]]:
	"""List directories at depth one or two and ZIP files at depth one only."""
	if not _is_real_directory(mount_root):
		raise ValueError(f"mount root is missing or not a real directory: {mount_root}")

	candidates: dict[str, dict[str, Any]] = {}
	try:
		with os.scandir(mount_root) as scan:
			entries = sorted(scan, key=lambda item: item.name.casefold())
	except OSError as error:
		raise ValueError(f"cannot enumerate mount root {mount_root}: {error}") from error

	for entry in entries:
		path = Path(entry.path)
		if entry.is_dir(follow_symlinks=False):
			candidates[str(path)] = {
				"path": str(path),
				"relativeToMountRoot": path.relative_to(mount_root).as_posix(),
				"depth": 1,
				"entryType": "directory",
			}
			for child in _sorted_child_directories(path):
				candidates[str(child)] = {
					"path": str(child),
					"relativeToMountRoot": child.relative_to(mount_root).as_posix(),
					"depth": 2,
					"entryType": "directory",
				}
		elif entry.is_file(follow_symlinks=False) and path.suffix.casefold() == ".zip":
			candidates[str(path)] = {
				"path": str(path),
				"relativeToMountRoot": path.relative_to(mount_root).as_posix(),
				"depth": 1,
				"entryType": "zip",
			}

	if len(candidates) > MAX_MOUNT_CANDIDATES:
		raise ValueError(
			f"mount candidate limit exceeded ({len(candidates)} > {MAX_MOUNT_CANDIDATES})"
		)
	return sorted(candidates.values(), key=lambda item: item["relativeToMountRoot"].casefold())


def _operation_directories(package_root: Path) -> list[tuple[Path, Path]]:
	"""Return (mod root, operation root) pairs using the standard mods layout."""
	mod_roots: dict[str, Path] = {str(package_root): package_root}
	mods_root = package_root / "mods"
	if package_root.name.casefold() == "mods":
		mods_root = package_root
	if _is_real_directory(mods_root):
		for child in _sorted_child_directories(mods_root):
			mod_roots[str(child)] = child

	pairs: list[tuple[Path, Path]] = []
	for mod_root in mod_roots.values():
		try:
			with os.scandir(mod_root) as scan:
				entries = sorted(scan, key=lambda item: item.name.casefold())
		except OSError:
			continue
		for entry in entries:
			if (
				OVERLAY_DIRECTORY.fullmatch(entry.name)
				and entry.is_dir(follow_symlinks=False)
			):
				pairs.append((mod_root, Path(entry.path)))
	return pairs


def _walk_operation_files(
	package_root: Path,
	mod_root: Path,
	operation_root: Path,
	*,
	file_budget: int,
) -> list[dict[str, Any]]:
	files: list[dict[str, Any]] = []
	stack: list[tuple[Path, int]] = [(operation_root, 0)]
	while stack:
		current, depth = stack.pop()
		if depth > MAX_OVERLAY_DEPTH:
			raise ValueError(f"overlay directory depth exceeded at {current}")
		try:
			with os.scandir(current) as scan:
				entries = sorted(scan, key=lambda item: item.name.casefold(), reverse=True)
		except OSError as error:
			raise ValueError(f"cannot enumerate overlay directory {current}: {error}") from error
		for entry in entries:
			if entry.is_symlink():
				# Record the path without following it or reading its target.
				mode = entry.stat(follow_symlinks=False).st_mode
				if stat.S_ISLNK(mode):
					files.append(
						{
							"path": Path(entry.path).relative_to(package_root).as_posix(),
							"modRoot": mod_root.relative_to(package_root).as_posix() or ".",
							"operation": operation_root.name,
							"entryType": "symlink",
							"bytes": None,
						}
					)
				if len(files) > file_budget:
					raise ValueError(
						f"overlay file limit exceeded ({MAX_OVERLAY_FILES}) under {package_root}"
					)
				continue
			if entry.is_dir(follow_symlinks=False):
				if depth == MAX_OVERLAY_DEPTH:
					raise ValueError(f"overlay directory depth exceeded at {entry.path}")
				stack.append((Path(entry.path), depth + 1))
				continue
			if not entry.is_file(follow_symlinks=False):
				continue
			info = entry.stat(follow_symlinks=False)
			files.append(
				{
					"path": Path(entry.path).relative_to(package_root).as_posix(),
					"modRoot": mod_root.relative_to(package_root).as_posix() or ".",
					"operation": operation_root.name,
					"entryType": "file",
					"bytes": info.st_size,
				}
			)
			if len(files) > file_budget:
				raise ValueError(
					f"overlay file limit exceeded ({MAX_OVERLAY_FILES}) under {package_root}"
				)
	return files


def scan_directory_overlays(package_root: Path) -> list[dict[str, Any]]:
	"""Enumerate operation-folder paths; only operation folders are traversed."""
	if not _is_real_directory(package_root):
		return []
	results: list[dict[str, Any]] = []
	for mod_root, operation_root in _operation_directories(package_root):
		remaining = MAX_OVERLAY_FILES - len(results)
		if remaining < 0:
			raise ValueError(f"overlay file limit exceeded ({MAX_OVERLAY_FILES})")
		results.extend(
			_walk_operation_files(
				package_root, mod_root, operation_root, file_budget=remaining
			)
		)
	results.sort(key=lambda item: item["path"].casefold())
	return results


def _archive_operation_paths(member_names: Iterable[str]) -> list[tuple[str, str, str]]:
	"""Return (member, operation, mod root) from shallow root or mods layouts."""
	files = [name.replace("\\", "/").lstrip("/") for name in member_names if name and not name.endswith("/")]
	operation_roots: dict[tuple[str, str], str] = {}
	for member in files:
		parts = member.split("/")
		for index, component in enumerate(parts[:-1]):
			if not OVERLAY_DIRECTORY.fullmatch(component):
				continue
			if index == 0:
				mod_root = "."
			elif index == 1:
				mod_root = parts[0]
			elif index >= 2 and parts[index - 2].casefold() == "mods":
				mod_root = "/".join(parts[:index])
			else:
				continue
			operation_path = "/".join(parts[: index + 1])
			operation_roots[(operation_path, component)] = mod_root

	results: list[tuple[str, str, str]] = []
	for member in files:
		parts = member.split("/")
		for index, component in enumerate(parts[:-1]):
			operation_path = "/".join(parts[: index + 1])
			key = (operation_path, component)
			if key in operation_roots:
				results.append((member, component, operation_roots[key]))
	return results


def scan_zip_overlays(archive_path: Path) -> list[dict[str, Any]]:
	"""List ZIP members in operation folders without extracting or opening data."""
	with zipfile.ZipFile(archive_path) as archive:
		infos = archive.infolist()
		if len(infos) > MAX_ARCHIVE_MEMBERS:
			raise ValueError(
				f"ZIP member limit exceeded ({len(infos)} > {MAX_ARCHIVE_MEMBERS}): {archive_path}"
			)
		member_sizes = {
			info.filename.replace("\\", "/"): info.file_size
			for info in infos
			if not info.is_dir()
		}
	results = []
	for member, operation, mod_root in _archive_operation_paths(member_sizes):
		results.append(
			{
				"path": member,
				"modRoot": mod_root,
				"operation": operation,
				"entryType": "archiveMember",
				"bytes": member_sizes[member],
			}
		)
		if len(results) > MAX_OVERLAY_FILES:
			raise ValueError(
				f"overlay file limit exceeded ({MAX_OVERLAY_FILES}) in ZIP {archive_path}"
			)
	results.sort(key=lambda item: item["path"].casefold())
	return results


def _catalog_paths(package: dict[str, Any]) -> set[str]:
	paths: set[str] = set()
	for item in package.get("sourceFileCatalog", []):
		path = item.get("path") if isinstance(item, dict) else item
		if isinstance(path, str):
			paths.add(path.replace("\\", "/"))
	return paths


def _root_is_available(path: Path) -> bool:
	if _is_real_directory(path):
		return True
	return path.is_file() and path.suffix.casefold() == ".zip" and zipfile.is_zipfile(path)


def _resolved_inventory_roots(
	packages: list[dict[str, Any]], mount_candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
	by_basename: dict[str, list[Path]] = defaultdict(list)
	for candidate in mount_candidates:
		candidate_path = Path(candidate["path"])
		if candidate["entryType"] == "directory":
			by_basename[candidate_path.name.casefold()].append(candidate_path)

	resolved: list[dict[str, Any]] = []
	for package in packages:
		declared = Path(package["sourceRoot"])
		root = declared if _root_is_available(declared) else None
		resolution = "exact" if root is not None else "unresolved"
		if root is None:
			matches = by_basename.get(declared.name.casefold(), [])
			if len(matches) == 1 and _root_is_available(matches[0]):
				root = matches[0]
				resolution = "uniqueBasenameWithinMountRoot"
		resolved.append(
			{
				"package": package,
				"declaredRoot": str(declared),
				"resolvedRoot": str(root) if root else None,
				"resolution": resolution,
				"available": root is not None,
			}
		)
	return resolved


def _scan_root(root: Path) -> list[dict[str, Any]]:
	if _root_is_available(root) and root.is_file():
		return scan_zip_overlays(root)
	return scan_directory_overlays(root)


def build_audit(inventory: dict[str, Any], mount_root: Path) -> dict[str, Any]:
	packages = inventory.get("packages")
	if not isinstance(packages, list):
		raise ValueError("inventory must contain a packages array")
	candidates = discover_mount_candidates(mount_root)
	resolved = _resolved_inventory_roots(packages, candidates)

	# Scan each candidate root once, then add inventory roots deeper than the
	# shallow mount view. No path beneath an assets directory is traversed.
	roots: dict[str, Path] = {candidate["path"]: Path(candidate["path"]) for candidate in candidates}
	for item in resolved:
		if item["resolvedRoot"]:
			root = Path(item["resolvedRoot"])
			roots[str(root)] = root

	root_scans: dict[str, list[dict[str, Any]]] = {}
	for key, root in roots.items():
		root_scans[key] = _scan_root(root)

	package_audits: list[dict[str, Any]] = []
	matched_roots: set[str] = set()
	for item in resolved:
		package = item["package"]
		root_key = item["resolvedRoot"]
		files = root_scans.get(root_key, []) if root_key else []
		catalog = _catalog_paths(package)
		matched_roots.add(root_key) if root_key else None
		package_audits.append(
			{
				"group": package.get("group"),
				"name": package.get("name"),
				"engine": package.get("engine"),
				"sourceInventory": package.get("sourceInventory"),
				"declaredRoot": item["declaredRoot"],
				"resolvedRoot": item["resolvedRoot"],
				"rootResolution": item["resolution"],
				"available": item["available"],
				"overlayFileCount": len(files),
				"overlayCatalogEntries": files,
				"overlayPathsAlreadyInBaseCatalog": sum(
					1 for entry in files if entry["path"] in catalog
				),
				"overlayPathsNewToBaseCatalog": [
					entry["path"] for entry in files if entry["path"] not in catalog
				],
			}
		)

	shallow_roots = []
	for candidate in candidates:
		root_key = candidate["path"]
		files = root_scans.get(root_key, [])
		is_inventory_root = root_key in matched_roots
		shallow_roots.append(
			{
				**candidate,
				"matchesInventoryPackageRoot": is_inventory_root,
				"overlayFileCount": len(files),
				"overlayPaths": [entry["path"] for entry in files],
				"overlayCatalogEntries": files,
			}
		)

	unique_overlay_paths = {
		(item["resolvedRoot"], entry["path"])
		for item in package_audits
		for entry in item["overlayCatalogEntries"]
	}
	new_catalog_paths = sum(
		len(item["overlayPathsNewToBaseCatalog"]) for item in package_audits
	)
	return {
		"schema": "example-mods-nonasset-overlay-audit/v1",
		"generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
		"method": {
			"mountRoot": str(mount_root),
			"mountCandidateDepth": 2,
			"mountCandidatesEnumerated": len(candidates),
			"inventoryPackageRootsDeclared": len(packages),
			"inventoryPackageRootsResolved": sum(1 for item in resolved if item["available"]),
			"inventoryPackageRootsResolvedByUniqueBasename": sum(
				1 for item in resolved if item["resolution"] == "uniqueBasenameWithinMountRoot"
			),
			"operationDirectoryRule": "Direct underscore-prefixed operation directories under a package root or under its conventional mods/<mod> child; operation directory names must start with underscore then an alphanumeric character.",
			"boundedReadPolicy": "Only enumerated operation directories are descended. Non-operation package directories, including assets trees, are not traversed. File content is not read or hashed. ZIPs are inspected through their central directory without extraction.",
			"limits": {
				"mountCandidates": MAX_MOUNT_CANDIDATES,
				"overlayFilesPerRoot": MAX_OVERLAY_FILES,
				"operationDirectoryDepth": MAX_OVERLAY_DEPTH,
				"zipMembers": MAX_ARCHIVE_MEMBERS,
			},
		},
		"summary": {
			"inventoryPackageCount": len(package_audits),
			"inventoryPackageRootsResolved": sum(1 for item in resolved if item["available"]),
			"inventoryPackageOverlayFileCount": sum(item["overlayFileCount"] for item in package_audits),
			"uniqueInventoryRootOverlayPaths": len(unique_overlay_paths),
			"newOverlayPathsNotInBaseCatalog": new_catalog_paths,
			"shallowMountCandidatesWithOverlays": sum(
				1 for item in shallow_roots if item["overlayFileCount"]
			),
			"unmatchedShallowMountCandidateCount": sum(
				1 for item in shallow_roots if not item["matchesInventoryPackageRoot"]
			),
			"unmatchedShallowCandidatesWithOverlays": sum(
				1
				for item in shallow_roots
				if not item["matchesInventoryPackageRoot"] and item["overlayFileCount"]
			),
		},
		"packages": package_audits,
		"shallowMountCandidates": shallow_roots,
		"shallowCandidateOverlayFileCount": sum(
			item["overlayFileCount"] for item in shallow_roots
		),
	}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("inventory", type=Path, help="existing package inventory JSON")
	parser.add_argument("--mount-root", type=Path, required=True, help="mounted example root")
	parser.add_argument(
		"--output",
		type=Path,
		help="output JSON path (defaults to updating the input inventory)",
	)
	args = parser.parse_args()
	output = args.output or args.inventory
	try:
		inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
		audit = build_audit(inventory, args.mount_root)
		inventory["nonAssetOverlayAudit"] = audit
		output.parent.mkdir(parents=True, exist_ok=True)
		output.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
		parser.error(str(error))
	print(json.dumps(audit["summary"], indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
