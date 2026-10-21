package;

import flixel.FlxState;
import ResultsModel.ResultsPlayer;

/** Menus opened straight from the smoke harness (--smoke-open) with fixed sample data,
 * so a muted, captured run can check a screen without playing a song first. */
class RuntimeSmokeScreens {
	public static function open(name:String):FlxState {
		return switch (name) {
			case 'results-solo': new ResultsState(results(false));
			case 'results-lobby': new ResultsState(results(true), function() {});
			case 'modifiers':
				ModifierState.resetAll();
				ModifierState.setOn('fc', true);
				ModifierState.setOn('invis', true);
				new ModifierState();
			case 'mp-lobby': new multiplayer.MpLobbyState();
			default: throw 'unknown --smoke-open screen: ' + name;
		};
	}

	static function player(id:String, name:String, score:Int, accuracy:Float, rank:String, misses:Int, quit:Bool = false):ResultsPlayer
		return {id: id, name: name, score: score, accuracy: accuracy, maxCombo: 412 - misses * 37, rank: rank, sicks: 380 - misses * 9,
			goods: 24 + misses * 5, bads: 4 + misses, shits: 2, misses: misses, modifiers: misses == 0 ? ['invis'] : [], failed: false, quit: quit};

	static function results(lobby:Bool):ResultsModel.ResultsData {
		var offsets:Array<Float> = [];
		var seed = 7;
		for (_ in 0...410) {
			seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;
			var a = (seed % 1000) / 1000;
			seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;
			var b = (seed % 1000) / 1000;
			offsets.push((a + b - 1) * 38 + 3);
		}
		var local = player('local', 'You', 962410, 0.9836, 'S', 0);
		return {
			title: 'Tutorial',
			difficulty: 'Hard',
			player: local,
			judgeable: 412,
			multiplier: 1.06,
			unranked: false,
			previousBest: 931208,
			previousRank: 'A',
			hitOffsets: offsets,
			storyMode: false,
			players: lobby ? [player('a', 'Cammie', 988120, 0.9951, 'S', 0), local, player('b', 'Boyfriend', 845891, 0.95, 'S', 2),
				player('c', 'Pico', 719561, 0.90, 'A', 5), player('d', 'Darnell', 0, 0, 'F', 0, true)] : null,
			note: lobby ? null : null
		};
	}
}
