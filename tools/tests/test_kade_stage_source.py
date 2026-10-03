"""Coverage for the Kade source-release stage extractor.

Kade-family compiled releases define their stages in code and ship no stage
data, so the importer refuses to invent one and points the user at the mod's
source release.  When a source release IS provided, KadeStageSource extracts
the authored layout mechanically.  This file pins that extraction against a
synthetic mini source tree exercising every supported pattern: the per-song
conditional chain (with a nested braceless else arm), hoisted and in-block
sprite declarations, loadGraphic + Sparrow props with animations,
setGraphicSize/scrollFactor, alpha-0 exclusions, curStage-guarded adds,
defaultCamZoom, and the curStage/player2 repositioning switches.
"""
from haxe_test_support import HAXE_COMMAND

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


PLAYSTATE = r'''
package;

class PlayState extends MusicBeatState {
	public static var instance:PlayState;
	var camGame:FlxCamera;
	var dad:Character;
	var boyfriend:Boyfriend;
	var gf:Character;
	var bg:FlxSprite;
	var stageFront:FlxSprite;
	var energyWall:FlxSprite;
	var hole:FlxSprite;
	var cover:FlxSprite;
	var converHole:FlxSprite;
	var spike:FlxSprite;
	varMAINLIGHT:FlxSprite;

	function create() {
		// hole/cover are declared early and configured inside the song block
		var cover:FlxSprite = new FlxSprite(-180, 755).loadGraphic(Paths.image('synth/cover', 'syn'));
		var hole:FlxSprite = new FlxSprite(50, 530).loadGraphic(Paths.image('synth/hole', 'syn'));
		var converHole:FlxSprite = new FlxSprite(7, 578).loadGraphic(Paths.image('synth/converHole', 'syn'));

		if (SONG.song.toLowerCase() == 'synth-final')
		{
			defaultCamZoom = 0.55;
			curStage = 'synthHell';

			var bg:FlxSprite = new FlxSprite(-10, -10).loadGraphic(Paths.image('synth/bg', 'syn'));
			bg.antialiasing = true;
			bg.scrollFactor.set(0.9, 0.9);
			bg.active = false;
			bg.setGraphicSize(Std.int(bg.width * 4));
			add(bg);

			hole.antialiasing = true;
			hole.scrollFactor.set(0.9, 0.9);

			energyWall = new FlxSprite(1350, -690).loadGraphic(Paths.image("synth/wall", 'syn'));
			energyWall.antialiasing = true;
			energyWall.scrollFactor.set(0.9, 0.9);
			add(energyWall);

			var stageFront:FlxSprite = new FlxSprite(-350, -355).loadGraphic(Paths.image('synth/terrain', 'syn'));
			stageFront.antialiasing = true;
			stageFront.scrollFactor.set(0.9, 0.9);
			stageFront.setGraphicSize(Std.int(stageFront.width * 1.55));
			add(stageFront);
		}
		else if (SONG.song.toLowerCase() == 'synth-remix')
		{
			defaultCamZoom = 0.75;
			curStage = 'synthPlain';

			var stageFront:FlxSprite;
			if (SONG.song.toLowerCase() != 'synth-remix')
			{
				stageFront = new FlxSprite(-1100, -460).loadGraphic(Paths.image('synth/islandA', 'syn'));
			}
			else
				stageFront = new FlxSprite(-1100, -460).loadGraphic(Paths.image('synth/islandB', 'syn'));

			stageFront.setGraphicSize(Std.int(stageFront.width * 1.4));
			stageFront.antialiasing = true;
			stageFront.scrollFactor.set(0.9, 0.9);
			add(stageFront);

			spike = new FlxSprite(20, 20);
			spike.frames = Paths.getSparrowAtlas('synth/spike', 'syn');
			spike.animation.addByPrefix('pulse', 'spike', 24, true);
			spike.animation.play('pulse');
			spike.scrollFactor.set(1, 1);
			add(spike);
		}

		var gfVersion:String = 'gf';

		switch (curStage)
		{
			case 'synthHell':
				gfVersion = 'gf-tied';
		}

		gf = new Character(400, 130, gfVersion);
		dad = new Character(100, 100, SONG.player2);

		switch (SONG.player2)
		{
			case 'synthOpp':
				dad.x -= 250;
				dad.y -= 365;
				gf.x += 345;
				dad.visible = false;
		}

		boyfriend = new Boyfriend(770, 450, SONG.player1);

		switch (curStage)
		{
			case 'synthHell':
				boyfriend.y -= 160;
				boyfriend.x += 350;
		}

		add(gf);

		if (curStage == 'synthHell')
			add(hole);

		add(dad);

		if (curStage == 'synthHell')
		{
			add(cover);
			add(converHole);
			add(dad.exSpikes);
		}
	}
}
'''


def hx_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


CHARACTER_HX = r'''
package;

class Character extends FlxSprite {
	public var exSpikes:FlxSprite;
	public var isPlayer:Bool = false;
	public var debugMode:Bool = false;
	var danced:Bool = false;

	// The dance() switch sits BEFORE the constructor on purpose: the extractor
	// must skip replay-only arms and find the definition arm in a later switch.
	public function dance() {
		switch (curCharacter)
		{
			case 'gf-tied':
				if (danced)
					playAnim('danceRight');
				else
					playAnim('danceLeft');
			default:
				playAnim('idle');
		}
	}

	public function new(x:Float, y:Float, ?curCharacter:String = 'bf', ?isPlayer:Bool = false) {
		super(x, y);
		var tex:FlxAtlasFrames;
		switch (curCharacter)
		{
			case 'gf-tied':
				tex = Paths.getSparrowAtlas('synth/GF Ex Tied', 'syn');
				frames = tex;

				trace(frames.frames.length);

				animation.addByIndices('danceLeft','GF Ex Tied',[0,1,2,3,4,5,6,7,8], "", 24, false);
				animation.addByIndices('danceRight','GF Ex Tied',[9,10,11,12,13,14,15,16,17,18,19], "", 24, false);

				addOffset('danceLeft', 0);
				addOffset('danceRight', 0);

				playAnim('danceRight');

				trace(animation.curAnim);
			case 'idleOpp':
				tex = Paths.getSparrowAtlas('synth/spike', 'syn');
				frames = tex;
				animation.addByPrefix('idle', 'Idle', 24);
				animation.addByPrefix('singUP', 'Sing Up', 24, false);

				addOffset("idle");
				addOffset("singUP", 93, -76);

				playAnim('idle');
			case 'scared':
				// Replay-only arm: no atlas, so nothing can be materialized.
				playAnim('scared');
		}

		dance();
	}
}
'''


class KadeStageSourceTest(unittest.TestCase):
    def build_source_tree(self, root: Path) -> None:
        source = root / "source"
        source.mkdir(parents=True)
        (source / "PlayState.hx").write_text(PLAYSTATE, newline='\n')
        (source / "Character.hx").write_text(CHARACTER_HX, newline='\n')
        images = root / "assets" / "syn" / "images" / "synth"
        images.mkdir(parents=True)
        for name in ("bg", "wall", "terrain", "cover", "hole", "converHole",
                     "islandA", "islandB", "spike", "GF Ex Tied"):
            (images / f"{name}.png").write_bytes(b"png")
        for name in ("spike", "GF Ex Tied"):
            (images / f"{name}.xml").write_text("<TextureAtlas/>", newline='\n')

    def run_probe(self, root: Path, song: str, player2: str) -> dict:
        fixture = f'''class KadeProbe {{
  static function main() {{
    var layout = KadeStageSource.extractStage({hx_string(str(root))}, {hx_string(song)}, {hx_string(player2)});
    if (layout == null) {{ Sys.println("LAYOUT NULL"); Sys.exit(1); }}
    Sys.println("ZOOM=" + layout.zoom);
    Sys.println("STAGE=" + layout.stageId);
    var assets:Array<Dynamic> = layout.assets;
    for (asset in assets) Sys.println("ASSET=" + asset.destination + "<-" + asset.source);
    var layers:Array<Dynamic> = layout.layers;
    for (layer in layers)
      Sys.println("LAYER=" + layer.file + "|" + layer.x + "|" + layer.y + "|" + layer.scale + "|"
        + layer.scroll[0] + "," + layer.scroll[1] + "|" + (layer.anim == null ? "" : layer.anim.name));
    Sys.println("BF=" + layout.actors.bf[0] + "," + layout.actors.bf[1]);
    Sys.println("DAD=" + layout.actors.dad[0] + "," + layout.actors.dad[1]);
    Sys.println("GF=" + layout.actors.gf[0] + "," + layout.actors.gf[1]);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="kade-source-", dir=ROOT / "tmp") as folder:
            probe = Path(folder) / "KadeProbe.hx"
            probe.write_text(fixture, newline='\n')
            result = subprocess_run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "--run", "KadeProbe"])
        return result

    def test_null_directory_enumeration_is_safe_for_source_discovery(self):
        """Windows/Wine may return null for a directory listing instead of throwing."""
        parser = (ROOT / "source/KadeStageSource.hx").read_text()
        parser = "\n".join(line for line in parser.splitlines()
                           if line not in ("package;", "import sys.FileSystem;", "import sys.io.File;"))
        filesystem = '''
class FileSystem {
  public static function isDirectory(path:String):Bool return true;
  public static function exists(path:String):Bool return false;
  public static function readDirectory(path:String):Array<String> return null;
}
'''
        file_stub = '''
class File {
  public static function getContent(path:String):String return null;
}
'''
        fixture = '''
class KadeNullDirectoryProbe {
  static function main() {
    var sourceRoot = KadeStageSource.findSourceRoot("fixture");
    var character = KadeStageSource.extractCharacter("fixture", "missing");
    Sys.println("SOURCE_SAFE=" + (sourceRoot == null));
    Sys.println("CHARACTER_SAFE=" + (character == null));
  }
}
'''
        with tempfile.TemporaryDirectory(prefix="kade-null-listing-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "KadeStageSource.hx").write_text(parser, newline='\n')
            (temp / "FileSystem.hx").write_text(filesystem, newline='\n')
            (temp / "File.hx").write_text(file_stub, newline='\n')
            (temp / "KadeNullDirectoryProbe.hx").write_text(fixture, newline='\n')
            output = subprocess_run([*HAXE_COMMAND, "-cp", folder, "--run", "KadeNullDirectoryProbe"])
        self.assertIn("SOURCE_SAFE=true", output)
        self.assertIn("CHARACTER_SAFE=true", output)

    def test_extracts_expurgation_shaped_stage_from_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.build_source_tree(root)
            output = self.run_probe(root, "synth-final", "synthOpp")
            values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
            self.assertEqual(values["ZOOM"], "0.55")
            self.assertEqual(values["STAGE"], "synthHell")
            # The red wall, terrain, hole strip and cover layers all resolve to
            # the donor tree; the alpha-zero / member adds are excluded.
            destinations = sorted(v.split("<-")[0] for v in
                                  [line.split("=", 1)[1] for line in output.splitlines()
                                   if line.startswith("ASSET=")])
            self.assertIn("prop-0.png", destinations)
            self.assertIn("prop-1.png", destinations)
            self.assertIn("prop-2.png", destinations)
            # Character repositioning: base + curStage bf shift + player2 dad shift.
            self.assertEqual(values["BF"], "1120,290")
            self.assertEqual(values["DAD"], "-150,-265")
            self.assertEqual(values["GF"], "745,130")
            # Authored scroll factor 0.9 and scale 4 on the backdrop layer.
            self.assertIn("LAYER=0|-10|-10|4|0.9,0.9", output)

    def test_else_arm_resolves_per_song_variants(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.build_source_tree(root)
            output = self.run_probe(root, "synth-remix", "tricky")
            values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
            self.assertEqual(values["ZOOM"], "0.75")
            self.assertEqual(values["STAGE"], "synthPlain")
            # The braceless else arm's island variant wins for this song.
            self.assertIn("islandB.png", output)
            self.assertNotIn("islandA.png", output)
            # The Sparrow prop keeps its animation and lands with scale/scroll.
            self.assertIn("|1,1|pulse", output)

    def test_compiled_release_without_source_is_reported_not_invented(self):
        # No source/ directory in the tree: the extractor must find nothing.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.build_source_tree(root)
            shutil.rmtree(root / "source")
            import subprocess
            with tempfile.TemporaryDirectory(prefix="kade-null-", dir=ROOT / "tmp") as probe_folder:
                probe = Path(probe_folder) / "KadeProbe.hx"
                probe.write_text(f'''class KadeProbe {{
  static function main() {{
    var layout = KadeStageSource.extractStage({hx_string(str(root))}, "synth-final", "synthOpp");
    Sys.println(layout == null ? "LAYOUT NULL" : "LAYOUT FOUND");
  }}
}}
''', newline='\n')
                result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", probe_folder,
                                         "--run", "KadeProbe"], cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("LAYOUT NULL", result.stdout)

    def run_character_probe(self, root: Path) -> str:
        fixture = '''class KadeProbe {
  static function main() {
    var root = ''' + hx_string(str(root)) + ''';
    var tied = KadeStageSource.extractCharacter(root, "gf-tied");
    if (tied == null) { Sys.println("TIED NULL"); Sys.exit(1); }
    Sys.println("ATLAS=" + tied.atlasKey + "|" + tied.atlasLibrary);
    Sys.println("PNG=" + tied.atlasPng);
    Sys.println("XML=" + tied.atlasXml);
    var anims:Array<Dynamic> = tied.animations;
    for (a in anims) {
      var idx:String = "prefix";
      if (a.indices != null) { var list:Array<Int> = a.indices; idx = list.join(","); }
      Sys.println("ANIM=" + a.name + "|" + a.prefix + "|" + a.fps + "|" + a.loop + "|" + idx);
    }
    var offs:Array<Dynamic> = tied.offsets;
    for (o in offs) Sys.println("OFFSET=" + o.name + "|" + o.x + "|" + o.y);
    Sys.println("INITIAL=" + tied.initialAnim);
    var opp = KadeStageSource.extractCharacter(root, "idleOpp");
    if (opp == null) { Sys.println("OPP NULL"); Sys.exit(1); }
    var oppAnims:Array<Dynamic> = opp.animations;
    for (a in oppAnims) Sys.println("OPPANIM=" + a.name + "|" + a.prefix + "|" + a.fps + "|" + a.loop);
    var oppOffs:Array<Dynamic> = opp.offsets;
    for (o in oppOffs) Sys.println("OPPOFFSET=" + o.name + "|" + o.x + "|" + o.y);
    Sys.println("OPPINITIAL=" + opp.initialAnim);
    Sys.println("REPLAYONLY=" + (KadeStageSource.extractCharacter(root, "scared") == null ? "null" : "found"));
    Sys.println("MISSING=" + (KadeStageSource.extractCharacter(root, "nobody") == null ? "null" : "found"));
    Sys.println("GFVER_HELL=" + KadeStageSource.stageGfVersion(root, "synthHell"));
    Sys.println("GFVER_PLAIN=" + (KadeStageSource.stageGfVersion(root, "synthPlain") == null ? "null" : "present"));
    Sys.println("GFVER_MISSING=" + (KadeStageSource.stageGfVersion(root, "nowhere") == null ? "null" : "present"));
    var text = KadeStageSource.playStateSource(root);
    Sys.println("HIDES_OPP=" + (KadeStageSource.player2HidesDad(text, "synthopp") ? "true" : "false"));
    Sys.println("HIDES_OTHER=" + (KadeStageSource.player2HidesDad(text, "tricky") ? "true" : "false"));
    var lowered:Array<Array<Dynamic>> = KadeStageSource.player2Adjustments(text, "synthopp");
    Sys.println("LOWERED_ADJ=" + lowered.length);
    var points = KadeStageSource.extractStage(root, "synth-final", "synthopp");
    Sys.println("LOWERED_GF=" + points.actors.gf[0] + "," + points.actors.gf[1]);
    Sys.println("LOWERED_DAD=" + points.actors.dad[0] + "," + points.actors.dad[1]);
  }
}
'''
        with tempfile.TemporaryDirectory(prefix="kade-char-", dir=ROOT / "tmp") as folder:
            probe = Path(folder) / "KadeProbe.hx"
            probe.write_text(fixture, newline='\n')
            return subprocess_run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                   "--run", "KadeProbe"])

    def test_extracts_code_defined_characters_from_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.build_source_tree(root)
            output = self.run_character_probe(root)
            values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
            # The gf-tied-style case: spaced atlas name, addByIndices dance pair,
            # one-argument addOffset entries, explicit initial animation.
            self.assertEqual(values["ATLAS"], "synth/GF Ex Tied|syn")
            self.assertTrue(values["PNG"].endswith("synth/GF Ex Tied.png"))
            self.assertTrue(values["XML"].endswith("synth/GF Ex Tied.xml"))
            self.assertIn("ANIM=danceLeft|GF Ex Tied|24|false|0,1,2,3,4,5,6,7,8", output)
            self.assertIn("ANIM=danceRight|GF Ex Tied|24|false|9,10,11,12,13,14,15,16,17,18,19", output)
            self.assertIn("OFFSET=danceLeft|0|0", output)
            self.assertIn("OFFSET=danceRight|0|0", output)
            self.assertEqual(values["INITIAL"], "danceRight")
            # The addByPrefix opponent case keeps fps/loop and its offsets.
            self.assertIn("OPPANIM=idle|Idle|24|false", output)
            self.assertIn("OPPANIM=singUP|Sing Up|24|false", output)
            self.assertIn("OPPOFFSET=idle|0|0", output)
            self.assertIn("OPPOFFSET=singUP|93|-76", output)
            self.assertEqual(values["OPPINITIAL"], "idle")
            # Replay-only arms and unknown ids extract nothing.
            self.assertEqual(values["REPLAYONLY"], "null")
            self.assertEqual(values["MISSING"], "null")

    def test_extracts_gf_version_mapping_and_visibility(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.build_source_tree(root)
            output = self.run_character_probe(root)
            values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
            self.assertEqual(values["GFVER_HELL"], "gf-tied")
            self.assertEqual(values["GFVER_PLAIN"], "null")
            self.assertEqual(values["GFVER_MISSING"], "null")
            # The player2 arm hides the opponent, matched case-insensitively.
            self.assertEqual(values["HIDES_OPP"], "true")
            self.assertEqual(values["HIDES_OTHER"], "false")
            self.assertEqual(values["LOWERED_ADJ"], "3")
            self.assertEqual(values["LOWERED_GF"], "745,130")
            self.assertEqual(values["LOWERED_DAD"], "-150,-265")


def subprocess_run(args):
    import subprocess
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout + result.stderr


if __name__ == "__main__":
    unittest.main()
