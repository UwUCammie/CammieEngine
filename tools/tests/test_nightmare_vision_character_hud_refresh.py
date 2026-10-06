"""Run NMV character health-icon and shared HUD refresh helpers without Flixel."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


def function_body(source, name):
    marker = 'function ' + name + '('
    start = source.index(marker)
    opening = source.index('{', start)
    line_end = source.find('\n', start)
    # Haxe allows expression-bodied getters; avoid consuming the next method's
    # brace when extracting one into the interpreter fixture.
    if line_end != -1 and line_end < opening:
        expression_end = source.find(';', line_end + 1) + 1
        return source[start:expression_end if expression_end != -1 else len(source)]
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ''
        if line_comment:
            if char == '\n':
                line_comment = False
        elif block_comment:
            if char == '*' and following == '/':
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char == '/' and following == '/':
            line_comment = True
            index += 1
        elif char == '/' and following == '*':
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError('unterminated function ' + name)


class NightmareVisionCharacterHUDRefreshTest(unittest.TestCase):
    def test_character_health_icon_reads_owner_definition_and_falls_back(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        source = (ROOT / 'source/Character.hx').read_text()
        getter = function_body(source, 'get_healthIcon')
        resolver = function_body(source, 'nightmareVisionHealthIconFromDefinition')
        fixture = '''
class Character {
 var nightmareVisionHealthIcon:Null<String>=null;var psychHealthIcon:Null<String>=null;var sourceHealthIconAssigned=false;var sourceHealthIconValue:String;
 public var curCharacter:String;
 public var healthIcon(get,never):String;
 public function new(character:String, data:Dynamic) {
  curCharacter=character;
  nightmareVisionHealthIcon=nightmareVisionHealthIconFromDefinition(data);
 }
''' + getter + '''
''' + resolver + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var authored=new Character('mobian_bf_firstperson',{healthicon:'bfmobian'});
  check(authored.healthIcon=='bfmobian','source healthicon identity');
  var absent=new Character('mobian-bf',{});
  check(absent.healthIcon=='face','missing source healthicon uses CharacterData template');
  var explicitNull=new Character('mobian-null',{healthicon:null});
  check(explicitNull.healthIcon=='face','null source healthicon uses CharacterData template');
  var blank=new Character('blank-id',{healthicon:''});
  check(blank.healthIcon=='','authored blank source healthicon is preserved');
  var native=new Character('native-bf',null);
  check(native.healthIcon=='native-bf','native character identity fallback');
  var invalid=new Character('invalid-id',{healthicon:7});
  check(invalid.healthIcon=='face','invalid source healthicon uses safe template icon');
  Sys.println('nightmare-vision-character-health-icon-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nightmare-vision-character-health-icon-ok', result.stdout)
        self.assertIn('healthicon must be a string', result.stdout + result.stderr)

    def test_shared_character_refresh_uses_icon_loader_and_health_color_update(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        source = (ROOT / 'source/PlayState.hx').read_text()
        refresh = function_body(source, 'refreshCharacterIconsAndColors')
        fixture = '''
class Character { public var healthIcon:String; public function new(id:String) healthIcon=id; }
class HealthIcon {
 public var character:String=''; public var selections:Array<String>=[];
 public var bopResets:Int=0;
 public function new(id:String) character=id;
 public function changeIcon(id:String):Void {if(character!=id)switchAnim(id);}public function switchAnim(id:String):Dynamic { character=id; selections.push(id); bopResets++; return this; }
}
class PlayState {
 public var iconP1:HealthIcon; public var iconP2:HealthIcon;public var sourceHUDIconMode=0;public var psychSourceIconP1:HealthIcon;public var psychSourceIconP2:HealthIcon;public var playHUD:Dynamic;
 public var boyfriend:Character; public var dad:Character;
 public var healthBar:Dynamic={}; public var colorRefreshes:Int=0;
 public function new() {}
 public function runRefresh():Void refreshCharacterIconsAndColors();
 public function updateHealthColors():Void colorRefreshes++;
''' + refresh + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var state=new PlayState();
  state.iconP1=new HealthIcon('old-player'); state.iconP2=new HealthIcon('old-opponent');
  state.boyfriend=new Character('bfmobian'); state.dad=new Character('zeph');
  state.runRefresh();
  check(state.iconP1.character=='bfmobian' && state.iconP2.character=='zeph',
   'shared refresh must pass live character icon ids to HealthIcon');
  check(state.iconP1.bopResets==1 && state.iconP2.bopResets==1,
   'changed icon ids use the existing icon loader once');
  check(state.colorRefreshes==1,'shared refresh must update the health-bar colors');
  // A girlfriend-only swap leaves both source HUD icon ids unchanged.
  state.boyfriend=new Character('bfmobian'); state.dad=new Character('zeph');
  state.runRefresh();
  check(state.iconP1.bopResets==1 && state.iconP2.bopResets==1,
   'unchanged icon ids preserve current bop state');
  check(state.colorRefreshes==2,'character changes still refresh bar colors');
  state.iconP1.character='no-gf';
  state.healthBar=null; state.boyfriend=new Character('new-player-icon');
  state.runRefresh();
  check(state.iconP1.character=='new-player-icon' && state.iconP1.bopResets==2
   && state.colorRefreshes==2,
   'real icon id replaces a no-girlfriend sentinel even without a health bar');
  Sys.println('nightmare-vision-shared-hud-refresh-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nightmare-vision-shared-hud-refresh-ok', result.stdout)

    def test_bank_and_native_character_swaps_use_psych_refresh_route(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        adapter = (ROOT / 'source/NightmareVisionHUDAdapter.hx').read_text()
        self.assertIn('refreshCharacterPresentation:refreshCharacterIconsAndColors,', play)
        character = (ROOT / 'source/Character.hx').read_text()
        self.assertIn('nightmareVisionHealthIcon = nightmareVisionHealthIconFromDefinition(nightmareVisionOwnedCharacter);',
                      character)
        bank_activate = play[play.index('}, function(previous, next) {', play.index('function nightmareVisionCharacterBank')):
                             play.index('nightmareVisionCharacterBanks.set(type, bank)')]
        self.assertIn('switchToChar(actor, role, false, true);', bank_activate)
        self.assertNotIn('refreshCharacterHUD();', bank_activate)
        self.assertIn('refreshCharacterHUD();', function_body(play, 'switchToChar'))
        self.assertIn('refreshCharacterHUD();', function_body(play, 'switchCharacter'))
        self.assertIn('if (playHUD != null) playHUD.onCharacterChange();', play)
        refresh = function_body(play, 'refreshCharacterIconsAndColors')
        self.assertIn('iconP1.character != boyfriend.healthIcon', refresh)
        self.assertIn('iconP1.switchAnim(boyfriend.healthIcon);', refresh)
        self.assertIn('iconP2.character != dad.healthIcon', refresh)
        self.assertIn('iconP2.switchAnim(dad.healthIcon);', refresh)
        self.assertIn('refreshCharacterPresentation();', adapter)
        self.assertIn('refreshCharacterPresentation = null;', adapter)


if __name__ == '__main__':
    unittest.main()
