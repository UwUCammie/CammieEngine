"""Build and install a checksum-pinned uncapped Lime 8.3.2 native library.

The upstream 8.3.2 haxelib package does not contain the uncapped SDL loop. This
helper builds the two narrowly patched source files from the exact upstream tag
using the already selected haxelib toolchain, then atomically installs the
result into that selected package. It never changes haxelib's selection.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


LIME_REPOSITORY = "https://github.com/openfl/lime.git"
LIME_TAG = "8.3.2"
LIME_COMMIT = "d78d5be8a29de6ad649ffe4684ee435f76fe051b"
CACHE_SCHEMA = 1
PATCHER_RELATIVE_PATH = Path("tools/patch_lime_uncapped_frame_loop.py")
PATCHER_MODULE_NAME = "patch_lime_uncapped_frame_loop"
FINGERPRINT_ENV_VARS = (
    "HXCPP_MINGW_EXE",
    "HXCPP_MINGW",
    "HXCPP_AR",
    "HXCPP_RANLIB",
    "HXCPP_STRIP",
    "HXCPP_RC",
    "HXCPP_COMPILE_THREADS",
    "HXCPP_COMPILE_FLAGS",
    "HXCPP_LINK_FLAGS",
    "HXCPP_COMPILER_FLAGS",
    "HXCPP_CONFIG",
    "MINGW_ROOT",
    "LIME_COMPILER_FLAGS",
    "LIME_ARCH_FLAGS",
)


class LimeUncappedError(RuntimeError):
    """A precondition, source, build, or publication check failed."""


@dataclass(frozen=True)
class BuildTarget:
    platform: str
    arch: str
    output_folder: str
    hxcpp_flags: Tuple[str, ...]
    binary_format: str


@dataclass(frozen=True)
class HaxelibSelection:
    haxelib: Path
    library_root: Path
    lime_package: Path
    hxcpp_package: Path
    hxcpp_version: str


def build_target(platform: str, arch: str, env: Optional[Mapping[str, str]] = None) -> BuildTarget:
    """Map the supported desktop target to hxcpp's actual defines and folder."""
    env = env or os.environ
    platform = platform.lower()
    arch = arch.lower().replace("x86_64", "64").replace("amd64", "64")
    arch = arch.replace("x86", "32").replace("aarch64", "arm64")
    if platform not in ("windows", "linux", "mac"):
        raise LimeUncappedError("platform must be windows, linux, or mac")
    if arch not in ("32", "64", "arm64"):
        raise LimeUncappedError("arch must be 32, 64, or arm64")

    if platform == "windows":
        if arch == "arm64":
            # hxcpp 4.3.2's Windows builder explicitly disables this target.
            raise LimeUncappedError("hxcpp 4.3.2 does not support Windows arm64 builds")
        flags = ["-Dwindows", "-DHXCPP_M64" if arch == "64" else "-DHXCPP_M32"]
        if env.get("HXCPP_MINGW_EXE") or env.get("HXCPP_MINGW"):
            flags.append("-DHXCPP_MINGW")
        return BuildTarget(platform, arch, "Windows64" if arch == "64" else "Windows", tuple(flags), "pe")

    target_define = "-Dlinux" if platform == "linux" else "-Dmac"
    if arch == "arm64":
        flags = (target_define, "-DHXCPP_ARM64", "-DHXCPP_M64")
        folder = "Linux64" if platform == "linux" else "MacArm64"
    elif arch == "64":
        flags = (target_define, "-DHXCPP_M64")
        folder = "Linux64" if platform == "linux" else "Mac64"
    else:
        flags = (target_define, "-DHXCPP_M32")
        folder = "Linux" if platform == "linux" else "Mac"
    return BuildTarget(platform, arch, folder, tuple(flags), "elf" if platform == "linux" else "macho")


def build_command(haxelib: Path, target: BuildTarget) -> List[str]:
    return [str(haxelib), "run", "hxcpp", "Build.xml", *target.hxcpp_flags]


def _run(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            capture_output=capture_output,
            text=True,
            check=False,
        )
    except OSError as error:
        raise LimeUncappedError(f"could not run {command[0]}: {error}") from error


def _checked_run(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    description: str,
) -> subprocess.CompletedProcess:
    result = _run(command, cwd=cwd, env=env, capture_output=True)
    if result.returncode != 0:
        detail = (result.stdout or "") + (result.stderr or "")
        raise LimeUncappedError(f"{description} failed (exit {result.returncode}):\n{detail.strip()}")
    return result


def _norm_path(path: Path) -> str:
    try:
        value = str(path.expanduser().resolve())
    except OSError:
        value = os.path.abspath(str(path.expanduser()))
    value = os.path.normpath(value)
    return os.path.normcase(value)


def _find_haxelib(env: Mapping[str, str]) -> Path:
    haxe_path = env.get("HAXEPATH")
    if not haxe_path:
        raise LimeUncappedError("HAXEPATH is required; run the repository toolchain bootstrap first")
    folder = Path(haxe_path)
    candidates = (folder / "haxelib.exe", folder / "haxelib") if os.name == "nt" else (folder / "haxelib", folder / "haxelib.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise LimeUncappedError(f"haxelib executable was not found under HAXEPATH: {folder}")


def _library_path_lines(output: str) -> List[Path]:
    paths: List[Path] = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("-L "):
            candidate = line[3:].strip().strip('"')
            if candidate:
                paths.append(Path(candidate))
        elif line and not line.startswith("-"):
            candidate = Path(line.strip('"'))
            if candidate.exists():
                paths.append(candidate)
    return paths


def verify_haxelib_selection(
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., subprocess.CompletedProcess] = _run,
) -> HaxelibSelection:
    """Read-only validation that the current haxelib package is the pinned one."""
    env = dict(env or os.environ)
    configured_root = env.get("HAXELIB_PATH")
    if not configured_root:
        raise LimeUncappedError("HAXELIB_PATH is required; refusing to install outside the repository toolchain")
    library_root = Path(configured_root).resolve()
    haxelib = _find_haxelib(env)

    config = runner([str(haxelib), "config"], env=env, capture_output=True)
    if config.returncode != 0:
        raise LimeUncappedError(f"haxelib config failed: {(config.stderr or config.stdout or '').strip()}")
    selected_root = (config.stdout or "").strip().splitlines()
    if not selected_root or _norm_path(Path(selected_root[-1])) != _norm_path(library_root):
        raise LimeUncappedError(
            "haxelib config does not select HAXELIB_PATH; refusing to change the selected package "
            f"(config={selected_root[-1] if selected_root else '<empty>'}, env={library_root})"
        )

    def selected_package(name: str, wanted_version: str) -> Path:
        result = runner([str(haxelib), "path", name], env=env, capture_output=True)
        if result.returncode != 0:
            raise LimeUncappedError(f"haxelib path {name} failed: {(result.stderr or result.stdout or '').strip()}")
        output = result.stdout or ""
        if f"-D {name}={wanted_version}" not in output.splitlines():
            raise LimeUncappedError(f"selected {name} version is not {wanted_version}; refusing to build Lime")
        expected = library_root / name / wanted_version.replace(".", ",")
        package_candidates = _library_path_lines(output)
        if not any(_norm_path(path) == _norm_path(expected) or _norm_path(path).startswith(_norm_path(expected) + os.sep) for path in package_candidates):
            raise LimeUncappedError(f"haxelib path {name} does not resolve to repository package {expected}")
        if not expected.is_dir():
            raise LimeUncappedError(f"selected {name} package is missing: {expected}")
        return expected

    lime_package = selected_package("lime", LIME_TAG)
    hxcpp_package = selected_package("hxcpp", "4.3.2")
    return HaxelibSelection(haxelib, library_root, lime_package, hxcpp_package, "4.3.2")


def _git_command(repo_root: Path, env: Mapping[str, str], runner: Callable[..., subprocess.CompletedProcess], *args: str) -> str:
    git = shutil.which("git", path=env.get("PATH"))
    if not git:
        bundled = repo_root / ".tools" / "git" / "cmd" / ("git.exe" if os.name == "nt" else "git")
        if bundled.is_file():
            git = str(bundled)
    if not git:
        raise LimeUncappedError("Git is required to verify or bootstrap the pinned Lime 8.3.2 source")
    result = runner([git, *args], cwd=repo_root, env=env, capture_output=True)
    if result.returncode != 0:
        raise LimeUncappedError(f"Git command failed: {(result.stderr or result.stdout or '').strip()}")
    return result.stdout or ""


def _source_git(source: Path, repo_root: Path, env: Mapping[str, str], runner: Callable[..., subprocess.CompletedProcess], *args: str) -> str:
    git = shutil.which("git", path=env.get("PATH"))
    if not git:
        bundled = repo_root / ".tools" / "git" / "cmd" / ("git.exe" if os.name == "nt" else "git")
        if bundled.is_file():
            git = str(bundled)
    if not git:
        raise LimeUncappedError("Git is required to verify or bootstrap the pinned Lime 8.3.2 source")
    result = runner([git, "-C", str(source), *args], cwd=repo_root, env=env, capture_output=True)
    if result.returncode != 0:
        raise LimeUncappedError(f"Git command failed in cached Lime source: {(result.stderr or result.stdout or '').strip()}")
    return result.stdout or ""


def ensure_source_checkout(
    repo_root: Path,
    *,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., subprocess.CompletedProcess] = _run,
) -> Path:
    """Reuse a valid checkout or anonymously clone the exact tag and its gitlinks."""
    env = dict(env or os.environ)
    repo_root = repo_root.resolve()
    tools_dir = repo_root / ".tools"
    source = tools_dir / "lime-8.3.2-source"
    tools_dir.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        temp_source = tools_dir / f".lime-8.3.2-source-{os.getpid()}-{int(time.time() * 1000)}"
        if temp_source.exists():
            raise LimeUncappedError(f"refusing to reuse an existing temporary Lime clone path: {temp_source}")
        git = shutil.which("git", path=env.get("PATH"))
        if not git:
            bundled = tools_dir / "git" / "cmd" / ("git.exe" if os.name == "nt" else "git")
            if bundled.is_file():
                git = str(bundled)
        if not git:
            raise LimeUncappedError("Git is required to bootstrap the pinned Lime 8.3.2 source")
        clone_env = dict(env)
        clone_env["GIT_TERMINAL_PROMPT"] = "0"
        clone_env["GIT_CONFIG_NOSYSTEM"] = "1"
        command = [
            git,
            "-c", "credential.helper=",
            "-c", "credential.interactive=never",
            "clone", "--depth=1", "--single-branch", "--branch", LIME_TAG,
            "--recurse-submodules", "--shallow-submodules", LIME_REPOSITORY, str(temp_source),
        ]
        try:
            result = runner(command, cwd=repo_root, env=clone_env, capture_output=True)
            if result.returncode != 0:
                raise LimeUncappedError(
                    "anonymous Lime 8.3.2 source clone failed: "
                    f"{(result.stderr or result.stdout or '').strip()}"
                )
            actual = _source_git(temp_source, repo_root, clone_env, runner, "rev-parse", "HEAD").strip()
            if actual != LIME_COMMIT:
                raise LimeUncappedError(f"Lime tag {LIME_TAG} resolved to {actual}, expected {LIME_COMMIT}")
            _verify_submodules(temp_source, repo_root, clone_env, runner)
            os.replace(str(temp_source), str(source))
        finally:
            if temp_source.exists():
                resolved_tools = tools_dir.resolve()
                resolved_temp = temp_source.resolve()
                if (
                    temp_source.is_symlink()
                    or resolved_temp.parent != resolved_tools
                    or resolved_temp.name != temp_source.name
                ):
                    raise LimeUncappedError(
                        f"refusing to recursively remove temporary clone outside .tools: {resolved_temp}"
                    )
                shutil.rmtree(resolved_temp)
    _verify_source_checkout(source, repo_root, env, runner, patcher=None)
    return source


def _verify_submodules(
    source: Path,
    repo_root: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess],
) -> str:
    output = _source_git(source, repo_root, env, runner, "submodule", "status", "--recursive")
    for line in output.splitlines():
        if not line:
            continue
        if line[0] != " ":
            raise LimeUncappedError(f"Lime source has an uninitialized or modified pinned submodule: {line}")
    return output.strip()


def _load_patcher(repo_root: Path):
    patcher_path = repo_root / PATCHER_RELATIVE_PATH
    if not patcher_path.is_file():
        raise LimeUncappedError(f"Lime patcher is missing: {patcher_path}")
    spec = importlib.util.spec_from_file_location(PATCHER_MODULE_NAME, patcher_path)
    if spec is None or spec.loader is None:
        raise LimeUncappedError(f"could not load Lime patcher: {patcher_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_source_checkout(
    source: Path,
    repo_root: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess],
    patcher,
) -> Tuple[str, str]:
    if not (source / ".git").exists():
        raise LimeUncappedError(f"cached Lime source is not a Git checkout: {source}")
    actual = _source_git(source, repo_root, env, runner, "rev-parse", "HEAD").strip()
    if actual != LIME_COMMIT:
        raise LimeUncappedError(f"cached Lime checkout is {actual}, expected exact 8.3.2 commit {LIME_COMMIT}")
    submodules = _verify_submodules(source, repo_root, env, runner)
    if patcher is not None:
        patcher.patch_file(source)
        allowed = set(patcher.PATCHED_PATHS)
        expected_hashes = {
            patcher.PATCHED_PATHS[0]: patcher.PATCHED_SHA256,
            patcher.PATCHED_PATHS[1]: patcher.FONT_PATCHED_SHA256,
        }
        for relative, expected_hash in expected_hashes.items():
            actual_hash = _normalized_hash((source / relative).read_bytes())
            if actual_hash != expected_hash:
                raise LimeUncappedError(f"pinned Lime patch output differs at {relative}")
    else:
        allowed = set()
    status = _source_git(source, repo_root, env, runner, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none")
    if patcher is None:
        # This early call only checks an existing/bootstrap checkout's identity
        # and gitlinks. The patch and allow-list are verified immediately before
        # fingerprinting, after loading the repository-owned patcher.
        return submodules, status.strip()
    changed_paths = set()
    for line in status.splitlines():
        if len(line) < 4:
            raise LimeUncappedError(f"could not parse cached Lime Git status: {line!r}")
        changed_paths.add(line[3:])
    unexpected = changed_paths - allowed
    missing_patch = allowed - changed_paths if patcher is not None else set()
    if unexpected:
        raise LimeUncappedError(
            "cached Lime checkout has unexpected source modifications; refusing to build: "
            + ", ".join(sorted(unexpected))
        )
    if missing_patch:
        raise LimeUncappedError("Lime patch files are not recorded as modified: " + ", ".join(sorted(missing_patch)))
    return submodules, status.strip()


def _normalized_hash(source: bytes) -> str:
    return hashlib.sha256(source.replace(b"\r\n", b"\n")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_fingerprint(path: Path) -> str:
    """Capture hxcpp source/config inputs without reading the full compiler tree."""
    digest = hashlib.sha256()
    ignored_dirs = {".git", "obj", "out", "tmp", "temp", "__pycache__"}
    ignored_suffixes = {".o", ".obj", ".a", ".lib", ".dll", ".exe", ".so", ".dylib", ".ndll", ".pyc"}
    files: List[Path] = []
    for current, directories, names in os.walk(path):
        directories[:] = sorted(name for name in directories if name.lower() not in ignored_dirs)
        for name in names:
            candidate = Path(current) / name
            if candidate.suffix.lower() not in ignored_suffixes and candidate.is_file():
                files.append(candidate)
    for file in sorted(files, key=lambda item: item.relative_to(path).as_posix().lower()):
        relative = file.relative_to(path).as_posix().encode("utf-8", errors="surrogateescape")
        file_stat = file.stat()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(
            json.dumps(
                {
                    "size": file_stat.st_size,
                    "mtime_ns": getattr(file_stat, "st_mtime_ns", int(file_stat.st_mtime * 1_000_000_000)),
                    "ctime_ns": getattr(file_stat, "st_ctime_ns", int(file_stat.st_ctime * 1_000_000_000)),
                    "device": getattr(file_stat, "st_dev", 0),
                    "file_id": getattr(file_stat, "st_ino", 0),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
        )
    return digest.hexdigest()


def _resolve_tool(name: str, env: Mapping[str, str]) -> Optional[Path]:
    if not name:
        return None
    candidate = Path(name)
    if candidate.is_file():
        return candidate.resolve()
    resolved = shutil.which(name, path=env.get("PATH"))
    return Path(resolved).resolve() if resolved else None


def _tool_record(name: str, env: Mapping[str, str]) -> Dict[str, str]:
    path = _resolve_tool(name, env)
    if path is None:
        return {"name": name, "path": "<not-found>"}
    try:
        file_stat = path.stat()
        return {
            "name": name,
            "path": str(path),
            "size": str(file_stat.st_size),
            "mtime_ns": str(getattr(file_stat, "st_mtime_ns", int(file_stat.st_mtime * 1_000_000_000))),
            "ctime_ns": str(getattr(file_stat, "st_ctime_ns", int(file_stat.st_ctime * 1_000_000_000))),
            "device": str(getattr(file_stat, "st_dev", 0)),
            "file_id": str(getattr(file_stat, "st_ino", 0)),
        }
    except OSError as error:
        return {"name": name, "path": str(path), "error": str(error)}


def input_fingerprint(
    repo_root: Path,
    source: Path,
    selection: HaxelibSelection,
    target: BuildTarget,
    env: Mapping[str, str],
    submodule_status: str,
    source_status: str,
) -> str:
    patcher_path = repo_root / PATCHER_RELATIVE_PATH
    haxe_dir = Path(env["HAXEPATH"])
    haxe_binary = _resolve_tool(str(haxe_dir / ("haxe.exe" if os.name == "nt" else "haxe")), env)
    tools = []
    for variable in ("HXCPP_MINGW_EXE", "HXCPP_AR", "HXCPP_RANLIB", "HXCPP_STRIP", "HXCPP_RC"):
        if env.get(variable):
            tools.append(_tool_record(env[variable], env))
    for fallback in (("cl.exe", "clang++.exe", "g++.exe") if os.name == "nt" else ("clang++", "g++", "cc")):
        found = _resolve_tool(fallback, env)
        if found:
            tools.append(_tool_record(str(found), env))
            break
    patch_hashes = {}
    patcher = _load_patcher(repo_root)
    for relative in patcher.PATCHED_PATHS:
        patch_hashes[relative] = _normalized_hash((source / relative).read_bytes())
    data = {
        "schema": CACHE_SCHEMA,
        "lime_commit": LIME_COMMIT,
        "submodules": submodule_status,
        "source_status": source_status,
        "patcher_sha256": _file_sha256(patcher_path),
        "patches": patch_hashes,
        "hxcpp_version": selection.hxcpp_version,
        "hxcpp_package": str(selection.hxcpp_package.resolve()),
        "hxcpp_tree_sha256": _tree_fingerprint(selection.hxcpp_package),
        "haxe_binary": _tool_record(str(haxe_binary or (haxe_dir / "haxe")), env),
        "haxe_version": _checked_run([str(haxe_dir / ("haxe.exe" if os.name == "nt" else "haxe")), "--version"], env=env, description="Haxe version check").stdout.strip(),
        "haxelib": _tool_record(str(selection.haxelib), env),
        "compiler_tools": tools,
        "compiler_environment": {key: env.get(key, "") for key in FINGERPRINT_ENV_VARS},
        "target": {"platform": target.platform, "arch": target.arch, "folder": target.output_folder, "flags": target.hxcpp_flags},
    }
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_pe(data: bytes, arch: str) -> bool:
    if len(data) < 0x40 or data[:2] != b"MZ":
        return False
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    if offset + 6 > len(data) or data[offset : offset + 4] != b"PE\0\0":
        return False
    machine = struct.unpack_from("<H", data, offset + 4)[0]
    return machine == (0x8664 if arch == "64" else 0x014C)


def _is_elf(data: bytes, arch: str) -> bool:
    if len(data) < 20 or data[:4] != b"\x7fELF":
        return False
    expected_class = 2 if arch in ("64", "arm64") else 1
    elf_class = data[4]
    machine = struct.unpack_from("<H" if data[5] == 1 else ">H", data, 18)[0]
    expected_machine = {"32": 3, "64": 62, "arm64": 183}[arch]
    return elf_class == expected_class and machine == expected_machine


def _is_macho(data: bytes, arch: str) -> bool:
    if len(data) < 8:
        return False
    magic = data[:4]
    cpu_type = None
    if magic in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf"):
        cpu_type = struct.unpack_from(">I", data, 4)[0]
    elif magic in (b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"):
        cpu_type = struct.unpack_from("<I", data, 4)[0]
    elif magic == b"\xca\xfe\xba\xbe" and len(data) >= 8:
        count = struct.unpack_from(">I", data, 4)[0]
        if count > 32:
            return False
        for index in range(count):
            pos = 8 + index * 20
            if pos + 4 > len(data):
                return False
            if _cpu_matches(struct.unpack_from(">I", data, pos)[0], arch):
                return True
        return False
    else:
        return False
    return _cpu_matches(cpu_type, arch)


def _cpu_matches(cpu_type: int, arch: str) -> bool:
    return cpu_type == {"32": 7, "64": 0x01000007, "arm64": 0x0100000C}[arch]


def is_valid_native_binary(path: Path, target: BuildTarget) -> bool:
    try:
        with path.open("rb") as file:
            data = file.read(4096)
    except OSError:
        return False
    if target.binary_format == "pe":
        return _is_pe(data, target.arch)
    if target.binary_format == "elf":
        return _is_elf(data, target.arch)
    return _is_macho(data, target.arch)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(str(temp), str(path))
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


@contextlib.contextmanager
def _exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            if lock_file.tell() == 0 and lock_file.read(1) == b"":
                lock_file.seek(0)
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _read_metadata(path: Path) -> Dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _metadata_path(repo_root: Path, target: BuildTarget) -> Path:
    return repo_root / ".tools" / f"lime-uncapped-{target.platform}-{target.arch}.json"


def _build_or_reuse(
    repo_root: Path,
    source: Path,
    selection: HaxelibSelection,
    target: BuildTarget,
    fingerprint: str,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess],
) -> Tuple[Path, bool]:
    source_binary = source / "ndll" / target.output_folder / "lime.ndll"
    package_binary = selection.lime_package / "ndll" / target.output_folder / "lime.ndll"
    metadata_file = _metadata_path(repo_root, target)
    metadata = _read_metadata(metadata_file)

    cached_digest = metadata.get("artifact_sha256")
    cache_matches = (
        metadata.get("schema") == CACHE_SCHEMA
        and metadata.get("input_fingerprint") == fingerprint
        and isinstance(cached_digest, str)
        and is_valid_native_binary(source_binary, target)
        and _file_sha256(source_binary) == cached_digest
    )
    if cache_matches:
        artifact = source_binary.read_bytes()
        if not package_binary.is_file() or _file_sha256(package_binary) != cached_digest:
            _atomic_write(package_binary, artifact)
        return package_binary, False

    command = build_command(selection.haxelib, target)
    print(">> building checksum-pinned Lime 8.3.2 native library: " + " ".join(command))
    result = runner(command, cwd=source / "project", env=dict(env), capture_output=True)
    if result.returncode != 0:
        detail = (result.stdout or "") + (result.stderr or "")
        raise LimeUncappedError(f"native Lime build failed (exit {result.returncode}); installed library was left unchanged:\n{detail.strip()}")
    if not is_valid_native_binary(source_binary, target):
        raise LimeUncappedError(f"native Lime build succeeded but output is missing or invalid: {source_binary}; installed library was left unchanged")
    artifact = source_binary.read_bytes()
    digest = hashlib.sha256(artifact).hexdigest()

    # Recheck the selected haxelib before publishing in case a concurrent setup
    # process changed ~/.haxelib or the active package during compilation.
    current = verify_haxelib_selection(env, runner)
    if _norm_path(current.lime_package) != _norm_path(selection.lime_package):
        raise LimeUncappedError("selected Lime package changed during native build; refusing to publish")
    _atomic_write(package_binary, artifact)
    metadata = {
        "schema": CACHE_SCHEMA,
        "input_fingerprint": fingerprint,
        "artifact_sha256": digest,
        "artifact_size": len(artifact),
        "lime_commit": LIME_COMMIT,
        "platform": target.platform,
        "arch": target.arch,
        "output_folder": target.output_folder,
        "updated_unix": int(time.time()),
    }
    _atomic_write(metadata_file, (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return package_binary, True


def ensure_lime_uncapped(
    repo_root: Path,
    platform: str,
    arch: str,
    *,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., subprocess.CompletedProcess] = _run,
) -> Path:
    env = dict(env or os.environ)
    repo_root = repo_root.resolve()
    target = build_target(platform, arch, env)
    lock = repo_root / ".tools" / f"lime-uncapped-{target.platform}-{target.arch}.lock"
    with _exclusive_lock(lock):
        selection = verify_haxelib_selection(env, runner)
        source = ensure_source_checkout(repo_root, env=env, runner=runner)
        patcher = _load_patcher(repo_root)
        submodules, source_status = _verify_source_checkout(source, repo_root, env, runner, patcher)
        fingerprint = input_fingerprint(repo_root, source, selection, target, env, submodules, source_status)
        package_binary, rebuilt = _build_or_reuse(repo_root, source, selection, target, fingerprint, env, runner)
    action = "built and installed" if rebuilt else "verified cached"
    print(f">> {action} Lime 8.3.2 uncapped native library at {package_binary}")
    return package_binary


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows", "linux", "mac"), required=True)
    parser.add_argument("--arch", choices=("32", "64", "arm64"), required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        ensure_lime_uncapped(args.repo_root, args.platform, args.arch)
    except (LimeUncappedError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
