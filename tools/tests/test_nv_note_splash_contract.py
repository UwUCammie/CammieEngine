"""Actual tap sprite comparisons against the complete pinned NV donor class."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_splash_fixture_support import splash_fixture_files

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/objects/note/NoteSplash.hx'


class NightmareVisionNoteSplashContractTest(unittest.TestCase):
    def test_constructor_cache_setup_and_update_match_full_donor(self):
        if not DONOR.is_file():
            self.skipTest('pinned Nightmare Vision donor unavailable')
        donor = re.sub(r'^(package|import)[^\n]*\n', '', DONOR.read_text(), flags=re.M)
        donor = donor.replace('class NoteSplash extends funkin.game.modchart.ModchartNote', 'class DonorTap extends DonorSprite')
        for name in ['update', 'drawSimple', 'drawComplex']:
            donor = donor.replace('override function ' + name, 'override public function ' + name)
        source = (DONOR.parents[1] / 'FunkinSprite.hx').read_text()
        offsets = source[source.index('\tinline function transformSpriteOffset'):source.index('\toverride function clone')]
        offsets = offsets.replace('inline function transformSpriteOffset', 'public function transformSpriteOffset')
        files = splash_fixture_files('', offsets)
        files['DonorTap.hx'] = 'import Strumline.StrumNote;import flixel.FlxCamera;using StringTools;\ntypedef RGBGraphics=NightmareVisionRGBGraphics;typedef NoteSkin=NightmareVisionNoteSkin;typedef PlayField=NightmareVisionPlayFieldView;typedef FlxColor=Int;\n' + donor
        files.pop('DonorSplash.hx')
        files['DonorSprite.hx'] = files['DonorSprite.hx'].replace('public function addOffset', 'public function addAnimByPrefix(n:String,p:String,f:Int=24,l:Bool=true)animation.addByPrefix(n,p,f,l);public function addOffset')
        files['NightmareVisionPlayFieldView.hx'] = files['NightmareVisionPlayFieldView.hx'].replace('public var player=1;', 'public var player=1;public var trackNoteSplashes=true;')
        skin = files['NightmareVisionNoteSkin.hx']
        skin = skin.replace('public var sustainSplashTexture=', 'public var keys=2;public var splashTexture="tap";public var splashScale=1.5;public var splashOffsets=[flixel.math.FlxPoint.get(2,3),flixel.math.FlxPoint.get(7,11)];public var splashAnims:Array<Dynamic>=[{anim:"note0",xmlName:"purple",offsets:[3.,5.],fps:7,looping:true},{anim:"note1",xmlName:"blue",offsets:[13.,15.],fps:8,looping:true}];public var sustainSplashTexture=')
        skin = skin.replace('public function loadSustainSplashFrames()', 'public static function resolveData(d:Dynamic){d.noteSplashAnimations=NoteUtil.DEFAULT_NOTESPLASH_ANIMATIONS;}public function loadNoteSplashFrames(t:String):Dynamic return Paths.getAtlasFrames(t);public function loadSustainSplashFrames()')
        files['NightmareVisionNoteSkin.hx'] = skin
        files['Paths.hx'] = files['Paths.hx'].replace('public static var loads:', 'public static function getSparrowAtlas(t:String):Dynamic return getAtlasFrames(t);public static var loads:')
        files['NoteUtil.hx'] = files['NoteUtil.hx'].replace('public static var skins=', 'public static var DEFAULT_NOTESPLASH_ANIMATIONS:Array<Dynamic>=[{anim:"note0",xmlName:"fallback0",offsets:[0.,0.]},{anim:"note1",xmlName:"fallback1",offsets:[0.,0.]}];public static var skins=')
        files['FakeAnimation.hx'] = files['FakeAnimation.hx'].replace('curAnim={name:n}', 'curAnim={name:n,finished:false}')
        files['FakeAnimation.hx'] = files['FakeAnimation.hx'].replace('public var pending:String;', 'public var pending:String;public var markFinished=false;')
        files['flixel/FlxSprite.hx'] = files['flixel/FlxSprite.hx'].replace('public function update(e:Float){', 'public function update(e:Float){if(animation.markFinished){animation.markFinished=false;animation.curAnim.finished=true;}')
        files['Main.hx'] = r'''
class Main {
 static function check(v:Bool,m:String)if(!v)throw m;
 static function make(host:Bool):Dynamic return host?new NightmareVisionNoteSplash(9,13,1,1,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return "Both"}):new DonorTap(9,13,1,1);
 static function snap(s:Dynamic):String {var values:Array<Dynamic>=[s.x,s.y,s.noteData,s.player,s.skin==null,s._textureLoaded,s.alpha,s.alive,s.visible,s.angle,s.scale.x,s.baseScale.x,s.width,s.height,s.spriteOffset.x,s.spriteOffset.y,s.animOffset.x,s.animOffset.y,s.animation.curAnim==null?"":s.animation.curAnim.name,s.animation.plays.join(","),s.rgbGraphics.colors.join(","),s.rgbGraphics.enabled,s.kills];return values.join("|");}
 static function scenario(host:Bool,n:Int):String {
  NoteUtil.skins=[new NightmareVisionNoteSkin(),new NightmareVisionNoteSkin()];Paths.loads=[];var s=make(host);var out=[snap(s)];var note=new Note();var field=new NightmareVisionPlayFieldView();var strum=new Strumline.StrumNote();var rgb=new NightmareVisionRGBGraphics();rgb.setColors([4,5,6]);
  check(s.noteData==1&&s.player==1&&s.skin==null&&s.scale.x==1.5&&s.animation.curAnim==null,"constructor state and inert seed");
  s.alpha=.37;s.angle=23;s.visible=false;s.setupNoteSplash(strum,note,"tap",rgb,field);out.push(snap(s));check(s.x==9&&s.y==13&&s.alpha==.37&&s.angle==23&&!s.visible,"tracked setup does not normalize unrelated fields");rgb.setColors([7,8,9]);check(s.rgbGraphics.colors[0]==4,"RGB input copied");
  var anim:Dynamic=s.animation.definitions.get("note1");check(anim.fps==24&&!anim.looping,"source ignores metadata fps and looping");
  switch(n){
   case 0: field.trackNoteSplashes=false;s.setupNoteSplash(strum,note,"tap",null,field);out.push(snap(s));strum.x+=80;s.update(.1);out.push(snap(s));
   case 1: NoteUtil.skins[1].splashAnims[1].xmlName="changed";s.setupNoteSplash(strum,note,"tap",null,field);check(s.animation.definitions.get("note1").prefix=="blue","metadata mutation alone does not invalidate cache");s.setupNoteSplash(strum,note,"new",null,field);check(s.animation.definitions.get("note1").prefix=="changed","explicit new texture reloads current metadata");out.push(snap(s));
   case 2: NoteUtil.skins[1].splashScale=9;s.scale.set(3,4);s.baseScale.set(5,6);s.kill();s.setupNoteSplash(strum,note,"tap",null,field);check(!s.alive&&s.scale.x==3&&s.baseScale.x==5,"setup neither revives nor resets constructor scale");out.push(snap(s));
   case 3: s.setupNoteSplash(strum,null,null,null,field);out.push(snap(s));check(s.noteData==0&&s._textureLoaded=="noteSplashes","nullable note/texture source defaults");
   case 4: s.animation.curAnim=null;s.update(.1);out.push(snap(s));s.playAnim("note1");s.animation.curAnim.finished=true;s.update(.1);out.push(snap(s));
   case 5: field.trackNoteSplashes=false;NoteUtil.skins[1].splashOffsets=null;s.setupNoteSplash(strum,note,"tap",null,field);out.push(snap(s));
   case 6: s.canPlayAnimations=false;var c:Int=s.centers;s.playAnim("note1");check(s.centers==c+1,"centers even when parent playback refused");out.push(snap(s));
   case 7: var err=false;try s.setupNoteSplash(strum,note,"tap",null,null)catch(_:Dynamic)err=true;check(err,"source optional field dereference remains invalid");out.push(snap(s));
   case 8: NoteUtil.skins[1].inEngineColoring=false;s.setColors([11,12,13]);out.push(snap(s));s.setColors(null);out.push(snap(s));
   case 9: NoteUtil.skins[1].splashAnims=null;s.setupNoteSplash(strum,note,"fallback",null,field);check(s.animation.definitions.get("note1").prefix=="fallback1","default animation catalogue");out.push(snap(s));
   case 10: s.animation.markFinished=true;s.update(.1);check(s.alive,"animation finishing in parent update retires next update");out.push(snap(s));s.update(.1);out.push(snap(s));
   case 11: NoteUtil.skins[1].keys=3;NoteUtil.skins[1].splashAnims=[null,{anim:null,xmlName:"skip",offsets:[0,0]}];s.setupNoteSplash(strum,note,"empty",null,field);out.push(snap(s));
  }
  out.push(Paths.loads.join(","));return out.join("\n");
 }
 static function main(){for(i in 0...12){var expected=scenario(false,i),actual=scenario(true,i);check(actual==expected,"scenario "+i+"\n"+actual+"\nexpected\n"+expected);}
  var s=new NightmareVisionNoteSplash(0,0,0,0,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return "Both"});s.draw();check(s.rgbGraphics.applied==1&&s.shader==s.rgbGraphics,"native RGB draw bridge");var p=s.baseScale;s.destroy();check(p.puts==1&&s.skin==null&&s.rgbGraphics==null,"shared offset ownership teardown");
 }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            (temp / 'flixel/util').mkdir(parents=True, exist_ok=True)
            (temp / 'flixel/util/FlxSignal.hx').write_text((ROOT / '.haxelib/flixel/6,1,2/flixel/util/FlxSignal.hx').read_text())
            (temp / 'flixel/util/FlxDestroyUtil.hx').write_text('package flixel.util;interface IFlxDestroyable {public function destroy():Void;}class FlxDestroyUtil {public static function destroyArray<T:IFlxDestroyable>(a:Array<T>):Array<T>{if(a!=null)for(v in a)if(v!=null)v.destroy();return null;}}')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            (temp / 'CppMain.hx').write_text('class CppMain {static function main(){var s=new NightmareVisionNoteSplash(0,0,0,0,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return "Both"});s.setupNoteSplash(new Strumline.StrumNote(),new Note(),"tap",null,new NightmareVisionPlayFieldView());}}')
            env = os.environ.copy()
            env['HAXEPATH'] = str(ROOT / '.tools/haxe')
            env['NEKOPATH'] = str(ROOT / '.tools/neko')
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'CppMain', '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-10000:])
        self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-10000:])
