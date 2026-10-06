package;
import nightmarevision.modchart.NightmareVisionModifierRegistry;
/** Immutable submod metadata reused by registered and unregistered source constructors. */
class NightmareVisionBuiltinCatalog {
	static var catalogs:Map<Int,Map<String,Array<String>>> = [];
	public static function submods(kind:String, keys:Int, prefix:String=''):Array<String> {
		if(kind=='path' || kind=='infinite') return [prefix+'visual',prefix+'speed'];
		var catalogue=catalogs.get(keys);
		if(catalogue==null) {
			catalogue=[];var registry=new NightmareVisionModifierRegistry(keys,2);
			for(def in registry.definitions) if(def.parent==null) catalogue.set(def.name,[]);
			for(def in registry.definitions) if(def.parent!=null) catalogue.get(def.parent).push(def.name);
			catalogs.set(keys,catalogue);
		}
		var key=kind=='localrotateX'?'localrotateX':kind;
		var result=catalogue.get(key);if(result==null) return [];
		if(kind=='rotateX' || kind=='localrotateX') {
			var old=kind=='localrotateX'?'local':'';
			return [for(name in result) prefix+name.substr(old.length)];
		}
		return result.copy();
	}
	public static function hasPosition(kind:String):Bool return ['reverse','perspectiveDONTUSE','opponentSwap','flip','invert','drunk','beat','receptorScroll','transformX','infinite','path','boost','rotateX','localrotateX'].indexOf(kind)>=0;
	public static function hasObject(kind:String, objectKind:String):Bool {
		return switch(kind) {
			case 'stealth','mini','perspectiveDONTUSE': true;
			case 'confusion': objectKind=='note'||objectKind=='receptor';
			case 'receptorScroll','xmod': objectKind=='note';
			default:false;
		};
	}
}
