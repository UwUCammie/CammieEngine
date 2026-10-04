#!/usr/bin/env python3
"""Create a clean, downloadable Windows x64 runtime ZIP and SHA-256 file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "CammieEngine-windows-x64"
DEFAULT_RELEASE_TAG = "v0.0.12"
BUNDLED_RESULTS_ROOT = ("assets", "imported_mods", "bundled-vslice-results")
# Keep this list in sync with ImportIO.isRegistry. These tracked registries are
# mutable in a developer runtime, so releases must source their bytes from HEAD.
SHARED_REGISTRY_PATHS = frozenset(path.casefold() for path in (
    "assets/data/freeplaySongJson.jsonc",
    "assets/data/freeplaySongJson.json",
    "assets/images/freeplaySongJson.jsonc",
    "assets/images/freeplaySongJson.json",
    "assets/data/storySonglist.json",
    "assets/data/codenameMods.json",
    "assets/imported_mods/compatOverlays.json",
    "assets/imported_mods/globalResultsProvider.json",
    "assets/images/custom_chars/custom_chars.jsonc",
    "assets/images/custom_chars/icon_only_chars.json",
    "assets/images/custom_stages/custom_stages.json",
    "assets/images/custom_cutscenes/cutscenes.json",
    "assets/images/custom_difficulties/difficulties.json",
    "assets/images/custom_ui/ui_packs/ui.json",
))
REQUIRED_RUNTIME_PATHS = (
    "Funkin.exe",
    "CammieUpdateHelper.exe",
    "lime.ndll",
    "libvlc.dll",
    "libvlccore.dll",
    "plugins/plugins.dat",
    "manifest/libvlc.json",
    "assets",
    "assets/data",
    "tools/astcenc.exe",
    "tools/astcenc-LICENSE.txt",
    "assets/imported_mods/bundled-vslice-results/pack.json",
    "assets/imported_mods/bundled-vslice-results/scripts/results.lua",
)
DOCS = (
    ("LICENSE", "LICENSE"),
    ("NOTICE", "NOTICE"),
    ("CHANGELOG.md", "docs/CHANGELOG.md"),
    ("USER-README.txt", "docs/USER-README.txt"),
    ("updateLog.txt", "docs/updateLog.txt"),
    ("README.md", "docs/BUILD-README.md"),
    ("tools/licenses/CodenameEngine-Dev-LICENSE.txt", "licenses/CodenameEngine-Dev-LICENSE.txt"),
    ("tools/licenses/astcenc-LICENSE.txt", "licenses/astcenc-LICENSE.txt"),
)
REQUIRED_DOCS = (
    "LICENSE",
    "NOTICE",
    "updateLog.txt",
    "tools/licenses/astcenc-LICENSE.txt",
    "tools/licenses/CodenameEngine-Dev-LICENSE.txt",
)
EXCLUDED_DIRECTORY_NAMES = {
    "imported_mods",
    "imported-mods",
    "local_imports",
    "local-imports",
}
STANDALONE_USER_STATE_ROOTS = {"import-cache"}
PACKAGED_CONTENT_ROOTS = {"assets", "mods", "templates", "do not readme.txt"}
START_HERE = """CammieEngine — Windows x64

1. Extract this ZIP to a writable folder.
2. Run Funkin.exe from the extracted folder.

The game includes its runtime libraries, update helper, and bundled assets. It does not need
Haxe, Neko, Visual Studio, or a separate installer. The optional ASTC texture
decoder and its license are in tools/.

Settings are created for this copy of the game on first launch. Keep the game
folder writable so saves and settings can be stored beside the executable.

See LICENSE, NOTICE, docs/, and licenses/ for project and bundled notices.
"""


def safe_tag(tag: str) -> str:
    """Return a filename-safe label without allowing path components."""
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", tag.strip()).strip(".-")
    if not label:
        raise ValueError("release tag must contain at least one filename-safe character")
    return label


def excluded_runtime_path(relative: Path) -> bool:
    parts = tuple(part.casefold() for part in relative.parts)
    # Opt-in runtime probes write logs/screenshots beside the executable.
    # They are development output, while authored media lives under assets/.
    if len(parts) == 1 and relative.suffix.casefold() in {".log", ".png"}:
        return True
    if parts and parts[0] in STANDALONE_USER_STATE_ROOTS:
        return True
    if "imported_mods" in parts and parts[:3] != BUNDLED_RESULTS_ROOT \
            and parts != BUNDLED_RESULTS_ROOT[:len(parts)]:
        return True
    if any(part in EXCLUDED_DIRECTORY_NAMES - {"imported_mods"} for part in parts):
        return True
    return parts[-3:] == ("assets", "data", "options.json")


def runtime_files(runtime: Path) -> list[tuple[Path, Path]]:
    """List regular files below the build output, skipping local state/imports."""
    result: list[tuple[Path, Path]] = []
    for directory, child_dirs, filenames in os.walk(runtime, followlinks=False):
        base = Path(directory)
        relative_base = base.relative_to(runtime)
        child_dirs[:] = sorted(
            name for name in child_dirs
            if not excluded_runtime_path(relative_base / name)
            and not (base / name).is_symlink()
        )
        for filename in sorted(filenames):
            source = base / filename
            relative = relative_base / filename
            if excluded_runtime_path(relative) or source.is_symlink():
                continue
            try:
                if not stat.S_ISREG(source.stat().st_mode):
                    continue
            except OSError as error:
                raise ValueError(f"could not inspect runtime file {source}: {error}") from error
            result.append((source, relative))
    return result


def regular_files(root: Path, label: str) -> dict[str, Path]:
    """Map regular files below root by relative POSIX path, ignoring symlinks."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} directory is missing or is not a real directory: {root}")

    result: dict[str, Path] = {}

    def raise_walk_error(error: OSError) -> None:
        raise error

    try:
        for directory, child_dirs, filenames in os.walk(
                root, followlinks=False, onerror=raise_walk_error):
            base = Path(directory)
            child_dirs[:] = sorted(
                name for name in child_dirs
                if not (base / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = base / filename
                if path.is_symlink():
                    continue
                try:
                    mode = path.stat(follow_symlinks=False).st_mode
                except OSError as error:
                    raise ValueError(f"could not inspect {label} file {path}: {error}") from error
                if not stat.S_ISREG(mode):
                    continue
                result[path.relative_to(root).as_posix()] = path
    except OSError as error:
        raise ValueError(f"could not enumerate {label} files under {root}: {error}") from error
    return result


def git_output(repository: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"")
        raise ValueError(f"could not read tracked release sources from Git: {detail.decode(errors='replace')}") from error
    return result.stdout


def tracked_runtime_content(repository: Path) -> dict[str, str]:
    """Map built content paths to committed source files named by Project.xml."""
    tracked = git_output(repository, "ls-files", "-z").decode("utf-8", errors="strict").split("\0")
    result: dict[str, str] = {}
    for source in tracked:
        if not source:
            continue
        if source.startswith("assets/"):
            target = source
        elif source.startswith("example_mods/"):
            target = "mods/" + source[len("example_mods/"):]
        elif source.startswith("TempFiles/"):
            target = "Templates/" + source[len("TempFiles/"):]
        elif source == "art/readme.txt":
            target = "do NOT readme.txt"
        else:
            continue
        if ("imported_mods" in source.casefold()
                and not source.casefold().startswith("assets/imported_mods/bundled-vslice-results/")) \
                or "local_imports" in source.casefold():
            continue
        result[target.casefold()] = source
    return result


def committed_shared_registries(repository: Path) -> dict[str, str]:
    """Map known mutable shared registries to their exact committed source paths."""
    tracked = git_output(repository, "ls-tree", "-r", "--name-only", "-z", "HEAD")
    result: dict[str, str] = {}
    for source in tracked.decode("utf-8", errors="strict").split("\0"):
        if not source:
            continue
        key = source.casefold()
        if key not in SHARED_REGISTRY_PATHS:
            continue
        previous = result.get(key)
        if previous is not None and previous != source:
            raise ValueError(f"case-colliding committed shared registries: {previous} and {source}")
        result[key] = source
    return result


def committed_file(repository: Path, relative: str) -> bytes:
    """Read only the committed source file, never a runtime/user copy."""
    return git_output(repository, "show", f"HEAD:{relative}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_package(runtime_dir: Path, output_dir: Path, tag: str, repo_root: Path = ROOT) -> tuple[Path, Path]:
    label = safe_tag(tag)
    runtime = runtime_dir.resolve(strict=True)
    repository = repo_root.resolve(strict=True)
    if not runtime.is_dir():
        raise ValueError(f"runtime path is not a directory: {runtime}")
    for relative in REQUIRED_RUNTIME_PATHS:
        candidate = runtime / relative
        if relative in {"assets", "assets/data"}:
            valid = candidate.is_dir()
        else:
            valid = candidate.is_file()
        if not valid:
            raise ValueError(f"required Windows runtime file or directory is missing: {candidate.as_posix()}")
    for relative in REQUIRED_DOCS:
        if not (repository / relative).is_file():
            raise ValueError(f"required release notice is missing: {repository / relative}")

    tracked_content = tracked_runtime_content(repository)
    shared_registries = committed_shared_registries(repository)
    for target, original in tracked_content.items():
        if target.startswith(('assets/songs/', 'assets/music/')):
            source = repository / original
            built = runtime / original
            if not built.is_file() or built.stat().st_size != source.stat().st_size:
                raise ValueError(f'bundled audio is missing or incomplete in runtime: {original}')
    seed = committed_file(repository, "assets/data/options.json")
    try:
        seed_options = json.loads(seed)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("committed assets/data/options.json is not valid JSON") from error
    if not isinstance(seed_options, dict):
        raise ValueError("committed assets/data/options.json must contain a JSON object")

    files = runtime_files(runtime)
    bundled_results_source = regular_files(
        repository.joinpath(*BUNDLED_RESULTS_ROOT), "bundled results source"
    )
    bundled_results_runtime: dict[str, Path] = {}
    for runtime_file, relative in files:
        if tuple(part.casefold() for part in relative.parts[:3]) == BUNDLED_RESULTS_ROOT:
            name = PurePosixPath(*relative.parts[3:]).as_posix()
            bundled_results_runtime[name] = runtime_file

    missing_results = sorted(bundled_results_source.keys() - bundled_results_runtime.keys())
    extra_results = sorted(bundled_results_runtime.keys() - bundled_results_source.keys())
    if missing_results or extra_results:
        details = []
        if missing_results:
            details.append("missing runtime files: " + ", ".join(missing_results))
        if extra_results:
            details.append("unexpected runtime files: " + ", ".join(extra_results))
        raise ValueError("bundled results files do not match source (" + "; ".join(details) + ")")

    allowed_runtime_files: list[tuple[Path, Path]] = []
    skipped_non_source_content = 0
    for source, relative in files:
        if tuple(part.casefold() for part in relative.parts[:3]) == BUNDLED_RESULTS_ROOT:
            original = repository / relative
            if not original.is_file() or original.is_symlink() or sha256(original) != sha256(source):
                raise ValueError(f"bundled results asset differs from its release source: {relative}")
            allowed_runtime_files.append((source, relative))
            continue
        if relative.parts and relative.parts[0].casefold() in PACKAGED_CONTENT_ROOTS:
            if relative.as_posix().casefold() not in tracked_content:
                skipped_non_source_content += 1
                continue
        allowed_runtime_files.append((source, relative))

    # Linux builds can contain case-only hardlink mirrors for song audio. Windows
    # resolves those names to the same file, while the updater rejects duplicate
    # case-insensitive paths. Collapse identical mirrors and reject ambiguous ones.
    unique_files: dict[str, tuple[Path, Path]] = {}
    for source, relative in allowed_runtime_files:
        key = relative.as_posix().casefold()
        prior = unique_files.get(key)
        if prior is not None:
            if source.stat().st_size != prior[0].stat().st_size or sha256(source) != sha256(prior[0]):
                raise ValueError(f"conflicting Windows paths: {prior[1]} and {relative}")
            continue
        unique_files[key] = (source, relative)

    # Include each tracked shared registry even when its runtime path was
    # excluded with imported_mods, and use its committed spelling in the ZIP.
    for key, original in shared_registries.items():
        relative = Path(*PurePosixPath(original).parts)
        unique_files[key] = (repository / original, relative)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"CammieEngine-{label}-windows-x64.zip"
    checksum_path = output_dir / "SHA256SUMS.txt"
    fd, temporary_name = tempfile.mkstemp(prefix=".windows-x64-", suffix=".zip", dir=output_dir)
    os.close(fd)
    temporary_archive = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            archive_names: set[str] = set()
            for source, relative in unique_files.values():
                if relative.as_posix().casefold() in {"release_tag", "updatelog.txt"}:
                    continue
                archive_name = str(PurePosixPath(ARCHIVE_ROOT, *relative.parts))
                committed_registry = shared_registries.get(relative.as_posix().casefold())
                if committed_registry is None:
                    archive.write(source, archive_name)
                else:
                    archive.writestr(archive_name, committed_file(repository, committed_registry))
                archive_names.add(archive_name.casefold())

            release_log_name = f"{ARCHIVE_ROOT}/updateLog.txt"
            archive.write(repository / "updateLog.txt", release_log_name)
            archive_names.add(release_log_name.casefold())

            release_tag_name = f"{ARCHIVE_ROOT}/RELEASE_TAG"
            archive.writestr(release_tag_name, label + "\n")
            archive_names.add(release_tag_name.casefold())

            options_name = f"{ARCHIVE_ROOT}/assets/data/options.json"
            archive.writestr(options_name, seed)
            archive_names.add(options_name.casefold())

            start_name = f"{ARCHIVE_ROOT}/START-HERE.txt"
            if start_name.casefold() not in archive_names:
                start_info = zipfile.ZipInfo(start_name)
                start_info.compress_type = zipfile.ZIP_DEFLATED
                start_info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(start_info, START_HERE)
                archive_names.add(start_name.casefold())

            for source_relative, archive_relative in DOCS:
                source = repository / source_relative
                if not source.is_file():
                    continue
                archive_name = str(PurePosixPath(ARCHIVE_ROOT, archive_relative))
                if archive_name.casefold() not in archive_names:
                    archive.write(source, archive_name)
                    archive_names.add(archive_name.casefold())

        # Enforce the helper's Windows path rule before publishing a ZIP.
        with zipfile.ZipFile(temporary_archive) as check:
            seen: set[str] = set()
            for name in check.namelist():
                key = name.removeprefix(f"{ARCHIVE_ROOT}/").rstrip("/").casefold()
                if key in seen:
                    raise ValueError(f"duplicate Windows path in release ZIP: {name}")
                seen.add(key)

        os.replace(temporary_archive, archive_path)
    finally:
        temporary_archive.unlink(missing_ok=True)

    checksum_path.write_text(f"{sha256(archive_path)}  {archive_path.name}\n", encoding="ascii")
    print(f"Packaged Windows x64 runtime: {archive_path} ({archive_path.stat().st_size} bytes)")
    if skipped_non_source_content:
        print(f"Excluded {skipped_non_source_content} runtime content files absent from tracked source")
    print(f"SHA-256: {checksum_path}")
    return archive_path, checksum_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True, help="Lime Windows runtime bin directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tag", default=DEFAULT_RELEASE_TAG,
                        help=f"release tag or CI label used in the archive name (default: {DEFAULT_RELEASE_TAG})")
    parser.add_argument("--repo-root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        make_package(args.runtime, args.output_dir, args.tag, args.repo_root)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"[windows-package] {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
