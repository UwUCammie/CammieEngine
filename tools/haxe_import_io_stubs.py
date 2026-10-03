"""Copy the real staged-import I/O modules into isolated Haxe fixtures.

Several import tests compile a small source subset in a temporary class path.
Modules that now use the import I/O facade need the facade and its hashing
dependencies available there as well. These are the production modules, not
behavioral test doubles.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_IO_MODULES = (
    "ImportRevision.hx",
    "ImportSourceSnapshot.hx",
    "ImportIO.hx",
    "ImportFile.hx",
    "ImportFileSystem.hx",
)


def install_import_io_dependencies(folder: Path) -> None:
    """Install the real ImportIO dependency modules into a fixture class path."""
    destination = Path(folder)
    for module in IMPORT_IO_MODULES:
        target = destination / module
        if target.exists():
            continue
        target.write_text((ROOT / "source" / module).read_text(encoding="utf-8"), encoding="utf-8")
