# Nightmare Vision native title and main menu port

Audit date: 2026-10-06
Donor: `../fnf_sources/NightmareVision`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`
Donor sources: `source/funkin/states/TitleState.hx`, `source/funkin/states/MainMenuState.hx`, `source/funkin/game/shaders/ColorSwap.hx`, and `source/Main.hx`.

## Native states

`NightmareVisionTitleState` follows donor create order: owner title init, random intro text, state script `onLoad`, `onStartIntro`, source art construction, base state creation, then the owner transition/plugin create hook. It keeps the donor's logo, girlfriend, Enter, Newgrounds, intro-credit timing, title callbacks, HSV hue control, skip flash, confirm delay, and two-press transition behavior. Its `introEndingText` remains a writable instance field for title scripts. The two title sprites share `NightmareVisionColorSwap`, which carries the donor's full hue, saturation, brightness, alpha, and flash API and its HSV fragment shader.

`NightmareVisionMainMenuState` uses the donor's `menus/menuBG`, `menus/menuDesat`, and four `menus/mainmenu/menu_*` atlases. It retains the camera-follow easing, item placement and selection animations, version text, input order, owner selection persistence, menu music ramp, flicker/tween effects, and `onCreate`, `onUpdatePost`, `onSelect`, and `onChangeSelection` callbacks. It uses the pinned donor version text `1.0`, `0.5.2h`, and `0.2.7`. A host build hash is omitted because it would identify the host checkout rather than this donor source.

Both states capture one `NightmareVisionStateSession`. They resolve image, atlas, music, and sound references through that owner's `NightmareVisionPaths` and asset cache. Required missing or undecodable art/audio raises a source-specific diagnostic; no Flixel fallback logo or beep is accepted. Source state-script requests and menu destinations use the owner's constructor factory, retaining redirects, reset behavior, and source transition overrides. Title static fields and menu selection are stored on the captured session, not shared process-wide state.

## Boundaries

`FlashingState` is provided by the source-state work. The existing host `FreeplayState` is reached through the selected owner's filtered-freeplay adapter; it is not the donor FreeplayState. `StoryMenuState`, `CreditsState`, `OptionsState`, `ModsState`, and `MasterEditorMenu` are not ported in this change and resolve to the explicit unported-state diagnostic (or a configured state redirect). The donor's OptionsState-specific `onPlayState` side effect is therefore not claimed. No rendered native title/menu parity or complete navigation parity is claimed here.

## Focused verification

`python tools/tests/test_nightmare_vision_native_title_menu.py` passed. The focused test compiles and executes the actual `NightmareVisionColorSwap` class against a minimal uniform host, compares its fragment source to the pinned donor text, and checks that both native states retain key source assets, callbacks, owner routes, and title field mutability. No full build or full regression suite was run by this port agent; the parent task owns the native build and full suite.
