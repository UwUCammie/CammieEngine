#!/usr/bin/env python3
"""
Validate the ported freeplay library against DisappointingPlus's ACTUAL
runtime resolution rules (read straight from the Haxe source):

  FreeplayState:  every listed song's `character` must be a custom_chars.jsonc
                  key with a `colors` array (Reflect.field(...).colors is read
                  unguarded on selection).
  HealthIcon:     character must resolve in custom_chars.jsonc or
                  icon_only_chars.json (else switchAnim null-derefs).
  DifficultyManager: a difficulty is offered iff
                  assets/data/<song>/<song>-<diff>.json exists (diff list from
                  custom_difficulties/difficulties.json).
  PlayState/CoolUtil.getSongFile: audio resolves as
                  assets/songs/<song>/<song>_Inst.ogg,
                  assets/songs/<song>/Inst.ogg, or
                  assets/music/<song>_Inst.ogg  (CASE-SENSITIVE, <song> = the
                  chart's `song` field).
  Note:           uiType must be a key of custom_ui/ui_packs/ui.json (curUiType
                  is dereferenced when notes spawn); custom directions
                  (>=10 * key count) need noteInfo.json. Event rows are
                  consumed by the engine's event pump.
  Character:      missing registry/folder/implementation is an import error;
                  the runtime fallback does not restore the intended character.

Exit code 1 if any ERROR found. Warnings don't fail the build.
"""
import json, os, re, sys
from collections import Counter
from character_dependencies import character_problems

TGT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AT = lambda *p: os.path.join(TGT, 'assets', *p)

def freeplay_registry_path():
    """Mirror FreeplayRegistry's JSONC-first, JSON-only-safe resolution."""
    candidates = (
        AT('data', 'freeplaySongJson.jsonc'),
        AT('data', 'freeplaySongJson.json'),
        AT('images', 'freeplaySongJson.jsonc'),
        AT('images', 'freeplaySongJson.json'),
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]

def rj(p):
    s = open(p, encoding='utf-8', errors='replace').read()
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//[^\n]*', '', s)
    s = re.sub(r',\s*([}\]])', r'\1', s)
    s = re.sub(r'([}\]\d"])\s*\n(\s*"[^"]+"\s*:)', r'\1,\n\2', s)
    s = re.sub(r'([}\]\d"])\s*\n(\s*\{)', r'\1,\n\2', s)
    s = re.sub(r',\s*,', ',', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        if e.msg == 'Extra data':
            return json.JSONDecoder().raw_decode(s)[0]
        raise

errors, warnings = [], []
err = lambda s: errors.append(s)
warn = lambda s: warnings.append(s)

fp = rj(freeplay_registry_path())
chars = rj(AT('images', 'custom_chars', 'custom_chars.jsonc'))
icons = rj(AT('images', 'custom_chars', 'icon_only_chars.json'))
ui = rj(AT('images', 'custom_ui', 'ui_packs', 'ui.json'))
# Registration alone is insufficient: notes and receptors load these files
# unconditionally. Audit every pack, including ones selected by modcharts.
for name, pack in ui.items():
    folder = AT('images', 'custom_ui', 'ui_packs', pack['uses'])
    required = ['NOTE_assets.png', 'NOTE_assets.xml']
    if pack.get('isPixel'):
        required = ['arrows-pixels.png']
        if not os.path.isfile(os.path.join(folder, 'arrows-pixels.xml')):
            required.append('arrowEnds.png')
    splash = 'noteSplashes-pixel' if pack.get('isPixel') else 'noteSplashes'
    # NoteSplash selects a custom atlas by PNG existence, then reads its XML.
    if os.path.isfile(os.path.join(folder, splash + '.png')):
        required.append(splash + '.xml')
    for filename in required:
        path = os.path.join(folder, filename)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            err(f'UI pack {name!r}: missing or empty {os.path.relpath(path, TGT)} (Note/Strumline load crash)')
diffs = rj(AT('images', 'custom_difficulties', 'difficulties.json'))['difficulties']
diff_names = [d['name'] for d in diffs]
default_diff = diffs.index(next(d for d in diffs if d['name'] == 'normal'))

stats = Counter()
seen = set()
# windows/wine runtime is case-insensitive; index the data dir lower->actual
data_dirs = {e.lower(): e for e in os.listdir(AT('data')) if os.path.isdir(AT('data', e))}
data_files = {}
for lk, act in data_dirs.items():
    data_files[lk] = {f.lower(): f for f in os.listdir(AT('data', act))}
for cat in fp:
    for s in cat['songs']:
        if isinstance(s, str):
            name, char = s, 'face'
        else:
            name, char = s['name'], s.get('character', 'face')
        if name in seen or name == 'Random-Song':
            continue
        seen.add(name)
        key = name.lower()

        # freeplay character: charJson entry WITH colors
        e = chars.get(char)
        if e is None:
            err(f'{name}: freeplay character {char!r} missing from custom_chars.jsonc (crash on select)')
        elif not isinstance(e.get('colors'), list):
            err(f'{name}: character {char!r} has no colors array (crash on select)')
        elif char not in icons and not os.path.isdir(AT('images', 'custom_chars', char)):
            warn(f'{name}: character {char!r} has no folder (icon falls back to iconGrid)')
        # icon chain
        ie = icons.get(char)
        if isinstance(ie, dict) and isinstance(ie.get('icons'), str):
            tgt = ie['icons']
            if tgt not in chars and tgt not in icons:
                err(f'{name}: icon_only {char!r} points at missing icon {tgt!r}')

        if key not in data_dirs:
            err(f'{name}: no chart folder')
            continue
        ddir = AT('data', data_dirs[key])
        dfiles = data_files[key]
        def chart_for(d):
            suffix = '' if diff_names.index(d) == default_diff else '-' + d
            want = (key + suffix + '.json').lower()
            return want in dfiles
        found = [d for d in diff_names if chart_for(d)]
        if not found:
            err(f'{name}: no difficulty chart visible to the engine')
            continue

        for d in found:
            suffix = '' if diff_names.index(d) == default_diff else '-' + d
            p = os.path.join(ddir, data_files[key][(key + suffix + '.json').lower()])
            try:
                raw = open(p, encoding='utf-8', errors='replace').read()
                dec = json.JSONDecoder()
                ch = dec.raw_decode(re.sub(r'//[^\n]*', '', raw))[0]['song']
            except Exception as ex:
                err(f'{name}{suffix}: chart unparseable even leniently: {ex}')
                continue
            sf = ch.get('song')
            stats['charts'] += 1
            # audio: the three paths getSongFile tries, in order (case-sensitive)
            def songfile(songtype):
                # exactly what CoolUtil.getSongFile does, CASE-SENSITIVE -
                # this build runs on linux where a case mismatch is a crash
                for cand in (
                    AT('songs', sf, f'{sf}_{songtype}.ogg'),
                    AT('songs', sf, f'{songtype}.ogg'),
                    AT('music', f'{sf}_{songtype}.ogg'),
                ):
                    if os.path.exists(cand):
                        return cand
                return None
            if songfile('Inst') is None:
                err(f'{name}{suffix}: no Inst resolves for song field {sf!r}')
            if ch.get('needsVoices'):
                # V-Slice imports may intentionally omit the legacy Voices.ogg
                # alias. PlayState resolves each destination basename from the
                # chart's vocalStems metadata, so validate every copied stem
                # before falling back to the old single-Voices lookup.
                stems = ch.get('vocalStems')
                if isinstance(stems, list) and stems:
                    for index, stem in enumerate(stems):
                        if isinstance(stem, str):
                            raw_stem = stem
                        elif isinstance(stem, dict):
                            raw_stem = stem.get('file') or stem.get('path')
                        else:
                            raw_stem = None
                        if not isinstance(raw_stem, str) or not raw_stem.strip():
                            err(f'{name}{suffix}: vocalStems[{index}] has no destination file')
                            continue
                        normalized_stem = raw_stem.replace('\\', '/')
                        if normalized_stem.lower().startswith('assets/'):
                            stem_path = os.path.join(TGT, normalized_stem)
                        else:
                            # PlayState intentionally strips any authored
                            # directory before joining the destination song.
                            stem_path = AT('songs', sf, os.path.basename(normalized_stem))
                        if not os.path.isfile(stem_path):
                            err(f'{name}{suffix}: vocal stem {raw_stem!r} does not resolve for {sf!r}')
                        else:
                            stats['vocal_stems'] += 1
                elif songfile('Voices') is None:
                    err(f'{name}{suffix}: needsVoices but no Voices resolves for {sf!r}')
            for f in ('player1', 'player2', 'gf'):
                v = ch.get(f)
                if isinstance(v, str) and v.strip():
                    character = v.strip()
                    if character.endswith('-dead'):
                        character = character[:-5]
                    missing = character_problems(AT(), chars, character)
                    if missing:
                        err(f'{name}{suffix}: {f}={v!r}: {", ".join(missing)} (incomplete character import; fallback is not the requested character)')
            v = ch.get('uiType')
            if isinstance(v, str) and v.strip() and v not in ui:
                err(f'{name}{suffix}: uiType {v!r} not in ui.json (Note spawn crash)')
            v = ch.get('stage')
            if isinstance(v, str) and v.strip() and v not in rj(AT('images', 'custom_stages', 'custom_stages.json')):
                warn(f'{name}{suffix}: stage {v!r} unknown (default stage used)')
            layout = ch.get('forceLayout')
            if layout is None:
                layout = ch.get('uiLayoutType') or 'none'
                if layout == 'normal':
                    layout = 'none'
            if layout != 'none' and not os.path.isfile(AT('images', 'custom_ui', 'ui_layouts', layout + '.hscript')):
                err(f'{name}{suffix}: required UI layout {layout!r} is missing')
            has_noteinfo = os.path.exists(os.path.join(ddir, 'noteInfo.json'))
            ev = special = 0
            key_count = ch.get('preferredNoteAmount') or {1: 6, 2: 9}.get(ch.get('mania'), 4)
            for sec in ch['notes']:
                if not isinstance(sec, dict):
                    err(f'{name}{suffix}: non-dict section in notes ({sec!r}) - engine crash')
                    continue
                for n in (sec.get('sectionNotes') or []):
                    if isinstance(n, list) and len(n) >= 2 and n[1] == -1:
                        ev += 1
                    if isinstance(n, list) and len(n) >= 2 and isinstance(n[1], int) and n[1] >= key_count * 10:
                        special += 1
            if ev:
                stats['events_supported'] += ev  # engine consumes these via its event pump now
            if special and not has_noteinfo:
                err(f'{name}{suffix}: {special} custom notes without noteInfo.json (silently lose their appearance and behavior)')

# every chart json parses at least leniently (like TJSON does)
bad_json = 0
for root, dirs, files in os.walk(AT('data')):
    if os.path.basename(root) == 'random-song':
        continue  # engine placeholder, never actually chart-loaded
    for f in files:
        if f.endswith('.json') and not f.endswith('.bak') and f.lower() not in ('noteinfo.json', 'credits.json', 'portcredits.json'):
            try:
                dec = json.JSONDecoder()
                dec.raw_decode(re.sub(r'//[^\n]*', '', open(os.path.join(root, f), encoding='utf-8', errors='replace').read()))
            except Exception:
                bad_json += 1
                err(f'unparseable chart json: {os.path.relpath(os.path.join(root, f), AT("data"))}')

# stage/char/cutscene hscripts: currentPlayState.<field> must exist on PlayState
# (hscript throws "Invalid field" mid-hook and silently kills the rest of that
# hook - e.g. one bad line in stage.start() skips ALL remaining stage setup)
PS_MEMBERS = set()
for src in ('PlayState.hx', 'MusicBeatState.hx'):
    sp = os.path.join(TGT, 'source', src)
    if os.path.exists(sp):
        code = open(sp, encoding='utf-8', errors='replace').read()
        PS_MEMBERS.update(re.findall(r'\bvar\s+(\w+)\s*(?:\(|[:=;])', code))
        PS_MEMBERS.update(re.findall(r'\bfunction\s+(\w+)', code))
# FlxState/FlxBasic/FlxTypedGroup inherited members scripts commonly touch
PS_MEMBERS.update(('add', 'remove', 'clear', 'insert', 'members', 'camera',
                   'width', 'height', 'visible', 'exists', 'forEach', 'kill',
                   'revive', 'scrollFactor', 'cameras', 'length'))
# compat get,never properties on PlayState - assigning them throws at runtime
PS_READONLY = {'stepCrochet'}
for sub in ('custom_stages', 'custom_chars', 'custom_cutscenes', 'custom_ui/ui_layouts'):
    d = AT('images', sub)
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        if not f.endswith(('.hscript', '.hxs')):
            continue
        txt = open(os.path.join(d, f), encoding='utf-8', errors='replace').read()
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
        txt = re.sub(r'//[^\n]*', '', txt)
        for m in re.finditer(r'currentPlayState\.(\w+)', txt):
            fld = m.group(1)
            if fld not in PS_MEMBERS:
                ln = txt[:m.start()].count('\n') + 1
                err(f'hscript {sub}/{f}:{ln}: currentPlayState.{fld} is not a '
                    f'PlayState member (Invalid field - kills the rest of the hook)')
            elif fld in PS_READONLY and re.search(
                    r'currentPlayState\.' + fld + r'\s*(?:[-+*/]?=(?!=))', txt):
                err(f'hscript {sub}/{f}: currentPlayState.{fld} is read-only '
                    f'(compat property)')

# same sweep for SONG modcharts in assets/data (their onEvent/stepHit hooks
# die mid-hook exactly like stage hooks - control's whole choreography lived
# behind a missing triggerEventNote this way)
for root, dirs, files in os.walk(AT('data')):
    for f in sorted(files):
        if not f.startswith('modchart') or not f.endswith(('.hscript', '.hxs')):
            continue
        p = os.path.join(root, f)
        txt = open(p, encoding='utf-8', errors='replace').read()
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
        txt = re.sub(r'//[^\n]*', '', txt)
        for m in re.finditer(r'currentPlayState\.(\w+)', txt):
            fld = m.group(1)
            if fld not in PS_MEMBERS:
                ln = txt[:m.start()].count('\n') + 1
                err(f'modchart {os.path.relpath(p, AT("data"))}:{ln}: '
                    f'currentPlayState.{fld} is not a PlayState member '
                    f'(Invalid field - kills the rest of the hook)')
            elif fld in PS_READONLY and re.search(
                    r'currentPlayState\.' + fld + r'\s*(?:[-+*/]?=(?!=))', txt):
                err(f'modchart {os.path.relpath(p, AT("data"))}: '
                    f'currentPlayState.{fld} is read-only (compat property)')

print(f'songs checked : {len(seen)}')
print(f'charts checked: {stats["charts"]}')
print(f'ERRORS        : {len(errors)}')
for e in errors[:60]:
    print('  [ERR]', e)
print(f'warnings      : {len(warnings)}')
for w in warnings[:25]:
    print('  [warn]', w)
if bad_json:
    print(f'  ({bad_json} of them non-strict json files)')
open('/tmp/validate_report.txt', 'w').write('\n'.join(['ERRORS:'] + errors + ['', 'WARNINGS:'] + warnings))
sys.exit(1 if errors else 0)
