# CammieEngine v0.0.28

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

## Freeplay browser

Host Freeplay displays eight aligned rows at the usual 1280x720 logical viewport,
with bounded title/source labels, visible import locks, a selected-song details panel,
and separate completion stars. Named authored V-Slice difficulty ratings appear in
the details panel after import/refresh; missing or ambiguous ratings display Unknown.
Menu portraits load their supplied animation atlases. Browsing keeps the normal
face; confirming a host song plays its selection animation, or its winning/losing
face fallback, before launch. Back cancels confirmation; navigation or search
cancels it and continues browsing. Launch checks import readiness again.
Type to search, use arrows to browse/change difficulty,
and hold Shift with Up/Down to move five matching songs. Tab or controller Select/Back
opens Library actions. Imported custom-menu scopes retain their authored presentation.
Imported mods display the same short package badge in Freeplay, Imported Mods and
category membership controls. It distinguishes identical package names without
renaming content. Search for four or more characters of a badge to narrow the view;
category and favorite filters still apply.

Host Library actions also offer **Grouping and sorting**. Group by mod or source
engine, or use a flat list. Choose group and chart order independently: default
authored chart order, alphabetical A-Z/Z-A, registry/engine order for groups, or favorites first
for charts, including **Recently played**. **Recently imported** orders mod/engine
groups by completed manual imports; automatic refreshes do not change that order.
Older imports without recorded history remain unknown. Preferences persist, and
sorting preserves the selected chart and difficulty. Play history begins when a song starts; previews
and canceled selections do not count. Older installs start with unknown history,
and unplayed songs sort after played songs. Search, categories and import locks
still apply. Best-score and authored-rating ordering support both directions.
Choose a **Comparison difficulty** in the sorting menu; it does not change the
selected play difficulty. Missing records sort last, and ratings stay in separate
scale blocks. The selected-song panel shows the value used for comparison. Scores
are raw saved host points, not a normalized ranking of player skill.
New or refreshed Psych/NV imports retain owner-local week order; NV Freeplay tabs
take precedence when supplied. Default chart order applies that sequence within
each mod's existing list positions, preserving default group order and the saved
registry. Unlisted songs follow in stable registry order. This does not apply
donor unlock rules or hide songs from the host library.
When an import refresh rebuilds Freeplay, or finishes while you are in gameplay
or another menu, returning to the same Freeplay view restores your search and
selected song by retained identity, even if its row has moved. The selected
difficulty returns only if still supported and present. Missing or ambiguous
selections show a notice, and pending imports stay locked. This temporary return
state is discarded when entering a different view and does not cross restarts.

## Freeplay library actions

In v0.0.27 development, press **Tab** or the controller **Select/Back** button in
Freeplay to favorite the selected chart, filter the view, or manage categories.
Categories can contain multiple mods, and a mod can belong to multiple categories.
Create or rename categories with the keyboard or the on-screen character grid;
add/remove mods from their membership list. Deleting a category preserves its mods,
scores and favorites. Selected category filters combine by union, then intersect
with favorites and song/mod search within the current view. Favorites show a `[FAVORITE]` label,
separate from difficulty stars, and are saved independently of imported files
and score slots. The host Freeplay category chooser includes **Favorites** and
**Category: <name>** entries spanning the installed library. Imported custom menus
keep their own scope. Freeplay remembers each chart's last manually selected
difficulty by name and restores it only while it remains supported and present.
Empty results cannot launch a hidden chart.
Re-importing an unchanged authored package from a different source folder retains
its chart identity and library metadata when its package identity and chart/audio
fingerprint uniquely match an installed owner. Different or ambiguous packages
remain separate. Uninstall/reinstall recovery is a separate roadmap milestone.

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

The first run downloads portable Haxe, Neko, Python and Git as needed. It uses
Visual Studio's C++ tools when installed, or downloads a portable LLVM-MinGW
compiler automatically. No administrator access is needed for the portable
tools. Internet access is needed for initial setup; missing Git is bootstrapped
as project-local MinGit. Double-clicking `run.bat` keeps its console open until
you press a key, while PowerShell and command-line runs return normally.
Close a game running from the selected build output before rebuilding it. A
separately extracted install can stay open during builds; close it before
replacing its executable. Successful Windows builds are cached by input
metadata; unchanged runs reuse the executable and still run every test. Use
`.\run.bat rebuild` to force a build. Automated gameplay checks are muted.
Failed builds or tests return a nonzero exit code. Tests requiring Linux-only tools or unavailable donor packages report
their skips explicitly.

Windows native import tests share a content-verified compilation cache between
test processes. Every behavior check still runs. Engine sources, libraries,
compiler inputs and executable hashes are checked before reuse; game assets
are not scanned for this cache. Set `CAMMIE_NATIVE_FIXTURE_CACHE` to choose its
directory (the default is `tmp/native-fixture-cache`).

Unlimited FPS uses a small native scheduler patch to the pinned Lime 8.3.2.
The first build fetches its exact source revision and compiles that library;
later builds reuse the verified cached binary. It requires no GitHub login.
Linux source builds also need Lime's native development dependencies, including
OpenGL, ALSA, X11/Xext/Xi/Xrandr/Xinerama and PulseAudio headers.

Use `.\run.bat` to build and play, `.\run.bat nobuild` to play the existing
build, or `.\run.bat test debug` to build and test with debug symbols.
To build, test and package the current development version:

```powershell
.\run.bat package
```

The ZIP and `SHA256SUMS.txt` are written to `dist/` only after the tests pass.
Packaging reads its default tag from `VERSION`; an explicit `--tag` on the
packaging tool or a tag argument to the Linux release script still overrides it.

Development metadata stays one patch above the newest published downloadable
GitHub build, including prereleases. Verify that build tag, then run
`python tools/development_version.py --latest-release <verified-tag> --apply`
to synchronize `VERSION`, `Project.xml`, and the runtime branding fallback. Repeating the command for the same
published build retains the same development version. Advance once after each
publication, without incrementing for ordinary edits, tests or builds. A
maintainer can still deliberately select an explicitly authorized release version.

On Linux, one command builds and packages a Windows x64 ZIP with the bundled
results screen:

```sh
./build-windows-release.sh
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
runtime files stay local and are excluded from Git automatically-including
future imports. Deliberate new engine assets in ignored folders require
`git add -f`; ordinary source-code changes do not.

New imports retain regular source files in `import-cache/` beside the game,
including executables, shared libraries and unknown formats. Only recognized
Apple `.DS_Store` metadata is excluded; ambiguous files are retained. Copies
are independent of the original folder and use bounded parallel workers with
integrity checks. When an engine update changes
the importer revision, outdated imports rebuild automatically while browsing
menus or Settings. Progress is shown there. The original folder is no longer
needed for those refreshes; keep the cache with the installation. Retaining
source uses additional disk space. Conflicting local edits stop a refresh and
leave the installed import intact. Imports created before source retention need
an initial migration; they are never silently overwritten.

Show FPS Counter displays the current FPS and a five-second rolling average,
with the average refreshed every half second. Unlimited FPS
removes the native frame cap; turning it off restores the selected finite cap.
Action input follows actual input updates even when several occur in one
millisecond. Existing compatibility script callbacks keep their 60 Hz clock.
In either options menu, Shift + Left/Right adjusts note offset by 20 ms.

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

Host Freeplay always pins favorites above other songs. Group and chart sorting apply within each section. Unselected tracks use compact rows; the expanded selection shows its source details and larger portrait.
