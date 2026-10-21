package multiplayer;

import haxe.io.Bytes;

/**
	The parts of being in a lobby that must keep working whichever screen is open: answering
	the server's `want` as host, receiving the lobby song as a joiner, and following song
	changes. Screens only draw and send what the player chooses.
**/
class MpSession {
	static var installed:Bool = false;
	/** Package id of the song this player last reacted to. */
	static var songId:String = '';

	public static function install():Void {
		if (installed)
			return;
		installed = true;
		var client = MpClient.get();
		client.listeners.push(onMessage);
		client.binaryListeners.push(onBinary);
		MpTasks.every(tick);
	}

	static function onMessage(message:Dynamic):Void {
		var client = MpClient.get();
		switch (Std.string(message.t)) {
			case 'lobby_state':
				var song:Dynamic = message.song;
				var id = song == null ? '' : Std.string(Reflect.field(song, 'package').id);
				if (id == songId)
					return;
				songId = id;
				if (song == null) {
					MpTransfer.forget();
					return;
				}
				// The host already has its own song; everyone else checks what they lack.
				if (message.host != client.accountId)
					MpTransfer.receive(song);
				else
					MpTransfer.forget();
			case 'want':
				if (client.isHost())
					MpTransfer.answerWant(Std.string(message.package_id), message.sha256);
			case 'chunk_begin':
				if (MpTransfer.fetch != null)
					MpTransfer.fetch.onChunkBegin(Std.string(message.sha256), Std.int(message.size));
			case 'disconnected':
				songId = '';
				MpTransfer.forget();
				MpTransfer.stopSending();
			default:
		}
	}

	static function onBinary(frame:Bytes):Void {
		if (MpTransfer.fetch != null)
			MpTransfer.fetch.onBinary(frame);
	}

	static function tick():Void {
		if (MpTransfer.fetch != null)
			MpTransfer.fetch.update();
	}

	/** Leaving a lobby forgets its song on both sides. */
	public static function left():Void {
		songId = '';
		MpTransfer.forget();
		MpTransfer.stopSending();
	}
}
