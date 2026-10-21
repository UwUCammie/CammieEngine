package multiplayer;

import multiplayer.MpTransfer.MpFetch;

/**
	One lobby song from countdown to results, as PlayState and the lobby screen see it.

	Starting a match fixes what the play may use: the player's ready modifiers only, the
	Classic judge, the match seed, and, when the song came from another player, the
	multiplayer cache mounted over the library with scripts sandboxed. All of it is put
	back when the song is left. While the song plays, PlayState feeds the play streams and
	the live scores come back here.
**/
class MpMatch implements MpHooks.MpActivePlay {
	public static var current(default, null):Null<MpMatch> = null;

	public var startServerMs(default, null):Float;
	public var seed(default, null):Int;
	public var title(default, null):String;
	public var difficulty(default, null):String;
	public var modifiers(default, null):Array<String>;
	public var stream(default, null):MpPlayStream = new MpPlayStream();
	public var names(default, null):Map<String, String> = new Map();
	/** Latest live scores: {account_id, score, acc, combo, miss, quit}. */
	public var live(default, null):Array<Dynamic> = [];
	public var begun(default, null):Bool = false;
	public var ended(default, null):Bool = false;
	/** The local view of this play, kept for the results screen's timing graph. */
	public var localResult:Null<ResultsModel.ResultsData> = null;
	/** The server's `results` message once every player finished. */
	public var results(default, null):Dynamic = null;

	var savedModifiers:Dynamic = null;
	var contentHeld:Bool = false;
	var scoreAt:Float = 0;

	function new() {}

	/**
		Start the countdown's song. Returns null on success, or why it could not start.
		`fetch` is this player's copy of the lobby song (null for the host).
	**/
	public static function begin(countdown:Dynamic, lobby:Dynamic, fetch:Null<MpFetch>, accountId:String):Null<String> {
		if (current != null)
			current.release();
		var song:Dynamic = lobby.song;
		var chartPath = MpTransfer.chartPathOf(song);
		if (chartPath == null)
			return 'The lobby song has no chart.';
		var match = new MpMatch();
		match.startServerMs = countdown.start_server_ms;
		match.seed = Std.int(countdown.seed);
		match.title = Std.string(song.title);
		match.difficulty = Std.string(song.difficulty);
		match.modifiers = [];
		var players:Array<Dynamic> = lobby.players;
		for (player in players) {
			match.names.set(player.account_id, player.name);
			if (player.account_id == accountId)
				match.modifiers = player.modifiers;
		}
		match.hold(fetch);
		var parts = chartPath.split('/');
		var chartName = parts[3].substr(0, parts[3].length - 5);
		try {
			PlayState.SONG = Song.loadFromJson(chartName, parts[2]);
		} catch (error:Dynamic) {
			match.release();
			return 'The song could not be loaded: ' + error;
		}
		PlayState.isStoryMode = false;
		PlayState.balls = 0;
		PlayState.watchedCutscene = false;
		ModifierState.isStoryMode = false;
		var index = DifficultyManager.getDifficultyNames().indexOf(match.difficulty.toLowerCase());
		PlayState.storyDifficulty = index >= 0 ? index : DifficultyManager.getDefaultDiff();
		current = match;
		MpHooks.current = match;
		MpClient.get().listeners.push(match.onMessage);
		if (flixel.FlxG.sound.music != null)
			flixel.FlxG.sound.music.stop();
		LoadingState.loadAndSwitchState(new PlayState());
		return null;
	}

	/** Apply the match's modifiers and, for another player's song, the cache overlay and sandbox. */
	function hold(fetch:Null<MpFetch>):Void {
		contentHeld = true;
		savedModifiers = ModifierState.snapshot();
		ModifierState.resetAll();
		for (id in modifiers)
			ModifierState.setOn(id, true);
		if (fetch != null && fetch.needsSandbox()) {
			#if sys
			var cwd = Sys.getCwd();
			MpOverlay.mount(cwd, fetch.mounts);
			ScriptSandbox.enable([cwd + '/' + MpCache.ROOT, cwd + '/tmp', lime.system.System.applicationStorageDirectory],
				[cwd + '/assets/data/options.json']);
			#end
		}
	}

	/** Undo hold(): called when PlayState goes away, and before a new match. */
	public function release():Void {
		if (!contentHeld)
			return;
		contentHeld = false;
		MpOverlay.unmount();
		ScriptSandbox.disable();
		ModifierState.restore(savedModifiers);
	}

	/** Seconds the countdown should still wait so that song position 0 lands on the server's start time. */
	public function countdownWait(countdownMs:Float):Float {
		var wait = (startServerMs - countdownMs - MpClient.get().serverNow()) / 1000;
		return wait > 0 ? Math.min(wait, 10) : 0;
	}

	/** The song started; the server learns how it is judged. */
	public function playBegin(lengthMs:Float, windows:Dynamic, offsetMs:Float):Void {
		if (begun)
			return;
		begun = true;
		MpClient.get().send({t: 'play_begin', offset_ms: offsetMs, length_ms: Std.int(Math.max(1, Math.min(lengthMs, 20 * 60 * 1000))),
			windows: windows, modifiers: modifiers});
		flush();
	}

	/** Every frame while playing: send what was recorded, and the live score at most 4 times a second. */
	public function frame(score:Int, accuracy:Float, combo:Int, misses:Int):Void {
		if (!begun || ended)
			return;
		flush();
		var now = haxe.Timer.stamp();
		if (now - scoreAt >= 0.25) {
			scoreAt = now;
			MpClient.get().send({t: 'score', score: score, acc: accuracy, combo: combo, miss: misses});
		}
	}

	function flush():Void {
		for (message in stream.drain())
			MpClient.get().send(message);
	}

	/** The song ended or the player died: the play is over for the server. */
	public function finishPlay(failed:Bool, ?result:ResultsModel.ResultsData):Void {
		if (result != null)
			localResult = result;
		if (ended)
			return;
		ended = true;
		if (begun) {
			flush();
			MpClient.get().send({t: 'play_end', failed: failed});
		}
	}

	/** Leave the song for the lobby, which waits for everyone's results. */
	public function leaveSong(failed:Bool):Void {
		finishPlay(failed);
		flixel.FlxG.switchState(() -> new MpLobbyState());
	}

	/** The results screen has been shown; the match is over. */
	public function close():Void {
		release();
		MpClient.get().listeners.remove(onMessage);
		if (current == this)
			current = null;
		if (MpHooks.current == this)
			MpHooks.current = null;
	}

	function onMessage(message:Dynamic):Void {
		switch (Std.string(message.t)) {
			case 'scores':
				live = message.players;
			case 'results':
				results = message;
			case 'disconnected':
				ended = true;
			default:
		}
	}

	/** The results screen's data: the server's rows, with this player's own timing graph. */
	public function resultsData(accountId:String):ResultsModel.ResultsData {
		var rows:Array<Dynamic> = results == null ? [] : results.players;
		var players:Array<ResultsModel.ResultsPlayer> = [for (row in rows) playerOf(row)];
		var mine = Lambda.find(players, function(p) return p.id == accountId);
		if (mine == null)
			mine = players.length > 0 ? players[0] : playerOf({account_id: accountId, name: names.get(accountId)});
		var ranked = results != null && results.ranked == true;
		return {
			title: title,
			difficulty: difficulty,
			player: mine,
			judgeable: localResult == null ? -1 : localResult.judgeable,
			multiplier: localResult == null ? 1 : localResult.multiplier,
			unranked: !ranked,
			previousBest: -1,
			previousRank: '',
			hitOffsets: localResult == null ? [] : localResult.hitOffsets,
			storyMode: false,
			players: players,
			note: results == null ? 'The match ended before every result arrived.'
				: (results.reason != null ? Std.string(results.reason) : (ranked ? null : 'Unranked'))
		};
	}

	static function playerOf(row:Dynamic):ResultsModel.ResultsPlayer {
		var counts:Dynamic = row.judgements == null ? {} : row.judgements;
		var count = function(field:String):Int {
			var value:Dynamic = Reflect.field(counts, field);
			return value == null ? 0 : Std.int(value);
		};
		return {
			id: Std.string(row.account_id),
			name: row.name == null ? 'Player' : Std.string(row.name),
			score: row.score == null ? 0 : Std.int(row.score),
			accuracy: row.accuracy == null ? 0 : row.accuracy,
			maxCombo: row.max_combo == null ? 0 : Std.int(row.max_combo),
			rank: row.rank == null ? 'D' : Std.string(row.rank),
			sicks: count('sick'),
			goods: count('good'),
			bads: count('bad'),
			shits: count('shit'),
			misses: count('miss'),
			modifiers: row.modifiers == null ? [] : row.modifiers,
			failed: row.failed == true,
			quit: row.quit == true
		};
	}
}
