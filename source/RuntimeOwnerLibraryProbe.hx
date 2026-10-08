package;

#if sys
import flixel.FlxG;
import haxe.crypto.Sha256;
import haxe.Int64;
import haxe.io.Bytes;
import haxe.io.Path;
import lime.app.Future;
import lime.media.AudioBuffer;
import lime.media.vorbis.VorbisFile;
import lime.text.Font as LimeFont;
import lime.utils.AssetLibrary;
import lime.utils.AssetType;
import lime.utils.Assets as LimeAssets;
import openfl.display.BitmapData;
import openfl.media.Sound;
import openfl.text.Font as OpenFlFont;
import openfl.utils.Assets as OpenFlAssets;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;

using StringTools;

/** Generated, isolated imports only: exercise the real receipt-bound file AssetLibrary path. */
@:access(RuntimeSmokeHarness)
@:access(PsychOwnerAssetLibraryCache)
@:access(lime.utils.AssetLibrary)
@:access(lime.media.AudioBuffer)
@:access(openfl.media.Sound)
@:access(openfl.utils.AssetLibrary)
class RuntimeOwnerLibraryProbe {
	static var started:Bool = false;
	static var phase:Int = 0;
	static var startedAt:Float = 0;
	static var workerMutex:Mutex = new Mutex();
	static var workerDone:Bool = false;
	static var workerError:String = '';
	static var workerResult:Dynamic;
	static var request:Dynamic;
	static var unknownSource:String;
	static var revisionBeforeUnrelatedImport:Int = -1;
	static var owners:Array<Dynamic> = [];
	static var cppOwners:Array<Dynamic> = [];
	static var unknownOwner:Dynamic;
	static var limeFutures:Array<Future<AssetLibrary>> = [];
	static var openFlFutures:Array<Dynamic> = [];
	static var cppLibraryFutures:Array<Future<Dynamic>> = [];
	static var cppOpenFlLibraryFutures:Array<Future<Dynamic>> = [];
	static var cppTypedFutures:Array<Future<Dynamic>> = [];
	static var globalSentinel:openfl.utils.AssetLibrary;
	static var cppGlobalSentinel:openfl.utils.AssetLibrary;
	static var cppAlphaOriginalSound:Bytes;
	static var cppAlphaOriginalStream:Bytes;
	static var cppAlphaOriginalFont:Bytes;
	static var cppAlphaChangedSoundPath:String;
	static var cppAlphaChangedStreamPath:String;
	static var cppAlphaChangedFontPath:String;

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_OWNER_LIBRARY_SMOKE') == '1';

	static function check(value:Bool, message:String):Void if (!value) throw message;

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			if (!started) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
				started = true;
				startedAt = Sys.time();
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null,
					'Owner-library smoke requires muted audio and isolated saves');
				request = CoolUtil.parseJson(File.getContent('tmp/owner-library-request.json'));
				check(request != null && request.kind == 'psych-owner-library-typed-media',
					'Expected generated Psych owner-library fixture');
				check(request.sourceRoot != null && request.cppSourceRoot != null
					&& request.unknownSourceRoot != null && request.sourceRoot != request.cppSourceRoot
					&& request.sourceRoot != request.unknownSourceRoot
					&& request.cppSourceRoot != request.unknownSourceRoot,
				'Three separate generated source selections are required');
				unknownSource = Std.string(request.unknownSourceRoot);
				check(request.warmLibrary != null && request.lazyLibrary != null
					&& request.warmLibrary != request.lazyLibrary,
					'Unique warm and lazy owner library names are required');
				check(request.cppLibrary != null && request.cppSoundId != null
					&& request.cppMusicId != null && request.cppStreamMusicId != null
					&& request.cppFontId != null,
				'Known-target typed media fixture metadata is missing');
				startImports(Std.string(request.sourceRoot));
				phase = 1;
				return;
			}
			check(Sys.time() - startedAt < 75, 'Owner-library native probe timed out');
			if (phase == 1) {
				workerMutex.acquire();
				var done = workerDone;
				var error = workerError;
				var result = workerResult;
				workerMutex.release();
				if (error != '') throw 'Actual retained import failed: ' + error;
				if (!done) return;
				if (ImportRefreshManager.browseTick().busy) return;
				check(result != null && result.owners != null && result.owners.length == 2,
					'Expected two actual scanner-discovered owner roots');
				owners = cast result.owners;
				verifyReadyOwners();
				beginLibraryLoads();
				phase = 2;
				return;
			}
			if (phase == 2) {
				for (future in limeFutures)
					if (future.isError) throw 'Lime owner library load failed: ' + Std.string(future.error);
				for (value in openFlFutures) {
					var future:Future<Dynamic> = cast value;
					if (future != null && future.isError)
						throw 'OpenFL owner library load failed: ' + Std.string(future.error);
				}
				for (future in limeFutures) if (!future.isComplete) return;
				for (value in openFlFutures) {
					var future:Future<Dynamic> = cast value;
					if (future == null || !future.isComplete) return;
				}
				verifyLoadedLibraries();
				startCppImport(Std.string(request.cppSourceRoot));
				phase = 3;
				return;
			}
			if (phase == 3) {
				workerMutex.acquire();
				var done = workerDone;
				var error = workerError;
				var result = workerResult;
				workerMutex.release();
				if (error != '') throw 'Actual retained CPP-target import failed: ' + error;
				if (!done || ImportRefreshManager.browseTick().busy) return;
				check(result != null && result.owners != null && result.owners.length == 2,
					'Expected two actual scanner-discovered CPP-target owner roots');
				cppOwners = cast result.owners;
				verifyReadyCppOwners();
				beginCppLibraryLoads();
				phase = 4;
				return;
			}
			if (phase == 4) {
				if (futureSetPending(cppLibraryFutures, 'Lime CPP owner library load')
					|| futureSetPending(cppOpenFlLibraryFutures, 'OpenFL CPP owner library load')) return;
				verifyCppLoadedLibraries();
				phase = 5;
				return;
			}
			if (phase == 5) {
				if (futureSetPending(cppTypedFutures, 'Typed CPP asset load')) return;
				verifyCppTypedLoads();
				verifyCppSourceFailures();
				startCppRefresh(Std.string(request.cppSourceRoot));
				phase = 6;
				return;
			}
			if (phase == 6) {
				workerMutex.acquire();
				var done = workerDone;
				var error = workerError;
				var result = workerResult;
				workerMutex.release();
				if (error != '') throw 'Actual changed-proof CPP refresh failed: ' + error;
				if (!done || ImportRefreshManager.browseTick().busy) return;
				check(result != null && result.owners != null && result.owners.length == 2
					&& result.copiedAssets > 0,
					'Actual CPP refresh did not publish both retained owner roots');
				for (index in 0...cppOwners.length)
					check(Reflect.field(result.owners[index], 'namespace') == cppOwners[index].namespace,
						'CPP refresh changed the selected owner namespace');
				verifyCppRefresh();
				revisionBeforeUnrelatedImport = ImportRefreshManager.availabilityRevision();
				startUnknownImport(unknownSource);
				phase = 7;
				return;
			}
			if (phase == 7) {
				workerMutex.acquire();
				var done = workerDone;
				var error = workerError;
				var result = workerResult;
				workerMutex.release();
				if (error != '') throw 'Actual uncaptured-target import failed: ' + error;
				if (!done || ImportRefreshManager.browseTick().busy) return;
				check(ImportRefreshManager.availabilityRevision() > revisionBeforeUnrelatedImport,
					'Unrelated third-owner import did not advance the manager revision');
				unknownOwner = Reflect.field(result, 'unknown');
				check(unknownOwner != null, 'Uncaptured-target owner summary was not returned');
				verifyUnknownTargetFailsClosed();
				verifyUnrelatedOwnerEpochKeepsAlpha();
				verifyUnrelatedOwnerEpochKeepsCppBeta();
				verifyOwnerRelease();
				verifyCppOwnerRelease();
				removeGlobalSentinels();
				restoreCppFixtureInputs();
				RuntimeSmokeHarness.emit('owner_library_native_verified', {
					managerImport:true, roots:4, html5Target:'html5', cppTarget:'windows', unknownTargetRejected:true,
					limeOpenFlFutures:true, imagePixels:true, preloadAndLazy:true,
					soundMusicFont:true, vorbisStreamingMusic:true,
					cppChangedProofRefresh:true, cppSourceFailures:true,
					cacheReuse:true, sameNameHostPreserved:true,
					unrelatedOwnerEpochPreserved:true, ownerReleaseInvalidated:true,
					pixelProofs:owners.map(function(ownerInfo:Dynamic):Dynamic return ownerInfo.pixelProof),
					cppProofs:cppOwners.map(function(ownerInfo:Dynamic):Dynamic return ownerInfo.cppProof)
				});
				phase = 8;
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) {
			cleanup();
			RuntimeSmokeHarness.fail('owner-library', Std.string(error));
		}
	}

	static function startImports(source:String):Void {
		workerMutex.acquire();
		workerDone = false;
		workerError = '';
		workerResult = null;
		workerMutex.release();
		Thread.create(function():Void {
			var result:Dynamic = null;
			var errorText = '';
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(_payload:Dynamic):Void {});
			ModuleFunctions.setImportCancelCallback(function():Bool return false);
			try {
				var scan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(scan != null && scan.errors != null && scan.errors.length == 0
					&& scan.rootScanTruncated != true && scan.packageScanTruncated != true,
					'Generated Psych source scan was incomplete');
				check(scan.songsFound == 0 && (scan.globalPacksToImport == null
					|| scan.globalPacksToImport == 0),
					'The warm/lazy fixture must remain a zero-song package import');
				check(scan.detectedRoots != null && scan.detectedRoots.length == 2,
					'Actual scanner did not select exactly two Psych roots');
				var contexts:Array<ImportRefreshManager.ImportSourceBuildContext> = [];
				var rootSummaries:Array<Dynamic> = [];
				for (root in scan.detectedRoots) {
					check(ImportRevision.normalizeEngine(root.engine) == ImportEngine.PSYCH,
						'Unexpected engine on selected fixture root: ' + root.engine);
					contexts.push({sourceRoot:root.root, engine:ImportEngine.PSYCH,
						build:{target:'html5', command:'', flags:[], values:[], flagsComplete:true}});
					var relative = Path.withoutDirectory(Path.normalize(root.root));
					rootSummaries.push({relative:relative, root:root.root,
						namespace:CompatScriptManifest.namespaceFor(root.root, ImportEngine.PSYCH)});
				}
			var imported = ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan, new Map(),
				ImportWorkflow.convertRetainedSource, function():Bool return false,
				function(_payload:Dynamic):Void {}, contexts);
			check(imported != null && imported.failed == 0 && imported.importedSongs != null
				&& imported.importedSongs.length == 0 && imported.copiedAssets > 0,
				'Actual zero-song converter did not publish the mapped owner assets: '
					+ (imported == null || imported.errors == null ? '' : imported.errors.join('; ')));

			result = {owners:rootSummaries};
			} catch (error:Dynamic) {
				errorText = Std.string(error);
			}
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			workerMutex.acquire();
			workerResult = result;
			workerError = errorText;
			workerDone = true;
			workerMutex.release();
		});
	}

	static function startCppImport(source:String):Void beginCppImport(source);

	static function startCppRefresh(source:String):Void {
		var alphaSource = Path.normalize(source + '/alpha/assets/runtime/sound.wav');
		var alphaStreamSource = Path.normalize(source + '/alpha/assets/runtime/stream.ogg');
		var betaStreamSource = Path.normalize(source + '/beta/assets/runtime/stream.ogg');
		var alphaFontSource = Path.normalize(source + '/alpha/assets/runtime/font.otf');
		var betaFontSource = Path.normalize(source + '/beta/assets/runtime/font.otf');
		cppAlphaOriginalSound = File.getBytes(alphaSource);
		cppAlphaOriginalStream = File.getBytes(alphaStreamSource);
		cppAlphaOriginalFont = File.getBytes(alphaFontSource);
		cppAlphaChangedSoundPath = alphaSource;
		cppAlphaChangedStreamPath = alphaStreamSource;
		cppAlphaChangedFontPath = alphaFontSource;
		var changedSound = Bytes.alloc(cppAlphaOriginalSound.length);
		for (index in 0...cppAlphaOriginalSound.length)
			changedSound.set(index, cppAlphaOriginalSound.get(index));
		// Preserve the generated WAV header and replace only sample bytes.
		for (index in 44...changedSound.length)
			changedSound.set(index, changedSound.get(index) ^ 0x5A);
		var changedStream = File.getBytes(betaStreamSource);
		var changedFont = File.getBytes(betaFontSource);
		check(Sha256.make(changedSound).toHex() != Sha256.make(cppAlphaOriginalSound).toHex()
			&& Sha256.make(changedStream).toHex() != Sha256.make(cppAlphaOriginalStream).toHex()
			&& Sha256.make(changedFont).toHex() != Sha256.make(cppAlphaOriginalFont).toHex(),
			'Private changed-proof payloads did not differ from the original assets');
		File.saveBytes(alphaSource, changedSound);
		File.saveBytes(alphaStreamSource, changedStream);
		File.saveBytes(alphaFontSource, changedFont);
		beginCppImport(source);
	}

	static function beginCppImport(source:String):Void {
		workerMutex.acquire();
		workerDone = false;
		workerError = '';
		workerResult = null;
		workerMutex.release();
		Thread.create(function():Void {
			var result:Dynamic = null;
			var errorText = '';
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(_payload:Dynamic):Void {});
			ModuleFunctions.setImportCancelCallback(function():Bool return false);
			try {
				var scan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(scan != null && scan.errors != null && scan.errors.length == 0
					&& scan.rootScanTruncated != true && scan.packageScanTruncated != true,
					'Generated CPP-target Psych source scan was incomplete');
				check(scan.songsFound == 0 && (scan.globalPacksToImport == null
					|| scan.globalPacksToImport == 0),
					'The CPP typed-media fixture must remain a zero-song package import');
				check(scan.detectedRoots != null && scan.detectedRoots.length == 2,
					'Actual scanner did not select exactly two CPP-target Psych roots');
				var contexts:Array<ImportRefreshManager.ImportSourceBuildContext> = [];
				var rootSummaries:Array<Dynamic> = [];
				for (root in scan.detectedRoots) {
					check(ImportRevision.normalizeEngine(root.engine) == ImportEngine.PSYCH,
						'Unexpected engine on CPP-target fixture root: ' + root.engine);
					contexts.push({sourceRoot:root.root, engine:ImportEngine.PSYCH,
						build:{target:'windows', command:'', flags:[], values:[], flagsComplete:true}});
					var relative = Path.withoutDirectory(Path.normalize(root.root));
					rootSummaries.push({relative:relative, root:root.root,
						namespace:CompatScriptManifest.namespaceFor(root.root, ImportEngine.PSYCH)});
				}
				var imported = ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan, new Map(),
					ImportWorkflow.convertRetainedSource, function():Bool return false,
					function(_payload:Dynamic):Void {}, contexts);
				check(imported != null && imported.failed == 0 && imported.importedSongs != null
					&& imported.importedSongs.length == 0 && imported.copiedAssets > 0,
					'Actual zero-song CPP converter did not publish typed owner assets: '
						+ (imported == null || imported.errors == null ? '' : imported.errors.join('; ')));
				result = {owners:rootSummaries, copiedAssets:imported.copiedAssets};
			} catch (error:Dynamic) {
				errorText = Std.string(error);
			}
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			workerMutex.acquire();
			workerResult = result;
			workerError = errorText;
			workerDone = true;
			workerMutex.release();
		});
	}

	static function startUnknownImport(source:String):Void {
		workerMutex.acquire();
		workerDone = false;
		workerError = '';
		workerResult = null;
		workerMutex.release();
		Thread.create(function():Void {
			var result:Dynamic = null;
			var errorText = '';
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(_payload:Dynamic):Void {});
			ModuleFunctions.setImportCancelCallback(function():Bool return false);
			try {
				var unknownScan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(unknownScan != null && unknownScan.errors != null && unknownScan.errors.length == 0
					&& unknownScan.detectedRoots != null && unknownScan.detectedRoots.length == 1
					&& unknownScan.songsFound == 0,
					'Unknown-target source scan was incomplete or unexpected');
				var unknownImport = ImportRefreshManager.importOnce(source, ImportEngine.PSYCH,
					unknownScan, new Map(), ImportWorkflow.convertRetainedSource,
					function():Bool return false, function(_payload:Dynamic):Void {});
				check(unknownImport != null && unknownImport.failed == 0 && unknownImport.copiedAssets > 0,
					'Unknown-target package did not reach ordinary retained import publication');
				var unknownRoot = unknownScan.detectedRoots[0].root;
				result = {unknown:{root:unknownRoot,
					namespace:CompatScriptManifest.namespaceFor(unknownRoot, ImportEngine.PSYCH)}};
			} catch (error:Dynamic) {
				errorText = Std.string(error);
			}
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			workerMutex.acquire();
			workerResult = result;
			workerError = errorText;
			workerDone = true;
			workerMutex.release();
		});
	}

	static function verifyReadyOwners():Void {
		for (ownerInfo in owners) {
			var ownerRoot = ownerPath(Std.string(ownerInfo.namespace));
			var binding = ImportRefreshManager.ownerAssetIndexBinding(ownerRoot,
				ImportEngine.PSYCH, 'package');
			check(binding != null && Reflect.field(binding, 'transactionId') != null
				&& Reflect.field(binding, 'snapshotId') != null,
				'Owner asset binding is not connected to a committed manager receipt: ' + ownerRoot);
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, ImportEngine.PSYCH, 'package');
			check(identity.bindingState == 'ready' && identity.indexVersion == 2
				&& identity.loadProfileComplete && identity.loadTarget == 'html5'
				&& identity.complete && identity.librariesComplete,
				'Explicit HTML5 source profile did not become a receipt-verified file library');
			check(identity.libraryState(Std.string(request.warmLibrary)) == 'declared'
				&& identity.libraryState(Std.string(request.lazyLibrary)) == 'declared',
				'Named source libraries were not committed for this exact owner');
			var warmProfile = identity.libraryLoadProfile(Std.string(request.warmLibrary));
			var lazyProfile = identity.libraryLoadProfile(Std.string(request.lazyLibrary));
			check(warmProfile != null && warmProfile.state == 'standard-file'
				&& warmProfile.projectPreloadState == 'known' && warmProfile.projectPreload == true
				&& warmProfile.projectEmbedState == 'known' && warmProfile.projectEmbed == false,
				'Warm library did not retain its known Project load settings');
			check(lazyProfile != null && lazyProfile.state == 'standard-file'
				&& lazyProfile.projectPreloadState == 'known' && lazyProfile.projectPreload == false,
				'Lazy library did not retain Project preload=false');
			var warmText = identity.resolve(Std.string(request.warmLibrary) + ':'
				+ Std.string(request.textId), 'TEXT');
			var warmImage = identity.resolve(Std.string(request.warmLibrary) + ':'
				+ Std.string(request.imageId), 'IMAGE');
			var lazyText = identity.resolve(Std.string(request.lazyLibrary) + ':'
				+ Std.string(request.lazyTextId), 'TEXT');
			check(warmText.state == 'found' && warmImage.state == 'found' && lazyText.state == 'found',
				'Committed source IDs did not resolve inside their owner library');
			check(warmText.entry.preloadState == 'enabled' && warmImage.entry.preloadState == 'enabled'
				&& lazyText.entry.preloadState == 'disabled',
				'Effective per-entry preload values differ from the explicit source fixture');
			for (file in (cast Reflect.field(binding, 'files'):Array<Dynamic>)) {
				var filePath = Std.string(Reflect.field(file, 'path'));
				check(filePath.startsWith(ownerRoot + '/') && FileSystem.exists(filePath)
					&& Sha256.make(File.getBytes(filePath)).toHex().toLowerCase()
						== Std.string(Reflect.field(file, 'sha256')).toLowerCase(),
					'Committed owner proof did not match the published file bytes: ' + filePath);
			}
			ownerInfo.ownerRoot = ownerRoot;
			ownerInfo.identity = identity;
			ownerInfo.warmTextPath = warmText.path;
			ownerInfo.warmImagePath = warmImage.path;
			ownerInfo.warmTextOriginal = File.getBytes(warmText.path);
			ownerInfo.warmImageOriginal = File.getBytes(warmImage.path);
			var expected = expectedOwner(Std.string(ownerInfo.relative));
			check(expected != null && File.getContent(warmText.path) == expected.warmText,
				'Fixture source text differs from committed owner content');
			ownerInfo.expected = expected;
		}
		check(owners[0].ownerRoot != owners[1].ownerRoot
			&& owners[0].namespace != owners[1].namespace,
			'Generated owner roots were collapsed into one namespace');
	}

	static function beginLibraryLoads():Void {
		var warmLibrary = Std.string(request.warmLibrary);
		var lazyLibrary = Std.string(request.lazyLibrary);
		globalSentinel = new openfl.utils.AssetLibrary();
		check(!LimeAssets.hasLibrary(warmLibrary) && !OpenFlAssets.hasLibrary(warmLibrary),
			'Generated global library name unexpectedly exists before sentinel registration');
		LimeAssets.registerLibrary(warmLibrary, globalSentinel);
		check(LimeAssets.getLibrary(warmLibrary) == globalSentinel
			&& OpenFlAssets.getLibrary(warmLibrary) == globalSentinel,
			'Could not install the same-named in-process host sentinel');
		for (ownerInfo in owners) {
			var lime = PsychOwnerLimeAssets.create(Std.string(ownerInfo.ownerRoot));
			var openFl = PsychOwnerOpenFlAssets.create(Std.string(ownerInfo.ownerRoot));
			ownerInfo.limeFacade = lime;
			ownerInfo.openFlFacade = openFl;
			check(Reflect.callMethod(lime, Reflect.field(lime, 'hasLibrary'), [warmLibrary])
				&& Reflect.callMethod(lime, Reflect.field(lime, 'hasLibrary'), [lazyLibrary]),
				'Owner facade did not report its receipt-declared libraries');
			var warmView:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [warmLibrary]);
			var lazyView:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [lazyLibrary]);
			var repeatedWarmView:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [warmLibrary]);
			var openView:openfl.utils.AssetLibrary = cast Reflect.callMethod(openFl, Reflect.field(openFl, 'getLibrary'), [warmLibrary]);
			check(warmView == repeatedWarmView && warmView != globalSentinel
				&& lazyView != globalSentinel && openView != null && openView.__proxy == warmView,
				'Owner-local Lime/OpenFL library instances were not isolated from the host registry');
			ownerInfo.warmView = warmView;
			ownerInfo.lazyView = lazyView;
			ownerInfo.openView = openView;
			var warmFuture:Future<AssetLibrary> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadLibrary'), [warmLibrary]);
			var repeatedFuture:Future<AssetLibrary> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadLibrary'), [warmLibrary]);
			var lazyFuture:Future<AssetLibrary> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadLibrary'), [lazyLibrary]);
			var openFuture:Dynamic = Reflect.callMethod(openFl, Reflect.field(openFl, 'loadLibrary'), [warmLibrary]);
			var repeatedOpenFuture:Dynamic = Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadLibrary'), [warmLibrary]);
			check(warmFuture == repeatedFuture && openFuture == repeatedOpenFuture,
				'Same-owner repeated library calls did not reuse their Future');
			limeFutures.push(warmFuture);
			limeFutures.push(lazyFuture);
			openFlFutures.push(openFuture);
			ownerInfo.warmFuture = warmFuture;
			ownerInfo.lazyFuture = lazyFuture;
			ownerInfo.openFuture = openFuture;
		}
		check(LimeAssets.getLibrary(warmLibrary) == globalSentinel
			&& OpenFlAssets.getLibrary(warmLibrary) == globalSentinel,
			'Owner get/load replaced the same-named host library');
	}

	static function verifyLoadedLibraries():Void {
		for (ownerInfo in owners) {
			var relative = Std.string(ownerInfo.relative);
			var expected = ownerInfo.expected;
			var warmFuture:Future<AssetLibrary> = cast ownerInfo.warmFuture;
			var lazyFuture:Future<AssetLibrary> = cast ownerInfo.lazyFuture;
			var openFuture:Future<Dynamic> = cast ownerInfo.openFuture;
			var warmView:AssetLibrary = warmFuture.value;
			var lazyView:AssetLibrary = lazyFuture.value;
			var openView:openfl.utils.AssetLibrary = cast openFuture.value;
			check(warmView == ownerInfo.warmView && lazyView == ownerInfo.lazyView
				&& openView != null && openView.__proxy == warmView,
				'Load Future did not resolve to its owner-local library view');
			var identity:RuntimeOwnerAssetIdentity = cast ownerInfo.identity;
			var warmText = identity.resolve(Std.string(request.warmLibrary) + ':'
				+ Std.string(request.textId), 'TEXT');
			var warmImage = identity.resolve(Std.string(request.warmLibrary) + ':'
				+ Std.string(request.imageId), 'IMAGE');
			var lazyText = identity.resolve(Std.string(request.lazyLibrary) + ':'
				+ Std.string(request.lazyTextId), 'TEXT');
			var warmCache = PsychOwnerAssetLibraryCache.entries.get(
				PsychOwnerAssetLibraryCache.cacheKey(identity, Std.string(request.warmLibrary)));
			var lazyCache = PsychOwnerAssetLibraryCache.entries.get(
				PsychOwnerAssetLibraryCache.cacheKey(identity, Std.string(request.lazyLibrary)));
			check(warmCache != null && lazyCache != null
				&& warmCache.sourceLibrary.cachedText.exists(warmText.entry.id)
				&& warmCache.sourceLibrary.cachedImages.exists(warmImage.entry.id)
				&& !lazyCache.sourceLibrary.cachedText.exists(lazyText.entry.id),
				'Native Lime load did not distinguish preloaded and lazy entries');
			var limeText:String = Reflect.callMethod(ownerInfo.limeFacade,
				Reflect.field(ownerInfo.limeFacade, 'getText'), [Std.string(request.warmLibrary)
					+ ':' + Std.string(request.textId)]);
			var openText:String = Reflect.callMethod(ownerInfo.openFlFacade,
				Reflect.field(ownerInfo.openFlFacade, 'getText'), [Std.string(request.warmLibrary)
					+ ':' + Std.string(request.textId)]);
			var lazyValue:String = Reflect.callMethod(ownerInfo.limeFacade,
				Reflect.field(ownerInfo.limeFacade, 'getText'), [Std.string(request.lazyLibrary)
					+ ':' + Std.string(request.lazyTextId)]);
			check(limeText == expected.warmText && openText == expected.warmText
				&& lazyValue == expected.lazyText,
				'Owner facade did not return the expected loaded and lazy text assets for ' + relative);
			var bitmap:BitmapData = Reflect.callMethod(ownerInfo.openFlFacade,
				Reflect.field(ownerInfo.openFlFacade, 'getBitmapData'), [Std.string(request.warmLibrary)
					+ ':' + Std.string(request.imageId)]);
			check(bitmap != null && bitmap.width == 2 && bitmap.height == 2,
				'OpenFL BitmapData decode/dimensions changed for owner ' + relative);
			var sourceBytes = File.getBytes(warmImage.path);
			var sourceHash = Sha256.make(sourceBytes).toHex().toLowerCase();
			var rawImage = lime.graphics.Image.fromBytes(sourceBytes);
			check(rawImage != null && rawImage.width == 2 && rawImage.height == 2,
				'Raw source PNG decode/dimensions changed for owner ' + relative + ', sourceSha256=' + sourceHash);
			var rawPixels = imagePixels(rawImage);
			var expectedRawPixels = expectedRawImagePixels(expected);
			check(samePixels(rawPixels, expectedRawPixels),
				'Raw source PNG pixels changed for owner ' + relative + ': expected='
					+ formatPixels(expectedRawPixels) + ', raw=' + formatPixels(rawPixels)
					+ ', sourceSha256=' + sourceHash);
			var routedPixels = bitmapPixels(bitmap);
			var nativeBaseline = BitmapData.fromFile(warmImage.path);
			check(nativeBaseline != null && nativeBaseline.width == 2 && nativeBaseline.height == 2,
				'Pinned BitmapData.fromFile baseline decode/dimensions failed for owner '
					+ relative + ', sourceSha256=' + sourceHash);
			var nativePixels = bitmapPixels(nativeBaseline);
			var pixelProof:Dynamic = {
				owner:relative,
				sourceSha256:sourceHash,
				rawExpected:formatPixels(expectedRawPixels),
				rawDecoded:formatPixels(rawPixels),
				routed:formatPixels(routedPixels),
				bitmapFromFile:formatPixels(nativePixels)
			};
			ownerInfo.pixelProof = pixelProof;
			check(samePixels(routedPixels, nativePixels),
				'Owner-routed BitmapData differs from pinned BitmapData.fromFile for owner '
					+ relative + ': rawExpected=' + formatPixels(expectedRawPixels)
					+ ', rawDecoded=' + formatPixels(rawPixels)
					+ ', routed=' + formatPixels(routedPixels)
					+ ', bitmapFromFile=' + formatPixels(nativePixels)
					+ ', sourceSha256=' + sourceHash);
			ownerInfo.expectedBitmapPixels = nativePixels.copy();
			nativeBaseline.dispose();
			var limeImage:lime.graphics.Image = warmView.getImage(warmImage.entry.id);
			check(limeImage != null && limeImage.width == 2 && limeImage.height == 2,
				'Lime Image decode/dimensions changed for owner ' + relative);
		}
		check(owners[0].warmView != owners[1].warmView
			&& owners[0].warmView.getText(Std.string(request.textId)) == owners[0].expected.warmText
			&& owners[1].warmView.getText(Std.string(request.textId)) == owners[1].expected.warmText,
			'Same Lime library name or asset ID crossed owner boundaries');
		check(LimeAssets.getLibrary(Std.string(request.warmLibrary)) == globalSentinel
			&& OpenFlAssets.getLibrary(Std.string(request.warmLibrary)) == globalSentinel,
			'Owner loads changed the registered same-name host library');
		verifyPreloadedCacheReuse();
	}

	static function verifyPreloadedCacheReuse():Void {
		for (ownerInfo in owners) {
			var textPath = Std.string(ownerInfo.warmTextPath);
			var imagePath = Std.string(ownerInfo.warmImagePath);
			var originalText:Bytes = cast ownerInfo.warmTextOriginal;
			var originalImage:Bytes = cast ownerInfo.warmImageOriginal;
			try {
				File.saveContent(textPath, 'temporarily changed after Lime preload');
				File.saveBytes(imagePath, Bytes.ofString('temporarily invalid after Lime preload'));
				var text:String = Reflect.callMethod(ownerInfo.limeFacade,
					Reflect.field(ownerInfo.limeFacade, 'getText'), [Std.string(request.warmLibrary)
						+ ':' + Std.string(request.textId)]);
				var expected = ownerInfo.expected;
				var bitmap:BitmapData = Reflect.callMethod(ownerInfo.openFlFacade,
					Reflect.field(ownerInfo.openFlFacade, 'getBitmapData'), [Std.string(request.warmLibrary)
						+ ':' + Std.string(request.imageId)]);
				check(text == expected.warmText && bitmap != null
					&& samePixels(bitmapPixels(bitmap), cast ownerInfo.expectedBitmapPixels),
					'Ordinary Lime/OpenFL reads bypassed their preloaded typed cache');
			} catch (error:Dynamic) {
				File.saveBytes(textPath, originalText);
				File.saveBytes(imagePath, originalImage);
				throw error;
			}
			File.saveBytes(textPath, originalText);
			File.saveBytes(imagePath, originalImage);
		}
	}

	static function verifyReadyCppOwners():Void {
		for (ownerInfo in cppOwners) {
			var ownerRoot = ownerPath(Std.string(ownerInfo.namespace));
			var binding = ImportRefreshManager.ownerAssetIndexBinding(ownerRoot,
				ImportEngine.PSYCH, 'package');
			check(binding != null && Reflect.field(binding, 'transactionId') != null
				&& Reflect.field(binding, 'snapshotId') != null,
				'CPP owner asset binding is not connected to a committed manager receipt: ' + ownerRoot);
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, ImportEngine.PSYCH, 'package');
			check(identity.bindingState == 'ready' && identity.indexVersion == 2
				&& identity.loadProfileComplete && identity.loadTarget == 'windows'
				&& identity.complete && identity.librariesComplete,
				'Explicit CPP-target source profile did not become a receipt-verified file library');
			var library = Std.string(request.cppLibrary);
			check(identity.libraryState(library) == 'declared',
				'CPP named source library was not committed for this exact owner');
			var profile = identity.libraryLoadProfile(library);
			check(profile != null && profile.state == 'standard-file'
				&& profile.projectPreloadState == 'known' && profile.projectPreload == false
				&& profile.projectEmbedState == 'known' && profile.projectEmbed == false,
				'CPP library did not retain its known file-backed Project settings');
			var sound = identity.resolve(library + ':' + Std.string(request.cppSoundId), 'SOUND');
			var music = identity.resolve(library + ':' + Std.string(request.cppMusicId), 'MUSIC');
			var streamMusic = identity.resolve(library + ':' + Std.string(request.cppStreamMusicId), 'MUSIC');
			var font = identity.resolve(library + ':' + Std.string(request.cppFontId), 'FONT');
			check(sound.state == 'found' && music.state == 'found' && streamMusic.state == 'found'
				&& font.state == 'found'
				&& sound.entry.preloadState == 'disabled' && music.entry.preloadState == 'disabled'
				&& streamMusic.entry.preloadState == 'disabled' && font.entry.preloadState == 'disabled',
				'CPP file entries did not retain their exact typed, lazy source identities');
			for (file in (cast Reflect.field(binding, 'files'):Array<Dynamic>)) {
				var filePath = Std.string(Reflect.field(file, 'path'));
				check(filePath.startsWith(ownerRoot + '/') && FileSystem.exists(filePath)
					&& Sha256.make(File.getBytes(filePath)).toHex().toLowerCase()
						== Std.string(Reflect.field(file, 'sha256')).toLowerCase(),
					'CPP owner proof did not match the published file bytes: ' + filePath);
			}
			var expected = expectedCppOwner(Std.string(ownerInfo.relative));
			check(expected != null
				&& Sha256.make(File.getBytes(sound.path)).toHex().toLowerCase() == expected.soundSha256
				&& Sha256.make(File.getBytes(music.path)).toHex().toLowerCase() == expected.musicSha256
				&& Sha256.make(File.getBytes(streamMusic.path)).toHex().toLowerCase() == expected.streamSha256
				&& Sha256.make(File.getBytes(font.path)).toHex().toLowerCase() == expected.fontSha256,
				'CPP fixture bytes differ from the generated source hashes');
			ownerInfo.ownerRoot = ownerRoot;
			ownerInfo.identity = identity;
			ownerInfo.soundPath = sound.path;
			ownerInfo.musicPath = music.path;
			ownerInfo.streamPath = streamMusic.path;
			ownerInfo.fontPath = font.path;
			ownerInfo.expected = expected;
		}
		check(cppOwners[0].ownerRoot != cppOwners[1].ownerRoot
			&& cppOwners[0].namespace != cppOwners[1].namespace,
			'Generated CPP owner roots were collapsed into one namespace');
	}

	static function beginCppLibraryLoads():Void {
		var library = Std.string(request.cppLibrary);
		cppGlobalSentinel = new openfl.utils.AssetLibrary();
		check(!LimeAssets.hasLibrary(library) && !OpenFlAssets.hasLibrary(library),
			'Generated CPP library name unexpectedly exists before sentinel registration');
		LimeAssets.registerLibrary(library, cppGlobalSentinel);
		check(LimeAssets.getLibrary(library) == cppGlobalSentinel
			&& OpenFlAssets.getLibrary(library) == cppGlobalSentinel,
			'Could not install the same-named CPP host sentinel');
		for (ownerInfo in cppOwners) {
			var lime = PsychOwnerLimeAssets.create(Std.string(ownerInfo.ownerRoot));
			var openFl = PsychOwnerOpenFlAssets.create(Std.string(ownerInfo.ownerRoot));
			ownerInfo.limeFacade = lime;
			ownerInfo.openFlFacade = openFl;
			check(Reflect.callMethod(lime, Reflect.field(lime, 'hasLibrary'), [library]),
				'CPP owner facade did not report its receipt-declared library');
			var view:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [library]);
			var repeatedView:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [library]);
			var openView:openfl.utils.AssetLibrary = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getLibrary'), [library]);
			check(view == repeatedView && view != cppGlobalSentinel && openView != null
				&& openView.__proxy == view,
				'CPP owner library view was not local to its receipt-bound owner');
			ownerInfo.libraryView = view;
			ownerInfo.openLibraryView = openView;
			var limeFuture:Future<Dynamic> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadLibrary'), [library]);
			var repeatedFuture:Future<Dynamic> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadLibrary'), [library]);
			var openFuture:Future<Dynamic> = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadLibrary'), [library]);
			var repeatedOpenFuture:Future<Dynamic> = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadLibrary'), [library]);
			check(limeFuture == repeatedFuture && openFuture == repeatedOpenFuture,
				'CPP repeated library calls did not reuse the same owner-local Future');
			ownerInfo.libraryFuture = limeFuture;
			ownerInfo.openLibraryFuture = openFuture;
			cppLibraryFutures.push(limeFuture);
			cppOpenFlLibraryFutures.push(openFuture);
		}
		check(LimeAssets.getLibrary(library) == cppGlobalSentinel
			&& OpenFlAssets.getLibrary(library) == cppGlobalSentinel,
			'CPP owner get/load replaced the same-named host library');
	}

	static function verifyCppLoadedLibraries():Void {
		for (ownerInfo in cppOwners) {
			var limeFuture:Future<Dynamic> = cast ownerInfo.libraryFuture;
			var openFuture:Future<Dynamic> = cast ownerInfo.openLibraryFuture;
			var view:AssetLibrary = cast limeFuture.value;
			var openView:openfl.utils.AssetLibrary = cast openFuture.value;
			check(view == ownerInfo.libraryView && openView != null
				&& openView.__proxy == view,
				'CPP library Future did not resolve to the retained local view');
			var identity:RuntimeOwnerAssetIdentity = cast ownerInfo.identity;
			var library = Std.string(request.cppLibrary);
			var soundId = library + ':' + Std.string(request.cppSoundId);
			var musicId = library + ':' + Std.string(request.cppMusicId);
			var streamId = library + ':' + Std.string(request.cppStreamMusicId);
			var fontId = library + ':' + Std.string(request.cppFontId);
			check(sameOwnerPath(view.getPath(Std.string(request.cppStreamMusicId)), ownerInfo.streamPath)
				&& hasOnlyIds(view.list('MUSIC'), [Std.string(request.cppSoundId),
					Std.string(request.cppMusicId), Std.string(request.cppStreamMusicId)])
				&& hasOnlyIds(identity.list(library, 'MUSIC'),
					[Std.string(request.cppSoundId), Std.string(request.cppMusicId),
						Std.string(request.cppStreamMusicId)]),
				'CPP MUSIC public path/list exposed a private stream lease instead of only owner Project assets');
			check(view.exists(Std.string(request.cppSoundId), 'SOUND')
				&& view.exists(Std.string(request.cppMusicId), 'MUSIC')
				&& view.exists(Std.string(request.cppStreamMusicId), 'MUSIC')
				&& view.exists(Std.string(request.cppFontId), 'FONT'),
				'Loaded Lime view lost one of the CPP typed asset entries');
			var lime = ownerInfo.limeFacade;
			var openFl = ownerInfo.openFlFacade;
			var sound:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAudioBuffer'), [soundId]);
			var soundAgain:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAudioBuffer'), [soundId]);
			var soundUncached:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAudioBuffer'), [soundId, false]);
			var music:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAsset'), [musicId, AssetType.MUSIC]);
			var musicAgain:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAsset'), [musicId, AssetType.MUSIC]);
			var musicUncached:AudioBuffer = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getAsset'), [musicId, AssetType.MUSIC, false]);
			var font:LimeFont = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getFont'), [fontId]);
			var fontAgain:LimeFont = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getFont'), [fontId]);
			var fontUncached:LimeFont = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'getFont'), [fontId, false]);
			check(sound != null && sound == soundAgain && soundUncached != null && sound != soundUncached
				&& music != null && music == musicAgain && musicUncached != null && music != musicUncached
				&& font != null && font == fontAgain && fontUncached != null && font != fontUncached,
				'Lime useCache optional arguments did not follow the native typed-asset contract');
			var openSound:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getSound'), [soundId]);
			var openSoundAgain:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getSound'), [soundId]);
			var openSoundUncached:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getSound'), [soundId, false]);
			var openMusic:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [musicId]);
			var openMusicAgain:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [musicId]);
			var openMusicUncached:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [musicId, false]);
			var openStreamMusic:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [streamId]);
			var openStreamMusicAgain:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [streamId]);
			var openStreamMusicUncached:Sound = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getMusic'), [streamId, false]);
			var openFont:OpenFlFont = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getFont'), [fontId]);
			var openFontAgain:OpenFlFont = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getFont'), [fontId]);
			var openFontUncached:OpenFlFont = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'getFont'), [fontId, false]);
			var openSoundCacheHit = openSound != null && openSound == openSoundAgain;
			var openSoundBypass = openSound != null && openSoundUncached != null && openSound != openSoundUncached;
			var openWavMusicCacheHit = openMusic != null && openMusic == openMusicAgain;
			var openWavMusicBypass = openMusic != null && openMusicUncached != null && openMusic != openMusicUncached;
			var openStreamDistinctDefault = openStreamMusic != null && openStreamMusicAgain != null
				&& openStreamMusic != openStreamMusicAgain;
			var openStreamDistinctUncached = openStreamMusic != null && openStreamMusicUncached != null
				&& openStreamMusic != openStreamMusicUncached;
			var openStreamBuffersDistinct = openStreamMusic != null && openStreamMusicAgain != null
				&& openStreamMusicUncached != null && openStreamMusic.__buffer != openStreamMusicAgain.__buffer
				&& openStreamMusic.__buffer != openStreamMusicUncached.__buffer
				&& openStreamMusicAgain.__buffer != openStreamMusicUncached.__buffer;
			var openStreamFilesDistinct = isVorbisBacked(openStreamMusic)
				&& isVorbisBacked(openStreamMusicAgain) && isVorbisBacked(openStreamMusicUncached)
				&& openStreamMusic.__buffer.__srcVorbisFile != openStreamMusicAgain.__buffer.__srcVorbisFile
				&& openStreamMusic.__buffer.__srcVorbisFile != openStreamMusicUncached.__buffer.__srcVorbisFile
				&& openStreamMusicAgain.__buffer.__srcVorbisFile != openStreamMusicUncached.__buffer.__srcVorbisFile;
			var openFontCacheHit = openFont != null && openFont == openFontAgain;
			var openFontBypass = openFont != null && openFontUncached != null && openFont != openFontUncached;
			var openFlCacheContractPassed = openSoundCacheHit && openSoundBypass
				&& openSound != openSoundUncached && openMusic != null && openMusic == openMusicAgain
				&& openWavMusicBypass && openStreamDistinctDefault && openStreamDistinctUncached
				&& openStreamBuffersDistinct && openStreamFilesDistinct
				&& openFontCacheHit && openFontBypass;
			if (!openFlCacheContractPassed)
				throw 'OpenFL useCache optional arguments did not follow the pinned native API: '
					+ 'sound(cacheHit=' + openSoundCacheHit + ',bypass=' + openSoundBypass
					+ ',soundNonNull=' + (openSound != null) + ',uncachedNonNull=' + (openSoundUncached != null)
					+ ',bufferSame=' + (openSound != null && openSoundAgain != null
						&& openSound.__buffer == openSoundAgain.__buffer) + '); '
					+ 'wavMusic(cacheHit=' + openWavMusicCacheHit + ',bypass=' + openWavMusicBypass
					+ ',soundNonNull=' + (openMusic != null) + ',uncachedNonNull=' + (openMusicUncached != null)
					+ ',bufferSame=' + (openMusic != null && openMusicAgain != null
						&& openMusic.__buffer == openMusicAgain.__buffer) + '); '
					+ 'vorbisMusic(defaultDistinct=' + openStreamDistinctDefault + ',uncachedDistinct='
					+ openStreamDistinctUncached + ',nonNull=' + (openStreamMusic != null) + '/'
					+ (openStreamMusicAgain != null) + '/' + (openStreamMusicUncached != null)
					+ ',vorbis=' + isVorbisBacked(openStreamMusic) + '/' + isVorbisBacked(openStreamMusicAgain)
					+ '/' + isVorbisBacked(openStreamMusicUncached) + ',buffersDistinct=' + openStreamBuffersDistinct
					+ ',vorbisFilesDistinct=' + openStreamFilesDistinct + '); '
					+ 'font(cacheHit=' + openFontCacheHit + ',bypass=' + openFontBypass
					+ ',fontNonNull=' + (openFont != null) + ',uncachedNonNull=' + (openFontUncached != null) + ')';
			var soundBaseline = AudioBuffer.fromFile(Std.string(ownerInfo.soundPath));
			var musicBaseline = AudioBuffer.fromFile(Std.string(ownerInfo.musicPath));
			var streamSourceBytes = File.getBytes(Std.string(ownerInfo.streamPath));
			var fontBaseline = fontBaselineFromPrivateCopy(File.getBytes(Std.string(ownerInfo.fontPath)));
			check(sameAudio(sound, soundBaseline) && sameAudio(soundUncached, soundBaseline)
				&& sameAudio(music, musicBaseline) && sameAudio(musicUncached, musicBaseline)
				&& sameAudio(openSound.__buffer, soundBaseline)
				&& sameAudio(openSoundUncached.__buffer, soundBaseline)
				&& sameAudio(openMusic.__buffer, musicBaseline)
				&& sameAudio(openMusicUncached.__buffer, musicBaseline),
				'CPP SOUND/MUSIC decoder output differed from the pinned Lime file baseline');
			var fontMatches = sameFont(font, fontBaseline) && sameFont(fontUncached, fontBaseline)
				&& sameFont(openFont, fontBaseline) && sameFont(openFontUncached, fontBaseline);
			if (!fontMatches)
				throw 'CPP FONT output differed from the pinned Lime file baseline: Lime=' + fontMismatch(font, fontBaseline)
					+ '; Lime uncached=' + fontMismatch(fontUncached, fontBaseline)
					+ '; OpenFL=' + fontMismatch(openFont, fontBaseline)
					+ '; OpenFL uncached=' + fontMismatch(openFontUncached, fontBaseline);
			check(isVorbisBacked(openStreamMusic) && isVorbisBacked(openStreamMusicAgain)
				&& isVorbisBacked(openStreamMusicUncached)
				&& sameVorbisStream(openStreamMusic, streamSourceBytes)
				&& sameVorbisStream(openStreamMusicAgain, streamSourceBytes)
				&& sameVorbisStream(openStreamMusicUncached, streamSourceBytes),
				'CPP MUSIC did not use the pinned Vorbis streaming branch and exact source decoder output');
			ownerInfo.soundBuffer = sound;
			ownerInfo.musicBuffer = music;
			ownerInfo.font = font;
			ownerInfo.openSound = openSound;
			ownerInfo.openMusic = openMusic;
			ownerInfo.streamSound = openStreamMusic;
			ownerInfo.streamSoundAgain = openStreamMusicAgain;
			ownerInfo.streamSoundUncached = openStreamMusicUncached;
			ownerInfo.openFont = openFont;
			ownerInfo.soundBaseline = soundBaseline;
			ownerInfo.musicBaseline = musicBaseline;
			ownerInfo.streamSourceBytes = streamSourceBytes;
			ownerInfo.fontBaseline = fontBaseline;
			ownerInfo.cppProof = {
				owner:ownerInfo.relative,
				soundSha256:Sha256.make(File.getBytes(Std.string(ownerInfo.soundPath))).toHex().toLowerCase(),
				musicSha256:Sha256.make(File.getBytes(Std.string(ownerInfo.musicPath))).toHex().toLowerCase(),
				streamSha256:Sha256.make(streamSourceBytes).toHex().toLowerCase(),
				fontSha256:Sha256.make(File.getBytes(Std.string(ownerInfo.fontPath))).toHex().toLowerCase(),
				sound:audioSignature(sound), music:audioSignature(music),
				stream:vorbisMetadataSignature(cast openStreamMusic.__buffer.__srcVorbisFile),
				font:fontSignature(font)
			};
			var warmSoundLoad:Future<Dynamic> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadAudioBuffer'), [soundId, false]);
			var musicLoad:Future<Dynamic> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadAsset'), [musicId, AssetType.MUSIC, false]);
			var fontLoad:Future<Dynamic> = cast Reflect.callMethod(lime,
				Reflect.field(lime, 'loadFont'), [fontId, false]);
			var openSoundLoad:Future<Dynamic> = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadSound'), [soundId, false]);
			var openMusicLoad:Future<Dynamic> = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadMusic'), [musicId, null]);
			var openFontLoad:Future<Dynamic> = cast Reflect.callMethod(openFl,
				Reflect.field(openFl, 'loadFont'), [fontId]);
			ownerInfo.typedLoads = {sound:warmSoundLoad, music:musicLoad, font:fontLoad,
				openSound:openSoundLoad, openMusic:openMusicLoad, openFont:openFontLoad};
			for (future in [warmSoundLoad, musicLoad, fontLoad, openSoundLoad, openMusicLoad, openFontLoad])
				cppTypedFutures.push(future);
		}
		check(cppOwners[0].soundBuffer != cppOwners[1].soundBuffer
			&& cppOwners[0].musicBuffer != cppOwners[1].musicBuffer
			&& cppOwners[0].streamSound != cppOwners[1].streamSound
			&& cppOwners[0].font != cppOwners[1].font
			&& !sameAudio(cppOwners[0].soundBuffer, cppOwners[1].soundBuffer)
			&& !sameAudio(cppOwners[0].musicBuffer, cppOwners[1].musicBuffer)
			&& !sameFont(cppOwners[0].font, cppOwners[1].font),
			'Same typed IDs crossed owner-specific Lime/OpenFL caches');
		check(LimeAssets.getLibrary(Std.string(request.cppLibrary)) == cppGlobalSentinel
			&& OpenFlAssets.getLibrary(Std.string(request.cppLibrary)) == cppGlobalSentinel,
			'CPP typed reads replaced the same-named host library');
	}

	static function verifyCppTypedLoads():Void {
		for (ownerInfo in cppOwners) {
			var loads:Dynamic = ownerInfo.typedLoads;
			var limeSound:Future<Dynamic> = cast Reflect.field(loads, 'sound');
			var limeMusic:Future<Dynamic> = cast Reflect.field(loads, 'music');
			var limeFont:Future<Dynamic> = cast Reflect.field(loads, 'font');
			var openSound:Future<Dynamic> = cast Reflect.field(loads, 'openSound');
			var openMusic:Future<Dynamic> = cast Reflect.field(loads, 'openMusic');
			var openFont:Future<Dynamic> = cast Reflect.field(loads, 'openFont');
			check(sameAudio(cast limeSound.value, ownerInfo.soundBaseline)
				&& sameAudio(cast limeMusic.value, ownerInfo.musicBaseline)
				&& sameFont(cast limeFont.value, ownerInfo.fontBaseline)
				&& sameAudio((cast openSound.value:Sound).__buffer, ownerInfo.soundBaseline)
				&& sameAudio((cast openMusic.value:Sound).__buffer, ownerInfo.musicBaseline)
				&& sameFont(cast openFont.value, ownerInfo.fontBaseline),
				'CPP typed async loaders returned values that differ from pinned file decoders');
		}
	}

	static function verifyCppSourceFailures():Void {
		var ownerInfo = cppOwners[0];
		var lime = ownerInfo.limeFacade;
		var openFl = ownerInfo.openFlFacade;
		var library = Std.string(request.cppLibrary);
		var soundId = library + ':' + Std.string(request.cppSoundId);
		var fontId = library + ':' + Std.string(request.cppFontId);
		var missingId = library + ':missing-generated-sound';
		var typedMismatch = (cast ownerInfo.identity:RuntimeOwnerAssetIdentity)
			.resolve(soundId, 'FONT');
		var musicCompatible = (cast ownerInfo.identity:RuntimeOwnerAssetIdentity)
			.resolve(soundId, 'MUSIC');
		var musicMismatch = (cast ownerInfo.identity:RuntimeOwnerAssetIdentity)
			.resolve(fontId, 'MUSIC');
		check(typedMismatch.state == 'type-mismatch'
			&& musicCompatible.state == 'found'
			&& musicMismatch.state == 'type-mismatch'
			&& !(Reflect.callMethod(lime, Reflect.field(lime, 'exists'), [soundId, AssetType.FONT]) == true)
			&& Reflect.callMethod(lime, Reflect.field(lime, 'exists'), [soundId, AssetType.MUSIC]) == true
			&& !(Reflect.callMethod(openFl, Reflect.field(openFl, 'exists'), [fontId, AssetType.MUSIC]) == true)
			&& Reflect.callMethod(openFl, Reflect.field(openFl, 'exists'), [soundId, AssetType.MUSIC]) == true,
			'Wrongly typed same-owner IDs did not fail exact Lime/OpenFL type lookup');
		var limeGetFailed = false;
		var openGetFailed = false;
		var musicFromSound:Sound = cast Reflect.callMethod(openFl,
			Reflect.field(openFl, 'getMusic'), [soundId]);
		try Reflect.callMethod(lime, Reflect.field(lime, 'getFont'), [soundId])
		catch (_:Dynamic) limeGetFailed = true;
		try Reflect.callMethod(openFl, Reflect.field(openFl, 'getMusic'), [fontId])
		catch (_:Dynamic) openGetFailed = true;
		var missing = (cast ownerInfo.identity:RuntimeOwnerAssetIdentity).resolve(missingId, 'SOUND');
		check(missing.state == 'missing'
			&& Reflect.callMethod(lime, Reflect.field(lime, 'exists'), [missingId, AssetType.SOUND]) != true
			&& limeGetFailed && openGetFailed && musicFromSound != null
			&& sameAudio(musicFromSound.__buffer, ownerInfo.soundBaseline),
			'Missing or wrongly typed synchronous lookups fell through to host/global assets');
		var limeMissing:Future<Dynamic> = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'loadAudioBuffer'), [missingId]);
		var openMissing:Future<Dynamic> = cast Reflect.callMethod(openFl,
			Reflect.field(openFl, 'loadSound'), [missingId]);
		var limeWrong:Future<Dynamic> = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'loadFont'), [soundId]);
		var openWrong:Future<Dynamic> = cast Reflect.callMethod(openFl,
			Reflect.field(openFl, 'loadMusic'), [fontId]);
		check(limeMissing != null && limeMissing.isError && openMissing != null && openMissing.isError
			&& limeWrong != null && limeWrong.isError && openWrong != null && openWrong.isError,
			'Missing/wrong-type asynchronous lookups did not fail through their native Futures');
	}

	static function verifyCppRefresh():Void {
		var alpha = cppOwners[0];
		var oldIdentity:RuntimeOwnerAssetIdentity = cast alpha.identity;
		var ownerRoot = Std.string(alpha.ownerRoot);
		var library = Std.string(request.cppLibrary);
		var soundId = library + ':' + Std.string(request.cppSoundId);
		var streamId = library + ':' + Std.string(request.cppStreamMusicId);
		var fontId = library + ':' + Std.string(request.cppFontId);
		var oldSound:AudioBuffer = cast alpha.soundBuffer;
		var oldStream:Sound = cast alpha.streamSound;
		var oldFont:LimeFont = cast alpha.font;
		var oldView:AssetLibrary = cast alpha.libraryView;
		var soundBytes = File.getBytes(Std.string(alpha.soundPath));
		var streamBytes = File.getBytes(Std.string(alpha.streamPath));
		var fontBytes = File.getBytes(Std.string(alpha.fontPath));
		check(Sha256.make(File.getBytes(cppAlphaChangedSoundPath)).toHex()
			!= Sha256.make(cppAlphaOriginalSound).toHex()
			&& Sha256.make(File.getBytes(cppAlphaChangedStreamPath)).toHex()
			!= Sha256.make(cppAlphaOriginalStream).toHex()
			&& Sha256.make(File.getBytes(cppAlphaChangedFontPath)).toHex()
			!= Sha256.make(cppAlphaOriginalFont).toHex(),
			'Generated CPP input mutations were not retained for the refresh');
		var refreshed = RuntimeOwnerAssetIdentity.acquire(ownerRoot, ImportEngine.PSYCH, 'package');
		check(refreshed != oldIdentity && refreshed.bindingState == 'ready'
			&& refreshed.loadProfileComplete && refreshed.loadTarget == 'windows',
			'Changed committed CPP proof did not produce a fresh verified owner identity');
		var refreshedSound = refreshed.resolve(soundId, 'SOUND');
		var refreshedStream = refreshed.resolve(streamId, 'MUSIC');
		var refreshedFont = refreshed.resolve(fontId, 'FONT');
		check(refreshedSound.state == 'found' && refreshedStream.state == 'found'
			&& refreshedFont.state == 'found'
			&& refreshedSound.path == alpha.soundPath && refreshedStream.path == alpha.streamPath
			&& refreshedFont.path == alpha.fontPath
			&& refreshedSound.entry.sha256 != alpha.expected.soundSha256
			&& refreshedStream.entry.sha256 != alpha.expected.streamSha256
			&& refreshedFont.entry.sha256 != alpha.expected.fontSha256
			&& Sha256.make(soundBytes).toHex().toLowerCase() == refreshedSound.entry.sha256
			&& Sha256.make(streamBytes).toHex().toLowerCase() == refreshedStream.entry.sha256
			&& Sha256.make(fontBytes).toHex().toLowerCase() == refreshedFont.entry.sha256,
			'CPP refresh did not replace the same typed IDs and owner paths with new proof bytes');
		var oldSoundHandleStale = false;
		var oldFontHandleStale = false;
		try oldView.getAudioBuffer(Std.string(request.cppSoundId)) catch (_:Dynamic) oldSoundHandleStale = true;
		try oldView.getFont(Std.string(request.cppFontId)) catch (_:Dynamic) oldFontHandleStale = true;
		check(oldSoundHandleStale && oldFontHandleStale,
			'Changed owner proof left a retained pre-refresh Lime view usable');
		var lime = PsychOwnerLimeAssets.create(ownerRoot);
		var openFl = PsychOwnerOpenFlAssets.create(ownerRoot);
		var newSound:AudioBuffer = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'getAudioBuffer'), [soundId]);
		var refreshedView:AssetLibrary = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'getLibrary'), [library]);
		var newStream:Sound = cast Reflect.callMethod(openFl,
			Reflect.field(openFl, 'getMusic'), [streamId]);
		var newFont:LimeFont = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'getFont'), [fontId]);
		var newOpenFont:OpenFlFont = cast Reflect.callMethod(openFl,
			Reflect.field(openFl, 'getFont'), [fontId]);
		var soundBaseline = AudioBuffer.fromFile(refreshedSound.path);
		var fontBaseline = fontBaselineFromPrivateCopy(fontBytes);
		check(newSound != oldSound && !sameAudio(newSound, oldSound)
			&& sameAudio(newSound, soundBaseline)
			&& newStream != null && newStream != oldStream && isVorbisBacked(newStream)
			&& sameVorbisStream(newStream, streamBytes)
			&& sameVorbisStream(oldStream, cppAlphaOriginalStream)
			&& sameOwnerPath(refreshedView.getPath(Std.string(request.cppStreamMusicId)), alpha.streamPath)
			&& hasOnlyIds(refreshedView.list('MUSIC'),
				[Std.string(request.cppSoundId), Std.string(request.cppMusicId),
					Std.string(request.cppStreamMusicId)])
			&& hasOnlyIds(refreshed.list(library, 'MUSIC'),
				[Std.string(request.cppSoundId), Std.string(request.cppMusicId),
					Std.string(request.cppStreamMusicId)])
			&& sameBytes(File.getBytes(cppAlphaChangedStreamPath), streamBytes)
			&& newFont != oldFont && sameFont(newFont, fontBaseline)
			&& sameFont(newOpenFont, fontBaseline),
			'New CPP facade reads reused stale SOUND/FONT objects after same-path proof refresh');
		alpha.identity = refreshed;
		alpha.limeFacade = lime;
		alpha.openFlFacade = openFl;
		alpha.libraryView = Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'), [library]);
		alpha.openLibraryView = Reflect.callMethod(openFl, Reflect.field(openFl, 'getLibrary'), [library]);
		alpha.soundBuffer = newSound;
		alpha.streamSound = newStream;
		alpha.font = newFont;
		alpha.openFont = newOpenFont;
		alpha.soundBaseline = soundBaseline;
		alpha.fontBaseline = fontBaseline;
		alpha.soundPath = refreshedSound.path;
		alpha.streamPath = refreshedStream.path;
		alpha.streamSourceBytes = streamBytes;
		alpha.fontPath = refreshedFont.path;
		alpha.cppProof = {owner:alpha.relative,
			soundSha256:refreshedSound.entry.sha256, streamSha256:refreshedStream.entry.sha256,
			fontSha256:refreshedFont.entry.sha256,
			sound:audioSignature(newSound), stream:vorbisMetadataSignature(cast newStream.__buffer.__srcVorbisFile),
			font:fontSignature(newFont), refreshed:true};
		var beta = cppOwners[1];
		var betaIdentity:RuntimeOwnerAssetIdentity = cast beta.identity;
		var currentBeta = RuntimeOwnerAssetIdentity.acquire(Std.string(beta.ownerRoot),
			ImportEngine.PSYCH, 'package');
		if (currentBeta != betaIdentity) {
			beta.identity = currentBeta;
			beta.limeFacade = PsychOwnerLimeAssets.create(Std.string(beta.ownerRoot));
			beta.openFlFacade = PsychOwnerOpenFlAssets.create(Std.string(beta.ownerRoot));
			beta.libraryView = Reflect.callMethod(beta.limeFacade,
				Reflect.field(beta.limeFacade, 'getLibrary'), [library]);
			beta.openLibraryView = Reflect.callMethod(beta.openFlFacade,
				Reflect.field(beta.openFlFacade, 'getLibrary'), [library]);
			beta.libraryFuture = Reflect.callMethod(beta.limeFacade,
				Reflect.field(beta.limeFacade, 'loadLibrary'), [library]);
			beta.soundBuffer = Reflect.callMethod(beta.limeFacade,
				Reflect.field(beta.limeFacade, 'getAudioBuffer'), [soundId]);
			beta.font = Reflect.callMethod(beta.limeFacade,
				Reflect.field(beta.limeFacade, 'getFont'), [fontId]);
		}
	}

	static function verifyUnrelatedOwnerEpochKeepsCppBeta():Void {
		var beta = cppOwners[1];
		var lime = beta.limeFacade;
		var identity:RuntimeOwnerAssetIdentity = cast beta.identity;
		var view:AssetLibrary = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'getLibrary'), [Std.string(request.cppLibrary)]);
		var future:Future<Dynamic> = cast Reflect.callMethod(lime,
			Reflect.field(lime, 'loadLibrary'), [Std.string(request.cppLibrary)]);
		var current = RuntimeOwnerAssetIdentity.acquire(Std.string(beta.ownerRoot),
			ImportEngine.PSYCH, 'package');
		check(current == identity && view == beta.libraryView && future == beta.libraryFuture
			&& sameAudio(view.getAudioBuffer(Std.string(request.cppSoundId)), beta.soundBaseline)
			&& sameVorbisStream(cast beta.streamSound, cast beta.streamSourceBytes)
			&& sameFont(view.getFont(Std.string(request.cppFontId)), beta.fontBaseline),
			'Unrelated third-owner import invalidated the stable CPP beta library/cache');
	}

	static function verifyCppOwnerRelease():Void {
		var alpha = cppOwners[0];
		var beta = cppOwners[1];
		var alphaView:AssetLibrary = cast alpha.libraryView;
		var betaView:AssetLibrary = cast beta.libraryView;
		PsychOwnerAssetPath.releaseOwner(Std.string(alpha.ownerRoot));
		var alphaStale = false;
		try alphaView.getFont(Std.string(request.cppFontId)) catch (_:Dynamic) alphaStale = true;
		check(alphaStale && sameAudio(betaView.getAudioBuffer(Std.string(request.cppSoundId)),
			beta.soundBaseline) && sameFont(betaView.getFont(Std.string(request.cppFontId)), beta.fontBaseline),
			'Releasing CPP alpha invalidated beta or left alpha active');
		var openStale = false;
		try Reflect.callMethod(alpha.openLibraryView, Reflect.field(alpha.openLibraryView, 'getFont'),
			[Std.string(request.cppFontId)]) catch (_:Dynamic) openStale = true;
		check(openStale, 'Released CPP owner left its OpenFL library wrapper active');
		PsychOwnerAssetPath.releaseOwner(Std.string(beta.ownerRoot));
	}

	static function verifyUnknownTargetFailsClosed():Void {
		var ownerRoot = ownerPath(Std.string(unknownOwner.namespace));
		var binding = ImportRefreshManager.ownerAssetIndexBinding(ownerRoot, ImportEngine.PSYCH, 'package');
		check(binding != null && Reflect.field(binding, 'transactionId') != null,
			'Unknown-target fixture did not receive an actual retained receipt binding');
		var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, ImportEngine.PSYCH, 'package');
		check(identity.bindingState == 'ready' && identity.indexVersion == 2
			&& !identity.loadProfileComplete && identity.loadTarget == null,
			'An uncaptured target was inferred from the Windows host');
		var lime = PsychOwnerLimeAssets.create(ownerRoot);
		var openFl = PsychOwnerOpenFlAssets.create(ownerRoot);
		var limeFuture:Future<AssetLibrary> = cast Reflect.callMethod(lime, Reflect.field(lime, 'loadLibrary'),
			[Std.string(request.unknownLibrary)]);
		var openFuture:Future<Dynamic> = cast Reflect.callMethod(openFl, Reflect.field(openFl, 'loadLibrary'),
			[Std.string(request.unknownLibrary)]);
		check(limeFuture != null && limeFuture.isError
			&& openFuture != null && openFuture.isError,
			'Unknown-target owner libraries did not fail closed through both facades');
		unknownOwner.ownerRoot = ownerRoot;
	}

	static function verifyUnrelatedOwnerEpochKeepsAlpha():Void {
		var alpha = owners[0];
		var identity:RuntimeOwnerAssetIdentity = cast alpha.identity;
		var lime = alpha.limeFacade;
		var before:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'),
			[Std.string(request.warmLibrary)]);
		var futureBefore:Dynamic = Reflect.callMethod(lime, Reflect.field(lime, 'loadLibrary'),
			[Std.string(request.warmLibrary)]);
		var current = RuntimeOwnerAssetIdentity.acquire(Std.string(alpha.ownerRoot),
			ImportEngine.PSYCH, 'package');
		check(current == identity,
			'Unrelated owner import invalidated a stable committed alpha identity');
		var after:AssetLibrary = cast Reflect.callMethod(lime, Reflect.field(lime, 'getLibrary'),
			[Std.string(request.warmLibrary)]);
		var futureAfter:Dynamic = Reflect.callMethod(lime, Reflect.field(lime, 'loadLibrary'),
			[Std.string(request.warmLibrary)]);
		check(before == after && futureBefore == futureAfter
			&& before.getText(Std.string(request.textId)) == alpha.expected.warmText,
			'Unrelated third-owner receipt did not preserve alpha library and cache');
	}

	static function verifyOwnerRelease():Void {
		var alpha = owners[0];
		var beta = owners[1];
		var oldAlpha:AssetLibrary = cast alpha.warmView;
		var betaBefore:AssetLibrary = cast beta.warmView;
		PsychOwnerAssetPath.releaseOwner(Std.string(alpha.ownerRoot));
		var alphaStale = false;
		try oldAlpha.getText(Std.string(request.textId)) catch (_:Dynamic) alphaStale = true;
		check(alphaStale, 'Released owner left its retained Lime library handle active');
		check(beta.warmView == betaBefore
			&& betaBefore.getText(Std.string(request.textId)) == beta.expected.warmText,
			'Releasing alpha disturbed beta with the same library and asset IDs');
		var openStale = false;
		try Reflect.callMethod(alpha.openView, Reflect.field(alpha.openView, 'getText'),
			[Std.string(request.textId)]) catch (_:Dynamic) openStale = true;
		check(openStale, 'Released owner left its retained OpenFL library handle active');
		PsychOwnerAssetPath.releaseOwner(Std.string(beta.ownerRoot));
		PsychOwnerAssetPath.releaseOwner(Std.string(unknownOwner.ownerRoot));
	}

	static function expectedOwner(relative:String):Dynamic {
		for (expected in (cast request.owners:Array<Dynamic>))
			if (Reflect.field(expected, 'rootRelative') == relative) return expected;
		return null;
	}

	static function expectedCppOwner(relative:String):Dynamic {
		for (expected in (cast request.cppOwners:Array<Dynamic>))
			if (Reflect.field(expected, 'rootRelative') == relative) return expected;
		return null;
	}

	static function audioSamples(buffer:AudioBuffer):Array<Int> {
		if (buffer == null || buffer.data == null) return null;
		var output:Array<Int> = [];
		for (index in 0...buffer.data.length) output.push(Std.int(buffer.data[index]));
		return output;
	}

	static function sameAudio(left:AudioBuffer, right:AudioBuffer):Bool {
		if (left == null || right == null || left.sampleRate != right.sampleRate
			|| left.channels != right.channels || left.bitsPerSample != right.bitsPerSample) return false;
		var leftSamples = audioSamples(left);
		var rightSamples = audioSamples(right);
		if (leftSamples == null || rightSamples == null || leftSamples.length != rightSamples.length) return false;
		for (index in 0...leftSamples.length) if (leftSamples[index] != rightSamples[index]) return false;
		return true;
	}

	static function audioSignature(buffer:AudioBuffer):String {
		if (buffer == null) return '<null>';
		var samples = audioSamples(buffer);
		return buffer.sampleRate + ':' + buffer.channels + ':' + buffer.bitsPerSample + ':'
			+ (samples == null ? '<null>' : samples.join(','));
	}

	static function isVorbisBacked(sound:Sound):Bool
		return sound != null && sound.__buffer != null && sound.__buffer.__srcVorbisFile != null;

	static function vorbisBaselineFromPrivateCopy(bytes:Bytes):VorbisFile {
		check(bytes != null && bytes.length > 0, 'Cannot build a Vorbis baseline from empty bytes');
		var digest = Sha256.make(bytes).toHex().toLowerCase();
		var directory = 'tmp';
		if (!FileSystem.exists(directory)) FileSystem.createDirectory(directory);
		var path = Path.normalize(directory + '/owner-library-vorbis-baseline-' + digest + '.ogg');
		if (FileSystem.exists(path)) {
			check(Sha256.make(File.getBytes(path)).toHex().toLowerCase() == digest,
				'Existing immutable Vorbis baseline copy does not match its content hash');
		} else {
			File.saveBytes(path, bytes);
		}
		var baseline = VorbisFile.fromFile(path);
		check(baseline != null, 'Pinned Lime Vorbis decoder rejected the exact-byte baseline copy');
		return baseline;
	}

	static function vorbisMetadataSignature(file:VorbisFile):String {
		if (file == null) return '<null>';
		var info = file.info();
		if (info == null) return '<no-info>';
		return info.version + ':' + info.channels + ':' + info.rate + ':' + info.bitrateLower + ':'
			+ info.bitrateNominal + ':' + info.bitrateUpper + ':' + Int64.toInt(file.pcmTotal()) + ':'
			+ Std.string(file.timeTotal()) + ':' + file.seekable() + ':' + file.streams();
	}

	static function readVorbisBlock(file:VorbisFile):Bytes {
		if (file == null) return null;
		var decoded = Bytes.alloc(4096);
		var length = file.read(decoded, 0, decoded.length, false, 2, true);
		if (length <= 0 || length > decoded.length) return null;
		return decoded.sub(0, length);
	}

	static function sameVorbisStream(sound:Sound, sourceBytes:Bytes):Bool {
		if (!isVorbisBacked(sound) || sourceBytes == null) return false;
		var routedBuffer:AudioBuffer = sound.__buffer;
		var routed:VorbisFile = cast routedBuffer.__srcVorbisFile;
		var baseline = vorbisBaselineFromPrivateCopy(sourceBytes);
		var result = false;
		try {
			var baselineInfo = baseline.info();
			var routedInfo = routed.info();
			var metadataMatches = baselineInfo != null && routedInfo != null
				&& routedBuffer.data == null && routedBuffer.channels == baselineInfo.channels
				&& routedBuffer.sampleRate == baselineInfo.rate && routedBuffer.bitsPerSample == 16
				&& vorbisMetadataSignature(routed) == vorbisMetadataSignature(baseline)
				&& routed.pcmSeek(Int64.ofInt(0)) == 0 && baseline.pcmSeek(Int64.ofInt(0)) == 0;
			if (metadataMatches) {
				var routedPcm = readVorbisBlock(routed);
				var baselinePcm = readVorbisBlock(baseline);
				result = sameBytes(routedPcm, baselinePcm);
			}
		} catch (_:Dynamic) {
			result = false;
		}
		baseline.clear();
		return result;
	}

	static function sameBytes(left:Bytes, right:Bytes):Bool {
		if (left == null || right == null || left.length != right.length) return false;
		for (index in 0...left.length) if (left.get(index) != right.get(index)) return false;
		return true;
	}

	static function hasOnlyIds(actual:Array<String>, expected:Array<String>):Bool {
		if (actual == null || expected == null || actual.length != expected.length) return false;
		for (id in expected) if (actual.indexOf(id) < 0) return false;
		return true;
	}

	static function sameOwnerPath(actual:String, expected:String):Bool {
		if (actual == null || expected == null) return false;
		var normalizedActual = StringTools.replace(Path.normalize(actual), '\\', '/').toLowerCase();
		var normalizedExpected = StringTools.replace(Path.normalize(expected), '\\', '/').toLowerCase();
		return normalizedActual == normalizedExpected;
	}

	static function sameFont(left:LimeFont, right:LimeFont):Bool
		return left != null && right != null && fontSampleData(left) == fontSampleData(right);

	static function fontBaselineFromPrivateCopy(bytes:Bytes):LimeFont {
		check(bytes != null && bytes.length > 0, 'Cannot build a native font baseline from empty bytes');
		var digest = Sha256.make(bytes).toHex().toLowerCase();
		var directory = 'tmp';
		if (!FileSystem.exists(directory)) FileSystem.createDirectory(directory);
		var path = Path.normalize(directory + '/owner-library-font-baseline-' + digest + '.otf');
		if (FileSystem.exists(path)) {
			check(Sha256.make(File.getBytes(path)).toHex().toLowerCase() == digest,
				'Existing immutable font baseline copy does not match its content hash');
		} else {
			File.saveBytes(path, bytes);
		}
		var baseline = LimeFont.fromFile(path);
		check(baseline != null, 'Pinned Lime font decoder rejected the exact-byte baseline copy');
		return baseline;
	}

	static function fontSignature(font:LimeFont):String {
		if (font == null) return '<null>';
		return Sha256.make(Bytes.ofString(fontSampleData(font))).toHex().toLowerCase();
	}

	static function fontSampleData(font:LimeFont):String {
		var parts = fontSampleParts(font);
		return parts.map(function(part:Dynamic):String return part.value).join('|');
	}

	static function fontMismatch(left:LimeFont, right:LimeFont):String {
		if (left == null || right == null)
			return 'null-side:left=' + (left == null) + ',right=' + (right == null);
		var leftParts = fontSampleParts(left);
		var rightParts = fontSampleParts(right);
		var sharedLength = leftParts.length < rightParts.length ? leftParts.length : rightParts.length;
		for (index in 0...sharedLength) {
			if (leftParts[index].value != rightParts[index].value)
				return leftParts[index].label + ': actual=' + Std.string(leftParts[index].value)
					+ ', baseline=' + Std.string(rightParts[index].value);
		}
		if (leftParts.length != rightParts.length)
			return 'part-count: actual=' + leftParts.length + ', baseline=' + rightParts.length;
		return 'match';
	}

	static function fontSampleParts(font:LimeFont):Array<Dynamic> {
		check(font != null, 'Cannot inspect a null native font');
		var parts:Array<Dynamic> = [
			{label:'name', value:Std.string(font.name)},
			{label:'numGlyphs', value:Std.string(font.numGlyphs)},
			{label:'height', value:Std.string(font.height)},
			{label:'unitsPerEM', value:Std.string(font.unitsPerEM)},
			{label:'ascender', value:Std.string(font.ascender)},
			{label:'descender', value:Std.string(font.descender)}
		];
		var characters = 'Aa0g';
		var glyphs = font.getGlyphs(characters);
		check(glyphs != null && glyphs.length == characters.length,
			'Pinned Lime font did not return glyph indexes for the native sample');
		for (index in 0...glyphs.length) {
			var glyph = glyphs[index];
			// Lime and OpenFL Font wrappers can share one native face. renderGlyph sets
			// that face's size, so normalize it before reading size-dependent metrics.
			var rendered:lime.graphics.Image = font.renderGlyph(glyph, 32);
			check(rendered != null && rendered.width > 0 && rendered.height > 0,
				'Pinned Lime font failed to render sample glyph ' + Std.string(Std.int(glyph)));
			var metrics = font.getGlyphMetrics(glyph);
			check(metrics != null && metrics.advance != null && metrics.horizontalBearing != null
				&& metrics.verticalBearing != null,
				'Pinned Lime font did not return metrics for glyph ' + Std.string(Std.int(glyph)));
			var character = characters.charAt(index);
			parts.push({label:'glyph-metrics-' + character, value:'glyph=' + Std.string(Std.int(glyph)) + ';advance=' + Std.string(metrics.advance.x)
				+ ',' + Std.string(metrics.advance.y) + ';height=' + Std.string(metrics.height)
				+ ';horizontal=' + Std.string(metrics.horizontalBearing.x) + ','
				+ Std.string(metrics.horizontalBearing.y) + ';vertical='
				+ Std.string(metrics.verticalBearing.x) + ',' + Std.string(metrics.verticalBearing.y)});
			parts.push({label:'glyph-raster-' + character, value:'image=' + rendered.width + 'x' + rendered.height + '@' + Std.string(rendered.x)
				+ ',' + Std.string(rendered.y)});
			for (y in 0...rendered.height) {
				for (x in 0...rendered.width)
					parts.push({label:'glyph-pixel-' + character + '-' + x + '-' + y,
						value:StringTools.hex(rendered.getPixel32(x, y, lime.graphics.PixelFormat.ARGB32), 8)});
			}
		}
		return parts;
	}

	static function futureSetPending(futures:Array<Future<Dynamic>>, label:String):Bool {
		var pending = false;
		for (future in futures) {
			if (future == null) throw label + ' returned no Future';
			if (future.isError) throw label + ' failed: ' + Std.string(future.error);
			if (!future.isComplete) pending = true;
		}
		return pending;
	}

	static function bitmapPixels(bitmap:BitmapData):Array<Int> {
		return [bitmap.getPixel32(0, 0), bitmap.getPixel32(1, 0),
			bitmap.getPixel32(0, 1), bitmap.getPixel32(1, 1)];
	}

	static function imagePixels(image:lime.graphics.Image):Array<Int> {
		return [image.getPixel32(0, 0, lime.graphics.PixelFormat.ARGB32),
			image.getPixel32(1, 0, lime.graphics.PixelFormat.ARGB32),
			image.getPixel32(0, 1, lime.graphics.PixelFormat.ARGB32),
			image.getPixel32(1, 1, lime.graphics.PixelFormat.ARGB32)];
	}

	static function expectedRawImagePixels(expected:Dynamic):Array<Int> {
		return [0, Std.int(expected.topRight), Std.int(expected.bottomLeft), Std.int(expected.bottomRight)];
	}

	static function samePixels(left:Array<Int>, right:Array<Int>):Bool {
		if (left == null || right == null || left.length != right.length) return false;
		for (index in 0...left.length) if (left[index] != right[index]) return false;
		return true;
	}

	static function formatPixels(pixels:Array<Int>):String {
		if (pixels == null) return '<null>';
		return '[' + pixels.map(function(pixel:Int):String return '0x' + StringTools.hex(pixel, 8)).join(',') + ']';
	}

	static function ownerPath(namespace:String):String return 'assets/imported_mods/' + namespace;

	static function removeGlobalSentinel():Void {
		if (globalSentinel != null) {
			if (LimeAssets.getLibrary(Std.string(request.warmLibrary)) == globalSentinel)
				LimeAssets.removeLibrary(Std.string(request.warmLibrary), false);
			globalSentinel = null;
		}
	}

	static function removeGlobalSentinels():Void {
		removeGlobalSentinel();
		if (cppGlobalSentinel != null) {
			var library = Std.string(request.cppLibrary);
			if (LimeAssets.getLibrary(library) == cppGlobalSentinel)
				LimeAssets.removeLibrary(library, false);
			cppGlobalSentinel = null;
		}
	}

	static function restoreCppFixtureInputs():Void {
		try if (cppAlphaChangedSoundPath != null && cppAlphaOriginalSound != null)
			File.saveBytes(cppAlphaChangedSoundPath, cppAlphaOriginalSound) catch (_:Dynamic) {}
		try if (cppAlphaChangedStreamPath != null && cppAlphaOriginalStream != null)
			File.saveBytes(cppAlphaChangedStreamPath, cppAlphaOriginalStream) catch (_:Dynamic) {}
		try if (cppAlphaChangedFontPath != null && cppAlphaOriginalFont != null)
			File.saveBytes(cppAlphaChangedFontPath, cppAlphaOriginalFont) catch (_:Dynamic) {}
	}

	static function cleanup():Void {
		removeGlobalSentinels();
		for (ownerInfo in owners) if (ownerInfo != null && ownerInfo.ownerRoot != null)
			PsychOwnerAssetPath.releaseOwner(Std.string(ownerInfo.ownerRoot));
		for (ownerInfo in cppOwners) if (ownerInfo != null && ownerInfo.ownerRoot != null)
			PsychOwnerAssetPath.releaseOwner(Std.string(ownerInfo.ownerRoot));
		if (unknownOwner != null && unknownOwner.ownerRoot != null)
			PsychOwnerAssetPath.releaseOwner(Std.string(unknownOwner.ownerRoot));
		restoreCppFixtureInputs();
	}
}
#end
