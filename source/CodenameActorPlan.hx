package;

import CodenameStagePlacement.CodenameStageOccurrence;
import CodenameStagePlacement.CodenameStagePlacementData;

typedef CodenameActorOccurrence = {
	var lineIndex:Int;
	var occurrenceIndex:Int;
	var authoredId:String;
	var nativeName:Null<String>;
	/** Non-null when the source engine's configured missing-XML fallback is used. */
	var sourceFallbackId:Null<String>;
	var role:String;
	var nativePrimary:Bool;
	var lineType:Null<Int>;
	var positionName:Null<String>;
	var placement:CodenameStageOccurrence;
}

/** Indexed construction identities from a validated selected-owner camera entry.
 * This is a construction plan, not a collection of live Character instances. */
class CodenameActorPlan {
	/** Every authored line, including empty ones, in original index order. */
	public var lines(default, null):Array<Dynamic> = [];
	public var occurrences(default, null):Array<CodenameActorOccurrence> = [];
	public var diagnostics(default, null):Array<String> = [];
	/** Authored stage identities and XML placement from this selected camera entry. */
	public var stage(default, null):Null<String>;
	public var nativeStage(default, null):Null<String>;
	public var stagePlacement(default, null):CodenameStagePlacementData;
	/** Verified scripts with no actor geometry, or geometry confined to named
	 * primary actors, do not own unrelated extra actors' XML slots. */
	public var staticXmlPlacementForExtras(default, null):Bool = false;
	var primary:Map<String, CodenameActorOccurrence> = [];

	public function new(entry:Dynamic, ?verifiedStageScript:String,
		?missingCharacterFallback:String) {
		if (entry == null || Reflect.field(entry, 'nativeCharacters') == null
			|| Reflect.field(entry, 'stagePlacement') == null)
			throw 'Codename actor metadata needs identity mapping and stage placement';
		stage = Std.isOfType(Reflect.field(entry, 'stage'), String)
			? StringTools.trim(cast Reflect.field(entry, 'stage')) : null;
		nativeStage = Std.isOfType(Reflect.field(entry, 'nativeStage'), String)
			? StringTools.trim(cast Reflect.field(entry, 'nativeStage')) : null;
		stagePlacement = CodenameStagePlacement.fromData(Reflect.field(entry, 'stagePlacement'));
		var placement = stagePlacement;
		if (verifiedStageScript != null) {
			CodenameStagePlacement.resolveScriptPlacement(placement, verifiedStageScript);
			var xmlOnlyOrScript = placement.unsupported.length == 0
				|| CodenameStagePlacement.onlyStageScriptUnsupported(placement);
			var scriptKeepsExtras = !CodenameStagePlacement.scriptMayChangeActorPlacement(verifiedStageScript)
				|| CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(verifiedStageScript);
			staticXmlPlacementForExtras = xmlOnlyOrScript && scriptKeepsExtras;
			if (CodenameStagePlacement.hasUnclassifiedPlacementAlias(verifiedStageScript))
				diagnostics.push('stage-script-unclassified-placement-alias');
		}
		var names:Dynamic = Reflect.field(entry, 'nativeCharacters');
		var missingIds:Map<String, Bool> = new Map();
		var missing:Dynamic = Reflect.field(entry, 'missingCharacters');
		if (Std.isOfType(missing, Array))
			for (id in (cast missing:Array<Dynamic>))
				if (Std.isOfType(id, String)) missingIds.set(cast id, true);
		var sourceLines:Array<Dynamic> = cast Reflect.field(entry, 'lines');
		for (i in 0...sourceLines.length) {
			var sourceLine = sourceLines[i];
			if (sourceLine == null) {
				lines.push(null);
				continue;
			}
			var ids:Array<String> = cast Reflect.field(sourceLine, 'characters');
			var role:String = Reflect.field(sourceLine, 'role');
			var type:Null<Int> = Reflect.field(sourceLine, 'type');
			var position:Null<String> = Reflect.field(sourceLine, 'position');
			var defaultLinePos = CodenameStrumlineLayout.defaultLinePosition(type);
			var keyCount = Std.int(lineNumber(Reflect.field(sourceLine, 'keyCount'), 4));
			if (keyCount <= 0) keyCount = 4;
			var strumLinePos = lineNumber(Reflect.field(sourceLine, 'strumLinePos'), defaultLinePos);
			if (!Math.isFinite(strumLinePos)) strumLinePos = defaultLinePos;
			var strumScale = lineNumber(Reflect.field(sourceLine, 'strumScale'), 1);
			if (!Math.isFinite(strumScale) || strumScale <= 0) strumScale = 1;
			var strumSpacing = lineNumber(Reflect.field(sourceLine, 'strumSpacing'), 1);
			if (!Math.isFinite(strumSpacing) || strumSpacing <= 0) strumSpacing = 1;
			var strumPos:Array<Float> = [0, 50];
			var rawStrumPos:Dynamic = Reflect.field(sourceLine, 'strumPos');
			if (Std.isOfType(rawStrumPos, Array)) {
				var authoredPos:Array<Dynamic> = cast rawStrumPos;
				if (authoredPos.length >= 2) {
					var posX = lineNumber(authoredPos[0], Math.NaN);
					var posY = lineNumber(authoredPos[1], Math.NaN);
					if (Math.isFinite(posX) && Math.isFinite(posY)) strumPos = [posX, posY];
				}
			}
			var line:Dynamic = {role:role, type:type, position:position,
				visible:Reflect.field(sourceLine, 'visible') != false, characters:ids.copy(),
				keyCount:keyCount, strumLinePos:strumLinePos, strumPos:strumPos,
				strumScale:strumScale, strumSpacing:strumSpacing};
			lines.push(line);
			ids = cast Reflect.field(line, 'characters');
			for (k in 0...ids.length) {
				var id = ids[k];
				var mappedName:Null<String> = Reflect.field(names, id);
				var sourceFallbackId:Null<String> = null;
				if (missingIds.exists(id)
					&& CodenameScriptDiscovery.safeRelativeName(missingCharacterFallback)
					&& missingCharacterFallback.toLowerCase() != id.toLowerCase()) {
					if (mappedName == null) mappedName = missingCharacterFallback;
					// New imports already map missing XML to DEFAULT_CHARACTER.
					// Retain the authored identity marker for those records too.
					if (mappedName == missingCharacterFallback)
						sourceFallbackId = missingCharacterFallback;
				}
				var nativePrimary = ['player', 'opponent', 'gf'].indexOf(role) >= 0
					&& !primary.exists(role);
				var allowXmlPlacement = staticXmlPlacementForExtras && !nativePrimary;
				var record:CodenameActorOccurrence = {lineIndex:i, occurrenceIndex:k,
					authoredId:id, nativeName:mappedName, sourceFallbackId:sourceFallbackId,
					role:role, nativePrimary:nativePrimary,
					lineType:type, positionName:position,
					placement:CodenameStagePlacement.select(placement, id, type, position, k,
						allowXmlPlacement)};
				occurrences.push(record);
				if (!primary.exists(role)) primary.set(role, record);
			}
		}
	}

	static function lineNumber(value:Dynamic, fallback:Float):Float {
		var number = if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			(cast value:Float) else if (Std.isOfType(value, String))
			Std.parseFloat(StringTools.trim(cast value)) else Math.NaN;
		return Math.isFinite(number) ? number : fallback;
	}

	/** Match the converter's first nonempty occurrence by its live fallback host
	 * or, only for an explicit missing-XML fallback, its exact authored ID. */
	public function primaryFor(role:String, nativeName:String):CodenameActorOccurrence {
		var record = primary.get(role);
		return primaryIdentityMatches(role, nativeName)
			? record : null;
	}

	/** The chart can still carry the authored id while its missing-XML visual is
	 * hosted by DEFAULT_CHARACTER. Accept either exact identity for that one
	 * marked occurrence; ordinary mappings stay exact-native only. */
	public function primaryIdentityMatches(role:String, characterName:String):Bool {
		var record = primary.get(role);
		return record != null && ((record.nativeName != null && record.nativeName == characterName)
			|| (record.sourceFallbackId != null && record.authoredId == characterName));
	}

	/** Apply the verified extra-actor exception to the active stage model only
	 * when its sole unresolved dependency is the same direct stage-script marker. */
	public function selectStagePlacement(data:CodenameStagePlacement.CodenameStagePlacementData,
		occurrence:CodenameActorOccurrence):CodenameStagePlacement.CodenameStageOccurrence {
		if (occurrence == null) throw 'Missing Codename actor occurrence';
		return CodenameStagePlacement.select(data, occurrence.authoredId,
			occurrence.lineType, occurrence.positionName, occurrence.occurrenceIndex,
			staticXmlPlacementForExtras && !occurrence.nativePrimary);
	}
}
