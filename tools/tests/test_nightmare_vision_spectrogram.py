from nv_sprite_dependency_support import add_native_sprite_dependencies
"""Exercise the NMV waveform/PlayableSong adapters without starting the game."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
LIME = ROOT / ".haxelib/lime/8,3,2/src"


class NightmareVisionSpectrogramTest(unittest.TestCase):
    def test_live_pcm_geometry_and_nonowning_playablesong_view(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        if not LIME.is_dir():
            self.skipTest("pinned Lime source is unavailable")

        fixture = r'''
import haxe.io.Bytes;
import lime.utils.Int16Array;
import lime.utils.UInt8Array;
import NightmareVisionSpectogramEnums.SPECDIRECTION;
import NightmareVisionSpectogramEnums.VISTYPE;
import NightmareVisionSpectogramAudioData;
import NightmareVisionPolygonSpectogram;
import NightmareVisionPlayableSongView;
import flixel.sound.FlxSound;

class FakeAudioBuffer {
 public var bitsPerSample:Int;
 public var channels:Int;
 public var sampleRate:Int;
 public var data:UInt8Array;
 public function new(bits:Int, channels:Int, rate:Int, bytes:Bytes, byteOffset:Int=0) {
  bitsPerSample=bits; this.channels=channels; sampleRate=rate;
  var view=UInt8Array.fromBytes(bytes);
  data=byteOffset == 0 ? view : view.subarray(byteOffset, bytes.length);
 }
}
class FakeAudioSource { public var buffer:Dynamic; public function new(buffer:Dynamic) this.buffer=buffer; }
class FakeChannel { public var __audioSource:FakeAudioSource; public function new(buffer:Dynamic) __audioSource=new FakeAudioSource(buffer); }
class SpectrumTestMain {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function expectError(fn:Void->Void, fragment:String):Void {
  var caught:Dynamic = null;
  try fn() catch (error:Dynamic) caught=error;
  check(caught != null && Std.string(caught).indexOf(fragment) >= 0,
   'Expected error containing ' + fragment + ', got ' + Std.string(caught));
 }
 static function pcm(values:Array<Int>):Bytes {
  var bytes=Bytes.alloc(values.length * 2);
  for (i in 0...values.length) {
   var value=values[i];
   bytes.set(i*2, value & 255);
   bytes.set(i*2+1, (value >> 8) & 255);
  }
  return bytes;
 }
 static function sound(length:Float, bytes:Bytes, bits:Int=16, channels:Int=2, rate:Int=4,
  byteOffset:Int=0):FlxSound {
  var result=new FlxSound(length);
  result._channel=new FakeChannel(new FakeAudioBuffer(bits, channels, rate, bytes, byteOffset));
  return result;
 }
 static function near(a:Float, b:Float):Bool return Math.abs(a-b) < 0.0001;
 static function main():Void {
  var data=pcm([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]);
  var offsetBytes=Bytes.alloc(data.length+2);
  offsetBytes.blit(2, data, 0, data.length);
  var input=sound(1000, offsetBytes, 16, 2, 4, 2);
  var pcmView=new NightmareVisionSpectogramAudioData(input);
  pcmView.checkAndSetBuffer();
  check(!pcmView.setBuffer && pcmView.audioData == null,
   'PCM view attached before its native FlxSound started');
  input.playing=true;
  pcmView.checkAndSetBuffer();
  check(pcmView.setBuffer && pcmView.sampleRate == 4 && pcmView.numSamples == 8
   && pcmView.audioData.length == 8,
   'live 16-bit stereo buffer was not exposed as an aligned sample view');
  var first=NightmareVisionSpectogramAudioData.getCurAud(pcmView.audioData, 0);
	check(near(first.left, 1000/32767), 'left channel or 32767 normalization changed');
	check(near(first.right, 3000/32767), 'source stereo stride changed');
	check(near(first.balanced, 2000/32767), 'source stereo averaging changed');
	check(near(NightmareVisionSpectogramAudioData.getBalanced(pcmView.audioData, 0), first.balanced),
	   'allocation-free waveform sample diverged from source stereo averaging');
  var last=NightmareVisionSpectogramAudioData.getCurAud(pcmView.audioData, 999);
  check(near(last.right, 8000/32767), 'final stereo sample pair was not bounded to the view');
	check(near(NightmareVisionSpectogramAudioData.getBalanced(pcmView.audioData, 999), last.balanced),
	   'allocation-free waveform sample did not clamp the final stereo pair');

  var badBits=sound(1000, data, 8, 2, 4); badBits.playing=true;
  expectError(function() new NightmareVisionSpectogramAudioData(badBits).checkAndSetBuffer(), '16-bit stereo');
  var badChannels=sound(1000, data, 16, 1, 4); badChannels.playing=true;
  expectError(function() new NightmareVisionSpectogramAudioData(badChannels).checkAndSetBuffer(), '16-bit stereo');
  var badRate=sound(1000, data, 16, 2, 0); badRate.playing=true;
  expectError(function() new NightmareVisionSpectogramAudioData(badRate).checkAndSetBuffer(), 'sample rate');

  var wave=new NightmareVisionPolygonSpectogram(input, 0xFF00FF00, 4, 1, SPECDIRECTION.HORIZONTAL);
  wave.waveAmplitude=100;
  wave.thickness=2;
  wave.generateSection(0, 1);
  check(wave.vertex_count == 16 && wave.index_count == 24,
	   'waveform did not emit the expected four quad segments');
	check(near(wave.vertices[0], 2) && near(wave.vertices[1], 0),
	   'source build_quad first vertex ordering changed');
	check(near(wave.vertices[2], 0) && near(wave.vertices[3], 0),
	   'source build_quad second vertex ordering changed');
	check(near(wave.vertices[4], 0) && near(wave.vertices[5], 2000/32767*100),
	   'horizontal source waveform coordinate changed');
  wave.visType=STATIC;
  var saved=wave.vertices[5];
  input.time=200;
  wave.update(1/60);
  check(wave.vertices[5] == saved, 'STATIC mode regenerated the waveform during update');
  wave.visType=FREQUENCIES;
  wave.update(1/60);
  check(wave.vertices[5] == saved, 'PolygonSpectogram invented frequency rendering absent from source');
	wave.visType=UPDATED;
	wave.realtimeVisLenght=1;
	wave.update(1/60);
  check(wave.vertex_count == 16, 'UPDATED mode failed to regenerate its waveform');

  var instrument=new FlxSound(1000); instrument.volume=0.6;
  var defaultActive:FlxSound=null;
  var player=new FlxSound(1000); player.volume=1;
  var opponent=new FlxSound(900); opponent.volume=0.65;
  var tracks=new VocalTracks(player);
  tracks.add(opponent, 'opponent');
  tracks.setRole(player, 'player');
  var defaultAudio=new NightmareVisionPlayableSongView(function() return defaultActive,
   function() return 1000, function() return tracks);
  defaultActive=instrument;
  defaultAudio.attachCurrentInstrumental(instrument);
  check(near(instrument.volume, 0.6), 'attaching the instrumental overwrote normalized volume without a source volume write');
  defaultAudio.release();

  var authoredInstrument=new FlxSound(1000); authoredInstrument.volume=0.6;
  var active:FlxSound=null;
  var audio=new NightmareVisionPlayableSongView(function() return active,
   function() return 1000, function() return tracks);
  audio.volume=0.4;
  check(audio.inst != null && !audio.inst.playing && audio.songLength == 1000
   && audio.members.length == 3 && audio.members[0] == audio.inst,
   'lazy instrumental slot or source PlayableSong member ordering changed');
  active=authoredInstrument;
  audio.attachCurrentInstrumental(authoredInstrument);
  check(near(authoredInstrument.volume, 0.4), 'cached source group volume write was not applied to the live track');
  check(audio.playerVocals.members.length == 1 && audio.playerVocals.members[0] == player
   && audio.opponentVocals.members.length == 1 && audio.opponentVocals.members[0] == opponent,
   'role-specific vocal group members were not preserved');
  audio.setTrackVolumeState(true);
  check(player.volume == 0 && near(opponent.volume, 0.4),
   'source hit/miss volume behavior changed the opponent vocal bus');
  audio.setTrackVolumeState(false);
  check(player.volume == 1 && near(opponent.volume, 0.4),
   'source player vocal bus was not restored independently');
  audio.play();
  check(authoredInstrument.playing && player.playing && opponent.playing
   && authoredInstrument.lastEndTime == 1000 && player.lastEndTime == 1000,
   'PlayableSong group play/end-time behavior diverged from the source');
  audio.pause();
  check(!authoredInstrument.playing && !player.playing && !opponent.playing,
   'PlayableSong pause did not reach all member sounds');
  var retainedGroup=audio.playerVocals;
  audio.release();
  check(!instrument.destroyed && !authoredInstrument.destroyed && !player.destroyed && !opponent.destroyed,
   'non-owning source view destroyed a PlayState-owned sound');
  expectError(function() retainedGroup.members, 'released');

  wave.destroy();
  check(wave.vis == null && wave.audioData == null && !input.destroyed,
   'visualizer teardown retained PCM or destroyed the source sound');
  pcmView.release();
  check(pcmView.snd == null && pcmView.audioData == null && !input.destroyed,
   'PCM view release retained or destroyed its source sound');
 }
}'''

        stubs = {
            "flixel/FlxG.hx": "package flixel; class FlxG { public static var height:Int=720; }\n",
            "flixel/util/FlxColor.hx": "package flixel.util; abstract FlxColor(Int) from Int to Int { public static inline var WHITE:FlxColor=cast 0xFFFFFFFF; }\n",
            "flixel/math/FlxPoint.hx": "package flixel.math; class FlxPoint { public var x:Float=0; public var y:Float=0; public function new(?x:Float=0, ?y:Float=0) { this.x=x; this.y=y; } }\n",
            "flixel/math/FlxMath.hx": "package flixel.math; class FlxMath { public static function remapToRange(v:Float,a:Float,b:Float,c:Float,d:Float):Float return c + (v-a)/(b-a)*(d-c); public static function lerp(a:Float,b:Float,t:Float):Float return a+(b-a)*t; }\n",
            "flixel/FlxStrip.hx": r'''package flixel;
import flixel.util.FlxColor;
import flixel.FlxDrawData;
class FlxStrip {
 public var vertices:FlxDrawData<Float>=new FlxDrawData<Float>();
 public var indices:FlxDrawData<Int>=new FlxDrawData<Int>();
 public var uvtData:FlxDrawData<Float>=new FlxDrawData<Float>();
 public var colors:FlxDrawData<Int>=new FlxDrawData<Int>();
 public var x:Float; public var y:Float; public var destroyed:Bool=false;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function makeGraphic(width:Int,height:Int,color:FlxColor):FlxStrip return this;
 public function update(elapsed:Float):Void {}
 public function destroy():Void destroyed=true;
}''',
            "flixel/FlxDrawData.hx": r'''package flixel;
abstract FlxDrawData<T>(Array<T>) {
 public inline function new() this=[];
 public var length(get,set):Int;
 inline function get_length():Int return this.length;
 inline function set_length(value:Int):Int { this.resize(value); return value; }
 @:arrayAccess public inline function __get(index:Int):T return this[index];
 @:arrayAccess public inline function __set(index:Int,value:T):T {
  if (index >= this.length) this.resize(index+1);
  this[index]=value; return value;
 }
}''',
            "flixel/sound/FlxSound.hx": r'''package flixel.sound;
class FlxSound {
 public var volume:Float=1; public var time:Float=0; public var length:Float;
 public var playing:Bool=false; public var pitch:Float=1; public var destroyed:Bool=false;
 public var _channel:Dynamic; public var lastEndTime:Float=-1;
 public function new(length:Float=0) this.length=length;
 public function play(forceRestart:Bool=false,startTime:Float=0,?endTime:Null<Float>):Void {
  time=startTime; playing=true; lastEndTime=endTime==null ? -1 : endTime;
 }
 public function pause():Void playing=false;
 public function resume():Void playing=true;
 public function stop():Void { playing=false; time=0; }
 public function getActualVolume():Float return volume;
 public function destroy():Void destroyed=true;
}''',
        }

        add_native_sprite_dependencies(stubs)
        # Real FlxStrip is a FlxSprite subtype; retain this fixture's mesh operations.
        stubs['flixel/FlxStrip.hx'] = stubs['flixel/FlxStrip.hx'].replace('class FlxStrip {', 'class FlxStrip extends FlxSprite {').replace(' public var x:Float; public var y:Float; public var destroyed:Bool=false;', '').replace('this.x=x; this.y=y;', 'super(x,y);').replace('public function makeGraphic(width:Int,height:Int,color:FlxColor):FlxStrip', 'override public function makeGraphic(width:Int,height:Int,color:Int=-1,unique:Bool=false,?key:String):FlxSprite').replace('public function update(elapsed:Float)', 'override public function update(elapsed:Float)').replace('public function destroy():Void', 'override public function destroy():Void')
        stubs['flixel/FlxSprite.hx'] = stubs['flixel/FlxSprite.hx'].replace('class FlxSprite {', 'class FlxSprite {public function update(e:Float):Void{}')
        with tempfile.TemporaryDirectory(prefix="nmv-spectrum-", dir=ROOT / "tmp") as scratch:
            scratch = Path(scratch)
            for relative, content in stubs.items():
                path = scratch / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            (scratch / "SpectrumTestMain.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-cp", str(ROOT / "source"), "-cp", str(LIME),
                 "--run", "SpectrumTestMain"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_imports_and_playstate_audio_lifetime_are_wired(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        interp = (ROOT / "source/NightmareVisionScriptInterp.hx").read_text()
        self.assertIn("funkin.audio.visualize.PolygonSpectogram', NightmareVisionPolygonSpectogram", play_state)
        self.assertIn("funkin.audio.visualize.PolygonSpectogram.VISTYPE', NightmareVisionSpectogramEnums.VISTYPE", play_state)
        self.assertIn("funkin.audio.visualize.SpectogramSprite.SPECDIRECTION', NightmareVisionSpectogramEnums.SPECDIRECTION", play_state)
        self.assertIn("funkin.objects.MeshRender', NightmareVisionMeshRender", play_state)
        self.assertIn("interp.variables.set('vocals', audioView)", play_state)
        self.assertIn("interp.variables.set('audio', audioView)", play_state)
        self.assertIn("field == 'audio' || field == 'vocals'", interp)
        self.assertIn("nightmareVisionAudioApi.attachCurrentInstrumental(FlxG.sound.music)", play_state)
        self.assertIn("nightmareVisionAudioApi.release()", play_state)
        self.assertNotIn("new FlxSound()", (ROOT / "source/NightmareVisionPlayableSongView.hx").read_text())


if __name__ == "__main__":
    unittest.main()
