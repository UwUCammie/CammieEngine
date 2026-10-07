# Psych Language and Discord integration

This Phase 2 checkpoint targets Psych 1.0.4 source revision
`5c67ced49e5a98535298a6daa3f8f4ec79ac8399` and is included in the authorized
v0.0.16 alpha release. It extends compatibility without claiming the full
roadmap or compatibility gate is complete.

## Engine rule

Language and Discord Lua callbacks, plain/embedded HScript imports and class
reflection reach captured services rather than separate implementations.
`PsychSourceOwnerAccess` authenticates the calling owner for achievements and
standard services. `PsychAlphabetOwnerAccess` supplies the same glyph resource
factory to gameplay and language reloads. `SourceClassFieldDiscovery` composes
field discovery for achievements, language and Discord.

Language parsing preserves source line order, key normalization, numbered
substitution, defaults, file translation and the owner glyph reload side effect.
Maps persist across same-owner scopes; each new gameplay state reloads once,
and captured methods reject calls after owner departure. Achievement popup
phrases use this language service without retaining the gameplay state.

Psych source Discord requests use the existing shared daemon. All providers
in one gameplay session share a lease, while each provider has a guard facade.
Requests and scalar snapshots are detached and retained before initialization.
Release restores identity and presence independently only when their revisions
still belong to the lease. Later external writes survive. The ready callback
records the real menu baseline and seeds presence without falsely marking a
queued identity change as applied. An absent baseline clears activity instead
of inventing menu data.

The importer publishes authored `.lang` files from authenticated package
data/library scopes and chart-free global providers. Files keep their names,
bytes and separate scopes; existing output edits are preserved. Psych import
revision advances from 2 to 3 so existing snapshots can regenerate these files.
Complete retained-source snapshots are unchanged.

## Evidence

The final build is `tmp/release-v0.0.16-build-final-2.log`; binary hashes are in
`tmp/release-v0.0.16-build-gate.json`. Earlier compilation diagnostics are kept
in the preceding release build logs.

Muted native retained-import checks at 60/unlimited FPS use actual published
owner receipts, source Iris, translated Lua and native-class reflection. They
verify shared/root language precedence, translation/interpolation, shared
runtime reuse, explicit language reload, source RPC images/plain details and
millisecond-to-second timestamp handling, nil client-ID reset, released-handle
rejection and state-switch restoration. The native ready-state record is
exercised without connecting to an external Discord client. These are native
component and marshalling checks, not external Discord UI certification or
whole source gameplay/menu acceptance.

Receipts and final full-suite/preservation results are in
`tmp/psych-standard-checkpoint.json`. The full log is
`tmp/release-v0.0.16-full-tests-native.log`. The earlier suite passed the production
contracts but failed one collision-naming assertion that pinned the old Psych
revision. That test now checks its minimum naming revision; the separate
revision test still requires language-publication revision 3. Focused evidence also covers importer
filesystem copies, source parser/bindings, shared RPC ready/clear/restart cases,
existing presets/glyphs and disconnected audit routes.

The subsequent Windows eval overlap timeout is retained in
`tmp/release-v0.0.16-full-tests-final.log`. Windows now executes that complete
case in the actual C++ filesystem fixture, with setup/cleanup and every overlap,
publication and handoff assertion retained. Linux continues its eval check.
The native module keeps a route/checkpoint guard so the actual overlap runs once;
the combined 39-test manager/native group passed with one pre-existing skip for
a separate eval case. No timeout increase or overlap skip was introduced.

The clean ZIP was checksum-verified and extracted to a fresh private runtime.
Muted Tutorial checks passed at 60/unlimited FPS with isolated saves, and the
package options were restored. Package/version/binary checks and both results
are recorded with the checkpoint. Local installed imports and source snapshots
are excluded by the packaging policy.

The static inventory now finds all 246 registered Lua callbacks in the pinned
Psych constructor. It traces the real guarded handoffs to achievements,
language and Discord. This exposure count is separate from per-feature
behavioral/native acceptance; it does not certify every reflective class or
historical Psych fork.

## Remaining work

Full enabled-Psych-Mods ordering and source build-feature profiles remain open.
Raw source `assets/translations` asset rename mappings are not yet interpreted;
the import report records the pinned `Project.xml` evidence. Wider Mods merging,
source application construction, Discord initialization/prepare/shutdown and
loadModRPC facade methods, achievement award/gallery flows, other source APIs,
imported entry/menu acceptance, library/freeplay work and measured performance
gates remain open. Shared importer language-scope discovery can also be factored
further while preserving each transaction's cancellation and ownership policy.

Production fixes contain no chart/mod-specific branches and preserve authored
content. Continue the roadmap on v0.0.17 after publishing the v0.0.16 build.
