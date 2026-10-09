CammieEngine v0.0.22 - alpha player guide

PLAY
Extract the complete release ZIP to a writable folder and run Funkin.exe.
Keep the assets, libraries and tools with the executable. Windows players
using a release ZIP do not need Haxe, Visual Studio or a source checkout.

Use the menus to select songs and change settings. Keyboard bindings are
configurable in Settings. Close the game before replacing or rebuilding it.
Back up the extracted game folder and your saves before updating an alpha.
The release includes a default V-Slice-style results screen. Imported mods can
provide their own ending screen.

IMPORT MODS
Use the engine's import menu to select a supported source package. Imports
are stored separately from the bundled songs; identically named songs can
remain accessible with their source labels.

New imports keep a source copy in import-cache beside the game, including
Windows .exe files used to identify the engine; shared libraries and other native
payloads are excluded. Future importer improvements automatically
refresh outdated imports while you browse menus or Settings; a progress bar
shows the work. Keep import-cache when moving or updating the game. This uses
additional disk space but removes the need to select the original folder again.
Pending songs stay gray until their mod is ready; completed mods remain playable.
Background import work pauses during gameplay and resumes when you return to a
menu. A transaction already installing files finishes safely before pausing.
Local edits, missing cached files or incomplete scans stop the refresh and
preserve the installed content. Older imports without a retained source are
not automatically enrolled or overwritten.

Import compatibility is experimental. Successful import or gameplay entry
alone does not establish accurate playback. Some scripts, effects, menus,
editors and source dependencies remain unsupported or under verification.
Report the source engine, package version, song, difficulty and exact steps
when an import fails or behaves differently from its original engine.

CREATE CONTENT
The chart editor and import tools are available in the engine. Existing
HScript and registry documentation is in the source repository. This guide
does not replace the format-specific documentation of the source engine.

HELP, SOURCE AND UPDATES
https://github.com/UwUCammie/CammieEngine
https://github.com/UwUCammie/CammieEngine/releases
https://github.com/UwUCammie/CammieEngine/issues

CREDITS
Maintained by UwUCammie. Built on AFunkinDisappointment's Disappointing Plus,
Modding Plus and Friday Night Funkin'. See the in-game Credits page,
assets/data/credits.txt, NOTICE and LICENSE for upstream attribution.
