package;

#if flixel
import flixel.graphics.tile.FlxGraphicsShader;
#end
import hscript.Expr;
import hscript.ParserEx;
import hscript.Printer;

using StringTools;

/** Runtime counterpart to OpenFL's FlxShader GLSL build metadata for owner
	class modules interpreted by hscript-ex. */
class PsychShaderSourceCompat {
	static final SHADER_BASE = 'flixel.system.FlxAssets.FlxShader';

	/** Attach runtime GLSL sources to an imported FlxShader subclass. The
		Haxe compiler normally consumes @:gl* metadata and creates uniform fields;
		owner source classes are interpreted, so this adapter expands the same
		metadata and passes the resulting source to PsychFlxShaderCompat.
	*/
	public static function prepareClass(declaration:ClassDecl,
		importAliases:Map<String, Array<String>>):Bool {
		if (declaration == null || !extendsFlxShader(declaration.extend, importAliases))
			return false;

		var metadata:Map<String, String> = new Map();
		for (field in declaration.fields) {
			if (field.meta == null) continue;
			for (entry in field.meta) {
				var name = entry.name;
				while (name.startsWith(':')) name = name.substr(1);
				switch (name) {
					case 'glVertexHeader', 'glVertexBody', 'glVertexSource',
						'glFragmentHeader', 'glFragmentBody', 'glFragmentSource':
						var value = metadataString(entry.params);
						if (value != null) metadata.set(name, value);
					default:
				}
			}
		}

		if (!metadata.iterator().hasNext()) return false;
		var sources = buildSources(metadata);
		var uniforms = shaderUniforms(sources[0], sources[1]);
		var declared:Map<String, Bool> = new Map();
		for (field in declaration.fields) declared.set(field.name, true);
		for (uniform in uniforms) {
			if (declared.exists(uniform)) continue;
			declared.set(uniform, true);
			declaration.fields.push({name:uniform, meta:[], access:[APublic],
				kind:KVar({get:null, set:null, type:null, expr:new ParserEx().parseString('null')})});
		}
		var parser = new ParserEx();
		var constructorArgs = [
			parser.parseString(haxe.Json.stringify(sources[0])),
			parser.parseString(haxe.Json.stringify(sources[1]))
		];
		var uniformInitializers = [for (uniform in uniforms)
			parser.parseString('this.' + uniform + ' = this.superClass.data.' + uniform)];
		for (field in declaration.fields) {
			if (field.name != 'new') continue;
			switch (field.kind) {
				case KFunction(fn):
					if (replaceSuperCall(fn.expr, constructorArgs, uniformInitializers)) {
						return true;
					}
				default:
			}
		}
		return false;
	}

	static function extendsFlxShader(parent:Null<CType>,
		importAliases:Map<String, Array<String>>):Bool {
		if (parent == null) return false;
		var parentPath = new Printer().typeToString(parent);
		if (parentPath == SHADER_BASE) return true;
		if (parentPath != 'FlxShader') return false;
		var imported = importAliases == null ? null : importAliases.get(parentPath);
		return imported != null && imported.join('.') == SHADER_BASE;
	}

	static function metadataString(params:Array<Expr>):Null<String> {
		if (params == null || params.length == 0) return null;
		#if hscriptPos
		return switch (params[0].e) {
			case EConst(CString(value)): value;
			default: null;
		};
		#else
		return switch (params[0]) {
			case EConst(CString(value)): value;
			default: null;
		};
		#end
	}

	static function replaceSuperCall(body:Expr, args:Array<Expr>, initializers:Array<Expr>):Bool {
		#if hscriptPos
		switch (body.e) {
			case EBlock(expressions):
				for (index in 0...expressions.length) {
					if (!replaceSuperCall(expressions[index], args, initializers)) continue;
					for (offset in 0...initializers.length)
						expressions.insert(index + 1 + offset, initializers[offset]);
					return true;
				}
			case ECall({e:EIdent('super')}, callArgs):
				callArgs.resize(0);
				for (arg in args) callArgs.push(arg);
				return true;
			default:
		}
		#else
		switch (body) {
			case EBlock(expressions):
				for (index in 0...expressions.length) {
					if (!replaceSuperCall(expressions[index], args, initializers)) continue;
					for (offset in 0...initializers.length)
						expressions.insert(index + 1 + offset, initializers[offset]);
					return true;
				}
			case ECall(EIdent('super'), callArgs):
				callArgs.resize(0);
				for (arg in args) callArgs.push(arg);
				return true;
			default:
		}
		#end
		return false;
	}

	static function shaderUniforms(vertex:String, fragment:String):Array<String> {
		var result:Array<String> = [];
		var seen:Map<String, Bool> = new Map();
		var source = (vertex == null ? '' : vertex) + '\n' + (fragment == null ? '' : fragment);
		var expression = ~/\buniform\s+[A-Za-z0-9]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?\s*;/g;
		var offset = 0;
		while (expression.matchSub(source, offset)) {
			var name = expression.matched(1);
			if (!seen.exists(name)) {
				seen.set(name, true);
				result.push(name);
			}
			var span = expression.matchedPos();
			offset = span.pos + span.len;
		}
		return result;
	}

	static function buildSources(metadata:Map<String, String>):Array<String> {
		#if flixel
		var base = new FlxGraphicsShader();
		var vertex = expandSource(base.glVertexSource, metadata.get('glVertexSource'),
			metadata.get('glVertexHeader'), metadata.get('glVertexBody'));
		var fragment = expandSource(base.glFragmentSource, metadata.get('glFragmentSource'),
			metadata.get('glFragmentHeader'), metadata.get('glFragmentBody'));
		return [vertex, fragment];
		#else
		var vertex = metadata.get('glVertexSource');
		var fragment = metadata.get('glFragmentSource');
		return [vertex == null ? '' : vertex, fragment == null ? '' : fragment];
		#end
	}

	static function expandSource(baseSource:String, authoredSource:Null<String>,
		header:Null<String>, body:Null<String>):String {
		var template = baseSource == null ? '' : baseSource;
		var result = authoredSource == null ? template : authoredSource;
		var headerToken = '#pragma header';
		var bodyToken = '#pragma body';
		if (result.indexOf(headerToken) >= 0) {
			var mainAt = template.indexOf('void main');
			var inheritedHeader = mainAt < 0 ? template : template.substr(0, mainAt);
			result = StringTools.replace(result, headerToken,
				inheritedHeader + (header == null ? '' : '\n' + header));
		} else if (authoredSource == null && header != null && header != '') {
			result = insertHeader(result, header);
		}
		if (result.indexOf(bodyToken) >= 0)
			result = StringTools.replace(result, bodyToken, body == null ? '' : body);
		else if (authoredSource == null && body != null && body != '')
			result = insertBody(result, body);
		return result;
	}

	static function insertHeader(source:String, header:String):String {
		var mainAt = source.indexOf('void main');
		if (mainAt < 0) return source + '\n' + header;
		return source.substr(0, mainAt) + header + '\n' + source.substr(mainAt);
	}

	static function insertBody(source:String, body:String):String {
		var mainAt = source.indexOf('void main');
		if (mainAt < 0) return source;
		var openBrace = source.indexOf('{', mainAt);
		if (openBrace < 0) return source;
		return source.substr(0, openBrace + 1) + '\n' + body + '\n' + source.substr(openBrace + 1);
	}
}
