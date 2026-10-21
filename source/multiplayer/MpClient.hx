package multiplayer;

import haxe.Json;
import haxe.io.Bytes;
import multiplayer.MpSocket.MpSocketEvent;

/** One connection to the multiplayer service (MULTIPLAYER_PROTOCOL.md at the repository
 * root): ticket handshake, server clock, and every message in and out. A single instance
 * lives for the game session; screens listen through `listeners`. */
class MpClient {
	public static inline var PROTOCOL:Int = 1;
	public static inline var PATH:String = '/cammie-engine/mp';
	static inline var CLOCK_SAMPLES:Int = 8;

	public static var instance(default, null):MpClient;

	/** Connection state shown by the menus. */
	public var state(default, null):String = 'offline';
	public var lastError(default, null):String = '';
	public var accountId(default, null):String = '';
	public var name(default, null):String = '';
	public var lobby(default, null):Dynamic = null;

	/** Called on the main thread with each server message. */
	public var listeners:Array<Dynamic->Void> = [];
	/** Called with each binary frame (song content from a host). */
	public var binaryListeners:Array<Bytes->Void> = [];

	var socket:MpSocket;
	var ticket:{ticket:String, secret:String, name:String, accountId:String};
	var offsets:Array<{rtt:Float, offset:Float}> = [];
	var clockOffset:Float = 0;
	var clockAt:Float = 0;

	public static function get():MpClient {
		if (instance == null)
			instance = new MpClient();
		return instance;
	}

	function new() {}

	public function connect():Void {
		if (state == 'connecting' || state == 'online')
			return;
		state = 'connecting';
		lastError = '';
		MpAccount.ticket(function(granted) {
			ticket = granted;
			socket = new MpSocket();
			socket.connect(MpEndpoint.play(), PATH);
			MpTasks.every(update);
		}, function(error) fail(error));
	}

	public function disconnect():Void {
		if (socket != null)
			socket.close();
		socket = null;
		lobby = null;
		state = 'offline';
		MpTasks.stop(update);
	}

	function fail(error:String):Void {
		lastError = error;
		if (socket != null)
			socket.close();
		socket = null;
		lobby = null;
		state = 'offline';
		MpTasks.stop(update);
		emit({t: 'disconnected', reason: error});
	}

	public function send(message:Dynamic):Void {
		if (socket != null && state == 'online')
			socket.sendText(Json.stringify(message));
	}

	public function sendBinary(frame:Bytes):Void {
		if (socket != null && state == 'online')
			socket.sendBinary(frame);
	}

	/** Milliseconds on the server's clock, estimated from the best of the time samples. */
	public function serverNow():Float
		return haxe.Timer.stamp() * 1000 + clockOffset;

	function update():Void {
		if (socket == null)
			return;
		for (event in socket.poll()) {
			switch (event) {
				case Opened:
				case Text(value):
					var message:Dynamic = null;
					try message = Json.parse(value) catch (_:Dynamic) {}
					if (message != null)
						receive(message);
				case Binary(value):
					for (listener in binaryListeners.copy())
						listener(value);
				case Closed(reason):
					fail(lastError != '' ? lastError : reason);
					return;
			}
		}
		if (state == 'online' && haxe.Timer.stamp() - clockAt > 30) {
			clockAt = haxe.Timer.stamp();
			offsets = [];
			for (_ in 0...CLOCK_SAMPLES)
				send({t: 'time', client_ms: haxe.Timer.stamp() * 1000});
		}
	}

	function receive(message:Dynamic):Void {
		switch (Std.string(message.t)) {
			case 'challenge':
				if (message.protocol != PROTOCOL) {
					fail('protocol_mismatch');
					return;
				}
				var version = EngineBranding.version();
				socket.sendText(Json.stringify({t: 'hello', protocol: PROTOCOL, version: version, ticket: ticket.ticket,
					proof: MpProof.make(ticket.secret, ticket.ticket, Std.string(message.nonce), version)}));
				return;
			case 'welcome':
				state = 'online';
				accountId = message.account_id;
				name = message.name;
				clockAt = 0;
			case 'time':
				var now = haxe.Timer.stamp() * 1000;
				var sent:Float = message.client_ms;
				var rtt = now - sent;
				offsets.push({rtt: rtt, offset: message.server_ms - (sent + rtt / 2)});
				var best = offsets[0];
				for (sample in offsets)
					if (sample.rtt < best.rtt)
						best = sample;
				clockOffset = best.offset;
			case 'lobby_state':
				lobby = message;
			case 'error':
				lastError = Std.string(message.code);
				// The server says nothing more to a removed player.
				if (lastError == 'kicked') {
					lobby = null;
					MpSession.left();
				}
				if (state != 'online') {
					fail(lastError);
					return;
				}
			default:
		}
		emit(message);
	}

	function emit(message:Dynamic):Void {
		for (listener in listeners.copy())
			listener(message);
	}

	/** Leave the lobby; the server sends the leaver no further lobby_state. */
	public function leaveLobby():Void {
		send({t: 'lobby_leave'});
		lobby = null;
		MpSession.left();
	}

	/** The socket, for the song sender's worker thread; null when not connected. */
	public function transferSocket():Null<MpSocket>
		return state == 'online' ? socket : null;

	public function inLobby():Bool
		return lobby != null && state == 'online';

	public function isHost():Bool
		return inLobby() && lobby.host == accountId;
}
