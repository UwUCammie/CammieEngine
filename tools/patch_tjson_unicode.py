"""Preserve Unicode strings in the pinned tolerant JSON parser on native builds."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TJSON_SOURCE = ROOT / '.haxelib/tjson/1,4,0/tjson/TJSON.hx'
SOURCE_SHA256 = 'b70d5f38130ff21bfa572d6926aee715c779ae199150f1cc10ec915949f8d928'
PATCHED_SHA256 = '907150ff0a77c137bdd9a4207c9dd881d38c243b26b545bf4cd0e0c23f5a68b9'

OLD_CHAR = '\t\t\tc = json.charAt(pos++);'
NEW_CHAR = '''\t\t\t// CammieEngine tjson-unicode: concatenate complete UTF-16 pairs.
\t\t\t// Splitting them into charAt strings loses astral characters on hxcpp.
\t\t\tvar charStart = pos++;
\t\t\tvar highUnit = json.charCodeAt(charStart);
\t\t\tvar lowUnit = pos < json.length ? json.charCodeAt(pos) : -1;
\t\t\tif (highUnit >= 0xD800 && highUnit <= 0xDBFF && lowUnit >= 0xDC00 && lowUnit <= 0xDFFF) {
\t\t\t\tc = json.substr(charStart, 2);
\t\t\t\tpos++;
\t\t\t} else c = json.charAt(charStart);'''

NEW_ESCAPE = r'''\t\t\t\t\tif(c=="u"){
\t\t\t\t\t\t// Decode standard JSON Unicode escapes together so a surrogate
\t\t\t\t\t\t// pair stays one code point, including lowercase hexadecimal.
\t\t\t\t\t\tvar escapeStart = pos - 2;
\t\t\t\t\t\tif (pos + 4 > json.length) throw "Unfinished Unicode escape";
\t\t\t\t\t\tvar high = Std.parseInt("0x" + json.substr(pos, 4));
\t\t\t\t\t\tpos += 4;
\t\t\t\t\t\tif (high != null && high >= 0xD800 && high <= 0xDBFF
\t\t\t\t\t\t\t&& json.substr(pos, 2) == "\\u" && pos + 6 <= json.length) {
\t\t\t\t\t\t\tvar low = Std.parseInt("0x" + json.substr(pos + 2, 4));
\t\t\t\t\t\t\tif (low != null && low >= 0xDC00 && low <= 0xDFFF) pos += 6;
\t\t\t\t\t\t}
\t\t\t\t\t\tsymbol += haxe.Json.parse('"' + json.substr(escapeStart, pos - escapeStart) + '"');
\t\t\t\t\t\tcontinue;
\t\t\t\t\t}'''.replace('\\t', '\t')


def patch_source(source: bytes) -> bytes:
    normalized = source.replace(b'\r\n', b'\n')
    digest = hashlib.sha256(normalized).hexdigest()
    if PATCHED_SHA256 and digest == PATCHED_SHA256:
        return source
    if digest != SOURCE_SHA256:
        raise ValueError(f'TJSON differs from pinned 1.4.0 source; refusing patch ({digest})')
    text = normalized.decode('utf-8')
    if text.count(OLD_CHAR) != 1:
        raise ValueError('Pinned TJSON character site was not unique')
    text = text.replace(OLD_CHAR, NEW_CHAR, 1)
    start = text.index('\t\t\t\t\tif(c=="u"){')
    end = text.index('\n\n\n\t\t\t\t\tthrow "Invalid escape sequence', start)
    text = text[:start] + NEW_ESCAPE + text[end:]
    patched = text.encode('utf-8')
    if PATCHED_SHA256 and hashlib.sha256(patched).hexdigest() != PATCHED_SHA256:
        raise ValueError('Patched TJSON hash did not match')
    return patched


def main() -> int:
    try:
        original = TJSON_SOURCE.read_bytes()
        patched = patch_source(original)
        if patched != original:
            TJSON_SOURCE.write_bytes(patched)
            print('>> patched TJSON Unicode string preservation')
    except (OSError, ValueError) as error:
        print(f'!! TJSON Unicode patch failed: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
