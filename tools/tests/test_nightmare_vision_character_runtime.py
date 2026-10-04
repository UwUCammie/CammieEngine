"""Run the native Nightmare Vision CharacterData adapter against lightweight atlas stubs."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def function_body(source, name):
    marker = 'function ' + name + '('
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ''
        if line_comment:
            if char == '\n':
                line_comment = False
        elif block_comment:
            if char == '*' and next_char == '/':
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char == '/' and next_char == '/':
            line_comment = True
            index += 1
        elif char == '/' and next_char == '*':
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


class NightmareVisionCharacterRuntimeTest(unittest.TestCase):
    def test_character_json_installs_animate_and_sparrow_animations(self):
        source = (ROOT / 'source/Character.hx').read_text()
        visual_builder = function_body(source, 'loadNightmareVisionCharacterVisual')
        health_color_loader = function_body(source, 'loadNightmareVisionHealthColors')
        health_color_array = function_body(source, 'nightmareVisionColorArrayFromPacked')
        health_colour_getter = function_body(source, 'get_healthColour')
        health_colour_setter = function_body(source, 'set_healthColour')
        health_array_getter = function_body(source, 'get_healthColorArray')
        health_array_setter = function_body(source, 'set_healthColorArray')
        number_helper = function_body(source, 'nightmareVisionNumber')
        pair_helper = function_body(source, 'nightmareVisionPair')
        fixture = '''import sys.FileSystem;
abstract FlxColor(Int) from Int to Int {
 public static function fromRGB(red:Int,green:Int,blue:Int,alpha:Int=255):FlxColor
  return cast ((alpha<<24)|((red&255)<<16)|((green&255)<<8)|(blue&255));
 public static function fromString(value:String):Null<FlxColor> {
  var clean=StringTools.trim(value);
  if(!StringTools.startsWith(clean,'#')&&!StringTools.startsWith(clean,'0x'))return null;
  var hex=StringTools.startsWith(clean,'#')?clean.substr(1):clean.substr(2);
  var parsed=Std.parseInt('0x'+hex);
  return parsed==null?null:cast(hex.length==6?parsed|0xFF000000:parsed);
 }
}
class FakePoint {
 public var x:Float = 1;
 public var y:Float = 1;
 public function new() {}
 public function set(x:Float, y:Float):Void { this.x=x; this.y=y; }
}
class FlxAtlasFrames {
 public var atlasKeys:Array<String> = [];
 public function new(?key:String) {if(key!=null)atlasKeys.push(key);}
 public function addAtlas(atlas:FlxAtlasFrames,?overwriteHash:Bool=false):FlxAtlasFrames {
  atlasKeys=atlasKeys.concat(atlas.atlasKeys); return this;
 }
}
class FlxAnimateFrames {
 public static function combineAtlas(atlases:Array<FlxAtlasFrames>):FlxAtlasFrames {
  if(atlases==null||atlases.length==0)return null;
  var result=atlases[0];
  for(i in 1...atlases.length) result.addAtlas(atlases[i]);
  return result;
 }
}
class NightmareVisionPaths {
 public var root:String;
 public static var lastKey:String='';
 public static var lastOwnerCheck:Bool=true;
 public static var atlasCalls:Array<String>=[];
 public function new(root:String) this.root=root;
 public function getTextureAtlas(key:String,?parentFolder:String,allowGPU:Bool=true,checkMods:Bool=true):FlxAtlasFrames {
  lastKey=key; lastOwnerCheck=checkMods; atlasCalls.push(key); return new FlxAtlasFrames(key);
 }
}
class FakeAnimation {
 public var calls:Array<Array<Dynamic>> = [];
 var names:Map<String,Bool> = [];
 public function new() {}
 public function exists(name:String):Bool return names.exists(name);
 public function findFrameLabelIndices(label:String):Array<Int>
  return label == 'Label/Idle' ? [0,1,2] : [];
 function record(name:String, kind:String, source:String, indices:Array<Int>, fps:Float, loop:Bool):Void {
  calls.push([kind,name,source,indices,fps,loop]); names.set(name,true);
 }
 public function add(name:String,indices:Array<Int>,fps:Float,loop:Bool):Void
  record(name,'raw-indices','',indices,fps,loop);
 public function addByFrameLabel(name:String,label:String,fps:Float,loop:Bool,?flipX:Bool,?flipY:Bool):Void
  if(label=='Label/Idle') record(name,'frame-label',label,[],fps,loop);
 public function addByFrameLabelIndices(name:String,label:String,indices:Array<Int>,fps:Float,loop:Bool,?flipX:Bool,?flipY:Bool):Void
  if(label=='Label/Idle') record(name,'frame-label-indices',label,indices,fps,loop);
 public function addBySymbol(name:String,symbol:String,fps:Float,loop:Bool,?flipX:Bool,?flipY:Bool):Void
  if(symbol.indexOf('Dusk/')==0) record(name,'symbol',symbol,[],fps,loop);
 public function addBySymbolIndices(name:String,symbol:String,indices:Array<Int>,fps:Float,loop:Bool,?flipX:Bool,?flipY:Bool):Void
  if(symbol.indexOf('Dusk/')==0) record(name,'symbol-indices',symbol,indices,fps,loop);
 public function addByPrefix(name:String,prefix:String,fps:Float,loop:Bool):Void
  record(name,'prefix',prefix,[],fps,loop);
 public function addByIndices(name:String,prefix:String,indices:Array<Int>,postfix:String,fps:Float,loop:Bool):Void
  record(name,'indices',prefix,indices,fps,loop);
}
class Character {
 public var animation:FakeAnimation = new FakeAnimation();
 public var frames:FlxAtlasFrames;
 public var scale:FakePoint = new FakePoint();
 public var animOffsets:Map<String,Array<Dynamic>> = [];
 public var camOffsets:Map<String,Array<Dynamic>> = [];
 public var cameraPosition:Array<Float> = [0,0];
 public var positionArray:Array<Float> = [0,0];
 public var enemyOffsetX:Int=0; public var playerOffsetX:Int=0; public var gfOffsetX:Int=0;
 public var enemyOffsetY:Int=0; public var playerOffsetY:Int=0; public var gfOffsetY:Int=0;
 public var antialiasing:Bool=true; public var flipX:Bool=false; public var holdTime:Float=4;
 public var beatInterval:Int=2; public var danceEvery:Int=1; public var curCharacter:String='dusk';
 public var hitboxUpdates:Int=0;
 public var isPlayer:Bool=false; public var playerColor:FlxColor=0xFF66FF33; public var enemyColor:FlxColor=0xFFFF0000;
 public var nightmareVisionCharacterData:Dynamic;
 var nightmareVisionHealthColour:Null<FlxColor>=null;
 var nightmareVisionHealthColorArray:Array<Int>=[255,0,0];
 public var healthColour(get,set):FlxColor;
 public var healthColorArray(get,set):Array<Int>;
 public function new() {}
 public function updateHitbox():Void hitboxUpdates++;
''' + visual_builder.replace('function loadNightmareVisionCharacterVisual(', 'public function loadNightmareVisionCharacterVisual(') + '\n' + health_color_loader + '\n' + health_color_array + '\n' + health_colour_getter + '\n' + health_colour_setter + '\n' + health_array_getter + '\n' + health_array_setter + '\n' + number_helper + '\n' + pair_helper + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function packed(value:FlxColor):Int return cast value;
 static function main():Void {
  var args=Sys.args();
  var animatePath=args[0];
  var sparrowPath=args[1];
  var multiPath=args[2];
  var ownerRoot=args[3];
  var authoredHealthColors:Array<Int>=[12,34,56];
  var dusk:Dynamic={image:'characters/Dusk', scale:1.5, no_antialiasing:true, flip_x:false,
   camera_position:[-545,-141], sing_duration:6.1, dance_every:1, position:[450,10],
   healthbar_colors:authoredHealthColors, healthbar_colour:-8751940,
   animations:[
    {anim:'singLEFT', name:'Dusk/Left', indices:[0,1], fps:24, loop:false,
     offsets:[590,109], cameraOffset:[-30,0]},
    {anim:'danceLeft', name:'Label/Idle', indices:[0,1], fps:24, loop:false,
     offsets:[0,0]},
    {anim:'danceRight', name:'Dusk/Idle', indices:[], fps:24, loop:false,
     offsets:[0,0]}
   ]};
  var actor=new Character();
  check(actor.loadNightmareVisionCharacterVisual(dusk,animatePath,ownerRoot),'Animate visual initialization');
  check(actor.frames!=null && NightmareVisionPaths.lastKey=='characters/Dusk' && NightmareVisionPaths.lastOwnerCheck,
   'Animate atlas goes through owner-scoped paths');
  check(actor.animation.exists('singLEFT') && actor.animation.exists('danceLeft')
   && actor.animation.exists('danceRight'),'Dusk sing and dance animation registrations');
  check(actor.animation.calls[0][0]=='symbol-indices' && actor.animation.calls[0][2]=='Dusk/Left',
   'Animate symbol-index fallback for Dusk/Left');
  check(actor.animation.calls[1][0]=='frame-label-indices' && actor.animation.calls[1][2]=='Label/Idle',
   'Animate frame-label path is preferred when available');
  check(actor.animOffsets.get('singLEFT')[0]==590 && actor.camOffsets.get('singLEFT')[0]==-30,
   'animation and camera offsets preserved');
  check(actor.positionArray[0]==450 && actor.positionArray[1]==10,'raw source position array preserved');
  check(actor.cameraPosition[0]==-545 && actor.cameraPosition[1]==-141,'camera_position preserved');
  check(actor.enemyOffsetX==450 && actor.playerOffsetX==450 && actor.gfOffsetY==10,
   'CharacterData position becomes the shared stage-slot offset');
  check(actor.holdTime>6 && actor.beatInterval==1 && actor.danceEvery==1,'sing and dance timing preserved');
  check(actor.scale.x==1.5 && actor.hitboxUpdates==1 && !actor.antialiasing && !actor.flipX,
   'scale, antialiasing, and authored flip are applied');
  check(actor.healthColorArray==authoredHealthColors
   && packed(actor.healthColour)==0xFF0C2238,
   'CharacterData healthbar_colors retains array identity and precedes packed healthbar_colour');
  authoredHealthColors[0]=99;
  check(actor.healthColorArray[0]==99,'mutated authored health RGB remains live on Character');

  var sparrow:Dynamic={scale:1, healthbar_colour:0xFF123456,
   animations:[{anim:'idle',name:'idle',indices:[],fps:12,loop:true,offsets:[2,3]}]};
  var sparrowActor=new Character();
  check(sparrowActor.loadNightmareVisionCharacterVisual(sparrow,sparrowPath,ownerRoot),'Sparrow visual initialization');
  check(sparrowActor.frames!=null && NightmareVisionPaths.lastKey=='characters/Sparrow'
   && NightmareVisionPaths.lastOwnerCheck,'Sparrow atlas goes through owner-scoped paths');
  check(sparrowActor.animation.exists('idle') && sparrowActor.animOffsets.get('idle')[1]==3,
   'Sparrow animation registration and offsets');
  check(sparrowActor.healthColorArray[0]==0x12 && sparrowActor.healthColorArray[1]==0x34
   && sparrowActor.healthColorArray[2]==0x56,
   'packed healthbar_colour initializes the Character RGB fallback');

  var multi:Dynamic={animations:[{anim:'stomp',name:'Stomp/Loop',indices:[],fps:12,loop:true}]};
  var multiActor=new Character();
  NightmareVisionPaths.atlasCalls=[];
  check(multiActor.loadNightmareVisionCharacterVisual(multi,multiPath,ownerRoot),
   'multi-Sparrow visual initialization');
  check(multiActor.frames!=null && multiActor.frames.atlasKeys.join('|')=='characters/Boy|characters/Stomp',
   'comma-separated Sparrow atlases are combined into one character frame collection');
  check(NightmareVisionPaths.atlasCalls.join('|')=='characters/Boy|characters/Stomp',
   'every component is loaded through the selected owner Paths facade');
  check(multiActor.animation.exists('stomp'),'multi-atlas character animation registration');
  Sys.println('nightmare-vision-character-runtime-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            (work / 'PsychCharacterOrientation.hx').write_text(
                (ROOT / 'source/PsychCharacterOrientation.hx').read_text(), newline='\n')
            owner = work / 'assets/imported_mods/nmv-owner'
            owner.mkdir(parents=True)
            owner_arg = owner.relative_to(ROOT).as_posix()
            animate = owner / 'images/characters/Dusk'
            animate.mkdir(parents=True)
            (animate / 'Animation.json').write_text('{}', newline='\n')
            sparrow = owner / 'images/characters/Sparrow'
            sparrow.parent.mkdir(parents=True, exist_ok=True)
            Path(str(sparrow) + '.png').write_text('', newline='\n')
            Path(str(sparrow) + '.xml').write_text('<TextureAtlas/>', newline='\n')
            for name in ('Boy', 'Stomp'):
                atlas = owner / 'images/characters' / name
                Path(str(atlas) + '.png').write_text('', newline='\n')
                Path(str(atlas) + '.xml').write_text('<TextureAtlas/>', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '--run', 'Main',
                 owner_arg + '/images/characters/Dusk', owner_arg + '/images/characters/Sparrow',
                 owner_arg + '/images/characters/Boy,' + owner_arg + '/images/characters/Stomp', owner_arg],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nightmare-vision-character-runtime-ok', result.stdout)

    def test_constructor_uses_owner_data_without_jsonbased_interpreter(self):
        source = (ROOT / 'source/Character.hx').read_text()
        constructor = source[source.index('\tpublic function new('):]
        self.assertIn('Song.characterRootForSong(Song.storageFolder(PlayState.SONG),', constructor)
        self.assertIn('NightmareVisionCharacterData.load(nightmareVisionOwnerRoot, curCharacter)', constructor)
        self.assertIn('loadNightmareVisionCharacterVisual(nightmareVisionOwnedCharacter, nightmareVisionImageRoot,', constructor)
        self.assertIn('codenameLiveDefinition == null && !nightmareVisionCharacterOwned', constructor)
        self.assertIn('&& !nightmareVisionCharacterOwned && isPlayer && !noFlip', constructor)
        self.assertIn("var findFrameLabels = Reflect.field(animation, 'findFrameLabelIndices')", source)
        self.assertIn("var addBySymbol = Reflect.field(animation, 'addBySymbol')", source)


if __name__ == '__main__':
    unittest.main()
