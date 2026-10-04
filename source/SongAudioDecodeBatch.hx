package;

import lime.media.AudioBuffer;
#if (cpp && target.threaded)
import sys.thread.Lock;
import sys.thread.Thread;
#end

/** Decode exactly two independent native song-audio files with one worker. */
class SongAudioDecodeBatch {
	/**
		Keep this limited to raw file decoding. The caller resolves paths and wraps
		buffers into OpenFL/Flixel sound objects on the main thread.
		Returns null as an all-or-nothing failure signal so callers can use their
		existing asset loader for both files.
	**/
	public static function decodePair(firstPath:String, secondPath:String):Array<AudioBuffer> {
		if (firstPath == null || secondPath == null)
			return null;

		#if (cpp && target.threaded && lime_cffi)
		var finished = new Lock();
		var second:AudioBuffer = null;
		var secondFailed = false;
		try {
			Thread.create(function():Void {
				try {
					second = AudioBuffer.fromFile(secondPath);
				} catch (_:Dynamic) {
					secondFailed = true;
				}
				finished.release();
			});
		} catch (_:Dynamic) {
			return null;
		}

		var first:AudioBuffer = null;
		var firstFailed = false;
		try {
			first = AudioBuffer.fromFile(firstPath);
		} catch (_:Dynamic) {
			firstFailed = true;
		}
		// Always wait for the worker before returning so a failed main-thread
		// decode cannot leave a background decoder using chart-local paths.
		finished.wait();
		if (firstFailed || secondFailed || first == null || second == null)
			return null;
		return [first, second];
		#else
		try {
			var first = AudioBuffer.fromFile(firstPath);
			var second = AudioBuffer.fromFile(secondPath);
			if (first == null || second == null)
				return null;
			return [first, second];
		} catch (_:Dynamic) {
			return null;
		}
		#end
	}
}
