# HXC mounted adapter audit

This report records the engine-level contracts used by the selected mounted HXC
content. Donor `.hxc` files remain read-only and are never executed as foreign
classes.

## Mixed Rabbit Hole source

`rabbit-hole.hxc` contains both `RabbitHoleOptions` (`Module`) and `RabbitHole`
(`Song`). The importer selects the Song lifecycle while registering the option
class as a companion. Its `rabbit_hole_settings.shadersEnabled` value is carried
through the generated namespaced store. Bloom is created by the native shader
owner and attached to exactly `camHUD` and `camGame`; the option gate defaults
to disabled.

## FPS Plus CharacterInfoBase

Literal `info.*`, `setSparrow()`, `offset`, `loop`, `addByPrefix`,
`addByIndices`, and `addExtraData` calls become detached metadata. The native
Character owns atlas loading, animation offsets/FPS/loop/index lists, focus
offsets, and reposition data. The donor constructor and helper objects are not
instantiated.

## Runtime shader safety

Song-owned shader descriptors receive an opaque native handle. Fragment paths are
resolved only below the selected `assets/imported_mods/...` root; absolute paths,
traversal, unknown cameras, and undeclared uniforms are rejected. Filter arrays
are mutated by exact filter identity and restored on song end, destroy, retry,
or active-state cleanup. Uniform writes, enable/disable, pulse, pause, resume,
reset, and clear operations stay on the binding owner. A recognized shader does
not mark an unsafe donor callback safe: a synthetic shader-only lifecycle hook is
emitted and dropped donor operations remain diagnostics.

The standalone `vignette.hxc` wrapper is a data-only/no-op declaration because
the native Vignette event handler already owns its shader lifecycle. Markov's
bounded `StaticShader` contract preserves `iTime`/`alpha` writes and the
`funnyGlitch` pulse without importing the donor camera/filter graph.

Regression coverage is in `tools/tests/test_hxc_round22_adapters.py` and uses
the mounted Rabbit, Whitty, Markov, and Vignette sources plus a synthetic gate
host.
