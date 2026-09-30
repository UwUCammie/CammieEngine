"""Check imported character dependencies without loading or hashing media."""
import json
from pathlib import Path
import re


def read_json(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    # Preserve quoted strings, including URLs, while removing JSONC comments.
    text = re.sub(r'("(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/)',
                  lambda m: m[0] if m[0].startswith('"') else '', text, flags=re.S)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.JSONDecoder().raw_decode(text.lstrip())[0]


def character_problems(assets, registry, name):
    """Match Character's registry/folder/implementation requirements."""
    folder = Path(assets) / 'images/custom_chars'
    issues = []
    entry = registry.get(name)
    if not isinstance(entry, dict):
        issues.append('missing registry entry')
    like = entry.get('like') if isinstance(entry, dict) else None
    # Character prefers a name-specific asset folder, but imported aliases may
    # deliberately share the implementation folder and its atlas.
    if not (folder / name).is_dir() and not (
            isinstance(like, str) and like and (folder / like).is_dir()):
        issues.append('missing character folder')
    if not isinstance(like, str) or not like or not any(
            (folder / (like + ext)).is_file() for ext in ('.hscript', '.hxs', '.json', '.jsonc')):
        issues.append('missing animation implementation')
    return issues


def registry_for(assets):
    folder = Path(assets) / 'images/custom_chars'
    for ext in ('.json', '.jsonc'):
        path = folder / ('custom_chars' + ext)
        if path.is_file():
            return read_json(path)
    return {}


def audit_characters(assets, donor_assets):
    assets, donor_assets = Path(assets), Path(donor_assets)
    registry, donor_registry = registry_for(assets), registry_for(donor_assets)
    references = {}
    for path in sorted((assets / 'data').glob('*/*.json')):
        if 'copy' in path.name.lower():
            continue
        try:
            song = read_json(path).get('song')
        except (ValueError, AttributeError):
            continue
        if not isinstance(song, dict) or 'notes' not in song:
            continue
        for role in ('player1', 'player2', 'gf'):
            name = song.get(role)
            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            if name.endswith('-dead'):
                name = name[:-5]
            if character_problems(assets, registry, name):
                references.setdefault(name, []).append({'chart': str(path.relative_to(assets)), 'role': role})
    return [dict(character=name, problems=character_problems(assets, registry, name),
                 donor_problems=character_problems(donor_assets, donor_registry, name),
                 references=references[name]) for name in sorted(references)]
