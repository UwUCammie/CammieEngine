package;

/** One-shot prompt ownership tied to the selection that armed it. */
class SelectionActionGate {
	var ownerKey:String = '';
	var ownerGeneration:Int = -1;
	var ownerToken:Int = 0;
	var nextToken:Int = 0;

	public function new() {}

	public function arm(selectionKey:String):Bool {
		return armFor(selectionKey, 0) != 0;
	}

	/** Arm a one-shot action for one concrete selection generation. */
	public function armFor(selectionKey:String, generation:Int):Int {
		if (selectionKey == null || StringTools.trim(selectionKey) == '') {
			clear();
			return 0;
		}
		ownerKey = selectionKey.toLowerCase();
		ownerGeneration = generation;
		nextToken++;
		if (nextToken <= 0)
			nextToken = 1;
		ownerToken = nextToken;
		return ownerToken;
	}

	public function consume(selectionKey:String):Bool {
		var matches = isArmedFor(selectionKey);
		clear();
		return matches;
	}

	/** Consume only if both the selected item and its generation still match. */
	public function consumeFor(selectionKey:String, generation:Int, token:Int):Bool {
		var matches = ownerToken != 0 && token != 0 && token == ownerToken
			&& ownerGeneration == generation && isArmedFor(selectionKey);
		clear();
		return matches;
	}

	public function isArmedFor(selectionKey:String):Bool {
		return ownerKey != '' && selectionKey != null
			&& ownerKey == StringTools.trim(selectionKey).toLowerCase();
	}

	public function clear():Void {
		ownerKey = '';
		ownerGeneration = -1;
		ownerToken = 0;
	}
}
