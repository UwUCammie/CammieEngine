package multiplayer;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import openfl.events.KeyboardEvent;
import MenuStyle.MenuHint;

private typedef MpRow = {
	var label:String;
	var detail:String;
	var enabled:Bool;
	var action:Void->Void;
}

private typedef MpEntry = {
	var label:String;
	var value:String;
	var max:Int;
	var allowed:String->Bool;
	var done:String->Void;
}

/**
	The Online screen: signing in, the lobby list, the lobby room and waiting for results.

	It is one screen whose rows change with the connection: everything it shows comes from
	MpClient (connection and lobby_state), MpTransfer (song download) and MpMatch (a song
	that just ended). Choosing a song opens Freeplay in its lobby pick mode.
**/
class MpLobbyState extends MusicBeatState {
	static inline var LIST_X:Int = 48;
	static inline var LIST_WIDTH:Int = 560;
	static inline var LIST_TOP:Int = 132;
	static inline var ROW_HEIGHT:Int = 46;
	static inline var VISIBLE_ROWS:Int = 10;
	static inline var SIDE_X:Int = 650;
	static inline var SIDE_WIDTH:Int = 582;
	static final CODE_ALPHABET:String = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

	/** A notice carried across a screen change, e.g. why a song could not start. */
	public static var pendingNotice:String = '';

	var client:MpClient;
	var rows:Array<MpRow> = [];
	var selected:Int = 0;
	var signature:String = '';
	var rowSprites:Array<FlxSprite> = [];
	var titleText:FlxText;
	var statusText:FlxText;
	var sideTitle:FlxText;
	var sideText:FlxText;
	var detailText:FlxText;
	var footer:MenuFooter;
	var entry:Null<MpEntry> = null;
	var entryText:FlxText;
	var entryBox:FlxSprite;
	var lobbies:Array<Dynamic> = [];
	var listAt:Float = -10;
	var notice:String = '';
	var noticeTime:Float = 0;
	var sentModifiers:String = '';
	var resultsOpened:Bool = false;
	static var autoJoined:Bool = false;
	static var autoReadied:String = '';

	override function create():Void {
		super.create();
		FlxG.camera.scroll.set();
		FlxG.camera.target = null;
		MenuWidgets.background(this);
		add(MenuWidgets.rect(SIDE_X, LIST_TOP, SIDE_WIDTH, 500, MenuStyle.CARD, MenuStyle.DETAIL_ALPHA));
		add(MenuWidgets.rect(SIDE_X, LIST_TOP, SIDE_WIDTH, 4, MenuStyle.TEAL));
		titleText = MenuWidgets.text(LIST_X, 34, 900, 'ONLINE', MenuStyle.HEADING_SIZE, MenuStyle.CREAM);
		add(titleText);
		statusText = MenuWidgets.text(LIST_X, 88, 1180, '', MenuStyle.BODY_SIZE, MenuStyle.MUTED);
		add(statusText);
		sideTitle = MenuWidgets.text(SIDE_X + 20, LIST_TOP + 18, SIDE_WIDTH - 40, '', MenuStyle.TITLE_SIZE, MenuStyle.CREAM);
		add(sideTitle);
		sideText = MenuWidgets.text(SIDE_X + 20, LIST_TOP + 54, SIDE_WIDTH - 40, '', MenuStyle.BODY_SIZE, MenuStyle.TEXT);
		add(sideText);
		detailText = MenuWidgets.text(LIST_X, FlxG.height - MenuStyle.BAR_HEIGHT - 40, LIST_WIDTH, '', MenuStyle.SMALL_SIZE, MenuStyle.MUTED);
		add(detailText);
		entryBox = MenuWidgets.rect(LIST_X, LIST_TOP, LIST_WIDTH, 92, MenuStyle.PANEL, 0.96);
		entryBox.visible = false;
		entryText = MenuWidgets.text(LIST_X + 18, LIST_TOP + 14, LIST_WIDTH - 36, '', MenuStyle.TITLE_SIZE, MenuStyle.CHOICE);
		entryText.visible = false;
		footer = new MenuFooter('ONLINE', []);
		add(footer);
		add(entryBox);
		add(entryText);

		var limit = OptionsHandler.options.mpCacheLimitGB;
		MpCache.limitBytes = (limit == null ? 2 : limit) * 1024 * 1024 * 1024;
		client = MpClient.get();
		client.listeners.push(onMessage);
		MpSession.install();
		MpAccount.refreshStatus();
		if (MpMatch.current != null) {
			// However the song was left, its play is over and its content is put away.
			MpMatch.current.finishPlay(true);
			MpMatch.current.release();
		}
		if (pendingNotice != '') {
			say(pendingNotice);
			pendingNotice = '';
		}
		if (MpAccount.session() != null && client.state == 'offline')
			client.connect();
		FlxG.stage.addEventListener(KeyboardEvent.KEY_DOWN, onKeyDown);
	}

	override function destroy():Void {
		FlxG.stage.removeEventListener(KeyboardEvent.KEY_DOWN, onKeyDown);
		client.listeners.remove(onMessage);
		super.destroy();
	}

	function say(text:String):Void {
		notice = text;
		noticeTime = 6;
	}

	function onMessage(message:Dynamic):Void {
		switch (Std.string(message.t)) {
			case 'lobby_list':
				lobbies = message.lobbies;
			case 'error':
				say(MpText.error(Std.string(message.code)));
			case 'disconnected':
				say(MpText.error(Std.string(message.reason)));
			case 'countdown':
				var fetch = client.isHost() ? null : MpTransfer.fetch;
				var problem = MpMatch.begin(message, client.lobby, fetch, client.accountId);
				if (problem != null)
					say(problem);
			default:
		}
	}

	// ------------------------------------------------------------------ what the screen shows

	function lobbyPlayer(accountId:String):Dynamic {
		if (client.lobby == null)
			return null;
		var players:Array<Dynamic> = client.lobby.players;
		for (player in players)
			if (player.account_id == accountId)
				return player;
		return null;
	}

	/** The modifiers this player would ready with: the ones switched on that the lobby allows. */
	function readyModifiers():Array<String> {
		var allowed:Array<String> = client.lobby == null || client.lobby.allowed_modifiers == null ? [] : client.lobby.allowed_modifiers;
		return [for (id in ModifierState.modifierIds(true)) if (allowed.indexOf(id) >= 0) id];
	}

	function buildRows():Array<MpRow> {
		var list:Array<MpRow> = [];
		var match = MpMatch.current;
		if (match != null && match.ended) {
			list.push({label: 'Leave the match', detail: 'Back to the lobby without waiting for the results.', enabled: true,
				action: function() {
					match.close();
					signature = '';
				}});
			return list;
		}
		if (MpAccount.session() == null) {
			switch (MpAccount.status) {
				case Waiting(code, _):
					list.push({label: 'Code ' + code, detail: 'Approve this code on the page that opened in your browser.', enabled: false,
						action: null});
					list.push({label: 'Open the page again', detail: '', enabled: true, action: function() MpAccount.beginSignIn()});
				case Starting:
					list.push({label: 'Starting sign-in...', detail: '', enabled: false, action: null});
				default:
					list.push({label: 'Sign in', detail: 'Opens uwucammie.com in your browser. The game never sees your password.',
						enabled: true, action: function() MpAccount.beginSignIn()});
			}
			return list;
		}
		if (client.state != 'online') {
			list.push({label: client.state == 'connecting' ? 'Connecting...' : 'Connect', detail: '', enabled: client.state == 'offline',
				action: function() client.connect()});
			list.push({label: 'Sign out', detail: 'Forget this game\'s session. You can also revoke it on the website.', enabled: true,
				action: function() {
					client.disconnect();
					MpAccount.signOut();
				}});
			return list;
		}
		if (client.lobby == null) {
			list.push({label: 'Create lobby', detail: 'Anyone can join from the list or with its code.', enabled: true,
				action: function() askText('Lobby name', client.name + '\'s lobby', 40, function(_) return true,
					function(name) client.send({t: 'lobby_create', name: name, capacity: 8}))});
			list.push({label: 'Create private lobby', detail: 'Players need the password to join.', enabled: true,
				action: function() askText('Lobby password', '', 64, function(_) return true, function(password) {
					if (password != '')
						client.send({t: 'lobby_create', name: client.name + '\'s lobby', capacity: 8, password: password});
				})});
			list.push({label: 'Join with a code', detail: 'The six-letter code shown in the lobby.', enabled: true,
				action: function() askText('Lobby code', '', 6, function(c) return CODE_ALPHABET.indexOf(c.toUpperCase()) >= 0,
					function(code) client.send({t: 'lobby_join', code: code.toUpperCase()}))});
			for (lobby in lobbies) {
				var info:Dynamic = lobby;
				var detail = info.players + '/' + info.capacity + ' players' + (info.song == null ? '' : ', ' + info.song)
					+ (info.state == 'playing' || info.state == 'countdown' ? ', playing now' : '');
				list.push({label: (info.locked ? '[locked] ' : '') + info.name, detail: detail,
					enabled: info.players < info.capacity && info.state != 'playing' && info.state != 'countdown',
					action: function() {
						if (info.locked)
							askText('Password for ' + info.name, '', 64, function(_) return true,
								function(password) client.send({t: 'lobby_join', id: info.id, password: password}));
						else
							client.send({t: 'lobby_join', id: info.id});
					}});
			}
			list.push({label: 'Sign out', detail: 'Signed in as ' + client.name + '.', enabled: true, action: function() {
				client.disconnect();
				MpAccount.signOut();
			}});
			return list;
		}

		var lobby:Dynamic = client.lobby;
		var me = lobbyPlayer(client.accountId);
		var host = client.isHost();
		var ready = me != null && me.ready == true;
		var hasSong = me != null && me.has_song == true;
		var fetch = MpTransfer.fetch;
		if (lobby.song != null) {
			var label = ready ? 'Ready' : 'Not ready';
			var detail = ready ? 'Press to stop being ready.' : 'Press when you are ready to play.';
			if (!hasSong)
				detail = fetch != null && fetch.state == 'failed' ? fetch.error : 'Getting the song first...';
			list.push({label: label, detail: detail, enabled: hasSong, action: function() {
				sentModifiers = readyModifiers().join(',');
				client.send({t: 'ready', ready: !ready, modifiers: readyModifiers()});
			}});
		}
		var mods = readyModifiers();
		list.push({label: 'Modifiers: ' + (mods.length == 0 ? 'none' : [for (id in mods) ModifierState.find(id).name].join(', ')),
			detail: 'Only visual modifiers count online; others stay off for the match.', enabled: true, action: openModifiers});
		if (host) {
			list.push({label: lobby.song == null ? 'Choose a song' : 'Change song', detail: 'Pick from Freeplay. Players without it get it from you.',
				enabled: true, action: chooseSong});
			var players:Array<Dynamic> = lobby.players;
			var everyone = lobby.song != null && Lambda.foreach(players, function(p) return p.ready == true);
			list.push({label: 'Start', detail: everyone ? 'Everyone is ready.' : 'Waiting for everyone to be ready.', enabled: everyone,
				action: function() client.send({t: 'start'})});
			var allowed:Array<String> = lobby.allowed_modifiers == null ? [] : lobby.allowed_modifiers;
			list.push({label: 'Visual modifiers: ' + (allowed.length == 0 ? 'off' : 'allowed'), detail: 'Whether players may use Flipped, Snake and the like.',
				enabled: true, action: function() client.send({t: 'lobby_settings',
					allowed_modifiers: allowed.length == 0 ? ['flipped', 'vanish', 'invis', 'snake', 'drunk'] : []})});
			for (player in players)
				if (player.account_id != client.accountId) {
					var target:Dynamic = player;
					list.push({label: 'Make ' + target.name + ' host', detail: '', enabled: true,
						action: function() client.send({t: 'lobby_transfer_host', account_id: target.account_id})});
					list.push({label: 'Remove ' + target.name, detail: '', enabled: true,
						action: function() client.send({t: 'lobby_kick', account_id: target.account_id})});
				}
		}
		list.push({label: 'Leave lobby', detail: '', enabled: true, action: function() {
			client.leaveLobby();
		}});
		return list;
	}

	function sideContent():{title:String, body:String} {
		var match = MpMatch.current;
		if (match != null && match.ended) {
			var lines = [];
			var live = match.live.copy();
			live.sort(function(a, b) return Std.int(b.score) - Std.int(a.score));
			for (row in live)
				lines.push(padName(match.names.get(row.account_id)) + '  ' + ResultsModel.formatScore(Std.int(row.score))
					+ (row.quit == true ? '  (left)' : ''));
			return {title: 'Waiting for the other players', body: lines.join('\n')};
		}
		if (client.state != 'online')
			return {title: 'Play together', body: 'Score-race lobbies for 2 to 16 players on the same song.\n\n'
				+ 'Songs you do not have are sent to you by the host and kept in a separate cache. '
				+ 'Their scripts run with file, network and system access blocked.'};
		if (client.lobby == null)
			return {title: 'Lobbies', body: lobbies.length == 0 ? 'No open lobbies right now. Create one!' : lobbies.length + ' open.'};
		var lobby:Dynamic = client.lobby;
		var lines = ['Code ' + lobby.code + (lobby.locked ? '   (private)' : ''), ''];
		if (lobby.song == null)
			lines.push('No song chosen yet.');
		else {
			lines.push(lobby.song.title + '  [' + lobby.song.difficulty + ']');
			if (lobby.song.scripted == true)
				lines.push('This song has scripts; they run sandboxed for players who received it.');
			var fetch = MpTransfer.fetch;
			if (fetch != null && fetch.state == 'downloading')
				lines.push('Receiving ' + megabytes(fetch.have()) + ' of ' + megabytes(fetch.manifest.total) + ' MB');
		}
		lines.push('');
		var players:Array<Dynamic> = lobby.players;
		for (player in players) {
			var state = player.ready == true ? 'ready' : (player.has_song == true ? 'not ready'
				: 'getting song ' + Math.round(player.progress * 100) + '%');
			lines.push(padName(player.name) + '  ' + state + (player.account_id == lobby.host ? '  (host)' : ''));
		}
		return {title: lobby.name + '  ' + players.length + '/' + lobby.capacity, body: lines.join('\n')};
	}

	static function megabytes(bytes:Float):String
		return Std.string(Math.round(bytes / 1024 / 1024 * 10) / 10);

	static function padName(name:Null<String>):String {
		var value = name == null ? 'Player' : name;
		if (value.length > 18)
			value = value.substr(0, 17) + '.';
		while (value.length < 18)
			value += ' ';
		return value;
	}

	function statusLine():String {
		if (notice != '')
			return notice;
		if (MpAccount.session() == null)
			return switch (MpAccount.status) {
				case Failed(message): message;
				case Waiting(_, url): 'Waiting for approval at ' + url;
				default: 'Sign in with your uwucammie.com account to play online.';
			};
		return switch (client.state) {
			case 'online': 'Signed in as ' + client.name;
			case 'connecting': 'Connecting to play.uwucammie.com...';
			default: client.lastError != '' ? MpText.error(client.lastError) : 'Not connected.';
		};
	}

	function refresh():Void {
		rows = buildRows();
		var side = sideContent();
		var key = [for (row in rows) row.label + '|' + row.enabled].join('/') + '#' + side.title + side.body;
		if (selected >= rows.length)
			selected = rows.length - 1;
		if (selected < 0)
			selected = 0;
		sideTitle.text = side.title;
		sideText.text = side.body;
		statusText.text = statusLine();
		if (key == signature)
			return;
		signature = key;
		drawRows();
	}

	function drawRows():Void {
		for (sprite in rowSprites) {
			remove(sprite, true);
			sprite.destroy();
		}
		rowSprites = [];
		var first = Std.int(Math.max(0, Math.min(selected - Std.int(VISIBLE_ROWS / 2), rows.length - VISIBLE_ROWS)));
		for (index in first...Std.int(Math.min(rows.length, first + VISIBLE_ROWS))) {
			var row = rows[index];
			var y = LIST_TOP + (index - first) * ROW_HEIGHT;
			var focus = index == selected ? 1.0 : 0.0;
			var card = MenuWidgets.rect(LIST_X, y, LIST_WIDTH, ROW_HEIGHT - 6, MenuStyle.cardColor(focus), MenuStyle.cardAlpha(focus));
			rowSprites.push(card);
			if (index == selected) {
				var stripe = MenuWidgets.rect(LIST_X, y, MenuStyle.STRIPE_WIDTH, ROW_HEIGHT - 6, MenuStyle.PINK);
				rowSprites.push(stripe);
			}
			var label = MenuWidgets.text(LIST_X + 18, y + 9, LIST_WIDTH - 36, row.label, MenuStyle.TITLE_SIZE,
				MenuStyle.titleColor(index == selected, !row.enabled));
			rowSprites.push(label);
		}
		for (sprite in rowSprites)
			insert(members.indexOf(footer), sprite);
		var current = rows.length > 0 ? rows[selected] : null;
		detailText.text = current == null ? '' : current.detail;
		var hints:Array<MenuHint> = [{key: 'ENTER', action: 'Select'}];
		if (client.lobby != null)
			hints.push({key: 'F2', action: 'Modifiers'});
		if (client.state == 'online' && client.lobby == null)
			hints.push({key: 'F5', action: 'Refresh'});
		hints.push({key: 'ESC', action: 'Back'});
		footer.setHints(hints);
	}

	// ------------------------------------------------------------------ actions

	function openModifiers():Void {
		if (subState != null)
			return;
		openSubState(new ModifierMenuSubState(false));
	}

	function chooseSong():Void {
		FreeplayState.lobbyPick = {
			chosen: function(chartPath, title, difficulty) {
				pendingNotice = 'Preparing ' + title + '...';
				FlxG.switchState(() -> new MpLobbyState());
				MpTransfer.share(chartPath, title, difficulty, 'classic', function(selection) {
					MpClient.get().send({t: 'song_select', selection: selection});
				}, function(error) pendingNotice = 'The song could not be shared: ' + error);
			},
			cancelled: function() FlxG.switchState(() -> new MpLobbyState())
		};
		FreeplayState.openHostLibrary();
		LoadingState.loadAndSwitchState(new FreeplayState());
	}

	function askText(label:String, initial:String, max:Int, allowed:String->Bool, done:String->Void):Void {
		entry = {label: label, value: initial, max: max, allowed: allowed, done: done};
		showEntry();
	}

	function showEntry():Void {
		var on = entry != null;
		entryBox.visible = entryText.visible = on;
		if (on)
			entryText.text = entry.label + '\n> ' + entry.value + '_';
	}

	function onKeyDown(event:KeyboardEvent):Void {
		if (entry == null || event.charCode < 32 || event.charCode == 127)
			return;
		var char = String.fromCharCode(event.charCode);
		if (entry.value.length < entry.max && entry.allowed(char)) {
			entry.value += entry.max == 6 ? char.toUpperCase() : char;
			showEntry();
		}
	}

	override function update(elapsed:Float):Void {
		super.update(elapsed);
		if (noticeTime > 0) {
			noticeTime -= elapsed;
			if (noticeTime <= 0)
				notice = '';
		}
		var match = MpMatch.current;
		if (match != null && match.ended && match.results != null && !resultsOpened) {
			resultsOpened = true;
			var data = match.resultsData(client.accountId);
			FlxG.switchState(() -> new ResultsState(data, function() {
				match.close();
				FlxG.switchState(() -> new MpLobbyState());
			}));
			return;
		}
		if (client.state == 'online' && client.lobby == null && haxe.Timer.stamp() - listAt > 3) {
			listAt = haxe.Timer.stamp();
			client.send({t: 'lobby_list'});
		}
		// A ready player who changes modifiers tells the lobby.
		var me = lobbyPlayer(client.accountId);
		if (me != null && me.ready == true && subState == null) {
			var mods = readyModifiers().join(',');
			if (sentModifiers != mods) {
				sentModifiers = mods;
				client.send({t: 'ready', ready: true, modifiers: readyModifiers()});
			}
		}
		autopilot();
		refresh();
		if (subState != null)
			return;
		if (entry != null) {
			if (FlxG.keys.justPressed.BACKSPACE && entry.value.length > 0) {
				entry.value = entry.value.substr(0, entry.value.length - 1);
				showEntry();
			} else if (FlxG.keys.justPressed.ENTER) {
				var done = entry.done;
				var value = StringTools.trim(entry.value);
				entry = null;
				showEntry();
				done(value);
			} else if (FlxG.keys.justPressed.ESCAPE) {
				entry = null;
				showEntry();
			}
			return;
		}
		if (controls.UP_P)
			move(-1);
		if (controls.DOWN_P)
			move(1);
		if (FlxG.keys.justPressed.F2 && client.lobby != null)
			openModifiers();
		if (FlxG.keys.justPressed.F5)
			listAt = -10;
		if (controls.ACCEPT && rows.length > 0) {
			var row = rows[selected];
			if (row.enabled && row.action != null) {
				FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt, 0.6);
				row.action();
				signature = '';
			}
		}
		if (controls.BACK) {
			if (client.lobby != null && (match == null || !match.ended)) {
				client.leaveLobby();
			} else {
				if (match != null)
					match.close();
				LoadingState.loadAndSwitchState(new MainMenuState());
			}
		}
	}

	/** A local end-to-end run (tools/mp_local_server.py) joins its lobby and readies for each song by itself. */
	function autopilot():Void {
		var code = MpEndpoint.testJoinCode();
		if (code == null || client.state != 'online')
			return;
		if (client.lobby == null) {
			if (!autoJoined) {
				autoJoined = true;
				client.send({t: 'lobby_join', code: code});
			}
			return;
		}
		var me = lobbyPlayer(client.accountId);
		var song:Dynamic = client.lobby.song;
		var id = song == null ? '' : Std.string(Reflect.field(song, 'package').id);
		if (me != null && me.has_song == true && me.ready != true && autoReadied != id && client.lobby.state != 'playing') {
			autoReadied = id;
			client.send({t: 'ready', ready: true, modifiers: []});
		}
	}

	function move(change:Int):Void {
		if (rows.length == 0)
			return;
		selected = (selected + change + rows.length) % rows.length;
		FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);
		signature = '';
	}
}
