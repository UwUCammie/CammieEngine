package;

using StringTools;

/** Reuse repeated pure integer-coordinate calls across adjacent scalar helpers.
 * No floating arithmetic, sample coordinates, loops or shader assets are changed.
 * Unsupported syntax stays with the original GLSL compiler path. */
class ShaderRepeatedCallOptimizer {
	static final TYPES = ['float','int','bool','vec2','vec3','vec4','ivec2','ivec3','ivec4'];
	static final BUILTINS = ['abs','floor','ceil','fract','sin','cos','tan','asin','acos','atan','sqrt','inversesqrt',
		'exp','exp2','log','log2','pow','min','max','clamp','mix','step','smoothstep','dot','length','distance','normalize',
		'mod','sign','radians','degrees','cross','reflect','refract'];

	public static function optimize(source:String):String {
		if (source == null || source.length > 100000 || ~/^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|else|endif|undef)\b/m.match(source)
			|| source.indexOf('\\\n') >= 0 || source.indexOf('\\\r') >= 0) return source;
		// New locals must not cross explicit precision or invariant boundaries.
		for (token in @:privateAccess CodenameShaderSource.glslTokens(source))
			if (['precision','highp','mediump','lowp','precise','invariant'].indexOf(token.text) >= 0) return source;
		return new RepeatedCallPass(source).run();
	}
	@:allow(RepeatedCallPass) static function type(name:String):Bool return TYPES.indexOf(name) >= 0;
	@:allow(RepeatedCallPass) static function builtin(name:String):Bool return type(name) || BUILTINS.indexOf(name) >= 0;
}

private class RepeatedCallPass {
	var source:String;
	var tokens:Array<Dynamic>;
	var functions:Map<String,Dynamic> = [];
	var macros:Map<String,Bool> = [];
	var constants:Map<String,Bool> = [];
	var purity:Map<String,Int> = [];
	var serial:Int = 0;

	public function new(source:String) {
		this.source = source;
		tokens = @:privateAccess CodenameShaderSource.glslTokens(source);
		for (line in source.split('\n')) {
			var define = ~/^[ \t]*#[ \t]*define[ \t]+([A-Za-z_][A-Za-z_0-9]*)(.*)$/;
			if (define.match(line)) {
				var name = define.matched(1), value = define.matched(2).trim();
				if (macros.exists(name)) constants.remove(name);
				else if (~/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.match(value)) constants.set(name,true);
				macros.set(name,true);
			}
		}
		var i = 0;
		while (i + 3 < tokens.length) {
			if (!ShaderRepeatedCallOptimizer.type(text(i)) || tokens[i+1].kind != 'identifier' || text(i+2) != '(') {i++;continue;}
			var close = matching(i+2,'(',')');
			if (close < 0 || text(close+1) != '{') {i++;continue;}
			var end = matching(close+1,'{','}');
			if (end < 0) break;
			var params:Array<Dynamic> = [];
			var valid = true;
			for (arg in arguments(i+3,close)) {
				if (arg.length != 2 || !ShaderRepeatedCallOptimizer.type(arg[0].text) || arg[1].kind != 'identifier') {valid=false;break;}
				params.push({type:arg[0].text,name:arg[1].text});
			}
			var name = text(i+1);
			if (functions.exists(name) || macros.exists(name)) functions.set(name,null);
			else functions.set(name,valid?{name:name,type:text(i),params:params,body:close+1,end:end}:null);
			i = end+1;
		}
	}

	function text(i:Int):String return i>=0 && i<tokens.length ? tokens[i].text : '';
	function matching(start:Int,open:String,close:String):Int {
		var depth=0;
		for(i in start...tokens.length) {
			if(text(i)==open) depth++;
			else if(text(i)==close && --depth==0) return i;
		}
		return -1;
	}
	function arguments(start:Int,end:Int):Array<Array<Dynamic>> {
		var result:Array<Array<Dynamic>>=[],begin=start,depth=0;
		if(start==end) return result;
		for(i in start...end) {
			if(text(i)=='(') depth++;
			else if(text(i)==')') depth--;
			else if(text(i)==',' && depth==0) {result.push(tokens.slice(begin,i));begin=i+1;}
		}
		result.push(tokens.slice(begin,end));return result;
	}
	function locals(fn:Dynamic):Map<String,String> {
		var values:Map<String,String>=[];
		for(p in (cast fn.params:Array<Dynamic>)) values.set(p.name,p.type);
		for(i in (fn.body+1)...fn.end) if(ShaderRepeatedCallOptimizer.type(text(i)) && tokens[i+1].kind=='identifier' && text(i+2)!='(') {
			var name=text(i+1),kind=text(i);
			values.set(name,values.exists(name)?'ambiguous':kind);
		}
		return values;
	}
	function pure(name:String, depth:Int = 0):Bool {
		if (depth > 32) return false;
		if(macros.exists(name)) return false;
		if(!functions.exists(name)) return ShaderRepeatedCallOptimizer.builtin(name);
		if(purity.exists(name)) return purity.get(name)==1;
		purity.set(name,-1);
		var fn=functions.get(name);
		if(fn==null || source.substring(tokens[fn.body].start,tokens[fn.end].end).indexOf('#')>=0) return false;
		var values=locals(fn);
		for(key in values.keys()) if(macros.exists(key) || values.get(key)=='ambiguous') return false;
		for(i in (fn.body+1)...fn.end) {
			var value=text(i);
			if(['[',']','{','}','++','--','discard','if','else','for','while','do','switch'].indexOf(value)>=0) return false;
			if(['=','+=','-=','*=','/='].indexOf(value)>=0) {
				var target=text(i-1);
				if(text(i-2)=='.') target=text(i-3);
				if(!values.exists(target)) return false;
			}
			if(tokens[i].kind!='identifier') continue;
			if(macros.exists(value) && (!constants.exists(value) || ShaderRepeatedCallOptimizer.type(value) || value=='return')) return false;
			if(text(i-1)=='.') {if(!~/^[xyzwrgbastpq]+$/.match(value)) return false;continue;}
			if(text(i+1)=='(') {if(!pure(value,depth+1)) return false;continue;}
			if(value=='return' || value=='true' || value=='false' || ShaderRepeatedCallOptimizer.type(value)) continue;
			if(!values.exists(value) && !constants.exists(value)) return false;
		}
		purity.set(name,1);return true;
	}

	// Only integer coordinates plus small literal offsets are normalized.
	// Floating expressions are never reassociated, even when algebraically equal.
	function affine(input:Array<Dynamic>,env:Map<String,Dynamic>,types:Map<String,String>):Dynamic {
		var a=[for(t in input) Std.string(t.text)];
		if(a.length==0) return null;
		var base:Dynamic=null,index=0;
		if(env!=null && env.exists(a[0])) {var v=env.get(a[0]);base={base:v.base,offset:v.offset};index=1;}
		else if(types!=null && types.get(a[0])=='int') {base={base:a[0],offset:0};index=1;}
		else if(a.length>=3 && a[1]=='.' && ['ivec2','ivec3','ivec4'].indexOf(types==null?null:types.get(a[0]))>=0
			&& ~/^[xyzw]$/.match(a[2])) {base={base:a[0]+'.'+a[2],offset:0};index=3;}
		else return null;
		while(index<a.length) {
			if(index+1>=a.length || (a[index]!='+' && a[index]!='-') || !~/^[0-9]{1,3}$/.match(a[index+1])) return null;
			var delta=Std.parseInt(a[index+1]);base.offset+=a[index]=='+'?delta:-delta;index+=2;
		}
		return Math.abs(base.offset)>128?null:base;
	}
	function coordinate(value:Dynamic):String return value.base+(value.offset>0?' + '+value.offset:value.offset<0?' - '+(-value.offset):'');

	function row(start:Int,limit:Int):Dynamic {
		if(start+7>=limit || text(start)!='float' || tokens[start+1].kind!='identifier' || text(start+2)!='='
			|| tokens[start+3].kind!='identifier' || macros.exists('float') || text(start+4)!='(') return null;
		var end=matching(start+4,'(',')');
		if(end<0 || end+1>=limit || text(end+1)!=';') return null;
		var wrapper=functions.get(text(start+3));
		if(wrapper==null || wrapper.type!='float' || wrapper.params.length==0 || wrapper.params.length>4
			|| wrapper.end-wrapper.body>512 || text(wrapper.body+1)!='return' || text(Std.int(wrapper.end)-1)!=';'
			|| !pure(wrapper.name)) return null;
		for(i in (wrapper.body+2)...(Std.int(wrapper.end)-1)) if([';','?','&&','||'].indexOf(text(i))>=0) return null;
		for(p in (cast wrapper.params:Array<Dynamic>)) if(p.type!='int') return null;
		var args=arguments(start+5,end);
		if(args.length!=wrapper.params.length || macros.exists(text(start+1))) return null;
		return {start:start,end:end+2,call:start+3,close:end,wrapper:wrapper,args:args};
	}

	public function run():String {
		var edits:Array<Dynamic>=[];
		for(fn in functions) {
			if(fn==null || source.substring(tokens[fn.body].start,tokens[fn.end].end).indexOf('#')>=0) continue;
			var types=locals(fn),i:Int=fn.body+1;
			while(i<fn.end) {
				if(['{',';','}'].indexOf(text(i-1))<0) {i++;continue;}
				var first=row(i,fn.end);
				if(first==null) {i++;continue;}
				var rows:Array<Dynamic>=[first],next:Int=first.end;
				while(rows.length<8) {
					var following=row(next,fn.end);
					if(following==null || following.wrapper.name!=first.wrapper.name) break;
					rows.push(following);next=following.end;
				}
				i=next;
				if(rows.length<2) continue;
				var values:Map<String,String>=[],declarations:Array<String>=[],replacements:Array<Dynamic>=[];
				var valid=true,calls=0;
				for(r in rows) {
					var wrapper=r.wrapper,env:Map<String,Dynamic>=[];
					for(k in 0...r.args.length) {
						var arg=affine(r.args[k],null,types);
						if(arg==null || macros.exists(arg.base.split('.')[0])) {valid=false;break;}
						env.set(wrapper.params[k].name,arg);
					}
					if(!valid) break;
					var begin:Int=wrapper.body+2,end:Int=wrapper.end-1,j=begin;
					var inner:Array<Dynamic>=[];
					while(j<end) {
						if(env.exists(text(j))) {valid=false;break;}
						if(tokens[j].kind!='identifier' || text(j+1)!='(') {j++;continue;}
						var leaf=functions.get(text(j));
						if(leaf==null || leaf.type!='float' || !pure(leaf.name)) {j++;continue;}
						var close=matching(j+1,'(',')'),args=arguments(j+2,close);
						if(close<0 || close>=end || args.length!=leaf.params.length) {valid=false;break;}
						var coordinates:Array<String>=[];
						for(k in 0...args.length) {
							var coord=leaf.params[k].type=='int'?affine(args[k],env,null):null;
							if(coord==null) {valid=false;break;}
							coordinates.push(coordinate(coord));
						}
						if(!valid) break;
						var key=leaf.name+'('+coordinates.join(', ')+')',name=values.get(key);
						if(name==null) {
							name='cammieSharedCall'+serial++;
							while(source.indexOf(name)>=0) name+='_';
							values.set(key,name);declarations.push('float '+name+' = '+key+';');
						}
						calls++;inner.push({start:tokens[j].start,end:tokens[close].end,text:name});j=close+1;
					}
					if(!valid) break;
					var expression=source.substring(tokens[begin].start,tokens[end].start);
					inner.reverse();
					for(edit in inner) {
						var start:Int=Std.int(edit.start)-Std.int(tokens[begin].start),finish:Int=Std.int(edit.end)-Std.int(tokens[begin].start);
						expression=expression.substring(0,start)+edit.text+expression.substring(finish);
					}
					replacements.push({start:tokens[r.call].start,end:tokens[r.close].end,text:'('+expression+')'});
				}
				if(!valid || declarations.length==0 || declarations.length>64 || calls<declarations.length*1.25) continue;
				edits.push({start:tokens[first.start].start,end:tokens[first.start].start,text:declarations.join('\n')+'\n'});
				for(edit in replacements) edits.push(edit);
			}
		}
		edits.sort(function(a,b) return b.start-a.start);
		for(edit in edits) source=source.substring(0,edit.start)+edit.text+source.substring(edit.end);
		return source;
	}
}
