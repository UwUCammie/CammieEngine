package;

#if sys
import flixel.FlxG;
import haxe.io.Path;
import lime.app.Future;
import lime.graphics.Image;
import lime.graphics.PixelFormat;
import lime.utils.AssetLibrary;
import lime.utils.AssetType;
import lime.utils.Assets as HostLimeAssets;
import openfl.display.BitmapData;
import openfl.events.Event;
import openfl.utils.Assets as HostOpenFlAssets;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;

using StringTools;

/** Actual retained-import proof for Nightmare Vision's raw compiled Assets API. */
@:access(RuntimeSmokeHarness)
class RuntimeNvAssetsProbe {
	static var started:Bool = false;
	static var phase:Int = 0;
	static var startedAt:Float = 0;
	static var workerMutex:Mutex = new Mutex();
	static var workerDone:Bool = false;
	static var workerError:String = '';
	static var workerResult:Dynamic;
	static var request:Dynamic;
	static var owners:Array<Dynamic> = [];
	static var setups:Array<Dynamic> = [];

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_NV_ASSETS_SMOKE') == '1';

	static function check(value:Bool, message:String):Void if (!value) throw message;

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			if (!started) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
				started = true;
				startedAt = Sys.time();
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null,
					'Nightmare Vision raw Assets smoke requires muted audio and isolated saves');
				request = CoolUtil.parseJson(File.getContent('tmp/nv-assets-request.json'));
				check(request != null && request.kind == 'nightmare-vision-raw-assets'
					&& request.generated == true && request.buildTarget == 'windows',
					'Expected a generated explicit-Windows Nightmare Vision fixture');
				check(request.sourceRoot != null && request.library != null && request.owners != null
					&& request.owners.length == 2,
					'Nightmare Vision package/core fixture metadata is incomplete');
				check(HostLimeAssets.getLibrary(Std.string(request.library)) == null
					&& HostOpenFlAssets.getLibrary(Std.string(request.library)) == null,
					'Generated library name is already registered in the host process');
				startImport(Std.string(request.sourceRoot));
				phase = 1;
				return;
			}
			check(Sys.time() - startedAt < 90, 'Nightmare Vision raw Assets native probe timed out');
			if (phase == 1) {
				var state = workerSnapshot();
				if (state.error != '') throw 'Actual retained Nightmare Vision import failed: ' + state.error;
				if (!state.done || ImportRefreshManager.browseTick().busy) return;
				check(state.result != null && state.result.roots != null && state.result.roots.length == 3,
					'Expected the actual scanner to retain one provider and two package roots');
				owners = cast state.result.roots;
				verifyCommittedOwners();
				for (owner in owners) if (owner.directory == 'alpha' || owner.directory == 'beta')
					setups.push(createOwnerRuntime(owner));
				check(setups.length == 2, 'Both selected content packages must have live source interpreters');
				for (setup in setups) executeSourceProbe(setup);
				beginLibraryLoads();
				phase = 2;
				return;
			}
			if (phase == 2) {
				if (librariesPending()) return;
				verifyLoadedLibrariesAndEvents();
				phase = 3;
				return;
			}
			if (phase == 3) {
				if (typedLoadsPending()) return;
				verifyTypedLoads();
				verifyIsolationAndHostRegistry();
				retireAlphaAndVerifyBeta();
				cleanup();
				RuntimeSmokeHarness.emit('nv_assets_native_verified', {
					managerTransaction: true,
					rootCount: owners.length,
					packageCount: setups.length,
					explicitBuildTarget: request.buildTarget,
					packageAndCoreReceipts: true,
					providerPackageReceipt: true,
					bareQualifiedLegacyAliasAndReflection: true,
					packageOverridesCore: true,
					typedShadowFailsClosed: true,
					looseAndSiblingAssetsBlocked: true,
					limeOpenFlImagesAndPixels: true,
					localLibrariesAndFutures: true,
					ownerCacheIsolationAndClear: true,
					ownerEventsAndTeardown: true
				});
				phase = 4;
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) {
			cleanup();
			RuntimeSmokeHarness.fail('nv-assets', Std.string(error));
		}
	}

	static function startImport(source:String):Void {
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
				var scan = ImportWorkflow.scanNow(source, ImportEngine.NIGHTMARE_VISION);
				check(scan != null && scan.errors != null && scan.errors.length == 0
					&& scan.rootScanTruncated != true && scan.packageScanTruncated != true,
					'Generated Nightmare Vision scan was incomplete');
				check(scan.songsFound == 0 && scan.detectedRoots != null && scan.detectedRoots.length == 3,
					'Fixture must scan as one game root and two content packages without charts');
				var rootSummaries:Array<Dynamic> = [];
				var contexts:Array<ImportRefreshManager.ImportSourceBuildContext> = [];
				for (root in scan.detectedRoots) {
					check(ImportRevision.normalizeEngine(root.engine) == ImportEngine.NIGHTMARE_VISION,
						'Unexpected selected source engine: ' + root.engine);
					var scannerRelative = relativeRoot(source, root.root);
					var ownerRelative = scannerRelative;
					var directory = scannerRelative == '' ? 'provider' : Path.withoutDirectory(scannerRelative);
					var parts = scannerRelative.split('/');
					if (parts.length == 3 && parts[0] == 'content' && parts[1] != '' && parts[2] == 'assets') {
						ownerRelative = 'content/' + parts[1];
						directory = parts[1];
					}
					rootSummaries.push({root:root.root, rootRelative:ownerRelative,
						scannerRootRelative:scannerRelative, directory:directory});
					contexts.push({sourceRoot:root.root, engine:ImportEngine.NIGHTMARE_VISION,
						build:{target:'windows', command:'', flags:[], values:[], flagsComplete:true}});
				}
				var imported = ImportRefreshManager.importOnce(source, ImportEngine.NIGHTMARE_VISION, scan,
					new Map(), ImportWorkflow.convertRetainedSource, function():Bool return false,
					function(_payload:Dynamic):Void {}, contexts);
				check(imported != null && imported.failed == 0 && imported.importedSongs != null
					&& imported.importedSongs.length == 0 && imported.copiedAssets > 0,
					'Actual zero-song retained import did not publish mapped assets: '
						+ (imported == null || imported.errors == null ? '' : imported.errors.join('; ')));
				result = {roots:rootSummaries};
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

	static function relativeRoot(source:String, root:String):String {
		var base = slash(Path.normalize(source));
		var selected = slash(Path.normalize(root));
		var foldedBase = base.toLowerCase();
		var foldedSelected = selected.toLowerCase();
		if (foldedSelected == foldedBase) return '';
		var prefix = foldedBase + '/';
		if (!foldedSelected.startsWith(prefix)) throw 'Scanner selected a root outside its source: ' + root;
		return selected.substr(prefix.length);
	}

	static function slash(value:String):String return StringTools.replace(value, '\\', '/');

	static function workerSnapshot():Dynamic {
		workerMutex.acquire();
		var result = {done:workerDone, error:workerError, result:workerResult};
		workerMutex.release();
		return result;
	}

	static function verifyCommittedOwners():Void {
		var provider:Dynamic = null;
		var byDirectory:Map<String, Dynamic> = new Map();
			for (item in owners) {
				var relative = Std.string(item.rootRelative);
			var ownerRoot = CompatScriptManifest.destinationRoot(Std.string(item.root), ImportEngine.NIGHTMARE_VISION);
			item.ownerRoot = ownerRoot;
			if (relative == '') provider = item;
			else byDirectory.set(Std.string(item.directory), item);
		}
		check(provider != null && byDirectory.exists('alpha') && byDirectory.exists('beta'),
			'Actual scanner did not preserve the provider/alpha/beta retained roots');
		for (directory in ['alpha', 'beta']) {
			var packageRoot = byDirectory.get(directory);
			check(packageRoot.scannerRootRelative == 'content/' + directory + '/assets'
				&& packageRoot.rootRelative == 'content/' + directory,
				'The selected package assets root was not bound to its direct retained family member: ' + directory);
		}
		var providerIdentity = RuntimeOwnerAssetIdentity.acquire(provider.ownerRoot,
			ImportEngine.NIGHTMARE_VISION, 'core');
		check(providerIdentity.bindingState == 'ready' && providerIdentity.complete
			&& providerIdentity.librariesComplete && providerIdentity.loadTarget == request.buildTarget,
			'Ordinary provider core identity was not committed with its captured Windows context');
		var providerCore = providerIdentity.resolve(Std.string(request.library) + ':core-only', 'IMAGE');
		check(providerCore.state == 'found' && providerCore.path != null
			&& providerCore.path.startsWith(provider.ownerRoot + '/__nmv_core/'),
			'Ordinary provider core receipt did not keep its engine asset in the core subtree');
		check(providerIdentity.handoff == null,
			'Ordinary provider identity was incorrectly classified as a receiver handoff');
		provider.identity = providerIdentity;
		for (directory in ['alpha', 'beta']) {
			var owner = byDirectory.get(directory);
			var packageIdentity = RuntimeOwnerAssetIdentity.acquire(owner.ownerRoot,
				ImportEngine.NIGHTMARE_VISION, 'package');
			var coreIdentity = RuntimeOwnerAssetIdentity.acquire(owner.ownerRoot,
				ImportEngine.NIGHTMARE_VISION, 'core');
			check(packageIdentity.bindingState == 'ready' && packageIdentity.complete
				&& packageIdentity.librariesComplete && packageIdentity.loadTarget == request.buildTarget,
				'Package identity is not tied to the explicit retained source context: ' + directory);
			check(coreIdentity.bindingState == 'ready' && coreIdentity.complete
				&& coreIdentity.librariesComplete && coreIdentity.loadTarget == request.buildTarget,
				'Authenticated provider core handoff is missing for ' + directory);
			var handoff = coreIdentity.handoff;
			var receiverNamespace = owner.ownerRoot.substr(CompatScriptManifest.ROOT_PREFIX.length + 1);
			var committedCoreBinding = ImportRefreshManager.ownerAssetIndexBinding(owner.ownerRoot,
				ImportEngine.NIGHTMARE_VISION, 'core');
			var committedHandoff = committedCoreBinding == null ? null : Reflect.field(committedCoreBinding, 'handoff');
			check(handoff != null && handoff.providerNamespace == providerIdentity.owner.substr(
				CompatScriptManifest.ROOT_PREFIX.length + 1)
				&& handoff.providerRootRelative == '' && handoff.receiverRootRelative == owner.rootRelative
				&& handoff.catalogVersion == 3 && handoff.providerProjectSha256 != null
				&& committedCoreBinding != null && Reflect.field(committedCoreBinding, 'owner') == owner.ownerRoot
				&& Reflect.field(committedCoreBinding, 'namespace') == receiverNamespace
				&& committedHandoff != null && Reflect.field(committedHandoff, 'receiverNamespace') == receiverNamespace
				&& Reflect.field(committedHandoff, 'receiverRootRelative') == owner.rootRelative
				&& Reflect.field(committedHandoff, 'providerNamespace') == handoff.providerNamespace
				&& Reflect.field(committedHandoff, 'providerRootRelative') == handoff.providerRootRelative
				&& Reflect.field(committedHandoff, 'providerProjectSha256') == handoff.providerProjectSha256
				&& Reflect.field(committedHandoff, 'catalogVersion') == handoff.catalogVersion,
				'Core sidecar handoff is not bound to the real outer Project and selected receiver');
			check(packageIdentity.libraryState(Std.string(request.library)) == 'declared'
				&& coreIdentity.libraryState(Std.string(request.library)) == 'declared',
				'Package and handed-off core did not retain their declared Project library');
			var sharedPackage = packageIdentity.resolve(Std.string(request.library) + ':shared-image', 'IMAGE');
			var sharedCore = coreIdentity.resolve(Std.string(request.library) + ':shared-image', 'IMAGE');
			var onlyCore = coreIdentity.resolve(Std.string(request.library) + ':core-only', 'IMAGE');
			var onlyPackage = packageIdentity.resolve(Std.string(request.library) + ':' + directory + '-only', 'IMAGE');
			check(sharedPackage.state == 'found' && sharedCore.state == 'found'
				&& sharedPackage.path.startsWith(owner.ownerRoot + '/images/')
				&& sharedCore.path.startsWith(owner.ownerRoot + '/__nmv_core/')
				&& onlyCore.state == 'found' && onlyPackage.state == 'found',
				'Package and handed-off core identities do not retain their separate mapped bytes');
			owner.packageIdentity = packageIdentity;
			owner.coreIdentity = coreIdentity;
			owner.expected = requestOwner(directory);
		}
		owners = [provider, byDirectory.get('alpha'), byDirectory.get('beta')];
		var family = ImportPackageFamilyCatalog.forOwner(byDirectory.get('alpha').ownerRoot);
		check(family != null && family.length == 2,
			'Committed family catalog did not authorize exactly the two source content packages');
		for (member in family) {
			var expected = byDirectory.get(member.directory);
			check(expected != null && expected.ownerRoot == member.root,
				'Committed family mapping did not resolve to the scanner-bound package namespace: ' + member.directory);
		}
	}

	static function requestOwner(directory:String):Dynamic {
		for (owner in (cast request.owners:Array<Dynamic>))
			if (owner.directory == directory) return owner;
		throw 'Generated fixture is missing package data for ' + directory;
	}

	static function createOwnerRuntime(owner:Dynamic):Dynamic {
		var directory = Std.string(owner.directory);
		var root = Std.string(owner.ownerRoot);
		var paths = new NightmareVisionPaths(root, null, null, directory);
		var prefs = new NightmareVisionClientPrefs(root, new CodenameOwnerSaveData(root), OptionsHandler.options);
		prefs.load();
		var mods = new NightmareVisionModsContext(root, directory);
		mods.pushGlobalMods();
		var difficulty = new NightmareVisionDifficultyAdapter(root);
		var plugins = new NightmareVisionPluginRuntime(root, FlxG.state,
			function():Array<NightmareVisionScriptDiscovery.NightmareVisionScriptEntry> return [],
			function(path:String):String return FNFAssets.getText(path),
			function(_child:NightmareVisionScriptInterp,
				_entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry):Void {},
			function(_name:String, _phase:String, _error:Dynamic):Void {},
			function():Void {});
		var interp = new NightmareVisionScriptInterp(FlxG.state);
		PlayState.seedNightmareVisionCommon(interp, paths, prefs, plugins, mods, difficulty);
		var limeFacade:Dynamic = interp.variables.get('Assets');
		var openFlFacade:Dynamic = interp.variables.get('OpenFlAssets');
		check(limeFacade != null && openFlFacade != null,
			'Actual seedNightmareVisionCommon did not bind both owner Assets facades');
		return {owner:owner, paths:paths, prefs:prefs, mods:mods, difficulty:difficulty,
			plugins:plugins, interp:interp, lime:limeFacade, openFl:openFlFacade};
	}

	static function executeSourceProbe(setup:Dynamic):Void {
		var probeResults:Dynamic = {};
		setup.probeResults = probeResults;
		setup.interp.variables.set('__nvAssetProbeResults', probeResults);
		var script = 'import lime.utils.Assets as LimeAssetsApi;\n'
			+ 'import openfl.utils.Assets as OpenFlAssetsApi;\n'
			+ 'import openfl.Assets as LegacyOpenFlAssetsApi;\n'
			+ 'import openfl.Assets;\n'
			+ 'import lime.utils.Assets;\n'
			+ "__nvAssetProbeResults.coreText = LimeAssetsApi.getText('" + request.library + ":core-text');\n"
			+ "__nvAssetProbeResults.packageText = OpenFlAssetsApi.getText('" + request.library + ':' + setup.owner.directory + "-text');\n"
			+ "__nvAssetProbeResults.bareLimeText = Assets.getText('" + request.library + ":core-text');\n"
			+ "__nvAssetProbeResults.bareOpenFlText = OpenFlAssets.getText('" + request.library + ':' + setup.owner.directory + "-text');\n"
			+ "__nvAssetProbeResults.sharedLimeImage = Assets.getImage('" + request.library + ":shared-image');\n"
			+ "__nvAssetProbeResults.sharedOpenFlBitmap = LegacyOpenFlAssetsApi.getBitmapData('" + request.library + ":shared-image');\n"
			+ "__nvAssetProbeResults.resolvedLimeAssets = Type.resolveClass('lime.utils.Assets');\n"
			+ "__nvAssetProbeResults.resolvedOpenFlAssets = Type.resolveClass('openfl.utils.Assets');\n"
			+ "__nvAssetProbeResults.resolvedLegacyOpenFlAssets = Type.resolveClass('openfl.Assets');\n";
		var parser = new NightmareVisionScriptParser();
		setup.interp.execute(parser.parseString(script, 'nv-raw-assets-' + setup.owner.directory));
		var expected:Dynamic = setup.owner.expected;
		var coreText:Dynamic = Reflect.field(probeResults, 'coreText');
		var packageText:Dynamic = Reflect.field(probeResults, 'packageText');
		var bareLimeText:Dynamic = Reflect.field(probeResults, 'bareLimeText');
		var bareOpenFlText:Dynamic = Reflect.field(probeResults, 'bareOpenFlText');
		check(coreText == expected.expectedCoreText && packageText == expected.expectedPackageText
			&& bareLimeText == expected.expectedCoreText && bareOpenFlText == expected.expectedPackageText,
			'HScript raw Assets text mismatch: expected core=' + Std.string(expected.expectedCoreText)
				+ ', package=' + Std.string(expected.expectedPackageText) + '; actual imported core='
				+ Std.string(coreText) + ', imported package=' + Std.string(packageText)
				+ ', bare Assets=' + Std.string(bareLimeText) + ', bare OpenFlAssets=' + Std.string(bareOpenFlText)
				+ '; seeded owner proxies: Assets=' + Std.string(setup.interp.variables.get('Assets') == setup.lime)
				+ ', OpenFlAssets=' + Std.string(setup.interp.variables.get('OpenFlAssets') == setup.openFl));
		var resolvedLime:Dynamic = Reflect.field(probeResults, 'resolvedLimeAssets');
		var resolvedOpenFl:Dynamic = Reflect.field(probeResults, 'resolvedOpenFlAssets');
		var resolvedLegacyOpenFl:Dynamic = Reflect.field(probeResults, 'resolvedLegacyOpenFlAssets');
		check(resolvedLime == setup.lime && resolvedOpenFl == setup.openFl && resolvedLegacyOpenFl == setup.openFl,
			'Type.resolveClass owner mismatch: lime=' + Std.string(resolvedLime == setup.lime)
				+ ', canonical OpenFL=' + Std.string(resolvedOpenFl == setup.openFl)
				+ ', legacy OpenFL=' + Std.string(resolvedLegacyOpenFl == setup.openFl));
		var image:Image = cast Reflect.field(probeResults, 'sharedLimeImage');
		var bitmap:BitmapData = cast Reflect.field(probeResults, 'sharedOpenFlBitmap');
		var expectedPixel = parseArgb(expected.sharedPixel);
		check(image != null && image.width == 2 && image.height == 2
			&& image.getPixel32(0, 0, PixelFormat.ARGB32) == expectedPixel,
			'Lime raw Assets image mismatch: expected=' + Std.string(expectedPixel) + ', actual='
				+ (image == null ? 'null' : Std.string(image.width) + 'x' + Std.string(image.height) + ':'
					+ Std.string(image.getPixel32(0, 0, PixelFormat.ARGB32))));
		check(bitmap != null && bitmap.width == 2 && bitmap.height == 2
			&& bitmap.getPixel32(0, 0) == expectedPixel,
			'OpenFL raw Assets bitmap mismatch: expected=' + Std.string(expectedPixel) + ', actual='
				+ (bitmap == null ? 'null' : Std.string(bitmap.width) + 'x' + Std.string(bitmap.height) + ':'
					+ Std.string(bitmap.getPixel32(0, 0))));
		setup.sourceImage = image;
		setup.sourceBitmap = bitmap;
	}

	static function parseArgb(value:String):Int {
		if (value == null || !~/^[0-9a-fA-F]{8}$/.match(value))
			throw 'Invalid fixture ARGB pixel: ' + value;
		// Parse bytes separately so native signed-int conversion cannot saturate
		// an unsigned 0xFFxxxxxx fixture value before the pixel comparison.
		var pixel = 0;
		for (index in 0...4) {
			var component = Std.parseInt('0x' + value.substr(index * 2, 2));
			if (component == null) throw 'Invalid fixture ARGB component: ' + value;
			pixel = (pixel << 8) | component;
		}
		return pixel;
	}

	static function beginLibraryLoads():Void {
		var library = Std.string(request.library);
		for (setup in setups) {
			var limeGet = Reflect.field(setup.lime, 'getLibrary');
			var openGet = Reflect.field(setup.openFl, 'getLibrary');
			var limeLoad = Reflect.field(setup.lime, 'loadLibrary');
			var openLoad = Reflect.field(setup.openFl, 'loadLibrary');
			check(limeGet != null && openGet != null && limeLoad != null && openLoad != null,
				'Source Assets facade is missing a library API');
			setup.limeView = Reflect.callMethod(setup.lime, limeGet, [library]);
			setup.openView = Reflect.callMethod(setup.openFl, openGet, [library]);
			setup.limeFuture = cast Reflect.callMethod(setup.lime, limeLoad, [library]);
			setup.openFuture = cast Reflect.callMethod(setup.openFl, openLoad, [library]);
			check(setup.limeView != null && setup.openView != null
				&& setup.limeFuture != null && setup.openFuture != null,
				'Owner-local library views or Futures were unavailable');
		}
	}

	static function librariesPending():Bool {
		var pending = false;
		for (setup in setups) {
			var limeFuture:Future<AssetLibrary> = cast setup.limeFuture;
			var openFuture:Future<openfl.utils.AssetLibrary> = cast setup.openFuture;
			if (limeFuture.isError) throw 'Lime package/core composite load failed: ' + Std.string(limeFuture.error);
			if (openFuture.isError) throw 'OpenFL package/core composite load failed: ' + Std.string(openFuture.error);
			if (!limeFuture.isComplete || !openFuture.isComplete) pending = true;
		}
		return pending;
	}

	static function verifyLoadedLibrariesAndEvents():Void {
		var alpha:Dynamic = null;
		var beta:Dynamic = null;
		for (setup in setups) {
			if (setup.owner.directory == 'alpha') alpha = setup;
			if (setup.owner.directory == 'beta') beta = setup;
			var limeFuture:Future<AssetLibrary> = cast setup.limeFuture;
			var openFuture:Future<openfl.utils.AssetLibrary> = cast setup.openFuture;
			var loadedLime:AssetLibrary = limeFuture.value;
			var loadedOpen:openfl.utils.AssetLibrary = openFuture.value;
			check(loadedLime == setup.limeView && Reflect.field(loadedOpen, '__proxy') == setup.limeView,
				'Lime/OpenFL Futures did not return the same local package/core library view');
			var coreText:String = loadedLime.getText('core-text');
			var packageText:String = loadedOpen.getText(Std.string(setup.owner.directory) + '-text');
			check(coreText == setup.owner.expected.expectedCoreText
				&& packageText == setup.owner.expected.expectedPackageText,
				'Real Source-ordered library reads changed core or package text bytes');
			var libraryImage:Image = loadedLime.getImage('shared-image');
			var openImage:Image = loadedOpen.getImage('shared-image');
			var bitmap:BitmapData = openImage == null ? null : BitmapData.fromImage(openImage);
			var expectedPixel = parseArgb(setup.owner.expected.sharedPixel);
			check(libraryImage != null && bitmap != null
				&& libraryImage.getPixel32(0, 0, PixelFormat.ARGB32) == expectedPixel
				&& bitmap.getPixel32(0, 0) == expectedPixel,
				'File-backed Lime/OpenFL library loads lost the package-owned image bytes');
			var imageFuture:Future<Image> = loadedLime.loadImage('shared-image');
			var bitmapFuture:Future<BitmapData> = cast Reflect.callMethod(setup.openFl,
				Reflect.field(setup.openFl, 'loadBitmapData'), [Std.string(request.library) + ':shared-image', true]);
			setup.imageFuture = imageFuture;
			setup.bitmapFuture = bitmapFuture;
			setup.libraryImage = libraryImage;
			setup.libraryBitmap = bitmap;
			var limeCache = Reflect.field(setup.lime, 'cache');
			var openCache = Reflect.field(setup.openFl, 'cache');
			check(limeCache != null && openCache != null
				&& Reflect.getProperty(limeCache, 'enabled') == true && Reflect.getProperty(openCache, 'enabled') == true,
				'Owner-local raw Assets caches are unavailable or disabled');
			setup.limeCache = limeCache;
			setup.openCache = openCache;
		}
		check(alpha != null && beta != null && alpha.limeView != beta.limeView
			&& alpha.openView != beta.openView && alpha.limeCache != beta.limeCache
			&& alpha.openCache != beta.openCache,
			'Same library names shared actual views or cache objects between owners');
		var alphaExpected = parseArgb(alpha.owner.expected.sharedPixel);
		var betaExpected = parseArgb(beta.owner.expected.sharedPixel);
		check(alphaExpected != betaExpected && alpha.libraryImage.getPixel32(0, 0, PixelFormat.ARGB32) == alphaExpected
			&& beta.libraryImage.getPixel32(0, 0, PixelFormat.ARGB32) == betaExpected,
			'Same-ID package image resolved across the two owners');
		verifyRawFacadeIsolation(alpha, beta);
		verifyOwnerEvents(alpha, beta);
		verifyDirectCacheClear(alpha, beta);
	}

	static function verifyRawFacadeIsolation(alpha:Dynamic, beta:Dynamic):Void {
		var library = Std.string(request.library);
		for (setup in [alpha, beta]) {
			var expected = setup.owner.expected;
			var limeImage1:Image = cast Reflect.callMethod(setup.lime,
				Reflect.field(setup.lime, 'getImage'), [library + ':shared-image', true]);
			var limeImage2:Image = cast Reflect.callMethod(setup.lime,
				Reflect.field(setup.lime, 'getImage'), [library + ':shared-image', true]);
			var openBitmap1:BitmapData = cast Reflect.callMethod(setup.openFl,
				Reflect.field(setup.openFl, 'getBitmapData'), [library + ':shared-image', true]);
			var openBitmap2:BitmapData = cast Reflect.callMethod(setup.openFl,
				Reflect.field(setup.openFl, 'getBitmapData'), [library + ':shared-image', true]);
			check(limeImage1 == limeImage2 && openBitmap1 == openBitmap2
				&& limeImage1.getPixel32(0, 0, PixelFormat.ARGB32) == parseArgb(expected.sharedPixel)
				&& openBitmap1.getPixel32(0, 0) == parseArgb(expected.sharedPixel),
				'Direct Assets cache did not reuse its owner-local decoded image');
			setup.rawImage = limeImage1;
			setup.rawBitmap = openBitmap1;
			var exists:Dynamic = Reflect.field(setup.lime, 'exists');
			var sibling = setup.owner.directory == 'alpha' ? 'beta' : 'alpha';
			check(!Reflect.callMethod(setup.lime, exists, [library + ':' + sibling + '-only', AssetType.IMAGE])
				&& !Reflect.callMethod(setup.lime, exists, [library + ':unmapped', AssetType.IMAGE])
				&& !Reflect.callMethod(setup.lime, exists, [library + ':type-shadow', AssetType.IMAGE]),
				'Raw Assets accepted sibling, loose, or package-shadowed core image identities');
			var shadowWasBlocked = false;
			try Reflect.callMethod(setup.lime, Reflect.field(setup.lime, 'getImage'),
				[library + ':type-shadow', true]) catch (_:Dynamic) shadowWasBlocked = true;
			check(shadowWasBlocked, 'Package text type mismatch fell through to a core image with the same ID');
			var missingPath:Dynamic = Reflect.callMethod(setup.lime, Reflect.field(setup.lime, 'getPath'),
				[library + ':unmapped']);
			check(missingPath == null, 'Raw Assets exposed a loose file which Project did not map');
		}
	}

	static function typedLoadsPending():Bool {
		var pending = false;
		for (setup in setups) {
			var imageFuture:Future<Image> = cast setup.imageFuture;
			var bitmapFuture:Future<BitmapData> = cast setup.bitmapFuture;
			if (imageFuture.isError) throw 'Lime typed image Future failed: ' + Std.string(imageFuture.error);
			if (bitmapFuture.isError) throw 'OpenFL typed bitmap Future failed: ' + Std.string(bitmapFuture.error);
			if (!imageFuture.isComplete || !bitmapFuture.isComplete) pending = true;
		}
		return pending;
	}

	static function verifyTypedLoads():Void {
		for (setup in setups) {
			var imageFuture:Future<Image> = cast setup.imageFuture;
			var bitmapFuture:Future<BitmapData> = cast setup.bitmapFuture;
			var expectedPixel = parseArgb(setup.owner.expected.sharedPixel);
			check(imageFuture.value != null && bitmapFuture.value != null
				&& imageFuture.value.getPixel32(0, 0, PixelFormat.ARGB32) == expectedPixel
				&& bitmapFuture.value.getPixel32(0, 0) == expectedPixel,
				'Typed image Future pixels differ from the authenticated package image');
		}
	}

	static function verifyOwnerEvents(alpha:Dynamic, beta:Dynamic):Void {
		var alphaLimeEvents = 0;
		var alphaOpenEvents = 0;
		var betaLimeEvents = 0;
		var betaOpenEvents = 0;
		var alphaOnChange:lime.app.Event<Void->Void> = cast Reflect.field(alpha.lime, 'onChange');
		var betaOnChange:lime.app.Event<Void->Void> = cast Reflect.field(beta.lime, 'onChange');
		var alphaLimeListener = function():Void alphaLimeEvents++;
		var betaLimeListener = function():Void betaLimeEvents++;
		alphaOnChange.add(alphaLimeListener);
		betaOnChange.add(betaLimeListener);
		var alphaOpenListener = function(_event:Event):Void alphaOpenEvents++;
		var betaOpenListener = function(_event:Event):Void betaOpenEvents++;
		Reflect.callMethod(alpha.openFl, Reflect.field(alpha.openFl, 'addEventListener'),
			[Event.CHANGE, alphaOpenListener]);
		Reflect.callMethod(beta.openFl, Reflect.field(beta.openFl, 'addEventListener'),
			[Event.CHANGE, betaOpenListener]);
		check(Reflect.callMethod(alpha.openFl, Reflect.field(alpha.openFl, 'hasEventListener'), [Event.CHANGE])
			&& Reflect.callMethod(alpha.openFl, Reflect.field(alpha.openFl, 'willTrigger'), [Event.CHANGE]),
			'OpenFL owner event listeners are not visible to their source facade');
		var libraryName = Std.string(request.library);
		var alphaIdentity = RuntimeOwnerAssetIdentity.acquire(alpha.owner.ownerRoot,
			ImportEngine.NIGHTMARE_VISION, 'package');
		var betaIdentity = RuntimeOwnerAssetIdentity.acquire(beta.owner.ownerRoot,
			ImportEngine.NIGHTMARE_VISION, 'package');
		var alphaLibrary = PsychOwnerAssetLibraryCache.getLime(alphaIdentity, libraryName);
		var betaLibrary = PsychOwnerAssetLibraryCache.getLime(betaIdentity, libraryName);
		alphaLibrary.onChange.dispatch();
		check(alphaLimeEvents == 1 && alphaOpenEvents == 1
			&& betaLimeEvents == 0 && betaOpenEvents == 0,
			'Owner library change events were not forwarded or crossed owner boundaries');
		var composite:AssetLibrary = cast alpha.limeView;
		composite.onChange.dispatch();
		check(alphaLimeEvents == 2 && alphaOpenEvents == 2
			&& betaLimeEvents == 0 && betaOpenEvents == 0,
			'Direct composite library dispatch did not reach its owner exactly once');
		Reflect.callMethod(alpha.openFl, Reflect.field(alpha.openFl, 'removeEventListener'),
			[Event.CHANGE, alphaOpenListener]);
		Reflect.callMethod(beta.openFl, Reflect.field(beta.openFl, 'removeEventListener'),
			[Event.CHANGE, betaOpenListener]);
		alphaOnChange.remove(alphaLimeListener);
		betaOnChange.remove(betaLimeListener);
		betaLibrary.onChange.dispatch();
		check(betaOpenEvents == 0 && betaLimeEvents == 0,
			'Removed owner event listeners still received a library change');
	}

	static function verifyDirectCacheClear(alpha:Dynamic, beta:Dynamic):Void {
		var limeClear = Reflect.field(alpha.limeCache, 'clear');
		var openClear = Reflect.field(alpha.openCache, 'clear');
		check(limeClear != null && openClear != null,
			'Owner cache objects do not expose their source clear methods');
		Reflect.callMethod(alpha.limeCache, limeClear, []);
		Reflect.callMethod(alpha.openCache, openClear, []);
		var alphaImage:Image = cast Reflect.callMethod(alpha.lime,
			Reflect.field(alpha.lime, 'getImage'), [Std.string(request.library) + ':shared-image', true]);
		var alphaBitmap:BitmapData = cast Reflect.callMethod(alpha.openFl,
			Reflect.field(alpha.openFl, 'getBitmapData'), [Std.string(request.library) + ':shared-image', true]);
		var betaImage:Image = cast Reflect.callMethod(beta.lime,
			Reflect.field(beta.lime, 'getImage'), [Std.string(request.library) + ':shared-image', true]);
		var betaBitmap:BitmapData = cast Reflect.callMethod(beta.openFl,
			Reflect.field(beta.openFl, 'getBitmapData'), [Std.string(request.library) + ':shared-image', true]);
		check(alphaImage != alpha.rawImage && alphaBitmap != alpha.rawBitmap
			&& alphaImage.getPixel32(0, 0, PixelFormat.ARGB32) == parseArgb(alpha.owner.expected.sharedPixel)
			&& alphaBitmap.getPixel32(0, 0) == parseArgb(alpha.owner.expected.sharedPixel),
			'Owner direct cache clear did not clear and decode only its local images');
		check(betaImage == beta.rawImage && betaBitmap == beta.rawBitmap,
			'Clearing alpha raw Assets cache changed beta owner cache entries');
	}

	static function verifyIsolationAndHostRegistry():Void {
		var library = Std.string(request.library);
		check(HostLimeAssets.getLibrary(library) == null && HostOpenFlAssets.getLibrary(library) == null,
			'Owner-local library get/load registered or replaced a process-global library');
	}

	static function retireAlphaAndVerifyBeta():Void {
		var alpha:Dynamic = null;
		var beta:Dynamic = null;
		for (setup in setups) {
			if (setup.owner.directory == 'alpha') alpha = setup;
			if (setup.owner.directory == 'beta') beta = setup;
		}
		check(alpha != null && beta != null, 'Both owner runtimes are required for teardown isolation');
		alpha.paths.releaseOwnerAssets();
		check(staleLibraryRejected(alpha.limeView, 'core-text')
			&& staleOpenFlLibraryRejected(alpha.openView, 'alpha-text'),
			'Released package owner left a usable retained Lime/OpenFL library view');
		var betaText:String = Reflect.callMethod(beta.lime,
			Reflect.field(beta.lime, 'getText'), [Std.string(request.library) + ':beta-text']);
		check(betaText == beta.owner.expected.expectedPackageText,
			'Releasing alpha invalidated beta owner Assets');
		alpha.released = true;
	}

	static function staleLibraryRejected(library:AssetLibrary, id:String):Bool {
		try {
			library.getText(id);
			return false;
		} catch (_:Dynamic) return true;
	}

	static function staleOpenFlLibraryRejected(library:openfl.utils.AssetLibrary, id:String):Bool {
		try {
			library.getText(id);
			return false;
		} catch (_:Dynamic) return true;
	}

	static function cleanup():Void {
		for (setup in setups) {
			if (setup == null) continue;
			try if (!setup.released && setup.paths != null) setup.paths.releaseOwnerAssets() catch (_:Dynamic) {}
			try if (setup.interp != null) setup.interp.release() catch (_:Dynamic) {}
			try if (setup.plugins != null) setup.plugins.destroy() catch (_:Dynamic) {}
			try if (setup.mods != null) setup.mods.release() catch (_:Dynamic) {}
			try if (setup.prefs != null) setup.prefs.release() catch (_:Dynamic) {}
			try if (setup.difficulty != null) setup.difficulty.release() catch (_:Dynamic) {}
		}
		setups = [];
	}
}
#end
