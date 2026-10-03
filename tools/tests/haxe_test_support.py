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
    return [str(HAXE), *(['-D', 'windows'] if windows else [])]


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
