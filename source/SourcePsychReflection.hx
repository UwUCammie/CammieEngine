package;

/** Source property and method operations with live, injected native boundaries. */
class SourcePsychReflection {
	final registry:()->Dynamic;
	final state:()->Dynamic;
	final play:()->Dynamic;
	final target:()->Dynamic;
	final isState:Dynamic->Bool;
	final resolveClass:String->Dynamic;
	final readProperty:(Dynamic,String)->Dynamic;
	final writeProperty:(Dynamic,String,Dynamic)->Void;
	final parse:Dynamic->Dynamic;
	final warn:String->Void;
	public function new(registry:()->Dynamic, state:()->Dynamic, play:()->Dynamic, target:()->Dynamic,
		isState:Dynamic->Bool, resolveClass:String->Dynamic, readProperty:(Dynamic,String)->Dynamic,
		writeProperty:(Dynamic,String,Dynamic)->Void, parse:Dynamic->Dynamic, warn:String->Void) {
		this.registry=registry;this.state=state;this.play=play;this.target=target;this.isState=isState;
		this.resolveClass=resolveClass;this.readProperty=readProperty;this.writeProperty=writeProperty;this.parse=parse;this.warn=warn;
	}
	public function read(object:Dynamic,key:String,maps:Bool=false):Dynamic
		return SourceScriptReflection.readPsychInstancePart(object,key,isState,registry,readProperty,maps);
	public function write(object:Dynamic,key:String,value:Dynamic,maps:Bool=false):Dynamic
		return SourceScriptReflection.writePsychPathPart(object,key,value,isState,registry,readProperty,writeProperty,maps);
	public function direct(name:String,maps:Bool=false):Dynamic {
		if (name=='this'||name=='instance'||name=='game') return play();
		var object:Dynamic=registry().get(name);
		return object==null ? read(state(),name,maps) : object;
	}
	public function loop(parts:Array<String>,parent:Bool=true,maps:Bool=false):Dynamic {
		var object=direct(parts[0]);
		var end=parent ? parts.length-1 : parts.length;
		for(i in 1...end) object=read(object,parts[i],maps);
		return object;
	}
	/** Text/object callbacks use a direct root even for a single-token path. */
	public function object(path:String):Dynamic {
		var parts=path.split('.');
		return parts.length>1 ? read(loop(parts),parts[parts.length-1]) : direct(parts[0]);
	}
	public function get(path:String,maps:Bool=false):Dynamic {
		var parts=path.split('.');
		return parts.length>1 ? read(loop(parts,true,maps),parts[parts.length-1],maps) : read(target(),path,maps);
	}
	public function set(path:String,value:Dynamic,maps:Bool=false,instances:Bool=false):Dynamic {
		var parts=path.split('.');
		var object=parts.length>1 ? loop(parts,true,maps) : target();
		write(object,parts[parts.length-1],instances?parse(value):value,maps);return value;
	}
	public function getClass(type:String,path:String,maps:Bool=false):Dynamic {
		var object=resolveClass(type);
		if(object==null){warn('getPropertyFromClass: Class $type not found');return null;}
		for(part in path.split('.')) object=read(object,part,maps);
		return object;
	}
	public function setClass(type:String,path:String,value:Dynamic,maps:Bool=false,instances:Bool=false):Dynamic {
		var object=resolveClass(type);
		if(object==null){warn('setPropertyFromClass: Class $type not found');return null;}
		var parts=path.split('.');
		for(i in 0...parts.length-1) object=read(object,parts[i],maps);
		write(object,parts[parts.length-1],instances?parse(value):value,maps);return value;
	}
	function groupRoot(path:String,maps:Bool):Dynamic {
		var parts=path.split('.');
		return parts.length>1 ? loop(parts,false,maps) : readProperty(target(),path);
	}
	function groupField(object:Dynamic,field:String,maps:Bool):Dynamic {
		var parts=field.split('.');
		var owner=SourceScriptReflection.groupFieldOwner(object,parts,readProperty);
		var key=parts[parts.length-1];
		return maps&&SourceScriptReflection.isPsychMap(owner) ? owner.get(key) : readProperty(owner,key);
	}
	function setGroupField(object:Dynamic,field:String,value:Dynamic,maps:Bool):Void {
		var parts=field.split('.');
		var owner=SourceScriptReflection.groupFieldOwner(object,parts,readProperty);
		var key=parts[parts.length-1];
		if(maps&&SourceScriptReflection.isPsychMap(owner)) owner.set(key,value);
		else writeProperty(owner,key,value);
	}
	public function getGroup(path:String,index:Int,field:Dynamic,maps:Bool=false):Dynamic {
		var group:Dynamic=groupRoot(path,maps);
		// The source deliberately re-reads the literal target property for dispatch.
		var dispatch:Dynamic=readProperty(target(),path);
		if(dispatch!=null) {
			if(Std.isOfType(dispatch,Array)) {
				var item:Dynamic=group[index];
				if(item!=null) return Type.typeof(field)==TInt ? item[field] : groupField(item,field,maps);
				warn('getPropertyFromGroup: Object #$index from group: $path doesn\'t exist!');
			} else return groupField(group.members[index],field,maps);
		}
		warn('getPropertyFromGroup: Group/Array $path doesn\'t exist!');
		return null;
	}
	public function setGroup(path:String,index:Int,field:Dynamic,value:Dynamic,maps:Bool=false,instances:Bool=false):Dynamic {
		var group:Dynamic=groupRoot(path,maps);
		if(group!=null) {
			if(Std.isOfType(group,Array)) {
				var item:Dynamic=group[index];
				if(item!=null) {
					if(Type.typeof(field)==TInt) {item[field]=instances?parse(value):value;return value;}
					setGroupField(item,field,instances?parse(value):value,maps);
				}
			} else setGroupField(group.members[index],field,instances?parse(value):value,maps);
		} else warn('setPropertyFromGroup: Group/Array $path doesn\'t exist!');
		return value;
	}
	public function addGroup(path:String,tag:String,index:Int=-1):Void {
		var object:Dynamic=direct(tag);
		if(object==null||object.destroy==null) {warn('addToGroup: Object $tag is not valid!');return;}
		var group:Dynamic=readProperty(target(),path);
		if(group==null) {warn('addToGroup: Group/Array $path is not valid!');return;}
		if(index<0) {
			if(Std.isOfType(group,Array)) group.push(object); else group.add(object);
		} else group.insert(index,object);
	}
	public function removeGroup(path:String,index:Int=-1,?tag:String,destroy:Bool=true):Void {
		var object:Dynamic=null;
		if(tag!=null) {
			object=direct(tag);
			if(object==null||object.destroy==null) {warn('removeFromGroup: Object $tag is not valid!');return;}
		}
		var group:Dynamic=readProperty(target(),path);
		if(group==null) {warn('removeFromGroup: Group/Array $path is not valid!');return;}
		if(Std.isOfType(group,Array)) {
			if(object!=null) {group.remove(object);if(destroy)object.destroy();}
			else group.remove(group[index]);
		} else {
			if(object==null)object=group.members[index];
			group.remove(object,true);
			if(destroy)object.destroy();
		}
	}
	public function callObject(object:Dynamic,path:String,args:Array<Dynamic>):Dynamic {
		var parts=path.split('.');
		if(object==null)return null;
		for(part in parts) object=read(object,StringTools.trim(part));
		var method:haxe.Constraints.Function=object;
		return method!=null ? Reflect.callMethod(object,method,args) : null;
	}
	public function call(path:String,?args:Array<Dynamic>):Dynamic {
		var parent=play();var parts=path.split('.');
		var variable:Dynamic=registry().get(StringTools.trim(parts[0]));
		if(variable!=null){parts.shift();path=StringTools.trim(parts.join('.'));parent=variable;}
		return path.length>0 ? callObject(parent,path,parse(args)) : Reflect.callMethod(null,parent,parse(args));
	}
	public function callClass(type:String,path:String,?args:Array<Dynamic>):Dynamic {
		return callObject(resolveClass(type),path,parse(args));
	}
}
