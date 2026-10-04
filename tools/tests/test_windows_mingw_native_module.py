"""The portable compiler must receive DLL linker flags through its driver."""
from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest

from patch_windows_mingw import patch_source

ROOT = Path(__file__).resolve().parents[2]


class WindowsMingwNativeModuleTest(unittest.TestCase):
    def test_native_module_auto_import_is_forwarded_and_patch_is_idempotent(self):
        pinned = '''<xml>
<compiler></compiler>
<linker id="dll"><flag value="--enable-auto-import"/></linker>
<linker id="exe"><flag value="-Wl,--enable-auto-import"/></linker>
<copyFile toolId="exe" name="libgcc_s_dw2-1.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs"/>
<copyFile toolId="exe" name="libstdc++-6.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs"/>
</xml>'''
        patched = patch_source(pinned)
        self.assertNotIn('<flag value="--enable-auto-import"/>', patched)
        self.assertEqual(patched.count('<flag value="-Wl,--enable-auto-import"/>'), 2)
        self.assertEqual(patch_source(patched), patched)

    def test_unknown_dll_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not unique'):
            patch_source('<xml><compiler></compiler></xml>')


if __name__ == '__main__':
    unittest.main()
