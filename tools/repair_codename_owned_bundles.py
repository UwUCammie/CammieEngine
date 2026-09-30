#!/usr/bin/env python3
"""Plan/apply Codename owner refreshes from an isolated importer preview.

The default plan only adds missing owner files. A separate explicit opt-in
allows narrowly recognized generated-artifact replacements; every target is
bound to before/after hashes and backed up before atomic replacement. Custom
implementation differences are rejected, and donor files are never modified.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

import refresh_codename_events as shared

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / 'tmp'
LOCK_ROOT = ROOT / '.tools'
MAX_FILES = 10000
MAX_BYTES = 2 * 1024 * 1024 * 1024
REGISTRIES = {'images/custom_chars/custom_chars.jsonc',
              'images/custom_stages/custom_stages.json'}
GENERATED_REPLACEMENT_POLICY = 1
CAMERA_FILE = '__cammie_compat_camera.json'
SONG_META_FILE = '__cammie_compat_song_meta_resolved.json'
CHARACTER_ATLAS_DIR = 'images/custom_chars'
LINE_ADDITIONS = {'keyCount', 'strumSpacing', 'strumPos', 'strumScale', 'strumLinePos'}


def registry_entry_equal(old, fresh):
    """Allow a newly explicit false for the importer's optional atlas flag.

    Older owner registries omitted this field. The runtime chooses an Animate
    atlas from the owned files, so an absent flag and ``false`` carry the same
    value. Other metadata changes remain conflicts and are never refreshed.
    """
    if isinstance(old, dict) and isinstance(fresh, dict):
        old = dict(old)
        fresh = dict(fresh)
        old_char = old.get('codenameCharacter')
        fresh_char = fresh.get('codenameCharacter')
        if isinstance(old_char, dict) and isinstance(fresh_char, dict):
            old_char = dict(old_char)
            fresh_char = dict(fresh_char)
            if 'animateAtlas' not in old_char and fresh_char.get('animateAtlas') is False:
                fresh_char.pop('animateAtlas')
            old['codenameCharacter'] = old_char
            fresh['codenameCharacter'] = fresh_char
    return shared.canonical(old) == shared.canonical(fresh)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def registry_generated_upgrade(old, fresh):
    """Accept only new bool atlas flags; return the entries newly enabled."""
    if not isinstance(old, dict) or not isinstance(fresh, dict) or set(old) != set(fresh):
        raise ValueError('owner registry conflict: registry keys changed')
    enabled = []
    for name in sorted(old):
        present, generated = old[name], fresh[name]
        if not isinstance(present, dict) or not isinstance(generated, dict):
            raise ValueError('owner registry conflict: invalid entry ' + str(name))
        present_char = present.get('codenameCharacter')
        generated_char = generated.get('codenameCharacter')
        if isinstance(present_char, dict) and isinstance(generated_char, dict):
            present_char, generated_char = dict(present_char), dict(generated_char)
            present_has = 'animateAtlas' in present_char
            generated_has = 'animateAtlas' in generated_char
            if (not present_has and generated_has
                    and isinstance(generated_char['animateAtlas'], bool)):
                if generated_char['animateAtlas']:
                    enabled.append(name)
                generated_char.pop('animateAtlas')
            elif present_has != generated_has or (present_has
                    and present_char.get('animateAtlas') != generated_char.get('animateAtlas')):
                raise ValueError('owner registry conflict: atlas flag changed for ' + str(name))
            present['codenameCharacter'] = present_char
            generated['codenameCharacter'] = generated_char
        if shared.canonical(present) != shared.canonical(generated):
            raise ValueError('owner registry conflict: authored metadata changed for ' + str(name))
    return enabled


def _stage_placement_value(line):
    match = re.fullmatch(
        r'\s*stage\.setCodenamePlacement\(("(?:\\.|[^"\\])*")\);\s*', line)
    if not match:
        return None
    try:
        value = json.loads(json.loads(match.group(1)))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_stage_placement_evolution(old_value, new_value):
    """Recognize importer-only placement schema evolution without arbitrary edits."""
    if old_value is None:
        return isinstance(new_value, dict) and bool(new_value.get('slots'))
    if not isinstance(old_value, dict) or not isinstance(new_value, dict):
        return False
    old = json.loads(json.dumps(old_value))
    new = json.loads(json.dumps(new_value))
    if 'runtimeMutationHooks' not in old and new.get('runtimeMutationHooks') == []:
        new.pop('runtimeMutationHooks')
    old_unsupported = old.get('unsupported')
    new_unsupported = new.get('unsupported')
    if old_unsupported == ['stage-script'] and new_unsupported == []:
        old['unsupported'] = []
    return shared.canonical(old) == shared.canonical(new)


def stage_script_generated_upgrade(old_bytes, new_bytes):
    """Allow only known Codename stage-converter outputs to change.

    The generated header is necessary but not sufficient: after removing the
    structured placement call, every remaining byte must match except for the
    generated actor-offset setter triple whose new numbers agree with the new
    placement object.
    """
    try:
        old_text, new_text = old_bytes.decode('utf-8'), new_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return False
    old_lines, new_lines = old_text.splitlines(), new_text.splitlines()
    generated_header = re.compile(
        r'^// Generated by the Codename importer from the donor stage XML \("[^"\r\n]+"\)\.$')
    if (not old_lines or not new_lines or not generated_header.fullmatch(old_lines[0])
            or old_lines[0] != new_lines[0]):
        return False
    old_calls = [(i, _stage_placement_value(line)) for i, line in enumerate(old_lines)
                 if 'stage.setCodenamePlacement' in line]
    new_calls = [(i, _stage_placement_value(line)) for i, line in enumerate(new_lines)
                 if 'stage.setCodenamePlacement' in line]
    if len(old_calls) > 1 or len(new_calls) != 1 or any(value is None for _, value in new_calls):
        return False
    if old_calls and old_calls[0][1] is None:
        return False
    old_value = old_calls[0][1] if old_calls else None
    new_value = new_calls[0][1]
    if not _safe_stage_placement_evolution(old_value, new_value):
        return False
    old_without = [line for line in old_lines if 'stage.setCodenamePlacement' not in line]
    new_without = [line for line in new_lines if 'stage.setCodenamePlacement' not in line]

    # A generated stage can change a source-authored character's x/y values.
    # Permit only the importer-emitted setOffsets/x/y triplet, and only when
    # the fresh values match the generated placement slot in the added call.
    if old_without != new_without:
        if len(old_without) != len(new_without):
            return False
        changed = [i for i, pair in enumerate(zip(old_without, new_without)) if pair[0] != pair[1]]
        if not changed:
            return False
        allowed = set()
        slots = new_value.get('slots')
        if not isinstance(slots, dict):
            return False
        for slot, placement in slots.items():
            if not isinstance(placement, dict):
                continue
            actor = {'girlfriend': 'gf', 'boyfriend': 'bf'}.get(slot, slot)
            x, y = placement.get('x'), placement.get('y')
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            candidates = [
                f'    stage.setOffsets("{actor}", {x:g}, {y:g}, false);',
                f'    {actor}.x = {x:g};',
                f'    {actor}.y = {y:g};',
            ]
            for index in range(len(new_without) - 2):
                if new_without[index:index + 3] == candidates:
                    allowed.update((index, index + 1, index + 2))
        if any(index not in allowed for index in changed):
            return False
        for index in changed:
            offset = re.fullmatch(
                r'\s*stage\.setOffsets\("([A-Za-z0-9_-]+)",\s*-?[0-9]+(?:\.[0-9]+)?,\s*'
                r'-?[0-9]+(?:\.[0-9]+)?,\s*(?:true|false)\);\s*', old_without[index])
            x_value = re.fullmatch(r'\s*([A-Za-z0-9_]+)\.x = -?[0-9]+(?:\.[0-9]+)?;\s*',
                                   old_without[index])
            y_value = re.fullmatch(r'\s*([A-Za-z0-9_]+)\.y = -?[0-9]+(?:\.[0-9]+)?;\s*',
                                   old_without[index])
            new_offset = re.match(r'\s*stage\.setOffsets\("([A-Za-z0-9_-]+)"',
                                  new_without[index])
            new_actor = re.match(r'\s*([A-Za-z0-9_]+)\.[xy] = ', new_without[index])
            old_actor = (offset.group(1) if offset else
                         x_value.group(1) if x_value else y_value.group(1) if y_value else None)
            new_actor_name = (new_offset.group(1) if new_offset else
                              new_actor.group(1) if new_actor else None)
            if old_actor is None or old_actor != new_actor_name:
                return False
    return old_text.endswith('\n') == new_text.endswith('\n')


def generated_fallback_id(preview, owner):
    """Resolve a copied engine-base character only from its owner receipt."""
    dependency_root = preview / owner / 'compat-engine-base'
    receipt_path = dependency_root / 'character-dependency.json'
    if not safe_file(receipt_path, preview):
        return None
    try:
        receipt = read_json(receipt_path)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if (not isinstance(receipt, dict) or set(receipt) !=
            {'version', 'ownerNamespace', 'fallbackId', 'sprite', 'files'}
            or receipt.get('version') != 2 or receipt.get('ownerNamespace') != owner
            or not shared.safe_segment(receipt.get('fallbackId', ''))
            or not shared.safe_segment(receipt.get('sprite', ''))
            or not isinstance(receipt.get('files'), list) or len(receipt['files']) < 2):
        return None
    destinations = set()
    for item in receipt['files']:
        if (not isinstance(item, dict)
                or set(item) != {'sourceRelative', 'destinationRelative', 'digest'}
                or not isinstance(item.get('digest'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', item['digest'])):
            return None
        source_relative, destination_relative = item.get('sourceRelative'), item.get('destinationRelative')
        if (not isinstance(source_relative, str) or not isinstance(destination_relative, str)
                or '\\' in source_relative or '\\' in destination_relative):
            return None
        relative = Path(destination_relative)
        source_parts = Path(source_relative).parts
        if (relative.is_absolute() or any(part in ('', '.', '..') or not shared.safe_segment(part)
                                           for part in relative.parts)
                or any(part in ('', '.', '..') or not shared.safe_segment(part) for part in source_parts)):
            return None
        destination = dependency_root / relative
        if (not safe_file(destination, preview) or digest(destination) != item['digest']
                or destination_relative in destinations):
            return None
        destinations.add(destination_relative)
    expected_xml = 'data/characters/' + receipt['fallbackId'] + '.xml'
    if expected_xml not in destinations:
        return None
    return receipt['fallbackId']


def _safe_codename_relative(value):
    return (isinstance(value, str) and value.strip() not in ('', '.', '..')
            and '\\' not in value and '\0' not in value
            and all(shared.safe_segment(part) for part in value.split('/')))


def _ini_value(contents, section, name):
    current = ''
    result = None
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if line.startswith('[') and line.endswith(']'):
            current = line[1:-1]
            continue
        if current != section or not line or line.startswith('#') or line.startswith(';'):
            continue
        equals = line.find('=')
        if equals < 0 or line[:equals].strip() != name:
            continue
        value = line[equals + 1:].strip()
        if (len(value) >= 2 and ((value.startswith('"') and value.endswith('"'))
                                 or (value.startswith("'") and value.endswith("'")))):
            value = value[1:-1]
        result = value
    return result


def _codename_config_value(root, section, name):
    """Mirror the selected Codename owner's supported flags-file precedence."""
    candidates = ('data/config/modpack.ini', 'data/config/flags.ini', 'flags.ini')
    evidence = []
    for relative in candidates:
        path = root / relative
        if not path.exists():
            evidence.append({'path': relative, 'exists': False})
            continue
        if not safe_file(path, root):
            return None, evidence, False
        try:
            contents = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            return None, evidence, False
        value = _ini_value(contents, section, name)
        evidence.append({'path': relative, 'exists': True, 'sha256': digest(path)})
        if value is not None:
            return value, evidence, True
    return None, evidence, True


def _codename_source_root(donor, provenance, owner, source_song):
    """Bind legacy provenance to one source root; never search across mod owners."""
    if (not isinstance(provenance, dict) or provenance.get('sourceOwner') != owner
            or provenance.get('sourceEngine') != 'Codename Engine'
            or provenance.get('sourceFolder') != source_song
            or not shared.safe_segment(provenance.get('modName', ''))
            or not shared.safe_segment(source_song)):
        return None
    mod_name = provenance['modName']
    roots = []
    direct_song = donor / 'songs' / source_song
    if (safe_directory(donor, donor) and safe_directory(direct_song, donor)
            and safe_directory(donor / 'data' / 'characters', donor)):
        direct_name, _, ok = _codename_config_value(donor, 'Common', 'NAME')
        if not ok:
            return None
        if donor.name == mod_name or direct_name == mod_name:
            roots.append(donor)
    mods = donor / 'mods'
    if mods.exists():
        if not safe_directory(mods, donor):
            return None
        try:
            children = sorted(mods.iterdir())
        except OSError:
            return None
        for child in children:
            if not child.is_dir() or child.is_symlink() or not safe_directory(child, donor):
                continue
            if not (safe_directory(child / 'songs' / source_song, donor)
                    and safe_directory(child / 'data' / 'characters', donor)):
                continue
            common_name, _, ok = _codename_config_value(child, 'Common', 'NAME')
            if not ok:
                return None
            if child.name == mod_name or common_name == mod_name:
                roots.append(child)
    # Identical candidate paths can arise when the directly selected root is
    # also enumerated through `mods`; count them once, but reject real ambiguity.
    unique = {path.resolve(): path for path in roots}
    if len(unique) != 1:
        return None
    selected = next(iter(unique.values()))
    song_folder = selected / 'songs' / source_song
    if (not safe_directory(song_folder, donor)
            or not safe_file(song_folder / 'meta.json', donor)
            or not safe_directory(song_folder / 'charts', donor)):
        return None
    return selected


def _codename_fallback_reference(root):
    configured, config_evidence, ok = _codename_config_value(root, 'Flags', 'DEFAULT_CHARACTER')
    if not ok:
        return None, config_evidence
    if configured is None:
        return 'bf', config_evidence
    if not _safe_codename_relative(configured):
        return None, config_evidence
    return configured, config_evidence


def _codename_native_character_name(authored_id):
    # CodenameImporter.safeStem: use the last path component, remove its final
    # extension, replace spaces with hyphens, then keep its supported ASCII set.
    clean = authored_id.strip().replace('\\', '/').rsplit('/', 1)[-1]
    clean = Path(clean).stem
    result = ''.join('-' if char == ' ' else char for char in clean
                     if char.isascii() and (char.isalnum() or char in '-_. '))
    return result if result.strip() else 'codename-content'


def _safe_scoped_file(root, relative):
    path = root / relative
    if not path.exists():
        return None
    return path if safe_file(path, root) else None


def _atlas_bundle(root, sprite):
    """Return Codename's resolved atlas files with raw and converted destinations."""
    if not _safe_codename_relative(sprite):
        return None
    base = Path('images') / 'characters' / Path(sprite)
    base_string = base.as_posix()
    directory = root / base
    manifest = _safe_scoped_file(root, base / 'Animation.json')
    if manifest is not None:
        if not safe_directory(directory, root):
            return None
        files = []
        total = 0
        for current, dirs, names in os.walk(directory, followlinks=False):
            folder = Path(current)
            if not safe_directory(folder, root):
                return None
            if any((folder / name).is_symlink() for name in dirs + names):
                return None
            for name in sorted(names):
                if Path(name).suffix.lower() not in {'.json', '.png', '.xml', '.txt',
                                                      '.jpg', '.jpeg', '.webp'}:
                    continue
                source = folder / name
                if not safe_file(source, root):
                    return None
                relative = source.relative_to(directory).as_posix()
                destination = (Path(base_string) / relative).as_posix()
                converted = (Path('images/custom_chars') / '__NATIVE__' / 'char' / relative).as_posix()
                files.append((source, destination, converted))
                total += source.stat().st_size
        names = {Path(source).name.lower() for source, _, _ in files}
        if ('animation.json' not in names or 'spritemap1.png' not in names
                or 'spritemap1.json' not in names or len(files) > MAX_FILES or total > MAX_BYTES):
            return None
        return files

    pages = []
    for page in range(1, 17):
        png_rel = Path(base_string + '/' + str(page) + '.png')
        xml_rel = Path(base_string + '/' + str(page) + '.xml')
        png, xml = _safe_scoped_file(root, png_rel), _safe_scoped_file(root, xml_rel)
        if png is None and xml is None:
            # A later page after a gap is ambiguous/incomplete for a refresh.
            for later in range(page + 1, 17):
                if ((root / (base_string + '/' + str(later) + '.png')).exists()
                        or (root / (base_string + '/' + str(later) + '.xml')).exists()):
                    return None
            break
        if png is None or xml is None:
            return None
        pages.extend([(png, str(png_rel), 'images/custom_chars/__NATIVE__/char/' + str(page) + '.png'),
                      (xml, str(xml_rel), 'images/custom_chars/__NATIVE__/char/' + str(page) + '.xml')])
    if pages:
        return pages

    png_rel, xml_rel = Path(base_string + '.png'), Path(base_string + '.xml')
    png, xml = _safe_scoped_file(root, png_rel), _safe_scoped_file(root, xml_rel)
    if png is not None and xml is not None:
        return [(png, png_rel.as_posix(), 'images/custom_chars/__NATIVE__/char.png'),
                (xml, xml_rel.as_posix(), 'images/custom_chars/__NATIVE__/char.xml')]
    if (root / png_rel).exists() or (root / xml_rel).exists():
        return None

    # CodenameImporter also accepts a unique nested Sparrow atlas whose file
    # stem matches a short sprite key, materializing it at the requested key.
    character_root = root / 'images' / 'characters'
    if not safe_directory(character_root, root):
        return None
    basename = Path(sprite).name.lower()
    matches = []
    for current, dirs, names in os.walk(character_root, followlinks=False):
        folder = Path(current)
        if not safe_directory(folder, root) or any((folder / name).is_symlink() for name in dirs + names):
            return None
        for name in names:
            source = folder / name
            if Path(name).suffix.lower() != '.png' or Path(name).stem.lower() != basename:
                continue
            xml = source.with_suffix('.xml')
            if not safe_file(source, root) or not safe_file(xml, root):
                continue
            matches.append((source, xml))
            if len(matches) > 1:
                return None
    if len(matches) != 1:
        return None
    source_png, source_xml = matches[0]
    return [(source_png, png_rel.as_posix(), 'images/custom_chars/__NATIVE__/char.png'),
            (source_xml, xml_rel.as_posix(), 'images/custom_chars/__NATIVE__/char.xml')]


def owner_local_fallback_proof(donor, runtime, preview, owner, source_song, context):
    """Prove the selected source root's local DEFAULT_CHARACTER is installed."""
    if not isinstance(context, dict):
        return None, []
    old, fresh = context.get('old'), context.get('fresh')
    if (not isinstance(old, dict) or not isinstance(fresh, dict)
            or old.get('sourceOwner') != owner or fresh.get('sourceOwner') != owner
            or old.get('sourceEngine') != 'Codename Engine'
            or fresh.get('sourceEngine') != 'Codename Engine'
            or old.get('sourceFolder') != source_song or fresh.get('sourceFolder') != source_song
            or old.get('modName') != fresh.get('modName')):
        return None, []
    source_root = _codename_source_root(donor, fresh, owner, source_song)
    if source_root is None:
        return None, []
    fallback_id, source_config = _codename_fallback_reference(source_root)
    if fallback_id is None:
        return None, []
    preview_owner, runtime_owner = preview / owner, runtime / owner
    runtime_fallback, runtime_config = _codename_fallback_reference(runtime_owner)
    preview_fallback, preview_config = _codename_fallback_reference(preview_owner)
    if runtime_fallback != fallback_id or preview_fallback != fallback_id:
        return None, []
    xml_relative = Path('data/characters') / (fallback_id + '.xml')
    source_xml = _safe_scoped_file(source_root, xml_relative)
    preview_xml = _safe_scoped_file(preview_owner, xml_relative)
    runtime_xml = _safe_scoped_file(runtime_owner, xml_relative)
    if (source_xml is None or preview_xml is None or runtime_xml is None
            or source_xml.read_bytes() != preview_xml.read_bytes()
            or source_xml.read_bytes() != runtime_xml.read_bytes()):
        return None, []
    try:
        element = ET.fromstring(source_xml.read_bytes())
    except (ET.ParseError, ValueError, OSError):
        return None, []
    if element.tag != 'character':
        return None, []
    sprite = element.attrib.get('sprite', fallback_id)
    if not _safe_codename_relative(sprite):
        return None, []
    native_name = _codename_native_character_name(fallback_id)
    atlas = _atlas_bundle(source_root, sprite)
    if not atlas:
        return None, []
    atlas_evidence = []
    converted_atlas = []
    for source_path, raw_destination, converted_template in atlas:
        preview_path = preview_owner / raw_destination
        runtime_path = runtime_owner / raw_destination
        converted_rel = converted_template.replace('__NATIVE__', native_name)
        preview_converted = preview_owner / converted_rel
        runtime_converted = runtime_owner / converted_rel
        if (not safe_file(preview_path, preview_owner) or not safe_file(runtime_path, runtime_owner)
                or not safe_file(preview_converted, preview_owner)
                or not safe_file(runtime_converted, runtime_owner)):
            return None, []
        source_bytes = source_path.read_bytes()
        if (source_bytes != preview_path.read_bytes() or source_bytes != runtime_path.read_bytes()
                or source_bytes != preview_converted.read_bytes()
                or source_bytes != runtime_converted.read_bytes()):
            return None, []
        row = {'source': str(source_path), 'relative': raw_destination,
               'sha256': digest(source_path)}
        atlas_evidence.append(row)
        converted_atlas.append({'relative': converted_rel, 'sha256': row['sha256']})
    script_relative = Path('images/custom_chars') / (native_name + '.hscript')
    preview_script = _safe_scoped_file(preview_owner, script_relative)
    runtime_script = _safe_scoped_file(runtime_owner, script_relative)
    if preview_script is None or runtime_script is None or preview_script.read_bytes() != runtime_script.read_bytes():
        return None, []
    script_text = preview_script.read_text(encoding='utf-8')
    header = '// Generated by the Codename importer from the donor character XML ("' + native_name + '").'
    if (not script_text.startswith(header) or 'function init(char) {' not in script_text
            or ('char.loadTextureAtlas(hscriptPath + \'char\');' not in script_text
                and 'FlxAtlasFrames.fromSparrow' not in script_text)):
        return None, []
    for label, owner_root in (('preview', preview_owner), ('runtime', runtime_owner)):
        registry = _safe_scoped_file(owner_root, 'images/custom_chars/custom_chars.jsonc')
        if registry is None:
            return None, []
        try:
            entry = read_json(registry).get(native_name)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None, []
        if (not isinstance(entry, dict) or entry.get('like') != native_name
                or not isinstance(entry.get('codenameCharacter'), dict)):
            return None, []

    evidence = {
        'fallbackSource': 'selected-owner', 'sourceRoot': source_root.relative_to(donor).as_posix(),
        'modName': fresh.get('modName'), 'sourceFolder': source_song,
        'sourceIdentity': fresh.get('sourceIdentity'), 'sourceFingerprint': fresh.get('sourceFingerprint'),
        'fallbackId': fallback_id, 'nativeName': native_name,
        'sourceFlags': source_config, 'runtimeFlags': runtime_config, 'previewFlags': preview_config,
        'characterXml': {'relative': xml_relative.as_posix(), 'sha256': digest(source_xml)},
        'atlasFiles': atlas_evidence, 'convertedAtlasFiles': converted_atlas,
        'characterScript': {'relative': script_relative.as_posix(), 'sha256': digest(preview_script)},
        'characterRegistry': 'images/custom_chars/custom_chars.jsonc'
    }
    return native_name, evidence


def camera_sidecar_generated_upgrade(old, fresh, fallback_id=None):
    if (not isinstance(old, dict) or not isinstance(fresh, dict)
            or old.get('version') != 1 or fresh.get('version') != 1
            or old.get('song') != fresh.get('song')
            or set(old) != {'version', 'song', 'difficulties'}
            or set(fresh) != set(old)
            or set(old['difficulties']) != set(fresh['difficulties'])):
        return False
    changed = False
    for difficulty, prior in old['difficulties'].items():
        current = fresh['difficulties'][difficulty]
        if not isinstance(prior, dict) or not isinstance(current, dict) or set(prior) != set(current):
            return False
        for key in prior:
            if key == 'lines':
                before, after = prior[key], current[key]
                if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
                    return False
                for old_line, new_line in zip(before, after):
                    if not isinstance(old_line, dict) or not isinstance(new_line, dict):
                        return False
                    additions = set(new_line) - set(old_line)
                    if not additions <= LINE_ADDITIONS or any(name in old_line for name in additions):
                        return False
                    projected = dict(new_line)
                    for name in additions:
                        projected.pop(name)
                    if shared.canonical(projected) != shared.canonical(old_line):
                        return False
                    changed = changed or bool(additions)
            elif key == 'nativeCharacters':
                before, after = prior[key], current[key]
                if not isinstance(before, dict) or not isinstance(after, dict) or set(before) != set(after):
                    return False
                missing = prior.get('missingCharacters')
                if not isinstance(missing, list):
                    return False
                for character in before:
                    if before[character] == after[character]:
                        continue
                    if (fallback_id is None or before[character] is not None
                            or after[character] != fallback_id or character not in missing):
                        return False
                    changed = True
            elif key == 'stagePlacement':
                before, after = prior[key], current[key]
                if not isinstance(before, dict) or not isinstance(after, dict):
                    return False
                projected = dict(after)
                if 'runtimeMutationHooks' not in before and projected.get('runtimeMutationHooks') == []:
                    projected.pop('runtimeMutationHooks')
                    changed = True
                if before.get('unsupported') == ['stage-script'] and projected.get('unsupported') == []:
                    projected['unsupported'] = ['stage-script']
                    changed = True
                if shared.canonical(projected) != shared.canonical(before):
                    return False
            elif shared.canonical(prior[key]) != shared.canonical(current[key]):
                return False
    return changed


def song_meta_generated_upgrade(old, fresh):
    if (not isinstance(old, dict) or not isinstance(fresh, dict)
            or old.get('version') != 1 or fresh.get('version') != 1
            or old.get('song') != fresh.get('song')
            or set(old) != {'version', 'song', 'chartDifficulties', 'difficulties'}
            or set(fresh) != set(old)
            or shared.canonical(old['chartDifficulties']) != shared.canonical(fresh['chartDifficulties'])
            or set(old['difficulties']) != set(fresh['difficulties'])):
        return False
    changed = False
    for difficulty, prior in old['difficulties'].items():
        current = fresh['difficulties'][difficulty]
        if not isinstance(prior, dict) or not isinstance(current, dict):
            return False
        if set(current) != set(prior) | {'configDefaults'} or 'configDefaults' in prior:
            return False
        if current.get('configDefaults') != {}:
            return False
        projected = {key: value for key, value in current.items() if key != 'configDefaults'}
        if shared.canonical(prior) != shared.canonical(projected):
            return False
        changed = True
    return changed


def character_registry_evidence(preview, runtime, owner, names):
    evidence = []
    preview_owner, runtime_owner = preview / owner, runtime / owner
    for name in names:
        if not shared.safe_segment(name):
            raise ValueError('unsafe generated character registry key')
        script_rel = Path(CHARACTER_ATLAS_DIR) / (name + '.hscript')
        source_script, installed_script = preview_owner / script_rel, runtime_owner / script_rel
        if (not safe_file(source_script, preview) or not safe_file(installed_script, runtime)
                or source_script.read_bytes() != installed_script.read_bytes()):
            raise ValueError('generated character atlas registry upgrade lacks an identical owner implementation: ' + name)
        text = source_script.read_text(encoding='utf-8')
        if (not text.startswith('// Generated by the Codename importer from the donor character XML (')
                or "char.loadTextureAtlas(hscriptPath + 'char');" not in text):
            raise ValueError('generated character atlas registry upgrade lacks a verified importer script: ' + name)
        atlas_rel = Path(CHARACTER_ATLAS_DIR) / name / 'char'
        atlas_dir = preview_owner / atlas_rel
        if not safe_directory(atlas_dir, preview):
            raise ValueError('generated character atlas registry upgrade lacks an owner atlas: ' + name)
        files = []
        for current, dirs, filenames in os.walk(atlas_dir, followlinks=False):
            folder = Path(current)
            if not safe_directory(folder, preview):
                raise ValueError('unsafe generated character atlas: ' + name)
            if any((folder / directory).is_symlink() for directory in dirs):
                raise ValueError('symlink in generated character atlas: ' + name)
            for filename in filenames:
                source = folder / filename
                if not safe_file(source, preview):
                    raise ValueError('unsafe generated character atlas file: ' + name)
                rel = source.relative_to(preview_owner)
                target = runtime_owner / rel
                if not safe_file(target, runtime) or source.read_bytes() != target.read_bytes():
                    raise ValueError('generated character atlas is not byte-identical in installed owner: ' + name)
                files.append((source, target))
        rels = {source.relative_to(preview_owner).as_posix() for source, _ in files}
        if ('images/custom_chars/' + name + '/char/Animation.json' not in rels
                or not any(path.endswith('.png') for path in rels)
                or not any(path.endswith('.json') and not path.endswith('/Animation.json') for path in rels)):
            raise ValueError('generated character atlas evidence is incomplete: ' + name)
        evidence.append({'character': name, 'script': str(source_script),
                         'scriptSha256': digest(source_script),
                         'atlasFiles': [{'preview': str(source), 'installed': str(target),
                                         'sha256': digest(source)} for source, target in files]})
    return evidence


def verified_generated_replacement(rel, old_bytes, fresh_bytes, preview, runtime, owner,
                                   source_context=None, donor=None):
    if rel.startswith('images/custom_stages/') and rel.endswith('.hscript'):
        if stage_script_generated_upgrade(old_bytes, fresh_bytes):
            return 'codename-stage-converter-script', []
        return None, []
    if rel.startswith('songs/') and rel.endswith('/' + CAMERA_FILE):
        try:
            old_camera = read_json_bytes(old_bytes)
            fresh_camera = read_json_bytes(fresh_bytes)
            if camera_sidecar_generated_upgrade(old_camera, fresh_camera):
                return 'codename-camera-sidecar-schema', []
            source_song = rel.split('/')[1]
            native_name, evidence = owner_local_fallback_proof(
                donor, runtime, preview, owner, source_song, source_context)
            if (native_name is not None
                    and camera_sidecar_generated_upgrade(old_camera, fresh_camera, native_name)):
                return 'codename-camera-sidecar-selected-owner-fallback', evidence
            fallback_id = generated_fallback_id(preview, owner)
            if camera_sidecar_generated_upgrade(old_camera, fresh_camera, fallback_id):
                return 'codename-camera-sidecar-schema', []
        except (ValueError, TypeError, json.JSONDecodeError):
            return None, []
    if rel.startswith('songs/') and rel.endswith('/' + SONG_META_FILE):
        try:
            if song_meta_generated_upgrade(read_json_bytes(old_bytes), read_json_bytes(fresh_bytes)):
                return 'codename-song-metadata-schema', []
        except (ValueError, TypeError, json.JSONDecodeError):
            return None, []
        return None, []
    if rel == 'images/custom_chars/custom_chars.jsonc':
        try:
            enabled = registry_generated_upgrade(read_json_bytes(old_bytes), read_json_bytes(fresh_bytes))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None, []
        if enabled:
            try:
                evidence = character_registry_evidence(preview, runtime, owner, enabled)
            except ValueError as error:
                raise ValueError('owner registry conflict: unverified Animate atlas addition: '
                                 + str(error))
            return 'codename-character-atlas-registry', evidence
    return None, []


def read_json_bytes(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=lambda pairs: _unique_pairs(pairs))


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def safe_file(path, root):
    if not path.is_file() or path.is_symlink() or not shared.within(path, root):
        return False
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            return False
    return True


def safe_directory(path, root):
    if not path.is_dir() or path.is_symlink() or not shared.within(path, root):
        return False
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            return False
    return True


def namespace(donor):
    # Existing renderer calls CompatScriptManifest.destinationRoot; no Python
    # recreation of the engine's namespace hash.
    return shared.render(donor, [])['namespace']


def owner_files(preview, owner):
    base = preview / owner
    if not safe_directory(base, preview):
        raise ValueError('preview owner is absent or unsafe')
    files, total = [], 0
    for current, dirs, names in os.walk(base, followlinks=False):
        folder = Path(current)
        if not safe_directory(folder, preview):
            raise ValueError('unsafe preview owner directory')
        for name in dirs:
            if (folder / name).is_symlink():
                raise ValueError('symlink in preview owner')
        for name in names:
            path = folder / name
            if not safe_file(path, base):
                raise ValueError('unsafe preview owner file')
            total += path.stat().st_size
            files.append(path)
            if len(files) > MAX_FILES or total > MAX_BYTES:
                raise ValueError('preview owner exceeds bounded repair budget')
    return sorted(files)


def manifest_songs(root, owner):
    return {folder.name: manifest for folder, manifest in shared.selected_songs(root, owner)}


def validate_selected_owner(manifest, owner, song):
    if not isinstance(manifest, dict) or manifest.get('selectedRoot') != owner:
        raise ValueError('selected owner mismatch: ' + song)
    roots = manifest.get('roots')
    if not isinstance(roots, list) or not roots:
        raise ValueError('selected owner roots missing: ' + song)
    selected = [root for root in roots if isinstance(root, dict)
                and root.get('path') == owner and root.get('engine') == 'Codename Engine']
    if len(selected) != 1 or len(roots) != 1 or manifest.get('overlays') not in (None, []):
        raise ValueError('ambiguous selected owner manifest: ' + song)


def provenance_record(root, song, owner):
    path = root / 'assets/data' / song / 'importProvenance.json'
    if not path.exists():
        return None, None
    if not safe_file(path, root):
        raise ValueError('unsafe import provenance: ' + song)
    record = read_json(path)
    if not isinstance(record, dict) or record.get('sourceOwner') != owner:
        raise ValueError('import provenance owner mismatch: ' + song)
    if record.get('sourceEngine') not in (None, 'Codename Engine'):
        raise ValueError('import provenance engine mismatch: ' + song)
    return record, path


def validate_provenance_pair(old, fresh, song):
    # Old imports may predate importProvenance.json. When both are present,
    # identity/fingerprint values are authoritative and must match exactly.
    # The source plan and selected owner manifest still gate a legacy install.
    if old is None:
        return {'song': song, 'live': 'legacy-absent', 'preview': 'present' if fresh is not None else 'absent'}
    if fresh is None:
        raise ValueError('preview import provenance missing: ' + song)
    for key in ('sourceIdentity', 'sourceFingerprint', 'sourceFolder', 'sourceEngine', 'modName'):
        before, after = old.get(key), fresh.get(key)
        if before != after:
            raise ValueError('source provenance differs for %s field %s' % (song, key))
    return {'song': song, 'live': 'present', 'preview': 'present',
            'sourceIdentity': old.get('sourceIdentity'),
            'sourceFingerprint': old.get('sourceFingerprint')}


def make_plan(donor_root, runtime_root, generated_root, owner,
              allow_generated_replacements=False):
    donor, runtime, preview = (Path(p).resolve() for p in
                               (donor_root, runtime_root, generated_root))
    if (shared.within(runtime, donor) or shared.within(preview, donor)
            or shared.within(runtime, preview) or shared.within(preview, runtime)):
        raise ValueError('donor, installed runtime and preview must be disjoint')
    if not donor.is_dir() or not (runtime / 'assets/data').is_dir():
        raise ValueError('donor or installed chart directory is missing')
    if (not shared.within(preview, TMP) or preview == runtime
            or not (preview / 'assets/data').is_dir()):
        raise ValueError('preview must be a separate repository-local tmp runtime')
    if not isinstance(owner, str) or not owner.startswith('assets/imported_mods/'):
        raise ValueError('owner must be a selected assets/imported_mods namespace')
    parts = owner.split('/')
    if len(parts) != 3 or parts[:2] != ['assets', 'imported_mods'] or not shared.safe_segment(parts[2]):
        raise ValueError('invalid derived owner namespace')
    installed, generated = manifest_songs(runtime, owner), manifest_songs(preview, owner)
    if not installed and not generated:
        raise ValueError('selected owner mismatch: no manifests use the explicit owner')
    if not installed or set(installed) != set(generated):
        raise ValueError('selected songs differ between installed and preview')
    inputs, conflicts, candidates, replacements, source_songs = {}, [], [], [], set()
    fallback_contexts = {}
    provenance = []
    for song in sorted(installed):
        for manifest, root in ((installed[song], runtime), (generated[song], preview)):
            if not safe_file(manifest, root):
                raise ValueError('unsafe selected manifest')
            inputs[str(manifest)] = digest(manifest)
        original, fresh = read_json(installed[song]), read_json(generated[song])
        validate_selected_owner(original, owner, song)
        validate_selected_owner(fresh, owner, song)
        old_provenance, old_provenance_path = provenance_record(runtime, song, owner)
        new_provenance, new_provenance_path = provenance_record(preview, song, owner)
        provenance.append(validate_provenance_pair(old_provenance, new_provenance, song))
        for path in (old_provenance_path, new_provenance_path):
            if path is not None:
                inputs[str(path)] = digest(path)
        for root in (runtime, preview):
            chart_folder = root / 'assets/data' / song
            for chart in sorted(chart_folder.glob('*.json')):
                if chart.name == 'compatScripts.json':
                    continue
                if not safe_file(chart, root):
                    raise ValueError('unsafe native chart')
                inputs[str(chart)] = digest(chart)
        # An absent installed plan is the whole-owner repair case. If it exists,
        # verify its source identity but preserve its bytes.
        old_plan = shared.source_plan(runtime, owner, runtime / 'assets/data' / song)
        new_plan = shared.source_plan(preview, owner, preview / 'assets/data' / song)
        if new_plan is None:
            raise ValueError('preview source plan missing or ambiguous: ' + song)
        source_songs.add(new_plan[0])
        context = {'old': old_provenance, 'fresh': new_provenance}
        if new_plan[0] not in fallback_contexts:
            fallback_contexts[new_plan[0]] = context
        elif fallback_contexts[new_plan[0]] != context:
            fallback_contexts[new_plan[0]] = None
        old_plan_path = runtime / owner / 'songs' / new_plan[0] / '__cammie_compat_scripts.json'
        if old_plan is None and old_plan_path.exists():
            raise ValueError('installed source plan is unsafe or ambiguous: ' + song)
        if old_plan is not None:
            if old_plan[0] != new_plan[0] or read_json(old_plan[1]) != read_json(new_plan[1]):
                raise ValueError('installed source plan differs: ' + song)
    for source in owner_files(preview, owner):
        relative = source.relative_to(preview / owner)
        rel = relative.as_posix()
        # A preview can contain other songs from the donor. Only selected
        # installed song trees and shared owner roots belong to this repair.
        if relative.parts[0] == 'songs' and (len(relative.parts) < 3 or relative.parts[1] not in source_songs):
            continue
        target = runtime / owner / relative
        if not shared.within(target, runtime) or target.is_symlink():
            raise ValueError('unsafe installed destination')
        inputs[str(source)] = digest(source)
        if target.exists():
            if not safe_file(target, runtime):
                raise ValueError('unsafe existing installed file')
            inputs[str(target)] = digest(target)
            if target.read_bytes() == source.read_bytes():
                continue
            # Internal dependency receipts may be reformatted by a newer
            # serializer. Preserve their installed bytes when their JSON value
            # is identical; there is no runtime behavior to refresh.
            if rel == 'compat-engine-base/character-dependency.json':
                try:
                    if canonical_json(read_json(target)) == canonical_json(read_json(source)):
                        continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
            generated_kind, evidence = verified_generated_replacement(
                rel, target.read_bytes(), source.read_bytes(), preview, runtime, owner,
                source_context=(fallback_contexts.get(relative.parts[1])
                                if relative.parts[:1] == ('songs',) and len(relative.parts) > 1 else None),
                donor=donor)
            if generated_kind is not None:
                if not allow_generated_replacements:
                    conflicts.append({'path': str(target), 'reason': 'verified generated replacement requires explicit opt-in',
                                      'kind': generated_kind})
                    continue
                replacements.append({
                    'source': str(source), 'target': str(target), 'kind': generated_kind,
                    'beforeSha256': inputs[str(target)], 'afterSha256': inputs[str(source)],
                    'beforeBytes': target.stat().st_size, 'afterBytes': source.stat().st_size,
                    'evidence': evidence,
                })
                continue
            if rel in REGISTRIES:
                present, expected = read_json(target), read_json(source)
                if not isinstance(present, dict) or not isinstance(expected, dict):
                    raise ValueError('invalid owner registry')
                missing = [key for key in expected if key not in present]
                changed = [key for key in expected if key in present
                           and not registry_entry_equal(present[key], expected[key])]
                if missing or changed:
                    raise ValueError('owner registry conflict: ' + rel)
            elif rel.startswith(('images/custom_chars/', 'images/custom_stages/')):
                raise ValueError('owned implementation conflict: ' + rel)
            else:
                conflicts.append({'path': str(target), 'reason': 'existing bytes preserved'})
            continue
        for parent in target.parents:
            if parent == runtime:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError('unsafe installed parent')
        candidates.append({'source': str(source), 'target': str(target),
                           'sha256': inputs[str(source)], 'bytes': source.stat().st_size})
    tools = ('tools/repair_codename_owned_bundles.py', 'tools/refresh_codename_events.py',
             'tools/CodenameEventRefreshRender.hx', 'source/CompatScriptManifest.hx',
             'source/ModuleFunctions.hx', 'source/CodenameImporter.hx',
             'source/CodenameScriptDiscovery.hx', 'source/CodenameInstallationAssetOverlay.hx',
             'source/CodenameInstallationSoundAssets.hx', 'source/CodenameScriptPlan.hx',
             'source/CodenameStagePlacement.hx', 'source/CodenameSongMetadata.hx')
    return {'version': 3, 'generatedReplacementPolicy': GENERATED_REPLACEMENT_POLICY,
            'allowGeneratedReplacements': bool(allow_generated_replacements),
            'donorRoot': str(donor), 'runtimeRoot': str(runtime),
            'generatedRoot': str(preview), 'owner': owner, 'songs': sorted(installed),
            'sourceProvenance': provenance,
            'toolSha256': {name: digest(ROOT / name) for name in tools},
            'inputsSha256': inputs, 'candidates': candidates,
            'replacements': replacements, 'conflicts': conflicts}


def apply_plan(plan, plan_path, allow_generated_replacements=False):
    locks = []
    try:
        if plan.get('generatedReplacementPolicy') != GENERATED_REPLACEMENT_POLICY:
            raise ValueError('unsupported generated replacement policy')
        if plan.get('replacements') and not allow_generated_replacements:
            raise ValueError('generated replacements require explicit apply opt-in')
        if bool(plan.get('allowGeneratedReplacements')) != bool(allow_generated_replacements):
            raise ValueError('plan/apply generated replacement opt-in differs')
        for mode in ('0', '1'):
            lock = (LOCK_ROOT / ('runtime-' + mode + '.lock')).open('a+')
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = make_plan(plan['donorRoot'], plan['runtimeRoot'], plan['generatedRoot'], plan['owner'],
                          allow_generated_replacements=allow_generated_replacements)
        if fresh != plan:
            raise ValueError('repair inputs changed since review')
        if not plan['candidates'] and not plan['replacements']:
            return None
        receipt = TMP / 'import-refresh-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        receipt.mkdir(parents=True)
        shutil.copy2(plan_path, receipt / 'plan.json')
        created, replaced, dirs = [], [], []
        try:
            for item in plan['replacements']:
                target = Path(item['target'])
                source = Path(item['source'])
                runtime_root = Path(plan['runtimeRoot'])
                if (not safe_file(target, runtime_root) or not safe_file(source, Path(plan['generatedRoot']))
                        or digest(target) != item['beforeSha256']
                        or digest(source) != item['afterSha256']):
                    raise ValueError('replacement target/source changed during apply: ' + str(target))
                backup = receipt / 'backups' / target.relative_to(runtime_root)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                if digest(backup) != item['beforeSha256']:
                    raise ValueError('replacement backup hash mismatch: ' + str(target))
                target_stat = target.stat()
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.owner-repair-', delete=False) as out:
                    staged = Path(out.name)
                    with source.open('rb') as data:
                        shutil.copyfileobj(data, out)
                    out.flush()
                    os.fsync(out.fileno())
                try:
                    if digest(staged) != item['afterSha256']:
                        raise ValueError('staged replacement content changed: ' + str(target))
                    os.chmod(staged, target_stat.st_mode)
                    current = target.stat()
                    if (current.st_dev, current.st_ino) != (target_stat.st_dev, target_stat.st_ino) \
                            or digest(target) != item['beforeSha256']:
                        raise ValueError('replacement target changed after backup: ' + str(target))
                    os.replace(staged, target)
                    installed = target.stat()
                    replaced.append((target, backup, installed.st_dev, installed.st_ino,
                                     item['beforeSha256'], item['afterSha256']))
                finally:
                    staged.unlink(missing_ok=True)
            for item in plan['candidates']:
                target = Path(item['target'])
                pending = []
                folder = target.parent
                while not folder.exists():
                    pending.append(folder)
                    folder = folder.parent
                for folder in reversed(pending):
                    folder.mkdir()
                    dirs.append(folder)
                with tempfile.NamedTemporaryFile(dir=TMP, prefix='owner-repair-', delete=False) as out:
                    staged = Path(out.name)
                    with Path(item['source']).open('rb') as data:
                        shutil.copyfileobj(data, out)
                    out.flush()
                    os.fsync(out.fileno())
                try:
                    if digest(staged) != item['sha256']:
                        raise ValueError('staged content changed')
                    os.chmod(staged, Path(item['source']).stat().st_mode)
                    # Atomic no-clobber addition on the same filesystem.
                    os.link(staged, target)
                    installed = target.stat()
                    created.append((target, installed.st_dev, installed.st_ino))
                finally:
                    staged.unlink(missing_ok=True)
            (receipt / 'created.json').write_text(json.dumps([str(p) for p, _, _ in created], indent=2) + '\n')
            (receipt / 'replacements.json').write_text(json.dumps([
                {'target': str(path), 'backup': str(backup), 'beforeSha256': before_hash,
                 'afterSha256': after_hash, 'kind': next(row['kind'] for row in plan['replacements']
                                                         if row['target'] == str(path))}
                for path, backup, _, _, before_hash, after_hash in replaced
            ], indent=2) + '\n')
            return receipt
        except Exception:
            residual = []
            for path, device, inode in reversed(created):
                # Do not erase a file someone changed after this transaction
                # created it, even if they ignored the runtime locks.
                expected = next(item['sha256'] for item in plan['candidates']
                                if item['target'] == str(path))
                current = path.stat() if path.exists() and not path.is_symlink() else None
                if (current is not None and current.st_dev == device and current.st_ino == inode
                        and path.is_file() and digest(path) == expected):
                    path.unlink()
                elif path.exists() or path.is_symlink():
                    residual.append(str(path))
            for path, backup, device, inode, before_hash, after_hash in reversed(replaced):
                current = path.stat() if path.exists() and not path.is_symlink() else None
                if (current is not None and current.st_dev == device and current.st_ino == inode
                        and path.is_file() and digest(path) == after_hash):
                    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.owner-rollback-',
                                                     delete=False) as out:
                        staged = Path(out.name)
                        with backup.open('rb') as data:
                            shutil.copyfileobj(data, out)
                        out.flush()
                        os.fsync(out.fileno())
                    try:
                        if digest(staged) != before_hash:
                            raise ValueError('rollback backup hash mismatch: ' + str(path))
                        os.chmod(staged, backup.stat().st_mode)
                        os.replace(staged, path)
                    finally:
                        staged.unlink(missing_ok=True)
                elif path.exists() or path.is_symlink():
                    residual.append(str(path))
            for folder in reversed(dirs):
                try:
                    folder.rmdir()
                except OSError:
                    pass
            (receipt / 'rolled-back.json').write_text(json.dumps({
                'created': [str(p) for p, _, _ in created],
                'replaced': [str(p) for p, _, _, _, _, _ in replaced],
                'retainedChanged': residual
            }, indent=2) + '\n')
            raise
    finally:
        for lock in reversed(locks):
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    for field in ('donor-root', 'runtime-root', 'generated-root', 'output'):
        p.add_argument('--' + field, type=Path, required=True)
    p.add_argument('--owner', required=True,
                   help='selected assets/imported_mods namespace copied in both preview and live manifests')
    p.add_argument('--allow-generated-replacements', action='store_true',
                   help='include only schema-verified importer output replacements in this hash-bound plan')
    a = sub.add_parser('apply')
    a.add_argument('--plan', type=Path, required=True)
    a.add_argument('--allow-generated-replacements', action='store_true',
                   help='explicitly authorize replacements named by an opted-in reviewed plan')
    args = parser.parse_args()
    if args.command == 'plan':
        if args.output.exists() or not shared.within(args.output, TMP):
            parser.error('output must be a new repository-local tmp file')
        plan = make_plan(args.donor_root, args.runtime_root, args.generated_root, args.owner,
                         allow_generated_replacements=args.allow_generated_replacements)
        args.output.write_text(json.dumps(plan, indent=2) + '\n')
        print('candidates=%d replacements=%d conflicts=%d' % (
            len(plan['candidates']), len(plan['replacements']), len(plan['conflicts'])))
    else:
        receipt = apply_plan(read_json(args.plan), args.plan,
                             allow_generated_replacements=args.allow_generated_replacements)
        print('receipt: ' + str(receipt) if receipt else 'no changes')


if __name__ == '__main__':
    main()
