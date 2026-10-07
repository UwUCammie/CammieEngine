# NV source state session and constructor integration, 0.0.16 development

Pinned donor: Nightmare Vision
`733165c42ca71eb0961a70e4173b2d81ba4a29ea`.

## Implemented behavior

One captured session now carries the authenticated Mods family, selected Paths,
preferences, mod options/configuration, difficulty and persistent plugins through
source state requests. The existing common preset seeds gameplay, plugins and
state scripts; there is no second copy of the compatibility API. Source FlxG
views replace switchState/resetState with captured navigation, and CoolUtil
temporary transitions restore their captured pair after the native switch.

The factory constructs the intended state after old-state teardown, checks its
source class name against selected config, resolves an authorized redirect and
destroys the intended candidate before constructing the scripted replacement.
Missing redirect files warn and retain the intended state. Reset retains the
resolved constructor rather than re-evaluating the original redirect. Legacy
instance requests retain a fresh reset constructor instead of returning a
destroyed object. Base-state, base-substate and direct ScriptedState constructors
are bound to the same owner through construction and `.new` lookup.

Source MusicBeatState and MusicBeatSubstate execute their different donor timing
and callback contracts: states catch up crossed steps, while substates dispatch
one changed step with explicit step/beat arguments. State-local groups bind their
parent before constructor onLoad and retire without releasing the family. Failed
scripted-state loading requests a source fallback screen after native create.
State and substate script loading now returns typed `Missing`, `AlreadyLoaded`,
`ParseFailed`, or `Loaded` results. State loading checks `scriptGroup.exists` with
the resolved source path before setting `scriptName`; its `fromFile` source name
is the selected script name. Substate loading skips that path check and leaves
the `fromFile` source name at its resolved path. Missing files still run the
requested empty-group `onLoad`, while parse failures return before that callback
and transfer their failed handle to the wrapper for destruction. File scripts
execute against the current `FlxG.state` before registration; the wrapper
reparents the group before constructor `onLoad`. The loader mode is passed by
the state host explicitly, so a substate whose writable `scriptPrefix` is set to
`states` still skips the state-only path check and keeps the resolved path as
its module name.
Source swipe, fade and scripted transitions use the captured substate contract.
An absent scripted-transition file uses a source swipe so a missing file cannot
leave an outgoing switch without a completion callback. This is a deliberate
generic missing-file safeguard, not exact reproduction of the donor's discarded
SwipeTransition expression in its SCRIPTED branch.

Native TitleState and MainMenuState ports use source assets/callbacks, plus the
full source ColorSwap shader API. Flashing-choice and scripted-state fallback
screens keep private preferences and selected assets. Remaining native menu
destinations display an explicit unsupported diagnostic or accept a configured
redirect through the named factory. The existing default Freeplay adapter filters
to the selected package; it is not the source Freeplay implementation.

Gameplay service adoption and lease selection retain a family only for its
authenticated selected chart root. Foreign roots keep their actual identity.
An initial plugin redirect suspends the incomplete gameplay shell before actor
creation and update, then finishes its outgoing handoff immediately. Departure
retires plugin/assets/configuration before unrelated state creation, restoring
the prior native presentation. Source state-local destruction does not retire
the retained session.

## Verification

Final runtime/build hashes and full results are recorded in
`tmp/nv-source-state-checkpoint.json`.

- Windows build: `tmp/nv-state-build-accepted.log`.
- Final full suite: 2,382 tests across 779 modules in 376.3 seconds, with 343
  existing platform/corpus skips and zero failures
  (`tmp/nv-state-full-tests-final.log`). All 23 development/API policy checks
  passed (`tmp/nv-state-policy-final.log`). These gate timings are not a
  build/test speed improvement claim.
- Factory, state/substate, native title/menu/ColorSwap and session bindings have
  focused interpreter/extraction fixtures. The title/menu checks pin source
  routes/assets/callbacks; ColorSwap executes its actual setters and compares
  the shader with the pinned donor. They do not prove stock menu rendering.
- State/substate loading has focused extracted-wrapper tests for missing,
  parse-failed, path-name and repeated-load behavior, plus a real Iris `fromFile`
  fixture extracted from `createScriptAt`. It checks `.hxs` resolution, the
  state full-path and unextended fallback checks, substate repeated loads,
  the substate `scriptPrefix='states'` edge, top-level parent timing,
  registration, onLoad reparenting, and failed-handle ownership.
- The initial full suite found three stale extraction boundaries: demo update's
  startup flag, scroll initialization's source session/base create boundary,
  and the expanded constructor binding fixture. They were repaired without
  weakening cases, timeouts or skips. The speed fixtures also assert that a
  pending source redirect skips incomplete gameplay initialization/control work.
- Muted native generated two-package checks passed at 60/unlimited FPS:
  `tmp/nv-state-native-60-accepted.log` and
  `tmp/nv-state-native-unlimited-accepted.log`. They execute plugin selection
  before title construction, captured base/substate/direct-script constructors,
  selected-package redirect, constructor onLoad/create/destroy, two resets after
  config mutation, missing redirect fallback, completion of a missing scripted
  transition, and unrelated-owner cleanup. Both logs contain zero source-script
  errors. Four framebuffer captures were reviewed after transitions completed.
- Required donor audit: `tmp/nv-state-source-audit-final.log`. The 70 protected
  source/settings/metadata inputs retained their hashes.

## Remaining contracts and next package

Phase 2 remains open. The session currently boots from gameplay integration;
complete source Init/bootstrap before imported-menu entry still needs wiring.
The native checks construct an authorized generated family directly, rather
than certifying the complete retained-import-to-menu pipeline. They render a
scripted title and a native title whose authored onStartIntro overrides the stock
art. They do not certify stock title/main-menu visuals or all menu input/audio,
whole-chart Feaster reset, or gameplay roundtrips across the real corpus.

Source Freeplay/Story/Credits/Options/Mods/editor states, source class inheritance
and broader state/substate imports, legacy asset profiles and full menu vocals
ownership remain incomplete. The private option edge cases and complete
profile/core behavior from the previous checkpoint stay open. Generic source
menu timing at unlimited FPS needs broader authored-script coverage beyond the
constructor and transition checks here.

Next: finish the source Init/session entry and script-load contracts, verify real
retained importer publication into the source state graph, then port missing
destinations and perform representative native menu/gameplay roundtrips. No
chart/mod-specific production branches, authored asset changes, quality reduction
or release publication are part of this checkpoint.
