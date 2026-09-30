"""Guard the shared native draw handoff to FunkinModchart."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameModchartDrawOwnershipTest(unittest.TestCase):
    def test_manager_must_be_attached_existing_and_visible(self):
        fixture = r'''class Main {
    static function check(value:Bool, label:String):Void {
        if (!value) throw label;
    }
    static function main():Void {
        var manager:Dynamic = {exists:true, visible:true};
        var other:Dynamic = {exists:true, visible:true};
        var owner:Dynamic = {members:[manager]};
        check(CodenameModchartDrawOwnership.managerOwnsVisibleDraw(owner, manager),
            "attached visible manager did not own rendering");
        manager.visible = false;
        check(!CodenameModchartDrawOwnership.managerOwnsVisibleDraw(owner, manager),
            "hidden manager retained draw ownership");
        manager.visible = true;
        manager.exists = false;
        check(!CodenameModchartDrawOwnership.managerOwnsVisibleDraw(owner, manager),
            "destroyed manager retained draw ownership");
        manager.exists = true;
        owner.members = [other];
        check(!CodenameModchartDrawOwnership.managerOwnsVisibleDraw(owner, manager),
            "detached manager retained draw ownership");
        owner.members = null;
        check(!CodenameModchartDrawOwnership.managerOwnsVisibleDraw(owner, manager),
            "malformed owner members were accepted");
        check(!CodenameModchartDrawOwnership.managerOwnsVisibleDraw(null, manager),
            "null owner was accepted");
    }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pre_draw_suppresses_native_items_and_reuses_snapshot(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        adapter = (ROOT / "source/modchart/backend/standalone/adapters/cammie/Cammie.hx").read_text()
        draw_start = play_state.index("override public function draw():Void")
        draw_end = play_state.index("override public function update(elapsed:Float)", draw_start)
        draw = play_state[draw_start:draw_end]
        self.assertIn("daNote.visible = !invsNotes && sourceVisible", play_state)
        self.assertIn("Cammie.prepareNativeDraw(this, parentWillDrawMembers)", draw)
        self.assertIn("var parentWillDrawMembers = persistentDraw || subState == null", draw)
        self.assertLess(draw.index("prepareNativeDraw"), draw.index("super.draw();"))
        self.assertIn("CodenameModchartDrawOwnership.managerOwnsVisibleDraw(state, Manager.instance)", adapter)
        self.assertIn("@:bypassAccessor sprite.visible = false", adapter)
        self.assertIn("preparedArrowItems = collectArrowItems()", adapter)
        self.assertIn("var prepared = preparedArrowItems", adapter)
        self.assertIn("restoreTrackedSprites()", adapter)
        self.assertIn("sprite.visible = sprite._fmVisible", adapter)
        renderer = (ROOT / ".haxelib/funkin-modchart/1,2,5/modchart/backend/graphics/CtxRenderer.hx").read_text()
        self.assertIn("return obj._fmVisible", renderer)
        self.assertIn("play-modchart-pre-draw", draw)
        self.assertNotIn("D-Sides", adapter)


if __name__ == "__main__":
    unittest.main()
