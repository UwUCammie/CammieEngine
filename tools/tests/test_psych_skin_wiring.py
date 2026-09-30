"""Selected source ownership gates both Psych skin banks and generated notes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_difficulty_visual_fallback import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychSkinWiringTest(unittest.TestCase):
    def test_selected_owner_and_current_chart_settings(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(extract_method(source, marker) for marker in (
            '\tfunction selectedPsychSkinRoot(', '\tfunction configurePsychNoteSkin(',
            '\tfunction configurePsychStrumSkins(', '\tfunction preparePsychNoteDefinitions('))
        fixture = '''typedef Manifest = {var selectedRoot:String; var roots:Array<{path:String,engine:String}>;}
typedef Line = {var members:Array<Note>;}
class ImportEngine { public static var PSYCH = 'Psych Engine'; }
class CompatScriptManifest {
 public static function selectedRoot(m:Dynamic):String return m.selectedRoot;
 public static function destinationKey(p:String):String return p;
}
class FileSystem { public static function isDirectory(p:String):Bool return p != 'missing'; }
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_phase:String):Void {}
}
class Note {
 public static var specialNoteJson:Array<Dynamic> = null;
 public var calls:Array<Dynamic> = [];
 public function new() {}
 public function configurePsychSkin(root:String, skin:String, disable:Bool, pixel:Bool,
  ?suffix:String = '', ?diagnosticIndex:Int = 0, ?diagnosticsEnabled:Bool = false):Bool {
  calls.push({root:root,skin:skin,disable:disable,pixel:pixel}); return true;
 }
}
class SkinWiring {
 var manifest:Manifest;
 var SONG:Dynamic;
 var pixelUI = false;
 var psychNoteSkinDiagnosticsChecked = false;
 var psychNoteSkinDiagnosticsEnabled = false;
 var psychNoteSkinConfigureCount = 0;
 var enemyStrums:Line;
 var playerStrums:Line;
 function getCompatScriptManifest():Manifest return manifest;
 public function new() {}
''' + methods + '''
 static function check(v:Bool, message:String):Void { if (!v) throw message; }
 static function main() {
  var state = new SkinWiring();
  state.manifest = {selectedRoot:'owner-v',roots:[{path:'owner-p',engine:'Psych Engine'},
   {path:'owner-v',engine:'V-Slice'}]};
  state.SONG = {arrowSkin:'atlas',disableNoteRGB:true};
  var dad = new Note(); var bf = new Note();
  state.enemyStrums = {members:[dad,null]}; state.playerStrums = {members:[bf]};
  state.configurePsychStrumSkins();
  check(dad.calls.length == 0 && bf.calls.length == 0, 'unselected Psych root leaked');
  state.manifest.selectedRoot = 'owner-p';
  state.configurePsychStrumSkins();
  check(dad.calls.length == 1 && bf.calls.length == 1, 'both banks must configure');
  check(dad.calls[0].root == 'owner-p' && dad.calls[0].skin == 'atlas'
   && dad.calls[0].disable, 'source settings lost');
  state.preparePsychNoteDefinitions(null);
  check(Note.specialNoteJson == null, 'native null definition semantics changed');
  state.preparePsychNoteDefinitions(state.selectedPsychSkinRoot());
  check(Note.specialNoteJson != null, 'Psych missing sidecar did not initialize');
  var encoded = NoteTypeCompat.nativeNoteData([5200,2,0,'Hurt Note'],4,Note.specialNoteJson);
  check(encoded >= 40 && Note.specialNoteJson[0].sourceNoteType == 'Hurt Note',
   'missing-sidecar chart lost its Hurt definition');
  var definitions = Note.specialNoteJson;
  state.preparePsychNoteDefinitions(state.selectedPsychSkinRoot());
  check(Note.specialNoteJson == definitions, 'existing custom definitions replaced');
  var note = new Note();
  state.configurePsychNoteSkin(note,state.selectedPsychSkinRoot());
  state.SONG.arrowSkin = ''; state.SONG.disableNoteRGB = false; state.pixelUI = true;
  state.configurePsychNoteSkin(note,state.selectedPsychSkinRoot());
  check(note.calls[1].skin == '' && !note.calls[1].disable && note.calls[1].pixel,
   'later construction must read current SONG settings');
  state.configurePsychNoteSkin(note,null);
  check(note.calls.length == 2, 'native note changed');
  state.manifest = {selectedRoot:'missing',roots:[{path:'missing',engine:'Psych Engine'}]};
  check(state.selectedPsychSkinRoot() == null,'missing owner accepted');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='psych-skin-wiring-') as folder:
            (Path(folder) / 'SkinWiring.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                                     '-cp', str(ROOT / 'source'), '-main', 'SkinWiring', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('swagNote', 'sustainNote'):
            semantic = source.index(f'EngineCompat.applyLegacyNoteRow({name}, songNotes);')
            apply = source.index(f'configurePsychNoteSkin({name}, psychSkinRoot);', semantic)
            next_setup = source.index('if (section.gfSection == true && !gottaHitNote)', apply)
            self.assertLess(semantic, apply)
            self.assertLess(apply, next_setup,
                            f'{name} Psych skin must configure after legacy row semantics and before insertion')
