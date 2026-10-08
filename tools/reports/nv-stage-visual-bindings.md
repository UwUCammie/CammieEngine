# Nightmare Vision stage visual bindings

The D-Sides Tricky stage failed early in `onLoad()`. The script adds the sky, then constructs `FlxBackdrop` for the optional error-sign layer and constructs another backdrop unconditionally for fog. The pinned Nightmare Vision `FunkinScript.preset()` exposes `FlxBackdrop` as a global, but the host's shared NV script seed did not. An unresolved bare constructor stopped the callback before the remaining layers and visual effects were created.

The script also imports `funkin.game.shaders.RGBPalette`. The pinned Nightmare Vision source revision contains `RGBGraphics`, `RGBShader`, and `UserRGB` in `RGBShader.hx`, but no `RGBPalette` class or symbol. D-Sides uses the imported value only through the `shader`, `r`, `g`, `b`, and `mult` members. The shared `PsychRGBPalette` has those channel setters and drives the same RGB mapping shader, so the host now binds that class to the legacy imported path. This is an explicit compatibility route for imported scripts; it does not claim that the path exists in the donor NV source.

`NightmareVisionStageVisualBindings.install()` now seeds the donor `FlxBackdrop` global, maps both qualified class paths through the interpreter's import and class-reflection scopes, and is installed by `PlayState.seedNightmareVisionCommon()` before script hooks run. Existing `BlendMode.SUBTRACT`, `FlxAxes`, and `FlxColor.BLACK` bindings were already present and did not cause this failure.

The focused test executes the import and constructor expressions in the real Nightmare Vision parser/interpreter. It checks palette channel values and shader uniforms, both backdrop constructor forms, and the same class tokens through Iris and `Type.resolveClass`. The test module passed 2/2 under forced Haxe eval.

Root verified Improbable Outset in an isolated, muted Windows runtime on 8 October 2026. The 60 FPS and unlimited runs each completed 30 seconds with exit 0. Reviewed captures show the carnival background, ground, actors, fog and blue palette; the stage callbacks have no detected script errors. Evidence: `tmp/v20-improbable-60-native-2.log` and `tmp/v20-improbable-unlimited-native-3.log`. The unlimited capture reports `unlimitedRequested=true`, draw/backend frame rate 0 and average FPS 1501. The private fixture retains donor stage and chart bytes. It includes only the dependencies needed for this stage check, so its fallback HUD icons do not establish full D-Sides HUD fidelity. This is a stage-rendering acceptance check, not a measured performance improvement.

Source evidence (SHA-256):

- D-Sides Tricky `script.hx`: `3BACB20702F7D06678436088C7F510276A470EA926FD34837754536A58FB8EAD`
- D-Sides Tricky `data.json`: `74069FD59A36151D6054290962E81B529FEF8D27BC9C2ABEDF92E66CD44501D5`
- Nightmare Vision `FunkinScript.hx`: `6D953FEFBE53EA2E8681DB0A10FAF3686484218AF2031741E299FCB2E2DA6EF1`
- Nightmare Vision `RGBShader.hx`: `CE54C0C21C920B6D92E05E09CD9F7971086D68A5AE8F382B1D26EE458796D0AF`
- Psych `RGBPalette.hx`: `CBA2183478B47984C14C5F0F7592EC0CE6CBCE05F27342A8E4A7DF8715FD597C`
