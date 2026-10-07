"""Complete donor alphabet classes with pinned group methods and typed IO."""
from pathlib import Path
import re
from source_attachment_fixture_support import attachment_fixture_files
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

def alphabet_fixture_files(parent_version="6.1.2"):
    files=attachment_fixture_files()
    for n in ['DonorPsychAttachedSprite.hx','DonorNVAttachedNode.hx','AttachmentContext.hx']:
        files.pop(n,None)
    native=ROOT/'.haxelib/flixel/6,1,2/flixel'
    sg=(native/'group/FlxSpriteGroup.hx').read_text()
    g=(native/'group/FlxGroup.hx').read_text()
    if parent_version == "5.6.1":
        base=ROOT/'tmp/upstream-flixel-5.6.1/flixel/group'
        oldsg=(base/'FlxSpriteGroup.hx').read_text()
        oldg=(base/'FlxGroup.hx').read_text()
        for key,names,old,new in [('flixel/group/FlxGroup.hx',['public function add(', 'public function getFirstNull(', 'override public function update(', 'override public function destroy('],oldg,g),('flixel/group/FlxSpriteGroup.hx',['public function add(', 'function preAdd(', 'public function transformChildren<', 'override function set_x(', 'override function set_y(', 'override function set_alpha(', 'override public function update('],oldsg,sg)]:
            for name in names:
                files[key]=files[key].replace(method(new,name).replace('override function','override public function'),method(old,name).replace('override function','override public function'))
        files['flixel/group/FlxGroup.hx']=files['flixel/group/FlxGroup.hx'].replace('var _memberAdded:flixel.util.FlxDestroyUtil.IFlxDestroyable;var _memberRemoved:flixel.util.FlxDestroyUtil.IFlxDestroyable;', 'var _memberAdded:flixel.util.FlxSignal.FlxTypedSignal<T->Void>;var _memberRemoved:flixel.util.FlxSignal.FlxTypedSignal<T->Void>;')
        files['flixel/group/FlxSpriteGroup.hx']=files['flixel/group/FlxSpriteGroup.hx'].replace('public var directAlpha=false;', 'var _sprites(get,never):Array<T>;function get__sprites()return group.members;public var directAlpha=false;')
        sg=oldsg;g=oldg
    add=''.join(method(g,n) for n in ['public function recycle(', 'public function getFirstAvailable(', 'public function remove('])
    files['flixel/group/FlxGroup.hx']=files['flixel/group/FlxGroup.hx'].replace('public var maxSize=0;', 'public var maxSize=0;var _marker=0;').replace('function onMemberAdd(v:T){}','function onMemberAdd(v:T){}function onMemberRemove(v:T){}'+add)
    extras=''.join(method(sg,n) for n in ['public inline function recycle(', 'public function remove('])+sg[sg.index('inline function scaleTransform('):sg.index(';',sg.index('inline function scaleTransform('))+1]+'public function compareScale(p:flixel.math.FlxPoint){transformChildren(scaleTransform,p);}'
    files['flixel/group/FlxSpriteGroup.hx']=files['flixel/group/FlxSpriteGroup.hx'].replace('import flixel.math.FlxMath;', 'import flixel.math.FlxRect;import flixel.math.FlxPoint;import flixel.math.FlxMath;').replace('override public function destroy()',extras+'override public function destroy()')
    files['flixel/FlxBasic.hx']=files['flixel/FlxBasic.hx'].replace('public function destroy()', 'public function kill(){exists=false;alive=false;}public function revive(){exists=true;alive=true;}public function destroy()')
    files['flixel/FlxG.hx']='package flixel;class FlxG {public static var width=1280;public static var log={error:function(v:Dynamic){},warn:function(v:Dynamic){}};}'
    files['IconAnimation.hx']=files['IconAnimation.hx'].replace('public var numFrames(get,never):Int;', 'public var name(get,never):String;function get_name()return _curAnim==null?null:_curAnim.name;public var numFrames(get,never):Int;',1)
    files['flixel/graphics/FlxGraphic.hx']=files['flixel/graphics/FlxGraphic.hx'].replace('public var width:Int;', 'public var key:String;public var width:Int;')
    files['flixel/graphics/frames/FlxAtlasFrames.hx']='package flixel.graphics.frames;class FlxAtlasFrames {public static var lastLoad:Array<String>=[];public static function fromSparrow(g:flixel.graphics.FlxGraphic,p:String){lastLoad=[g.key,p];return new FlxAtlasFrames();}public var frames:Array<FlxFrame>=[];public function new(){for(c in ["a","b","c","question","1","_","space"]){for(p in [" lowercase"," uppercase"," bold"," normal"])frames.push(new FlxFrame(c+p+"0000"));}}}class FlxFrame {public var name:String;public var w=19;public var h=31;public function new(n:String)name=n;}'
    files['flixel/FlxSprite.hx']=files['flixel/FlxSprite.hx'].replace('public var frames:Dynamic;', 'public var frames(default,set):Dynamic;function set_frames(v:Dynamic){frames=v;if(v!=null && v.frames.length>0){frameWidth=v.frames[0].w;frameHeight=v.frames[0].h;}return v;}')
    files['AlphabetIO.hx']="""class AlphabetIO {public var data:String='{\"allowed\":\"abc1_? ",\"characters\":{\"a\":{\"normal\":[3,5],\"bold\":[7,9]},\"?\":{\"animation\":\"question\"}}}';public var log:Array<String>=[];public var fail=false;public var aa=true;public function new(){}public function path(s:String){log.push('path:'+s);return 'owned/'+s;}public function exists(s:String){log.push('exists:'+s);return !StringTools.contains(s,'missing');}public function text(s:String){log.push('text:'+s);if(fail)throw 'read-failed';return data;}public function atlas(s:String){log.push('atlas:'+s);return new flixel.graphics.frames.FlxAtlasFrames();}public function owner():PsychAlphabetOwner return {atlas:atlas,getPath:path,exists:exists,text:text,antialiasing:function()return aa};}"""
    files['Paths.hx']='class Paths {public static var io:AlphabetIO;public static function getPath(s:String)return io.path(s);public static function getSparrowAtlas(s:String)return io.atlas(s);}'
    files['ClientPrefs.hx']='class ClientPrefs {public static var data(get,never):Dynamic;static function get_data()return {antialiasing:Paths.io.aa};}'
    files['openfl/utils/Assets.hx']='package openfl.utils;class Assets {public static function exists(p:String,t:Dynamic)return Paths.io.exists(p);public static function getText(p:String)return Paths.io.text(p);}'
    source=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/objects/Alphabet.hx').read_text()
    source=re.sub(r'^(package|import)[^\n]*\n','',source,flags=re.M)
    source=re.sub(r'\bAlphabet\b','DonorAlphabet',source)
    source=re.sub(r'\bAlphaCharacter\b','DonorAlphaCharacter',source)
    source=re.sub(r'\bAlignment\b','DonorAlignment',source)
    source=source.replace('override function update','override public function update').replace('recycle(DonorAlphaCharacter, true)','recycle(DonorAlphaCharacter, null, true)')
    files['DonorAlphabet.hx']='import haxe.Json;import openfl.utils.Assets;import flixel.FlxSprite;import flixel.group.FlxSpriteGroup;import flixel.math.FlxPoint;import flixel.math.FlxMath;import flixel.FlxG;using StringTools;final TEXT:Dynamic=null;'+source
    attached=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/objects/AttachedText.hx').read_text()
    attached=re.sub(r'^package[^\n]*\n','',attached,flags=re.M).replace('class AttachedText','class DonorAttachedText').replace('extends Alphabet','extends DonorAlphabet').replace('override function update','override public function update')
    files['DonorAttachedText.hx']='import flixel.FlxSprite;'+attached
    path_source=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/backend/Paths.hx').read_text()
    atlas_method=method(path_source,'inline static public function getSparrowAtlas(')
    files['DonorPathsAtlas.hx']='import flixel.graphics.FlxGraphic;import flixel.graphics.frames.FlxAtlasFrames;using StringTools;final TEXT:Dynamic=null;class Language {public static function getFileTranslation(s:String)return s;}class DonorPathsAtlas {public static var mask=0;public static function image(s:String,?p:String,?gpu:Bool=true){var g=new FlxGraphic(33,27);g.key=(mask&1)!=0?"owned/images/"+s+".png":"assets/images/source_compat/psych/alphabet.png";return g;}public static function getPath(s:String,t:Dynamic,?p:String)return (mask&2)!=0?"owned/"+s:"assets/images/source_compat/psych/alphabet.xml";'+atlas_method+'}'
    return files
