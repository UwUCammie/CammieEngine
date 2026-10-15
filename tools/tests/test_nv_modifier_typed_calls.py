"""Nightmare Vision modifiers are called through typed methods when an entry
offers them, with the same results as the function fields."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"

FIXTURE = r'''
import nightmarevision.modchart.NightmareVisionModifierCalls;
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartTransform;

/** Records which route ran; both routes compute the same thing. */
class Shift implements NightmareVisionModifierCalls {
	public static var log:Array<String> = [];
	public function new() {}
	public function getPos(time:Float, diff:Float, tDiff:Float, beat:Float, pos:NightmareVisionModchartVector, data:Int, player:Int,
		obj:Dynamic):NightmareVisionModchartVector {
		log.push('typed-pos');
		return shift(time, diff, tDiff, beat, pos, data);
	}
	public static function shift(time:Float, diff:Float, tDiff:Float, beat:Float, pos:NightmareVisionModchartVector, data:Int) {
		pos.x += time * 0.01 + diff + data;
		pos.y += tDiff * beat;
		return pos;
	}
	public function updateObjectOfKind(beat:Float, obj:Dynamic, pos:NightmareVisionModchartVector, player:Int, kind:String):Void {
		log.push('typed-' + kind);
		pos.z += beat;
	}
	public function getValue(player:Int):Float return 0.5 + player;
	public function getSubmodValue(modName:String, player:Int):Float return modName.length;
}

class Main {
	static function check(ok:Bool, label:String):Void if (!ok) throw label;

	static function entries(typed:Bool):Map<String, NightmareVisionModifierExecution> {
		var calls = new Shift();
		var made:NightmareVisionModifierExecution = {builtin: null,
			getPosition: function(t, d, td, b, p, data, player, obj) { Shift.log.push('field-pos'); return Shift.shift(t, d, td, b, p, data); },
			updateObject: function(b, obj, p, player, kind) { Shift.log.push('field-' + kind); p.z += b; },
			value: function(player) return 0.5 + player,
			subValue: function(name, player) return name.length};
		if (typed) made.calls = calls;
		var map = new Map();
		map.set('shift', made);
		return map;
	}

	static function run(typed:Bool):String {
		var registry = new NightmareVisionModifierRegistry(4);
		var map = entries(typed);
		registry.executionNames = function(player) return ['shift', 'shift'];
		registry.executionEntry = function(name) return map.get(name);
		var transform = new NightmareVisionModchartTransform(registry);
		var context = new NightmareVisionModchartContext(1280, 720, 4, 112, 500, 3.25);
		var out = [];
		for (kind in [NightmareVisionModchartObject.NOTE, NightmareVisionModchartObject.RECEPTOR]) {
			var object = new NightmareVisionModchartObject(kind);
			object.strumTime = 1250;
			object.data = 2;
			var pos = transform.getPositionInto(context, object, 40, 60, 3.25, new NightmareVisionModchartVector());
			transform.updateObject(context, object, pos, 3.25);
			out.push([pos.x, pos.y, pos.z, object.x, object.y].join(','));
		}
		return out.join('|');
	}

	static function main() {
		Shift.log = [];
		var viaFields = run(false);
		check(Shift.log.indexOf('typed-pos') < 0, 'an entry without calls used the typed route');
		var fieldLog = Shift.log.join(',');
		Shift.log = [];
		var viaCalls = run(true);
		check(Shift.log.indexOf('field-pos') < 0 && Shift.log.indexOf('field-note') < 0, 'an entry with calls still used the function fields');
		check(Shift.log.join(',') == StringTools.replace(fieldLog, 'field-', 'typed-'), 'call order changed: ' + Shift.log.join(','));
		check(viaFields == viaCalls, 'typed route changed results:\n' + viaFields + '\n' + viaCalls);
	}
}
'''


class NightmareVisionModifierTypedCallsTest(unittest.TestCase):
    def test_transform_prefers_typed_calls_with_identical_results(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(FixturePath(SOURCE)), "-cp", str(FixturePath(work)), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manager_and_builtin_entries_offer_the_same_methods(self):
        manager = (SOURCE / "NightmareVisionModManager.hx").read_text(encoding="utf-8")
        entry = manager[manager.index("function executionEntry(name:String)"):]
        entry = entry[:entry.index("return entry;")]
        # The typed route and the fields all point at the same modifier.
        self.assertIn("calls:mod,", entry)
        self.assertIn("getPosition:mod.getPos,", entry)
        self.assertIn("value:mod.getValue, subValue:mod.getSubmodValue,", entry)
        builtin = (SOURCE / "NightmareVisionBuiltinModifier.hx").read_text(encoding="utf-8")
        self.assertIn("calls:this,value:getValue,subValue:getSubmodValue,getPosition:getPos,updateObject:dispatchObject", builtin)
        # updateObjectOfKind is the same switch as both updateObject fields.
        base = (SOURCE / "NightmareVisionModifier.hx").read_text(encoding="utf-8")
        switch = base[base.index("public function updateObjectOfKind("):]
        switch = switch[:switch.index("\n\t}\n")]
        for line in ("case 'note': updateNote(beat, obj, pos, player);", "case 'receptor': updateReceptor(beat, obj, pos, player);",
                "case 'noteSplash': updateNoteSplash(beat, obj, pos, player);",
                "case 'sustainSplash': updateSustainSplash(beat, obj, pos, player);"):
            self.assertIn(line, switch)
            self.assertIn(line.replace(' ', '').replace("'", "'"), entry.replace(' ', '').replace('mod.', ''))
        self.assertIn("implements nightmarevision.modchart.NightmareVisionModifierCalls", base)


if __name__ == "__main__":
    unittest.main()
