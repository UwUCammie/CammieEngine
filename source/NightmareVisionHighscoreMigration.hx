package;

import haxe.io.Path;
import CompatScriptManifest.CompatScriptManifestData;

/** A registered chart row eligible for a bounded owner-score migration.
 *
 * `loadChart` must load this exact registered folder and native difficulty.
 * It is called only after both values of the corresponding native best-score
 * pair exist, so charts without scores never incur a parse or mutate Song's
 * static chart state. Callers that already hold a chart may supply `chart`.
 */
typedef NightmareVisionHighscoreMigrationEntry = {
	var registeredSong:String;
	var nativeDifficultyIndex:Int;
	var destinationChartPath:String;
	var provenance:Dynamic;
	var ownerManifest:CompatScriptManifestData;
	@:optional var chart:Dynamic;
	@:optional var loadChart:Void->Dynamic;
}

typedef NightmareVisionHighscoreMigrationResult = {
	var migrated:Int;
	var unchanged:Int;
	var skipped:Int;
	var ambiguous:Int;
	var diagnostics:Array<String>;
}

private typedef NightmareVisionHighscoreMigrationCandidate = {
	var sourceOwner:String;
	var sourceFolder:String;
	var destinationFolder:String;
	var registeredSong:String;
	var sourceSong:String;
	var sourceDifficulty:Int;
	var sourceDifficulties:Array<String>;
	var targetKey:String;
	var nativeKey:String;
	var nativeScore:Int;
	var nativeAccuracy:Float;
	var identity:String;
}

/** Bounded migration from native best scores into one owner's private NMV
	Highscore maps. The caller supplies already-registered charts and receipt
	metadata; this helper does no filesystem or media scan. */
class NightmareVisionHighscoreMigration {
	static final SOURCE_ENGINE:String = 'Nightmare Vision';

	/** Read a paired native best-score record. Accuracy comes from the exact
		`best-score` key as the score; the separate `best-accuracy` aggregate can
		represent another play and is deliberately ignored. */
	public static function migrate(entries:Array<NightmareVisionHighscoreMigrationEntry>,
		ownerRoot:String, authorizedRoots:Array<String>, scores:NightmareVisionHighscore,
		difficulty:NightmareVisionDifficultyAdapter, ?report:String->Void):NightmareVisionHighscoreMigrationResult {
		var result:NightmareVisionHighscoreMigrationResult = {
			migrated:0, unchanged:0, skipped:0, ambiguous:0, diagnostics:[]
		};
		if (scores == null || difficulty == null) {
			diagnose(result, report, '[nv-score-migration-service-missing]');
			return result;
		}
		var cleanOwner = ownerPath(ownerRoot);
		var allowed = new Map<String, Bool>();
		if (authorizedRoots != null) for (root in authorizedRoots) {
			var clean = ownerPath(root);
			if (clean != null) allowed.set(CompatScriptManifest.destinationKey(clean), true);
		}
		if (cleanOwner == null || !allowed.exists(CompatScriptManifest.destinationKey(cleanOwner))) {
			diagnose(result, report, '[nv-score-migration-owner-scope] session owner is not in its authorized family');
			return result;
		}
		if (Highscore.songScores == null || Highscore.songAccuracy == null) {
			diagnose(result, report, '[nv-score-migration-native-ledger-unavailable] native score maps are not loaded');
			return result;
		}

		var originalDifficulties = difficulty.difficulties;
		var originalIndex = difficulty.currentDifficultyIndex;
		var restored = false;
		var restore = function():Void {
			if (restored) return;
			restored = true;
			difficulty.difficulties = originalDifficulties;
			if (!difficulty.released) difficulty.selectDifficulty(originalIndex);
		};
		var failure:Dynamic = null;
		try {
			var candidates:Array<NightmareVisionHighscoreMigrationCandidate> = [];
			var seenEntries:Map<String, Bool> = new Map();
			if (entries != null) for (entry in entries) {
				var pending = validateReceiptAndPair(entry, allowed, result, report);
				if (pending == null || seenEntries.exists(pending.identity)) continue;
				seenEntries.set(pending.identity, true);
				var candidate = materializeCandidate(entry, pending, scores, difficulty, result, report);
				if (candidate != null) candidates.push(candidate);
			}

			var byTarget:Map<String, Array<NightmareVisionHighscoreMigrationCandidate>> = new Map();
			for (candidate in candidates) {
				var group = byTarget.get(candidate.targetKey);
				if (group == null) {group = []; byTarget.set(candidate.targetKey, group);}
				group.push(candidate);
			}
			for (targetKey in byTarget.keys()) {
				var group = byTarget.get(targetKey);
				if (group == null || group.length == 0) continue;
				if (group.length > 1) {
					result.ambiguous++;
					result.skipped += group.length;
					diagnose(result, report, '[nv-score-migration-ambiguous] multiple registered native charts map to '
						+ targetKey + '; left the private score unchanged');
					continue;
				}
				var candidate = group[0];
				if (scores.songScores.exists(candidate.targetKey)
					&& scores.songScores.get(candidate.targetKey) >= candidate.nativeScore) {
					result.unchanged++;
					continue;
				}

				difficulty.difficulties = candidate.sourceDifficulties.copy();
				difficulty.selectDifficulty(candidate.sourceDifficulty);
				// `-1` follows the source adapter's current-difficulty path. The copied
				// source menu and index above are the exact receipt-mapped slot.
				scores.saveScore(candidate.sourceSong, candidate.nativeScore, -1, candidate.nativeAccuracy);
				result.migrated++;
			}
		} catch (error:Dynamic) {
			failure = error;
		}
		try restore() catch (restoreError:Dynamic) {
			if (failure == null) failure = restoreError;
		}
		if (failure != null) throw failure;
		return result;
	}

	/** Validate small provenance and difficulty metadata, then check for a native
		pair before asking the caller to parse the chart. */
	static function validateReceiptAndPair(entry:NightmareVisionHighscoreMigrationEntry,
		allowed:Map<String, Bool>, result:NightmareVisionHighscoreMigrationResult,
		report:String->Void):Null<NightmareVisionHighscoreMigrationCandidate> {
		if (entry == null || !validComponent(entry.registeredSong)
			|| entry.nativeDifficultyIndex < 0) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-entry-invalid]');
			return null;
		}
		var registered = StringTools.trim(entry.registeredSong).toLowerCase();
		var receipt = entry.provenance;
		var destination = fieldString(receipt, 'destinationFolder');
		var sourceFolder = fieldString(receipt, 'sourceFolder');
		var receiptOwner = ownerPath(Reflect.field(receipt, 'sourceOwner'));
		if (receipt == null || Reflect.field(receipt, 'version') != 1
			|| Reflect.field(receipt, 'sourceEngine') != SOURCE_ENGINE
			|| !validComponent(destination) || destination.toLowerCase() != registered
			|| !validSourceFolder(sourceFolder) || receiptOwner == null
			|| !allowed.exists(CompatScriptManifest.destinationKey(receiptOwner))) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-provenance-invalid] ' + registered);
			return null;
		}
		if (!manifestOwnsChart(entry.ownerManifest, receiptOwner)) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-owner-mismatch] ' + registered);
			return null;
		}
		var sourceDifficulties = validateSourceDifficulties(Reflect.field(receipt, 'sourceSelectableDifficulties'));
		if (sourceDifficulties == null) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-source-difficulties-invalid] ' + registered);
			return null;
		}

		var ending:String;
		try ending = DifficultyManager.getDiffEnding(entry.nativeDifficultyIndex) catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-difficulty-invalid] ' + registered + ': ' + Std.string(error));
			return null;
		}
		if (ending == null || (ending != '' && !StringTools.startsWith(ending, '-'))) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-difficulty-invalid] ' + registered);
			return null;
		}
		var sourceDifficultyName:String;
		try sourceDifficultyName = ending == ''
			? nativeDifficultyName(entry.nativeDifficultyIndex) : ending.substr(1) catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-difficulty-name-missing] ' + registered
				+ ': ' + Std.string(error));
			return null;
		}
		if (sourceDifficultyName == '') {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-difficulty-name-missing] ' + registered);
			return null;
		}
		var sourceDifficulty = findDifficulty(sourceDifficulties, sourceDifficultyName);
		if (sourceDifficulty < 0) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-source-difficulty-unmapped] ' + registered
				+ ':' + sourceDifficultyName);
			return null;
		}

		var nativeKey:String;
		try nativeKey = Highscore.formatSong(registered, entry.nativeDifficultyIndex, 'best-score') catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-key-failed] ' + registered + ': ' + Std.string(error));
			return null;
		}
		var hasScore = Highscore.songScores.exists(nativeKey);
		var hasAccuracy = Highscore.songAccuracy.exists(nativeKey);
		if (!hasScore && !hasAccuracy) {
			result.skipped++;
			return null;
		}
		if (!hasScore || !hasAccuracy) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-pair-missing] ' + nativeKey);
			return null;
		}
		var scoreValue:Dynamic = Highscore.songScores.get(nativeKey);
		var accuracyValue:Dynamic = Highscore.songAccuracy.get(nativeKey);
		var nativeScore = exactScore(scoreValue);
		var nativeAccuracy = exactAccuracy(accuracyValue);
		if (nativeScore == null || nativeScore < 0) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-score-invalid] ' + nativeKey);
			return null;
		}
		if (nativeAccuracy == null || Math.isNaN(nativeAccuracy)
			|| nativeAccuracy == Math.POSITIVE_INFINITY || nativeAccuracy == Math.NEGATIVE_INFINITY
			|| nativeAccuracy < 0) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-accuracy-invalid] ' + nativeKey);
			return null;
		}
		var identity = receiptOwner + '|' + sourceFolder.toLowerCase() + '|'
			+ destination.toLowerCase() + '|' + registered + '|'
			+ entry.nativeDifficultyIndex + '|' + sourceDifficulty;
		return {
			sourceOwner:receiptOwner, sourceFolder:sourceFolder, destinationFolder:destination,
			registeredSong:registered, sourceSong:null, sourceDifficulty:sourceDifficulty,
			sourceDifficulties:sourceDifficulties, targetKey:null, nativeKey:nativeKey,
			nativeScore:nativeScore, nativeAccuracy:nativeAccuracy, identity:identity
		};
	}

	static function materializeCandidate(entry:NightmareVisionHighscoreMigrationEntry,
		pending:NightmareVisionHighscoreMigrationCandidate, scores:NightmareVisionHighscore,
		difficulty:NightmareVisionDifficultyAdapter, result:NightmareVisionHighscoreMigrationResult,
		report:String->Void):Null<NightmareVisionHighscoreMigrationCandidate> {
		var chartPath = validatedChartPath(entry.destinationChartPath, pending.registeredSong,
			entry.nativeDifficultyIndex);
		var chartExists = false;
		try chartExists = chartPath != null && FNFAssets.exists(chartPath) catch (_:Dynamic) {}
		if (!chartExists) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-path-missing] ' + pending.registeredSong);
			return null;
		}
		var chart = entry.chart;
		if (chart == null && entry.loadChart != null) try chart = entry.loadChart() catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-load-failed] ' + pending.registeredSong
				+ ': ' + Std.string(error));
			return null;
		}
		if (chart == null) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-missing] ' + pending.registeredSong);
			return null;
		}
		var storage = fieldString(chart, 'compatStorageFolder');
		if (!validComponent(storage) || storage.toLowerCase() != pending.registeredSong) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-not-registered] ' + pending.registeredSong);
			return null;
		}
		var chartFile = fieldString(chart, 'compatChartFileName');
		var ending:String;
		try ending = DifficultyManager.getDiffEnding(entry.nativeDifficultyIndex) catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-difficulty-invalid] ' + pending.registeredSong
				+ ': ' + Std.string(error));
			return null;
		}
		var expectedChartFile = pending.registeredSong + ending.toLowerCase();
		if (chartFile.toLowerCase() != expectedChartFile) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-chart-difficulty-mismatch] ' + pending.registeredSong
				+ ' expected ' + expectedChartFile + ' but loaded ' + chartFile);
			return null;
		}
		var sourceSongValue:Dynamic = Reflect.field(chart, 'song');
		var sourceSong = Std.isOfType(sourceSongValue, String) ? cast(sourceSongValue, String) : '';
		var cleanSourceSong = StringTools.trim(sourceSong);
		if (cleanSourceSong == '' || cleanSourceSong.toLowerCase() == 'null' || sourceSong.indexOf('\u0000') >= 0) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-source-title-missing] ' + pending.registeredSong);
			return null;
		}
		var nativeSongId:String;
		try nativeSongId = Highscore.scoreSongIdForChart(chart) catch (error:Dynamic) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-identity-failed] ' + pending.registeredSong
				+ ': ' + Std.string(error));
			return null;
		}
		if (nativeSongId == null || StringTools.trim(nativeSongId).toLowerCase() != pending.registeredSong) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-native-identity-mismatch] ' + pending.registeredSong);
			return null;
		}

		var targetKey:String = null;
		var keyError:Dynamic = null;
		var originalDifficulties = difficulty.difficulties;
		var originalIndex = difficulty.currentDifficultyIndex;
		try {
			difficulty.difficulties = pending.sourceDifficulties.copy();
			difficulty.selectDifficulty(pending.sourceDifficulty);
			targetKey = scores.formatSong(sourceSong, -1);
		} catch (error:Dynamic) {
			keyError = error;
		}
		try {
			difficulty.difficulties = originalDifficulties;
			if (!difficulty.released) difficulty.selectDifficulty(originalIndex);
		} catch (restoreError:Dynamic) {
			if (keyError == null) keyError = restoreError;
		}
		if (keyError != null) {
			result.skipped++;
			diagnose(result, report, '[nv-score-migration-private-key-failed] ' + pending.registeredSong
				+ ': ' + Std.string(keyError));
			return null;
		}
		return {
			sourceOwner:pending.sourceOwner, sourceFolder:pending.sourceFolder,
			destinationFolder:pending.destinationFolder, registeredSong:pending.registeredSong,
			sourceSong:sourceSong, sourceDifficulty:pending.sourceDifficulty,
			sourceDifficulties:pending.sourceDifficulties, targetKey:targetKey,
			nativeKey:pending.nativeKey, nativeScore:pending.nativeScore,
			nativeAccuracy:pending.nativeAccuracy, identity:pending.identity
		};
	}

	static function findDifficulty(difficulties:Array<String>, wanted:String):Int {
		for (index in 0...difficulties.length)
			if (difficulties[index].toLowerCase() == wanted.toLowerCase()) return index;
		return -1;
	}

	static function nativeDifficultyName(index:Int):String {
		try {
			var names = DifficultyManager.getDifficultyNames();
			return names == null || index < 0 || index >= names.length || names[index] == null
				? '' : StringTools.trim(names[index]);
		} catch (_:Dynamic) return '';
	}

	static function manifestOwnsChart(manifest:CompatScriptManifestData, receiptOwner:String):Bool {
		if (manifest == null || manifest.roots == null) return false;
		var selected = CompatScriptManifest.selectedRoot(manifest);
		if (selected == null || CompatScriptManifest.destinationKey(selected)
			!= CompatScriptManifest.destinationKey(receiptOwner)) return false;
		for (root in manifest.roots)
			if (root != null && root.dependency != true
				&& root.engine == SOURCE_ENGINE
				&& CompatScriptManifest.destinationKey(root.path) == CompatScriptManifest.destinationKey(selected))
				return true;
		return false;
	}

	static function validatedChartPath(value:String, registered:String,
		difficultyIndex:Int):Null<String> {
		if (value == null || StringTools.trim(value) == '') return null;
		var normalized = Path.normalize(StringTools.replace(StringTools.trim(value), '\\', '/'));
		normalized = StringTools.replace(normalized, '\\', '/');
		if (StringTools.startsWith(normalized, '/') || ~/^[A-Za-z]:/.match(normalized)) return null;
		for (part in normalized.split('/')) if (part == '..' || part == '' || part == '.') return null;
		var expectedEnding:String;
		try expectedEnding = DifficultyManager.getDiffEnding(difficultyIndex).toLowerCase()
		catch (_:Dynamic) return null;
		var expected = 'assets/data/' + registered + '/' + registered + expectedEnding;
		var lower = normalized.toLowerCase();
		if (lower != expected + '.json' && lower != expected + '.jsonc') return null;
		return normalized;
	}

	static function validateSourceDifficulties(value:Dynamic):Null<Array<String>> {
		if (!Std.isOfType(value, Array)) return null;
		var result:Array<String> = [];
		var seen:Map<String, Bool> = new Map();
		for (item in (cast value:Array<Dynamic>)) {
			if (!Std.isOfType(item, String)) return null;
			var name = StringTools.trim(cast item);
			if (!validDifficulty(name)) return null;
			var key = name.toLowerCase();
			if (seen.exists(key)) return null;
			seen.set(key, true);
			result.push(name);
		}
		return result.length == 0 ? null : result;
	}

	static function exactScore(value:Dynamic):Null<Int> {
		switch (Type.typeof(value)) {
			case TInt: return cast value;
			case TFloat:
				var numeric:Float = cast value;
				if (Math.isNaN(numeric) || numeric == Math.POSITIVE_INFINITY
					|| numeric == Math.NEGATIVE_INFINITY || numeric != Math.floor(numeric)) return null;
				return Std.int(numeric);
			default: return null;
		}
	}

	static function exactAccuracy(value:Dynamic):Null<Float> {
		switch (Type.typeof(value)) {
			case TInt: return cast value;
			case TFloat: return cast value;
			default: return null;
		}
	}

	static function ownerPath(value:Dynamic):Null<String> {
		if (!Std.isOfType(value, String)) return null;
		var clean = StringTools.replace(StringTools.trim(cast value), '\\', '/');
		while (StringTools.endsWith(clean, '/')) clean = clean.substr(0, clean.length - 1);
		if (!StringTools.startsWith(clean.toLowerCase(), 'assets/imported_mods/')) return null;
		var parts = clean.split('/');
		if (parts.length < 3) return null;
		for (index in 2...parts.length) if (!validComponent(parts[index])) return null;
		return clean;
	}

	static function validComponent(value:String):Bool {
		if (value == null) return false;
		var clean = StringTools.trim(value);
		return clean != '' && clean != '.' && clean != '..'
			&& clean.indexOf('..') < 0 && clean.indexOf('/') < 0
			&& clean.indexOf('\\') < 0 && clean.indexOf(':') < 0
			&& clean.indexOf('\u0000') < 0;
	}

	static function validDifficulty(value:String):Bool {
		return validComponent(value) && value.indexOf('"') < 0 && value.indexOf('\'') < 0;
	}

	static function validSourceFolder(value:String):Bool {
		if (value == null || StringTools.trim(value) == '') return false;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (StringTools.startsWith(clean, '/') || ~/^[A-Za-z]:/.match(clean)) return false;
		for (part in clean.split('/')) if (!validComponent(part)) return false;
		return true;
	}

	static function fieldString(object:Dynamic, field:String):String {
		var value = object == null ? null : Reflect.field(object, field);
		return !Std.isOfType(value, String) ? '' : StringTools.trim(cast value);
	}

	static function diagnose(result:NightmareVisionHighscoreMigrationResult,
		report:String->Void, message:String):Void {
		result.diagnostics.push(message);
		if (report != null) report(message);
	}
}
