# NV source Splash integration

Pinned donor: Nightmare Vision `source/Splash.hx` at
`733165c42ca71eb0961a70e4173b2d81ba4a29ea`.

`NightmareVisionSplashState` remains a native `FlxState`, separate from the
MusicBeat states. Its captured host provides selected-owner `NightmareVisionPaths`,
private owner-save reads, a startup-state constructor, and a state-switch closure.
The switch closure receives a constructor that reads the current
`Main.startMeta.initialState` when Flixel invokes it, preserving the source
factory timing after Init has queued the switch.

The state disables auto-pause during the intro and restores its captured value
on completion or external departure. After one second it attempts the selected
owner's `videos/intro` on C++ builds through `NightmareVisionVideoSprite`, the
shared owner-scoped decoder used by source video imports. It preserves format,
end, and delayed-start callbacks, and passes its mute option when the native
sound manager or selected owner's saved mute field is true. A missing path,
unavailable decoder, failed load, or
non-C++ target falls back to watermark branding. Cleanup checks the video handle
before stopping or destroying it, so early keyboard skips and decoder absence
do not hit the donor's null-video edge.

Branding lists files from the selected package and its captured core, removes
directories, selects one using Flixel's random source, and loads the matching
`images/branding/watermarks` graphic. Pixel suffixes disable antialiasing. The
source 0.8 screen-fit scale, one-second start, four squash/stretch/settle/fade
steps, elastic and quad easing, `sounds/intro` playback, and final 0.8-second
wait are retained. An empty result completes instead of trying to center a null
graphic.

Completion restores `mute` and `volume` from the private owner-save fields, with
the source defaults of unmuted and full volume when an owner has no saved value.
Every created timer, branding tween, delayed video start, and video handle is
retired on completion and state destruction. Unexpected departure also restores
owner audio and captured auto-pause. The feature does not change update or draw
frame rates. Native muted checks must seed the selected owner `mute` value as
true, so the source volume restore cannot unmute the probe.

The focused regression extracts the actual production class and executes the
branding, timing, easing, skip, save-restore, unexpected-departure cleanup, and
late-bound initial state constructor against narrow Flixel service stubs. It
also enables the extracted C++ branch under a test-only define and runs the
shared video-wrapper contract with a narrow stub, covering the muted option,
format/end callbacks, delayed start, missing decoder, load failure, and an
already-ended callback. It checks that unlimited FPS values are untouched and
the private mute value stays true. The parent task's Windows build verifies
the real C++ integration. The retained startup native probe skips Splash, so
actual Splash video decoding and branding rendering remain unverified.

No donor files, mod assets, charts, or authored content were changed.
