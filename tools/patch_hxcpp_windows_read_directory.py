"""Keep hxcpp Windows directory enumeration working for long paths."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS_SOURCE = ROOT / '.haxelib/hxcpp/4,3,2/src/hx/libs/std/Sys.cpp'

# This patch runs after patch_hxcpp_windows_full_path.py. Pin both the exact
# fullPath-patched input and the exact combined output so bootstrap remains
# idempotent and rejects unrelated hxcpp source changes.
SOURCE_SHA256 = '738753925e792a9da13c77939b01dc9cbd4f34a686e58542127511974e085f94'
PATCHED_SHA256 = '6c1cf02b66d59dff7777a5ff6c294349dea7ff6cbda2f594ceaf69233a025fc7'

INCLUDE_OLD = b'#include <vector>'
INCLUDE_NEW = b'#include <vector>\n#include <string>'

OLD = b'''#if defined(NEKO_WINDOWS)
   const wchar_t *path = p.wchar_str();
   size_t len = wcslen(path);
   if (len>MAX_PATH)
      return null();

   WIN32_FIND_DATAW d;
   HANDLE handle;
  #if defined(HX_WINRT) && !defined(_XBOX_ONE)
   std::wstring tempWStr(path);
   std::string searchPath(tempWStr.begin(), tempWStr.end());
  #else
   wchar_t searchPath[ MAX_PATH + 4 ];
   memcpy(searchPath,path, len*sizeof(wchar_t));
  #endif


   if( len && path[len-1] != '/' && path[len-1] != '\\\\' )
      searchPath[len++] = '/';
   searchPath[len++] = '*';
   searchPath[len++] = '.';
   searchPath[len++] = '*';
   searchPath[len] = '\\0';

   hx::EnterGCFreeZone();
  #if defined(HX_WINRT) && !defined(_XBOX_ONE)
   handle = FindFirstFileEx(searchPath.c_str(), FindExInfoStandard, &d, FindExSearchNameMatch, NULL, 0);
  #else
   handle = FindFirstFileW(searchPath,&d);
  #endif
   if( handle == INVALID_HANDLE_VALUE )
   {
      hx::ExitGCFreeZone();
      return null();
   }
   while( true )
   {
      // skip magic dirs
      if( d.cFileName[0] != '.' || (d.cFileName[1] != 0 && (d.cFileName[1] != '.' || d.cFileName[2] != 0)) )
      {
         hx::ExitGCFreeZone();
         result->push(String::create(d.cFileName));
         hx::EnterGCFreeZone();
      }
      if( !FindNextFileW(handle,&d) )
         break;
   }
   FindClose(handle);
#elif !defined(EPPC)'''

NEW = b'''#if defined(NEKO_WINDOWS)
   WIN32_FIND_DATAW d;
   HANDLE handle;
  #if defined(HX_WINRT) && !defined(_XBOX_ONE)
   // Keep the WinRT enumeration API and path handling isolated from desktop
   // Win32. Its platform API still has a MAX_PATH input limit.
   const wchar_t *path = p.wchar_str();
   size_t len = wcslen(path);
   if (len > MAX_PATH)
      hx::Throw(HX_CSTRING("Invalid directory"));
   std::wstring tempWStr(path);
   std::string searchPath(tempWStr.begin(), tempWStr.end());
   if (len && path[len-1] != '/' && path[len-1] != '\\\\')
      searchPath += '/';
   searchPath += "*.*";
  #else
   hx::strbuf pathBuffer;
   std::wstring searchPath(p.wchar_str(&pathBuffer));
   for (size_t i = 0; i < searchPath.size(); ++i)
      if (searchPath[i] == L'/') searchPath[i] = L'\\\\';

   const bool extendedPath = searchPath.compare(0, 4, L"\\\\\\\\?\\\\") == 0;
   const bool devicePath = searchPath.compare(0, 4, L"\\\\\\\\.\\\\") == 0;
   const bool driveAbsolute = searchPath.size() >= 3 &&
      ((searchPath[0] >= L'A' && searchPath[0] <= L'Z') ||
       (searchPath[0] >= L'a' && searchPath[0] <= L'z')) &&
      searchPath[1] == L':' && searchPath[2] == L'\\\\';
   const bool uncAbsolute = !extendedPath && !devicePath &&
      searchPath.compare(0, 2, L"\\\\\\\\") == 0;

   // Resolve relative paths with a query-then-grow buffer. Absolute long paths
   // skip this API because older Windows versions limit GetFullPathNameW too.
   if (!extendedPath && !devicePath && !driveAbsolute && !uncAbsolute)
   {
      hx::strbuf inputBuffer;
      const wchar_t *input = p.wchar_str(&inputBuffer);
      DWORD capacity = GetFullPathNameW(input, 0, NULL, NULL);
      if (capacity == 0)
         hx::Throw(HX_CSTRING("Invalid directory"));
      std::vector<wchar_t> fullPathBuffer(capacity);
      for (;;)
      {
         DWORD length = GetFullPathNameW(input, capacity, fullPathBuffer.data(), NULL);
         if (length == 0)
            hx::Throw(HX_CSTRING("Invalid directory"));
         if (length < capacity)
         {
            searchPath.assign(fullPathBuffer.data(), length);
            break;
         }
         capacity = length + 1;
         fullPathBuffer.resize(capacity);
      }
      for (size_t i = 0; i < searchPath.size(); ++i)
         if (searchPath[i] == L'/') searchPath[i] = L'\\\\';
   }

   // The extended prefix disables Win32's legacy MAX_PATH parsing. Convert
   // UNC paths to the required \\\\?\\UNC\\server form.
   if (!extendedPath && !devicePath && searchPath.size() + 4 >= MAX_PATH)
   {
      if (searchPath.compare(0, 2, L"\\\\\\\\") == 0)
         searchPath = L"\\\\\\\\?\\\\UNC\\\\" + searchPath.substr(2);
      else if (searchPath.size() >= 3 && searchPath[1] == L':' && searchPath[2] == L'\\\\')
         searchPath = L"\\\\\\\\?\\\\" + searchPath;
      else
         hx::Throw(HX_CSTRING("Invalid directory"));
   }

   if (!searchPath.empty() && searchPath[searchPath.size()-1] != L'\\\\')
      searchPath += L'\\\\';
   searchPath += L"*.*";
  #endif

   hx::EnterGCFreeZone();
  #if defined(HX_WINRT) && !defined(_XBOX_ONE)
   handle = FindFirstFileEx(searchPath.c_str(), FindExInfoStandard, &d, FindExSearchNameMatch, NULL, 0);
  #else
   handle = FindFirstFileW(searchPath.c_str(), &d);
  #endif
   if (handle == INVALID_HANDLE_VALUE)
   {
      hx::ExitGCFreeZone();
      hx::Throw(HX_CSTRING("Invalid directory"));
   }
   while (true)
   {
      // skip magic dirs
      if (d.cFileName[0] != '.' || (d.cFileName[1] != 0 && (d.cFileName[1] != '.' || d.cFileName[2] != 0)))
      {
         hx::ExitGCFreeZone();
         result->push(String::create(d.cFileName));
         hx::EnterGCFreeZone();
      }
      if (!FindNextFileW(handle, &d))
      {
         if (GetLastError() != ERROR_NO_MORE_FILES)
         {
            FindClose(handle);
            hx::ExitGCFreeZone();
            hx::Throw(HX_CSTRING("Invalid directory"));
         }
         break;
      }
   }
   FindClose(handle);
#elif !defined(EPPC)'''


def _digest(patched: bytes) -> str:
    return hashlib.sha256(patched).hexdigest()


FILE_PATHS_PATCHED_SHA256 = 'c612fdc5a7b84a80981e864a529fcaf0560f9a1cf42483b2efb84ed6162dee1c'


def patch_source(source: bytes) -> bytes:
    normalized = source.replace(b'\r\n', b'\n')
    digest = hashlib.sha256(normalized).hexdigest()
    if digest in (PATCHED_SHA256, FILE_PATHS_PATCHED_SHA256):
        return source
    if digest != SOURCE_SHA256:
        raise ValueError(f'hxcpp Sys.cpp differs from pinned fullPath-patched 4.3.2 source; refusing patch ({digest})')
    if normalized.count(INCLUDE_OLD) != 1 or normalized.count(OLD) != 1:
        raise ValueError('Pinned Windows readDirectory sites were not unique')
    patched = normalized.replace(INCLUDE_OLD, INCLUDE_NEW, 1)
    patched = patched.replace(OLD, NEW, 1)
    if _digest(patched) != PATCHED_SHA256:
        raise ValueError('Patched hxcpp Windows readDirectory hash did not match')
    return patched


def main() -> int:
    try:
        original = SYS_SOURCE.read_bytes()
        patched = patch_source(original)
        if patched != original:
            SYS_SOURCE.write_bytes(patched)
            print('>> patched Windows readDirectory long-path handling')
    except (OSError, ValueError) as error:
        print(f'!! Windows readDirectory patch failed: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
