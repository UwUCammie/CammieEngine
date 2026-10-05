# NV quant colors and receptor reload checkpoint

Verified locally on 5 October 2026, after v0.0.13. Implementation subtasks used GPT-6 Luna with Max reasoning. Source: Nightmare Vision revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin.utils.NoteUtil`, `funkin.objects.note.Note`, `StrumNote`, and `PlayField`. Shared Psych RGB rendering remains the foundation; the quant rules are NV dialect extensions.

## Implemented boundary

Notes retain the donor default quant of 4. When enabled at first classification, rhythmic subdivision uses the source 48-row beat / 192-row measure grid and exact eleven quant palettes. Chart classification subtracts the owner's note offset to recover authored time; sustain tails inherit the head's classification, while ordinary host prevNote links do not. Reloads and field transfers retain initialized classification. Notes added by scripts initialize on first attachment.

Global quant coloring, a skin's quantsEnabled metadata, and canQuant have distinct source semantics. Turning metadata off does not silently discard stored quant colors. Custom colors are reapplied after reloads; existing alpha/flash state is preserved. Receptor field.quants is independent of chart coloring, press uses the current owner's arrowRGBquant[0], and confirmation uses last-note colors through the actual per-object shader. Toggling receptor quant mode retains its animation, reset timer and alpha. Explicit RGB disabling is respected.

All changes are in engine/compatibility code. No mod/chart-specific production branches or donor edits were introduced.

## Validation

Windows build and canonical `run.bat test`: 2,205 tests across 709 modules in 130.9 seconds; 345 skipped, zero failed. Focused tests compare the pure algorithm/palettes against pinned donor source, exercise flags/reload/custom colors, and verify nonzero note-offset classification. Skips remain unavailable historical fixtures or explicit platform limitations, not successful coverage.

Muted NV native probes passed at 60 and unlimited FPS over two scene visits each, covering constructor/mutation/skin/vector and quant routes. First-visit keyboard checks passed 128 assertions with 32 press/release callbacks. Ordinary Psych plain/embedded Countdown regression checks passed at both caps. Captures were inspected. 29 protected donor/import/settings hashes remained unchanged; private probes were removed. Native receipts, source/binary hashes and initial fixture failures are recorded in `tmp/nv-quant-checkpoint.json`.

## Remaining scope

Full source PlayField group/splash/underlay behavior, source Note recycle/reflection, wider-key/pixel-sheet geometry, physical controller checks and the complete hold/release lifecycle remain open. These bounded checks do not complete Phase 2, certify every chart, or establish performance improvements. No release was published.

The ordinary Psych capture reproduces the reported opening opponent-note visibility and missing wizard actors. Its Countdown regression verifies enum bindings and execution, not complete scene fidelity; those opening defects are the next separate compatibility investigation.

The separate opening defects described above are resolved within the opening/reveal boundary in `psych-opening-contracts.md`; the earlier captures remain historical evidence.
