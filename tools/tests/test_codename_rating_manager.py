"""Compile and exercise the source-compatible Codename rating manager."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameRatingManagerTest(unittest.TestCase):
    def test_script_imports_construct_and_replace_the_live_manager(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('funkin.game.scoring.RatingManager', CodenameRatingManager);", bindings)
        self.assertIn("bindings.set('funkin.game.scoring.HitWindowData.WindowPreset', windowPresetConstants());", bindings)
        self.assertIn("ratingManager:CodenameRatingManager = new CodenameRatingManager()",
                      (ROOT / "source/PlayState.hx").read_text())
        main = r'''import hscript.Interp;
import CodenameRatingManager.CodenameWindowPreset;

class Main {
	static function main():Void {
		var bindings:Map<String, Dynamic> = new Map();
		bindings.set("funkin.game.scoring.RatingManager", CodenameRatingManager);
		bindings.set("funkin.game.scoring.HitWindowData.WindowPreset", {
			DEFAULT: CodenameWindowPreset.DEFAULT,
			CNE_CLASSIC: CodenameWindowPreset.CNE_CLASSIC,
			FNF_CLASSIC: CodenameWindowPreset.FNF_CLASSIC,
			FNF_VSLICE: CodenameWindowPreset.FNF_VSLICE
		});
		var script = 'import funkin.game.scoring.RatingManager; '
			+ 'import funkin.game.scoring.HitWindowData.WindowPreset; '
			+ 'PlayState.instance.ratingManager = new RatingManager(WindowPreset.CNE_CLASSIC); '
			+ 'PlayState.instance.ratingManager.addRating({name:"epic", window:37.8, score:350, splash:true});';
		var parsed = CodenameScriptParser.prepare(script, bindings);
		if (parsed.program == null || parsed.diagnostics.length != 0)
			throw parsed.diagnostics.length == 0 ? "no program" : parsed.diagnostics[0].message;
		var host = {ratingManager:new CodenameRatingManager()};
		var interp = new Interp();
		interp.variables.set("RatingManager", CodenameRatingManager);
		interp.variables.set("WindowPreset", bindings.get("funkin.game.scoring.HitWindowData.WindowPreset"));
		interp.variables.set("PlayState", {instance:host});
		interp.execute(parsed.program);
		if (host.ratingManager.lastHitWindow != 250
			|| host.ratingManager.judgeNote(37.8).name != "epic"
			|| host.ratingManager.judgeNote(38).name != "sick")
			throw "Codename script rating manager is not live";
	}
}'''
        with tempfile.TemporaryDirectory(prefix="codename-rating-script-", dir=ROOT / "tmp") as temp:
            (Path(temp) / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", temp, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_presets_custom_ratings_boundaries_and_replacement(self):
        main = r'''import CodenameRatingManager.CodenameRating;
import CodenameRatingManager.CodenameWindowPreset;

class Main {
	static function check(ok:Bool, message:String):Void {
		if (!ok) throw message;
	}

	static function byName(manager:CodenameRatingManager, name:String):CodenameRating {
		for (rating in manager.ratingData) if (rating.name == name) return rating;
		return null;
	}

	static function main():Void {
		var manager = new CodenameRatingManager(CodenameWindowPreset.CNE_CLASSIC);
		check(manager.getHitWindow("sick") == 50 && manager.getHitWindow("good") == 187.5
			&& manager.getHitWindow("bad") == 225 && manager.getHitWindow("shit") == 250,
			"CNE_CLASSIC windows");
		check(manager.ratingData.map(rating -> rating.name).join(",") == "sick,good,bad,shit",
			"default rating ordering");
		check(manager.lastHitWindow == 250, "initial maximum window");
		check(byName(manager, "shit").breaksCombo, "upstream SHITS_BREAK_COMBO default");
		check(manager.judgeNote(50).name == "sick" && manager.judgeNote(50.001).name == "good"
			&& manager.judgeNote(187.5).name == "good" && manager.judgeNote(187.501).name == "bad"
			&& manager.judgeNote(225).name == "bad" && manager.judgeNote(225.001).name == "shit"
			&& manager.judgeNote(250).name == "shit",
			"inclusive judgement window edges");
		check(manager.judgeNote(251).name == "shit", "source fallback after all windows");

		manager.addRating({name:"epic", window:37.8, accuracy:1.0, score:350, splash:true});
		check(manager.ratingData.map(rating -> rating.name).join(",") == "epic,sick,good,bad,shit",
			"custom rating sorted into timing order");
		check(manager.lastHitWindow == 250 && manager.judgeNote(37.8).name == "epic"
			&& manager.judgeNote(37.801).name == "sick" && manager.judgeNote(50).name == "sick",
			"custom epic bucket and unchanged maximum window");
		var epic = byName(manager, "epic");
		check(epic.accuracy == 1 && epic.score == 350 && epic.health == 0.023
			&& epic.splash && !epic.breaksCombo && epic.hittable,
			"source defaults and authored epic fields");

		manager.addRating({name:"EPIC", window:12.0, score:420});
		epic = byName(manager, "epic");
		check(manager.ratingData.length == 5 && manager.ratingData[0] == epic
			&& epic.window == 12 && epic.score == 420 && epic.accuracy == 1
			&& epic.health == 0.023 && !epic.splash && !epic.breaksCombo && epic.hittable,
			"case-insensitive replacement, sorting, and per-add defaults");
		check(manager.lastHitWindow == 250 && manager.judgeNote(12).name == "epic"
			&& manager.judgeNote(12.001).name == "sick",
			"replacement timing window");

		manager.addRating({name:"wide", window:300, score:9});
		manager.addRating({name:"wide", window:2, score:10});
		check(manager.lastHitWindow == 300 && manager.ratingData[0].name == "wide"
			&& manager.judgeNote(250.001).name == "shit",
			"lastHitWindow remains historical maximum after replacement");

		var disabledManager = new CodenameRatingManager(CodenameWindowPreset.CNE_CLASSIC);
		disabledManager.addRating({name:"disabled", window:1, hittable:false});
		check(disabledManager.judgeNote(1).name == "sick", "non-hittable entry is skipped");

		var defaultManager = new CodenameRatingManager();
		check(defaultManager.getHitWindow("sick") == 37.8
			&& defaultManager.getHitWindow("shit") == 180,
			"default Etterna preset remains the default");
		CodenameRatingManager.SHITS_BREAK_COMBO = false;
		var flagManager = new CodenameRatingManager(CodenameWindowPreset.CNE_CLASSIC);
		check(!byName(flagManager, "shit").breaksCombo, "runtime SHITS_BREAK_COMBO override");
		CodenameRatingManager.SHITS_BREAK_COMBO = true;
		var unknownManager = new CodenameRatingManager(CodenameWindowPreset.CNE_CLASSIC);
		unknownManager.addRating({name:"unknown"});
		check(byName(unknownManager, "unknown").window == -1
			&& unknownManager.lastHitWindow == 250,
			"unknown rating window uses source fallback");
		unknownManager.removeRating("UNKNOWN");
		check(byName(unknownManager, "unknown") == null && unknownManager.lastHitWindow == 250,
			"removal is case-insensitive and does not recompute source maximum");
	}
}'''

        with tempfile.TemporaryDirectory(prefix="codename-rating-", dir=ROOT / "tmp") as temp:
            base = Path(temp)
            (base / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", temp,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
