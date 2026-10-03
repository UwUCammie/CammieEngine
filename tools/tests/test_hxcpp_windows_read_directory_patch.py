"""Pin and native-mock the hxcpp Windows long-path directory patch."""

import hashlib
import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "patch_hxcpp_windows_read_directory",
    ROOT / "tools/patch_hxcpp_windows_read_directory.py",
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


CPP_TEMPLATE = r'''#include <algorithm>
#include <cstdint>
#include <cwchar>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#define NEKO_WINDOWS 1
#define MAX_PATH 260
#define HX_CSTRING(value) value
#define ERROR_NO_MORE_FILES 18

using DWORD = uint32_t;
using HANDLE = intptr_t;
static const HANDLE INVALID_HANDLE_VALUE = static_cast<HANDLE>(-1);
static const int FindExInfoStandard = 0;
static const int FindExSearchNameMatch = 0;
struct WIN32_FIND_DATAW { wchar_t cFileName[64]; };

namespace hx {
struct strbuf {};
static int gcDepth = 0;
inline void EnterGCFreeZone() { ++gcDepth; }
inline void ExitGCFreeZone() { --gcDepth; }
[[noreturn]] inline void Throw(const char *message) { throw std::runtime_error(message); }
}

struct String {
  std::wstring value;
  bool isNull;
  String() : isNull(false) {}
  const wchar_t *wchar_str(hx::strbuf * = nullptr) const { return value.c_str(); }
  static String create(const wchar_t *text) {
    String result;
    result.value = text;
    return result;
  }
};

template<class T> struct ArrayStorage {
  std::vector<T> values;
  void push(T value) { values.push_back(value); }
};
template<class T> using Array = ArrayStorage<T> *;
template<class T> struct Array_obj {
  static Array<T> __new() { return new ArrayStorage<T>(); }
};

static std::wstring lastSearchPath;
static std::wstring resolvedPath;
static std::wstring growToPath;
static int fullPathCalls = 0;
static int findCalls = 0;
static int findNextIndex = 0;
static bool growAfterQuery = false;
static bool failFullPath = false;
static bool failFind = false;
static bool failFindNext = false;
static DWORD lastError = ERROR_NO_MORE_FILES;
static int closeCalls = 0;

inline DWORD GetFullPathNameW(const wchar_t *input, DWORD capacity,
  wchar_t *buffer, wchar_t **) {
  ++fullPathCalls;
  if (failFullPath || std::wstring(input) != L"relative\\folder") return 0;
  if (capacity == 0) return static_cast<DWORD>(resolvedPath.size() + 1);
  if (growAfterQuery && fullPathCalls == 2) {
    resolvedPath = growToPath;
    growAfterQuery = false;
  }
  const DWORD required = static_cast<DWORD>(resolvedPath.size() + 1);
  if (capacity < required) return required;
  std::copy(resolvedPath.begin(), resolvedPath.end(), buffer);
  buffer[resolvedPath.size()] = L'\0';
  return static_cast<DWORD>(resolvedPath.size());
}

static void setName(WIN32_FIND_DATAW *data, const wchar_t *name) {
  std::wcsncpy(data->cFileName, name, 63);
  data->cFileName[63] = L'\0';
}

static HANDLE startFind(const std::wstring &path, WIN32_FIND_DATAW *data) {
  ++findCalls;
  lastSearchPath = path;
  findNextIndex = 0;
  lastError = ERROR_NO_MORE_FILES;
  if (failFind) return INVALID_HANDLE_VALUE;
  setName(data, L".");
  return 1;
}

inline HANDLE FindFirstFileW(const wchar_t *path, WIN32_FIND_DATAW *data) {
  return startFind(path, data);
}

static std::wstring widenAscii(const char *text) {
  std::wstring result;
  while (*text) result.push_back(static_cast<unsigned char>(*text++));
  return result;
}

inline HANDLE FindFirstFileEx(const char *path, int, WIN32_FIND_DATAW *data,
  int, void *, int) {
  return startFind(widenAscii(path), data);
}

static bool FindNextFileW(HANDLE, WIN32_FIND_DATAW *data) {
  static const wchar_t *names[] = {L"first.txt", L"..", L"second"};
  if (failFindNext) {
    lastError = 5;
    return false;
  }
  if (findNextIndex >= 3) return false;
  setName(data, names[findNextIndex++]);
  return true;
}

static DWORD GetLastError() { return lastError; }
static bool FindClose(HANDLE) { ++closeCalls; return true; }

static Array<String> _hx_std_sys_read_dir(String p) {
  Array<String> result = Array_obj<String>::__new();
__PATCH_BODY__
#endif
  hx::ExitGCFreeZone();
  return result;
}

static bool runListCase(const wchar_t *label, const std::wstring &input,
  const std::wstring &expectedSearch, bool expectFailure = false,
  bool resolutionFailure = false, bool listingFailure = false,
  bool enumerationFailure = false) {
  lastSearchPath.clear();
  fullPathCalls = 0;
  findCalls = 0;
  failFullPath = resolutionFailure;
  failFind = listingFailure;
  failFindNext = enumerationFailure;
  closeCalls = 0;
  hx::gcDepth = 0;
  bool threw = false;
  Array<String> result = nullptr;
  try {
    result = _hx_std_sys_read_dir(String::create(input.c_str()));
  } catch (const std::runtime_error &error) {
    threw = std::string(error.what()) == "Invalid directory";
  }
  if (expectFailure) {
    if (!threw || hx::gcDepth != 0) {
      std::wcerr << label << L": expected Invalid directory with GC zone restored\n";
      return false;
    }
    return true;
  }
  if (threw || result == nullptr || lastSearchPath != expectedSearch || hx::gcDepth != 0) {
    std::wcerr << label << L": path, result, or GC zone mismatch\n";
    return false;
  }
  if (result->values.size() != 2 || result->values[0].value != L"first.txt" ||
      result->values[1].value != L"second") {
    std::wcerr << label << L": directory entries were not preserved\n";
    return false;
  }
  return true;
}

int main() {
  (void)FindExInfoStandard;
  (void)FindExSearchNameMatch;
  (void)findCalls;
  (void)closeCalls;
#ifdef HX_WINRT
  if (!runListCase(L"WinRT separate branch", L"C:\\short",
      L"C:\\short/*.*")) return 1;
  if (!runListCase(L"WinRT explicit invalid list", std::wstring(MAX_PATH + 1, L'x'),
      L"", true)) return 2;
#else
  if (!runListCase(L"short drive path", L"C:\\short", L"C:\\short\\*.*")) return 3;

  std::wstring longDrive = L"C:\\root\\";
  longDrive.append(310, L'漢');
  if (!runListCase(L"long drive path", longDrive,
      L"\\\\?\\C:\\root\\" + std::wstring(310, L'漢') + L"\\*.*")) return 4;

  std::wstring longUnc = L"\\\\server\\share\\";
  longUnc.append(300, L'd');
  if (!runListCase(L"long UNC path", longUnc,
      L"\\\\?\\UNC\\server\\share\\" + std::wstring(300, L'd') + L"\\*.*")) return 5;

  if (!runListCase(L"already extended path", L"\\\\?\\C:\\long\\path",
      L"\\\\?\\C:\\long\\path\\*.*")) return 6;

  resolvedPath = L"C:\\mock-cwd\\relative\\folder";
  if (!runListCase(L"relative path", L"relative\\folder",
      L"C:\\mock-cwd\\relative\\folder\\*.*") || fullPathCalls != 2) return 7;

  resolvedPath = L"C:\\mock-cwd\\short";
  growToPath = L"C:\\mock-cwd\\" + std::wstring(300, L'g');
  growAfterQuery = true;
  if (!runListCase(L"growing dynamic full path", L"relative\\folder",
      L"\\\\?\\C:\\mock-cwd\\" + std::wstring(300, L'g') + L"\\*.*") || fullPathCalls != 3) return 8;

  if (!runListCase(L"relative resolution failure", L"relative\\folder", L"", true, true)) return 9;

  if (!runListCase(L"invalid directory listing", L"C:\\missing", L"", true, false, true)) return 10;
  if (!runListCase(L"mid-enumeration failure", L"C:\\interrupted", L"", true, false, false, true) || closeCalls != 1) return 11;
#endif
  std::cout << "hxcpp-windows-read-directory-ok\n";
  return 0;
}
'''


class HxcppWindowsReadDirectoryPatchTest(unittest.TestCase):
    @staticmethod
    def source_before_patch() -> bytes:
        source = PATCHER.SYS_SOURCE.read_bytes().replace(b"\r\n", b"\n")
        digest = hashlib.sha256(source).hexdigest()
        if digest == PATCHER.PATCHED_SHA256:
            if source.count(PATCHER.NEW) != 1 or source.count(PATCHER.INCLUDE_NEW) != 1:
                raise AssertionError("patched readDirectory sites were not unique")
            source = source.replace(PATCHER.NEW, PATCHER.OLD, 1)
            source = source.replace(PATCHER.INCLUDE_NEW, PATCHER.INCLUDE_OLD, 1)
        return source

    def test_patch_hash_chain_is_idempotent_and_rejects_drift(self):
        source = self.source_before_patch()
        self.assertEqual(hashlib.sha256(source).hexdigest(), PATCHER.SOURCE_SHA256)
        patched = PATCHER.patch_source(source)
        self.assertEqual(hashlib.sha256(patched).hexdigest(), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)
        with self.assertRaisesRegex(ValueError, "differs from pinned"):
            PATCHER.patch_source(source + b"// unexpected hxcpp source drift\n")

    def compile_and_run(self, *, winrt: bool = False):
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            self.skipTest("a C++11 compiler is unavailable")
        body = PATCHER.NEW.decode("utf-8")
        source = CPP_TEMPLATE.replace("__PATCH_BODY__", body)
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            cpp = work / "read_directory_patch.cpp"
            binary = work / "read_directory_patch"
            cpp.write_text(source, encoding="utf-8", newline='\n')
            command = [compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror"]
            if winrt:
                command.append("-DHX_WINRT=1")
            command.extend([str(cpp), "-o", str(binary)])
            compile_result = subprocess.run(
                command, capture_output=True, text=True, timeout=60
            )
            self.assertEqual(
                compile_result.returncode,
                0,
                compile_result.stdout + compile_result.stderr,
            )
            run_result = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=10
            )
        self.assertEqual(run_result.returncode, 0, run_result.stdout + run_result.stderr)
        self.assertIn("hxcpp-windows-read-directory-ok", run_result.stdout)

    def test_desktop_mock_handles_long_drive_unc_relative_and_errors(self):
        self.compile_and_run()

    def test_winrt_mock_keeps_its_separate_enumeration_path(self):
        self.compile_and_run(winrt=True)


if __name__ == "__main__":
    unittest.main()
