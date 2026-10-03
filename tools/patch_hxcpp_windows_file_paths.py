"""Use extended Unicode Windows paths in hxcpp's CRT filesystem calls."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT / '.haxelib/hxcpp/4,3,2/src/hx/libs/std'
SYS_SOURCE_SHA256 = '6c1cf02b66d59dff7777a5ff6c294349dea7ff6cbda2f594ceaf69233a025fc7'
SYS_PATCHED_SHA256 = 'c612fdc5a7b84a80981e864a529fcaf0560f9a1cf42483b2efb84ed6162dee1c'
FILE_SOURCE_SHA256 = '263403494c41fad713df0631e06325b3ab642bc8f800864c49ea6dff2280167a'
FILE_PATCHED_SHA256 = '6410a7ea79c58da2170d42c9a670b579bacea510865344c15c216c6d0dd40fe7'

HELPER = r'''
#ifdef NEKO_WINDOWS
// CammieEngine windows-file-paths: the CRT still applies MAX_PATH even when
// enumeration succeeds. Keep public Haxe paths unchanged; extend API inputs.
std::wstring hx_cammie_windows_path(String path)
{
   hx::strbuf buffer;
   std::wstring result(path.wchar_str(&buffer));
   for (size_t i = 0; i < result.size(); ++i)
      if (result[i] == L'/') result[i] = L'\\';
   if (result.compare(0, 4, L"\\\\?\\") == 0 || result.compare(0, 4, L"\\\\.\\") == 0)
      return result;
   DWORD capacity = GetFullPathNameW(result.c_str(), 0, NULL, NULL);
   if (capacity == 0) return result;
   std::vector<wchar_t> absolute(capacity);
   for (;;) {
      DWORD length = GetFullPathNameW(result.c_str(), capacity, absolute.data(), NULL);
      if (length == 0) return result;
      if (length < capacity) {
         result.assign(absolute.data(), length);
         break;
      }
      capacity = length + 1;
      absolute.resize(capacity);
   }
   if (result.compare(0, 2, L"\\\\") == 0)
      return L"\\\\?\\UNC\\" + result.substr(2);
   if (result.size() >= 3 && result[1] == L':' && result[2] == L'\\')
      return L"\\\\?\\" + result;
   return result;
}
#endif
'''.encode()

STAT_OLD = b'''      #if defined(HX_SMART_STRINGS)
      if (path.isUTF16Encoded())
      {
         hx::strbuf buf;
         err = _wstat(path.wchar_str(&buf),&s);
      }
      else
      #endif
      {
         hx::strbuf buf;
         err = _stat(path.utf8_str(&buf),&s);
      }'''
STAT_NEW = b'''      std::wstring nativePath = hx_cammie_windows_path(path);
      err = _wstat(nativePath.c_str(),&s);'''

SYS_REPLACEMENTS = [
    (b'/**\n   sys_exists', HELPER + b'\n/**\n   sys_exists', 1),
    (b'const wchar_t * wpath = path.wchar_str();',
     b'std::wstring nativePath = hx_cammie_windows_path(path);\n   const wchar_t * wpath = nativePath.c_str();', 2),
    (STAT_OLD, STAT_NEW, 2),
    (b'bool err = _wrename(path.wchar_str(&buf0),newname.wchar_str(&buf1));',
     b'bool err = _wrename(hx_cammie_windows_path(path).c_str(),hx_cammie_windows_path(newname).c_str());', 1),
    (b'''   #if defined(NEKO_WINDOWS) && defined(HX_SMART_STRINGS)
   if (path.isUTF16Encoded())
      err = _wunlink(path.wchar_str());
   else
   #endif''', b'''   #if defined(NEKO_WINDOWS)
      err = _wunlink(hx_cammie_windows_path(path).c_str());
   #else''', 1),
    (b'''      err = unlink(path.utf8_str(&buf));
   }''', b'''      err = unlink(path.utf8_str(&buf));
   }
   #endif''', 1),
    (b'''   #if defined(NEKO_WINDOWS) && defined(HX_SMART_STRINGS)
   if (path.isUTF16Encoded())
   {
      ok = _wrmdir(path.wchar_str()) == 0;
   }
   else
   #endif''', b'''   #if defined(NEKO_WINDOWS)
      ok = _wrmdir(hx_cammie_windows_path(path).c_str()) == 0;
   #else''', 1),
    (b'''      ok = rmdir(path.utf8_str(&buf)) == 0;
   }''', b'''      ok = rmdir(path.utf8_str(&buf)) == 0;
   }
   #endif''', 1),
]
FILE_REPLACEMENTS = [
    (b'#   include <windows.h>', b'#   include <windows.h>\n#   include <string>\nstd::wstring hx_cammie_windows_path(String path);', 1),
    (b'_wfopen(fname.wchar_str(&buf0),r.wchar_str(&buf1))',
     b'_wfopen(hx_cammie_windows_path(fname).c_str(),r.wchar_str(&buf1))', 1),
    (b'_wfopen(name.wchar_str(&buf), L"rb")',
     b'_wfopen(hx_cammie_windows_path(name).c_str(), L"rb")', 2),
]


def transform(source: bytes, replacements, *, reverse=False) -> bytes:
    result = source.replace(b'\r\n', b'\n')
    for old, new, count in reversed(replacements) if reverse else replacements:
        before, after = (new, old) if reverse else (old, new)
        if result.count(before) != count:
            raise ValueError('Pinned Windows file path patch site was not unique')
        result = result.replace(before, after)
    return result


def patch_source(source: bytes, *, file=False) -> bytes:
    expected, patched = (FILE_SOURCE_SHA256, FILE_PATCHED_SHA256) if file else (SYS_SOURCE_SHA256, SYS_PATCHED_SHA256)
    digest = hashlib.sha256(source.replace(b'\r\n', b'\n')).hexdigest()
    if digest == patched:
        return source
    if digest != expected:
        raise ValueError(f'hxcpp differs from pinned Windows path source ({digest})')
    result = transform(source, FILE_REPLACEMENTS if file else SYS_REPLACEMENTS)
    if hashlib.sha256(result).hexdigest() != patched:
        raise ValueError('Patched Windows file path hash did not match')
    return result


def unpatch_sys_source(source: bytes) -> bytes:
    if hashlib.sha256(source.replace(b'\r\n', b'\n')).hexdigest() == SYS_PATCHED_SHA256:
        return transform(source, SYS_REPLACEMENTS, reverse=True)
    return source


def main() -> int:
    try:
        for name in ('Sys.cpp', 'File.cpp'):
            path = STD / name
            original = path.read_bytes()
            patched = patch_source(original, file=name == 'File.cpp')
            if patched != original:
                path.write_bytes(patched)
                print(f'>> patched Windows long file paths in {name}')
    except (OSError, ValueError) as error:
        print(f'!! Windows file path patch failed: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
