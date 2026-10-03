package;

import tjson.TJSON;

typedef ImportRegistryRefreshResult = {
	var text:String;
	var conflicts:Array<String>;
}

private typedef ImportRegistryValue = {
	var exists:Bool;
	var value:Dynamic;
}

/** Three-way JSON/JSONC reconciliation for shared engine registries. */
class ImportRegistryRefresh {
	/**
	 * Remove only the prior generated contribution, leaving unrelated live
	 * values intact. A live value that has diverged from the prior generated
	 * value is preserved and reported as a conflict.
	 */
	public static function prepare(beforeText:String, previousGenerated:String, live:String):ImportRegistryRefreshResult {
		return reconcile(previousGenerated, beforeText, live, true);
	}

	/**
	 * Apply changed generated values on top of live registry content. Changed
	 * leaves are written only when live still matches the baseline; identical
	 * generated values are already applied, and divergent live edits conflict.
	 */
	public static function merge(beforeText:String, generated:String, live:String):ImportRegistryRefreshResult {
		return reconcile(beforeText, generated, live, false);
	}

	static function reconcile(baseText:String, desiredText:String, liveText:String,
		preparing:Bool):ImportRegistryRefreshResult {
		if (baseText == null || desiredText == null || liveText == null)
			return {text: liveText == null ? "" : liveText, conflicts: ["$: registry text is missing"]};
		var base:Dynamic;
		var desired:Dynamic;
		var live:Dynamic;
		try {
			base = TJSON.parse(baseText, "import registry baseline");
			desired = TJSON.parse(desiredText, "generated import registry");
			live = TJSON.parse(liveText, "live import registry");
		} catch (error:Dynamic) {
			return {text: liveText, conflicts: ["$: could not parse JSON/JSONC: " + Std.string(error)]};
		}

		var conflicts:Array<String> = [];
		var result = reconcileValue(present(base), present(desired), present(live), "$", preparing, conflicts);
		if (!result.exists)
			return {text: liveText, conflicts: conflicts.length == 0 ? ["$: registry root cannot be removed"] : conflicts};
		if (deepEqual(result.value, live)) return {text: liveText, conflicts: conflicts};
		try {
			return {text: TJSON.encode(result.value, "fancy") + "\n", conflicts: conflicts};
		} catch (error:Dynamic) {
			return {text: liveText, conflicts: conflicts.concat(["$: could not encode merged registry: " + Std.string(error)])};
		}
	}

	static function reconcileValue(base:ImportRegistryValue, desired:ImportRegistryValue, live:ImportRegistryValue,
		path:String, preparing:Bool, conflicts:Array<String>):ImportRegistryValue {
		if (valuesEqual(base, desired)) return cloneValue(live);
		if (preparing && valuesEqual(live, desired)) {
			conflicts.push(path + ": local deletion or reversion matches the original registry; preserving it");
			return cloneValue(live);
		}
		if (valuesEqual(live, base)) return cloneValue(desired);
		if (valuesEqual(live, desired)) return cloneValue(live);

		if (isObjectPair(base, desired)) {
			if (live.exists && !isObject(live.value)) {
				conflicts.push(path + ": live value changed type; preserving it");
				return cloneValue(live);
			}
			if (!live.exists && base.exists && desired.exists) {
				conflicts.push(path + ": locally deleted object conflicts with importer changes; preserving deletion");
				return cloneValue(live);
			}
			var output:Dynamic = {};
			var keys = unionObjectFields(base, desired, live);
			for (key in keys) {
				var beforeField = objectField(base, key);
				var desiredField = objectField(desired, key);
				var liveField = objectField(live, key);
				var merged = reconcileValue(beforeField, desiredField, liveField,
					path == "$" ? key : path + "." + key, preparing, conflicts);
				if (merged.exists) Reflect.setField(output, key, merged.value);
			}
			if (!desired.exists && Reflect.fields(output).length == 0) return absent();
			return present(output);
		}

		if (base.exists && desired.exists && live.exists
			&& isArray(base.value) && isArray(desired.value) && isArray(live.value)) {
			if (isAppendRemoveArrayDelta(base.value, desired.value) && isPrimitiveUniqueArray(live.value))
				return present(reconcilePrimitiveArray(base.value, desired.value, live.value, path, preparing, conflicts));
			var identity = objectArrayIdentity(base.value, desired.value, live.value);
			if (identity != null && !objectArrayWasReordered(base.value, desired.value, identity))
				return present(reconcileObjectArray(base.value, desired.value, live.value, identity, path, preparing, conflicts));
		}

		conflicts.push(path + ": live value differs from both the baseline and generated value; preserving it");
		return cloneValue(live);
	}

	static function reconcilePrimitiveArray(base:Array<Dynamic>, desired:Array<Dynamic>, live:Array<Dynamic>,
		path:String, preparing:Bool, conflicts:Array<String>):Array<Dynamic> {
		var output:Array<Dynamic> = [];
		for (value in live) output.push(cloneDynamic(value));
		var removed:Array<Dynamic> = [];
		var added:Array<Dynamic> = [];
		for (value in base) if (!containsValue(desired, value)) removed.push(value);
		for (value in desired) if (!containsValue(base, value)) added.push(value);

		for (value in removed) removeFirst(output, value);
		if (added.length > 0) {
			for (value in base) {
				if (containsValue(desired, value) && !containsValue(live, value)) {
					conflicts.push(path + ": locally deleted array item " + Std.string(value) + "; preserving deletion");
				}
			}
		}
		for (value in added) {
			if (!containsValue(output, value)) insertByTargetOrder(output, value, desired, base);
		}
		return output;
	}

	static function reconcileObjectArray(base:Array<Dynamic>, desired:Array<Dynamic>, live:Array<Dynamic>, identity:String,
		path:String, preparing:Bool, conflicts:Array<String>):Array<Dynamic> {
		var output:Array<Dynamic> = [];
		for (entry in live) output.push(cloneDynamic(entry));
		var baseIds = objectArrayIds(base, identity);
		var desiredIds = objectArrayIds(desired, identity);

		for (baseEntry in base) {
			var id = identityValue(baseEntry, identity);
			var baseIndex = indexOfIdentity(output, identity, id);
			var desiredIndex = indexOfIdentity(desired, identity, id);
			if (desiredIndex < 0) {
				if (baseIndex >= 0) {
					if (preparing) {
						var entryPath = path + "[" + identity + "=" + Std.string(id) + "]";
						var remainder = subtractGeneratedEntry(baseEntry, output[baseIndex], entryPath, identity, conflicts);
						if (remainder.exists) output[baseIndex] = remainder.value;
						else output.splice(baseIndex, 1);
					} else if (deepEqual(output[baseIndex], baseEntry)) output.splice(baseIndex, 1);
					else conflicts.push(path + "[" + identity + "=" + Std.string(id) + "]: locally edited removed entry; preserving it");
				} else if (preparing) conflicts.push(path + "[" + identity + "=" + Std.string(id) + "]: locally deleted removed entry; preserving deletion");
				continue;
			}

			var desiredEntry = desired[desiredIndex];
			if (baseIndex < 0) {
				if (!deepEqual(baseEntry, desiredEntry))
					conflicts.push(path + "[" + identity + "=" + Std.string(id) + "]: locally deleted changed entry; preserving deletion");
				continue;
			}
			var entryPath = path + "[" + identity + "=" + Std.string(id) + "]";
			var reconciled = reconcileValue(present(baseEntry), present(desiredEntry), present(output[baseIndex]),
				entryPath, preparing, conflicts);
			if (reconciled.exists) output[baseIndex] = reconciled.value;
			else output.splice(baseIndex, 1);
		}

		for (desiredEntry in desired) {
			var id = identityValue(desiredEntry, identity);
			if (indexOfIdentity(base, identity, id) >= 0) continue;
			var liveIndex = indexOfIdentity(output, identity, id);
			var entryPath = path + "[" + identity + "=" + Std.string(id) + "]";
			if (liveIndex >= 0) {
				var reconciled = reconcileValue(absent(), present(desiredEntry), present(output[liveIndex]),
					entryPath, preparing, conflicts);
				if (reconciled.exists) output[liveIndex] = reconciled.value;
				else output.splice(liveIndex, 1);
			} else {
				insertObjectByTargetOrder(output, desiredEntry, identity, desiredIds, baseIds);
			}
		}
		return output;
	}

	/**
	 * Remove a generated keyed entry while preserving foreign nested additions.
	 * Unchanged fields act as the container header and stay when another value
	 * remains. Diverged fields are user edits, so keep them and report conflicts.
	 */
	static function subtractGeneratedEntry(base:Dynamic, live:Dynamic, path:String, identity:Null<String>,
		conflicts:Array<String>):ImportRegistryValue {
		if (deepEqual(base, live)) return absent();

		if (isObject(base) && isObject(live)) {
			var output:Dynamic = {};
			var unchanged:Array<String> = [];
			for (field in Reflect.fields(live)) {
				if (!Reflect.hasField(base, field)) {
					Reflect.setField(output, field, cloneDynamic(Reflect.field(live, field)));
					conflicts.push(path + "." + field + ": locally added field under removed entry; preserving it");
					continue;
				}

				var baseField = Reflect.field(base, field);
				var liveField = Reflect.field(live, field);
				if (deepEqual(baseField, liveField)) {
					unchanged.push(field);
					continue;
				}

				if ((isObject(baseField) && isObject(liveField)) || (isArray(baseField) && isArray(liveField))) {
					var remainder = subtractGeneratedValue(baseField, liveField, path + "." + field, null, conflicts);
					if (remainder.exists) Reflect.setField(output, field, remainder.value);
				} else {
					conflicts.push(path + "." + field + ": locally edited generated value; preserving it");
					Reflect.setField(output, field, cloneDynamic(liveField));
				}
			}

			if (Reflect.fields(output).length == 0) return absent();
			// Keep the old container header while foreign children or local edits remain.
			for (field in unchanged) Reflect.setField(output, field, cloneDynamic(Reflect.field(base, field)));
			if (identity != null && !Reflect.hasField(output, identity) && Reflect.hasField(live, identity))
				Reflect.setField(output, identity, cloneDynamic(Reflect.field(live, identity)));
			return present(output);
		}

		var value = subtractGeneratedValue(base, live, path, identity, conflicts);
		return value;
	}

	static function subtractGeneratedValue(base:Dynamic, live:Dynamic, path:String, identity:Null<String>,
		conflicts:Array<String>):ImportRegistryValue {
		if (deepEqual(base, live)) return absent();

		if (isArray(base) && isArray(live)) {
			var baseArray:Array<Dynamic> = cast base;
			var liveArray:Array<Dynamic> = cast live;
			if (isPrimitiveUniqueArray(baseArray) && isPrimitiveUniqueArray(liveArray)) {
				var retainedBase:Array<Dynamic> = [];
				var retainedLive:Array<Dynamic> = [];
				for (item in baseArray) if (containsValue(liveArray, item)) retainedBase.push(item);
				for (item in liveArray) if (containsValue(baseArray, item)) retainedLive.push(item);
				if (!arrayEqual(retainedBase, retainedLive)) {
					conflicts.push(path + ": locally reordered generated array; preserving it");
					return present(cloneDynamic(liveArray));
				}
				for (item in baseArray) if (!containsValue(liveArray, item))
					conflicts.push(path + ": locally deleted generated array item " + Std.string(item) + "; preserving deletion");
				var remainder:Array<Dynamic> = [];
				for (item in liveArray) if (!containsValue(baseArray, item)) remainder.push(cloneDynamic(item));
				return remainder.length == 0 ? absent() : present(remainder);
			}

			var arrayIdentity = objectArrayIdentity(baseArray, liveArray, liveArray);
			if (arrayIdentity == null || objectArrayWasReordered(baseArray, liveArray, arrayIdentity)) {
				conflicts.push(path + ": cannot safely identify or order generated array entries; preserving it");
				return present(cloneDynamic(liveArray));
			}
			var output:Array<Dynamic> = [];
			for (liveEntry in liveArray) {
				var id = identityValue(liveEntry, arrayIdentity);
				var baseIndex = indexOfIdentity(baseArray, arrayIdentity, id);
				if (baseIndex < 0) {
					output.push(cloneDynamic(liveEntry));
					continue;
				}
				var entryPath = path + "[" + arrayIdentity + "=" + Std.string(id) + "]";
				var remainder = subtractGeneratedEntry(baseArray[baseIndex], liveEntry, entryPath, arrayIdentity, conflicts);
				if (remainder.exists) output.push(remainder.value);
			}
			for (baseEntry in baseArray) {
				var id = identityValue(baseEntry, arrayIdentity);
				if (indexOfIdentity(liveArray, arrayIdentity, id) < 0)
					conflicts.push(path + "[" + arrayIdentity + "=" + Std.string(id) + "]: locally deleted generated child; preserving deletion");
			}
			return output.length == 0 ? absent() : present(output);
		}

		if (isObject(base) && isObject(live))
			return subtractGeneratedEntry(base, live, path, identity, conflicts);

		conflicts.push(path + ": locally edited generated value; preserving it");
		return present(cloneDynamic(live));
	}

	static function insertObjectByTargetOrder(output:Array<Dynamic>, entry:Dynamic, identity:String,
		desiredIds:Array<Dynamic>, baseIds:Array<Dynamic>):Void {
		var id = identityValue(entry, identity);
		var targetIndex = indexOfValue(desiredIds, id);
		for (index in (targetIndex + 1)...desiredIds.length) {
			var next = indexOfIdentity(output, identity, desiredIds[index]);
			if (next >= 0) {
				output.insert(next, cloneDynamic(entry));
				return;
			}
		}
		for (index in 0...output.length) {
			var currentId = identityValue(output[index], identity);
			if (!containsValue(baseIds, currentId) && !containsValue(desiredIds, currentId)) {
				output.insert(index, cloneDynamic(entry));
				return;
			}
		}
		output.push(cloneDynamic(entry));
	}

	static function objectArrayIdentity(base:Array<Dynamic>, desired:Array<Dynamic>, live:Array<Dynamic>):Null<String> {
		var candidates = ["name", "id", "namespace", "root", "key"];
		for (candidate in candidates) {
			if (objectArrayHasUniqueIdentity(base, candidate) && objectArrayHasUniqueIdentity(desired, candidate)
				&& objectArrayHasUniqueIdentity(live, candidate)) return candidate;
		}
		return null;
	}

	static function objectArrayHasUniqueIdentity(values:Array<Dynamic>, identity:String):Bool {
		for (index in 0...values.length) {
			var value = values[index];
			if (!isObject(value) || !Reflect.hasField(value, identity)) return false;
			var id = Reflect.field(value, identity);
			if (!isIdentityValue(id)) return false;
			for (other in 0...index) if (deepEqual(identityValue(values[other], identity), id)) return false;
		}
		return true;
	}

	static function objectArrayWasReordered(base:Array<Dynamic>, desired:Array<Dynamic>, identity:String):Bool {
		var baseRetained:Array<Dynamic> = [];
		var desiredRetained:Array<Dynamic> = [];
		for (entry in base) {
			var id = identityValue(entry, identity);
			if (indexOfIdentity(desired, identity, id) >= 0) baseRetained.push(id);
		}
		for (entry in desired) {
			var id = identityValue(entry, identity);
			if (indexOfIdentity(base, identity, id) >= 0) desiredRetained.push(id);
		}
		return !arrayEqual(baseRetained, desiredRetained);
	}

	static function objectArrayIds(values:Array<Dynamic>, identity:String):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		for (entry in values) result.push(cloneDynamic(identityValue(entry, identity)));
		return result;
	}

	static function indexOfIdentity(values:Array<Dynamic>, identity:String, id:Dynamic):Int {
		for (index in 0...values.length) {
			if (isObject(values[index]) && Reflect.hasField(values[index], identity)
				&& deepEqual(Reflect.field(values[index], identity), id)) return index;
		}
		return -1;
	}

	static function identityValue(value:Dynamic, identity:String):Dynamic return Reflect.field(value, identity);

	static function isIdentityValue(value:Dynamic):Bool {
		return value != null && (Std.isOfType(value, String) || isNumber(value));
	}

	/** Recognize only ordered primitive array appends/removals; reorder and object arrays stay atomic. */
	static function isAppendRemoveArrayDelta(base:Array<Dynamic>, desired:Array<Dynamic>):Bool {
		if (!isPrimitiveUniqueArray(base) || !isPrimitiveUniqueArray(desired)) return false;
		var retained:Array<Dynamic> = [];
		for (value in base) if (containsValue(desired, value)) retained.push(value);
		var targetRetained:Array<Dynamic> = [];
		var additions:Array<Dynamic> = [];
		for (value in desired) {
			if (containsValue(base, value)) targetRetained.push(value);
			else additions.push(value);
		}
		if (!arrayEqual(retained, targetRetained)) return false;
		var expected = retained.concat(additions);
		return arrayEqual(expected, desired);
	}

	static function insertByTargetOrder(output:Array<Dynamic>, value:Dynamic, desired:Array<Dynamic>, base:Array<Dynamic>):Void {
		var targetIndex = indexOfValue(desired, value);
		for (index in (targetIndex + 1)...desired.length) {
			var next = indexOfValue(output, desired[index]);
			if (next >= 0) {
				output.insert(next, cloneDynamic(value));
				return;
			}
		}
		for (index in 0...output.length) {
			if (!containsValue(base, output[index])) {
				output.insert(index, cloneDynamic(value));
				return;
			}
		}
		output.push(cloneDynamic(value));
	}

	static function removeFirst(values:Array<Dynamic>, target:Dynamic):Void {
		var index = indexOfValue(values, target);
		if (index >= 0) values.splice(index, 1);
	}

	static function containsValue(values:Array<Dynamic>, target:Dynamic):Bool return indexOfValue(values, target) >= 0;

	static function indexOfValue(values:Array<Dynamic>, target:Dynamic):Int {
		for (index in 0...values.length) if (deepEqual(values[index], target)) return index;
		return -1;
	}

	static function isPrimitiveUniqueArray(values:Array<Dynamic>):Bool {
		for (index in 0...values.length) {
			if (!isPrimitive(values[index])) return false;
			for (other in 0...index) if (deepEqual(values[index], values[other])) return false;
		}
		return true;
	}

	static function isPrimitive(value:Dynamic):Bool {
		return value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool) || isNumber(value);
	}

	static function isNumber(value:Dynamic):Bool {
		return switch (Type.typeof(value)) {
			case TInt, TFloat: true;
			default: false;
		};
	}

	static function isObjectPair(base:ImportRegistryValue, desired:ImportRegistryValue):Bool {
		return (!base.exists || isObject(base.value)) && (!desired.exists || isObject(desired.value))
			&& (base.exists || desired.exists);
	}

	static function isObject(value:Dynamic):Bool {
		if (value == null) return false;
		return switch (Type.typeof(value)) {
			case TObject: true;
			default: false;
		};
	}

	static function unionObjectFields(base:ImportRegistryValue, desired:ImportRegistryValue,
		live:ImportRegistryValue):Array<String> {
		var fields:Array<String> = [];
		var seen:Map<String, Bool> = new Map();
		for (source in [live, desired, base]) {
			if (!source.exists || !isObject(source.value)) continue;
			for (field in Reflect.fields(source.value)) {
				if (!seen.exists(field)) {
					seen.set(field, true);
					fields.push(field);
				}
			}
		}
		return fields;
	}

	static function objectField(value:ImportRegistryValue, key:String):ImportRegistryValue {
		if (!value.exists || !isObject(value.value) || !Reflect.hasField(value.value, key)) return absent();
		return present(Reflect.field(value.value, key));
	}

	static function valuesEqual(first:ImportRegistryValue, second:ImportRegistryValue):Bool {
		return first.exists == second.exists && (!first.exists || deepEqual(first.value, second.value));
	}

	static function deepEqual(first:Dynamic, second:Dynamic):Bool {
		if (first == null || second == null) return first == second;
		if ((Std.isOfType(first, String) || Std.isOfType(second, String)))
			return Std.isOfType(first, String) && Std.isOfType(second, String) && (cast first:String) == (cast second:String);
		if ((Std.isOfType(first, Bool) || Std.isOfType(second, Bool)))
			return Std.isOfType(first, Bool) && Std.isOfType(second, Bool) && (cast first:Bool) == (cast second:Bool);
		if (isNumber(first) || isNumber(second))
			return isNumber(first) && isNumber(second) && (cast first:Float) == (cast second:Float);
		if (isArray(first) && isArray(second)) return arrayEqual(cast first, cast second);
		if (isObject(first) || isObject(second)) {
			if (!isObject(first) || !isObject(second)) return false;
			var firstFields = Reflect.fields(first);
			var secondFields = Reflect.fields(second);
			if (firstFields.length != secondFields.length) return false;
			for (field in firstFields) {
				if (!Reflect.hasField(second, field) || !deepEqual(Reflect.field(first, field), Reflect.field(second, field)))
					return false;
			}
			return true;
		}
		return false;
	}

	static function arrayEqual(first:Array<Dynamic>, second:Array<Dynamic>):Bool {
		if (first.length != second.length) return false;
		for (index in 0...first.length) if (!deepEqual(first[index], second[index])) return false;
		return true;
	}

	static function cloneValue(value:ImportRegistryValue):ImportRegistryValue {
		return value.exists ? present(cloneDynamic(value.value)) : absent();
	}

	static function cloneDynamic(value:Dynamic):Dynamic {
		if (isArray(value)) {
			var result:Array<Dynamic> = [];
			for (entry in (cast value:Array<Dynamic>)) result.push(cloneDynamic(entry));
			return result;
		}
		if (isObject(value)) {
			var result:Dynamic = {};
			for (field in Reflect.fields(value)) Reflect.setField(result, field, cloneDynamic(Reflect.field(value, field)));
			return result;
		}
		return value;
	}

	static function isArray(value:Dynamic):Bool return value != null && Std.isOfType(value, Array);

	static inline function present(value:Dynamic):ImportRegistryValue return {exists: true, value: value};
	static inline function absent():ImportRegistryValue return {exists: false, value: null};
}
