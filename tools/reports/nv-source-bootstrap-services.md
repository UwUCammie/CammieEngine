# Nightmare Vision owner-scoped bootstrap services

Pinned donor: Nightmare Vision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.
The service layer follows `source/Init.hx` and is called by the typed bootstrap
host at its existing step boundaries. It does not own state construction,
preferences/highscores loading, Discord, Mods population, startup metadata, or
the source plugin-script host.

`NightmareVisionBootstrapServices` installs the donor Flixel settings, the
ratio scale mode, persistent source music, the source default antialias value,
and owner-local HotReload, DebugText, and FullScreen plugins. Hot reload uses
the source Controls getters and owner reset/repopulate/config callbacks. Hard
reload clears the selected `NightmareVisionPaths` cache just before source
state creation. Fullscreen writes the source `fullscreen` field through the
owner save callback on every plugin update and does not flush storage there.

Global settings retain their pre-owner values and are restored only if their
current values still match the values installed by this source owner. The
service captures the native sound shortcut arrays in its constructor and
exposes `applySourceSoundKeys`, which must run after source controls reload and
before the later Flixel configuration step. It also captures global sound
volume and mute state before ClientPrefs load; `applySourceAudioPreferences`
records the last source values it set and restores each original value only
when that value is still unchanged at teardown. It pauses and temporarily persists
borrowed host music while source states run, then restores and resumes it only
when Flixel still points to this owner's music handle. Owner plugins and their
signals are removed during release.

`FlxKeyManager.preventDefaultKeys` is declared as generic `Array<Key>` and
hxcpp stores it as `cpp::VirtualArray`. The service keeps the source `[TAB]`
assignment typed, then captures the actual stored field container through
`Reflect.field`; teardown restores the prior raw container only while both the
original key manager and source container remain current. This preserves
container identity as well as the key values and leaves later-owner replacements
untouched.

`NightmareVisionSound` keeps the donor muted transform behavior on the source
music instance. `NightmareVisionRatioScaleMode` keeps the donor design-size and
camera resize behavior. The source interpreter's `trace` binding is installed
only after the donor FunkinScript and DebugText steps. The interpreter also
gets owner-local `Iris.warn`, `Iris.error`, and `Iris.print` bindings, with the
donor yellow, red, and white DebugText colors. These calls use the unchanged
`Iris.logLevel` for console output; no process-global Iris callback is
assigned. Module and callback failures can use
`reportError(name, callback, error)`, which writes to the console immediately
and queues its red DebugText message until the owner's DebugText group exists.
The interpreter's optional `sourceError` callback routes its internal unknown-
member diagnostic through the same owner red DebugText and Iris console path.

The owner facade handles explicit source `Iris` calls. The donor's compiled
`funkin.backend.Logger` is not a source preset binding, so this service does not
provide a partial Logger imitation.

Feature mapping follows the host project. The donor gates video initialization
with `VIDEOS_ALLOWED`, which the host does not define. The host includes hxvlc
for CPP and already uses `NightmareVisionVideoSprite`, so its bootstrap invokes
`Handle.init()` under `#if cpp`. LibVLC is a process-wide shared singleton; the
service does not dispose it when an owner exits, since native video users do
not expose owner leases. Source states must destroy their owned video sprites
before releasing Paths. `FEATURE_DEBUG_TRACY` is absent in the host; the
conditional service method does nothing when that donor feature is disabled.

The DebugText font is resolved through the selected source Paths and remains a
required source asset. Source-package fixtures must include the donor Consolas
font rather than substituting a native font.

Focused verification:

- `python tools/tests/test_nightmare_vision_bootstrap_services.py -v`: 2 passed.
  It compiles the new modules against the pinned HaxeFlixel 6.1.2 classes and
  exercises owner validation, trace-step gating, source hot-reload order, and
  the real Flixel pre-state-create signal. Its key-container regression verifies
  exact raw identity and values on restore, and ensures replacement containers
  and replacement managers survive teardown. It also checks buffered module
  errors, the owner-local Iris facade, donor colors, and console output.
- `python tools/tests/test_nightmare_vision_source_diagnostics.py -v`: 1 passed.
  It executes an unknown member call in the real NMV interpreter and verifies
  owner red DebugText plus console output.
- `python tools/tests/test_nightmare_vision_bootstrap.py -v`: 2 passed. This
  pins the surrounding pure bootstrap call order and startup constructor route.
- A small C++ target code-generation attempt stopped in hxcpp setup because the
  environment has no configured Visual Studio toolchain (`HXCPP_VARS`). No
  application build or full test suite was run.

`NightmareVisionStateSession.initializeSourceControls` creates this service
before source preferences load. Its preference reload applies source audio
values and sound-key arrays through the scoped service. `NightmareVisionInitHost`
calls the public service methods at donor Init boundaries, and the source state
session releases the service during teardown. These focused checks do not
establish a complete retained-import-to-title runtime roundtrip or stock
source-menu visual parity.
