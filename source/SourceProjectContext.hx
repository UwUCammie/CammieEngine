package;

using StringTools;

/** Explicit tri-state build flag supplied by a verified import record. */
typedef SourceProjectContextFlag = {
	var name:String;
	/** One of enabled, disabled, or unresolved. */
	var state:String;
	@:optional var provenance:String;
}

/** Known string value supplied independently of flag presence. */
typedef SourceProjectContextValue = {
	var name:String;
	var value:String;
	@:optional var provenance:String;
}

/** Result of looking up a project-local define. Presence and string value are
 * separate because Lime can test a bare flag even when it has no value. */
typedef SourceProjectContextLookup = {
	/** enabled, disabled, or unresolved */
	var state:String;
	/** known, absent, or unresolved */
	var valueState:String;
	var hasValue:Bool;
	@:optional var value:String;
	var provenance:Array<String>;
}

typedef SourceProjectContextDiagnostic = {
	var code:String;
	var message:String;
	@:optional var name:String;
	@:optional var location:String;
}

/** String interpolation returns the partially expanded value for diagnostics;
 * callers must use state == "known" before using it as a path or value. */
typedef SourceProjectContextResolution = {
	/** known or unresolved */
	var state:String;
	var value:String;
	@:optional var boolValue:Bool;
	var diagnostics:Array<SourceProjectContextDiagnostic>;
}

/** Opaque compiler-only declaration retained for evidence, never a condition. */
typedef SourceProjectContextOpaque = {
	var operation:String;
	var name:String;
	@:optional var value:String;
	@:optional var provenance:String;
}

private typedef SourceProjectContextSymbol = {
	var state:String;
	var valueState:String;
	@:optional var value:String;
	var provenance:Array<String>;
}

/**
	Bounded, project-local subset of Lime's define and environment behavior.

	This class never reads or mutates the host process environment. Build flags
	carry tri-state presence; known string values are a separate input. Project
	assignments update only this context, and compiler-only haxedef declarations
	are recorded as opaque inputs rather than conditions.
*/
class SourceProjectContext {
	public static inline var MAX_NAME_LENGTH:Int = 256;
	public static inline var MAX_VALUE_LENGTH:Int = 16384;
	public static inline var MAX_EXPANSION_DEPTH:Int = 16;
	public static inline var MAX_EXPANSIONS:Int = 128;
	public static inline var MAX_DIAGNOSTICS:Int = 512;
	public static inline var MAX_PROVENANCE:Int = 64;

	public var diagnostics(default, null):Array<SourceProjectContextDiagnostic>;
	public var opaque(default, null):Array<SourceProjectContextOpaque>;
	public var flagsComplete(default, null):Bool;
	/** Lime's command token is independent of define presence and must be supplied explicitly. */
	public var command(default, null):Null<String>;

	var symbols:Map<String, SourceProjectContextSymbol>;
	var diagnosticLimitReported:Bool = false;

	public function new(?flags:Array<SourceProjectContextFlag>, ?values:Array<SourceProjectContextValue>,
		flagsComplete:Bool = false, ?command:String) {
		symbols = new Map();
		diagnostics = [];
		opaque = [];
		this.flagsComplete = flagsComplete;
		this.command = command;
		if (flags != null) for (flag in flags) seedFlag(flag);
		if (values != null) for (value in values) seedValue(value);
	}

	public static function seed(flags:Array<SourceProjectContextFlag>,
		values:Array<SourceProjectContextValue>, flagsComplete:Bool = false,
		?command:String):SourceProjectContext {
		return new SourceProjectContext(flags, values, flagsComplete, command);
	}

	/** A child parse receives a deep copy of the current project-local defines. */
	public function clone():SourceProjectContext {
		var copy = new SourceProjectContext(null, null, flagsComplete, command);
		for (name in symbols.keys()) copy.symbols.set(name, cloneSymbol(symbols.get(name)));
		return copy;
	}

	/**
		Apply one ordered Lime-local define/environment operation. `set`, `define`,
		and `setenv` all establish presence plus a string value. `setenv` defaults
		to "1" when no value is supplied; the other two default to the empty string.
		No operation changes Sys.environment or Sys.putEnv.
	*/
	public function apply(operation:String, name:String, ?value:String, ?provenance:String):Void {
		var op = operation == null ? "" : StringTools.trim(operation).toLowerCase();
		if (!validName(name)) {
			addDiagnostic("invalid-name", "A project define operation has an invalid name.", name, provenance);
			return;
		}
		switch (op) {
			case "set", "define", "setenv":
				var assigned = value == null ? (op == "setenv" ? "1" : "") : value;
				if (assigned.length > MAX_VALUE_LENGTH) {
					markValueUnresolved(name, provenance);
					addDiagnostic("value-limit", "A project-local value exceeds the size limit.", name, provenance);
					return;
				}
				var prior = symbols.get(name);
				var trail = prior == null ? [] : prior.provenance.copy();
				appendProvenance(trail, provenance);
				symbols.set(name, {
					state:"enabled", valueState:"known", value:assigned,
					provenance:trail
				});
			case "unset", "undefine":
				var prior = symbols.get(name);
				var trail = prior == null ? [] : prior.provenance.copy();
				appendProvenance(trail, provenance);
				symbols.set(name, {
					state:"disabled", valueState:"absent",
					provenance:trail
				});
				if (op == "undefine") recordOpaque("undefine-haxedef", name, null, provenance);
			case "haxedef":
				recordOpaque(op, name, value, provenance);
			default:
				addDiagnostic("unsupported-operation", "A project-local define operation is unsupported.", name, provenance);
		}
	}

	/** Mark both presence and value uncertain after an unresolved branch could
	 * have set, removed, or changed this name. Prior known values are discarded. */
	public function markUnresolved(name:String, ?provenance:String):Void {
		if (!validName(name)) {
			markAllUnresolved(provenance);
			return;
		}
		var prior = symbols.get(name);
		var trail = prior == null ? [] : prior.provenance.copy();
		appendProvenance(trail, provenance);
		symbols.set(name, {
			state:"unresolved", valueState:"unresolved",
			provenance:trail
		});
	}

	/** Preserve known define presence when only its value expression is unknown. */
	public function markValueUnresolved(name:String, ?provenance:String):Void {
		if (!validName(name)) {
			markAllUnresolved(provenance);
			return;
		}
		var symbol = symbols.get(name);
		if (symbol == null || symbol.state != "enabled") {
			markUnresolved(name, provenance);
			return;
		}
		symbol.valueState = "unresolved";
		symbol.value = null;
		appendProvenance(symbol.provenance, provenance);
	}

	/** An unresolved dynamic assignment name could affect any currently known
	 * symbol, so taint the bounded context rather than preserving stale values. */
	public function markAllUnresolved(?provenance:String):Void {
		for (name in symbols.keys()) markUnresolved(name, provenance);
		flagsComplete = false;
		addDiagnostic("context-tainted", "An unresolved project assignment could affect any known define.", null, provenance);
	}

	/** An include with unknown contents may introduce any previously absent
	 * define. Preserve known enabled values, but stop proving absent names. */
	public function markMissingUnresolved(?provenance:String):Void {
		flagsComplete = false;
		var absentNames:Array<String> = [];
		for (name in symbols.keys()) {
			var symbol = symbols.get(name);
			if (symbol != null && symbol.state == "disabled") absentNames.push(name);
		}
		for (name in absentNames) markUnresolved(name, provenance);
		addDiagnostic("include-context-unresolved",
			"An unavailable Project include may define names that were previously known absent.", null, provenance);
	}

	/** Look up flag presence and string value independently. Unlisted inputs are
	 * unresolved, not known absent, because the donor build context is incomplete. */
	public function lookup(name:String):SourceProjectContextLookup {
		var symbol = name == null ? null : symbols.get(name);
		if (symbol == null) return flagsComplete
			? {state:"disabled", valueState:"absent", hasValue:false, provenance:[]}
			: {state:"unresolved", valueState:"unresolved", hasValue:false, provenance:[]};
		return {
			state:symbol.state,
			valueState:symbol.valueState,
			hasValue:symbol.valueState == "known",
			value:symbol.valueState == "known" ? symbol.value : null,
			provenance:symbol.provenance.copy()
		};
	}

	/** Return effective, known string-valued defines in stable name order. */
	public function valuesSnapshot():Array<SourceProjectContextValue> {
		var result:Array<SourceProjectContextValue> = [];
		for (name in symbols.keys()) {
			var symbol = symbols.get(name);
			if (symbol == null || symbol.state != "enabled" || symbol.valueState != "known") continue;
			result.push({name:name, value:symbol.value == null ? "" : symbol.value,
				provenance:symbol.provenance == null ? "" : symbol.provenance.join(" | ")});
		}
		result.sort(function(left, right) return Reflect.compare(left.name, right.name));
		return result;
	}

	/** Safely expand `${NAME}` references and simple Lime string comparisons. */
	public function interpolate(input:String, ?location:String):SourceProjectContextResolution {
		var diagnosticStart = diagnostics.length;
		var result = expandText(input == null ? "" : input, location, [], {count:0}, 0);
		return resolution(result.state, result.value, diagnosticStart);
	}

	/**
		Evaluate Lime's bounded `if` / `unless` condition grammar.

		`if` splits raw text on `||` before interpolation. `unless` interpolates the
		whole string before splitting. Both then interpolate each clause and each
		space-delimited term. This preserves Lime's observable behavior when a
		`${VALUE}` contains a literal `||`.
	*/
	public function condition(ifValue:Null<String>, unlessValue:Null<String>,
		?location:String):SourceProjectContextResolution {
		var diagnosticStart = diagnostics.length;
		var ifState = ifValue == null ? "enabled" : evaluateIf(ifValue, location);
		if (ifState == "disabled") return resolution("known", "false", diagnosticStart, false);

		var unlessState = "disabled";
		if (unlessValue != null) {
			var whole = expandText(unlessValue, location, [], {count:0}, 0);
			if (whole.state != "known") unlessState = "unresolved";
			else {
				unlessState = evaluateOrClauses(whole.value.split("||"), location);
			}
		}
		if (unlessState == "enabled") return resolution("known", "false", diagnosticStart, false);
		if (ifState == "unresolved" || unlessState == "unresolved")
			return resolution("unresolved", "", diagnosticStart);
		return resolution("known", "true", diagnosticStart, true);
	}

	/** Apply Lime's HXProject.merge rule for define/environment maps: child keys
	 * only fill names that are known absent in the parent. Unknown parent presence
	 * remains unresolved instead of being overwritten by an included value. */
	public function mergeNonOverwriting(child:SourceProjectContext):Void {
		if (child == null || child == this) return;
		for (name in child.symbols.keys()) {
			var parent = symbols.get(name);
			if (parent != null && parent.state != "disabled") continue;
			if (parent == null && !flagsComplete) continue;
			symbols.set(name, cloneSymbol(child.symbols.get(name)));
		}
		if (!child.flagsComplete) flagsComplete = false;
		for (item in child.opaque) opaque.push(cloneOpaque(item));
		for (item in child.diagnostics) addDiagnostic(item.code, item.message, item.name, item.location);
	}

	/** Merge only uncertainty from an include whose execution is unresolved.
	 * Lime's project merge is add-only, so parent-enabled values remain stable;
	 * names known absent in the parent become uncertain if the child could add them. */
	public function mergeUnresolved(child:SourceProjectContext, ?provenance:String):Void {
		if (child == null || child == this) return;
		if (flagsComplete && !child.flagsComplete) markMissingUnresolved(provenance);
		for (name in child.symbols.keys()) {
			var childSymbol = child.symbols.get(name);
			if (childSymbol == null || childSymbol.state == "disabled") continue;
			var parent = symbols.get(name);
			if (parent != null && parent.state != "disabled") continue;
			if (parent == null && !flagsComplete) continue;
			var reason = provenance;
			if (reason == null && childSymbol.provenance != null && childSymbol.provenance.length > 0)
				reason = childSymbol.provenance[childSymbol.provenance.length - 1];
			markUnresolved(name, reason);
		}
		for (item in child.opaque) opaque.push(cloneOpaque(item));
		for (item in child.diagnostics) addDiagnostic(item.code, item.message, item.name, item.location);
	}

	function seedFlag(flag:SourceProjectContextFlag):Void {
		if (flag == null || !validName(flag.name)) {
			addDiagnostic("invalid-flag", "A build-context flag has an invalid name.", flag == null ? null : flag.name,
				flag == null ? null : flag.provenance);
			return;
		}
		var state = normalizeState(flag.state);
		var existing = symbols.get(flag.name);
		if (existing == null) {
			symbols.set(flag.name, {
				state:state,
				valueState:state == "disabled" ? "absent" : "unresolved",
				provenance:provenanceList(flag.provenance)
			});
			return;
		}
		if (existing.state != state) {
			markUnresolved(flag.name, flag.provenance);
			addDiagnostic("conflicting-flags", "Conflicting build-context flag states were supplied.", flag.name, flag.provenance);
		} else appendProvenance(existing.provenance, flag.provenance);
	}

	function seedValue(item:SourceProjectContextValue):Void {
		if (item == null || !validName(item.name) || item.value == null
			|| item.value.length > MAX_VALUE_LENGTH) {
			addDiagnostic("invalid-value", "A build-context string value is invalid or exceeds the size limit.",
				item == null ? null : item.name, item == null ? null : item.provenance);
			if (item != null && validName(item.name)) markValueUnresolved(item.name, item.provenance);
			return;
		}
		var existing = symbols.get(item.name);
		if (existing != null && (existing.state == "disabled" || existing.state == "unresolved")) {
			markUnresolved(item.name, item.provenance);
			addDiagnostic("value-flag-conflict", "A string value conflicts with a disabled or unresolved build flag.",
				item.name, item.provenance);
			return;
		}
		if (existing != null && existing.valueState == "known" && existing.value != item.value) {
			markUnresolved(item.name, item.provenance);
			addDiagnostic("conflicting-values", "Conflicting build-context string values were supplied.",
				item.name, item.provenance);
			return;
		}
		var trail = existing == null ? [] : existing.provenance.copy();
		appendProvenance(trail, item.provenance);
		symbols.set(item.name, {state:"enabled", valueState:"known", value:item.value, provenance:trail});
	}

	function evaluateIf(raw:String, ?location:String):String {
		return evaluateOrClauses(raw.split("||"), location);
	}

	function evaluateOrClauses(clauses:Array<String>, ?location:String):String {
		var result = "disabled";
		for (clause in clauses) {
			var current = evaluateAndTerms(clause, location);
			result = triOr(result, current);
			if (result == "enabled") return result;
		}
		return result;
	}

	function evaluateAndTerms(raw:String, ?location:String):String {
		var expanded = expandText(raw, location, [], {count:0}, 0);
		var result = expanded.state == "known" ? "enabled" : "unresolved";
		for (term in expanded.value.split(" ")) {
			var resolvedTerm = expandText(term, location, [], {count:0}, 0);
			var atom = resolvedTerm.state == "known"
				? conditionAtom(StringTools.trim(resolvedTerm.value), location)
				: "unresolved";
			result = triAnd(result, atom);
			if (result == "disabled") return result;
		}
		return result;
	}

	function conditionAtom(term:String, ?location:String):String {
		if (term == "" || term == "true") return "enabled";
		if (term == "false") return "disabled";
		if (command != null && term == command) return "enabled";
		var symbol = symbols.get(term);
		if (symbol == null) {
			if (command != null && flagsComplete) return "disabled";
			addDiagnostic("condition-unresolved", "A Project.xml condition depends on an uncaptured flag.", term, location);
			return "unresolved";
		}
		if (symbol.state == "unresolved") {
			addDiagnostic("condition-unresolved", "A Project.xml condition depends on an uncaptured flag.", term, location);
			return "unresolved";
		}
		if (symbol.state == "disabled" && command == null) {
			addDiagnostic("command-unresolved", "A Project.xml condition may match the uncaptured Lime command.", term, location);
			return "unresolved";
		}
		return symbol.state;
	}

	function expandText(input:String, ?location:String, stack:Array<String>,
		counter:{count:Int}, depth:Int):{state:String, value:String} {
		if (input.length > MAX_VALUE_LENGTH) {
			addDiagnostic("interpolation-size-limit", "A Project.xml expression exceeds the size limit.", null, location);
			return {state:"unresolved", value:input.substr(0, MAX_VALUE_LENGTH)};
		}
		if (depth > MAX_EXPANSION_DEPTH) {
			addDiagnostic("interpolation-depth-limit", "Project.xml variable expansion exceeded its depth limit.", null, location);
			return {state:"unresolved", value:input};
		}
		var current = input;
		var doublePattern = new EReg("\\$\\$\\{(.*?)}", "");
		var doubleSeen:Map<String, Bool> = new Map();
		doubleSeen.set(current, true);
		while (doublePattern.match(current)) {
			counter.count++;
			if (counter.count > MAX_EXPANSIONS) {
				addDiagnostic("interpolation-count-limit", "Project.xml variable expansion exceeded its count limit.", null, location);
				return {state:"unresolved", value:current};
			}
			var alias = doublePattern.matched(1);
			var position = doublePattern.matchedPos();
			var target = resolveExpression(alias, location, stack, counter, depth + 1);
			if (target.state != "known") return {state:"unresolved", value:current};
			current = current.substr(0, position.pos) + "${" + target.value + "}"
				+ current.substr(position.pos + position.len);
			if (doubleSeen.exists(current)) {
				addDiagnostic("variable-cycle", "Project.xml double-variable substitution contains a cycle.", alias, location);
				return {state:"unresolved", value:current};
			}
			doubleSeen.set(current, true);
			if (current.length > MAX_VALUE_LENGTH) {
				addDiagnostic("interpolation-size-limit", "Expanded Project.xml text exceeds the size limit.", null, location);
				return {state:"unresolved", value:current.substr(0, MAX_VALUE_LENGTH)};
			}
		}
		var pattern = new EReg("\\$\\{(.*?)}", "");
		var valueSeen:Map<String, Bool> = new Map();
		valueSeen.set(current, true);
		while (pattern.match(current)) {
			counter.count++;
			if (counter.count > MAX_EXPANSIONS) {
				addDiagnostic("interpolation-count-limit", "Project.xml variable expansion exceeded its count limit.", null, location);
				return {state:"unresolved", value:current};
			}
			var expression = pattern.matched(1);
			var position = pattern.matchedPos();
			var replacement = resolveExpression(expression, location, stack, counter, depth + 1);
			if (replacement.state != "known") return {state:"unresolved", value:current};
			current = current.substr(0, position.pos) + replacement.value
				+ current.substr(position.pos + position.len);
			if (valueSeen.exists(current)) {
				addDiagnostic("variable-cycle", "Project.xml variable substitution contains a cycle.", expression, location);
				return {state:"unresolved", value:current};
			}
			valueSeen.set(current, true);
			if (current.length > MAX_VALUE_LENGTH) {
				addDiagnostic("interpolation-size-limit", "Expanded Project.xml text exceeds the size limit.", null, location);
				return {state:"unresolved", value:current.substr(0, MAX_VALUE_LENGTH)};
			}
		}
		if (current.indexOf("${") >= 0) {
			addDiagnostic("malformed-variable", "A Project.xml variable expression is malformed.", null, location);
			return {state:"unresolved", value:current};
		}
		return {state:"known", value:current};
	}

	function resolveExpression(expression:String, ?location:String, stack:Array<String>,
		counter:{count:Int}, depth:Int):{state:String, value:String} {
		if (depth > MAX_EXPANSION_DEPTH) {
			addDiagnostic("interpolation-depth-limit", "Project.xml variable expression exceeded its depth limit.", null, location);
			return {state:"unresolved", value:expression};
		}
		if (expression.length > MAX_NAME_LENGTH * 2) {
			addDiagnostic("invalid-variable", "A Project.xml variable expression is too long.", expression, location);
			return {state:"unresolved", value:expression};
		}
		if (StringTools.startsWith(expression, "haxelib:")) {
			addDiagnostic("haxelib-variable-unsupported", "Haxelib variable lookup is outside the retained source context.", expression, location);
			return {state:"unresolved", value:expression};
		}
		var exactSymbol = symbols.get(expression);
		if (exactSymbol != null) return resolveSymbol(expression, exactSymbol, location, stack, counter, depth);
		var comparison = findComparison(expression);
		if (comparison != null) {
			var compact = StringTools.replace(expression, " ", "");
			var left = compact.substr(0, comparison.position);
			var right = compact.substr(comparison.position + comparison.op.length);
			if (!validName(left) || containsComparison(right)) {
				addDiagnostic("comparison-unsupported", "Only one simple Lime string comparison is supported.", expression, location);
				return {state:"unresolved", value:expression};
			}
			var leftResolved = resolveExpression(left, location, stack, counter, depth + 1);
			if (leftResolved.state != "known") {
				addDiagnostic("comparison-unresolved", "A Project.xml comparison depends on an uncaptured string value.", left, location);
				return {state:"unresolved", value:expression};
			}
			var leftValue = leftResolved.value;
			var matches = switch (comparison.op) {
				case "==": leftValue == right;
				case "!=": leftValue != right;
				case "<=": leftValue <= right;
			case "<": leftValue < right;
			case ">=": leftValue >= right;
			case ">": leftValue > right;
				default: false;
			};
			return {state:"known", value:matches ? "true" : "false"};
		}
		if (isProjectLookup(expression)) {
			addDiagnostic("project-property-unsupported", "Project object fields and directory values are not resolved from host state.", expression, location);
			return {state:"unresolved", value:expression};
		}
		if (flagsComplete) return {state:"known", value:expression};
		addDiagnostic("variable-unresolved", "A Project.xml variable value was not explicitly captured.", expression, location);
		return {state:"unresolved", value:expression};
	}

	function resolveSymbol(expression:String, symbol:SourceProjectContextSymbol,
		?location:String, stack:Array<String>, counter:{count:Int}, depth:Int):{state:String, value:String} {
		if (symbol.state == "unresolved"
			|| (symbol.state == "enabled" && symbol.valueState != "known")) {
			addDiagnostic("variable-unresolved", "A Project.xml variable value was not explicitly captured.", expression, location);
			return {state:"unresolved", value:expression};
		}
		if (symbol.state == "disabled") return {state:"known", value:expression};
		return {state:"known", value:symbol.value == null ? "" : symbol.value};
	}

	static function isProjectLookup(expression:String):Bool {
		return expression == "projectDirectory" || (expression != null && expression.indexOf(".") >= 0);
	}

	function resolution(state:String, value:String, diagnosticStart:Int,
		?boolValue:Bool):SourceProjectContextResolution {
		var start = diagnosticStart < 0 ? 0 : diagnosticStart;
		if (start > diagnostics.length) start = diagnostics.length;
		return {state:state, value:value, boolValue:boolValue,
			diagnostics:diagnostics.slice(start)};
	}

	function addDiagnostic(code:String, message:String, ?name:String, ?location:String):Void {
		if (diagnostics.length >= MAX_DIAGNOSTICS) {
			if (!diagnosticLimitReported) {
				diagnosticLimitReported = true;
				diagnostics.push({code:"diagnostic-limit", message:"Further SourceProjectContext diagnostics were omitted."});
			}
			return;
		}
		diagnostics.push({code:code, message:message, name:name, location:location});
	}

	function recordOpaque(operation:String, name:String, ?value:String, ?provenance:String):Void {
		if (opaque.length >= MAX_DIAGNOSTICS) {
			addDiagnostic("opaque-limit", "Further compiler-only project declarations were omitted.", name, provenance);
			return;
		}
		opaque.push({operation:operation, name:name, value:value, provenance:provenance});
	}

	static function normalizeState(value:String):String {
		return switch (value == null ? "" : StringTools.trim(value).toLowerCase()) {
			case "enabled": "enabled";
			case "disabled": "disabled";
			default: "unresolved";
		};
	}

	static function validName(value:String):Bool {
		return value != null && value.length > 0 && value.length <= MAX_NAME_LENGTH
			&& ~/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.match(value);
	}

	static function provenanceList(value:String):Array<String> {
		var result:Array<String> = [];
		appendProvenance(result, value);
		return result;
	}

	static function appendProvenance(target:Array<String>, value:String):Void {
		if (target == null || value == null || StringTools.trim(value) == ""
			|| target.length >= MAX_PROVENANCE || target.indexOf(value) >= 0) return;
		target.push(value);
	}

	static function cloneSymbol(symbol:SourceProjectContextSymbol):SourceProjectContextSymbol {
		return {
			state:symbol.state,
			valueState:symbol.valueState,
			value:symbol.value,
			provenance:symbol.provenance == null ? [] : symbol.provenance.copy()
		};
	}

	static function cloneOpaque(item:SourceProjectContextOpaque):SourceProjectContextOpaque {
		return {operation:item.operation, name:item.name, value:item.value, provenance:item.provenance};
	}

	static function triAnd(left:String, right:String):String {
		if (left == "disabled" || right == "disabled") return "disabled";
		if (left == "unresolved" || right == "unresolved") return "unresolved";
		return "enabled";
	}

	static function triOr(left:String, right:String):String {
		if (left == "enabled" || right == "enabled") return "enabled";
		if (left == "unresolved" || right == "unresolved") return "unresolved";
		return "disabled";
	}

	static function findComparison(expression:String):Null<{op:String, position:Int}> {
		var compact = StringTools.replace(expression, " ", "");
		for (comparisonOp in ["==", "!=", "<=", "<", ">=", ">"])
			if (compact.indexOf(comparisonOp) >= 0)
				return {op:comparisonOp, position:compact.indexOf(comparisonOp)};
		return null;
	}

	static function containsComparison(value:String):Bool {
		return value.indexOf("==") >= 0 || value.indexOf("!=") >= 0
			|| value.indexOf("<=") >= 0 || value.indexOf("<") >= 0
			|| value.indexOf(">=") >= 0 || value.indexOf(">") >= 0;
	}
}
