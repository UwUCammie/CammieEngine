# CammieEngine v0.0.9

An **alpha** Friday Night Funkin’ engine built on Disappointing Plus, Modding
Plus, and HaxeFlixel. Includes gameplay, a chart editor, scripting, and mod imports.

Compatibility with **Codename, Modding Plus/Poop, Psych, V-Slice, and Nightmare
Vision** is experimental. Some scripts, effects, menus, and editors remain
incomplete; importing successfully does not guarantee accurate playback.
Nightmare Vision has a separate import profile and reuses Psych compatibility
code where the supplied engines have identical behavior.

## Play on Windows

Download the **Windows x64 ZIP** from [GitHub Releases](https://github.com/UwUCammie/CammieEngine/releases), extract
it to a writable folder, and run **Funkin.exe**. Keep the included assets, DLLs,
and tools beside it. Players do not need a compiler or source checkout.

On Windows, including under Wine, **Settings → Check for Updates** checks
published releases and asks before downloading. A bundled Windows helper
uses the Windows HTTPS and certificate APIs to verify and install the package
after the game closes; it also replaces its own installed copy. Download
progress stays visible in Settings, Main Menu, and Freeplay browsing. Local
settings and imports remain in place; an existing
asset file is kept, so a clean extraction is needed when a release changes
bundled static assets. Releases before alpha.6 need one manual ZIP extraction
to acquire the bundled helper.

Maintainers build the Windows release locally and upload its ZIP and checksum
to GitHub Releases. Native Windows smoke checks cover startup and Tutorial gameplay.

## Build from source

Linux, with C++ build tools installed:

```sh
./run.sh build  # compile without launching
./run.sh        # compile when needed and play
```

On Windows 11, open PowerShell in this folder and use one command to build
the Windows x64 game and run the full regression suite:

```powershell
.\run.bat test
```

The first run downloads portable Haxe, Neko and Python as needed. It uses
Visual Studio's C++ tools when installed, or downloads a portable LLVM-MinGW
compiler automatically. No administrator access is needed for the portable
tools. Internet access and Git for Windows are needed for initial setup.
Close the game before building. Failed builds or tests return a nonzero exit
code. Tests requiring Linux-only tools or unavailable donor packages report
their skips explicitly.

Use `.\run.bat` to build and play, `.\run.bat nobuild` to play the existing
build, or `.\run.bat test debug` to build and test with debug symbols.
To build, test and package the v0.0.9 alpha for release:

```powershell
.\run.bat package
```

The ZIP and `SHA256SUMS.txt` are written to `dist/` only after the tests pass.
On Linux, one command builds and packages a Windows x64 ZIP with the bundled
results screen:

```sh
./build-windows-release.sh v0.0.9
```

The script uses `.tools/llvm-mingw` when installed locally; otherwise set
`HXCPP_MINGW_EXE` and `MINGW_ROOT` for a MinGW-w64 compiler. Add `--wine-smoke`
after the tag for a bounded Wine launch check. The ZIP and `SHA256SUMS.txt`
appear in `dist/`; upload both to the matching GitHub prerelease. The
cross-build uses `-Dwindows -DHXCPP_MINGW -DHXCPP_M64`.
`run.bat` is the native Windows entry point.
The optional Wine check uses GNU `timeout` and accepts `WINE_BIN` to select
another Wine executable.
The AppImage target is
`./build.sh appimage`; for a writable runtime, set `DISAPPOINTINGPLUS_RUNTIME_DIR`
or use `APPIMAGE_EXTRACT_AND_RUN=1` when running the read-only AppImage. Build
scratch files use the project-local `tmp/` directory. The Windows build stages
its ASTC decoder under `export/<mode>/windows/bin/tools/`. Close the game before
rebuilding. To check an existing Windows build only, run `./build.sh wine-smoke`.

## Local imports

Bundled assets are included. Imported mod libraries, build output, and personal
runtime files stay local and are excluded from Git automatically—including
future imports. Deliberate new engine assets in ignored folders require
`git add -f`; ordinary source-code changes do not.

New imports retain the selected source package in `import-cache/` beside the
game, excluding native executables and libraries. When an engine update changes
the importer revision, outdated imports rebuild automatically while browsing
menus or Settings. Progress is shown there. The original folder is no longer
needed for those refreshes; keep the cache with the installation. Retaining
source uses additional disk space. Conflicting local edits stop a refresh and
leave the installed import intact. Imports created before source retention need
an initial migration; they are never silently overwritten.

## Verification

The Lua translation corpus is **122/122 clean**. For offscreen gameplay checks,
use `python3 tools/run_runtime_smoke_matrix.py` with `--runtime-root` or
`--asset-root` as needed. Logs go to `tmp/runtime-smoke/logs/`; the runner
does not build anything automatically.
`python3 tools/run_import_refresh_smoke.py` checks sequential imports and
automatic retained-source refresh on an existing Linux build, then cleans its
private runtime. Add `--wine` to check an existing Windows build using a private
Wine prefix.

## Details and credits

Maintained by **UwUCammie**, building on AFunkinDisappointment’s Disappointing
Plus and the original Modding Plus and Friday Night Funkin’ contributors.

- [Compatibility inventory](tools/reports/example-mods-compatibility-inventory.md)
  and [verification report](tools/reports/engine-discrepancies-verification.md)
- [Architecture](ENGINE_ARCHITECTURE.md) · [Update log](updateLog.txt)
- [Credits](assets/data/credits.txt) · [License](LICENSE) · [Third-party notices](NOTICE)
