package;

import flixel.util.FlxSignal.FlxTypedSignal;

/**
	Small script-facing collection for live Nightmare Vision field views.
	Implemented mutations follow unbounded FlxTypedGroup semantics; native lines remain owned by
	PlayState through attachment hooks. This collection never updates, draws,
	kills or destroys native receptor banks.
*/
@:keep
class NightmareVisionPlayFields {
	@:keep public var members:Array<NightmareVisionPlayFieldView> = [];
	public var length(get, never):Int;
	var logicalLength:Int = 0;
	public var memberAdded(get, never):FlxTypedSignal<NightmareVisionPlayFieldView->Void>;
	public var memberRemoved(get, never):FlxTypedSignal<NightmareVisionPlayFieldView->Void>;
	var added:FlxTypedSignal<NightmareVisionPlayFieldView->Void>;
	var removed:FlxTypedSignal<NightmareVisionPlayFieldView->Void>;
	var nativeAdd:NightmareVisionPlayFieldView->Void;
	var nativeRemove:NightmareVisionPlayFieldView->Void;
	var nativeChanged:Void->Void;

	public function new(?onAdd:NightmareVisionPlayFieldView->Void,
		?onRemove:NightmareVisionPlayFieldView->Void, ?onChanged:Void->Void) {
		setNativeHooks(onAdd, onRemove, onChanged);
	}
	public function setNativeHooks(?onAdd:NightmareVisionPlayFieldView->Void,
		?onRemove:NightmareVisionPlayFieldView->Void, ?onChanged:Void->Void):Void {
		nativeAdd = onAdd; nativeRemove = onRemove; nativeChanged = onChanged;
	}

	function get_length():Int return logicalLength;

	@:keep public function add(field:NightmareVisionPlayFieldView):NightmareVisionPlayFieldView {
		if (field == null || members.indexOf(field) >= 0) return field;
		var hole = members.indexOf(null);
		if (hole >= 0) {
			members[hole] = field;
			if (hole >= logicalLength) logicalLength = hole + 1;
		} else { members.push(field); logicalLength++; }
		if (nativeAdd != null) nativeAdd(field);
		if (added != null) added.dispatch(field);
		changed();
		return field;
	}
	@:keep public function insert(position:Int, field:NightmareVisionPlayFieldView):NightmareVisionPlayFieldView {
		if (field == null || members.indexOf(field) >= 0) return field;
		if (position < logicalLength && members[position] == null) members[position] = field;
		else { members.insert(position, field); logicalLength++; }
		if (nativeAdd != null) nativeAdd(field);
		if (added != null) added.dispatch(field);
		changed();
		return field;
	}
	@:keep public function remove(field:NightmareVisionPlayFieldView, splice:Bool = false):NightmareVisionPlayFieldView {
		if (members == null) return null;
		var index = members.indexOf(field);
		if (index < 0) return null;
		if (splice) { members.splice(index, 1); logicalLength--; } else members[index] = null;
		if (field != null && nativeRemove != null) nativeRemove(field);
		if (removed != null) removed.dispatch(field);
		changed();
		return field;
	}
	@:keep public function replace(oldField:NightmareVisionPlayFieldView,
		newField:NightmareVisionPlayFieldView):NightmareVisionPlayFieldView {
		var index = members.indexOf(oldField);
		if (index < 0) return null;
		members[index] = newField;
		if (oldField != null && nativeRemove != null) nativeRemove(oldField);
		if (newField != null && nativeAdd != null) nativeAdd(newField);
		if (removed != null) removed.dispatch(oldField);
		if (added != null) added.dispatch(newField);
		changed();
		return newField;
	}
	@:keep public function clear():Void {
		// FlxTypedGroup exposes zero logical length while removal listeners still
		// see the old live member array. Clearing never kills/destroys its members.
		logicalLength = 0;
		for (field in members) {
			if (field != null && nativeRemove != null) nativeRemove(field);
			if (removed != null) removed.dispatch(field);
		}
		members.resize(0);
		changed();
	}

	function changed():Void if (nativeChanged != null) nativeChanged();
	function get_memberAdded():FlxTypedSignal<NightmareVisionPlayFieldView->Void> {
		if (added == null) added = new FlxTypedSignal<NightmareVisionPlayFieldView->Void>();
		return added;
	}
	function get_memberRemoved():FlxTypedSignal<NightmareVisionPlayFieldView->Void> {
		if (removed == null) removed = new FlxTypedSignal<NightmareVisionPlayFieldView->Void>();
		return removed;
	}
	/** Release the facade only; the host still owns every native bank. */
	public function destroy():Void {
		var previous = members == null ? [] : members.copy();
		// Collection destruction must notify the host before its hook is cleared,
		// otherwise the display state keeps drawing banks whose facade is gone.
		clear();
		if (added != null) { added.removeAll(); added.destroy(); added = null; }
		if (removed != null) { removed.removeAll(); removed.destroy(); removed = null; }
		setNativeHooks();
		for (field in previous) if (field != null) field.destroy();
	}

	/** Match the source lookup: mutable field IDs take precedence over array order. */
	@:keep public function getFieldFromID(id:Int):NightmareVisionPlayFieldView {
		for (field in members)
			if (field != null && field.ID == id) return field;
		return id >= 0 && id < members.length ? members[id] : null;
	}

	@:keep public function iterator():Iterator<NightmareVisionPlayFieldView>
		return members.iterator();
}
