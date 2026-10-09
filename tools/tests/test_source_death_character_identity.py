"""Execute the source-owned death-identity and fallback section of Character.new."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE, HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source" / "Character.hx"
PSYCH_DONOR = ROOT.parent / "fnf_sources" / "FNF-PsychEngine" / "source" / "objects" / "Character.hx"
NV_DONOR = ROOT.parent / "fnf_sources" / "NightmareVision" / "source" / "funkin" / "objects" / "Character.hx"


def extract_section(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def character_flag_helpers() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    return "\n".join((
        extract_method(source, "\tfunction loadNightmareVisionCharacterFlags("),
        extract_method(source, "\tstatic function nightmareVisionNumber("),
    ))


def constructor_resolution_code() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    identity = extract_section(
        source,
        "\t\tvar sourceDeathFallbackId:Null<String> = null;",
        "\t\tvar psychCameraRoot =",
    )
    visual_resolution_start = source.index(
        "\t\tvar visualResolution:Dynamic = sourceDeathVisualResolution == null"
    )
    visual_resolution_end = source.index(";", visual_resolution_start) + 1
    return identity + "\n" + source[visual_resolution_start:visual_resolution_end]


def run_fixture(fixture: str) -> subprocess.CompletedProcess[str]:
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="source-death-character-", dir=ROOT / "tmp") as scratch:
        folder = Path(scratch)
        (folder / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(folder), "--main", "Main", "--interp"],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": scratch},
            capture_output=True,
            text=True,
            timeout=60,
        )


FIXTURE = r'''using StringTools;

class ImportEngine {
 public static inline var PSYCH:String='Psych Engine';
 public static inline var NIGHTMARE_VISION:String='Nightmare Vision';
 public static inline var CODENAME:String='Codename Engine';
}

class FlxG { public static var state:Dynamic; }

class PlayState {
 public static var instance:PlayState;
 public static var SONG:Dynamic={song:'fixture'};
 public function new() {}
}

class Song {
 public static var manifestCalls:Array<String>=[];
 public static var currentSongCalls:Array<String>=[];
 public static var codenameRoot:String='';
 public static var manifestResponses:Map<String,Dynamic>=new Map();
 public static var currentSongResolution:Dynamic={complete:false,selectedRegistryName:null};
 public static function reset():Void {
  manifestCalls=[]; currentSongCalls=[]; manifestResponses=new Map();
  currentSongResolution={complete:false,selectedRegistryName:null};
 }
 public static function storageFolder(song:Dynamic):String return 'fixture';
 public static function characterRootForSong(folder:String,?engine:String):String {
  return engine==ImportEngine.CODENAME ? codenameRoot : '';
 }
 public static function characterVisualRegistryEntryInManifest(id:String,root:String):Dynamic return null;
 public static function resolveCharacterVisualInManifest(id:String,root:String,
  requireComplete:Bool,engine:String):Dynamic {
  manifestCalls.push(id);
  return manifestResponses.exists(id) ? manifestResponses.get(id)
   : {complete:false,selectedRegistryName:null,implementationName:null,assetRootPath:null};
 }
 public static function resolveCharacterVisualForCurrentSong(id:String):Dynamic {
  currentSongCalls.push(id); return currentSongResolution;
 }
}

class NightmareVisionCharacterData {
 public static var calls:Array<String>=[];
 public static var definitions:Map<String,Dynamic>=new Map();
 public static function reset():Void { calls=[]; definitions=new Map(); }
 public static function load(root:String,id:String):Dynamic {
  calls.push(root+':'+id); return definitions.get(id);
 }
}

class Character {
 public var sourceStunnedState=false;public var nightmareVisionLegacyActor=false;
 public var curCharacter:String='';
 public var requestedCharacter:String='';
 public var isPlayer:Bool=false;
 public var isDie:Bool=false;
 public var flipX:Bool=false;
 public var nightmareVisionHealthIcon:Null<String>=null;
 public var sourceHealthIconAssigned:Bool=false;
 public var sourceHealthIconValue:String;
 public var gameoverCharacter:Null<String>=null;
 public var gameoverConfirmDeathSound:Null<String>=null;
 public var gameoverLoopDeathSound:Null<String>=null;
 public var gameoverInitialDeathSound:Null<String>=null;
 public var lastVisualCharacterId:String='';
 public var lastSourceVisualResolution:Dynamic;
 public var lastVisualResolution:Dynamic;
 public var lastNVVisualId:String='';
 public var vSliceSustains:Bool=false;
 public var singDuration:Float=1;
 public var holdTime:Float=1;
 public function new() {}
 public static function isNoGirlfriend(id:String):Bool return false;
 public static function nightmareVisionHealthIconFromDefinition(definition:Dynamic):Null<String>
  return Reflect.field(definition,'healthicon');
 public function nightmareVisionNullableString(definition:Dynamic,field:String):Null<String> {
  var value:Dynamic=Reflect.field(definition,field);
  return value==null?null:Std.string(value);
 }
''' + character_flag_helpers() + r'''
 public function markDeathConstructionStage(stage:String):Void {}
 public function resolveDeathIdentity(requested:String,ownerRoot:String,ownerEngine:String,
  ?codename:Dynamic):Void {
  curCharacter=requested; this.isPlayer=false;
  requestedCharacter=requested==null?'':requested.trim();
  var sourceConstruction:Dynamic=null;
  var sourceCharacterOwnerRoot=ownerRoot;
  var sourceCharacterOwnerEngine=ownerEngine;
  var codenameRuntime:Dynamic=codename;
''' + constructor_resolution_code() + r'''
  lastVisualCharacterId=visualCharacterId;
  lastSourceVisualResolution=sourceDeathVisualResolution;
  lastVisualResolution=visualResolution;
  lastNVVisualId=nightmareVisionOwnerRoot==''?'':visualCharacterId;
 }
}

class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function complete(id:String):Dynamic
  return {complete:true,selectedRegistryName:id,implementationName:id,
   assetRootPath:'owner/'+id,diagnosticCode:'',diagnostic:''};
 static function incomplete():Dynamic
  return {complete:false,selectedRegistryName:null,implementationName:null,
   assetRootPath:null,diagnosticCode:'missing',diagnostic:'missing'};
 static function main():Void {
  var owner=new PlayState(); PlayState.instance=owner; FlxG.state=owner;

  // Complete exact source-owned death definitions win before donor fallback.
  Song.reset(); NightmareVisionCharacterData.reset();
  Song.manifestResponses.set('psych-dead',complete('psych-dead'));
  Song.manifestResponses.set('bf',complete('bf'));
  var psychExact=new Character();
  psychExact.resolveDeathIdentity('psych-dead','psych-owner',ImportEngine.PSYCH);
  check(psychExact.curCharacter=='psych-dead' && psychExact.requestedCharacter=='psych-dead',
   'Psych source death identity must stay authored');
  check(psychExact.sourceStunnedState,'Psych source stun profile missing');
  check(psychExact.lastVisualCharacterId=='psych-dead' && Song.manifestCalls.join(',')=='psych-dead',
   'complete exact Psych death visual must win without consulting bf');

  Song.reset(); NightmareVisionCharacterData.reset();
  Song.manifestResponses.set('nv-dead',complete('nv-dead'));
  Song.manifestResponses.set('bf',complete('bf'));
  NightmareVisionCharacterData.definitions.set('nv-dead',
   {healthicon:'nv-icon',gameover_character:'nv-respawn',gameover_confirm_sound:'nv-confirm',
    gameover_loop_sound:'nv-loop',gameover_intial_sound:'nv-initial'});
  var nvExact=new Character();
  nvExact.sourceHealthIconAssigned=true;
  nvExact.sourceHealthIconValue='previous-script-icon';
  nvExact.resolveDeathIdentity('nv-dead','nv-owner',ImportEngine.NIGHTMARE_VISION);
  check(nvExact.sourceStunnedState,'NV source stun profile missing');
  check(!nvExact.sourceHealthIconAssigned,
   'new source death definition must clear a previous scripted icon override');
  check(nvExact.curCharacter=='nv-dead' && nvExact.lastVisualCharacterId=='nv-dead',
   'NV exact death identity and selected visual id must remain authored');
  check(Song.manifestCalls.join(',')=='nv-dead' && NightmareVisionCharacterData.calls.join(',')=='nv-owner:nv-dead',
   'NV metadata must be loaded from the exact selected owner visual');
  check(nvExact.nightmareVisionHealthIcon=='nv-icon' && nvExact.gameoverCharacter=='nv-respawn'
   && nvExact.gameoverConfirmDeathSound=='nv-confirm' && nvExact.gameoverLoopDeathSound=='nv-loop'
   && nvExact.gameoverInitialDeathSound=='nv-initial',
   'NV source metadata fields were not retained on the actor');

  // Missing source death variants use the donor DEFAULT_CHARACTER, never the
  // suffix-stripped custom name, while curCharacter continues to identify the request.
  Song.reset(); NightmareVisionCharacterData.reset();
  Song.manifestResponses.set('authored-dead',incomplete());
  Song.manifestResponses.set('bf',complete('bf'));
  NightmareVisionCharacterData.definitions.set('bf',
   {healthicon:'bf-icon',gameover_character:'bf-gameover'});
  var nvFallback=new Character();
  nvFallback.resolveDeathIdentity('authored-dead','nv-owner',ImportEngine.NIGHTMARE_VISION);
  check(nvFallback.curCharacter=='authored-dead' && nvFallback.requestedCharacter=='authored-dead',
   'NV fallback must not replace authored curCharacter/requestedCharacter');
  check(nvFallback.lastVisualCharacterId=='bf' && nvFallback.lastVisualResolution.selectedRegistryName=='bf'
   && Song.manifestCalls.join(',')=='authored-dead,bf',
   'incomplete NV death visual must retry the donor bf visual in order');
  check(NightmareVisionCharacterData.calls.join(',')=='nv-owner:bf'
   && nvFallback.lastNVVisualId=='bf' && nvFallback.nightmareVisionHealthIcon=='bf-icon'
   && nvFallback.gameoverCharacter=='bf-gameover',
   'NV metadata lookup must follow the selected fallback visual id');

  Song.reset(); NightmareVisionCharacterData.reset();
  Song.manifestResponses.set('authored-dead',incomplete());
  Song.manifestResponses.set('bf',complete('bf'));
  var psychFallback=new Character();
  psychFallback.resolveDeathIdentity('authored-dead','psych-owner',ImportEngine.PSYCH);
  check(psychFallback.curCharacter=='authored-dead' && psychFallback.lastVisualCharacterId=='bf'
   && Song.manifestCalls.join(',')=='authored-dead,bf',
   'Psych missing death variant must select DEFAULT_CHARACTER while preserving authored identity');

  for (testCase in [
   {label:'native',root:'',engine:'',requested:'native-dead',expected:'native'},
   {label:'HXC',root:'hxc-owner',engine:'HXC',requested:'hxc-dead',expected:'hxc'},
   {label:'Codename',root:'codename-owner',engine:ImportEngine.CODENAME,
    requested:'xml-dead',expected:'xml'}
  ]) {
   Song.reset(); NightmareVisionCharacterData.reset();
   Song.codenameRoot=testCase.label=='Codename'?'codename-owner':'';
   Song.currentSongResolution=complete(testCase.expected);
   var legacy=new Character();
   legacy.resolveDeathIdentity(testCase.requested,testCase.root,testCase.engine);
   check(!legacy.sourceStunnedState,"native/unrelated actor acquired Psych/NV stun profile");
   check(legacy.curCharacter==testCase.expected && legacy.lastVisualCharacterId==testCase.expected,
    testCase.label+' legacy -dead id must keep the established suffix-stripping behavior');
   check(Song.manifestCalls.length==0 && Song.currentSongCalls.join(',')==testCase.expected,
    testCase.label+' legacy visual must not enter the Psych/NV death fallback resolver');
  }
 }
}
'''


class SourceDeathCharacterIdentityTest(unittest.TestCase):
    def test_fallback_id_matches_both_pinned_donor_defaults(self):
        psych = PSYCH_DONOR.read_text(encoding="utf-8")
        nightmare_vision = NV_DONOR.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_CHARACTER:String = 'bf'", psych)
        self.assertIn("DEFAULT_CHARACTER:String = 'bf'", nightmare_vision)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_extracted_constructor_identity_and_owner_visual_fallback(self):
        result = run_fixture(FIXTURE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
