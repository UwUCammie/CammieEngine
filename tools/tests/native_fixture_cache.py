"""Persistent, content-addressed cache for expensive native test fixtures."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import threading
import time
from typing import Any, Callable, Iterator, Mapping


_CACHE_SCHEMA = 1
_PROCESS_LOCK = threading.RLock()
_RENAME_RETRYABLE_WINERRORS = frozenset((5, 32, 33))
_RENAME_RETRY_WINDOW_SECONDS = 2.0
_RENAME_RETRY_MAX_ATTEMPTS = 16
_RENAME_RETRY_INITIAL_DELAY_SECONDS = 0.025
_RENAME_RETRY_MAX_DELAY_SECONDS = 0.2


@dataclass(frozen=True)
class CachedNativeFixture:
    executable: Path
    key: str
    sha256: str
    reused: bool


def canonical_fingerprint_bytes(fingerprint: Mapping[str, Any]) -> bytes:
    """Serialize fingerprint data deterministically for its cache key."""
    return json.dumps(fingerprint, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def fingerprint_key(fingerprint: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_fingerprint_bytes(fingerprint)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_executable(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    path = PurePosixPath(normalized)
    if (path.is_absolute() or normalized.startswith("//")
            or (len(normalized) >= 2 and normalized[1] == ":")
            or not parts or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("expected executable must be a normalized relative path")
    return path


@contextmanager
def _exclusive_process_lock(path: Path) -> Iterator[None]:
    """Lock a persistent file with the host OS so separate Python workers serialize."""
    if path.is_symlink() or _is_junction(path):
        raise ValueError("native fixture cache lock cannot be a symlink or junction")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    if path.resolve(strict=True).parent != path.parent.resolve(strict=True):
        raise ValueError("native fixture cache lock escaped its cache namespace")
    with path.open("r+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            while True:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    winerror = getattr(error, "winerror", None)
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK) and winerror not in (33, 36):
                        raise
                    time.sleep(0.05)
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


def _inside(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker()) if checker is not None else False


def _read_valid_entry(entry: Path, *, key: str, expected: PurePosixPath,
                      reused: bool) -> CachedNativeFixture | None:
    marker = entry / "READY.json"
    try:
        if entry.is_symlink() or _is_junction(entry) or marker.is_symlink() or _is_junction(marker):
            return None
        record = json.loads(marker.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None
        if (record.get("schema") != _CACHE_SCHEMA
                or record.get("key") != key
                or record.get("executable") != expected.as_posix()):
            return None

        entry_root = entry.resolve(strict=True)
        executable = (entry / Path(*expected.parts)).resolve(strict=True)
        if not _inside(entry_root, executable) or not executable.is_file():
            return None
        size = executable.stat().st_size
        if size <= 0 or size != record.get("size"):
            return None
        digest = sha256_file(executable)
        if digest != record.get("sha256"):
            return None
        return CachedNativeFixture(executable, key, digest, reused)
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _remove_owned_directory(path: Path, namespace: Path, required_prefix: str) -> None:
    """Remove only a helper-owned direct child with the expected name prefix."""
    namespace_root = namespace.resolve(strict=True)
    if not path.name.startswith(required_prefix) or path.parent.resolve(strict=True) != namespace_root:
        raise ValueError("refusing to remove a path outside the native fixture cache")
    if path.is_symlink():
        path.unlink(missing_ok=True)
    elif _is_junction(path):
        os.rmdir(path)
    elif path.is_dir():
        resolved = path.resolve(strict=True)
        if not _inside(namespace_root, resolved) or resolved.parent != namespace_root:
            raise ValueError("refusing to recursively remove a path outside the native fixture cache")
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _replace_with_retry(source: Path, destination: Path, *,
                        replace: Callable[[Path, Path], Any] | None = None,
                        windows: bool | None = None,
                        retry_window_seconds: float = _RENAME_RETRY_WINDOW_SECONDS,
                        monotonic: Callable[[], float] | None = None,
                        sleep: Callable[[float], None] | None = None) -> None:
    """Retry transient Windows rename locks without masking permanent errors."""
    replace_fn = os.replace if replace is None else replace
    is_windows = os.name == "nt" if windows is None else windows
    if is_windows:
        clock = time.monotonic if monotonic is None else monotonic
        wait = time.sleep if sleep is None else sleep
        deadline = clock() + max(0.0, retry_window_seconds)
        delay = _RENAME_RETRY_INITIAL_DELAY_SECONDS
        attempts = 0
        while True:
            attempts += 1
            try:
                replace_fn(source, destination)
                return
            except OSError as error:
                if getattr(error, "winerror", None) not in _RENAME_RETRYABLE_WINERRORS:
                    raise
                remaining = deadline - clock()
                if remaining <= 0 or attempts >= _RENAME_RETRY_MAX_ATTEMPTS:
                    raise
                wait(min(delay, remaining))
                delay = min(delay * 2, _RENAME_RETRY_MAX_DELAY_SECONDS)
    else:
        replace_fn(source, destination)


def _quarantine_invalid_entry(entry: Path, namespace: Path, key: str) -> None:
    if not entry.exists() and not entry.is_symlink():
        return
    namespace_root = namespace.resolve(strict=True)
    if entry.parent.resolve(strict=True) != namespace_root:
        raise ValueError("refusing to quarantine a path outside the native fixture cache")
    quarantine = namespace / f".corrupt-{key}-{time.time_ns()}-{os.getpid()}"
    if quarantine.parent.resolve(strict=True) != namespace_root:
        raise ValueError("refusing to quarantine a path outside the native fixture cache")
    # get_or_build calls this while holding both the process lock and the
    # per-key OS lock, so another cache writer cannot race the rename.
    _replace_with_retry(entry, quarantine)

    corrupt = sorted(namespace.glob(f".corrupt-{key}-*"),
                     key=lambda path: path.stat().st_mtime_ns if path.exists() else 0,
                     reverse=True)
    for obsolete in corrupt[2:]:
        _remove_owned_directory(obsolete, namespace, f".corrupt-{key}-")


def _clean_stale_staging(namespace: Path, key: str) -> None:
    for stale in namespace.glob(f".building-{key}-*"):
        _remove_owned_directory(stale, namespace, f".building-{key}-")


def _write_ready_marker(path: Path, record: Mapping[str, Any]) -> None:
    temporary = path.with_name(".READY.json.tmp")
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("utf-8")
    with temporary.open("wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def get_or_build(cache_root: Path | str, fingerprint: Mapping[str, Any],
                 expected_executable: str,
                 builder: Callable[[Path], Path | str], *,
                 build_metadata: Mapping[str, Any] | None = None) -> CachedNativeFixture:
    """Return a validated cached executable or build and atomically publish it.

    `builder` receives a private staging directory and must write and return the
    expected executable path under that directory. It raises on build failure.
    The cache never interprets a failed build as a valid entry.
    """
    expected = _relative_executable(expected_executable)
    key = fingerprint_key(fingerprint)
    root = Path(cache_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    namespace = root / "import-windows"
    if namespace.is_symlink() or _is_junction(namespace):
        raise ValueError("native fixture cache namespace cannot be a symlink or junction")
    namespace.mkdir(parents=True, exist_ok=True)
    namespace = namespace.resolve(strict=True)
    if namespace.parent != root:
        raise ValueError("native fixture cache namespace escaped its configured cache root")
    entry = namespace / key

    with _PROCESS_LOCK:
        with _exclusive_process_lock(namespace / f"{key}.lock"):
            hit = _read_valid_entry(entry, key=key, expected=expected, reused=True)
            if hit is not None:
                return hit

            _quarantine_invalid_entry(entry, namespace, key)
            _clean_stale_staging(namespace, key)
            staging = Path(tempfile.mkdtemp(prefix=f".building-{key}-{os.getpid()}-",
                                            dir=namespace))
            try:
                produced = Path(builder(staging)).resolve(strict=True)
                staging_root = staging.resolve(strict=True)
                expected_path = (staging / Path(*expected.parts)).resolve(strict=True)
                if not _inside(staging_root, produced) or produced != expected_path:
                    raise ValueError("builder returned an executable outside its expected staging path")
                if not produced.is_file() or produced.stat().st_size <= 0:
                    raise RuntimeError("native fixture builder did not produce a nonempty executable")

                record = {
                    "schema": _CACHE_SCHEMA,
                    "key": key,
                    "executable": expected.as_posix(),
                    "size": produced.stat().st_size,
                    "sha256": sha256_file(produced),
                    "createdUnixNs": time.time_ns(),
                    "buildMetadata": dict(build_metadata or {}),
                }
                _write_ready_marker(staging / "READY.json", record)
                os.replace(staging, entry)
            except BaseException:
                if staging.exists() or staging.is_symlink():
                    _remove_owned_directory(staging, namespace, f".building-{key}-")
                raise

            built = _read_valid_entry(entry, key=key, expected=expected, reused=False)
            if built is None:
                raise RuntimeError("published native fixture failed ready-manifest validation")
            return built
