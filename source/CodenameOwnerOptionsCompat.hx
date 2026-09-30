package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

/** Selected-owner adapter for Codename's `data/config/options*.xml` files.
	This currently materializes checkboxes, the portable option type shared by
	older Codename packages. Unknown option types are returned as diagnostics.
*/
class CodenameOwnerOptionsCompat {
	public static function parse(xmlText:String, source:String):Dynamic {
		var result:Dynamic = {menus:[], diagnostics:[]};
		if (xmlText == null || StringTools.trim(xmlText) == '') {
			result.diagnostics.push('[codename-options-xml] Empty selected-owner options document: ' + source);
			return result;
		}
		try {
			var document = Xml.parse(xmlText);
			var root:Xml = null;
			for (element in document.elements()) { root = element; break; }
			if (root == null) {
				result.diagnostics.push('[codename-options-xml] No root element in ' + source);
				return result;
			}
			if (root.nodeName == 'menu') {
				var menu = parseMenu(root, source, result.diagnostics);
				if (menu.options.length > 0) result.menus.push(menu);
			} else {
				var nestedMenuFound = false;
				for (element in root.elements()) if (element.nodeName == 'menu') {
					nestedMenuFound = true;
					var menu = parseMenu(element, source, result.diagnostics);
					if (menu.options.length > 0) result.menus.push(menu);
				}
				if (!nestedMenuFound) {
					var menu = parseMenu(root, source, result.diagnostics);
					if (menu.options.length > 0) result.menus.push(menu);
				}
			}
		} catch (error:Dynamic) {
			result.diagnostics.push('[codename-options-xml] Could not parse ' + source + ': ' + Std.string(error));
		}
		return result;
	}

	static function parseMenu(element:Xml, source:String, diagnostics:Array<String>):Dynamic {
		var name = element.get('name');
		var desc = element.get('desc');
		var menu:Dynamic = {name:(name == null || StringTools.trim(name) == '' ? Path.withoutExtension(source) : name),
			desc:desc == null ? '' : desc, source:source, options:[]};
		for (option in element.elements()) {
			switch (option.nodeName) {
				case 'separator':
					// Separators have no data behavior and can be skipped safely.
				case 'checkbox':
					var id = option.get('id');
					var label = option.get('name');
					if (id == null || StringTools.trim(id) == '' || label == null || StringTools.trim(label) == '') {
						diagnostics.push('[codename-options-xml] Checkbox requires nonempty id and name in ' + source);
						continue;
					}
					if (!validSaveField(id)) {
						diagnostics.push('[codename-options-xml] Checkbox has an unsupported owner save id "'
							+ id + '" in ' + source);
						continue;
					}
					menu.options.push({kind:'checkbox', id:id, label:label,
						desc:option.get('desc') == null ? '' : option.get('desc'), source:source});
				default:
					diagnostics.push('[codename-options-unsupported] Unsupported XML option type "'
						+ option.nodeName + '" in ' + source);
			}
		}
		return menu;
	}

	/** Enumerate only selected-owner option files. */
	public static function load(ownerRoot:String):Dynamic {
		var result:Dynamic = {menus:[], diagnostics:[]};
		if (ownerRoot == null || ownerRoot == '') return result;
		#if sys
		var files:Array<String> = [];
		for (relative in ['data/config/options.xml', 'config/options.xml']) {
			var resolved = CodenameScriptDiscovery.resolveScopedRelative(ownerRoot, relative);
			if (resolved != null && FileSystem.exists(Path.join([ownerRoot, resolved]))
				&& !FileSystem.isDirectory(Path.join([ownerRoot, resolved]))) files.push(resolved);
		}
		for (folder in ['data/config/options', 'config/options']) {
			try {
				for (name in new CodenamePaths(ownerRoot).getFolderContent(folder, false))
					if (Path.extension(name).toLowerCase() == 'xml') {
						var relative = folder + '/' + name;
						var resolved = CodenameScriptDiscovery.resolveScopedRelative(ownerRoot, relative);
					if (resolved != null) files.push(resolved);
					}
			} catch (error:Dynamic) {
				result.diagnostics.push('[codename-options-xml] Could not enumerate ' + folder + ': ' + Std.string(error));
			}
		}
		files.sort(Reflect.compare);
		var previous:String = null;
		for (relative in files) {
			if (relative == previous) continue;
			previous = relative;
			var path = Path.join([ownerRoot, relative]);
			try {
				var parsed = parse(FNFAssets.getText(path), relative);
				var parsedMenus:Array<Dynamic> = cast parsed.menus;
				var parsedDiagnostics:Array<String> = cast parsed.diagnostics;
				for (menu in parsedMenus) result.menus.push(menu);
				for (diagnostic in parsedDiagnostics) result.diagnostics.push(diagnostic);
			} catch (error:Dynamic) {
				result.diagnostics.push('[codename-options-xml] Could not read ' + relative + ': ' + Std.string(error));
			}
		}
		#end
		return result;
	}

	public static function value(saveData:Dynamic, option:Dynamic):Bool {
		if (saveData == null || option == null || Reflect.field(option, 'kind') != 'checkbox') return false;
		var id:Dynamic = Reflect.field(option, 'id');
		if (!Std.isOfType(id, String) || !validSaveField(cast id)) return false;
		var stored:Dynamic = saveData.getField(cast id);
		return stored == true;
	}

	/** Toggle one XML-defined checkbox in this selected owner's private save. */
	public static function toggle(saveData:Dynamic, option:Dynamic):Bool {
		if (saveData == null || option == null || Reflect.field(option, 'kind') != 'checkbox') return false;
		var id:Dynamic = Reflect.field(option, 'id');
		if (!Std.isOfType(id, String) || !validSaveField(cast id)) return false;
		saveData.setField(cast id, !value(saveData, option));
		return true;
	}

	static function validSaveField(name:String):Bool
		return name != null && StringTools.trim(name) != '' && name != 'codenameImportedModData'
			&& name != '__proto__' && name != 'prototype' && name != 'constructor';
}
