package;

import haxe.io.Path;
import PsychAssetProfile;
#if sys
import sys.FileSystem;
#end

/** Compiled Lime files enter the same receipt-backed mapping/publication path. */
@:access(PsychAssetProfile)
class SourceCompiledAssetProfile {
	public static function resolve(content:String, selectedRoot:String, receipt:Dynamic,
		result:PsychAssetProfileResult, cancelled:Void->Bool):PsychAssetProfileResult {
		#if sys
		var defaultPath = Path.join([selectedRoot,'manifest/default.json']);
		if (!FileSystem.exists(defaultPath)) return result;
		result.diagnostics = [];
		result.provenance = 'receipt-bound'; result.complete = true;
		result.projectRelative = PsychAssetProfile.joinRelative(result.rootRelative,'manifest/default.json');
		result.compiledManifests = true;
		// Entire libraries may be embedded in the executable and absent on disk.
		// File manifests establish their own IDs, not the complete registration set.
		result.librariesComplete = false;
		var candidateByIdentity:Map<String,Int> = [];
		var files = FileSystem.readDirectory(Path.directory(defaultPath)); files.sort(Reflect.compare);
		var total = 0;
		var assetCount = 0;
		for (name in files) {
			PsychAssetProfile.checkpointProjectWork(cancelled);
			if (!StringTools.endsWith(name,'.json')) continue;
			if (result.inputFiles.length >= 64) return PsychAssetProfile.fail(result,'manifest-count-limit','Too many compiled manifests');
			var relative = 'manifest/'+name;
			var canonical = PsychAssetProfile.containedSourcePath(selectedRoot,relative);
			if (canonical == '' || FileSystem.isDirectory(canonical))
				return PsychAssetProfile.fail(result,'manifest-path-invalid','Compiled manifest leaves its selected root');
			var snapshotRelative = PsychAssetProfile.joinRelative(result.rootRelative,relative);
			var entry = PsychAssetProfile.receiptFile(receipt,snapshotRelative,result);
			var bytes = PsychAssetProfile.verifiedProjectBytes(canonical,entry,SourceCompiledAssetManifest.MAX_BYTES,result,'manifest-hash-mismatch');
			if (bytes == null) return result;
			total += bytes.length;
			if (total > 32*1024*1024) return PsychAssetProfile.fail(result,'manifest-bytes-limit','Compiled manifest set exceeds limit');
			var digest = haxe.crypto.Sha256.make(bytes).toHex();
			result.inputFiles.push({path:snapshotRelative,size:bytes.length,sha256:digest,parentInclude:null,order:result.inputFiles.length});
			if (name == 'default.json') result.projectSha256 = digest;
			var manifest:Dynamic;
			try manifest = SourceCompiledAssetManifest.parse(bytes.toString()) catch(error:Dynamic)
				return PsychAssetProfile.fail(result,'manifest-invalid',name+': '+Std.string(error));
			var library = name.substr(0,name.length-5);
			if (library == '' || library.indexOf(':') >= 0 || library.indexOf('$') >= 0)
				return PsychAssetProfile.fail(result,'manifest-library-invalid','Invalid emitted library filename');
			var custom = (manifest.libraryType != null && manifest.libraryType != '')
				|| (manifest.libraryArgs != null && (cast manifest.libraryArgs:Array<Dynamic>).length != 0);
			result.libraries.push({order:result.libraries.length,name:library,state:'enabled',sourcePath:'',
				type:custom ? Std.string(manifest.libraryType) : '',typeState:'known',embed:null,embedState:'known',
				preload:false,preloadState:'unresolved',generate:false,generateState:'known',prefix:'',prefixState:'known',conditions:[]});
			if (custom) {
				result.complete = false;
				result.diagnostics.push('manifest-library-unsupported: '+library+' uses custom loading semantics');
				continue;
			}
			var root:String = manifest.rootPath == null ? '' : manifest.rootPath;
			var resolvedRoot = relativePath('manifest',root,true);
			if (resolvedRoot == null) return PsychAssetProfile.fail(result,'manifest-root-escape','Compiled library root leaves the selected source');
			for (asset in (cast manifest.assets:Array<Dynamic>)) {
				PsychAssetProfile.checkpointProjectWork(cancelled);
				if (++assetCount > SourceCompiledAssetManifest.MAX_ASSETS)
					return PsychAssetProfile.fail(result,'manifest-asset-limit','Compiled manifest set exceeds asset limit');
				var key = library + '\x00' + asset.id;
				if (candidateByIdentity.exists(key)) {result.candidates[candidateByIdentity.get(key)] = null; candidateByIdentity.remove(key);}
				if (asset.className != null || asset.path == null || asset.path == '') {
					result.complete = false;
					result.diagnostics.push('manifest-embedded-unavailable: '+library+':'+asset.id);
					continue;
				}
				var source = relativePath(resolvedRoot,asset.path,false);
				if (source == null) return PsychAssetProfile.fail(result,'manifest-asset-escape','Compiled asset leaves the selected source: '+asset.id);
				var type:String = asset.type; // The shared publication policy validates declared Lime types.
				candidateByIdentity.set(key,result.candidates.length);
				result.candidates.push({order:result.candidates.length,sourceRelative:source,targetRelative:source,
					includePatterns:[],excludePatterns:[],conditions:[],state:'enabled',type:type,embed:'false',
					library:library,assetId:asset.id,assetIdOverride:true});
			}
		}
		result.candidates = result.candidates.filter(function(candidate) return candidate != null);
		if (result.projectSha256 == '') return PsychAssetProfile.fail(result,'manifest-default-missing','Default manifest was not authenticated');
		return result;
		#else
		return result;
		#end
	}
	/** Resolve the manifest's relative physical path without accepting a source escape. */
	public static function relativePath(base:String, value:String, allowEmpty:Bool):Null<String> {
		if (value == null || value.indexOf(':') >= 0 || value.indexOf('\\') >= 0
			|| value.indexOf('\x00') >= 0 || StringTools.startsWith(value,'/')) return null;
		var parts:Array<String> = base == '' ? [] : base.split('/');
		for (part in value.split('/')) {
			if (part == '' || part == '.') continue;
			if (part == '..') {if (parts.length == 0) return null; parts.pop();}
			else parts.push(part);
		}
		return parts.length == 0 && !allowEmpty ? null : parts.join('/');
	}
}
