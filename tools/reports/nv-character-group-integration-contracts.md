# NV real CharacterGroup scene integration

Development version 0.0.16. The repaired Windows build, final canonical suite and both native caps are accepted. Receipt: `tmp/source-nv-character-group-checkpoint.json`. This is the connected scene counterpart to `nv-character-group-core-contracts.md`, not a full Character or outer Stage parity claim.

## Source and integration boundaries

Pinned source: NV `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin/objects/CharacterGroup.hx` and `funkin/states/PlayState.hx`. The source group is an actual FlxSpriteGroup with independent writable map and parent. Source game roles are plain fields (`PlayState:189-207`). Direct group parent assignment or `change` does not assign game roles or refresh HUD. The explicit game caller (`2131-2145`) assigns the returned actor and refreshes HUD.

PlayState now creates real groups from source stage positions before stage scripts. The source hook controls automatic mounting; STOP leaves groups and their actors unmounted until an authored attachment. Initial characters start at zero, then source `addChar` plus native group preAdd apply offsets once. GF loads its character script after add/parent assignment; dad and BF load before add/parent assignment, matching the distinct source sequence at `681-694`. Explicit preloads load the actor's current `curCharacter` script after group `addToList`; direct group construction/change performs no extra script initialization.

Mounted groups are indivisible state scene units. Their current members, including hidden cached actors, receive native group traversal. The old active NV bank/facade construction, flat actor mounting and scene-forwarding activation paths are removed from PlayState. Psych/native/Codename routes retain their prior behavior. Public role-group pointers are live, replaceable and nullable; replacements do not automatically reconcile mounted objects or destroy old groups. Source role positions are actual public FlxPoint identities.

`SourceCharacterConstruction` is a separate optional sixth host constructor argument after the existing optional Codename context. Scoped source factories preserve the actual four NV Character arguments and supply captured root/engine/provider before definitions, atlas or interpreter initialization. Metadata, icon, position/orientation/camera and visual/interpreter resolution use that captured root. Released providers are rejected before IO. Omitted-context constructors retain the existing host route; globals are not temporarily swapped.

The source CharacterGroup class and Character imports keep real native Class identity and scoped Type factories. CharacterType remains an Int abstract with BF/DAD/GF constants; it is not exposed as an invented runtime Enum.

## Ownership and host compatibility

The state owns each mounted group through actual membership; the group owns current members through native membership. There is no extra cleanup list for cached, map-only, unmounted, detached or replaced actors/groups. Authored sharing and raw arrays retain native semantics rather than receiving universal deduplication or reparenting. The borrowed role classification array is used only to protect supported role units during host stage replacement, never to destroy them.

Manual stage mount/remove/remount remains effective. During host stage replacement only, a transient cleanup guard unlinks borrowed role bookkeeping without resetting group cameras, detaching their state ownership or destroying their members. Ordinary stage props retain the existing flat bridge. The actual donor Stage extends FlxTypedContainer, whereas host StageHelper extends FlxSpriteGroup and is not mounted as another scene owner. Full outer container ordering/transforms/lifetime parity remains separate.

The host-only `switchToChar` compatibility bridge now uses group membership, transfers alpha, hides retained previous actors and updates caller role/field/HUD pointers. Explicit `destroy=true` removes and destroys the previous actor once. This is a preserved host compatibility boundary, not an extra side effect added to the source group methods.

When `hide_girlfriend` is true, the source GF group's members/map/parent stay empty/null, and no source GF script is loaded. Existing legacy host paths still require a GF object, so an invisible state-owned placeholder remains in `game.gf` outside the source group. GF preload fallback treats that unchanged placeholder as source absence. This is an explicit remaining game-role/API deviation; full null-GF migration is not claimed.

## Focused evidence and executed native gate

Four connected headless fixtures pass using actual Iris, actual typed core groups, captured construction interfaces and C++ generation. They cover actual imports/Class roundtrips, root isolation without global swaps, source placement, parent independence, rejected stale IO and the extracted compatibility switch's retained/explicit-destroy cases. Source phase checks pin initial script ordering, preload ordering, old-route retirement and native branch exclusion. A live alias fixture additionally covers null/replaced group pointers through bare/game/reflection routes.

The six older integration regression modules were migrated with their behavior assertions retained: gameplay lifecycle, retained preloads, event preparation, character-change events, Psych preload bridge and stage forwarding. Their combined focused run passes 13 tests with zero skips/failures. The gameplay donor test now reads the actually supplied pinned source rather than skipping a stale location.

`tmp/test-source-nv-character-group-native.ps1` installs only a private Tutorial owner, a STOP stage hook, two controlled source character definitions and a generated atlas with a byte-identical core face bitmap. It preserves original chart bytes, options/save/version/tag behavior, 70 protected inputs and 38 immutable source core copies. Both accepted native runs contain the four group markers plus the STOP marker twice, with two real 1280x720 nonempty frame readbacks and the requested backend/draw/unlimited mode.

The core reviewer owns `tmp/source-nv-character-group-native.hx`. It verifies real constructors, manual mounting after STOP, cache and actual field ownership, independent parent/game role pointers, exact manual native velocity traversal for hidden/visible cached actors, animation advance, actual transforms and one-owner scene membership. Standalone native teardown observes destroyed actor state, preserved map/parent references, cleared borrowed cells and surviving shared provider IO. These are bounded traversal/lifetime observations, not precise default-scene draw/destructor call counters or authored donor chart acceptance.

## Remaining scope

The mixed Character parent graph still inherits the native FlxSprite rather than the source plain-sprite wrapper; broader source base-Class metadata identity remains open. Whole Character malformed/fallback metadata, full dialogue/stage/container behavior and full Phase 2 parity remain open. Writable maps can hold references outside membership, and source null/error/field-ID behavior remains owned by the core contract rather than normalized in scene integration. The accepted final canonical suite passes 2,307 cases across 756 modules in 145.8 seconds, with 344 skips and zero failures (`tmp/source-nv-character-group-full-tests-final.log`). The receipt verifies the gated binary, reviewed captures and restored/protected inputs.


### Accepted native receipts

- 60 FPS: `source-nv-character-group-d2c6bbcc`, 28.675 seconds, two visits.
- Unlimited: `source-nv-character-group-92527fbd`, 27.310 seconds, two visits.
- Each run passes all five marker categories twice, real frame/mode gates and unchanged 70 protected files. Root reviewed all four captures: controlled source character, Tutorial scene and source HUD visual sanity.
- Gated executable SHA256: `50F514AF2E5DCDC7EA490F293C48EE44D1E0847DD0428E86CB7B248BA84244BF`, recorded in `tmp/source-nv-character-group-build-runtime.json` after the repaired build. Native launches were performed by root.

These receipts provide bounded source component/runtime evidence. They do not certify complete source Character assets, an authored donor chart, exact default draw/destructor call counts or the outer Stage container implementation.
