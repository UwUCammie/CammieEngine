package;

/** Runtime-visible form of haxe.xml.Access, whose abstract dot access erases in HScript. */
@:keep
class CodenameXmlAccess {
	public final x:Xml;
	public var name(get, never):String;
	public var innerData(get, never):String;
	public var innerHTML(get, never):String;
	public var node(get, never):CodenameXmlFieldAccess;
	public var nodes(get, never):CodenameXmlFieldAccess;
	public var att(get, never):CodenameXmlFieldAccess;
	public var has(get, never):CodenameXmlFieldAccess;
	public var hasNode(get, never):CodenameXmlFieldAccess;
	public var elements(get, never):Iterator<CodenameXmlAccess>;

	public function new(x:Xml) {
		if (x == null || (x.nodeType != Xml.Document && x.nodeType != Xml.Element))
			throw 'Invalid XML node';
		this.x = x;
	}

	function get_name():String return x.nodeType == Xml.Document ? 'Document' : x.nodeName;
	function get_innerData():String return new haxe.xml.Access(x).innerData;
	function get_innerHTML():String return new haxe.xml.Access(x).innerHTML;
	function get_node():CodenameXmlFieldAccess return new CodenameXmlFieldAccess(this, 'node');
	function get_nodes():CodenameXmlFieldAccess return new CodenameXmlFieldAccess(this, 'nodes');
	function get_att():CodenameXmlFieldAccess return new CodenameXmlFieldAccess(this, 'att');
	function get_has():CodenameXmlFieldAccess return new CodenameXmlFieldAccess(this, 'has');
	function get_hasNode():CodenameXmlFieldAccess return new CodenameXmlFieldAccess(this, 'hasNode');
	function get_elements():Iterator<CodenameXmlAccess> {
		var result:Array<CodenameXmlAccess> = [];
		for (element in x.elements()) result.push(new CodenameXmlAccess(element));
		return result.iterator();
	}
	public function toString():String return x.toString();
}

/** A property proxy used by CodenameScriptInterp.get/set. */
@:keep
class CodenameXmlFieldAccess {
	public final owner:CodenameXmlAccess;
	public final kind:String;
	public function new(owner:CodenameXmlAccess, kind:String) {
		this.owner = owner;
		this.kind = kind;
	}
	public function getField(name:String):Dynamic {
		var xml = owner.x;
		switch (kind) {
			case 'node':
				var child = xml.elementsNamed(name);
				if (!child.hasNext()) throw owner.name + ' is missing element ' + name;
				return new CodenameXmlAccess(child.next());
			case 'nodes':
				var children:Array<CodenameXmlAccess> = [];
				for (child in xml.elementsNamed(name)) children.push(new CodenameXmlAccess(child));
				return children;
			case 'hasNode': return xml.elementsNamed(name).hasNext();
			case 'att':
				if (xml.nodeType == Xml.Document) throw 'Cannot access document attribute ' + name;
				var value = xml.get(name);
				if (value == null) throw owner.name + ' is missing attribute ' + name;
				return value;
			case 'has':
				if (xml.nodeType == Xml.Document) throw 'Cannot access document attribute ' + name;
				return xml.exists(name);
			default: throw 'Unsupported XML access ' + kind;
		}
	}
	public function setField(name:String, value:Dynamic):Dynamic {
		if (kind != 'att') throw 'Cannot assign XML ' + kind + '.' + name;
		if (owner.x.nodeType == Xml.Document) throw 'Cannot access document attribute ' + name;
		owner.x.set(name, Std.string(value));
		return value;
	}
}
