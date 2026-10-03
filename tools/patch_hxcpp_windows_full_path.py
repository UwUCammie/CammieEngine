"""Keep Windows filesystem fullPath from returning truncated long paths."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS_SOURCE = ROOT / '.haxelib/hxcpp/4,3,2/src/hx/libs/std/Sys.cpp'
SOURCE_SHA256 = 'a564165f28d9dc5f8a0bc04cb6dfd782c20ffa1d2a2ff950d3d9f41ff731fd0c'
PATCHED_SHA256 = '738753925e792a9da13c77939b01dc9cbd4f34a686e58542127511974e085f94'
# Also accept the exact output of the subsequent pinned readDirectory patch.
READ_DIRECTORY_PATCHED_SHA256 = '6c1cf02b66d59dff7777a5ff6c294349dea7ff6cbda2f594ceaf69233a025fc7'
OLD = b'''   wchar_t buf[MAX_PATH+1];
   hx::strbuf wbuf;
   if( GetFullPathNameW(path.wchar_str(&wbuf),MAX_PATH+1,buf,NULL) == 0 )
      return null();
   return String::create(buf);'''
NEW = b'''   // CammieEngine windows-full-path: a too-small buffer returns the
   // required length, not zero. Never treat its contents as a complete path.
   hx::strbuf wbuf;
   const wchar_t *input = path.wchar_str(&wbuf);
   DWORD capacity = GetFullPathNameW(input,0,NULL,NULL);
   if (capacity == 0) return null();
   std::vector<wchar_t> buffer(capacity);
   for (;;) {
      DWORD length = GetFullPathNameW(input,capacity,buffer.data(),NULL);
      if (length == 0) return null();
      if (length < capacity) return String::create(buffer.data());
      capacity = length + 1;
      buffer.resize(capacity);
   }'''


FILE_PATHS_PATCHED_SHA256 = 'c612fdc5a7b84a80981e864a529fcaf0560f9a1cf42483b2efb84ed6162dee1c'


def patch_source(source: bytes) -> bytes:
    normalized = source.replace(b'\r\n', b'\n')
    digest = hashlib.sha256(normalized).hexdigest()
    if digest in (PATCHED_SHA256, READ_DIRECTORY_PATCHED_SHA256, FILE_PATHS_PATCHED_SHA256):
        return source
    if digest != SOURCE_SHA256:
        raise ValueError(f'hxcpp Sys.cpp differs from pinned 4.3.2 source; refusing patch ({digest})')
    if normalized.count(OLD) != 1:
        raise ValueError('Pinned Windows fullPath site was not unique')
    patched = normalized.replace(b'#include <time.h>', b'#include <time.h>\n#include <vector>', 1)
    patched = patched.replace(OLD, NEW, 1)
    if PATCHED_SHA256 and hashlib.sha256(patched).hexdigest() != PATCHED_SHA256:
        raise ValueError('Patched hxcpp Windows fullPath hash did not match')
    return patched


def main() -> int:
    try:
        original = SYS_SOURCE.read_bytes()
        patched = patch_source(original)
        if patched != original:
            SYS_SOURCE.write_bytes(patched)
            print('>> patched Windows fullPath buffer sizing')
    except (OSError, ValueError) as error:
        print(f'!! Windows fullPath patch failed: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
