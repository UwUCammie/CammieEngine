"""Exercise production substate control reads against getter-backed actions."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, ROOT, TEST_TMP

CONSUMERS = ('PauseSubState', 'GameOverSubstate', 'VictoryLoopState', 'SelectSongsState', 'CodenameModSwitchMenu')

class NativeSubstateControlsTest(unittest.TestCase):
    def test_native_menu_actions_call_live_control_getters(self):
        methods = []
        count = 0
        for consumer in CONSUMERS:
            source = (ROOT / 'source' / (consumer + '.hx')).read_text(encoding='utf-8')
            reads = sorted(set(re.findall(r'\b(?:controls|nativeControls)\.(?:UP_MENU|DOWN_MENU|ACCEPT|BACK)\b', source)))
            self.assertTrue(reads, consumer)
            methods.append('public function read' + consumer + '():Array<Bool> return [' + ','.join(reads) + '];')
            count += len(reads)
        checks = ''.join('for(value in probe.read' + name + '())if(value!=pressed)throw "' + name + ' input getter was bypassed";' for name in CONSUMERS)
        files = {
            'MusicBeatSubstate.hx': (ROOT/'source/MusicBeatSubstate.hx').read_text(encoding='utf-8'),
            'flixel/FlxG.hx': 'package flixel;class FlxG {}',
            'flixel/FlxSubState.hx': 'package flixel;class FlxSubState {public function new(){}public function create():Void{}public function update(e:Float):Void{}}',
            'TitleState.hx': 'class TitleState {public static var soundExt:String;}',
            'Conductor.hx': 'typedef BPMChangeEvent={var stepTime:Int;var songTime:Float;var bpm:Float;}class Conductor {public static var bpmChangeMap:Array<BPMChangeEvent>=[];public static var songPosition=0.;public static var stepCrochet=125.;}',
            'Controls.hx': '@:keep class Controls {public var pressed=false;public var calls=0;public function new(){}' + ''.join('public var '+name+'(get,never):Bool;inline function get_'+name+'():Bool {calls++;return pressed;}' for name in ('UP_MENU','DOWN_MENU','ACCEPT','BACK')) + '}',
            'PlayerSettings.hx': 'class PlayerSettings {public static var player1={controls:new Controls()};}',
            'Probe.hx': 'class Probe extends MusicBeatSubstate {public function new(){super();}' + ''.join(methods) + '}',
            'SourceProbe.hx': 'class SourceProbe extends Probe {public function new(){super();}override function get_controls():Dynamic return {sourceFacade:true};}',
            'Main.hx': 'class Main {static function main(){if(Reflect.getProperty(new SourceProbe(),"controls").sourceFacade!=true)throw "source controls override lost";for(probe in [new Probe(),new SourceProbe()])for(pressed in [true,false,true]){PlayerSettings.player1.controls=new Controls();PlayerSettings.player1.controls.pressed=pressed;' + checks + 'if(PlayerSettings.player1.controls.calls!='+str(count)+')throw "not all live getters called";}Sys.println("native-menu-getters:passed");}}',
        }
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            root=Path(directory)
            for name,content in files.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(root),'--run','Main'],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('native-menu-getters:passed',result.stdout)
