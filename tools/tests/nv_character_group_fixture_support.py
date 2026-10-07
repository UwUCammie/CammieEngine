"""Full immutable NV CharacterGroup and actual host group method dependencies."""
from pathlib import Path
import re
from nv_sprite_macro_fixture_support import nv_sprite_macro_fixture_files
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

def nv_character_group_fixture_files():
 files=nv_sprite_macro_fixture_files()
 native=ROOT/'.haxelib/flixel/6,1,2/flixel'
 files['Character.hx']='class Character extends flixel.FlxSprite {public var curCharacter:String;public var positionArray:Array<Float>=[3,5];public var danceEveryNumBeats=1;public var isPlayer=false;public var observedDestroy:Void->Void;public function new(x=0.,y=0.,name="bf",player=false){super(x,y);curCharacter=name;isPlayer=player;}override public function destroy(){if(observedDestroy!=null)observedDestroy();super.destroy();}}'
 files['NightmareVisionPlayFieldView.hx']='class NightmareVisionPlayFieldView {public var ID:Int;public var owner:Character;public function new(id:Int,c:Character){ID=id;owner=c;}}'
 files['NightmareVisionPlayFields.hx']='class NightmareVisionPlayFields {public var members:Array<NightmareVisionPlayFieldView>=[];public function new(){}}'
 files['PlayState.hx']='class PlayState {public static var instance:PlayState;public var gfPosition:flixel.math.FlxPoint;public var playFields:NightmareVisionPlayFields;public static var construct:String->Bool->Character;public function new(){gfPosition=new flixel.math.FlxPoint(100,200);playFields=new NightmareVisionPlayFields();}}'
 # Native Character construction is the only owner-dependent donor seam.
 donor=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/objects/CharacterGroup.hx').read_text(encoding='utf-8')
 donor=re.sub(r'^package[^\n]*\n','',donor,flags=re.M).replace('CharacterGroup','DonorCharacterGroup').replace('CharacterType','DonorCharacterType')
 donor=donor.replace('new Character(0, 0, newCharacter, type == BF)', 'PlayState.construct(newCharacter, type == BF)')
 files['DonorCharacterGroup.hx']='using StringTools;\n'+donor
 group=(native/'group/FlxGroup.hx').read_text(encoding='utf-8')
 g=files['flixel/group/FlxGroup.hx']
 for sig in ['public function remove(', 'public function clear(']:
  if sig not in g:g=g.rstrip()[:-1]+method(group,sig)+'}'
 g=g.replace('function onMemberAdd(v:T){}','public var added:T->Void;function onMemberAdd(v:T){if(added!=null)added(v);}')
 g=g.replace('import flixel.util.FlxDestroyUtil;', 'import flixel.util.FlxDestroyUtil;class FlxArrayUtil {public static function clearArray<T>(a:Array<T>):Void a.resize(0);}')
 files['flixel/group/FlxGroup.hx']=g
 sg=(native/'group/FlxSpriteGroup.hx').read_text(encoding='utf-8')
 g=files['flixel/group/FlxSpriteGroup.hx']
 for sig in ['public function remove(', 'public inline function clear(']:
  if sig not in g:g=g.rstrip()[:-1]+method(sg,sig)+'}'
 files['flixel/group/FlxSpriteGroup.hx']=g
 files['FixtureOwner.hx']='import NightmareVisionCharacterGroupOwner;class FixtureOwner {public var scene:PlayState;public var created=0;public var resolved:String;public var during:Void->Void;public var failure:Dynamic;public function new(){scene=new PlayState();}public function construct(name:String,player:Bool):Character{created++;if(failure!=null)throw failure;if(during!=null)during();return new Character(0,0,resolved==null?name:resolved,player);}public function owner():NightmareVisionCharacterGroupOwner return {construct:construct,scene:function()return scene==null?null:{gfPosition:scene.gfPosition,playFields:scene.playFields}};}'
 return files
