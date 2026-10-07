package;

import flixel.group.FlxSpriteGroup;
import NightmareVisionCharacterGroupOwner.NightmareVisionCharacterGroupScene;

/** The source Int-backed abstract is not a runtime Haxe enum. */
enum abstract NightmareVisionCharacterType(Int) to Int {
 var BF = 0;
 var DAD = 1;
 var GF = 2;
}

/** Actual source group storage, placement and field-owner transaction. */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionCharacterGroup extends FlxSpriteGroup {
 public var parent:Null<Character>;
 public var type:NightmareVisionCharacterType;
 public var gfCheck:Bool = false;
 public var map:Map<String, Character> = new Map();
 var owner:Null<NightmareVisionCharacterGroupOwner>;

 public function new(x:Float = 0, y:Float = 0, _type:NightmareVisionCharacterType,
  ?owner:NightmareVisionCharacterGroupOwner) {
  type = _type;
  gfCheck = (_type == DAD);
  super(x, y);
  this.owner = owner;
  NightmareVisionSpriteMethods.bind(this, owner == null ? null : owner.spriteOwner);
 }

 public function addChar(char:Character):Void {
  if (char == null) return;
  startPos(char);
  if (map == null) fail('addChar map');
  map.set(char.curCharacter, char);
  add(char);
 }

 public function addToList(newCharacter:String):Character {
  if (map == null) fail('addToList map');
  var existing = map.get(newCharacter);
  if (existing != null) return existing;
  if (owner == null || owner.construct == null) fail('addToList owner constructor');
  var newChar = owner.construct(newCharacter, type == BF);
  if (newChar == null) fail('addToList constructed character');
  newChar.alpha = 0.00001;
  addChar(newChar);
  return newChar;
 }

 public function change(name:String):Character {
  if (parent == null) fail('change parent');
  if (parent.curCharacter != name) {
   var checkFields:Array<Bool> = [];
   var scene = currentScene();
   if (scene != null && scene.playFields != null) {
    if (scene.playFields.members == null) fail('change snapshot members');
    for (field in scene.playFields.members) {
     if (field == null) fail('change snapshot field');
     checkFields.push(field.owner == parent);
    }
   }
   final old = parent;
   if (map == null) fail('change map');
   if (!map.exists(name)) addToList(name);
   if (parent == null) fail('change alpha parent');
   var lastAlpha = parent.alpha;
   parent.alpha = 0.0001;
   if (map == null) fail('change replacement map');
   parent = map.get(name);
   if (parent == null) fail('change replacement parent');
   parent.alpha = lastAlpha;
   scene = currentScene();
   if (scene == null) fail('change publication scene');
   if (scene.playFields == null) fail('change publication fields');
   if (scene.playFields.members == null) fail('change publication members');
   for (field in scene.playFields.members) {
    if (field == null) fail('change publication field');
    if (checkFields[field.ID]) field.owner = parent;
   }
  }
  return parent;
 }

 public function startPos(?char:Character):Void {
  if (char == null) return;
  if (gfCheck) {
   if (char.curCharacter == null) fail('startPos identity');
   if (StringTools.startsWith(char.curCharacter, 'gf')) {
    var scene = currentScene();
    if (scene != null && scene.gfPosition == null) fail('startPos gfPosition');
    char.setPosition(scene == null ? 0 : scene.gfPosition.x, scene == null ? 0 : scene.gfPosition.y);
    char.scrollFactor.set(0.95, 0.95);
    char.danceEveryNumBeats = 2;
   }
  }
  if (char.positionArray == null) fail('startPos positionArray');
  char.x += char.positionArray[0];
  char.y += char.positionArray[1];
 }

 function currentScene():Null<NightmareVisionCharacterGroupScene> {
  return owner == null || owner.scene == null ? null : owner.scene();
 }
 static function fail(phase:String):Dynamic {
  throw '[nightmare-vision-character-group] Missing ' + phase;
 }
 override public function destroy():Void {
  try {super.destroy();} catch (error:Dynamic) {owner = null;throw error;}
  owner = null;
 }
}
