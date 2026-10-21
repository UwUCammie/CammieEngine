package multiplayer;

import haxe.io.Bytes;

/** Incremental SHA-256 (FIPS 180-4), so large song files are hashed in fixed-size pieces
 * instead of being read into memory whole. haxe.crypto.Sha256 only hashes one buffer. */
class MpSha256 {
	static final K:Array<Int> = [
		0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
		0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
		0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
		0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
		0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
		0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
		0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
		0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
	];

	var h:Array<Int> = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
	var block:Bytes = Bytes.alloc(64);
	var filled:Int = 0;
	var lengthLow:Int = 0;
	var lengthHigh:Int = 0;
	var w:Array<Int> = [for (_ in 0...64) 0];

	public function new() {}

	public function update(data:Bytes, start:Int, length:Int):Void {
		var index = start;
		var end = start + length;
		// The message length in bits is kept in two 32-bit halves.
		var low = lengthLow + (length << 3);
		if (uless(low, lengthLow))
			lengthHigh++;
		lengthHigh += length >>> 29;
		lengthLow = low;
		while (index < end) {
			var take = 64 - filled;
			if (take > end - index)
				take = end - index;
			block.blit(filled, data, index, take);
			filled += take;
			index += take;
			if (filled == 64) {
				compress();
				filled = 0;
			}
		}
	}

	public function digestHex():String {
		var high = lengthHigh;
		var low = lengthLow;
		var pad = Bytes.alloc(filled < 56 ? 56 - filled : 120 - filled);
		pad.fill(0, pad.length, 0);
		pad.set(0, 0x80);
		var savedLow = lengthLow;
		var savedHigh = lengthHigh;
		update(pad, 0, pad.length);
		var tail = Bytes.alloc(8);
		tail.set(0, (high >>> 24) & 255);
		tail.set(1, (high >>> 16) & 255);
		tail.set(2, (high >>> 8) & 255);
		tail.set(3, high & 255);
		tail.set(4, (low >>> 24) & 255);
		tail.set(5, (low >>> 16) & 255);
		tail.set(6, (low >>> 8) & 255);
		tail.set(7, low & 255);
		update(tail, 0, 8);
		lengthLow = savedLow;
		lengthHigh = savedHigh;
		var out = new StringBuf();
		for (value in h)
			out.add(StringTools.hex(value, 8).toLowerCase());
		return out.toString();
	}

	static inline function uless(a:Int, b:Int):Bool
		return (a ^ 0x80000000) < (b ^ 0x80000000);

	static inline function rotr(x:Int, n:Int):Int
		return (x >>> n) | (x << (32 - n));

	function compress():Void {
		for (i in 0...16)
			w[i] = (block.get(i * 4) << 24) | (block.get(i * 4 + 1) << 16) | (block.get(i * 4 + 2) << 8) | block.get(i * 4 + 3);
		for (i in 16...64) {
			var s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
			var s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
			w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
		}
		var a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
		for (i in 0...64) {
			var s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
			var ch = (e & f) ^ (~e & g);
			var t1 = (hh + s1 + ch + K[i] + w[i]) | 0;
			var s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
			var maj = (a & b) ^ (a & c) ^ (b & c);
			var t2 = (s0 + maj) | 0;
			hh = g;
			g = f;
			f = e;
			e = (d + t1) | 0;
			d = c;
			c = b;
			b = a;
			a = (t1 + t2) | 0;
		}
		h[0] = (h[0] + a) | 0;
		h[1] = (h[1] + b) | 0;
		h[2] = (h[2] + c) | 0;
		h[3] = (h[3] + d) | 0;
		h[4] = (h[4] + e) | 0;
		h[5] = (h[5] + f) | 0;
		h[6] = (h[6] + g) | 0;
		h[7] = (h[7] + hh) | 0;
	}
}
