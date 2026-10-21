"""Use the host platform defines when running portable Haxe eval probes.

Haxe's eval target does not automatically define ``windows`` on Windows.
Production Windows branches must still be exercised by the regression probes.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe' / ('haxe.exe' if os.name == 'nt' else 'haxe')
TEST_TMP = Path(os.environ.get('CAMMIE_TEST_TMP', str(ROOT / 'tmp')))


def haxe_command(*, windows=None):
    if windows is None:
        windows = os.name == 'nt'
    # Shared importer identity lookups now include receipt-backed archive reads.
    # Supply the project's pinned JSON library to every standalone compiler probe.
    return [str(HAXE), '-cp', str(ROOT / '.haxelib/tjson/1,4,0'), *(['-D', 'windows'] if windows else [])]


HAXE_COMMAND = haxe_command()


class FixturePath(type(Path())):
    """Keep fixture strings in Haxe's canonical slash form on either host.

    Filesystem operations still use the native pathlib implementation. This
    also makes interpolated Haxe strings safe from Windows escape sequences.
    """
    def __str__(self):
        return super().__str__().replace('\\', '/')

    @property
    def _str_normcase(self):
        # Python 3.12 compares paths through this property. Preserve native
        # equality/hashing with ordinary pathlib paths despite slash strings.
        return self._flavour.normcase(super().__str__())


MULTIPLAYER_STUBS = {
    'MpHooks.hx': 'package multiplayer;\nclass MpHooks { public static var current:Dynamic = null; }\n',
    'MpOverlay.hx': ('package multiplayer;\nclass MpOverlay {\n public static var active:Bool = false;\n'
                     ' public static function startRecording(root:String):Void {}\n'
                     ' public static function stopRecording():Array<String> return [];\n'
                     ' public static function read(path:String):String return path;\n}\n'),
    'MpCache.hx': ('package multiplayer;\nclass MpCache {\n'
                   ' public static function rememberSongFiles(folder:String, paths:Array<String>):Void {}\n}\n'),
}


def write_multiplayer_stubs(folder):
    """Inert multiplayer seams for fixtures that compile lifted game code without source/:
    no lobby song is active and nothing is mounted, as in every single-player run."""
    target = Path(folder) / 'multiplayer'
    target.mkdir(parents=True, exist_ok=True)
    for name, text in MULTIPLAYER_STUBS.items():
        (target / name).write_text(text, encoding='utf-8', newline='\n')
