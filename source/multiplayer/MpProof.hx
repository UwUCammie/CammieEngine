package multiplayer;

import haxe.crypto.Hmac;
import haxe.io.Bytes;

/** The hello proof: HMAC-SHA256 over the ticket, the server's nonce and the game version,
 * keyed by the ticket secret, so the secret itself never crosses the socket. */
class MpProof {
	public static function make(secret:String, ticket:String, nonce:String, version:String):String {
		var message = 'CE-MP-AUTH\n' + ticket + '\n' + nonce + '\n' + version;
		return new Hmac(SHA256).make(Bytes.ofString(secret), Bytes.ofString(message)).toHex();
	}
}
