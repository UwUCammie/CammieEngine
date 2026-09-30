"""Pin Codename Switch Mod defaults, user remaps, and source input dispatch."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameSwitchModControlsTest(unittest.TestCase):
    def test_default_remap_unbind_and_settings_preservation(self):
        source = (ROOT / "source/CodenameControlsCompat.hx").read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Controls.hx").write_text("""class Controls {
 public var SWITCHMOD:Bool;
 public function new(value:Bool) SWITCHMOD=value;
}
""")
            (base / "Main.hx").write_text(r'''class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var settings:Dynamic={keys:{left:[65,37]},codenameMenuKeys:{up_menu:[87,38]}};
  check(CodenameControlsCompat.switchModKeyboardBindings(settings,9).join(",")=="9",
   "missing Codename binding must use upstream Tab default");
  Reflect.setField(settings.codenameMenuKeys,"switchmod",[43,43,"67",0,-1,"bad"]);
  check(CodenameControlsCompat.switchModKeyboardBindings(settings,9).join(",")=="43,67",
   "Codename remap must retain valid distinct key codes only");
  check(CodenameControlsCompat.switchModPressed(new Controls(true))
   && !CodenameControlsCompat.switchModPressed(new Controls(false)),
   "source SWITCHMOD must read the live native action");
  Reflect.setField(settings.codenameMenuKeys,"switchmod",[]);
  check(CodenameControlsCompat.switchModKeyboardBindings(settings,9).length==0,
   "an explicit empty remap must allow the shortcut to be unbound");
  check(CodenameControlsCompat.saveSwitchModKeyboardBindings(settings,[70,70,0,71])
   && Reflect.field(settings.codenameMenuKeys,"switchmod").join(",")=="70,71"
   && Reflect.field(settings.codenameMenuKeys,"up_menu").join(",")=="87,38"
   && settings.keys.left.join(",")=="65,37",
   "saving the Codename remap overwrote unrelated personal controls");
  var empty:Dynamic={};
  check(CodenameControlsCompat.saveSwitchModKeyboardBindings(empty,[])
   && Reflect.field(Reflect.field(empty,"codenameMenuKeys"),"switchmod").length==0,
   "saving an unbound action did not create the isolated Codename key map");
  check(!CodenameControlsCompat.saveSwitchModKeyboardBindings(null,[71]),
   "missing save data should fail without mutation");
 }
}''')
            (base / "CodenameControlsCompat.hx").write_text(source)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", directory, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_action_is_just_pressed_defaulted_and_remappable(self):
        controls = (ROOT / "source/Controls.hx").read_text()
        interp = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        state = (ROOT / "source/ControlsState.hx").read_text()
        self.assertIn('var SWITCHMOD = "switch-mod";', controls)
        self.assertIn("SWITCHMOD(get, never)", controls)
        self.assertIn("func(_switchMod, JUST_PRESSED);", controls)
        self.assertIn("setKeyboardBindingsByName('SWITCHMOD', switchModKeys);", controls)
        self.assertIn("Control.SWITCHMOD => [FlxGamepadInputID.BACK]", controls)
        self.assertIn("field == 'SWITCHMOD' && Std.isOfType(object, Controls)", interp)
        self.assertIn("case 'Switch Mod':", state)
        self.assertIn("setKeyboardBindingsByName('SWITCHMOD', keyCodes)", state)
        self.assertIn("currentKeys.length != 0 || editingSwitchMod", state)
        self.assertIn("saveSwitchModKeyboardBindings(FlxG.save.data, keyCodes)", state)


if __name__ == "__main__":
    unittest.main()
