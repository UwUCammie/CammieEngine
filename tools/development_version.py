"""Set development metadata to the next patch after a verified published build."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = re.compile(r'(<app\b[^>]*\bversion=")([^"]+)(")')
DOC_VERSION = re.compile(r'(?m)^((?:# )?CammieEngine v)\d+\.\d+\.\d+')


def next_patch_version(latest_release: str) -> str:
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-+][A-Za-z0-9.-]+)?', latest_release)
    if match is None:
        raise ValueError('latest release must be a verified semantic version tag')
    major, minor, patch = (int(part) for part in match.groups())
    return f'{major}.{minor}.{patch + 1}'


def configure_development_version(root: Path, latest_release: str, apply: bool = False) -> str:
    target = next_patch_version(latest_release)
    project_path = root / 'Project.xml'
    version_path = root / 'VERSION'
    project_bytes = project_path.read_bytes()
    project = project_bytes.decode('utf-8')
    match = APP_VERSION.search(project)
    if match is None:
        raise ValueError('Project.xml has no application version')
    current = version_path.read_text(encoding='utf-8').strip()
    branding_path = root / 'source' / 'EngineBranding.hx'
    branding = branding_path.read_text(encoding='utf-8') if branding_path.is_file() else None
    branding_pattern = re.compile(r"(FALLBACK_VERSION:String = ')[^']+(')")
    if branding is not None and not branding_pattern.search(branding):
        raise ValueError('EngineBranding.hx has no fallback version')
    branding_matches = branding is None or f"FALLBACK_VERSION:String = '{target}'" in branding
    documents = []
    for name in ('README.md', 'USER-README.txt'):
        path = root / name
        if not path.is_file():
            continue
        original = path.read_bytes()
        text = original.decode('utf-8')
        if DOC_VERSION.search(text) is None:
            raise ValueError(f'{name} has no CammieEngine version heading')
        updated = DOC_VERSION.sub(lambda found: found.group(1) + target, text, count=1).encode('utf-8')
        documents.append((path, original, updated))
    docs_match = all(original == updated for _, original, updated in documents)
    if current == target and match.group(2) == target and branding_matches and docs_match:
        return target
    if not apply:
        raise ValueError(f'development VERSION and Project.xml must both be {target}; use --apply after verifying the latest published build')
    project = APP_VERSION.sub(lambda found: found.group(1) + target + found.group(3), project, count=1)
    project_path.write_bytes(project.encode('utf-8'))
    if branding is not None:
        branding = branding_pattern.sub(lambda found: found.group(1) + target + found.group(2), branding, count=1)
        branding_path.write_bytes(branding.encode('utf-8'))
    newline = '\r\n' if b'\r\n' in version_path.read_bytes() else '\n'
    version_path.write_bytes((target + newline).encode('ascii'))
    for path, original, updated in documents:
        if original != updated:
            path.write_bytes(updated)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--latest-release', required=True, help='newest verified published GitHub build tag, including prereleases')
    parser.add_argument('--apply', action='store_true', help='update VERSION and Project.xml once; repeated calls retain the same version')
    parser.add_argument('--repo-root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        version = configure_development_version(args.repo_root, args.latest_release, args.apply)
    except (OSError, ValueError) as error:
        parser.exit(1, f'[development-version] {error}\n')
    print(f'Development version: {version}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
