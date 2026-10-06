"""Execute the actual tail effect and pinned donor against identical sprite dependencies."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_splash_fixture_support import splash_fixture_files

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/objects/note/SustainSplash.hx'


class NightmareVisionSustainSplashContractTest(unittest.TestCase):
    def test_actual_sprite_matches_donor_setup_animation_and_tail_lifecycle(self):
        if not DONOR.is_file():
            self.skipTest('pinned Nightmare Vision donor unavailable')
        donor = re.sub(r'^(package|import)[^\n]*\n', '', DONOR.read_text(), flags=re.M)
        donor = donor.replace('class SustainSplash extends funkin.game.modchart.ModchartNote', 'class DonorSplash extends DonorSprite')
        donor = donor.replace('override function update', 'override public function update')
        donor = donor.replace('override function drawSimple', 'override public function drawSimple')
        donor = donor.replace('override function drawComplex', 'override public function drawComplex')
        sprite_source = (DONOR.parents[1] / 'FunkinSprite.hx').read_text()
        offset_method = sprite_source[sprite_source.index('\tinline function transformSpriteOffset'):sprite_source.index('\toverride function clone')]
        offset_method = offset_method.replace('inline function transformSpriteOffset', 'public function transformSpriteOffset')
        files = splash_fixture_files(donor, offset_method)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            # Use the pinned Flixel signal implementation, not a deduplication approximation.
            signal = ROOT / '.haxelib/flixel/6,1,2/flixel/util/FlxSignal.hx'
            (temp / 'flixel/util').mkdir(parents=True, exist_ok=True)
            (temp / 'flixel/util/FlxSignal.hx').write_text(signal.read_text())
            (temp / 'flixel/util/FlxDestroyUtil.hx').write_text('package flixel.util;interface IFlxDestroyable {public function destroy():Void;}class FlxDestroyUtil {public static function destroyArray<T:IFlxDestroyable>(a:Array<T>):Array<T>{if(a!=null)for(v in a)if(v!=null)v.destroy();return null;}}')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            # Static targets reject Float/null comparisons that eval can accept.
            skin_path = temp / 'NightmareVisionNoteSkin.hx'
            skin_path.write_text(skin_path.read_text().replace('susSplashScale:Null<Float>', 'susSplashScale:Float'))
            (temp / 'CppMain.hx').write_text('class CppMain {static function main(){var splash=new NightmareVisionSustainSplash(0,0,0,0,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return "Both"});splash.setupSplash(new Strumline.StrumNote(),new Note(),.5,true,null,new NightmareVisionPlayFieldView());}}')
            env = os.environ.copy()
            env['HAXEPATH'] = str(ROOT / '.tools/haxe')
            env['NEKOPATH'] = str(ROOT / '.tools/neko')
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp_result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'CppMain', '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-10000:])
        self.assertEqual(cpp_result.returncode, 0, (cpp_result.stdout + cpp_result.stderr)[-10000:])
