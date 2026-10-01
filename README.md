# CammieEngine v0.0.1-alpha.7

An **alpha** Friday Night Funkin’ engine built on Disappointing Plus, Modding
Plus, and HaxeFlixel. Includes gameplay, a chart editor, scripting, and mod imports.

Compatibility with **Codename, Modding Plus/Poop, Psych, V-Slice, and Nightmare
Vision** is experimental. Some scripts, effects, menus, and editors remain
incomplete; importing successfully does not guarantee accurate playback.

## Play on Windows

Download the **Windows x64 ZIP** from [GitHub Releases](https://github.com/UwUCammie/CammieEngine/releases), extract
it to a writable folder, and run **Funkin.exe**. Keep the included assets, DLLs,
and tools beside it. Players do not need a compiler or source checkout.

On Windows, including under Wine, **Settings → Check for Updates** checks
published releases and asks before downloading. A bundled Windows helper
uses the Windows HTTPS and certificate APIs to verify and install the package
after the game closes; it also replaces its
own installed copy. Local settings and imports remain in place; an existing
asset file is kept, so a clean extraction is needed when a release changes
bundled static assets. Releases before alpha.6 need one manual ZIP extraction
to acquire the bundled helper.

Maintainers build the Windows release locally and upload its ZIP and checksum
to GitHub Releases. Playback on native Windows hardware still needs verification.

## Build from source

Linux, with C++ build tools installed:

```sh
./run.sh build  # compile without launching
./run.sh        # compile when needed and play
```

Windows developers can use `run.bat build` with the Visual Studio C++ workload.
On Linux, one command builds and packages a Windows x64 ZIP with the bundled
results screen:

```sh
./build-windows-release.sh v0.0.1-alpha.7
```

The script uses `.tools/llvm-mingw` when installed locally; otherwise set
`HXCPP_MINGW_EXE` and `MINGW_ROOT` for a MinGW-w64 compiler. Add `--wine-smoke`
after the tag for a bounded Wine launch check. The ZIP and `SHA256SUMS.txt`
appear in `dist/`; upload both to the matching GitHub prerelease. The
cross-build uses `-Dwindows -DHXCPP_MINGW -DHXCPP_M64`.
`run.bat` remains the native Windows/MSVC entry point.
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

## Verification

The Lua translation corpus is **122/122 clean**. For offscreen gameplay checks,
use `python3 tools/run_runtime_smoke_matrix.py` with `--runtime-root` or
`--asset-root` as needed. Logs go to `tmp/runtime-smoke/logs/`; the runner
does not build anything automatically.

## Details and credits

Maintained by **UwUCammie**, building on AFunkinDisappointment’s Disappointing
Plus and the original Modding Plus and Friday Night Funkin’ contributors.

- [Compatibility inventory](tools/reports/example-mods-compatibility-inventory.md)
  and [verification report](tools/reports/engine-discrepancies-verification.md)
- [Architecture](ENGINE_ARCHITECTURE.md) · [Update log](updateLog.txt)
- [Credits](assets/data/credits.txt) · [License](LICENSE) · [Third-party notices](NOTICE)
