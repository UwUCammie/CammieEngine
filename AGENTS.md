# AGENTS.md

Guidance for working in this repository. Everything below was verified against the working tree, which differs enormously from the last commit (see [Repo state and gotchas](#repo-state-and-gotchas)).

## What this is

Friday Night Funkin' **Disappointing Plus**: a HaxeFlixel 6.1.2 fork of Modding Plus (itself derived from base FNF), kept deliberately old-school. The engine surrounds gameplay with an HScript interpreter used for stages, characters, cutscenes, UI layouts and per-song modcharts, and ships a huge library of ported community content (~1,300 song folders, tens of GB of media). The current game version lives in `Project.xml` (`<app version=...>`) and user-facing changes are logged in `updateLog.txt`. `CHANGELOG.md` is the inherited base-game changelog; do not add to it.

## Commands

### Build and test (Windows 11)

From PowerShell in the repository, ` .\run.bat test` builds Windows x64 and
runs the full regression suite. ` .\run.bat package` also packages the v0.0.10
alpha ZIP and checksum in `dist/`, after successful tests. ` .\run.bat` builds
and plays; ` .\run.bat nobuild` plays the current build. Add `debug` for a debug
build. Close the game before building.

Portable Haxe 4.3.6, Neko 2.3.0 and Python are bootstrapped into `.tools/`.
MSVC is preferred when installed; otherwise a checksum-verified native
Windows LLVM-MinGW compiler is downloaded without administrator access.
Git for Windows is required for initial git-backed haxelib setup. Batch files
must use CRLF (enforced by `.gitattributes`). Extensionless native Haxe/haxelib
copies keep the existing interpreter probes compatible with Windows.

### Build and run (Linux, supported path)

`./run.sh` is the canonical workflow. Do not hand-roll haxelib setup.

```bash
./run.sh          # release run; rebuilds only when inputs changed
./run.sh debug    # debug build + run
./run.sh build    # build if needed, no launch (also: ./run.sh build debug)
./run.sh rebuild  # force a build, no launch
./run.sh nobuild  # skip build/setup entirely, just run the binary
./run.sh server   # start the Haxe compilation server (port 6000)
```

On first use it downloads portable Haxe 4.3.6 + Neko into `.tools/`, installs pinned haxelibs into `.haxelib/` (lime 8.3.2, openfl 9.5.2, flixel 6.1.2, flixel-addons 4.0.2, flixel-ui 2.6.5, flixel-animate 1.5.0, hscript 2.5.0, hxvlc 2.3.1, tjson, hscript-ex and discord_rpc from git), then does four things on every run that look surprising but are intentional:

- Lowercases `assets/data` folders and hardlinks case mirror folders under `assets/songs` for each chart's `song` field. The engine lowercases chart lookups but uses exact case for audio paths, and Linux is case-sensitive.
- Rewrites `Project.xml` so large asset folders are not embedded.
- Patches haxelib sources: discord_rpc's bundled rapidjson (gcc >= 15 rejects it) and flixel 6.1.2 `FlxSprite.checkEmptyFrame` (adds a 1x1 fallback frame to prevent a SIGSEGV on empty sprites).
- Takes an exclusive flock via `tools/runtime_lock.sh` so a build can never overwrite `lime.ndll` while a game instance has it mapped. Never build while the game runs; let run.sh wait.

If builds act stale after changing `Project.xml` or defines: `pkill -f 'haxe --wait'` then `./run.sh server` again. Start the compile server (`./run.sh server`) to skip re-typechecking and save significant time per build.

Direct commands (only with the run.sh env: `HAXEPATH`, `NEKOPATH`, `HAXELIB_PATH`, `LD_LIBRARY_PATH`):

```bash
haxelib run lime build linux -debug   # or: ... build linux, add --connect 6000 when the server runs
```

Binary lands at `export/release/linux/bin/Funkin` (debug: `export/debug/linux/bin/Funkin`). The game's working directory at runtime is that `bin` directory, so runtime reads/writes are relative to it (e.g. the live settings file is `export/.../linux/bin/assets/data/options.json`). run.sh backs up and restores that live file across builds because lime's asset sync would otherwise overwrite it with the repo seed.

### Tests

```bash
python3 -m unittest discover -s tools/tests   # serial full suite; hundreds of tests, several minutes
python3 tools/run_tests.py                    # same modules in parallel for faster local feedback
```

There is no Haxe test framework. `tools/tests/*.py` are `unittest` suites that either extract methods/classes from `source/*.hx` and compile them standalone with the portable interpreter (`.tools/haxe/haxe ... --interp`), or validate real assets, registries and HScript files (some tests also read `.haxelib/hscript/2,5,0`). When you change engine behavior, add a test in this style; these tests are what pin the ported-content regressions. Requires `.tools/haxe`, so run `./run.sh` (or at least its toolchain bootstrap) once after cloning.

### Port tooling (`tools/`, Python 3)

- `validate_ported_songs.py`: cross-checks charts, registries, audio and UI packs against the engine's actual resolution rules. Exits 1 on errors.
- `audit_port_assets.py <donor_root>`: reports recoverable omissions versus the donor installation that this content was imported from, plus static asset references.
- `repair_imported_assets.py [--apply]`: restores missing media/scripts from the donor without overwriting ported work (dry-run by default).
- `launch_cache.py`, `runtime_lock.sh`: used by run.sh, described above.

## Architecture

### Entry and state flow

`source/Main.hx` creates `FlxGame(0, 0, TitleState, ...)`. States are swapped with `LoadingState.loadAndSwitchState(...)` (uses `FlxG.switchState` directly; `ChartingState` gets a wrapper state first). Typical flow: `TitleState` -> `MainMenuState` -> `FreeplayState` or `StoryMenuState` -> `ModifierState`/`ChartingState` -> `PlayState` -> `VictoryLoopState`/`GameOverSubstate` -> menus. `CustomStateState.hx` maps custom-menu names to states.

`MusicBeatState` is the beat-synced base class for states. It derives `curStep` from `Conductor` plus the BPM-change map and fires `stepHit()`/`beatHit()` for every step crossed in a frame (capped by `maxStepCatchUp`, set to 0 for demo playback). Never "optimize" this back to firing once per frame; single-step modchart events get eaten otherwise.

### Assets

`Paths.hx` (library/preload paths) and `FNFAssets.hx` (direct disk reads plus writes) are the asset layer, with `CoolUtil` helpers. On native targets `FNFAssets` prefers a disk path from the asset manifest and otherwise reads the filesystem; `isInScope` rejects paths outside the game cwd. JSON goes through `CoolUtil.parseJson` -> TJSON, which tolerates comments and trailing commas (that is why many `.json`/`.jsonc` files here are JSONC). `CoolUtil.parseJson` throws on null input on purpose: TJSON.parse(null) segfaults native builds.

Audio extension is `TitleState.soundExt` (`.ogg` on native). `CoolUtil.getSongFile` resolves audio case-sensitively as `assets/songs/<song>/<song>_Inst.ogg`, then `assets/songs/<song>/Inst.ogg`, then `assets/music/<song>_Inst.ogg` (same for Voices).

### Chart loading (`Song.hx`, `DifficultyManager.hx`)

Charts live at `assets/data/<lowercased song folder>/<lowercased json name>.json` and are shaped `{"song": {...}}`; `Song.SwagSong` is the chart schema (notes, bpm, speed, player1/2, stage, gf, uiType, cutsceneType, mania/preferredNoteAmount, stageID, ...). For a non-default difficulty, `Song.loadFromJson` first loads that difficulty's `defaults` chart (mapped in `assets/images/custom_difficulties/difficulties.json`, e.g. `erect`, `nightmare`, `pico`) and then overrides **only** song/notes/bpm/needsVoices/speed/mania from the requested chart. Character, stage, UI and cutscene fields must be edited in the default chart, not a hard-only file. When fields are missing, `Song.loadFromJson` infers legacy defaults from the song name (hardcoded base-game tables) before parsing is done.

### PlayState and HScript

`source/PlayState.hx` (~5,000 lines) is the core. It loads a song's companion files from its chart folder: `modchart-<default>.hscript` if present, else `modchart.hscript`; `events.json` (psych-format events), `noteInfo.json` (custom note definitions), dialogue files, `preload.txt`.

The HScript API is assembled in `PlayState.makeHaxeState`/`makeHaxeStateUI`/`makeHaxeExState`. Scripts get hooks (`start`, `songStart`, `onEvent`, `beatHit`, `stepHit`, `update`, `onPause`/`onResume`, `playerOne/TwoTurn`, `playerOne/TwoSing`, `playerOne/TwoMiss`, `noteLoaded`, `noteHit`, ...), engine objects (`boyfriend`, `dad`, `gf`, `camHUD`, `currentPlayState`/`PlayState.instance`, `stage`, `iconP1/P2`, `vocals`, ...), helpers (`addSprite` with layer constants, `soundPlaySafe`, `addCharacter`/`switchToChar`, camera helpers) and the `updateUV`/`getUV` universal variable map. Song events reach HScript `onEvent` before `PlayState.triggerEventNote` handles built-ins, and legacy chart events (sectionNotes rows with noteData `-1`) are merged with psych `events` arrays by `SongEvents.hx`.

The same interpreter is used for custom characters (`Character.hx`, optional `<char>.hscript`/`.json`), stages (`StageHelper.hx`), cutscenes (`VideoCutscene.hx`), UI layouts and custom note behavior. `PluginManager` seeds global script variables and can load extra hscript-ex plugin classes from `assets/scripts/plugin_classes/` (listed in `classes.txt`, currently empty; `RunningTankman.hx` there is not loaded). `source/plugins/ExamplePlugin.hx` documents the script-facing API and is only compiled with `-Dtypebuild`.

### Custom content registries (`assets/images/` and `assets/data/`)

- `custom_chars/custom_chars.jsonc` (plus `icon_only_chars.json`): every playable/opponent character must be registered here with colors/icons; each entry can point at a folder with `char.png`/`char.xml`, icons, portraits and an optional HScript/JSON.
- `custom_stages/custom_stages.json`, `custom_cutscenes/cutscenes.json`: registry name -> folder/script.
- `custom_difficulties/difficulties.json`: difficulty list, display names, icon animations and `defaults` chaining.
- `custom_ui/`: `ui_packs/ui.json` (map of uiType -> note/splash/healthbar pack), `ui_layouts/<name>/<name>.hscript`, `custom_notes/`, `dialog_boxes/`, `custom_countdowns/`.
- `freeplaySongJson.jsonc` (freeplay categories, display name -> `character` key, week) and `storySonglist.json` (story mode; `storySonglist-week-by-week.json` exists but nothing loads it). New songs/difficulties must be registered; `DifficultyManager.addSongSupport` scans `assets/data/<song>/<song>.json` plus `<song>-<diff>.json` at runtime.

### Module/import system

`ModuleState.hx`, `ModuleFunctions.hx`, `ModPlusCarryState.hx` and the `New*State.hx` files implement in-game import/export of songs, stages, characters and weeks, including psych-format chart/character conversion. `ModuleFunctions.psychCharDecode`/`psychToDisChar` generate HScript for imported characters.

### Options and saves

`OptionsHandler.options` is cached in `FlxG.save.data.options` but persisted to `assets/data/options.json` relative to the runtime cwd; the repo copy is the seed. Options definitions/visibility are in `OptionsHandler.hx` (option list + save-data mask). `PlayerSettings.hx` holds control schemes.

## Repo state and gotchas

- **The working tree is a giant uncommitted port.** Roughly 12.8k untracked files (most of `assets/data`, `assets/images`, `assets/music`) plus ~150 modified tracked files. Never `git checkout -- .`, `git clean -fd`, mass-revert, or bulk-format; you would destroy the imported library. Read `tools/reports/port-assets.md` for where the import stands.
- **Assets are enormous**: `assets/music` ~18 GB, `assets/images` ~16 GB, `assets/songs` hundreds of MB; a build copies them to `export/...` (~35 GB). Never write code that scans, hashes or embeds these trees at build time. Follow the metadata-based approach in `tools/launch_cache.py`.
- **Backup junk exists and is not live**: `source/VictoryLoopState (2).hx` (duplicate of `VictoryLoopState.hx`, not a compilable module name), `assets/data/**/modchart - Copy*.hscript`, `*- copy.json`, `front - Copy.png`, etc. Do not edit them expecting an effect, and do not treat them as the source of truth.
- **Case sensitivity matters on Linux.** Chart folders/files are lowercase; `assets/songs` gets exact-case hardlink mirrors created by run.sh for the chart `song` field; custom char/stage/script paths are case-sensitive. Use the exact case from registries and chart fields.
- **HScript compatibility shims are deliberate.** Names like `timeBarBG`, `judOffsetX`, `iconsVertical`, `forceCamera`, `hscriptSafePlay`, `showOnlyStrums` and many "old-engine alias" comments exist because hundreds of ported scripts reference them. Do not delete or rename them as dead code.
- **Memory management in `Main.hx` is load-bearing.** It prunes dead `FlxSound`s and clears the bitmap cache when leaving PlayState. Removing it reintroduces multi-GB growth and native SIGBUS crashes on rapid scene switches. `PlayState.hscriptSafePlay`'s decode/cache/timing behavior is similarly a crash fix for ported modcharts; do not simplify it.
- `export/`, `.tools/`, `.haxelib/` are gitignored. Never commit build output, and remember `.haxelib` is locally patched by run.sh.
- `docs/` is generated API documentation (`builddocs.bat`: `lime build html5 -xml -Dtypebuild` then `haxelib run dox`). Do not hand-edit, and do not assume it reflects the working tree.
- `dump/decoding_error.txt` is captured debug output, not source.
- `Modding.md` describes a planned Polymod `mods/` folder loader. There is no Polymod dependency and no loader in `source/`; `example_mods/` is just packaged as `mods/`. Actual modding today is HScript + the registries above.
- CI (`.github/workflows/*.yml`, `azure-pipelines.yml`) builds with Haxe 4.2 and predates the local toolchain; local truth is `run.sh` (Haxe 4.3.x, pinned libs).
- Update `updateLog.txt` for user-visible changes (recent project commits routinely do this and little else).

## Style

- Tabs for indentation, one class per PascalCase `.hx` file whose name matches the class (the `VictoryLoopState (2)` stray aside). `source/` is flat except `plugins/` and `shaders/`.
- The codebase is intentionally informal (`daSong`, `swagShit`, `coolTextFile`, comment prose). Match surrounding style; do not clean up names or comments.
- `hxformat.json` exists but formatting is inconsistent, and there is no wired-up lint/format command. Do not reformat unrelated code.
- JSON(C) under `assets/` is hand-maintained with comments and trailing commas in places; preserve existing formatting and register new content in the correct registry rather than inventing new paths.
- Tests: add Python `unittest` coverage in `tools/tests/` for engine behavior changes, using the extract-and-interpret pattern; run the whole suite from the repo root before finishing.
