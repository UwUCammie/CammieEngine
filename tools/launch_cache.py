#!/usr/bin/env python3
"""Cache successful builds using input metadata, without reading gigabytes of media."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREES = ('source', 'assets', 'art', 'example_mods', 'TempFiles', '.haxelib',
         '.tools/haxe', '.tools/neko')
ROOT_INPUTS = ('Project.xml', 'VERSION', 'run.sh')
HELPERS = ('tools/launch_cache.py', 'tools/runtime_lock.sh')


def metadata(path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_mode]


def fingerprint(root):
    digest = hashlib.sha256(b'DisappointingPlus build cache v1\n')

    def visit(path, label, ancestors=()):
        path = os.fspath(path)
        file_stat = os.stat(path)
        if stat.S_ISDIR(file_stat.st_mode):
            resolved = os.path.realpath(path)
            if resolved in ancestors:
                raise ValueError(f'Symlink cycle in build inputs: {path}')
            with os.scandir(path) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
            for child in children:
                if child.name not in {'.git', '__pycache__'}:
                    visit(child.path, label + '/' + child.name, (*ancestors, resolved))
        else:
            digest.update(repr((label, file_stat.st_size, file_stat.st_mtime_ns,
                                file_stat.st_ctime_ns, file_stat.st_mode)).encode())
            if os.path.basename(path) == '.dev':
                # Haxelib development overrides can point outside this checkout.
                external = Path(Path(path).read_text().strip())
                if not external.is_absolute():
                    external = root / external
                visit(external, label + ':dev', ancestors)

    for name in ROOT_INPUTS:
        path = root / name
        if path.exists():
            visit(path, name)
        else:
            digest.update(('missing:' + name).encode())
    for name in (*TREES, *HELPERS):
        path = root / name
        if path.exists():
            visit(path, name)
        else:
            digest.update(('missing:' + name).encode())
    for name in ('CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'HAXE_STD_PATH',
                 'HAXEFLAGS', 'HXCPP_CONFIG'):
        digest.update(json.dumps([name, os.environ.get(name)]).encode())
    config = Path(os.environ.get('HXCPP_CONFIG', str(Path.home() / '.hxcpp_config.xml')))
    if config.is_file():
        visit(config, 'hxcpp-config')
    return digest.hexdigest()


def outputs(build):
    binary = build / 'linux/bin/Funkin'
    if not os.access(binary, os.X_OK) or not (build / 'linux/bin/assets').is_dir():
        raise FileNotFoundError('Runtime missing')
    return {name: metadata(build / 'linux/bin' / name) for name in ('Funkin', 'lime.ndll')}


def state_path(build):
    return build / '.launch-cache.json'


def fresh(root, build):
    try:
        state = json.loads(state_path(build).read_text())
        return state['outputs'] == outputs(build) and state['inputs'] == fingerprint(root)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def capture(root, build):
    state_path(build).unlink(missing_ok=True)
    return fingerprint(root)


def record(root, build, before):
    if fingerprint(root) != before:
        print('>> inputs changed during the build; next launch will recheck with a build')
        return
    state = {'inputs': before, 'outputs': outputs(build)}
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=build, delete=False) as handle:
        json.dump(state, handle)
    os.replace(handle.name, state_path(build))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'capture', 'record'])
    parser.add_argument('build', type=Path)
    parser.add_argument('before', nargs='?')
    args = parser.parse_args()
    build = ROOT / args.build
    if args.action == 'check':
        raise SystemExit(0 if fresh(ROOT, build) else 1)
    if args.action == 'capture':
        print(capture(ROOT, build))
    elif args.before is None:
        parser.error('record requires the input fingerprint captured before building')
    else:
        record(ROOT, build, args.before)


if __name__ == '__main__':
    main()
