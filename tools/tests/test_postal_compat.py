from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f'unterminated method: {marker}')


class PostalCompatibilityTest(unittest.TestCase):
    def test_chart_layout_and_character_controls(self):
        fixtures = [
            ROOT / 'assets/data/no-regerts/no-regerts-hard.json',
            ROOT / 'assets/data/no-regerts/no-regerts-postal.json',
            ROOT / 'assets/data/playing-with-scissors/playing-with-scissors-hard.json',
            ROOT / 'assets/data/playing-with-scissors/playing-with-scissors-postal.json',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted Postal chart fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        song = (ROOT / 'source/Song.hx').read_text()
        # Song's loader now validates visual fields against the live registries
        # before applying the legacy-layout fallback. Extract the small helper
        # methods as well as the forceLayout block so this regression test keeps
        # exercising the source implementation when that validation evolves.
        valid_layout = extract_method(song, 'static function validLayout')
        visual_valid = extract_method(song, 'static function isValidVisualValue')
        layout_start = song.find("\t\tif (parsedJson.forceLayout == null)")
        if layout_start < 0:
            layout_start = song.index("\t\tif (!isValidVisualValue('forceLayout'")
            layout_end = song.index("\n\t\tif (!isValidVisualValue('cutsceneType'", layout_start)
        else:
            layout_end = song.index('\n\t\tif (parsedJson.cutsceneType == null)', layout_start)
        layout = song[layout_start:layout_end]
        char = (ROOT / 'source/Character.hx').read_text()
        sing = char[char.index('\tpublic function sing('):char.index('\n\toverride function update(')]
        controls = char[char.index('\t@:keep public var canSing'):char.index('\n\tpublic function dance()')]
        fixture = '''class FNFAssets {
 public static function exists(path:String, ext:Dynamic):Bool {
  return path.indexOf('custom_ui/ui_layouts/') >= 0;
 }
}
class Extensions { public static var Hscript:Dynamic = null; }
class FlxColor {public static var WHITE=0xffffff;}
class Actor {
 var color=0xffffff;public var played="";
 var animation={getByName:function(n:String):Dynamic return {name:n}};
 function callInterp(n:String,args:Array<Dynamic>){}
 public function new(){}
 public function playAnim(n:String,f:Bool=false,r:Bool=false,frame:Int=0){played=n;}
''' + controls + sing + '''
}
class PostalCompatTest {
 static function validCharacter(name:String):Bool return true;
 static function validStage(name:String):Bool return true;
 static function validUIType(name:String):Bool return true;
 static function validCutscene(name:String):Bool return true;
''' + valid_layout + visual_valid + '''
 static function layout(parsedJson:Dynamic):String {
''' + layout + '''
 return parsedJson.forceLayout;
 }
 static function main(){
  for(name in ['no-regerts','playing-with-scissors']) for(diff in ['hard','postal']) {
   var chart=haxe.Json.parse(sys.io.File.getContent('assets/data/'+name+'/'+name+'-'+diff+'.json')).song;
   if(layout(chart)!='postal')throw 'Legacy chart must automatically choose Postal';
  }
  if(layout({uiLayoutType:'ourple'})!='ourple'||layout({uiLayoutType:'normal'})!='none'||layout({})!='none')throw 'Legacy layout defaults incorrect';
  if(layout({forceLayout:'psych',uiLayoutType:'postal'})!='psych'||layout({forceLayout:'none',uiLayoutType:'postal'})!='none')throw 'Explicit editor choice must win';
  var actor=new Actor();actor.sing(0);if(actor.played!='singLEFT')throw 'Normal singing';
  actor.canSing=false;actor.sing(1);if(actor.played!='singLEFT')throw 'Disabled singing interrupted animation';
  actor.specialPlayAnim('hey',true);actor.canSing=true;actor.sing(2);if(actor.played!='hey'||!actor.specialAnim)throw 'Special animation interrupted';
  actor.specialAnim=false;actor.sing(3);if(actor.played!='singRIGHT')throw 'Singing did not resume';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'PostalCompatTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'PostalCompatTest', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
