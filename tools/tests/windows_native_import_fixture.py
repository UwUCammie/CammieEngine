"""Build and retrieve the shared native Windows import regression fixture."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import patch_hxcpp_windows_file_paths as patcher
from haxe_test_support import HAXE, TEST_TMP
from native_fixture_cache import CachedNativeFixture, get_or_build, sha256_file
from test_import_refresh_manager import FIXTURE, STUBS
from test_import_io import IO_SCHEDULER_FIXTURE


_SEQUENCE_CHECKPOINT = "committed:view.committedOwnerRoots,revision:view.revision};"
_MANAGER_ARGS_CHECKPOINT = "  var args=Sys.args();\n  var mode=args[0];"
_EXPECTED_EXECUTABLE = "cpp/NativeImportFilesystemFixture.exe"
_HXCPP_CONFIG = "fixture_hxcpp_config.xml"
_HXCPP_CONFIG_SOURCE = "<xml><section id=\"vars\"/><section id=\"exes\"/></xml>\n"
_HAXE_TIMEOUT_SECONDS = 180

MAIN = r'''import haxe.Json;
import sys.io.File;
import sys.FileSystem;
@:access(ImportRefreshManager)
@:access(ImportRefreshManagerFixture)
@:access(ImportIOSchedulerFixture)
class NativeImportFilesystemFixture {
 static function main() {
  var args=Sys.args();
  try {
   switch(args[0]) {
    case "manager-fixture":
     ImportRefreshManagerFixture.main();
    case "io-scheduler":
     ImportIOSchedulerFixture.main();
    case "registry-refresh":
     var mode=args[1];
     var before=File.getContent(args[2]);
     var generated=File.getContent(args[3]);
     var live=File.getContent(args[4]);
     var result=if(mode=="prepare") ImportRegistryRefresh.prepare(before,generated,live)
      else if(mode=="seed") ImportRegistryRefresh.regenerationSeed(before,generated,live)
      else ImportRegistryRefresh.merge(before,generated,live);
     File.saveContent(args[5],result.text);
     Sys.println(Json.stringify({conflicts:result.conflicts}));
    case "fresh", "auto-refresh", "auto-refresh-sequence", "cleanup-scheduler":
     ImportRefreshManagerFixture.main();
    case "pointer":
     ImportRefreshManager.atomicText(args[1],args[2]);
     Sys.println(Json.stringify({ok:true,text:File.getContent(args[1])}));
    case "capture":
     var result=ImportSourceSnapshot.capture(args[1],args[2],"Nightmare Vision","0.0.9");
     if(!result.complete) throw result.error;
     ImportSourceSnapshot.verify(result.snapshotRoot,result.snapshotId);
     Sys.println(Json.stringify({ok:true,result:result}));
    case "verify":
     ImportSourceSnapshot.verify(args[1],args[2]);
     Sys.println(Json.stringify({ok:true}));
    case "psych-asset-profile":
     ImportSourceSnapshot.verify(args[1],args[2]);
     var content=args[1]+"/content";
     var profile=PsychAssetProfile.resolveRetained(content,args[2],args[3],"Psych Engine",args[4],Json.parse(args[5]));
     var mapped:Array<Dynamic>=[];
     var walk=PsychAssetProfile.walkLanguageFiles(profile,content,function(file) mapped.push(file));
     Sys.println(Json.stringify({ok:true,profile:profile,mapped:mapped,walk:walk}));
    case "source-asset-profile":
     ImportSourceSnapshot.verify(args[1],args[2]);
     var content=args[1]+"/content";
     var profile=PsychAssetProfile.resolveRetained(content,args[2],args[3],args[4],args[5],Json.parse(args[6]));
     var mapped:Array<Dynamic>=[];
     var languageOnly=args.length>7 && args[7]=="language";
     var filter:Null<String->String->Bool>=languageOnly
      ? function(source:String,target:String):Bool return StringTools.endsWith(source.toLowerCase(),".lang")
       || StringTools.endsWith(target.toLowerCase(),".lang")
      : null;
     var walk=PsychAssetProfile.walkMappedFiles(profile,content,function(file) mapped.push(file),null,null,filter);
     Sys.println(UnicodeSafeJson.stringifyStandard({ok:true,profile:profile,mapped:mapped,walk:walk}));
    case "project-resolution-scheduler":
     ImportSourceSnapshot.verify(args[1],args[2]);
     var content=args[1]+"/content";
     var build:PsychAssetProfile.PsychAssetProfileBuild=cast Json.parse(args[3]);
     ImportWorkScheduler.bindForegroundThread();
     var lease=ImportWorkScheduler.beginGameplay();
     var done=new sys.thread.Lock();
     var cancelGate=new sys.thread.Mutex();
     var cancelRequested=false;
     var sawCancellation=false;
     var workerError="";
     sys.thread.Thread.create(function() {
      try {
       PsychAssetProfile.resolveRetained(content,args[2],"","Psych Engine","scheduler-profile-owner",build,function() {
        cancelGate.acquire(); var value=cancelRequested; cancelGate.release(); return value;
       });
      } catch(error:Dynamic) {
       sawCancellation=Std.isOfType(error,ImportWorkCancelled); workerError=Std.string(error);
      }
      done.release();
     });
     if(done.wait(0.05)) throw "Project resolver did not pause for gameplay";
     cancelGate.acquire(); cancelRequested=true; cancelGate.release();
     if(!done.wait(2) || !sawCancellation) throw "Paused Project resolver did not cancel: "+workerError;
     var foreground=PsychAssetProfile.resolveRetained(content,args[2],"","Psych Engine","scheduler-profile-owner",build,function() return false);
     ImportWorkScheduler.endGameplay(lease);
     if(!foreground.complete) throw "Foreground Project resolver did not complete";
     Sys.println(UnicodeSafeJson.stringifyStandard({ok:true,cancelled:sawCancellation,foreground:foreground.complete}));
    case "io":
     var directory=args[1];
     FileSystem.createDirectory(directory);
     if(!FileSystem.exists(directory)||!FileSystem.isDirectory(directory)) throw "directory missing";
     var path=directory+"/雪.txt";
     File.saveContent(path,"long-path-bytes");
     if(File.getContent(path)!="long-path-bytes"||File.getBytes(path).length!=15||FileSystem.stat(path).size!=15)
      throw "incorrect long-path read or stat";
     var input=File.read(path,true);
     var text=input.readAll().toString(); input.close();
     if(text!="long-path-bytes") throw "incorrect streaming read";
     FileSystem.rename(path,path+".renamed");
     FileSystem.deleteFile(path+".renamed");
     FileSystem.deleteDirectory(directory);
     Sys.println(Json.stringify({ok:true}));
   }
  } catch(error:Dynamic) Sys.println(Json.stringify({ok:false,error:Std.string(error)}));
 }
}'''


@dataclass(frozen=True)
class NativeImportFixture:
    executable: Path
    environment: dict[str, str]
    key: str
    sha256: str
    reused: bool


class NativeFixtureUnavailable(RuntimeError):
    """The optional Windows native toolchain is not installed."""


def native_fixture_source() -> str:
    if _SEQUENCE_CHECKPOINT not in FIXTURE:
        raise AssertionError("native refresh fixture lost its overlap checkpoint")
    if FIXTURE.count(_MANAGER_ARGS_CHECKPOINT) != 1:
        raise AssertionError("native refresh fixture lost its manager argument checkpoint")
    source = FIXTURE.replace(
        _MANAGER_ARGS_CHECKPOINT,
        '  var args=Sys.args();\n'
        '  if(args.length>0 && args[0]=="manager-fixture") args.shift();\n'
        '  var mode=args[0];',
    )
    return source.replace(
        _SEQUENCE_CHECKPOINT,
        "committed:view.committedOwnerRoots,revision:view.revision,active:ImportRefreshManager.active};",
    )


def native_fixture_sources() -> dict[str, str]:
    io_source = IO_SCHEDULER_FIXTURE.replace("class Main {", "class ImportIOSchedulerFixture {")
    checkpoint = '  var args=Sys.args(); var install=args[0];'
    if io_source.count(checkpoint) != 1:
        raise AssertionError("native IO scheduler fixture lost its argument checkpoint")
    io_source = io_source.replace(checkpoint,
        '  var args=Sys.args(); if(args.length>0 && args[0]=="io-scheduler") args.shift(); var install=args[0];')
    return {
        **STUBS,
        "ImportIOSchedulerFixture.hx": io_source,
        "ImportRefreshManagerFixture.hx": native_fixture_source(),
        "NativeImportFilesystemFixture.hx": MAIN,
    }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _tree_identity(root: Path, *, suffix: str | None = None,
                   excluded_suffixes: set[str] | None = None) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(f"required native fixture input directory is missing: {root}")
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise RuntimeError(f"native fixture input root cannot be a symlink or junction: {root}")
    items = []
    for path in sorted(root.rglob("*"), key=lambda item: (item.as_posix().casefold(), item.as_posix())):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise RuntimeError(f"native fixture input tree contains an unsupported symlink or junction: {path}")
        if not path.is_file():
            continue
        if suffix is not None and path.suffix.lower() != suffix.lower():
            continue
        if excluded_suffixes and path.suffix.lower() in excluded_suffixes:
            continue
        items.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        })
    return {"files": items}


def _capture_engine_sources(source_root: Path, destination: Path,
                            expected_identity: dict[str, Any]) -> dict[str, Any]:
    """Stage the exact engine Haxe bytes represented by a cache fingerprint.

    The source tree is fingerprinted before a cache miss is entered. Reading it
    again for compilation would let an edit between those steps produce a
    binary under the old cache key. Copying each file's bytes into staging and
    comparing that manifest closes that race; later edits to the checkout do
    not change the compiler input.
    """
    if not source_root.is_dir():
        raise FileNotFoundError(f"required native fixture input directory is missing: {source_root}")
    if source_root.is_symlink() or (hasattr(source_root, "is_junction") and source_root.is_junction()):
        raise RuntimeError(f"native fixture input root cannot be a symlink or junction: {source_root}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"engine Haxe staging directory already exists: {destination}")

    destination.mkdir(parents=True)
    captured_files = []
    for path in sorted(source_root.rglob("*"),
                       key=lambda item: (item.as_posix().casefold(), item.as_posix())):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise RuntimeError(f"native fixture input tree contains an unsupported symlink or junction: {path}")
        if not path.is_file() or path.suffix.lower() != ".hx":
            continue
        relative = path.relative_to(source_root).as_posix()
        content = path.read_bytes()
        target = destination.joinpath(*Path(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        captured_files.append({"path": relative, "sha256": _sha256_bytes(content)})

    captured_identity = {"files": captured_files}
    if captured_identity != expected_identity:
        raise RuntimeError("engine Haxe source tree changed after native fixture fingerprinting")
    return captured_identity


def _hxcpp_source_identity(root: Path) -> dict[str, Any]:
    excluded = {".o", ".obj", ".exe", ".dll", ".a", ".lib", ".ndll", ".pdb", ".ilk", ".d"}
    directories = {
        name: _tree_identity(root / name, excluded_suffixes=excluded)
        for name in ("build-tool", "hxcpp", "include", "project", "src", "toolchain", "tools/hxcpp")
    }
    files = {}
    for name in ("haxelib.json", "haxelib.xml", "hxcpp.n", "run.n"):
        path = root / name
        if path.is_file():
            files[name] = sha256_file(path)
    return {"files": files, "directories": directories}


def _tool_version(path: Path, *args: str) -> str:
    completed = subprocess.run([str(path), *args], cwd=ROOT, capture_output=True,
                               text=True, timeout=15)
    if completed.returncode != 0:
        raise RuntimeError(f"could not identify native fixture tool {path}: {completed.stderr}")
    return (completed.stdout + completed.stderr).strip()


def _mingw_archive_identity() -> dict[str, str]:
    run_bat = (ROOT / "run.bat").read_text(encoding="utf-8")
    match = re.search(
        r'call :download_tool llvm-mingw "([^"]+)" "!MINGW_ROOT!" bin\\clang\.exe ([0-9a-f]{64})',
        run_bat,
        re.IGNORECASE,
    )
    if match is None:
        raise RuntimeError("run.bat no longer identifies the checksum-pinned Windows LLVM-MinGW archive")
    return {"url": match.group(1), "sha256": match.group(2).lower()}


def _native_toolchain() -> tuple[Path, dict[str, str], dict[str, Any]]:
    compiler = ROOT / ".tools/llvm-mingw-windows"
    clangxx = compiler / "bin/x86_64-w64-mingw32-clang++.exe"
    if not HAXE.is_file() or not clangxx.is_file():
        raise NativeFixtureUnavailable("portable Haxe or native Windows LLVM-MinGW toolchain is unavailable")

    tool_paths = {
        "haxe": HAXE,
        "clangxx": clangxx,
        "clang": compiler / "bin/clang.exe",
        "ar": compiler / "bin/llvm-ar.exe",
        "ranlib": compiler / "bin/llvm-ranlib.exe",
        "strip": compiler / "bin/llvm-strip.exe",
        "windres": compiler / "bin/llvm-windres.exe",
        "linker": compiler / "bin/ld.lld.exe",
        "targetLinker": compiler / "bin/x86_64-w64-mingw32-ld",
        "assembler": compiler / "bin/x86_64-w64-mingw32-as.exe",
        "dlltool": compiler / "bin/x86_64-w64-mingw32-dlltool.exe",
    }
    identity: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "mingwArchive": _mingw_archive_identity(),
        "tools": {},
    }
    for name, path in tool_paths.items():
        if path.is_file():
            identity["tools"][name] = {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
        elif name != "haxe":
            identity["tools"][name] = {"path": path.relative_to(ROOT).as_posix(), "missing": True}

    identity["haxeVersion"] = _tool_version(HAXE, "--version")
    identity["clangVersion"] = _tool_version(clangxx, "--version")
    tool_search_path = os.pathsep.join([
        str(HAXE.parent), str(ROOT / ".tools/neko"),
        str(compiler / "bin"), os.environ.get("PATH", ""),
    ])
    resolved_tools = {
        "mingwCompiler": "x86_64-w64-mingw32-clang++.exe",
        "archiver": "llvm-ar.exe",
        "ranlib": "llvm-ranlib.exe",
        "strip": "llvm-strip.exe",
        "resourceCompiler": "llvm-windres.exe",
        "linker": "ld.lld.exe",
        "targetLinker": "x86_64-w64-mingw32-ld",
        "assembler": "x86_64-w64-mingw32-as.exe",
        "dlltool": "x86_64-w64-mingw32-dlltool.exe",
    }
    identity["resolvedTools"] = {}
    for name, command in resolved_tools.items():
        resolved = shutil.which(command, path=tool_search_path)
        if resolved is None:
            identity["resolvedTools"][name] = {"command": command, "missing": True}
            continue
        resolved_path = Path(resolved).resolve(strict=True)
        try:
            display_path = resolved_path.relative_to(ROOT).as_posix()
        except ValueError:
            display_path = str(resolved_path)
        identity["resolvedTools"][name] = {
            "command": command,
            "path": display_path,
            "sha256": sha256_file(resolved_path),
        }
    for label, pattern in (("targetTripletTools", "x86_64-w64-mingw32-*"),
                           ("llvmDriverTools", "llvm-*.exe"),
                           ("clangDrivers", "clang*.exe")):
        entries = {}
        for path in sorted((compiler / "bin").glob(pattern), key=lambda item: (item.name.casefold(), item.name)):
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                raise RuntimeError(f"compiler tool directory contains an unsupported symlink: {path}")
            if path.is_file():
                entries[path.name] = sha256_file(path)
        identity[label] = entries
    for name, path in (("haxeRuntime", ROOT / ".tools/haxe"),
                       ("nekoRuntime", ROOT / ".tools/neko")):
        if path.is_dir():
            identity[name] = _tree_identity(path)

    # run.bat downloads this exact archive through download_windows_tool.ps1,
    # which verifies the pinned SHA-256 before extraction. Also hash the active
    # LLVM and x86_64 sysroot directories below so local edits invalidate the
    # cache. Other architecture sysroots are not inputs to this x86_64 fixture.
    identity["sysroot"] = {
        "relativePath": compiler.relative_to(ROOT).as_posix(),
        "distributionSha256": identity["mingwArchive"]["sha256"],
        "target": "x86_64-w64-mingw32",
        "directories": {},
    }
    for name, relative in (
        ("llvmInclude", "include"),
        ("llvmLibraries", "lib"),
        ("targetInclude", "x86_64-w64-mingw32/include"),
        ("targetLibraries", "x86_64-w64-mingw32/lib"),
    ):
        directory = compiler / relative
        if directory.is_dir():
            identity["sysroot"]["directories"][name] = _tree_identity(directory)
    bin_dir = compiler / "bin"
    runtime_dlls = {}
    for path in sorted(bin_dir.glob("*.dll"), key=lambda item: (item.name.casefold(), item.name)):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise RuntimeError(f"compiler runtime directory contains an unsupported symlink: {path}")
        if path.is_file():
            runtime_dlls[path.name] = sha256_file(path)
    identity["compilerRuntimeDlls"] = runtime_dlls
    return compiler, {name: str(path) for name, path in tool_paths.items()}, identity


def _patch_identity() -> dict[str, str]:
    identities = {}
    for filename, expected in (("Sys.cpp", patcher.SYS_PATCHED_SHA256),
                               ("File.cpp", patcher.FILE_PATCHED_SHA256)):
        path = patcher.STD / filename
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"hxcpp {filename} is not in the pinned Windows-path patch state: {actual}"
            )
        identities[filename] = actual
    return identities


def _build_environment(compiler: Path) -> dict[str, str]:
    unsupported = (
        "CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS",
        "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH",
        "LIBRARY_PATH", "CCC_OVERRIDE_OPTIONS",
    )
    configured = [name for name in unsupported if os.environ.get(name, "").strip()]
    if configured:
        raise RuntimeError(
            "native fixture caching requires a controlled MinGW compile environment; "
            "unset external compiler override(s): " + ", ".join(configured)
        )
    return {
        **os.environ,
        "HAXEPATH": str(HAXE.parent),
        "NEKOPATH": str(ROOT / ".tools/neko"),
        "HAXELIB_PATH": str(ROOT / ".haxelib"),
        "HAXE_STD_PATH": str(ROOT / ".tools/haxe/std"),
        "MINGW_ROOT": str(compiler),
        "HXCPP_CONFIG": "<STAGING>/" + _HXCPP_CONFIG,
        "HXCPP_MINGW_EXE": "x86_64-w64-mingw32-clang++.exe",
        "HXCPP_AR": "llvm-ar.exe",
        "HXCPP_RANLIB": "llvm-ranlib.exe",
        "HXCPP_STRIP": "llvm-strip.exe",
        "HXCPP_RC": "llvm-windres.exe",
        "PATH": os.pathsep.join([
            str(HAXE.parent), str(ROOT / ".tools/neko"),
            str(compiler / "bin"), os.environ.get("PATH", ""),
        ]),
    }


def _command_template() -> list[str]:
    return [
        str(HAXE), "-cp", "<STAGING>/engine-source",
        "-cp", str(ROOT / ".haxelib/tjson/1,4,0"),
        "-cp", "<STAGING>", "-main", "NativeImportFilesystemFixture",
        "-cpp", "<STAGING>/cpp", "-D", "windows", "-D", "HXCPP_M64",
        "-D", "HXCPP_MINGW", "-D", "HXCPP_RC=llvm-windres.exe",
    ]


def _fingerprint(sources: dict[str, str], compiler_identity: dict[str, Any],
                 environment: dict[str, str]) -> dict[str, Any]:
    generated = {
        path: _sha256_bytes(source.encode("utf-8"))
        for path, source in sorted(sources.items())
    }
    recipe_paths = (
        ROOT / "tools/tests/native_fixture_cache.py",
        ROOT / "tools/tests/windows_native_import_fixture.py",
        ROOT / "tools/tests/test_import_refresh_manager.py",
        ROOT / "tools/tests/test_import_windows_native_filesystem.py",
        ROOT / "tools/tests/haxe_test_support.py",
        ROOT / "tools/patch_hxcpp_windows_file_paths.py",
        ROOT / "run.bat",
    )
    recipe = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in recipe_paths
    }
    hxcpp = ROOT / ".haxelib/hxcpp/4,3,2"
    tjson = ROOT / ".haxelib/tjson/1,4,0"
    patch_sources = {
        filename: sha256_file(patcher.STD / filename)
        for filename in ("Sys.cpp", "File.cpp")
    }
    effective_environment = {
        key: value for key, value in environment.items()
        if key != "HXCPP_COMPILE_THREADS"
    }
    effective_environment["HXCPP_CONFIG"] = "<STAGING>/" + _HXCPP_CONFIG
    return {
        "schema": 1,
        "repositoryRoot": str(ROOT.resolve()),
        "generatedHaxeSources": generated,
        "generatedHxcppConfigSha256": _sha256_bytes(_HXCPP_CONFIG_SOURCE.encode("utf-8")),
        "engineHaxeSources": _tree_identity(ROOT / "source", suffix=".hx"),
        "haxelibs": {
            "hxcpp-4.3.2": _hxcpp_source_identity(hxcpp),
            "tjson-1.4.0": _tree_identity(tjson),
        },
        "recipeFiles": recipe,
        "hxcppPatch": {
            "sourceSha256": {
                "Sys.cpp": patcher.SYS_SOURCE_SHA256,
                "File.cpp": patcher.FILE_SOURCE_SHA256,
            },
            "expectedPatchedSha256": {
                "Sys.cpp": patcher.SYS_PATCHED_SHA256,
                "File.cpp": patcher.FILE_PATCHED_SHA256,
            },
            "actualSha256": patch_sources,
        },
        "nativeToolchain": compiler_identity,
        "compile": {
            "command": _command_template(),
            "timeoutSeconds": _HAXE_TIMEOUT_SECONDS,
            "environment": {
                key: value for key, value in sorted(effective_environment.items())
            },
            "expectedExecutable": _EXPECTED_EXECUTABLE,
        },
    }


def get_native_fixture() -> NativeImportFixture:
    if os.name != "nt":
        raise NativeFixtureUnavailable("native Windows import fixture runs only on Windows")
    compiler, tool_paths, compiler_identity = _native_toolchain()
    patch_identity = _patch_identity()
    environment = _build_environment(compiler)
    sources = native_fixture_sources()
    fingerprint = _fingerprint(sources, compiler_identity, environment)
    fingerprint["hxcppPatch"]["actualSha256"] = patch_identity
    build_metadata = {
        "command": _command_template(),
        "timeoutSeconds": _HAXE_TIMEOUT_SECONDS,
        "tools": tool_paths,
    }
    cache_root = Path(os.environ.get(
        "CAMMIE_NATIVE_FIXTURE_CACHE",
        str(TEST_TMP / "native-fixture-cache"),
    ))

    def build(staging: Path) -> Path:
        _capture_engine_sources(
            ROOT / "source", staging / "engine-source",
            fingerprint["engineHaxeSources"],
        )
        for relative, content in sources.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        (staging / _HXCPP_CONFIG).write_text(
            _HXCPP_CONFIG_SOURCE, encoding="utf-8", newline="\n")

        command = [
            str(HAXE), "-cp", str(staging / "engine-source"),
            "-cp", str(ROOT / ".haxelib/tjson/1,4,0"),
            "-cp", str(staging), "-main", "NativeImportFilesystemFixture",
            "-cpp", str(staging / "cpp"), "-D", "windows", "-D", "HXCPP_M64",
            "-D", "HXCPP_MINGW", "-D", "HXCPP_RC=llvm-windres.exe",
        ]
        build_environment = dict(environment)
        build_environment["HXCPP_CONFIG"] = str(staging / _HXCPP_CONFIG)
        process = subprocess.run(command, cwd=ROOT, env=build_environment,
                                 capture_output=True, text=True,
                                 timeout=_HAXE_TIMEOUT_SECONDS)
        if process.returncode != 0:
            raise AssertionError(process.stdout + process.stderr)
        return staging / _EXPECTED_EXECUTABLE

    cached: CachedNativeFixture = get_or_build(
        cache_root, fingerprint, _EXPECTED_EXECUTABLE, build,
        build_metadata=build_metadata,
    )
    return NativeImportFixture(
        executable=cached.executable,
        environment=environment,
        key=cached.key,
        sha256=cached.sha256,
        reused=cached.reused,
    )
