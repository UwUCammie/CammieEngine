package;

/** One line of the modifiers panel. */
typedef ModifierRow = {
	/** 'start', 'characters', 'header', 'modifier' or 'reset'. */
	var kind:String;
	/** Section title for a header, modifier id for a modifier. */
	var id:String;
}

/** The modifiers panel as plain data: which lines it shows in which order, which
 * of them the cursor can land on, and which slice is on screen. No display
 * objects, so it is tested on its own. */
class ModifierMenuRows {
	/** Optional Start song and Choose characters lines, then each group's header and modifiers, then Reset all. */
	public static function build(withStart:Bool, withCharacters:Bool, groups:Array<String>, modifierGroup:Array<String>, modifierIds:Array<String>):Array<ModifierRow> {
		var rows:Array<ModifierRow> = [];
		if (withStart)
			rows.push({kind: 'start', id: ''});
		if (withCharacters)
			rows.push({kind: 'characters', id: ''});
		for (group in groups) {
			var first = true;
			for (index in 0...modifierIds.length) {
				if (modifierGroup[index] != group)
					continue;
				if (first) {
					rows.push({kind: 'header', id: group});
					first = false;
				}
				rows.push({kind: 'modifier', id: modifierIds[index]});
			}
		}
		rows.push({kind: 'reset', id: ''});
		return rows;
	}

	public static function selectable(row:ModifierRow):Bool
		return row != null && row.kind != 'header';

	/** The next line the cursor can land on, wrapping, from `from` in direction `step`. */
	public static function move(rows:Array<ModifierRow>, from:Int, step:Int):Int {
		if (rows.length == 0)
			return 0;
		var index = from;
		for (_ in 0...rows.length) {
			index = (index + step + rows.length) % rows.length;
			if (selectable(rows[index]))
				return index;
		}
		return from;
	}

	/** First selectable line, the cursor's starting place. */
	public static function first(rows:Array<ModifierRow>):Int {
		for (index in 0...rows.length)
			if (selectable(rows[index]))
				return index;
		return 0;
	}

	/** First line on screen when `visible` lines fit, keeping the cursor away from the edges. */
	public static function firstVisible(selected:Int, count:Int, visible:Int):Int {
		if (count <= visible)
			return 0;
		var top = selected - Std.int(visible / 2);
		if (top < 0)
			top = 0;
		if (top > count - visible)
			top = count - visible;
		return top;
	}

	/** Right-hand value of a modifier line. */
	public static function valueLabel(on:Bool, amount:Null<Float>, defAmount:Null<Float>, precision:Null<Float>):String {
		if (amount == null)
			return on ? 'ON' : 'OFF';
		// Multipliers (default 1) read as "x1.5"; rates (default 0) as plain numbers.
		var text = Std.string(Math.round(amount * 100) / 100);
		return defAmount == 1 ? 'x' + text : text;
	}
}
