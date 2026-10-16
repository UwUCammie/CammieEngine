"""Copy the real staged-import I/O modules into isolated Haxe fixtures.

Several import tests compile a small source subset in a temporary class path.
Modules that now use the import I/O facade need the facade and its hashing
dependencies available there as well. ImportSourceSnapshot also uses the
cooperative scheduler and its cancellation type. These are the production
modules, not behavioral test doubles.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_IO_MODULES = (
    "SongLoadingWork.hx",
    "ImportRevision.hx",
    "PsychFreeplayOrder.hx",
    "FreeplayAuthoredOrder.hx",
    "PsychSongNameCompat.hx",
    "PsychFamilyChartFields.hx",
    "PsychFamilyFormatProbe.hx",
    "NightmareVisionSongNameCompat.hx",
    "ImportDirectoryListing.hx",
    "ImportSourceSnapshot.hx",
    "ImportIO.hx",
    "ImportDiscoveryReuse.hx",
    "ImportFile.hx",
    "ImportGeneratedOutput.hx",
    "ImportFileSystem.hx",
    "ImportWorkScheduler.hx",
    "ImportWorkCancelled.hx",
)


# These isolated source-subset tests have no durable archive. Transaction/archive
# behavior is exercised separately against the complete production modules.
ARCHIVE_LOOKUP_STUB = """package;
class LibraryIdentityArchive {
 public static function load(root:String):LibraryIdentityArchive return new LibraryIdentityArchive();
 public function new(){}
 public function ownerFor(engine:String,identity:String,fingerprint:String):String return null;
 public function destinationFor(engine:String,identity:String,fingerprint:String,source:String,?planned:String):String return null;
}
"""


# ImportRootScanner and the importer's chart reader go through these. They only
# need each other and two small helpers, so any isolated fixture can take them.
CHART_FORMAT_MODULES = (
    "PsychFamilyChartFields.hx",
    "PsychFamilyFormatProbe.hx",
    "PsychSongNameCompat.hx",
    "ImportDirectoryListing.hx",
)


def install_chart_format_modules(folder: Path) -> None:
    """Install the real shared chart/format readers into a fixture class path."""
    destination = Path(folder)
    for module in CHART_FORMAT_MODULES:
        target = destination / module
        if target.exists():
            continue
        target.write_text((ROOT / "source" / module).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def install_import_io_dependencies(folder: Path) -> None:
    """Install the real ImportIO dependency modules into a fixture class path."""
    destination = Path(folder)
    for module in IMPORT_IO_MODULES:
        target = destination / module
        if target.exists():
            continue
        target.write_text((ROOT / "source" / module).read_text(encoding="utf-8"), encoding="utf-8")

    archive = destination / 'LibraryIdentityArchive.hx'
    if not archive.exists():
        archive.write_text(ARCHIVE_LOOKUP_STUB, encoding='utf-8')
