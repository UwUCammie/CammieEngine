"""Regression guard for the VS Tricky V-Slice Expurgation start freeze.

Donor song scripts gate their intro cutscene on V-Slice's
`PlayState.instance.isInCutscene`: they cancel the native countdown, play a
script-owned entrance, then call `startCountdown()` and clear the flag. The
engine must expose that spelling as a read/write alias of its cutscene state
with script-owned storage, because the native countdown consumes and clears
the native `inCutscene` flag on re-entry — sharing one storage would wipe the
script's gate and replay the cutscene forever.
"""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HxcIsInCutsceneAliasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()

    def test_playstate_exposes_the_donor_cutscene_gate(self):
        source = self.play_state
        self.assertIn("public var isInCutscene(get, set):Bool;", source)
        self.assertIn("function get_isInCutscene():Bool", source)
        self.assertIn("function set_isInCutscene(value:Bool):Bool", source)

    def test_alias_storage_is_script_owned_not_the_native_flag(self):
        source = self.play_state
        # Reads union the native cutscene hand-off flag and the script-owned
        # gate; writes only ever touch the script-owned gate so the native
        # countdown cleanup cannot clobber a script's intro cutscene.
        getter = source[source.index("function get_isInCutscene"):source.index("function set_isInCutscene")]
        setter = source[source.index("function set_isInCutscene"):source.index("function set_isInCutscene") + 220]
        self.assertIn("inCutscene || hxcScriptInCutscene", getter)
        self.assertIn("hxcScriptInCutscene = value == true", setter)
        self.assertNotIn("inCutscene = value", setter)

    def test_script_flag_resets_with_the_song(self):
        source = self.play_state
        # The song-state teardown (where the other per-song HXC flags reset)
        # must clear the script-owned gate so a retried song starts clean.
        teardown = source[source.index("hxcCountdownEndDispatched = false;"):source.index("loadedCompatScriptPaths.clear();")]
        self.assertIn("hxcScriptInCutscene = false", teardown)


if __name__ == "__main__":
    unittest.main()
