# Nightmare Vision source state factory core

Donor contract: `fnf_sources/NightmareVision`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, as recorded in `nv-source-title-transition-contracts.md`.

`NightmareVisionStateFactory` accepts requested-state constructor closures. It constructs the requested class first, asks its typed host for the source simple class name, then resolves `stateRedirects` through the selected owner's path lookup. A configured path with no script emits the host diagnostic and leaves the requested state alive. A present script destroys the requested state before the host constructs its owner-scoped scripted wrapper. The returned constructor is retained for `resetState`, which reuses it directly. Null constructor results return before class-name or redirect lookup.

The host wrapper constructor owns script binding and `onLoad` order. The core calls it only after the original state is destroyed; host integration must bind the wrapper's parent before invoking `onLoad`. The core contains no Flixel or source interpreter dependency, so its factory rules run in a recording-host Haxe interpreter fixture.

`switchWithTransitions` follows donor `CoolUtil.switchState`: capture both current values, set the temporary pair, request the state switch, then register a post-switch callback to restore the captured pair. Nested calls each capture and restore their own values in callback registration order.

Focused verification: `python tools/tests/test_nightmare_vision_state_factory.py -v` passed 2 tests. The Haxe interpreter fixture covers construction and redirect ordering, native fallback for missing scripts, reset constructor retention, nested `onLoad` requests, null constructor results, and temporary transition restoration. This verifies the factory core; a native host and rendered menu flow remain integration work.
