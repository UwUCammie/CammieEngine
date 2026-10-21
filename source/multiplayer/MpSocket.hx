package multiplayer;

import haxe.io.Bytes;
#if sys
import sys.thread.Deque;
import sys.thread.Lock;
import sys.thread.Mutex;
import sys.thread.Thread;
#end

enum MpSocketEvent {
	Opened;
	Text(value:String);
	Binary(value:Bytes);
	Closed(reason:String);
}

/** A WebSocket whose blocking work runs on two threads: one receives, one sends.
 * The main thread only queues sends and drains received events with poll(). */
class MpSocket {
	var id:Int = 0;
	var closing:Bool = false;
	#if sys
	var events:Deque<MpSocketEvent> = new Deque();
	var outgoing:Deque<Null<{data:Bytes, binary:Bool}>> = new Deque();
	var writerDone:Lock = new Lock();
	var queueLock:Mutex = new Mutex();
	#end
	var queued:Float = 0;

	public function new() {}

	public function connect(endpoint:MpEndpoint, path:String):Void {
		#if sys
		Thread.create(function() {
			var handle = MpNative.open(endpoint, path);
			if (handle <= 0) {
				events.add(Closed('connect_failed:' + handle));
				return;
			}
			id = handle;
			events.add(Opened);
			Thread.create(writeLoop);
			while (true) {
				var message = MpNative.receive(handle);
				if (message.kind == 0)
					events.add(Text(message.data.toString()));
				else if (message.kind == 1)
					events.add(Binary(message.data));
				else {
					events.add(Closed(message.kind == 2 ? 'closed' : 'error:' + message.error));
					break;
				}
			}
			outgoing.add(null);
			writerDone.wait();
			MpNative.release(handle);
		});
		#else
		throw 'Multiplayer needs a native build.';
		#end
	}

	#if sys
	function writeLoop():Void {
		while (true) {
			var item = outgoing.pop(true);
			if (item == null)
				break;
			var failed = MpNative.send(id, item.data, item.binary) != 0;
			count(-item.data.length);
			if (failed) {
				// The receive loop ends once the connection is shut down.
				MpNative.shutdown(id);
				while (outgoing.pop(true) != null) {}
				break;
			}
		}
		writerDone.release();
	}
	#end

	public function sendText(value:String):Void {
		#if sys
		if (!closing) {
			var data = Bytes.ofString(value);
			count(data.length);
			outgoing.add({data: data, binary: false});
		}
		#end
	}

	public function sendBinary(value:Bytes):Void {
		#if sys
		if (!closing) {
			count(value.length);
			outgoing.add({data: value, binary: true});
		}
		#end
	}

	/** Bytes queued to send and not yet handed to the connection; any thread may ask. */
	public function queuedBytes():Float {
		#if sys
		queueLock.acquire();
		var value = queued;
		queueLock.release();
		return value;
		#else
		return 0;
		#end
	}

	function count(change:Float):Void {
		#if sys
		queueLock.acquire();
		queued += change;
		queueLock.release();
		#end
	}

	public function isClosing():Bool
		return closing;

	/** Every event received since the last call, oldest first. */
	public function poll():Array<MpSocketEvent> {
		var list:Array<MpSocketEvent> = [];
		#if sys
		while (true) {
			var event = events.pop(false);
			if (event == null)
				break;
			list.push(event);
		}
		#end
		return list;
	}

	public function close():Void {
		if (closing)
			return;
		closing = true;
		#if sys
		var handle = id;
		if (handle > 0)
			Thread.create(function() MpNative.shutdown(handle));
		#end
	}
}
