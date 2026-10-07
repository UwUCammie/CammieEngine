# Nightmare Vision package-family catalog report

## Source and publication proof

ImportPackageFamilyCatalog recognizes direct siblings in a retained Nightmare Vision container only when the complete snapshot receipt records their paths and source inspection confirms the engine relationship. Full game-root captures require structural Nightmare Vision evidence. Content-container captures require persisted scanner evidence from the original scan. Candidate membership never comes from a display name, a shared parent alone, or an unrecorded directory.

Family publication runs inside the normal staged import transaction. ModuleFunctions.publishNightmareVisionFamilyMemberRoots publishes configured siblings even when they contain no chart rows. It requires a direct package-root meta.json, resolves the normal import namespace, and uses the existing asset, script, shared-core, and non-overwriting copy paths. It creates no chart entries. CompatScriptManifest records the exact namespace selected during staging. A v2 catalog is emitted only when the transaction owns that package's meta.json and at least one non-core runtime file.

The v2 record binds each member's directory label, exact retained sourceRelative, and installed namespace to one snapshot ID and container. The transaction validates that each catalog namespace has config and runtime outputs in its own manifest before publication. Manifest schema remains version 1, and older catalog-less records remain readable.

## Refresh and runtime lookup

On refresh or re-import, ImportPackageFamilyCatalog.reusableNamespaces revalidates the previous v2 catalog against its own retained receipt, source structure, and committed manifest-owned live config/runtime files. It carries a namespace forward only when the new snapshot independently proves the same exact relative member path and directory label under the same retained-import identity. New snapshot bytes do not merge unrelated records or derive labels from namespaces.

forOwner admits sibling roots only from valid committed manifests with verified transaction-owned config/runtime files. It rejects duplicate-label ambiguity, invalid receipts, conflicting mappings, or mismatched source structure with an empty result. It does not hash every retained file during runtime lookup. Legacy v1 reconstruction remains limited to relationships represented by the same committed source snapshot.

Package-local meta.json is copied beside the package's namespace even when the shared core is staged below __nmv_core. In content/<package> layout, the package's own assets/ stays package-owned; the sibling engine assets/ is treated as core only when the direct content relationship and engine-root evidence are valid. Arbitrary paths named content cannot borrow a parent's assets, and an explicitly selected assets/ root retains its core-only behavior.

Nightmare Vision importer revision advanced from 3 to 4 so installed revision 3 receipts regenerate from retained source and acquire the package-local config and family mapping through the existing transaction. There is no application version bump.

## Bounded evidence and limits

The earlier bounded installed-record inspection found the old-dsides and new-dsides records in different retained snapshots and did not find a committed owner record for nightmare-vision-old-dsides-b7814b6812. Those records were not joined by this change. A revision 3 import must regenerate from its retained source before the new family catalog can authorize runtime switching. The implementation does not claim to create missing playable charts or repair pre-existing unowned directories.

If a sibling lacks direct package config or staged package runtime output, it is not enrolled. Interrupted publication, collisions, and user edits remain subject to existing transaction recovery and conflict checks. Root-owned runtime/menu integration and native validation remain outside this importer package.

## Focused verification

The focused importer gate passed 67 tests in 51.97 seconds with 3 environment-dependent skips. It covered compat-script publication, core-root resolution, source-family receipt validation and rebase, import transactions, manager lifecycle, and revision handling. The changed-snapshot rebase test publishes two namespace-owned package outputs in a real transaction, captures changed source bytes under a second snapshot ID, and verifies exact member paths retain their original namespaces. After the NMV importer revision advanced to 4, the revision and family-catalog suites were rerun: 8 tests passed in 3.50 seconds.

The symlink-specific collector case is skipped when Windows does not grant directory-symlink privileges. No full application build or full test suite was run by this package task.

The subsequent root-owned build, full suite and bounded native configuration
checks are recorded in [the integration checkpoint](nv-family-config-integration.md).
