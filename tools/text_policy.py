"""Inventory punctuation in engine-owned text without scanning retained content."""
from pathlib import Path

TEXT_SUFFIXES = frozenset({'.hx', '.py', '.md', '.txt', '.xml', '.json', '.jsonc', '.yml', '.yaml', '.sh', '.bat', '.ps1', '.lua', '.hscript', '.html', '.css', '.js'})
OWNED_TREES = ('source', 'tools', '.github')
EXCLUDED_PREFIXES = ('tools/licenses/', 'source/crowplexus/', 'source/llua/', 'source/discord_rpc/', 'source/Polymod/')
EXCLUDED_DIRECTORIES = frozenset({'__pycache__', '.git', '.haxelib', '.tools', 'vendor', 'generated', 'export', 'tmp', 'dump', 'docs', 'assets', 'example_mods'})


def engine_text_files(root: Path):
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path
    for tree in OWNED_TREES:
        folder = root / tree
        if not folder.is_dir():
            continue
        for path in folder.rglob('*'):
            relative = path.relative_to(root)
            if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
                continue
            if any(relative.as_posix().startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                continue
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def punctuation_violations(root: Path):
    for path in engine_text_files(root):
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if chr(0x2014) in line:
                yield f'{path.relative_to(root).as_posix()}:{line_number}'
