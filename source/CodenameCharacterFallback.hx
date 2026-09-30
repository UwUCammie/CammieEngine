package;

typedef CodenameCharacterFallbackReference = {
	var id:Null<String>;
	var configured:Bool;
	var diagnostic:Null<String>;
}

typedef CodenameCharacterSourceDefinition = {
	var requestedId:String;
	var definitionId:String;
	var xmlText:String;
	var usedFallback:Bool;
	var configuredFallback:Bool;
	var fallbackId:String;
	var diagnostic:Null<String>;
	/** Asset root may be a receipt-verified base dependency; scripts still use root. */
	@:optional var assetRoot:String;
	@:optional var fallbackAssetFiles:Array<String>;
}

/** Source-engine missing-character fallback, resolved only inside one owner. */
class CodenameCharacterFallback {
	static var configPaths:Array<String> = [
		'data/config/modpack.ini', 'data/config/flags.ini', 'flags.ini'
	];

	public static function defaultReference(root:String,
		resolve:(String, String)->Null<String>, read:(String, String)->String):CodenameCharacterFallbackReference {
		if (root == null || root == '' || resolve == null || read == null)
			return {id:null, configured:false, diagnostic:'selected owner is unavailable'};
		for (candidate in configPaths) {
			var relative = resolve(root, candidate);
			if (relative == null) continue;
			var defaults:Dynamic;
			try defaults = CodenameSongMetadata.configDefaults(read(root, relative)) catch (error:Dynamic)
				return {id:null, configured:false,
					diagnostic:'Codename flags could not be read: ' + relative + ' (' + Std.string(error) + ')'};
			if (!Reflect.hasField(defaults, 'characterFallback')) continue;
			var configuredId = StringTools.trim(Std.string(Reflect.field(defaults, 'characterFallback')));
			if (!CodenameScriptDiscovery.safeRelativeName(configuredId))
				return {id:null, configured:true,
					diagnostic:'Codename DEFAULT_CHARACTER cannot be represented safely: ' + configuredId};
			return {id:configuredId, configured:true, diagnostic:null};
		}
		return {id:'bf', configured:false, diagnostic:null};
	}

	/** Return the exact source XML when present; otherwise use Codename's
	 * owner-configured DEFAULT_CHARACTER (engine default: bf). A broken existing
	 * XML definition stays broken instead of silently borrowing another actor. */
	public static function resolve(root:String, requestedId:String,
		resolve:(String, String)->Null<String>, read:(String, String)->String,
		?dependency:(String, String)->Null<CodenameBaseCharacterDependency.CodenameBaseCharacterDependencyResolution>):CodenameCharacterSourceDefinition {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeRelativeName(requestedId))
			return null;
		var requestedPath = resolve(root, 'data/characters/' + requestedId + '.xml');
		if (requestedPath != null) {
			var requestedXml:String;
			try requestedXml = read(root, requestedPath) catch (error:Dynamic)
				return {requestedId:requestedId, definitionId:requestedId, xmlText:null,
					usedFallback:false, configuredFallback:false, fallbackId:requestedId,
					diagnostic:'Codename character XML could not be read: ' + requestedPath
						+ ' (' + Std.string(error) + ')'};
			if (!validCharacterXml(requestedXml))
				return {requestedId:requestedId, definitionId:requestedId, xmlText:null,
					usedFallback:false, configuredFallback:false, fallbackId:requestedId,
					diagnostic:'Codename character XML is invalid: ' + requestedPath};
			return {requestedId:requestedId, definitionId:requestedId, xmlText:requestedXml,
				usedFallback:false, configuredFallback:false, fallbackId:requestedId,
				diagnostic:null, assetRoot:root, fallbackAssetFiles:[]};
		}
		var fallback = defaultReference(root, resolve, read);
		if (fallback.id == null)
			return {requestedId:requestedId, definitionId:null, xmlText:null, usedFallback:false,
				configuredFallback:fallback.configured, fallbackId:null,
				diagnostic:fallback.diagnostic == null ? 'Codename DEFAULT_CHARACTER is unavailable' : fallback.diagnostic};
		var fallbackPath = resolve(root, 'data/characters/' + fallback.id + '.xml');
		if (fallbackPath != null) {
			var fallbackXml:String;
			try fallbackXml = read(root, fallbackPath) catch (error:Dynamic)
				return {requestedId:requestedId, definitionId:null, xmlText:null, usedFallback:false,
					configuredFallback:fallback.configured, fallbackId:fallback.id,
					diagnostic:'Codename DEFAULT_CHARACTER XML could not be read: ' + fallbackPath
						+ ' (' + Std.string(error) + ')'};
			if (!validCharacterXml(fallbackXml))
				return {requestedId:requestedId, definitionId:null, xmlText:null, usedFallback:false,
					configuredFallback:fallback.configured, fallbackId:fallback.id,
					diagnostic:'Codename DEFAULT_CHARACTER XML is invalid: ' + fallbackPath};
			return {requestedId:requestedId, definitionId:fallback.id, xmlText:fallbackXml,
				usedFallback:true, configuredFallback:fallback.configured, fallbackId:fallback.id,
				diagnostic:null, assetRoot:root, fallbackAssetFiles:[]};
		}
		if (dependency != null) {
			var materialized = dependency(root, fallback.id);
			if (materialized != null && materialized.definitionId == fallback.id
				&& validCharacterXml(materialized.xmlText) && materialized.assetRoot != null
				&& materialized.assetFiles != null)
				return {requestedId:requestedId, definitionId:fallback.id, xmlText:materialized.xmlText,
					usedFallback:true, configuredFallback:fallback.configured, fallbackId:fallback.id,
					diagnostic:null, assetRoot:materialized.assetRoot,
					fallbackAssetFiles:materialized.assetFiles};
		}
		var unavailable = fallback.id.toLowerCase() == requestedId.toLowerCase()
			? 'missing character is itself DEFAULT_CHARACTER: ' + fallback.id
			: 'Codename DEFAULT_CHARACTER XML is unavailable: ' + fallback.id;
		return {requestedId:requestedId, definitionId:null, xmlText:null, usedFallback:false,
			configuredFallback:fallback.configured, fallbackId:fallback.id, diagnostic:unavailable};
	}

	static function validCharacterXml(contents:String):Bool {
		if (contents == null || StringTools.trim(contents) == '') return false;
		try {
			var root = Xml.parse(contents).firstElement();
			return root != null && root.nodeType == Xml.Element && root.nodeName == 'character';
		} catch (_:Dynamic) return false;
	}
}
