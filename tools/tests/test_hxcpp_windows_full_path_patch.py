"""Regression tests for the pinned hxcpp Windows fullPath buffer patch."""

import hashlib
import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest
from tools.patch_hxcpp_windows_file_paths import unpatch_sys_source


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "patch_hxcpp_windows_full_path", ROOT / "tools/patch_hxcpp_windows_full_path.py"
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)
READ_DIRECTORY_SPEC = importlib.util.spec_from_file_location(
    "patch_hxcpp_windows_read_directory",
    ROOT / "tools/patch_hxcpp_windows_read_directory.py",
)
READ_DIRECTORY_PATCHER = importlib.util.module_from_spec(READ_DIRECTORY_SPEC)
READ_DIRECTORY_SPEC.loader.exec_module(READ_DIRECTORY_PATCHER)


CPP_TEMPLATE = r'''#include <algorithm>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using DWORD = uint32_t;
namespace hx { struct strbuf {}; }

struct String {
  std::wstring value;
  bool isNull;
  String() : isNull(false) {}
  const wchar_t *wchar_str(hx::strbuf *) const { return value.c_str(); }
  static String create(const wchar_t *text) {
    String result;
    result.value = text;
    return result;
  }
};

static String null() {
  String result;
  result.isNull = true;
  return result;
}

static std::wstring inputPath;
static std::wstring resolvedPath;
static std::wstring pathAfterGrowth;
static int apiCalls = 0;
static int failOnCall = 0;
static bool growAfterQuery = false;

static DWORD GetFullPathNameW(const wchar_t *input, DWORD capacity,
  wchar_t *buffer, wchar_t **) {
  apiCalls++;
  if (std::wstring(input) != inputPath || apiCalls == failOnCall) return 0;
  if (capacity == 0) return static_cast<DWORD>(resolvedPath.size() + 1);
  if (apiCalls == 2 && growAfterQuery) {
    resolvedPath = pathAfterGrowth;
    growAfterQuery = false;
  }
  const DWORD required = static_cast<DWORD>(resolvedPath.size() + 1);
  if (capacity < required) return required;
  std::copy(resolvedPath.begin(), resolvedPath.end(), buffer);
  buffer[resolvedPath.size()] = L'\0';
  return static_cast<DWORD>(resolvedPath.size());
}

static String fullPath(String path) {
__PATCH_BODY__
}

static bool runCase(const wchar_t *label, const std::wstring &input,
  const std::wstring &resolved, bool grow, const std::wstring &grown,
  int failCall, const std::wstring &expected, int expectedCalls) {
  inputPath = input;
  resolvedPath = resolved;
  pathAfterGrowth = grown;
  growAfterQuery = grow;
  failOnCall = failCall;
  apiCalls = 0;
  String result = fullPath(String::create(input.c_str()));
  if (expected.empty()) {
    if (!result.isNull) {
      std::wcerr << label << L": expected failure\n";
      return false;
    }
  } else if (result.isNull || result.value != expected) {
    std::wcerr << label << L": result did not match expected full path\n";
    return false;
  }
  if (apiCalls != expectedCalls) {
    std::wcerr << label << L": unexpected API call count " << apiCalls << L"\n";
    return false;
  }
  return true;
}

int main() {
  const std::wstring shortPath = L"C:\\Users\\Café\\Dependency.class";
  if (!runCase(L"short Unicode", shortPath, shortPath, false, L"", 0,
    shortPath, 2)) return 1;

  std::wstring longPath = L"C:\\root\\";
  longPath.append(420, L'漢');
  longPath += L"\\Dependency.class";
  if (longPath.size() <= 260) return 2;
  if (!runCase(L"long Unicode", longPath, longPath, false, L"", 0,
    longPath, 2)) return 3;

  if (!runCase(L"query failure", shortPath, shortPath, false, L"", 1,
    L"", 1)) return 4;
  if (!runCase(L"copy failure", shortPath, shortPath, false, L"", 2,
    L"", 2)) return 5;

  const std::wstring initial = L"C:\\root\\before-growth";
  std::wstring grown = initial;
  grown.append(360, L'é');
  if (!runCase(L"path grows between calls", initial, initial, true, grown, 0,
    grown, 3)) return 6;

  std::cout << "hxcpp-full-path-ok\n";
  return 0;
}
'''


class HxcppWindowsFullPathPatchTest(unittest.TestCase):
    @staticmethod
    def original_source() -> bytes:
        source = unpatch_sys_source(PATCHER.SYS_SOURCE.read_bytes()).replace(b"\r\n", b"\n")
        digest = hashlib.sha256(source).hexdigest()
        if digest == READ_DIRECTORY_PATCHER.PATCHED_SHA256:
            if source.count(READ_DIRECTORY_PATCHER.NEW) != 1:
                raise AssertionError("patched hxcpp readDirectory body was not unique")
            source = source.replace(READ_DIRECTORY_PATCHER.NEW, READ_DIRECTORY_PATCHER.OLD, 1)
            if source.count(READ_DIRECTORY_PATCHER.INCLUDE_NEW) != 1:
                raise AssertionError("patched hxcpp readDirectory includes were not unique")
            source = source.replace(
                READ_DIRECTORY_PATCHER.INCLUDE_NEW,
                READ_DIRECTORY_PATCHER.INCLUDE_OLD,
                1,
            )
            digest = hashlib.sha256(source).hexdigest()
        if digest == PATCHER.PATCHED_SHA256:
            if source.count(PATCHER.NEW) != 1:
                raise AssertionError("patched hxcpp body was not unique")
            source = source.replace(PATCHER.NEW, PATCHER.OLD, 1)
            include = b"#include <time.h>\n#include <vector>"
            if source.count(include) != 1:
                raise AssertionError("patched vector include was not unique")
            source = source.replace(include, b"#include <time.h>", 1)
        return source

    def test_pinned_patch_is_idempotent_and_rejects_drift(self):
        original = self.original_source()
        self.assertEqual(hashlib.sha256(original).hexdigest(), PATCHER.SOURCE_SHA256)
        patched = PATCHER.patch_source(original)

        self.assertEqual(hashlib.sha256(patched).hexdigest(), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)
        with self.assertRaisesRegex(ValueError, "differs from pinned"):
            PATCHER.patch_source(original + b"// unexpected hxcpp source drift\n")

    def test_full_path_patch_accepts_the_later_read_directory_bootstrap_output(self):
        original = self.original_source()
        full_path_patched = PATCHER.patch_source(original)
        combined = READ_DIRECTORY_PATCHER.patch_source(full_path_patched)

        self.assertEqual(hashlib.sha256(combined).hexdigest(),
                         PATCHER.READ_DIRECTORY_PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(combined), combined)
        self.assertEqual(READ_DIRECTORY_PATCHER.patch_source(combined), combined)

    def test_compiled_replacement_retries_long_unicode_paths_and_propagates_failures(self):
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            self.skipTest("a C++11 compiler is unavailable")

        patched_body = PATCHER.NEW.decode("utf-8")
        source = CPP_TEMPLATE.replace("__PATCH_BODY__", patched_body)
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            cpp = work / "full_path_patch.cpp"
            binary = work / "full_path_patch"
            cpp.write_text(source, encoding="utf-8", newline='\n')
            compile_result = subprocess.run(
                [compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(binary)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            run_result = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=10
            )

        self.assertEqual(run_result.returncode, 0, run_result.stdout + run_result.stderr)
        self.assertIn("hxcpp-full-path-ok", run_result.stdout)


if __name__ == "__main__":
    unittest.main()
