package;

#if sys
import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import ImportRefreshTransaction.ImportRefreshManifest;
import ImportRefreshTransaction.ImportRefreshStagedOutput;

/** Derived analysis migration. Never reconverts source or claims chart/media bytes. */
@:access(ImportRefreshTransaction)
class ChartDifficultyRefresh {
	static function parseJson(text:String):Dynamic {
		var end = text.length;
		while (end > 0 && [0,9,10,13,32].indexOf(text.charCodeAt(end-1)) >= 0) end--;
		return tjson.TJSON.parse(text.substr(0,end));
	}
	static inline var MAX_CHART_BYTES:Int = 8388608;
	static inline var MAX_METADATA_BYTES:Int = 1048576;
	static function readText(install:String,path:String,limit:Int,reads:Map<String,String>):Null<String> {
		var resolved = ImportRefreshTransaction.safeChild(install,path,false);
		if (!FileSystem.exists(resolved)) {reads.set(path,'missing');return null;}
		if (FileSystem.isDirectory(resolved)) throw 'Chart analysis input is not a regular file: '+path;
		if (FileSystem.stat(resolved).size > limit) {reads.set(path,'oversized:'+FileSystem.stat(resolved).size);return null;}
		var text = File.getContent(resolved);
		reads.set(path,haxe.crypto.Sha256.make(haxe.io.Bytes.ofString(text)).toHex());return text;
	}
	/** Script files directly inside one imported folder. Optional content: a
	 * missing or unreadable folder contributes nothing. */
	static function listScripts(install:String,directory:String):Array<String> {
		try {
			var resolved = ImportRefreshTransaction.safeChild(install,directory,false);
			if (!FileSystem.exists(resolved) || !FileSystem.isDirectory(resolved)) return [];
			var names = [for (name in FileSystem.readDirectory(resolved))
				if (ChartMechanicScan.isScript(name) && !FileSystem.isDirectory(Path.join([resolved,name]))) name];
			names.sort(Reflect.compare);
			return names;
		} catch (_:Dynamic) return [];
	}
	/** What each of an owner's note type scripts does, read without running it. */
	static function noteHazards(install:String,owner:String,reads:Map<String,String>):Map<String,ChartMechanicScan.NoteScriptHazard> {
		var result:Map<String,ChartMechanicScan.NoteScriptHazard> = [];
		for (directory in ChartMechanicScan.noteScriptFolders()) for (name in listScripts(install,owner+'/'+directory)) {
			ImportWorkScheduler.cooperate();
			var kind = NoteTypeCompat.canonical(Path.withoutExtension(name)).toLowerCase();
			if (kind == '' || result.exists(kind)) continue;
			var text = readText(install,owner+'/'+directory+'/'+name,ChartMechanicScan.MAX_SCRIPT_BYTES,reads);
			var hazard = text == null ? null : ChartMechanicScan.noteHazard(text,ChartMechanicScan.isLua(name));
			if (hazard != null) result.set(kind,hazard);
		}
		return result;
	}
	static function songModchart(install:String,owner:String,sourceFolder:String,folder:String,reads:Map<String,String>):Float {
		var scripts:Array<ChartMechanicScan.ChartScriptText> = [];
		if (owner != null && sourceFolder != null) for (directory in ChartMechanicScan.songScriptFolders(sourceFolder)) for (name in listScripts(install,owner+'/'+directory)) {
			if (scripts.length >= ChartMechanicScan.MAX_SONG_SCRIPTS) break;
			ImportWorkScheduler.cooperate();
			var text = readText(install,owner+'/'+directory+'/'+name,ChartMechanicScan.MAX_SCRIPT_BYTES,reads);
			if (text != null) scripts.push({text:text,lua:ChartMechanicScan.isLua(name)});
		}
		return ChartMechanicScan.modchart(scripts,readText(install,folder+'/events.json',MAX_METADATA_BYTES,reads));
	}
	public static function refresh(install:String,state:String,owner:String,manifest:ImportRefreshManifest,?progress:Dynamic->Void):ImportRefreshManifest {
		if (manifest.revision != null && Reflect.field(manifest.revision,'chartAnalysisVersion') == ChartDifficultyAnalysis.VERSION) return manifest;
		var folders:Map<String,Array<String>> = [];
		for (entry in manifest.files) {
			ImportWorkScheduler.cooperate();
			var path = entry.path;
			if (!StringTools.startsWith(path,'assets/data/') || !StringTools.endsWith(path,'.json')) continue;
			var parts = path.split('/'); if (parts.length != 4) continue;
			var folder = parts[2]; var file = parts[3];
			if (file != folder+'.json' && !StringTools.startsWith(file,folder+'-')) continue;
			var key = Path.directory(path);
			if (!folders.exists(key)) folders.set(key,[]);
			folders.get(key).push(path);
		}
		var stage = Path.join([install,'import-cache','analysis-'+Std.string(Sys.time()).split('.').join('-')+'-'+Std.random(1000000)]);
		FileSystem.createDirectory(stage);
		var outputs:Array<ImportRefreshStagedOutput> = []; var generated:Array<String> = [];
		var reads:Map<String,String> = []; var completed = 0; var total = 0; for (_ in folders.keys()) total++;
		var hazardsByOwner:Map<String,Map<String,ChartMechanicScan.NoteScriptHazard>> = [];
		try {
			for (folder in folders.keys()) {
				ImportWorkScheduler.cooperate();
				if (progress != null) progress({phase:'analyzing-chart-difficulty',current:folder,completed:completed,total:total});
				var definitions:Array<Dynamic> = []; var noteText = readText(install,folder+'/noteInfo.json',MAX_METADATA_BYTES,reads);
				if (noteText != null) {
					var raw:Dynamic = parseJson(noteText);
					if (Std.isOfType(raw,Array)) definitions = cast raw;
				}
				var nightmare = false; var provenanceText = readText(install,folder+'/importProvenance.json',MAX_METADATA_BYTES,reads);
				var sourceOwner:Null<String> = null; var sourceFolder:Null<String> = null;
				if (provenanceText != null) {
					var raw:Dynamic = parseJson(provenanceText);
					nightmare = Reflect.field(raw,'sourceEngine') == 'Nightmare Vision';
					sourceOwner = ChartMechanicScan.safeOwner(Reflect.field(raw,'sourceOwner'));
					var named:Dynamic = Reflect.field(raw,'sourceFolder');
					if (sourceOwner != null && ChartMechanicScan.safeName(named)) sourceFolder = cast named;
				}
				// Retained donor scripts are read, never run, for mechanics that
				// converted note metadata cannot express.
				if (sourceOwner != null && !hazardsByOwner.exists(sourceOwner)) hazardsByOwner.set(sourceOwner,noteHazards(install,sourceOwner,reads));
				var context:ChartMechanicScan.ChartAnalysisContext = {
					noteHazards:sourceOwner == null ? null : hazardsByOwner.get(sourceOwner),
					modchart:songModchart(install,sourceOwner,sourceFolder,folder,reads)};
				var table:Dynamic = {}; var count = 0;
				for (path in folders.get(folder)) {
					ImportWorkScheduler.cooperate();
					var chartText = readText(install,path,MAX_CHART_BYTES,reads);
					if (chartText == null) {
						if (StringTools.startsWith(reads.get(path),'oversized:')) continue;
						throw 'Owned chart is missing: '+path;
					}
					var result = ChartDifficultyAnalysis.analyze(parseJson(chartText),definitions,nightmare,context);
					if (result == null) continue;
					var song = folder.split('/').pop(); var name = Path.withoutExtension(Path.withoutDirectory(path));
					var difficulty = name == song ? 'normal' : name.substr(song.length+1);
					Reflect.setField(table,difficulty.toLowerCase(),result); count++;
				}
				if (count > 0) {
					var name = Std.string(outputs.length)+'.json'; File.saveContent(Path.join([stage,name]),Json.stringify(table)); generated.push(name);
					outputs.push({path:folder+'/chartDensity.json',stagedPath:name});
				}
				completed++;
			}
			if (progress != null) progress({phase:'analyzing-chart-difficulty',current:'',completed:total,total:total});
			for (path in reads.keys()) {
				ImportWorkScheduler.cooperate();
				var resolved = ImportRefreshTransaction.safeChild(install,path,false);
				var expected = reads.get(path);
				var hash = StringTools.startsWith(expected,'oversized:') && FileSystem.exists(resolved) ? 'oversized:'+FileSystem.stat(resolved).size
					: FileSystem.exists(resolved) ? ImportSourceSnapshot.sha256File(resolved) : 'missing';
				if (hash != reads.get(path)) throw 'Chart analysis input changed during calculation: '+path;
			}
			var revision:Dynamic = manifest.revision == null ? {} : Reflect.copy(manifest.revision);
			Reflect.setField(revision,'chartAnalysisVersion',ChartDifficultyAnalysis.VERSION);
			Reflect.setField(revision,'chartAnalysisWarnings',[for(path in reads.keys()) if(StringTools.startsWith(reads.get(path),'oversized:')) 'Difficulty analysis skipped oversized input: '+path]);
			var result = ImportRefreshTransaction.apply(install,stage,state,owner,manifest.ownedRoots,outputs,revision,null,null,progress,true);
			if (result.status != ImportRefreshTransaction.STATUS_APPLIED) throw 'Difficulty analysis refresh '+result.status+': '+[for(c in result.conflicts)c.path+' ('+c.reason+')'].join(', ');
			for (name in generated) FileSystem.deleteFile(Path.join([stage,name])); FileSystem.deleteDirectory(stage);
			return ImportRefreshTransaction.loadManifest(state,owner);
		} catch (error:Dynamic) {
			for (name in generated) if (FileSystem.exists(Path.join([stage,name]))) FileSystem.deleteFile(Path.join([stage,name]));
			FileSystem.deleteDirectory(stage); throw error;
		}
	}
}
#end
