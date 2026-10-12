package;

import haxe.io.Path;
import openfl.media.Sound;
#if lime_vorbis
import lime.media.AudioBuffer;
import lime.media.vorbis.VorbisFile;
#end

/** Streaming decode for an already scoped local path. Every call gets its own
 * playback cursor; callers retain their normal loader when streaming is absent. */
class NativeVorbisSound {
	public static function load(path:String):Null<Sound> {
		if (path == null || Path.extension(path).toLowerCase() != 'ogg') return null;
		#if lime_vorbis
		#if sys
		if (!sys.FileSystem.exists(path) || sys.FileSystem.isDirectory(path)) return null;
		#end
		var vorbis:VorbisFile = null;
		try {
			vorbis = VorbisFile.fromFile(path);
			if (vorbis == null) return null;
			var buffer = AudioBuffer.fromVorbisFile(vorbis);
			if (buffer != null) {
				var sound = Sound.fromAudioBuffer(buffer);
				if (sound != null) return sound;
			}
		} catch (_:Dynamic) {}
		if (vorbis != null) vorbis.clear();
		#end
		return null;
	}
}
