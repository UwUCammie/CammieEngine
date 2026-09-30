package;

import crowplexus.hscript.Expr;
import crowplexus.hscript.Parser;
import crowplexus.hscript.Tools;

/** NMV public module declarations use the interpreter's shared-field table. */
class NightmareVisionScriptParser extends Parser {
	public function new() {
		super();
		allowTypes = true;
		allowMetadata = true;
		allowJSON = true;
	}

	/** The source ParserEx interpolates single quotes; stable Iris leaves them
	 * literal. Lower only string interpolation, keeping the Iris module grammar. */
	override public function parseString(source:String, ?origin:String = "hscript"):Expr {
		var normalized = HaxeStringInterpolation.normalize(source);
		if (normalized.error != '') throw origin + ': ' + normalized.error;
		return super.parseString(normalized.source, origin);
	}

	override function parseStructure(id:String):Expr {
		if (id == 'for') {
			#if hscriptPos
			var start = tokenMin;
			#end
			ensure(TPOpen);
			var key = getIdent();
			var value = maybe(TOp('=>')) ? getIdent() : null;
			ensureToken(TId('in'));
			var iterator = parseExpr();
			ensure(TPClose);
			var body = parseExpr();
			// Keep EFor so Iris's comprehension lowering still traverses the
			// loop body. Only the iterator carries the extra source binding.
			if (value != null) iterator = mk(EMeta(':nmvKeyValue', [mk(EIdent(value))], iterator));
			return mk(EFor(key, iterator, body), #if hscriptPos start, pmax(body) #end);
		}
		if (id != 'public') return super.parseStructure(id);
		var declaration = parseExpr();
		switch (Tools.expr(declaration)) {
			case EVar(_, _, _, _):
				return mk(EMeta(':sharable', [], declaration));
			case EFunction(_, _, name, _) if (name != null):
				return mk(EMeta(':sharable', [], declaration));
			default:
				return unexpected(TId(id));
		}
	}
}
