package multiplayer;

/** What the player is told for each server error code (MULTIPLAYER_PROTOCOL.md section 2). */
class MpText {
	public static function error(code:String):String {
		return switch (code) {
			case 'protocol_mismatch' | 'version_mismatch': 'This version of the game cannot play online. Update to the latest release.';
			case 'signin_required' | 'signin_expired' | 'signin_invalid': 'Sign in again to play online.';
			case 'session_revoked': 'This game was signed out from the website. Sign in again.';
			case 'rate_limited': 'Too many requests. Wait a moment and try again.';
			case 'lobby_full': 'That lobby is full.';
			case 'lobby_not_found': 'No lobby has that code.';
			case 'lobby_password': 'Wrong password.';
			case 'lobby_busy': 'That lobby is playing a song. Try again after it.';
			case 'not_host': 'Only the host can do that.';
			case 'not_ready': 'Not everyone is ready.';
			case 'modifier_not_allowed': 'One of your modifiers is not allowed in this lobby.';
			case 'package_too_large': 'That song is too large to share (over 250 MB).';
			case 'content_unavailable': 'You do not have the whole song yet.';
			case 'server_busy': 'The server is busy. Try again soon.';
			case 'kicked': 'The host removed you from the lobby.';
			case 'closed' | 'disconnected': 'Disconnected from the server.';
			case 'bad_request': 'The server refused that.';
			default:
				StringTools.startsWith(code, 'connect_failed') || StringTools.startsWith(code, 'error:')
					? 'Could not reach play.uwucammie.com.' : code;
		};
	}
}
