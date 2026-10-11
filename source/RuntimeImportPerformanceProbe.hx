package;

#if sys
import haxe.io.Bytes;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import ImportSourceSnapshot.ImportSnapshotSha256;
#end

/** Opt-in isolated benchmark of identical portable/native capture, verify and refresh work. */
class RuntimeImportPerformanceProbe {
	public static function run():Void {
		#if sys
		var root = Sys.getEnv('CAMMIE_IMPORT_PERFORMANCE_DIR');
		if (root == null) return;
		if (FileSystem.exists(root)) throw 'Import benchmark requires a fresh output directory';
		FileSystem.createDirectory(root);
		var capability = NativeStreamingSha256.create();
		if (capability == null) throw 'Native hash acceleration unavailable';
		capability.close();
		var results:Array<Dynamic> = [];
		var started = haxe.Timer.stamp();
		var bytes = Bytes.alloc(8 * 1024 * 1024);
		for (i in 0...bytes.length) bytes.set(i,(i * 31 + (i >> 8)) & 255);
		for (size in [0,1,55,56,63,64,65,127,128,129,65536,1000000]) {
			var expected = haxe.crypto.Sha256.make(bytes.sub(0,size)).toHex();
			for (portable in [true,false]) {
				ImportSnapshotSha256.forcePortable = portable;
				var hash = new ImportSnapshotSha256();
				var at = 0;
				while (at < size) {var n = Std.int(Math.min(size-at,137));hash.update(bytes,at,n);at+=n;}
				if (hash.digestHex() != expected) throw 'Hash mismatch: '+size;
				var rejected = false;try hash.update(bytes,0,1) catch (_:Dynamic) rejected = true;
				if (!rejected) throw 'Finalized stream accepted bytes';
			}
		}
		// Synthetic media packages keep conversion out of the measured I/O phases.
		for (pack in 0...24) {
			var donor = root+'/donors/pack'+pack;
			FileSystem.createDirectory(donor);
			File.saveBytes(donor+'/media.bin',bytes);
			for (j in 0...16) File.saveContent(donor+'/entry'+j+'.json',haxe.Json.stringify({packageId:pack,entry:j,data:'fixture'}));
		}
		for (portable in [true,false]) {
			ImportSnapshotSha256.forcePortable = portable;
			var mode = portable ? 'portable' : 'native';
			var install = root+'/'+mode+'/install';FileSystem.createDirectory(install);
			var totals:Dynamic = {mode:mode,packages:24,mediaMiB:192,capture:0.0,verify:0.0,install:0.0,refresh:0.0};
			for (pack in 0...24) {
				var donor = root+'/donors/pack'+pack;
				var now = haxe.Timer.stamp();
				var snapshot = ImportSourceSnapshot.capture(donor,root+'/'+mode+'/snapshots','Psych Engine','benchmark');
				if (!snapshot.complete) throw snapshot.error;
				totals.capture += haxe.Timer.stamp()-now;
				now = haxe.Timer.stamp();ImportSourceSnapshot.verify(snapshot.snapshotRoot,snapshot.snapshotId);
				totals.verify += haxe.Timer.stamp()-now;
				var owner = 'benchmark:'+pack;
				var ownedRoot = 'assets/imported_mods/pack'+pack;
				var files = FileSystem.readDirectory(donor);files.sort(Reflect.compare);
				var outputs = [for (file in files) {path:ownedRoot+'/'+file,stagedPath:file}];
				for (refresh in [false,true]) {
					now = haxe.Timer.stamp();
					var result = ImportRefreshTransaction.apply(install,donor,install+'/import-cache/state',owner,[ownedRoot],outputs);
					if (result.status != ImportRefreshTransaction.STATUS_APPLIED) throw haxe.Json.stringify(result);
					if (refresh) totals.refresh += haxe.Timer.stamp()-now;else totals.install += haxe.Timer.stamp()-now;
				}
				Sys.println('IMPORT_BENCH_PROGRESS|'+haxe.Json.stringify({mode:mode,completed:pack+1,totals:totals}));
			}
			results.push(totals);Sys.println('IMPORT_BENCH_RESULT|'+haxe.Json.stringify(totals));
			File.saveContent(root+'/results.json',haxe.Json.stringify(results,null,'  '));
		}
		ImportSnapshotSha256.forcePortable = false;
		Sys.println('IMPORT_BENCH_COMPLETE|'+(haxe.Timer.stamp()-started));
		Sys.exit(0);
		#end
	}
}
