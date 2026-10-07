# Psych Discord ownership and callback contract

The Discord facade follows `FNF-PsychEngine/source/backend/Discord.hx` at donor commit `5c67ced49e5a98535298a6daa3f8f4ec79ac8399`. The pinned donor file SHA-256 is `7B37504A267E160B4D48F37FE856F81FA7D70A0598D3F6A73DADB3D68AF635C4`.

Psych registers Lua globals named `changeDiscordPresence` and `changeDiscordClientID`. The presence callback signature is `changePresence(details = 'In the Menus', ?state, ?smallImageKey, ?hasStartTimestamp, ?endTimestamp, largeImageKey = 'icon')`. Details and state pass through unchanged; the third argument maps to the small image key, the last argument maps to the large image key, and the version text is `Engine Version: 1.0.4`. A null ID resets to `863222024192262205`. The source text concatenates `"Engine Version: "` with the donor's `1.0.4` version, including one space after the colon.

The donor's timestamp implementation treats `Date.now().getTime()` and `endTimestamp` as raw milliseconds, adds the supplied end value directly to the start value, then truncates both after division by 1000. This can make a positive `endTimestamp` appear as a zero- or one-second difference. The host preserves that observed arithmetic instead of interpreting the argument as seconds. An omitted end value resolves to zero.

`PsychDiscordClient` is an owner-guarded source facade. `PsychDiscordBindings.installLua` installs the two Lua callback names; `install` exposes the `backend.DiscordClient` import; and `installScope` maps the same source statics through the real `SourceNativeClassScope` and shared `SourceClassFieldDiscovery`. `clientID`, `isInitialized`, `changePresence`, `changeDiscordClientID`, `resetClientID`, and `updatePresence` are exposed. A provider's `release()` retires only its own facade; `PsychStandardServices` owns the shared lease and releases it when the source owner departs.

The engine continues to use one `DiscordRpcLifecycle` and one daemon. `DiscordClient` now retains a cloned request and its presence/identity revisions before daemon initialization. Snapshots and queued messages receive fresh objects containing only scalar rich-presence fields, so callers cannot mutate the retained or queued values. Presence and identity restore separately compare their expected revision; a later external write to either field wins without preventing restoration of the still-owned other field. Restoring an absent baseline queues an explicit clear and keeps reconnects from inventing a menu activity.

The bundled `hxdiscord_rpc` wrapper does not expose a named clear method. Its only activity operation calls `linc::discord_rpc::update_presence`, which zero-initializes `DiscordRichPresence` and invokes `Discord_UpdatePresence`. The host represents absence with that empty presence update on the existing daemon; no fake details or image values are published. Focused tests verify the queued lifecycle command and retained absence. They do not verify the resulting UI against a running external Discord client.

The native daemon lifecycle methods `initialize`, `prepare`, `shutdown`, `check`, and Psych's `loadModRPC` are not exposed through the imported facade. Initialization and teardown remain host/session responsibilities; this package covers the donor Lua callbacks and source presence/client-ID methods above. The focused tests use the portable Haxe interpreter plus a fake native SDK typecheck; no game build, full suite, or external Discord runtime was run for this change.

The real ready callback records its menu fallback in the shared snapshot only when no request or explicit clear exists. Lifecycle presence seeding leaves identity unchanged so a queued application-ID change still restarts the SDK. A source lease can therefore restore the actual menu baseline rather than clearing it.

Focused validation:

- `$env:CAMMIE_TEST_TMP='C:/t/cammie-test'; $env:PYTHONPATH='tools/tests'; python -m unittest test_source_discord_presence_lease test_psych_discord_bindings test_source_discord_identity`: 6 tests passed.
