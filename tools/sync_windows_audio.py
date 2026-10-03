"""Sync bundled audio by Git's file list without walking large import trees."""

from pathlib import Path
import argparse
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sync_audio(runtime: Path, repository: Path = ROOT) -> int:
    runtime = runtime.resolve(strict=True)
    repository = repository.resolve(strict=True)
    names = subprocess.check_output(
        ['git', '-C', str(repository), 'ls-files', '-z', 'assets/songs', 'assets/music']
    ).decode('utf-8').split('\0')
    copied = 0
    for relative in filter(None, names):
        source = repository / relative
        target = runtime / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError(f'Bundled audio source is missing: {source}')
        before = source.stat()
        current = target.stat() if target.exists() else None
        if current is not None and current.st_size == before.st_size and current.st_mtime_ns >= before.st_mtime_ns:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    args = parser.parse_args()
    print(f'>> synced {sync_audio(args.runtime)} bundled audio files')


if __name__ == '__main__':
    main()
