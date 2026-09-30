package hscript;

/** Owner-scoped value for a source class used as a runtime class argument. */
class ScriptClassSymbol {
	public final scope:ScriptClassScope;
	public final descriptor:ClassDeclEx;
	public final fullName:String;

	public function new(scope:ScriptClassScope, descriptor:ClassDeclEx, fullName:String) {
		this.scope = scope;
		this.descriptor = descriptor;
		this.fullName = fullName;
	}
}
