# Runtime owner asset identity

`RuntimeOwnerAssetIdentity` loads a Lime identity sidecar only when
`ImportRefreshManager.ownerAssetIndexBinding(owner, engine, scope)` supplies the
matching committed-manifest binding. It verifies the sidecar path and bytes,
the receipt-bound owner, engine, scope, namespace, snapshot, root, and Project
hash, then checks every indexed asset path and hash against committed manifest
membership. It does not rehash media on each lookup. Lookup still checks that
the selected physical file exists and remains inside the owner.

The cache is keyed by normalized owner, engine, and scope. It reuses the loaded
index only while both the manager generation and availability revision match,
so ordinary asset getters do not clone the manager's committed-file list. A
sidecar present without a current manager binding is `unverified`; it cannot
authorize an ID. A legacy owner with no sidecar retains the old path behavior.

The public result distinguishes `found`, `missing`, `type-mismatch`,
`unclaimed`, `unknown`, `invalid`, `unverified`, and `no-index`. Only `no-index`
and a complete catalog's `unclaimed` library permit the facades' legacy
fallback. A declared library miss or wrong type cannot resolve through a
same-named global/default asset. Nightmare Vision resolves package entries
before the same owner's authenticated core entries; it does not search sibling
import owners by ID. `PsychOwnerAssetPath.releaseOwner` and
`NightmareVisionPaths.releaseOwnerAssets` clear only that owner's cached index.

Declared libraries are exposed as virtual ID views for the supported getters,
`exists`, `getPath`, `isLocal`, and `list`. Empty declared libraries remain
visible even when they contain no entries. Dynamic library registration and
binding APIs are not represented by the immutable sidecar. Registration of a
declared or uncertain owner library is rejected; unload/remove of those
libraries also fails without touching a same-named global library. OpenFL
class-binding mutation and owner MovieClip construction are rejected because
the file-backed index does not supply those runtime classes. Unclaimed native
library operations retain their legacy global route. The virtual view is not a
complete Lime/OpenFL `AssetLibrary` implementation: preload state, class
bindings, bundles, and full load/unload lifecycle remain unsupported and are
not certified by the lookup/list tests.

Focused validation used the real Lime/OpenFL facade wrappers with a temporary
receipt-bound empty-library sidecar. It checks that same-named global libraries
survive owner unload/remove/register calls and that empty owner declarations
return owner views. The helper suite also covers qualified IDs, type mismatch,
missing and unclaimed results, epoch refresh, stale/unverified sidecars, and
legacy no-index behavior. Native/game builds were not run for this focused
change.
