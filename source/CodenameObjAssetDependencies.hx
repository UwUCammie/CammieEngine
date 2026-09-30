package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef CodenameObjAssetDependencyFile = {
	var source:String;
	var relative:String;
	@:optional var sourceRelative:String;
}

/** Plans owner-local material and diffuse-texture files consumed by a
	Codename OBJ. This follows the same `mtllib` and `map_Kd` subset as
	CodenameFlx3DAssetSource; it never searches another import or the game base. */
class CodenameObjAssetDependencies {
	public static function filesFor(ownerRoot:String, objRelative:String):Array<CodenameObjAssetDependencyFile> {
		var result:Array<CodenameObjAssetDependencyFile> = [];
		#if sys
		if (ownerRoot == null || objRelative == null || !FileSystem.isDirectory(ownerRoot)
			|| !CodenameScriptDiscovery.safeRelativeName(objRelative))
			return result;

		var objResolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, objRelative);
		if (objResolution.relative == null)
			return result;
		var objSource = Path.join([ownerRoot, objResolution.relative]);
		var objContent:String;
		try objContent = File.getContent(objSource) catch (_:Dynamic) return result;
		var objSourceDirectory = Path.directory(objResolution.relative);
		var objDestinationDirectory = Path.directory(objRelative);
		var seen:Map<String, Bool> = new Map();

		for (line in objContent.split('\n')) {
			var words = tokens(line);
			if (words.length < 2 || words[0] != 'mtllib')
				continue;
			// Away3D consumes the first library name on each mtllib directive,
			// matching the runtime resolver's current contract.
			var materialName = normalizeName(words[1]);
			if (materialName == null)
				continue;
			var material = resolveDependency(ownerRoot, objSourceDirectory,
				objDestinationDirectory, materialName);
			if (material == null)
				continue;
			appendUnique(result, seen, material);
			var materialContent:String;
			try materialContent = File.getContent(material.source) catch (_:Dynamic) continue;

			var materialSourceDirectory = Path.directory(material.sourceRelative);
			var materialDestinationDirectory = Path.directory(material.relative);
			for (materialLine in materialContent.split('\n')) {
				var materialWords = tokens(materialLine);
				if (materialWords.length < 2 || materialWords[0] != 'map_Kd')
					continue;
				var nameIndex = textureFilenameIndex(materialWords);
				if (nameIndex >= materialWords.length)
					continue;
				var textureName = normalizeName(materialWords.slice(nameIndex).join(' '));
				if (textureName == null)
					continue;
				var texture = resolveDependency(ownerRoot, materialSourceDirectory,
					materialDestinationDirectory, textureName);
				if (texture != null)
					appendUnique(result, seen, texture);
			}
		}
		#end
		return result;
	}

	#if sys
	static function resolveDependency(ownerRoot:String, sourceDirectory:String,
		destinationDirectory:String, name:String):Null<CodenameObjAssetDependencyFile> {
		if (name == null)
			return null;
		var sourceRelative = joinRelative(sourceDirectory, name);
		var destinationRelative = joinRelative(destinationDirectory, name);
		if (!CodenameScriptDiscovery.safeRelativeName(sourceRelative)
			|| !CodenameScriptDiscovery.safeRelativeName(destinationRelative))
			return null;
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, sourceRelative);
		if (resolution.relative == null)
			return null;
		var source = Path.join([ownerRoot, resolution.relative]);
		if (FileSystem.isDirectory(source) || !CodenameScriptDiscovery.withinRoot(ownerRoot, source))
			return null;
		return {source:source, relative:destinationRelative, sourceRelative:resolution.relative};
	}

	static function appendUnique(result:Array<CodenameObjAssetDependencyFile>,
		seen:Map<String, Bool>, file:CodenameObjAssetDependencyFile):Void {
		if (file == null || seen.exists(file.relative))
			return;
		seen.set(file.relative, true);
		result.push(file);
	}
	#end

	static function joinRelative(directory:String, name:String):String
		return directory == null || directory == '' || directory == '.' ? name : directory + '/' + name;

	static function normalizeName(name:String):Null<String> {
		if (name == null)
			return null;
		var clean = StringTools.trim(name).replace('\\', '/');
		if (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.indexOf('?') >= 0 || clean.indexOf('#') >= 0)
			return null;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return null;
		return clean;
	}

	static function textureFilenameIndex(words:Array<String>):Int {
		var index = 1;
		while (index < words.length) {
			switch (words[index]) {
				case '-blendu', '-blendv', '-cc', '-clamp', '-texres': index += 2;
				case '-mm': index += 3;
				case '-o', '-s', '-t': index += 4;
				default: return index;
			}
		}
		return index;
	}

	static function tokens(line:String):Array<String>
		return ~/[	 ]+/g.split(StringTools.trim(line));
}
