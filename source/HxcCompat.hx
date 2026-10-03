package;

import HxcMenuSpec.HxcMenuItemSpec;
import HxcMenuSpec.HxcMenuSpecData;
import HxcPauseSpec.HxcPauseSpecData;
import HxcCutsceneTimeline.HxcCutsceneTimelineData;
import HxcNoteTextSpec.HxcNoteTextRule;
import HxcNoteTextSpec.HxcNoteTextStaticOverlayData;
import HxcNoteTextSpec.HxcNoteTextSpecData;
import HxcStoryMenuSpec.HxcStoryMenuSpecData;

using StringTools;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** A diagnostic produced while inspecting a donor HXC class. */
typedef HxcCompatDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
}

/** The data-only part of an HXC event adapter. */
typedef HxcCompatEventAdapter = {
	var sourceName:String;
	var canonicalName:String;
	var fields:Array<String>;
	var safe:Bool;
}

/**
	One donor function parameter together with its optionality. HXC allows
	`?name` and `name:Type = default` parameters; hscript only understands the
	`?` marker (filling null), so the default value has to be replayed as a
	null-guard prologue when it is a literal.
*/
typedef HxcCompatArgumentInfo = {
	var name:String;
	var optional:Bool;
	var defaultValue:String;
	@:optional var type:String;
}

/** One lifecycle method which can be exposed to the native HScript state. */
typedef HxcCompatCallbackAdapter = {
	var sourceName:String;
	var canonicalName:String;
	var arguments:Array<String>;
	var body:String;
	var safe:Bool;
	@:optional var argumentInfos:Array<HxcCompatArgumentInfo>;
}

private typedef HxcCompatFunction = {
	var name:String;
	var arguments:Array<String>;
	var body:String;
	@:optional var argumentInfos:Array<HxcCompatArgumentInfo>;
}

private typedef HxcCompatInheritance = {
	var path:String;
	var functions:Array<HxcCompatCallbackAdapter>;
	var stateDeclarations:Array<HxcCompatStateDeclaration>;
}

/** One top-level HXC declaration selected without executing donor code. */
private typedef HxcCompatClassFragment = {
	var name:String;
	var base:String;
	var source:String;
}

#if sys
private typedef HxcCompatCharacterFile = { var path:String; var source:String; }
#end

/** A class-level literal which can be carried into generated HScript safely. */
typedef HxcCompatStateInitializer = {
	var name:String;
	var value:String;
}

private typedef HxcCompatStateDeclaration = {
	var name:String;
	var initializer:String;
}

private typedef HxcCompatTypedGraphRoot = {
	var field:String;
	var itemType:String;
}

private typedef HxcCompatIfBlock = {
	var condition:String;
	var body:String;
}

/** A complete boolean preference switch that assigns an owned camera's filter list. */
private typedef HxcShaderFilterSwitch = {
	var variable:String;
	var saveField:String;
	var preferenceField:String;
	var camera:String;
	var trueFilters:Array<String>;
	var falseFilters:Array<String>;
	var start:Int;
	var length:Int;
}

/** Literal song-credit choices carried into the native banner adapter. */
private typedef HxcCompatSongCreditsPlan = {
	var defaultIcon:String;
	var pixelIcon:String;
	var overrides:Array<{var song:String; var icon:String;}>;
}

/** Structural native menu description emitted for complete HXC menu graphs. */
private typedef HxcCompatMenuPlan = HxcMenuSpecData;
private typedef HxcCompatPausePlan = HxcPauseSpecData;

/** Literal rules for a manifest-scoped Freeplay capsule module. */
private typedef HxcCompatFreeplayPlan = {
	var levelIds:Array<String>;
	var levelIdsName:String;
	var iconMethodName:String;
	var displayMethodName:String;
	var characterRules:Array<{var key:String; var icon:String;}>;
	var songRules:Array<{var key:String; var icon:String;}>;
	var variationRules:Array<{var key:String; var variation:String; var matchIcon:String; var fallbackIcon:String;}>;
	var iconOffsetX:Float;
	var atlas:String;
	var animations:Array<{var name:String; var prefix:String; var fps:Float; var looped:Bool;}>;
	var defaultAnimation:String;
	var animationOverrides:Array<{var song:String; var animation:String;}>;
}

private typedef HxcCompatFreeplaySwitchRules = {
	var direct:Array<{var key:String; var value:String;}>;
	var variation:Array<{var key:String; var variation:String; var matchIcon:String; var fallbackIcon:String;}>;
}

/**
	Result of the deliberately small HXC compatibility pass.

	HXC is Haxe-like, but it is not HScript and its callback payload classes are
	not ABI-compatible with this project.  This pass therefore never attempts to
	evaluate donor source.  It recognizes the stable class/lifecycle vocabulary
	and emits a data adapter for event names which already have a native handler.
	Everything else remains visible as a diagnostic instead of being silently
	dropped or copied as if it were an HScript file.
*/
typedef HxcCompatResult = {
	var path:String;
	var kind:String;
	var className:String;
	var baseClass:String;
	/** Literal character definition selected by an HXC wrapper constructor. */
	var characterConstructor:String;
	/** Resolved donor base source used for inherited character lifecycle methods. */
	var characterBasePath:String;
	/** Donor-only inherited hooks retained as explicit diagnostics. */
	var characterBaseGaps:Array<String>;
	/** Direct character hooks which remain donor-only when no safe adapter exists. */
	var characterHookGaps:Array<String>;
	var identifier:String;
	var callbacks:Array<String>;
	var canonicalCallbacks:Array<String>;
	var noteKinds:Array<String>;
	var fields:Array<String>;
	/** Payload fields read through `data.value.foo`/`data.get*('foo')`. */
	var payloadFields:Array<String>;
	/** Donor callback payload types observed in method signatures. */
	var payloadTypes:Array<String>;
	/** Generic payload operations which the native adapter can expose safely. */
	var payloadPatterns:Array<String>;
	/** Whether every callback using a donor payload has a safe native adapter. */
	var payloadSafe:Bool;
	/** Generic note-kind operations found in authored lifecycle callbacks. */
	var noteBehaviorPatterns:Array<String>;
	/** Class-level state which can be carried by generated callback closures. */
	var stateFields:Array<String>;
	/** Class-level literals with semantics safe to evaluate in HScript. */
	var stateInitializers:Array<HxcCompatStateInitializer>;
	/** Narrow constructor assignments/calls which are safe to replay after state setup. */
	var constructorStatements:Array<String>;
	/**
		Bounded constructor materialization for FPS Plus/BaseStage scripts.

		Those stages build their display list from `new()` rather than an HScript
		`start()`/`onCreate()` callback.  Keep the translated body separate from
		module constructor state: it is emitted inside the stage scope's one-shot
		`start()` hook, after PlayState has seeded the stage aliases and layer
		helpers.
	*/
	@:optional var stageConstructorBody:String;
	/** Authored event kind of a custom V-Slice SongEvent subclass (empty for
	    classes that route to a native event). */
	@:optional var customEventKind:String;
	/** Raw handleEvent body of that custom SongEvent subclass. */
	@:optional var customEventBody:String;
	/** True only when a module's constructor/state setup is fully represented. */
	var moduleInitializationSafe:Bool;
	/** True only when all routed module behavior has a native semantic path. */
	var moduleSafe:Bool;
	/** True when the authored module constructor/state literal disables dispatch. */
	var moduleDisabled:Bool;
	/** True when the complete HXC video-module contract is owned by the native host. */
	@:optional var videoModuleAdapter:Bool;
	/** True when a complete HXC StoryMenu visual/transition/helper module is native-owned. */
	@:optional var storyMenuSpec:Null<HxcStoryMenuSpecData>;
	/** Conservative reasons a module was retained as unsupported. */
	var moduleSafetyReasons:Array<String>;
	var callbackAdapters:Array<HxcCompatCallbackAdapter>;
	/** Safe non-lifecycle helpers referenced by translated lifecycle methods. */
	var helperAdapters:Array<HxcCompatCallbackAdapter>;
	var eventAdapters:Array<HxcCompatEventAdapter>;
	var generatedHscript:String;
	/** Data-only menu description; donor UI objects are never emitted. */
	@:optional var menuSpec:Null<HxcMenuSpecData>;
	/** Data-only pause description; donor pause object graphs are never emitted. */
	@:optional var pauseSpec:Null<HxcPauseSpecData>;
	/** Data-only perfect-hit text cue; donor FlxText objects are never emitted. */
	@:optional var noteTextSpec:Null<HxcNoteTextSpecData>;
	/** Data-only constructor timeline for a bounded ScriptedCutscene HXC. */
	@:optional var cutsceneTimeline:Null<HxcCutsceneTimelineData>;
	var nativeNoteDefinitions:Array<Dynamic>;
	var diagnostics:Array<HxcCompatDiagnostic>;
	/** Other top-level classes carried by the same file (for mixed HXC packs). */
	@:optional var companionClassNames:Array<String>;
	/** Literal CharacterInfoBase metadata, if this is an FPS Plus definition. */
	@:optional var characterDefinition:Dynamic;
	/** Literal FlxRuntimeShader metadata, if this is a shader helper file. */
	@:optional var shaderDefinition:Dynamic;
	/** Bounded camera-shader operation lowered to an engine-owned filter host. */
	@:optional var runtimeShaderDescriptor:Dynamic;
	/** Bounded shader/filter graphs keyed by their donor shader fields. */
	@:optional var runtimeShaderDescriptors:Array<Dynamic>;
}

/**
	Read-only compatibility metadata for the concrete V-Slice/HXC scripts used
	by the example donor library.  This is intentionally lexical rather than a
	general Haxe parser: import discovery must remain safe for arbitrary donor
	files, and the native runtime must never execute an untrusted foreign class
	just because it looked syntactically plausible.
*/
class HxcCompat {
	static var lifecycleNames:Array<String> = [
		'onCreate', 'onCreatePost', 'onSongStart', 'onUpdate', 'onUpdatePost',
		'onBeatHit', 'onStepHit', 'onSectionHit', 'onCountdownStart',
		'onCountdownTick', 'onCountdownStep', 'onCountdownEnd', 'onStartCountdown', 'onGoodNoteHit', 'onOpponentNoteHit',
		'onNoteHit', 'onNoteIncoming', 'onNoteMiss', 'onOpponentNoteMiss',
		'onNoteGhostMiss',
		'onSongEvent', 'onSongEnd', 'onEndSong', 'onSongRetry', 'onPause', 'onResume',
		'onPauseSubstateOpen', 'onPauseSubstateClose',
		'onStateOpenEnd', 'onSubStateOpenEnd', 'onSubStateCloseEnd', 'onPlayStateEnter',
		'onDifficultySwitch', 'onCapsuleSelected', 'onDestroy'
	];

	/** Return true for an HXC path without opening it. */
	public static function isHxcPath(path:String):Bool {
		return path != null && path.toLowerCase().endsWith('.hxc');
	}

	/** Analyze one HXC source file without modifying it or its donor tree. */
	public static function analyze(source:String, ?path:String):HxcCompatResult {
		var text = source == null ? '' : source;
		var clean = stripComments(text);
		var qualifiedStateAliases = collectQualifiedStateAliases(clean);
		// Only these two donor menu classes have a direct native destination. Keep
		// the allow-list explicit; arbitrary qualified names must still fail the
		// manifest-scoped state boundary below.
		clean = lowerQualifiedStateAliases(clean);
		var classFragments = collectClassFragments(clean);
		var classNames = [for (fragment in classFragments) fragment.name];
		var classBases = [for (fragment in classFragments) fragment.base];
		var selectedClassIndex = selectClassIndex(classNames, classBases,
			path == null ? '' : path.toLowerCase(), text);
		var className = selectedClassIndex >= 0 && selectedClassIndex < classNames.length
			? classNames[selectedClassIndex] : '';
		var baseClass = selectedClassIndex >= 0 && selectedClassIndex < classBases.length
			? classBases[selectedClassIndex] : '';
		// Some donor event files define a small lifecycle module before the actual
		// SongEvent (for example cameraFlashEvent/cameraFadeEvent). Select the
		// event class when one is present so the file is not falsely diagnosed as
		// an unsupported module and its event identifier is preserved.
		// selectClassIndex() gives Song/Character/Shader declarations the same
		// path-aware precedence.  This matters for files such as rabbit-hole.hxc,
		// where a Module options declaration intentionally shares one file with the
		// Song implementation, and for standalone FlxRuntimeShader wrappers.
		// Keep the mixed-file text for data-only descriptors.  Rabbit Hole stores
		// its option Module before the Song class, so the shader gate lives outside
		// the selected Song fragment even though the filter cameras belong to it.
		var mixedSource = clean;
		var selectedSource = selectedClassIndex >= 0 && selectedClassIndex < classFragments.length
			? classFragments[selectedClassIndex].source : clean;
		// Analyze the selected declaration as the executable owner. Companion
		// classes are merged below through their own safety pass; this prevents a
		// donor constructor in an unrelated top-level class from contaminating the
		// selected lifecycle adapter.
		clean = selectedSource;
		var identifier = classIdentifier(clean, className);
		var customEventKind:String = '';
		var customEventBody:String = '';
		if (identifier == '')
			identifier = firstString(clean, '\\bsuper\\s*\\(\\s*[\"\\\']([^\"\\\']+)[\"\\\']');
		if (identifier == '')
			identifier = firstString(clean, '\\bgetTitle\\s*\\(.*?return\\s*[\"\\\']([^\"\\\']+)[\"\\\']');

		var lowerBase = baseClass.toLowerCase();
		var lowerPath = path == null ? '' : path.toLowerCase();
		var kind = classify(lowerBase, lowerPath, false, clean);
		var characterDefinition:Dynamic = kind == 'character'
			? detectCharacterInfoDefinition(clean) : null;
		var shaderDefinition:Dynamic = kind == 'shader'
			? detectShaderDefinition(clean, className, baseClass) : null;
		var runtimeShaderDescriptors = detectRuntimeShaderDescriptors(mixedSource, kind);
		var runtimeShaderDescriptor:Dynamic = runtimeShaderDescriptors.length == 0
			? null : runtimeShaderDescriptors[0];
		// Complete menu graphs are lowered as one typed/data-only description. This
		// is deliberately structural: the class name and donor path do not select
		// the route, and no foreign UI object is ever carried into HScript.
		var menuSpec:HxcCompatMenuPlan = detectMenuSpec(clean, kind);
		var pauseSpec:HxcCompatPausePlan = detectPauseSpec(clean, kind);
		var noteTextSpec:HxcNoteTextSpecData = detectNoteTextSpec(clean, kind);
		var storyMenuSpec:HxcStoryMenuSpecData = kind == 'module'
			? HxcStoryMenuSpec.extract(clean) : null;
		var methods = collectMatches(clean, '\\bfunction\\s+([A-Za-z_][A-Za-z0-9_]*)', 1);
		var callbacks:Array<String> = [];
		var canonicalCallbacks:Array<String> = [];
		for (method in methods) {
			var lifecycle = lifecycleCallback(method);
			if (lifecycle == '' && kind == 'character')
				lifecycle = characterLifecycleCallback(method);
			if (lifecycle == '')
				continue;
			appendUnique(callbacks, method);
			appendUnique(canonicalCallbacks, lifecycle);
		}

		var noteKinds = collectMatches(clean,
			'(?:noteData|note)\\s*\\.\\s*kind\\s*(?:==|!=|===|!==)\\s*[\"\\\']([^\"\\\']+)[\"\\\']', 1);
		if (kind == 'note-kind')
			for (declared in collectMatches(clean,
				'\\bsuper\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 1))
				appendUnique(noteKinds, declared);
		var fields = collectMatches(clean,
			'(?:data|event)\\s*\\.get(?:String|Float|Int|Bool)\\s*\\(\\s*[\"\\\']([^\"\\\']+)', 1);
		for (field in collectMatches(clean,
			'(?:data|event)\\s*\\.value\\s*\\.([A-Za-z_][A-Za-z0-9_]*)', 1))
			appendUnique(fields, field);
		var payloadFields = fields.copy();
		for (field in collectMatches(clean,
			'(?:data|event)\\s*\\.value\\s*\\[\\s*["\\\']([^"\\\']+)["\\\']\\s*\\]', 1))
			appendUnique(payloadFields, field);
		var payloadTypes = collectPayloadTypes(clean);
		var payloadPatterns = collectPayloadPatterns(clean);
		var noteBehaviorPatterns = collectNoteBehaviorPatterns(clean);
		var stateDeclarations = collectStateDeclarations(clean);
		var stateFields:Array<String> = [];
		var stateInitializers:Array<HxcCompatStateInitializer> = [];
		var stateInitializerSafe = true;
		// A detected runtime-shader descriptor owns its shader/filter fields
		// outright: the generated handle aliases replace the donor constructor,
		// so those fields must not also carry the bounded initializer.
		var descriptorShaderFields:Map<String, Bool> = new Map<String, Bool>();
		var descriptorFilterFields:Map<String, Bool> = new Map<String, Bool>();
		for (descriptor in runtimeShaderDescriptors) {
			var shaderField:Dynamic = Reflect.field(descriptor, 'shaderField');
			var filterField:Dynamic = Reflect.field(descriptor, 'filterField');
			if (shaderField != null && Std.string(shaderField) != '')
				descriptorShaderFields.set(Std.string(shaderField), true);
			if (filterField != null && Std.string(filterField) != '')
				descriptorFilterFields.set(Std.string(filterField), true);
		}
		for (declaration in stateDeclarations) {
			if (declaration == null || declaration.name == null || declaration.name == '')
				continue;
			appendUnique(stateFields, declaration.name);
			if (declaration.initializer == null || StringTools.trim(declaration.initializer) == '')
				continue;
			var initializer = StringTools.trim(declaration.initializer);
			// Save/Preferences and current-chart aliases are translated before the
			// literal gate.  The generated adapter seeds those values explicitly; the
			// donor singleton itself is never evaluated.
			var translatedInitializer = translateBody(initializer);
			if (isSimpleLiteral(translatedInitializer))
				setStateInitializer(stateInitializers, declaration.name, translatedInitializer);
			else if (boundedPointInitializer(translatedInitializer) != null)
				setStateInitializer(stateInitializers, declaration.name,
					boundedPointInitializer(translatedInitializer));
			else if (isBoundedNoteStyleInitializer(translatedInitializer))
				setStateInitializer(stateInitializers, declaration.name, translatedInitializer);
			else if (descriptorShaderFields.exists(declaration.name)
				|| descriptorFilterFields.exists(declaration.name)) {
				// The generated opaque handle owns these fields; donor constructors
				// are not replayed and the dropped initializer is intentional.
			}
			else if (!descriptorShaderFields.exists(declaration.name)
				&& !descriptorFilterFields.exists(declaration.name)
				&& isBoundedShaderInitializer(translatedInitializer)) {
				// FlxRuntimeShader/ShaderFilter construction is the standard donor
				// shape for stage/module shader fields. Dropping these initializers
				// leaves null filters which the native render pass dereferences, so
				// seed the bounded constructor instead of leaving the field empty.
				setStateInitializer(stateInitializers, declaration.name, translatedInitializer);
			} else
				stateInitializerSafe = false;
		}
		var callbackAdapters:Array<HxcCompatCallbackAdapter> = [];
		var helperAdapters:Array<HxcCompatCallbackAdapter> = [];
		var characterBaseGaps:Array<String> = [];
		var characterHookGaps:Array<String> = [];
		var constructorStatements:Array<String> = [];
		var functions = collectFunctions(clean);
		// The V-Slice video Module owns a tightly defined hxvlc lifecycle. Recognize
		// the whole helper/state/callback contract structurally so its foreign typed
		// group is never copied into HScript. Partial copies stay on the normal
		// conservative diagnostic path.
		var videoModuleAdapter = kind == 'module'
			&& detectVideoModuleAdapter(clean, functions, stateDeclarations);
		var companionClassNames:Array<String> = [];
		var shaderOptionModuleNames:Array<String> = [];
		for (method in functions) {
			var callbackName = lifecycleCallback(method.name);
			if (callbackName == '' && kind == 'character')
				callbackName = characterLifecycleCallback(method.name);
			var callbackBody = kind == 'character'
				? translateCharacterBody(method.body, method.name, method.arguments)
				: (kind == 'module'
					? translateModuleBody(method.body, method.name, method.arguments, clean)
					: translateBody(method.body, method.name, method.arguments));
			// Song-level shader setup is a data-only operation.  Keep the donor
			// callback's safety result independent from the descriptor: a synthetic
			// native shader hook may cover the bounded filter operation, but it must
			// never make an otherwise unsafe donor callback executable.  This is
			// important for mixed callbacks such as Markov's onCountdownStart, where
			// only the StaticShader graph is portable and the surrounding object graph
			// is intentionally retained as a diagnostic.
			if (runtimeShaderDescriptors.length > 0)
				callbackBody = translateRuntimeShaderOperations(callbackBody,
					runtimeShaderDescriptors, stateInitializers, functions);
			var adapter:HxcCompatCallbackAdapter = {
				sourceName: method.name,
				canonicalName: callbackName == '' ? method.name : callbackName,
				arguments: method.arguments,
				argumentInfos: method.argumentInfos,
				body: callbackBody,
				safe: (kind == 'character'
				? isSafeCharacterBody(method.body, method.name, method.arguments)
				: kind == 'module'
					? isSafeTranslatedBody(callbackBody)
					: isSafeTranslatedBody(method.body))
			};
			if (callbackName != '')
				// Multiple donor spellings can share one native hook. Preserve all
				// safe bodies instead of silently dropping a later alias at emit time.
				if (kind == 'character' && !adapter.safe)
					appendUnique(characterHookGaps, method.name);
				else
					mergeCallbackAdapter(callbackAdapters, adapter);
			else if (!isHxcMetadataMethod(method.name)) {
				helperAdapters.push(adapter);
				if (kind == 'character' && !adapter.safe)
					appendUnique(characterHookGaps, method.name);
			}
		}
		if (kind == 'module') {
			var ownedFreeplayHelpers = freeplayCustomizationOwnedHelpers(clean);
			if (ownedFreeplayHelpers.length > 0)
				for (helper in helperAdapters.copy())
					if (helper != null && ownedFreeplayHelpers.indexOf(helper.sourceName) >= 0)
						helperAdapters.remove(helper);
		}
		if (videoModuleAdapter) {
			callbackAdapters = videoModuleCallbackAdapters();
			helperAdapters = videoModuleHelperAdapters();
		}
		// A few V-Slice files intentionally colocate an options Module and its
		// Song/State owner. Analyze each companion independently, then merge only
		// literal state and callbacks which passed that companion's own safety gate.
		// This keeps ModuleHandler name lookup working without instantiating a donor
		// class or allowing an unsafe constructor to leak into the selected scope.
		if (classFragments != null && classFragments.length > 1) {
			for (index in 0...classFragments.length) {
				if (index == selectedClassIndex)
					continue;
				var companionFragment = classFragments[index];
				if (companionFragment == null || companionFragment.name == null
					|| companionFragment.name == '')
					continue;
				// Another concrete stage/character declaration has its own registry
				// identity. Its lifecycle cannot run as the selected owner's module.
				var companionFamily = HxcScriptIdentity.familyForBase(companionFragment.base);
				if (companionFamily == 'stage' || companionFamily == 'character')
					continue;
				appendUnique(companionClassNames, companionFragment.name);
				var companionPath = (path == null ? '' : path) + '#companion:' + companionFragment.name;
				var companion = analyze(companionFragment.source, companionPath);
				if (companion == null)
					continue;
				if (runtimeShaderDescriptors.length == 1
					&& completeRuntimeShaderOptionCompanion(companion,
						companionFragment.source, companionFragment.name, runtimeShaderDescriptor))
					appendUnique(shaderOptionModuleNames, companionFragment.name);
				for (field in companion.stateFields)
					appendUnique(stateFields, field);
				for (initializer in companion.stateInitializers) {
					if (initializer == null || initializer.name == null || initializer.name == '')
						continue;
					var alreadyDefined = false;
					for (existing in stateInitializers)
						if (existing != null && existing.name == initializer.name) {
							alreadyDefined = true;
							break;
						}
					if (!alreadyDefined)
						stateInitializers.push({name: initializer.name, value: initializer.value});
				}
				for (statement in companion.constructorStatements)
					if (statement != null && StringTools.trim(statement) != '')
						constructorStatements.push(statement);
				for (callback in companion.callbackAdapters)
					if (callback != null && callback.safe) {
						mergeCallbackAdapter(callbackAdapters, callback);
						appendUnique(callbacks, callback.sourceName);
						appendUnique(canonicalCallbacks, callback.canonicalName);
					}
				for (helper in companion.helperAdapters)
					if (helper != null && helper.safe)
						helperAdapters.push(helper);
			}
		}
		// The source-level countdown callback is covered only when the colocated
		// module provides the same literal, defaulted bool gate and the entire
		// callback is exactly the bounded fragment/filter/camera shape below. The
		// native hook uses the shared per-root option store and scoped shader owner;
		// any additional donor statement keeps the original strict warning.
		var coveredRuntimeShaderCallbacks:Array<String> = [];
		if (runtimeShaderDescriptors.length == 1 && shaderOptionModuleNames.length > 0) {
			for (method in functions)
				if (method != null && method.name != null
					&& method.name.toLowerCase() == 'oncountdownstart'
					&& isCompleteRuntimeShaderCallback(method, runtimeShaderDescriptor,
						shaderOptionModuleNames)) {
					appendUnique(coveredRuntimeShaderCallbacks, method.name);
					for (callback in callbackAdapters)
						if (callback != null && callback.sourceName == method.name) {
							callback.safe = true;
						callback.body = 'HxcCompatRuntime.applyShaderDescriptor(PlayState.instance, '
							+ shaderDescriptorLiteral(runtimeShaderDescriptor)
							+ ', __hxcStore, hxcAssetRoot);';
					}
			}
		}
		// Stage shader callbacks can be lowered as a whole when the descriptor
		// owns every shader operation and the remaining translated callback plus
		// its local helper dependencies are safe. This keeps stage behavior such as
		// shadow refresh and character placement in the same lifecycle call.
		if (runtimeShaderDescriptors.length > 0) {
			for (method in functions) {
				if (method == null || method.name == null
					|| method.name.toLowerCase() != 'oncountdownstart')
					continue;
				for (callback in callbackAdapters) {
					if (callback == null || callback.sourceName != method.name)
						continue;
					var complete = false;
					if (kind == 'stage' && runtimeShaderDescriptors.length == 1) {
						var stageBodyComplete = isCompleteStageRuntimeShaderCallback(method, callback,
							runtimeShaderDescriptor, helperAdapters);
						if (stageBodyComplete) {
						// This legacy single-graph stage contract already verifies literal
						// shader writes, the registered camera, source-backed preference
						// proof, translated body syntax, and safe local helpers. Keep its
						// established body gate while adding the native call-arity bound.
						complete = runtimeCameraHelperAritiesSafe(callback.body);
						if (complete)
							Reflect.setField(runtimeShaderDescriptor, 'stageCountdownCovered', true);
						}
					}
					if (!complete && !(kind == 'stage' && runtimeShaderDescriptors.length == 1))
						complete = isCompleteShaderCallback(method, callback,
							runtimeShaderDescriptors, helperAdapters, stateFields, stateInitializers, functions, kind);
					if (complete) {
						callback.safe = true;
						appendUnique(coveredRuntimeShaderCallbacks, method.name);
					}
				}
			}
		}
		for (method in functions)
			if (method != null && method.name != null
				&& method.name.toLowerCase() == 'oncountdownstart'
				&& new EReg('new\\s+FlxRuntimeShader|new\\s+ShaderFilter|\\.filters\\b', 'm').match(method.body)
				&& coveredRuntimeShaderCallbacks.indexOf(method.name) < 0)
				for (callback in callbackAdapters)
					if (callback != null && callback.sourceName == method.name)
						callback.safe = false;

		var characterConstructor = kind == 'character' ? characterConstructorTarget(functions) : '';
		var characterBasePath = '';
		if (kind == 'character' && baseClass != '') {
			var inheritance = collectCharacterInheritance(path, baseClass);
			if (inheritance != null) {
				characterBasePath = inheritance.path;
				for (declaration in inheritance.stateDeclarations) {
					if (declaration == null || declaration.name == null || declaration.name == '')
						continue;
					appendUnique(stateFields, declaration.name);
					if (declaration.initializer == null || StringTools.trim(declaration.initializer) == '')
						continue;
					var inheritedInitializer = StringTools.trim(translateBody(declaration.initializer));
					if (isSimpleLiteral(inheritedInitializer))
						setStateInitializer(stateInitializers, declaration.name, inheritedInitializer);
					else
						stateInitializerSafe = false;
				}
				// The chain is stored ancestor -> direct base. Merge in reverse so
				// each inherited body is prepended in execution order and a wrapper
				// override remains the final body: ancestor -> base -> wrapper.
				var inheritedIndex = inheritance.functions.length - 1;
				while (inheritedIndex >= 0) {
					mergeCharacterAdapter(callbackAdapters, helperAdapters,
						inheritance.functions[inheritedIndex], characterBaseGaps);
					inheritedIndex--;
				}
			}
		}
		// Inherited declarations are collected in ancestor -> direct-base order,
		// but the wrapper's own fields were scanned before that closure. Reapply
		// the local declarations after the merge so HXC's normal shadowing rule is
		// preserved: ancestor -> base -> wrapper, with the wrapper winning a
		// same-name initializer (and a declaration without an initializer clearing
		// the inherited value rather than silently retaining it).
		if (kind == 'character' && stateDeclarations != null) {
			for (declaration in stateDeclarations) {
				if (declaration == null || declaration.name == null || declaration.name == '')
					continue;
				clearStateInitializer(stateInitializers, declaration.name);
				if (declaration.initializer == null || StringTools.trim(declaration.initializer) == '')
					continue;
				var wrapperInitializer = StringTools.trim(translateBody(declaration.initializer));
				if (isSimpleLiteral(wrapperInitializer))
					setStateInitializer(stateInitializers, declaration.name, wrapperInitializer);
				else
					stateInitializerSafe = false;
			}
		}
		if (kind == 'character') {
			for (adapter in callbackAdapters)
				if (adapter != null) {
					appendUnique(callbacks, adapter.sourceName);
					appendUnique(canonicalCallbacks, adapter.canonicalName);
				}
		}
		// A standalone FlxRuntimeShader HXC is a source/uniform declaration, not a
		// lifecycle script.  The event/module adapter already owns the vignette
		// effect, so emitting its donor `setIntensity`/`update` methods would only
		// create an unscoped shader object (and can shadow the native event route).
		// Keep the detached shaderDefinition for import diagnostics while making the
		// generated runtime intentionally data-only/no-op.
		if (kind == 'shader') {
			callbacks = [];
			canonicalCallbacks = [];
			callbackAdapters = [];
			helperAdapters = [];
			stateFields = [];
			stateInitializers = [];
			constructorStatements = [];
		}
		// BaseStage-derived FPS Plus scripts put their visual construction in
		// `new()`.  Generic module constructor replay intentionally rejects foreign
		// object graphs, but stage construction has a narrow engine-owned adapter
		// for the common BGSprite/FlxSprite/layer/starting-point surface.  Do not
		// copy any other constructor expressions into the generated interpreter.
		var constructorSafe = kind == 'stage' ? true : applyConstructorState(functions, stateFields, stateInitializers,
			constructorStatements);
		var moduleInitializationSafe = kind != 'module' || (stateInitializerSafe && constructorSafe);
		var moduleSafe = kind != 'module';
		if (videoModuleAdapter) {
			// The native host owns the video group, tweens, typed config, and all
			// callbacks. None of those donor fields or constructor operations enter
			// the generated interpreter.
			stateFields = [];
			stateInitializers = [];
			constructorStatements = [];
			constructorSafe = true;
			stateInitializerSafe = true;
			moduleInitializationSafe = true;
			moduleSafe = true;
		}
		// HXC modules are constructed once and then receive lifecycle dispatch from
		// the host.  A literal `active = false` is an authored control-flow rule,
		// not an unsafe donor callback: preserve the field initialization and keep
		// ordinary callbacks out of the generated adapter.  A complete native
		// replacement is handled by the narrow boundary check below.
		var authoredModuleDisabled = kind == 'module' && hasLiteralFalseActive(stateInitializers);
		// A donor module may be disabled in its original runtime even though its
		// complete lifecycle operation has been lowered to a single native host
		// boundary.  In that narrow case the compatibility adapter is the owner of
		// the operation, so retaining the donor's dispatch gate would discard the
		// bounded replacement.  Do not make this a filename/class allow-list: only
		// an all-boundary callback set qualifies.  Any ordinary callback, helper, or
		// unsafe body keeps the authored module disabled.
		var moduleDisabled = authoredModuleDisabled
			&& !hasCompleteNativeModuleBoundary(callbackAdapters, helperAdapters);
		var moduleSafetyReasons:Array<String> = [];
		if (moduleDisabled) {
			callbackAdapters = [];
			callbacks = [];
			canonicalCallbacks = [];
			moduleSafe = true;
		} else if (kind == 'module')
			// A module is executable only when both sides of the boundary are safe:
			// callback roots must be native and constructor/state initialization must
			// be deterministic. Keep the flags independent for diagnostics, but do
			// not claim a dynamic `active` expression is harmless merely because its
			// callbacks happen to use allow-listed APIs.
			moduleSafe = videoModuleAdapter || (moduleInitializationSafe && applyModuleSafety(functions,
				callbackAdapters, helperAdapters, stateFields, stateInitializers, moduleSafetyReasons, clean));
		if (storyMenuSpec != null) {
			// This complete StoryMenu module is executed by StoryMenuState's
			// owner-scoped host. Keep only the donor helper's destination field in
			// HScript; the menu sprite, callback, sounds, and timer never cross into
			// the interpreter.
			stateFields = [storyMenuSpec.characterHelperField];
			stateInitializers = [];
			constructorStatements = [];
			callbackAdapters = [];
			helperAdapters = [];
			constructorSafe = true;
			stateInitializerSafe = true;
			moduleInitializationSafe = true;
			moduleSafe = true;
			moduleDisabled = false;
			moduleSafetyReasons.resize(0);
		}
		// V-Slice Stage uses `buildStage()` for the same one-shot construction
		// phase that this engine exposes as `start()`.  Merge it centrally so a
		// donor stage can be translated without editing its chart or script.
		if (kind == 'stage') {
			for (helper in helperAdapters.copy()) {
				if (helper != null && helper.sourceName.toLowerCase() == 'buildstage') {
					helperAdapters.remove(helper);
					helper.canonicalName = 'start';
					mergeCallbackAdapter(callbackAdapters, helper, true);
				}
			}
		}
		if (menuSpec != null)
			applyMenuSpecAdapters(menuSpec, kind, functions, callbackAdapters, helperAdapters,
				stateFields, stateInitializers, constructorStatements);
		if (pauseSpec != null)
			applyPauseSpecAdapters(pauseSpec, kind, functions, callbackAdapters, helperAdapters,
				stateFields, stateInitializers, constructorStatements);
		if (noteTextSpec != null)
			applyNoteTextSpecAdapters(noteTextSpec, kind, callbackAdapters, helperAdapters,
				stateFields, stateInitializers, constructorStatements);
		if (menuSpec != null || pauseSpec != null || noteTextSpec != null) {
			// The menu host owns the complete graph.  Once the structural contract has
			// been recognized, donor constructor/callback safety no longer controls
			// dispatch: the generated adapter contains only the native boundary call.
			if (kind == 'module') {
				moduleInitializationSafe = true;
				moduleSafe = true;
				moduleDisabled = false;
				moduleSafetyReasons.resize(0);
			}
		}
		// Modules and note kinds use the same isolated HScript interpreter and
		// mutable payload bridge as ordinary HXC scripts. Modules have already
		// passed the stricter seeded-root/constructor gate above; unsupported
		// payload fields still remain visible through the payload diagnostic and
		// are never treated as a native class execution.
		// Constructor-only FPS Plus stages are common in the mounted donor set.
		// Their visual graph lives in `new()` and has no callback for the normal
		// lifecycle collector to emit.  The generated start hook below owns only
		// the bounded stage vocabulary; arbitrary constructor statements remain
		// diagnostics and are never copied into HScript.
		var stageConstructorBody = kind == 'stage' ? translateStageConstructor(functions) : '';
		var adapters:Array<HxcCompatEventAdapter> = [];
		var diagnostics:Array<HxcCompatDiagnostic> = [];
		if (kind == 'stage' && stageConstructorBody != null
			&& StringTools.trim(stageConstructorBody) != '')
			diagnostics.push(makeDiagnostic('info', 'hxc-stage-constructor-adapter',
				'FPS Plus/BaseStage constructor visuals and start-point offsets were lowered to the native stage/layer adapter.'));
		var cutsceneTimeline:Null<HxcCutsceneTimelineData> = null;
		if (kind == 'cutscene') {
			var timelineResult = HxcCutsceneTimeline.extract(clean, path, className, baseClass);
			cutsceneTimeline = timelineResult.timeline;
			for (finding in timelineResult.diagnostics)
				diagnostics.push(makeDiagnostic(finding.severity, finding.code, finding.message));
		}
		if (qualifiedStateAliases.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-state-alias',
				'Explicit qualified HXC menu aliases lowered: ' + qualifiedStateAliases.join(', ') + '.'));
		if (characterBaseGaps.length > 0)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-character-base',
				'Inherited HXC character hook(s) remain donor-only and were not emitted: '
				+ characterBaseGaps.join(', ') + '.'));
		if (characterHookGaps.length > 0)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-character-hook',
				'Direct HXC character hook(s) remain donor-only and were not emitted: '
				+ characterHookGaps.join(', ') + '.'));
		if (className == '' || baseClass == '') {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-class',
				'HXC class declaration was not recognized; no foreign code was executed.'));
		} else if (kind == 'song-event') {
			var canonical = EngineCompat.eventName(identifier);
			var inferred = inferEventAction(clean);
			if ((canonical == '' || canonical == identifier) && inferred != '')
				canonical = inferred;
			if (isNativeEvent(canonical)) {
				adapters.push({
					sourceName: identifier,
					canonicalName: canonical,
					fields: fields.copy(),
					safe: true
				});
				diagnostics.push(makeDiagnostic('info', 'hxc-event-adapter',
					'Recognized HXC SongEvent ' + className + ' (' + identifier + ') and routed it to native event ' + canonical + '.'));
				var bodyCoverage = EngineCompat.hxcEventBodyCoverage(clean, identifier, canonical);
				if (bodyCoverage != null && bodyCoverage.gaps != null && bodyCoverage.gaps.length > 0)
					diagnostics.push(makeDiagnostic('warning', 'hxc-event-body-gap',
						'HXC event body for ' + className + ' is only partially covered by native event '
						+ canonical + ': ' + bodyCoverage.gaps.join(', ') + '.'));
				else if (bodyCoverage == null || !bodyCoverage.covered)
					diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-event-body',
						'HXC event body for ' + className + ' is not covered by the centralized native route.'));
			} else {
				// A custom SongEvent subclass owns one authored kind and a
				// handleEvent body of ordinary engine calls; the emitter below
				// lowers that body into a self-filtering songEvent adapter.
				customEventKind = identifier;
				for (method in functions) {
					if (method != null && method.name != null
						&& method.name.toLowerCase() == 'handleevent') {
						customEventBody = method.body;
						break;
					}
				}
				diagnostics.push(makeDiagnostic('info', 'hxc-custom-event-adapter',
					'Custom HXC SongEvent ' + className + ' (' + identifier
					+ ') emits a self-filtering songEvent adapter for its authored kind.'));
			}
			// A recognized event is routed through the native implementation.  The
			// semantic audit above distinguishes a fully covered body from a body
			// whose donor-only module/options still need a future adapter; do not emit
			// the old unconditional warning for every native alias.
		} else if (kind == 'note-kind') {
			for (noteKind in noteKinds)
				diagnostics.push(makeDiagnostic('info', 'hxc-note-kind',
					'Preserved authored HXC note kind ' + noteKind + ' as native note identity; only generic callback operations are bridged.'));
			var bridgedNotePatterns = noteBehaviorPatterns.copy();
			bridgedNotePatterns.remove('donor-state');
			bridgedNotePatterns.remove('tally-state');
			bridgedNotePatterns.remove('tally-adapter');
			if (noteBehaviorPatterns.indexOf('tally-adapter') >= 0)
				bridgedNotePatterns.push('tally-adapter');
			if (bridgedNotePatterns.length > 0)
				diagnostics.push(makeDiagnostic('info', 'hxc-note-behavior-adapter',
					'Generic HXC note lifecycle/graphics behavior is bridged for: '
					+ bridgedNotePatterns.join(', ') + '.'));
			if (noteBehaviorPatterns.indexOf('donor-state') >= 0
				|| noteBehaviorPatterns.indexOf('tally-state') >= 0)
				diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-note-state',
					'HXC note kind retains donor-specific tally state outside the generic note bridge.'));
		} else if (kind == 'module') {
			diagnostics.push(makeDiagnostic('info', 'hxc-module-lifecycle',
				'Recognized HXC Module ' + className + '; lifecycle names can be routed through EngineCompat.'));
			if (videoModuleAdapter)
				diagnostics.push(makeDiagnostic('info', 'hxc-video-module-adapter',
					'Complete HXC video creation/configuration, HUD and camera behavior, controls, resync, pause/focus, cleanup, and playback-error behavior is owned by the native hxvlc host.'));
			if (storyMenuSpec != null)
				diagnostics.push(makeDiagnostic('info', 'hxc-story-menu-adapter',
					'Complete HXC StoryMenu selection visuals, sounds, delayed campaign handoff, and character helper are owned by the native story/menu boundary.'));
			var safeModuleCallbackNames:Array<String> = [];
			for (callback in callbackAdapters)
				if (callback != null && callback.safe)
					appendUnique(safeModuleCallbackNames, callback.canonicalName);
			if (safeModuleCallbackNames.length > 0)
				diagnostics.push(makeDiagnostic('info', 'hxc-module-adapter',
					'Executable HXC Module lifecycle callbacks routed through the native adapter: '
					+ safeModuleCallbackNames.join(', ') + '.'));
			if (menuSpec != null)
				diagnostics.push(makeDiagnostic('info', 'hxc-menu-overlay-adapter',
					'Complete HXC main-menu graph lowered to the native MainMenuState overlay host.'));
			if (pauseSpec != null)
				diagnostics.push(makeDiagnostic('info', 'hxc-pause-overlay-adapter',
					'Complete HXC pause graph lowered to the native PauseSubState overlay host.'));
			if (noteTextSpec != null) {
				diagnostics.push(makeDiagnostic('info', 'hxc-note-text-adapter',
					'Bounded note-hit text cues were lowered to a data-only native owner with per-song chance and line rules.'));
				if (noteTextSpec.missRules == null)
					diagnostics.push(makeDiagnostic('warning', 'hxc-note-text-scope',
						'Miss-specific text remains outside the bounded cue adapter.'));
			}
			if (pauseSpec == null && looksLikePauseGraph(clean))
				diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-module-body',
					'HXC pause helper/substate graph is partial; only the complete data-only shape can use the native PauseSubState host.'));
			if (!moduleSafe || !moduleInitializationSafe) {
				var reasonText = moduleSafetyReasons.length > 0
					? ' (' + moduleSafetyReasons.join(', ') + ')' : '';
				diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-module-body',
					'HXC Module has constructor, state, or callback behavior without a safe native adapter yet' + reasonText + '.'));
			}
		} else if (kind == 'shader') {
			diagnostics.push(makeDiagnostic('info', 'hxc-shader-adapter',
				'Recognized FlxRuntimeShader helper ' + className
				+ '; shader source and uniforms remain data-only and are owned by the native filter host.'));
		} else if (kind == 'song-script' || kind == 'stage' || kind == 'character'
			|| kind == 'cutscene' || kind == 'state' || kind == 'substate' || kind == 'ui') {
			diagnostics.push(makeDiagnostic('info', 'hxc-class-adapter',
				'Recognized HXC ' + kind + ' ' + className
				+ '; compatible lifecycle methods can be exposed through the native HScript state.'));
			if (menuSpec != null && kind == 'state')
				diagnostics.push(makeDiagnostic('info', 'hxc-menu-state-materialized',
					'Complete HXC main-menu state lowered to a manifest-scoped native MainMenuState materialization.'));
		} else {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-class',
				'HXC ' + (className == '' ? 'class' : className) + ' extends ' + baseClass
				+ ' and has no safe native data adapter yet.'));
		}
		if (runtimeShaderDescriptors.length > 0) {
			for (descriptor in runtimeShaderDescriptors) {
				var descriptorCameras:Dynamic = Reflect.field(descriptor, 'cameras');
				var descriptorName = Std.string(Reflect.field(descriptor, 'shaderName'));
				diagnostics.push(makeDiagnostic('info', 'hxc-runtime-shader-binding',
					'Bounded HXC shader ' + descriptorName + ' is owned by the native filter host for '
					+ (descriptorCameras == null ? 'no camera' : Std.string(descriptorCameras))
					+ '; asset resolution is restricted to the selected manifest root.'));
			}
			for (method in functions) {
				if (method == null || method.name == null)
					continue;
				var lifecycleName = lifecycleCallback(method.name);
				if ((lifecycleName == 'onCountdownStart' || method.name.toLowerCase() == 'oncountdownstart')
					&& new EReg('new\\s+FlxRuntimeShader|new\\s+ShaderFilter|\\.filters\\b', 'm').match(method.body)
					&& coveredRuntimeShaderCallbacks.indexOf(method.name) < 0)
					diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-shader-callback',
						'HXC callback ' + method.name
						+' retains donor operations around the bounded shader setup; only the synthetic native filter hook is emitted.'));
				for (descriptor in runtimeShaderDescriptors)
					if (Reflect.field(descriptor, 'pulseWarningHelper') != null
						&& Std.string(Reflect.field(descriptor, 'pulseWarningHelper')) == method.name
						&& Reflect.field(descriptor, 'pulseComplete') != true)
						diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-shader-pulse-body',
							'HXC shader pulse helper ' + method.name
							+' has operations beyond the recognized owned shader tween/timer/sound contract; those remaining donor operations are not executed.'));
			}
		}
		if (menuSpec != null) {
			var menuFallbacks:Array<String> = [];
			if (new EReg('\\bApplication\\s*\\.\\s*current\\s*\\.\\s*window\\s*\\.\\s*close\\s*\\(', 'm').match(clean))
				menuFallbacks.push('window-close');
			if (new EReg('\\b(?:SongRegistry|PlayState)\\s*\\.\\s*(?:instance\\s*\\.\\s*)?(?:fetchEntry|load|loadFromJson|startSong)\\s*\\(', 'm').match(clean))
				menuFallbacks.push('chart-launch');
			if (menuFallbacks.length > 0)
				diagnostics.push(makeDiagnostic('info', 'hxc-menu-bounded-fallback',
					'Bounded native menu host ignored donor-only action(s): '
					+ menuFallbacks.join(', ') + '.'));
		}

		// A disabled module never receives a lifecycle payload. Do not report its
		// donor callback signature as an executable payload gap after the callback
		// adapters have been intentionally filtered above.
		var payloadSafe = (menuSpec != null || pauseSpec != null
			|| (noteTextSpec != null && moduleSafe && moduleInitializationSafe))
			? true : (moduleDisabled
				? true : payloadAdapterSafe(clean, kind, callbackAdapters, functions, payloadTypes));
		if (!videoModuleAdapter && !moduleDisabled && (payloadTypes.length > 0 || payloadPatterns.length > 0)) {
			if (payloadSafe) {
				diagnostics.push(makeDiagnostic('info', 'hxc-payload-adapter',
					'Generic mutable HXC payload adapter covers: ' + payloadPatterns.join(', ') + '.'));
			} else {
				// Keep this warning whenever a callback body still needs a donor-only
				// class, even if another callback in the same file uses a supported
				// field. A payload adapter is data-only and never executes arbitrary
				// HXC classes on the native runtime.
				diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-payload',
					'HXC callback payload types are donor-specific; lifecycle aliases do not translate their methods automatically.'));
			}
		}

		var unknown = kind == 'shader' ? [] : EngineCompat.unknownScriptFunctions(clean);
		if (kind == 'stage' && stageConstructorBody != null
			&& StringTools.trim(stageConstructorBody) != '') {
			// These donor names are consumed by the bounded constructor pass. Keep
			// unrelated helper calls visible to the normal diagnostics.
			for (name in ['BGSprite', 'addToBackground', 'addToBackgroundLayer',
				'addToForeground', 'addToForegroundLayer', 'addToCharacterLayer'])
				unknown.remove(name);
		}
		if (runtimeShaderDescriptors.length > 0)
			for (shaderApi in ['setFloat', 'setInt', 'setBool'])
				unknown.remove(shaderApi);
		if (characterDefinition != null)
			for (metadataHelper in ['setSparrow', 'offset', 'loop', 'addByPrefix',
				'addByIndices', 'addExtraData'])
				unknown.remove(metadataHelper);
		if (unknown.length > 0 && !videoModuleAdapter)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-api',
				'Unmapped engine API(s) remain in HXC source: ' + unknown.join(', ') + '.'));
		if (!videoModuleAdapter)
			for (message in unsupportedHxcApiMembers(clean))
				diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-api', message));
		var literalFactories = collectMatches(clean,
			'\\bScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init\\s*\\(\\s*["\\\']([A-Za-z_][A-Za-z0-9_]*)["\\\']\\s*\\)', 1);
		var dynamicFactoryNames = collectMatches(clean,
			'\\bScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\)', 1);
		var dynamicFactory = new EReg('\\bScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init\\s*\\(\\s*new\\s+', 'm').match(clean);
		if (literalFactories.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-state-factory',
				'Literal HXC state factory target(s) routed through the selected manifest root: '
				+ literalFactories.join(', ') + '.'));
		if (dynamicFactoryNames.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-state-factory-dynamic',
				'Dynamic HXC state factory expression(s) are resolved as names inside the selected manifest root: '
				+ dynamicFactoryNames.join(', ') + '.'));
		if (dynamicFactory)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-state-factory',
			'ScriptedMusicBeat state construction cannot use a donor class expression; only name expressions in the selected manifest root are supported.'));
		var factoryVariables = collectMatches(clean,
			'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*ScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init\\s*\\(\\s*(?:["\\\'][A-Za-z_][A-Za-z0-9_]*["\\\']|[A-Za-z_][A-Za-z0-9_.]*)\\s*\\)', 1);
		var closureVariables = collectMatches(clean,
			'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*\\(\\s*\\)\\s*->\\s*new\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(', 1);
		// A variable may be reused for a safe native closure and a donor-qualified
		// closure in the same callback. Do not let the safe assignment mask the
		// qualified one; only the two aliases lowered above may pass this gate.
		var qualifiedClosureVariables = collectMatches(clean,
			'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_.]*)?\\s*=\\s*\\(\\s*\\)\\s*->\\s*new\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\.[A-Za-z_][A-Za-z0-9_.]*\\s*\\(', 1);
		var qualifiedClosure = new EReg('new[ \\t\\r\\n]+[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*[ \\t\\r\\n]*\\(', 'm').match(clean);
		var switchVariables = collectMatches(clean,
			'\\bFlxG\\s*\\.\\s*switchState\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 1);
		var switched = new EReg('\\bFlxG\\s*\\.\\s*switchState\\s*\\(', 'm').match(clean);
		var directSafeSwitch = new EReg('\\bFlxG\\s*\\.\\s*switchState\\s*\\(\\s*(?:ScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init\\s*\\(\\s*(?:["\\\'][A-Za-z_][A-Za-z0-9_]*["\\\']|[A-Za-z_][A-Za-z0-9_.]*)\\s*\\)|new\\s+(?:MainMenuState|StoryMenuState|FreeplayState|TitleState|CreditsState|SaveDataState)\\b|\\(\\s*\\)\\s*->\\s*new\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\()', 'm').match(clean);
		var unsafeSwitch = switched && !directSafeSwitch;
		if (unsafeSwitch && switchVariables.length > 0) {
			unsafeSwitch = false;
			for (target in switchVariables)
				if (factoryVariables.indexOf(target) < 0 && closureVariables.indexOf(target) < 0
					|| qualifiedClosureVariables.indexOf(target) >= 0)
					unsafeSwitch = true;
		}
		if (menuSpec == null && unsafeSwitch)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-state-switch',
				'An HXC FlxG.switchState target is not a literal native alias or root-scoped factory result; arbitrary closures and donor-only classes are rejected at runtime.'));
		else if (menuSpec == null && qualifiedClosure && switched)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-state-switch',
				'Qualified donor state closures are not resolved by name; only native aliases or an unqualified state found in the selected manifest root are allowed.'));
		if (new EReg('\\bFlxG\\s*\\.\\s*state\\s*\\.(?:subState\\s*\\.\\s*)?openSubState\\s*\\(', 'm').match(clean)
			|| new EReg('(^|[;{}])\\s*openSubState\\s*\\(', 'm').match(clean))
			diagnostics.push(makeDiagnostic('info', 'hxc-substate-route',
				'HXC openSubState calls are routed through the selected manifest root; non-HXC substate objects remain rejected.'));
		var adaptedApis = EngineCompat.hxcApiNames(clean);
		if (adaptedApis.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-api-adapter',
				'Central HXC character/stage aliases are available for: '
				+ adaptedApis.join(', ') + '.'));
		// The native host exposes a deliberately coarse rank fallback so imported
		// score UI can still render, but the mounted donor tree does not include
		// V-Slice's threshold implementation. Keep the semantic gap visible even
		// when the surrounding callback has otherwise safe roots.
		if (new EReg('\\bScoring\\s*\\.\\s*calculateRank\\s*\\(', 'm').match(clean))
			diagnostics.push(makeDiagnostic('info', 'hxc-rank-adapter',
			'Scoring.calculateRank uses the native V-Slice threshold adapter; empty charts return no rank and donor-specific weighting remains outside this data-only route.'));
		if (lowerHxcApiAliases(clean) != clean)
			diagnostics.push(makeDiagnostic('info', 'hxc-api-alias',
				'Native HXC property aliases were lowered before HScript generation.'));

		var sourceConstructs = unsupportedConstructs(clean);
		var translatedConstructs = unsupportedConstructs(translateBody(clean));
		var constructs = translatedConstructs;
		if (sourceConstructs.length > translatedConstructs.length)
			diagnostics.push(makeDiagnostic('info', 'hxc-syntax-adapter',
				'Deterministic HXC syntax lowering was applied before HScript generation.'));
		if (constructs.length > 0 && !videoModuleAdapter)
			diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-syntax',
				'HXC syntax needs a runtime adapter before this source can execute unchanged: '
				+ constructs.join(', ') + '.'));
		var safeCallbackNames:Array<String> = [];
		for (callback in callbackAdapters)
			if (callback != null && callback.safe)
				appendUnique(safeCallbackNames, callback.canonicalName);
		if (safeCallbackNames.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-lifecycle-adapter',
				'Lifecycle callbacks available through the centralized adapter: '
				+ safeCallbackNames.join(', ') + '.'));
		var safeHelpers:Array<String> = [];
		for (helper in helperAdapters)
			if (helper != null && helper.safe)
				appendUnique(safeHelpers, helper.sourceName);
		if (safeHelpers.length > 0)
			diagnostics.push(makeDiagnostic('info', 'hxc-helper-adapter',
				'Safe helper methods referenced by translated HXC callbacks: '
				+ safeHelpers.join(', ') + '.'));
		if (!videoModuleAdapter)
			for (callback in callbackAdapters)
				if (callback != null && !callback.safe)
					diagnostics.push(makeDiagnostic('warning', 'unsupported-hxc-callback-body',
						'HXC callback ' + callback.sourceName + ' -> ' + callback.canonicalName
						+ ' was discovered, but its body still contains donor-only syntax or state access.'));

		var result:HxcCompatResult = {
			path: path == null ? '' : path,
			kind: kind,
			className: className,
			baseClass: baseClass,
			characterConstructor: characterConstructor,
			characterBasePath: characterBasePath,
			characterBaseGaps: characterBaseGaps,
			characterHookGaps: characterHookGaps,
			identifier: identifier,
			callbacks: callbacks,
			canonicalCallbacks: canonicalCallbacks,
			noteKinds: noteKinds,
			fields: fields,
			payloadFields: payloadFields,
			payloadTypes: payloadTypes,
		payloadPatterns: payloadPatterns,
			payloadSafe: payloadSafe,
			noteBehaviorPatterns: noteBehaviorPatterns,
			stateFields: stateFields,
			stateInitializers: stateInitializers,
			constructorStatements: constructorStatements,
			stageConstructorBody: stageConstructorBody,
			customEventKind: customEventKind,
			customEventBody: customEventBody,
			moduleInitializationSafe: moduleInitializationSafe,
			moduleSafe: kind == 'module' ? moduleSafe && moduleInitializationSafe : true,
			moduleDisabled: moduleDisabled,
			videoModuleAdapter: videoModuleAdapter,
			storyMenuSpec: storyMenuSpec,
			moduleSafetyReasons: moduleSafetyReasons,
			callbackAdapters: callbackAdapters,
				helperAdapters: helperAdapters,
			eventAdapters: adapters,
		generatedHscript: '',
		menuSpec: menuSpec,
		pauseSpec: pauseSpec,
		noteTextSpec: noteTextSpec,
				cutsceneTimeline: cutsceneTimeline,
			nativeNoteDefinitions: [],
			diagnostics: diagnostics,
			companionClassNames: companionClassNames,
			characterDefinition: characterDefinition,
			shaderDefinition: shaderDefinition,
			runtimeShaderDescriptor: runtimeShaderDescriptor,
			runtimeShaderDescriptors: runtimeShaderDescriptors
		};
		result.generatedHscript = generateHscript(result);
		result.nativeNoteDefinitions = nativeNoteDefinitions(result);
		return result;
	}

	/** Collect donor payload type names from callback signatures/import aliases. */
	static function collectPayloadTypes(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		for (name in collectMatches(source,
			'\\b([A-Za-z_][A-Za-z0-9_.]*ScriptEvent)\\b', 1))
			appendUnique(result, name);
		return result;
	}

	/** Return the small payload vocabulary which the runtime adapter supplies. */
	static function collectPayloadPatterns(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		if (new EReg('\\.(?:getFloat|getBool|getInt|getString)\\s*\\(', 'm').match(source))
			result.push('typed-getters');
		if (new EReg('\\b(?:event|data|scriptEvent|callback)\\s*\\.\\s*note\\b', 'm').match(source))
			result.push('note');
		if (new EReg('\\.eventData\\s*(?:\\.value)?\\b', 'm').match(source))
			result.push('eventData/value');
		if (new EReg('\\.(?:cancel|cancelEvent)\\s*\\(', 'm').match(source))
			result.push('cancel');
		if (new EReg('\\.(?:eventCanceled|canceled|cancelled)\\b', 'm').match(source))
			result.push('cancellation-state');
		if (new EReg('\\.(?:step|beat|elapsed)\\b', 'm').match(source))
			result.push('time');
		return result;
	}

	/**
		Inventory the note operations that have an engine-neutral meaning.  This
		is deliberately lexical: an authored callback may still mention donor
		state, but generic kind routing, cancellation, health writes, and the
		standard Flixel note graphics surface can be bridged without naming a
		chart or song.
	*/
	static function collectNoteBehaviorPatterns(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		if (noteKindAvoidsHits(source))
			result.push('avoid-auto-hit');
		if (new EReg('(?:noteData|note)\\s*\\.\\s*kind', 'm').match(source))
			result.push('kind-routing');
		if (new EReg('\\.(?:cancel|cancelEvent)\\s*\\(', 'm').match(source))
			result.push('cancellation');
		if (new EReg('PlayState\\s*\\.\\s*instance\\s*\\.\\s*health\\s*(?:=|\\+=|-=)', 'm').match(source))
			result.push('health');
		if (new EReg('\\.frames\\s*=|\\.animation\\s*\\.|\\.holdNoteSprite\\s*\\.|\\.(?:loadGraphic|updateHitbox)\\s*\\(', 'm').match(source))
			result.push('graphics');
		if (new EReg('\\.(?:kill|destroy)\\s*\\(', 'm').match(source))
			result.push('lifecycle');
		if (new EReg('\\.lowPriority\\b', 'm').match(source))
			result.push('priority');
		var hasNamespacedStore = new EReg('[A-Za-z_][A-Za-z0-9_]*Preferences\\s*\\.\\s*get[A-Za-z_][A-Za-z0-9_]*Save|Save\\s*\\.\\s*instance', 'm').match(source);
		if (hasNamespacedStore || new EReg('\\bsave\\s*\\.', 'm').match(source))
			if (hasNamespacedStore)
				result.push('state-store');
			else
				result.push('donor-state');
		var tallyFields = collectMatches(source,
			'\\bHighscore\\s*\\.\\s*tallies\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)', 1);
		if (tallyFields.length > 0) {
			var tallySafe = true;
			for (field in tallyFields)
				if (['totalNotes', 'missed', 'sick', 'good', 'bad', 'shit', 'combo', 'maxCombo', 'totalNotesHit'].indexOf(field) < 0)
					tallySafe = false;
			if (tallySafe)
				result.push('tally-adapter');
			else
				result.push('tally-state');
		} else if (new EReg('\\bHighscore\\s*\\.\\s*tallies\\b', 'm').match(source))
			// A bare tally root (or a computed member) cannot be proven to stay on
			// the narrow explicit per-song counter view. Keep it diagnosed instead of
			// silently exposing an arbitrary donor state object.
			result.push('tally-state');
		return result;
	}

	/** A declared note kind which punishes hits and cancels misses is optional
	 * hazardous input. Do not execute callbacks speculatively or infer this from
	 * a note/class name, lowPriority, artwork, or ordinary miss damage. */
	public static function noteKindAvoidsHits(source:String):Bool {
		// Most imported scripts have neither callback. Avoid parsing all their
		// function bodies again just to reject an inapplicable note policy.
		if (source == null || source.indexOf('onNoteHit') < 0 || source.indexOf('onNoteMiss') < 0)
			return false;
		var hit:HxcCompatFunction = null;
		var miss:HxcCompatFunction = null;
		for (method in collectFunctions(stripComments(source))) {
			if (method.name == 'onNoteHit') hit = method;
			if (method.name == 'onNoteMiss') miss = method;
		}
		if (hit == null || miss == null || miss.arguments.length == 0)
			return false;
		// String payloads cannot advertise executable health/cancellation writes.
		var strings = ~/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/g;
		var hitCode = strings.replace(hit.body, '""');
		var missCode = strings.replace(miss.body, '""');
		if (!new EReg('\\b' + miss.arguments[0] + '\\s*\\.\\s*(?:cancel|cancelEvent)\\s*\\(\\s*\\)', '').match(missCode))
			return false;
		var number = '(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)';
		var health = '\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*health\\s*';
		// Literal negative health/delta, zero-health death, or positive drain.
		if (new EReg(health + '(?:=|\\+=)\\s*-\\s*' + number + '\\s*;', '').match(hitCode)
			|| new EReg(health + '=\\s*0(?:\\.0+)?\\s*;', '').match(hitCode))
			return true;
		var drain = new EReg(health + '-=\\s*(' + number + ')\\s*;', '');
		if (drain.match(hitCode) && Std.parseFloat(drain.matched(1)) > 0)
			return true;
		return hit.arguments.length > 0 && new EReg('\\b' + hit.arguments[0]
			+ '\\s*\\.\\s*healthChange\\s*=\\s*-\\s*' + number + '\\s*;', '').match(hitCode);
	}

	/**
		Decide whether the payload reads in this source can use the native data
		adapter. Payloads are shared by every routed HXC scope, including modules
		and native SongEvent aliases. Ordinary helper arguments are not payloads
		merely because they use dotted property access; only a lifecycle callback
		with a typed event or an argument read is audited here.
	*/
	static function payloadAdapterSafe(source:String, kind:String,
		callbacks:Array<HxcCompatCallbackAdapter>, functions:Array<HxcCompatFunction>,
		payloadTypes:Array<String>):Bool {
		if (source == null)
			return false;
		var sawPayloadMethod = false;
		var unsafe = false;
		for (method in functions) {
			if (method == null)
				continue;
			var callbackName = lifecycleCallback(method.name);
			var typedPayload = methodHasPayloadArgument(source, method.name);
			var bodyPayload = payloadBodyUses(method.body, method.arguments);
			// A regular helper's `obj.field` parameter is local data, not the
			// lifecycle payload. Require a routed callback before auditing an
			// untyped dotted argument.
			if (!bodyPayload || (!typedPayload && callbackName == ''))
				continue;
			sawPayloadMethod = true;
			var adapter:HxcCompatCallbackAdapter = null;
			if (callbacks != null)
				for (candidate in callbacks)
					if (candidate != null && candidate.sourceName == method.name) {
						adapter = candidate;
						break;
					}
			// Callback execution safety is diagnosed independently below.  A body
			// can contain an unrelated donor root (and therefore stay out of the
			// generated adapter) while its event payload fields are still completely
			// covered.  Keep this verdict about payload ABI only; unknown payload
			// fields/methods continue to fail the strict body audit.
			if (callbackName == '' || adapter == null
				|| !payloadBodySupported(method.body, method.arguments, kind, callbackName)) {
				unsafe = true;
			}
		}
		// An annotated payload which is only forwarded to `super` (or otherwise
		// never dereferenced) needs no adapter at all.  Do not turn an unused type
		// annotation into a false-positive donor gap; once a callback actually
		// consumes its argument, the strict field/method audit above still applies.
		if (!sawPayloadMethod)
			return true;
		return !unsafe;
	}

	static function methodHasPayloadArgument(source:String, name:String):Bool {
		if (source == null || name == null || name == '')
			return false;
		var expression = new EReg('\\bfunction\\s+' + name + '\\s*\\(([^)]*)\\)', 'm');
		if (!expression.match(source))
			return false;
		var arguments = expression.matched(1);
		return new EReg('(?:ScriptEvent|SongEventScriptEvent|CountdownScriptEvent)', 'm').match(arguments);
	}

	static function payloadBodyUses(source:String, arguments:Array<String>):Bool {
		if (source == null || source == '')
			return false;
		if (arguments != null)
			for (argument in arguments)
				if (argument != null && argument != ''
					&& new EReg('\\b' + argument + '\\s*\\.', 'm').match(source))
					return true;
		return false;
	}

	/** Validate only direct payload reads/methods with deterministic semantics. */
	static function payloadBodySupported(source:String, arguments:Array<String>, kind:String,
		callbackName:String):Bool {
		if (source == null || source == '')
			return true;
		var root = arguments == null || arguments.length == 0 ? '' : arguments[0];
		if (root == '') {
			return false;
		}
		// These direct fields are deliberately copied by EngineCompat's lifecycle
		// and freeplay payload constructors. They are shallow views; nested donor
		// state below them is still rejected by the chain allow-list.
		for (field in ['events', 'targetState', 'capsule', 'freeplayState', 'difficulty',
			'variation', 'character'])
			if (new EReg('\\b' + root + '\\s*\\.\\s*' + field + '\\b', 'm').match(source)) {
				var fieldAllowed = switch (field) {
					case 'events': callbackName == 'songLoaded';
					case 'targetState': callbackName == 'stateChangeBegin'
						|| callbackName == 'stateChangeEnd' || callbackName == 'subStateOpenEnd'
						|| callbackName == 'subStateCloseBegin' || callbackName == 'subStateCloseEnd'
						|| callbackName == 'gameOver' || callbackName == 'difficultySwitch'
						|| callbackName == 'capsuleSelected';
					case 'capsule' | 'freeplayState' | 'difficulty' | 'variation':
						callbackName == 'difficultySwitch' || callbackName == 'capsuleSelected';
					case 'character': callbackName == 'characterAdded';
					default: false;
				};
					if (!fieldAllowed) {
						return false;
					}
			}
		// Unknown direct event objects are not manufactured by the bridge.
		for (field in ['stage', 'event', 'SongEvent'])
			if (new EReg('\\b' + root + '\\s*\\.\\s*' + field + '\\b', 'm').match(source)) {
				return false;
			}
		var calls = collectMatches(source,
			'\\b' + root + '((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)\\s*\\(', 1);
		for (chain in calls) {
			var normalized = StringTools.replace(chain, ' ', '');
			if (normalized == '.getFloat' || normalized == '.getBool' || normalized == '.getInt'
				|| normalized == '.getString' || normalized == '.cancel' || normalized == '.cancelEvent'
				|| normalized == '.note.noteData.getDirection'
				|| normalized == '.note.noteData.getMustHitNote'
				|| normalized == '.note.noteData.getStrumlineIndex'
				|| normalized == '.note.get_isHoldNote'
				|| normalized == '.note.updateHitbox' || normalized == '.note.kill'
				|| normalized == '.note.destroy'
				|| normalized == '.note.holdNoteSprite.loadGraphic'
				|| normalized == '.note.holdNoteSprite.alpha'
				|| normalized == '.note.holdNoteSprite.updateHitbox'
				|| normalized == '.note.holdNoteSprite.updateColorTransform'
				|| normalized == '.note.holdNoteSprite.updateClipping'
				|| normalized == '.note.animation.addByPrefix'
				|| normalized == '.note.animation.play'
				|| normalized == '.targetState.members.contains'
				|| normalized == '.targetState.members.add'
				|| normalized == '.targetState.members.remove'
				|| normalized == '.targetState.add'
				|| normalized == '.targetState.remove'
				|| normalized == '.targetState.refresh')
				continue;
			return false;
		}
		var chains = collectMatches(source,
			'\\b' + root + '((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 1);
		for (chain in chains) {
			var normalized = StringTools.replace(chain, ' ', '');
			if (payloadFieldChainSupported(normalized))
				continue;
			return false;
		}
		// The note proxy is mutable for the small surface copied by
		// EngineCompat.hxcApplyNoteCallbackPayload.  Keep unknown/donor-only note
		// writes diagnosed, but do not reject generic lowPriority/graphics/layout
		// changes which the native pump deliberately applies back to Note.
		var noteWrite = new EReg('\\b' + root
			+ '\\s*\\.\\s*note\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*(?:=(?!=)|\\+=|\\-=|\\+\\+|--)', 'm');
		if (noteWrite.match(source)) {
			var writableNoteFields = ['lowPriority', 'active', 'visible', 'alpha', 'x', 'y', 'angle', 'frames', 'offset', 'flipY'];
			if (writableNoteFields.indexOf(noteWrite.matched(1)) < 0) {
				return false;
			}
		}
		return true;
	}

	static function payloadFieldChainSupported(chain:String):Bool {
		if (chain == null || chain == '')
			return true;
		for (field in ['.eventCanceled', '.canceled', '.cancelled', '.eventKind', '.cancel', '.cancelEvent', '.step', '.beat',
			'.elapsed', '.healthChange', '.judgement', '.dir', '.direction', '.playerOne',
			'.isPlayer', '.goodHit', '.countdownStep', '.songPosition', '.songLength', '.value',
			'.events', '.events.length', '.targetState', '.capsule', '.freeplayState', '.difficulty', '.variation', '.character',
			// EngineCompat.hxcFreeplayPayload exposes a shallow capsule view.  These
			// nested fields are copied data, not the donor FreeplayState graph; keep
			// the allow-list explicit so arbitrary capsule methods still diagnose.
			'.capsule.alive', '.capsule.freeplayData', '.capsule.freeplayData.levelId',
			'.capsule.freeplayData.songCharacter', '.capsule.freeplayData.data',
			'.capsule.freeplayData.data.id', '.capsule.pixelIcon',
			'.capsule.pixelIcon.character', '.capsule.pixelIcon.offset',
			'.capsule.pixelIcon.offset.x'])
			if (chain == field)
				return true;
		if (chain == '.eventData' || chain == '.eventData.eventKind' || chain == '.eventData.value'
			|| StringTools.startsWith(chain, '.eventData.value.')
			|| StringTools.startsWith(chain, '.eventData.'))
			return true;
		// State-change payloads carry the real native FlxState.  Its members
		// group and add/remove surface are engine-owned, unlike arbitrary donor
		// objects nested below an event.  The direct `targetState` callback gate
		// above still limits this allowance to state lifecycle hooks.
		if (chain == '.targetState.members' || chain == '.targetState.members.contains'
			|| chain == '.targetState.members.add' || chain == '.targetState.members.remove'
			|| chain == '.targetState.add' || chain == '.targetState.remove'
			|| chain == '.targetState.refresh')
			return true;
		if (chain == '.note' || chain == '.note.kind' || chain == '.note.strumTime'
			|| chain == '.note.isSustainNote' || chain == '.note.mustPress' || chain == '.note.nativeNote'
			|| chain == '.note.lowPriority' || chain == '.note.active' || chain == '.note.visible'
			|| chain == '.note.alpha' || chain == '.note.x' || chain == '.note.y' || chain == '.note.angle'
			|| chain == '.note.offset' || chain == '.note.offset.x' || chain == '.note.offset.y'
			|| chain == '.note.flipY'
			|| chain == '.note.frames' || chain == '.note.animation' || chain == '.note.animation.curAnim'
			|| chain == '.note.holdNoteSprite'
			|| chain == '.note.hsvShader' || chain == '.note.hsvShader.saturation'
			|| chain == '.note.holdNoteSprite.alpha'
			|| chain == '.note.noteData' || chain == '.note.noteData.data' || chain == '.note.noteData.kind'
			|| chain == '.note.noteData.getDirection' || chain == '.note.noteData.getMustHitNote'
			|| chain == '.note.noteData.getStrumlineIndex' || chain == '.note.get_isHoldNote'
			|| chain == '.note.updateHitbox' || chain == '.note.kill' || chain == '.note.destroy'
			|| chain == '.note.holdNoteSprite.loadGraphic'
			|| chain == '.note.holdNoteSprite.updateHitbox'
			|| chain == '.note.holdNoteSprite.updateColorTransform'
			|| chain == '.note.holdNoteSprite.updateClipping'
			|| chain == '.note.animation.addByPrefix' || chain == '.note.animation.play')
			return true;
		return false;
	}

	/** Alias used by import code that calls the pass a translator. */
	public static function translate(source:String, ?path:String):HxcCompatResult {
		return analyze(source, path);
	}

	/**
		Create native note definitions for a ScriptedNoteKind-like module. The
		definition remains data-only, while source callbacks identify the HXC
		interpreter that PlayState routes through its generic note payload bridge.
	*/
	public static function nativeNoteDefinitions(result:HxcCompatResult):Array<Dynamic> {
		var output:Array<Dynamic> = [];
		if (result == null || result.kind != 'note-kind')
			return output;
		var index = 0;
		for (kind in result.noteKinds) {
			var safe = safeIdentifier(kind);
			output.push({
				noteName: 'HXC ' + kind,
				avoidAutoHit: result.noteBehaviorPatterns.indexOf('avoid-auto-hit') >= 0 ? true : null,
				animNames: ['purple', 'blue', 'green', 'red'],
				animInt: [4, 5, 6, 7],
				classes: ['hxc', 'hxc-kind:' + safe],
				id: 'hxc:' + safe + ':' + index,
				sourceKind: kind,
				sourceEngine: 'HXC',
				sourceClass: result.className,
				sourcePath: result.path,
				sourceCallbacks: result.canonicalCallbacks
			});
			index++;
		}
		return output;
	}

	static function classify(base:String, path:String, hasNoteKind:Bool, source:String):String {
		// Concrete source types own their lifecycle even when a package stores
		// a character companion beside stage or song scripts. Directory names
		// remain the fallback for classless legacy files.
		if (isCharacterBase(base))
			return 'character';
		if (base == 'scriptednotekind' || base == 'notekind' || hasNoteKind
			|| path.indexOf('/notes/') >= 0 || path.indexOf('\\\\notes\\\\') >= 0)
			return 'note-kind';
		if (base == 'scriptedsongevent' || base == 'scriptedsong_event'
			|| base == 'scriptevent' || base == 'songevent'
			|| base == 'scriptedsong-event')
			return 'song-event';
		if (base.endsWith('songevent'))
			return 'song-event';
		if (base == 'module' || base == 'scriptedmodule' || base.endsWith('.module'))
			return 'module';
		if (isShaderBase(base))
			return 'shader';
		if (base == 'song' || base.endsWith('.song') || path.indexOf('/songs/') >= 0
			|| path.indexOf('\\\\songs\\\\') >= 0 || path.indexOf('/song-scripts/') >= 0)
			return 'song-script';
		if (base == 'stage' || base == 'basestage' || base.endsWith('.stage')
			|| path.indexOf('/stages/') >= 0 || path.indexOf('\\\\stages\\\\') >= 0)
			return 'stage';
		if (base.indexOf('character') >= 0 || base.indexOf('sparrowcharacter') >= 0
			|| path.indexOf('/characters/') >= 0 || path.indexOf('\\\\characters\\\\') >= 0)
			return 'character';
		if (base.indexOf('cutscene') >= 0 || path.indexOf('/cutscenes/') >= 0
			|| path.indexOf('\\\\cutscenes\\\\') >= 0)
			return 'cutscene';
		if (base.indexOf('substate') >= 0 || path.indexOf('/substates/') >= 0
			|| path.indexOf('\\\\substates\\\\') >= 0)
			return 'substate';
		if (base.indexOf('musicbeatstate') >= 0 || base.indexOf('state') >= 0
			|| path.indexOf('/states/') >= 0
			|| path.indexOf('\\\\states\\\\') >= 0)
			return 'state';
		if (path.indexOf('/ui/') >= 0 || path.indexOf('\\\\ui\\\\') >= 0)
			return 'ui';
		return 'unknown';
	}

	/** Select the declaration whose family owns a mixed HXC source file. */
	static function selectClassIndex(names:Array<String>, bases:Array<String>, path:String, source:String):Int {
		if (names == null || names.length == 0)
			return -1;
		var lowerPath = path == null ? '' : path.replace('\\', '/').toLowerCase();
		// Song files occasionally carry a small options Module before their Song
		// class.  The chart-local Song declaration owns the generated program; the
		// Module is merged as a safe companion below.
		if (lowerPath.indexOf('/songs/') >= 0 || lowerPath.indexOf('\\\\songs\\\\') >= 0
			|| lowerPath.indexOf('/song-scripts/') >= 0) {
			for (index in 0...names.length)
				if (index < bases.length && isSongBase(bases[index]))
					return index;
		}
		// Preserve the event precedence used by V-Slice's helper files.
		for (index in 0...names.length)
			if (index < bases.length && isSongEventBase(bases[index]))
				return index;
		// CharacterInfoBase/Character wrappers are selected before a generic state
		// declaration when a donor keeps a helper class in the same file.
		if (lowerPath.indexOf('/characters/') >= 0 || lowerPath.indexOf('\\\\characters\\\\') >= 0
			|| lowerPath.indexOf('/character/') >= 0) {
			var characterIndex = selectCharacterClassIndex(names, path, source);
			if (characterIndex >= 0)
				return characterIndex;
		}
		if (lowerPath.indexOf('/stages/') >= 0 || lowerPath.indexOf('\\\\stages\\\\') >= 0) {
			var identity = HxcScriptIdentity.inspect(source, 'stage',
				haxe.io.Path.withoutExtension(haxe.io.Path.withoutDirectory(path.replace('\\', '/'))));
			for (index in 0...names.length)
				if (names[index] == identity.stageClassName)
					return index;
			for (index in 0...names.length)
				if (index < bases.length && HxcScriptIdentity.familyForBase(bases[index]) == 'stage')
					return index;
		}
		for (index in 0...names.length)
			if (index < bases.length && isShaderBase(bases[index]))
				return index;
		// Misplaced character companions can also carry unrelated helper classes.
		// Select their actor declaration once the directory's owning type is absent.
		var characterIndex = selectCharacterClassIndex(names, path, source);
		if (characterIndex >= 0)
			return characterIndex;
		return 0;
	}

	/** Keep generated actor callbacks tied to the lexical discovery owner. */
	static function selectCharacterClassIndex(names:Array<String>, path:String, source:String):Int {
		var identity = HxcScriptIdentity.inspect(source, 'character',
			haxe.io.Path.withoutExtension(haxe.io.Path.withoutDirectory(path.replace('\\', '/'))));
		for (index in 0...names.length)
			if (names[index] == identity.characterClassName)
				return index;
		return -1;
	}

	static function isSongBase(base:String):Bool {
		if (base == null || base == '')
			return false;
		var lower = base.toLowerCase();
		return lower == 'song' || lower.endsWith('.song');
	}

	static function isCharacterBase(base:String):Bool {
		return HxcScriptIdentity.familyForBase(base) == 'character';
	}

	static function isShaderBase(base:String):Bool {
		if (base == null || base == '')
			return false;
		var lower = base.toLowerCase();
		return lower == 'flxruntimeshader'
			|| lower.endsWith('.flxruntimeshader')
			|| lower == 'scriptedflxruntimeshader';
	}

	/** Extract balanced top-level class fragments for the companion merge. */
	static function collectClassFragments(source:String):Array<HxcCompatClassFragment> {
		var result:Array<HxcCompatClassFragment> = [];
		if (source == null)
			return result;
		for (declaration in HxcScriptIdentity.classDeclarations(source)) {
			// Keep the existing executable-family boundary: plain helper classes
			// have no engine base and are not standalone lifecycle owners.
			if (declaration.base == '')
				continue;
			result.push({name: declaration.name, base: declaration.base, source: declaration.source});
		}
		return result;
	}

	/** Return true for the SongEvent base classes used by V-Slice donor files. */
	static function isSongEventBase(base:String):Bool {
		if (base == null || base == '')
			return false;
		var lower = base.toLowerCase();
		return lower == 'songevent' || lower == 'scriptedsongevent' || lower == 'scriptedsong_event'
			|| lower == 'scriptedsong-event' || lower == 'scriptedsong'
			|| lower.endsWith('.songevent') || lower.endsWith('.scriptedsong_event')
			|| lower.endsWith('.scriptedsong-event') || lower.endsWith('.scriptedsong');
	}

	/** Find the event identifier in the selected class, not a preceding helper module. */
	static function classIdentifier(source:String, className:String):String {
		if (source == null || className == null || className == '')
			return '';
		var expression = new EReg('\\bclass\\s+' + className + '\\b[^\\{]*\\{', 'm');
		if (!expression.match(source))
			return '';
		var position = expression.matchedPos();
		var open = source.indexOf('{', position.pos);
		if (open < 0)
			return '';
		var close = matchingDelimiter(source, open, '{', '}');
		if (close < 0)
			return '';
		var body = source.substr(open + 1, close - open - 1);
		var identifiers = collectMatches(body,
			'\\bsuper\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 1);
		return identifiers.length == 0 ? '' : identifiers[identifiers.length - 1];
	}

	static function inferEventAction(source:String):String {
		var lower = source.toLowerCase();
		if ((lower.indexOf('flxg.camera.zoom') >= 0 || lower.indexOf('camera.zoom') >= 0)
			&& lower.indexOf('camhud.zoom') >= 0)
			return 'Add Camera Zoom';
		if (lower.indexOf('swapstage(') >= 0 || lower.indexOf('loadstage(') >= 0
			|| lower.indexOf('stageid') >= 0)
			return 'Change Stage';
		if (lower.indexOf('.flash(') >= 0 || lower.indexOf('camera.flash(') >= 0)
			return 'Camera Flash';
		if ((lower.indexOf('characterdataparser') >= 0 || lower.indexOf('newchar') >= 0)
			&& (lower.indexOf('character') >= 0 || lower.indexOf('char') >= 0))
			return 'Change Character';
		if (lower.indexOf('scrollspeed') >= 0 && (lower.indexOf('tween') >= 0 || lower.indexOf('speed') >= 0))
			return 'Change Scroll Speed';
		return '';
	}

	static function isNativeEvent(name:String):Bool {
		if (name == null || name == '')
			return false;
		switch (name) {
		case 'Add Camera Zoom' | 'Zoom Camera' | 'Change Character' | 'Change Stage'
				| 'Camera Flash' | 'Camera Fade' | 'Lyrics' | 'Play Video'
				| 'Change Scroll Speed' | 'Set Camera Bop' | 'Play Animation'
				| 'Camera Follow Pos' | 'Set Cam Zoom' | 'Vignette' | 'Markov Popups'
				| 'Note Swap':
				return true;
			default:
				return false;
		}
	}

	/** Map V-Slice lifecycle spellings to the callback names used by PlayState. */
	static function lifecycleCallback(name:String):String {
		if (name == null)
			return '';
		switch (name.toLowerCase()) {
			case 'new': return '';
			case 'step': return 'stepHit';
			case 'oncreate' | 'create': return 'start';
			case 'oncreatepost' | 'createpost': return 'createPost';
			case 'onsongstart' | 'songstart': return 'songStart';
			case 'onupdate' | 'update': return 'update';
			case 'onupdatepost' | 'updatepost': return 'updatePost';
			case 'onbeathit' | 'beathit': return 'beatHit';
			case 'onstephit' | 'stephit': return 'stepHit';
			case 'onsectionhit' | 'sectionhit': return 'sectionHit';
			case 'oncountdowntick' | 'countdowntick': return 'countdownTick';
			case 'oncountdownstep' | 'countdownstep': return 'countdownStep';
			case 'oncountdownend' | 'countdownend': return 'countdownEnd';
			case 'onstartcountdown' | 'startcountdown': return 'startCountdown';
			case 'oncountdownstart' | 'countdownstart': return 'countdownStart';
			case 'ongoodnotehit' | 'goodnotehit': return 'goodNoteHit';
			case 'onopponentnotehit' | 'opponentnotehit': return 'opponentNoteHit';
			case 'onnotehit' | 'notehit': return 'noteHit';
			case 'onnoteincoming' | 'noteincoming': return 'noteIncoming';
			case 'onnotemiss' | 'notemiss': return 'noteMiss';
			case 'onopponentnotemiss' | 'opponentnotemiss': return 'opponentNoteMiss';
			case 'onnoteghostmiss' | 'noteghostmiss': return 'noteGhostMiss';
			case 'onsongend' | 'onendsong' | 'songend': return 'songEnd';
			case 'onsongretry' | 'songretry': return 'songRetry';
			case 'onsongevent' | 'songevent': return 'songEvent';
			case 'onpause' | 'pause': return 'pause';
			case 'onresume' | 'resume': return 'resume';
			case 'onpausesubstateopen' | 'pausesubstateopen': return 'subStateOpenEnd';
			case 'onpausesubstateclose' | 'pausesubstateclose': return 'subStateCloseBegin';
			case 'onsongloaded' | 'songloaded': return 'songLoaded';
			case 'onstatechangebegin' | 'statechangebegin': return 'stateChangeBegin';
			case 'onstatechangeend' | 'statechangeend': return 'stateChangeEnd';
			case 'onstateopenend' | 'stateopenend': return 'stateChangeEnd';
			case 'onsubstateclosebegin' | 'substateclosebegin': return 'subStateCloseBegin';
			case 'onsubstateopenend' | 'substateopenend': return 'subStateOpenEnd';
			case 'onsubstatecloseend' | 'substatecloseend': return 'subStateCloseEnd';
			case 'onplaystateenter' | 'playstateenter': return 'playStateEnter';
			case 'ondifficultyswitch' | 'difficultyswitch': return 'difficultySwitch';
			case 'oncapsuleselected' | 'capsuleselected': return 'capsuleSelected';
			case 'onfocusgained' | 'focusgained': return 'focusGained';
			case 'ongameover' | 'gameover': return 'gameOver';
			case 'ondestroy' | 'destroy': return 'destroy';
			default: return '';
		}
	}

	/** Character callbacks which PlayState dispatches on the actor's live scope. */
	static function characterLifecycleCallback(name:String):String {
		if (name == null)
			return '';
		switch (name.toLowerCase()) {
			case 'onadd' | 'add': return 'onAdd';
			case 'dance': return 'dance';
			case 'playanimation': return 'playAnimation';
			case 'playsinganimation': return 'playSingAnimation';
			case 'onanimationfinished' | 'animationfinished': return 'onAnimationFinished';
			default: return '';
		}
	}

	/** Read the literal definition id selected by a wrapper's `super(...)`. */
	static function characterConstructorTarget(functions:Array<HxcCompatFunction>):String {
		if (functions == null)
			return '';
		for (method in functions)
			if (method != null && method.name != null && method.name.toLowerCase() == 'new') {
				var target = firstString(method.body, '\\bsuper\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
				if (target != '')
					return target;
			}
		return '';
	}

	/**
		Read the data-only CharacterInfoBase constructor used by FPS Plus packs.
		The donor helper methods (`setSparrow`, `offset`, `loop`, addByPrefix and
		addByIndices) are metadata builders, not executable engine objects. Keep
		their literal result in a detached definition so the native Character owns
		atlas/frame lifetime and no donor class is instantiated.
	*/
	static function detectCharacterInfoDefinition(source:String):Dynamic {
		if (source == null || source == ''
			|| !new EReg('\\b(?:CharacterInfoBase|CharacterInfo|SparrowCharacter)\\b', 'm').match(source)
			|| !new EReg('\\binfo\\s*\\.\\s*(?:name|spritePath|frameLoadType|iconName)\\b', 'm').match(source))
			return null;
		var spritePath = firstString(source, '\\binfo\\s*\\.\\s*spritePath\\s*=\\s*["\\\']([^"\\\']+)["\\\']');
		var name = firstString(source, '\\binfo\\s*\\.\\s*name\\s*=\\s*["\\\']([^"\\\']+)["\\\']');
		var iconName = firstString(source, '\\binfo\\s*\\.\\s*iconName\\s*=\\s*["\\\']([^"\\\']+)["\\\']');
		var frameLoadType = new EReg('\\binfo\\s*\\.\\s*frameLoadType\\s*=\\s*setSparrow\\s*\\(', 'm').match(source)
			? 'sparrow' : '';
		var focus = literalNumberPair(source, '\\binfo\\s*\\.\\s*focusOffset\\s*\\.\\s*set\\s*\\(');
		if (focus == null)
			focus = [0, 0];
		var animations:Array<Dynamic> = [];
		collectCharacterPrefixAnimations(source, animations);
		collectCharacterIndexAnimations(source, animations);
		var extras:Array<Dynamic> = [];
		var extraExpression = new EReg('\\baddExtraData\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*\\[([^\\]]*)\\]\\s*\\)', 'g');
		var remaining = source;
		while (extraExpression.match(remaining)) {
			var values = literalNumberArray(extraExpression.matched(2));
			if (values != null)
				extras.push({name: extraExpression.matched(1), values: values});
			var position = extraExpression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		if (name == '' && spritePath == '' && animations.length == 0)
			return null;
		return {
			name: name,
			spritePath: spritePath,
			frameLoadType: frameLoadType,
			iconName: iconName,
			focusOffset: focus,
			animations: animations,
			extraData: extras
		};
	}

	static function collectCharacterPrefixAnimations(source:String, output:Array<Dynamic>):Void {
		var expression = new EReg('\\baddByPrefix\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*offset\\s*\\(\\s*([-+0-9.]+)\\s*,\\s*([-+0-9.]+)\\s*\\)\\s*,\\s*["\\\']([^"\\\']*)["\\\']\\s*,\\s*([-+0-9.]+)(?:\\s*,\\s*loop\\s*\\(\\s*(true|false)(?:\\s*,[^)]*)?\\))?', 'g');
		var remaining = source;
		while (expression.match(remaining)) {
			var name = expression.matched(1);
			if (name != null && name != '')
				appendCharacterAnimation(output, {
					name:name,
					kind:'prefix',
					offsetX:validNumeric(expression.matched(2), '0'),
					offsetY:validNumeric(expression.matched(3), '0'),
					prefix:expression.matched(4),
					fps:validNumeric(expression.matched(5), '24'),
					loop:expression.matched(6) == 'true',
					indices:[]
				});
			var position = expression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
	}

	static function collectCharacterIndexAnimations(source:String, output:Array<Dynamic>):Void {
		var expression = new EReg('\\baddByIndices\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*offset\\s*\\(\\s*([-+0-9.]+)\\s*,\\s*([-+0-9.]+)\\s*\\)\\s*,\\s*["\\\']([^"\\\']*)["\\\']\\s*,\\s*\\[([^\\]]*)\\]\\s*,\\s*["\\\']([^"\\\']*)["\\\']\\s*,\\s*([-+0-9.]+)(?:\\s*,\\s*loop\\s*\\(\\s*(true|false)(?:\\s*,[^)]*)?\\))?', 'g');
		var remaining = source;
		while (expression.match(remaining)) {
			var indices = literalIntArray(expression.matched(5));
			if (indices != null)
				appendCharacterAnimation(output, {
					name:expression.matched(1),
					kind:'indices',
					offsetX:validNumeric(expression.matched(2), '0'),
					offsetY:validNumeric(expression.matched(3), '0'),
					prefix:expression.matched(4),
					indicesPrefix:expression.matched(6),
					fps:validNumeric(expression.matched(7), '24'),
					loop:expression.matched(8) == 'true',
					indices:indices
				});
			var position = expression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
	}

	static function appendCharacterAnimation(output:Array<Dynamic>, value:Dynamic):Void {
		if (output == null || value == null)
			return;
		var name = Std.string(Reflect.field(value, 'name'));
		for (existing in output)
			if (existing != null && Std.string(Reflect.field(existing, 'name')) == name)
				return;
		output.push(value);
	}

	static function validNumeric(value:String, fallback:String):String {
		if (value == null || StringTools.trim(value) == '')
			return fallback;
		var clean = StringTools.trim(value);
		return new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', '').match(clean)
			? clean : fallback;
	}

	static function literalNumberPair(source:String, prefix:String):Null<Array<Dynamic>> {
		var expression = new EReg(prefix + '\\s*([-+0-9.]*)\\s*,?\\s*([-+0-9.]*)\\s*\\)', 'm');
		if (!expression.match(source))
			return null;
		var first = StringTools.trim(expression.matched(1));
		var second = StringTools.trim(expression.matched(2));
		return [first == '' ? 0 : Std.parseFloat(validNumeric(first, '0')),
			second == '' ? 0 : Std.parseFloat(validNumeric(second, '0'))];
	}

	static function literalNumberArray(source:String):Null<Array<Dynamic>> {
		if (source == null)
			return null;
		var values:Array<Dynamic> = [];
		for (piece in source.split(',')) {
			var clean = StringTools.trim(piece);
			if (clean == '')
				continue;
			var number = validNumeric(clean, '');
			if (number == '')
				return null;
			values.push(Std.parseFloat(number));
		}
		return values;
	}

	static function literalIntArray(source:String):Null<Array<Int>> {
		var values = literalNumberArray(source);
		if (values == null)
			return null;
		var result:Array<Int> = [];
		for (value in values) {
			var number = Std.int(value);
			if (number != value)
				return null;
			result.push(number);
		}
		return result;
	}

	static function detectShaderDefinition(source:String, className:String, baseClass:String):Dynamic {
		if (!isShaderBase(baseClass) || source == null)
			return null;
		var fragment = firstString(source,
			'Assets\\s*\\.\\s*getText\\s*\\(\\s*Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		if (fragment == '')
			fragment = firstString(source, 'Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		if (fragment == '')
			return null;
		var uniforms:Array<String> = collectMatches(source,
			'\\.set(?:Float|Int|Bool)\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 1);
		return {className:className, baseClass:baseClass, fragment:fragment, uniforms:uniforms};
	}

	/**
		Recognize a complete song/stage-owned shader/filter setup as data. This is
		kept strict on purpose: only a literal fragment name, a literal camera list
		and ordinary Flixel filter construction may cross the native boundary. A
		foreign shader object graph or arbitrary camera expression stays on the
		normal HXC safety path.
	*/
	static function detectRuntimeShaderDescriptors(source:String, kind:String):Array<Dynamic> {
		var descriptors:Array<Dynamic> = [];
		if ((kind != 'song-script' && kind != 'stage') || source == null || source == '')
			return descriptors;
		var shaderFields:Array<{var name:String; var fragment:String;}> = [];
		for (declaration in collectStateDeclarations(source)) {
			if (declaration == null || !isIdentifier(declaration.name)
				|| declaration.initializer == null || declaration.initializer == '')
				continue;
			var initializer = declaration.initializer;
			if (!new EReg('(?:new\\s+FlxRuntimeShader|createRuntimeShader)\\s*\\(', 'm').match(initializer))
				continue;
			var fragment = firstString(initializer,
				'Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
			if (fragment == '')
				continue;
			var found = false;
			for (existing in shaderFields)
				if (existing.name == declaration.name)
					found = true;
			if (!found)
				shaderFields.push({name: declaration.name, fragment: fragment});
		}
		var functions = collectFunctions(source);
		var dynamicCameraField = kind == 'stage' ? detectRegisteredStageCamera(source) : '';
		if (shaderFields.length == 0) {
			// Some bounded single-shader callbacks construct their graph after an
			// explicit option check. Preserve that established route: its descriptor
			// still comes from one literal fragment/filter pair and is independently
			// checked by the stricter complete-callback recognizer.
			var callbackDescriptor = detectRuntimeShaderDescriptor(source, kind);
			if (callbackDescriptor == null)
				return descriptors;
			var filterField = Std.string(Reflect.field(callbackDescriptor, 'filterField'));
			var evidence = runtimeShaderCameraEvidence(source, functions, filterField,
				dynamicCameraField);
			if (evidence.cameras.length == 0 && !evidence.dynamicCameraUsed)
				return descriptors;
			Reflect.setField(callbackDescriptor, 'cameraBindings', evidence.bindings);
			descriptors.push(callbackDescriptor);
			return descriptors;
		}
		// Keep the established option-gated one-shader route for existing imports.
		// Multi-graph files use the per-field detector below so each shader keeps
		// its own fragment, uniforms, filter, and camera evidence.
		var legacy:Dynamic = shaderFields.length == 1
			? detectRuntimeShaderDescriptor(source, kind) : null;
		for (shader in shaderFields) {
			var filterField = '';
			var filterMatches = 0;
			for (declaration in collectStateDeclarations(source)) {
				if (declaration == null || !isIdentifier(declaration.name)
					|| declaration.initializer == null)
					continue;
				if (new EReg('^new\\s+ShaderFilter\\s*\\(\\s*'
					+ EReg.escape(shader.name) + '\\s*\\)$', 'm').match(StringTools.trim(declaration.initializer))) {
					filterField = declaration.name;
					filterMatches++;
				}
			}
			if (filterMatches != 1 || !isIdentifier(filterField))
				continue;

			var cameraEvidence = runtimeShaderCameraEvidence(source, functions,
				filterField, dynamicCameraField);
			var cameras:Array<String> = cameraEvidence.cameras;
			var usedDynamicCamera:Bool = cameraEvidence.dynamicCameraUsed;
			if (cameras.length == 0 && !usedDynamicCamera)
				continue;

			var descriptor:Dynamic = null;
			if (legacy != null && Std.string(Reflect.field(legacy, 'shaderField')) == shader.name)
				descriptor = legacy;
			else {
				var uniforms:Array<String> = collectMatches(source,
					'\\b' + EReg.escape(shader.name)
						+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(\\s*["\\\']([^"\\\']+)', 1);
				descriptor = {
					shaderName: shader.fragment,
					cameras: cameras.copy(),
					shaderField: shader.name,
					filterField: filterField,
					dynamicCameraField: usedDynamicCamera ? dynamicCameraField : '',
					deferCameraBinding: true,
					uniforms: uniforms,
					initialEnabled: true,
					pulseHelper: '',
					pulseDuration: 0.5,
					gate: null
				};
			}
			// Legacy metadata can include unrelated camera writes from a helper.
			// The generic detector's exact filter/camera evidence is authoritative
			// for multi-graph files and is also retained for diagnostics/tests.
			Reflect.setField(descriptor, 'shaderName', shader.fragment);
			Reflect.setField(descriptor, 'shaderField', shader.name);
			Reflect.setField(descriptor, 'filterField', filterField);
			Reflect.setField(descriptor, 'cameraBindings', cameraEvidence.bindings);
			if (shaderFields.length > 1) {
				Reflect.setField(descriptor, 'cameras', cameras.copy());
				Reflect.setField(descriptor, 'dynamicCameraField', usedDynamicCamera ? dynamicCameraField : '');
				Reflect.setField(descriptor, 'preferenceGuard', null);
				Reflect.setField(descriptor, 'gate', null);
				Reflect.setField(descriptor, 'deferCameraBinding', true);
				var uniforms:Array<String> = collectMatches(source,
					'\\b' + EReg.escape(shader.name)
						+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(\\s*["\\\']([^"\\\']+)', 1);
				Reflect.setField(descriptor, 'uniforms', uniforms);
				var pulse = detectRuntimeShaderPulse(source, functions, shader.name, cameras, uniforms);
				Reflect.setField(descriptor, 'pulseHelper', pulse == null
					|| Reflect.field(pulse, 'emittable') != true ? '' : Std.string(Reflect.field(pulse, 'helperName')));
				Reflect.setField(descriptor, 'pulseDuration', pulse == null ? 0.5 : Reflect.field(pulse, 'pulseDuration'));
				Reflect.setField(descriptor, 'pulseWarningHelper', pulse == null ? '' : Reflect.field(pulse, 'helperName'));
				Reflect.setField(descriptor, 'pulseComplete', pulse != null && Reflect.field(pulse, 'complete') == true);
				Reflect.setField(descriptor, 'pulseArguments', pulse == null ? [] : Reflect.field(pulse, 'arguments'));
				Reflect.setField(descriptor, 'pulseHoldDuration', pulse == null ? '' : Reflect.field(pulse, 'holdDuration'));
				Reflect.setField(descriptor, 'pulseEase', pulse == null ? 'circOut' : Reflect.field(pulse, 'ease'));
				Reflect.setField(descriptor, 'pulseUniform', pulse == null ? 'alpha' : Reflect.field(pulse, 'uniform'));
				Reflect.setField(descriptor, 'pulseSoundParameter', pulse == null ? '' : Reflect.field(pulse, 'soundParameter'));
			}
			descriptors.push(descriptor);
		}
		return descriptors;
	}

	/** Find static camera targets and a single verified stage-owned camera. */
	static function runtimeShaderCameraEvidence(source:String,
		functions:Array<HxcCompatFunction>, filterField:String,
		dynamicCameraField:String):Dynamic {
		var cameras:Array<String> = [];
		var bindings:Array<Dynamic> = [];
		var dynamicCameraUsed = false;
		if (source == null || filterField == null || filterField == '')
			return {cameras: cameras, dynamicCameraUsed: false, bindings: bindings};
		var targets:Array<String> = ['camGame', 'camHUD'];
		if (isIdentifier(dynamicCameraField))
			targets.push(dynamicCameraField);
		for (method in functions) {
			if (method == null || method.name == null || method.body == null)
				continue;
			for (target in targets) {
				var pattern = '(?:game\\s*\\.|PlayState\\s*\\.\\s*instance\\s*\\.)?'
					+ EReg.escape(target) + '\\s*\\.\\s*filters\\s*=\\s*([^;\\n]+)';
				var assignment = new EReg(pattern, 'gm');
				var offset = 0;
				while (offset < method.body.length && assignment.match(method.body.substr(offset))) {
					var match = assignment.matchedPos();
					var absolute = offset + match.pos;
					var rhs = StringTools.trim(assignment.matched(1));
					var exactFilter = rhs == '[' + filterField + ']';
					var localAlias = false;
					var identifierValue = new EReg('^[A-Za-z_][A-Za-z0-9_]*$', 'm');
					if (identifierValue.match(rhs)) {
						var localName = identifierValue.matched(0);
						localAlias = new EReg('\\bvar\\s+' + EReg.escape(localName) + '\\b', 'm').match(method.body)
							&& new EReg('\\b' + EReg.escape(filterField) + '\\b', 'm').match(method.body);
					}
					if (exactFilter || localAlias) {
						if (target == dynamicCameraField)
							dynamicCameraUsed = true;
						else
							appendUnique(cameras, target);
						if (exactFilter)
							bindings.push({methodName: method.name, camera: target,
								cameraField: target == dynamicCameraField ? target : '', enabled: true});
					}
					offset = absolute + match.len;
				}
			}
		}
		return {cameras: cameras, dynamicCameraUsed: dynamicCameraUsed, bindings: bindings};
	}

	static function detectRuntimeShaderDescriptor(source:String, kind:String):Dynamic {
		if ((kind != 'song-script' && kind != 'stage') || source == null || source == '')
			return null;
		var fragment = firstString(source,
			'Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		if (fragment == '')
			return null;
		var lower = source.toLowerCase();
		if (lower.indexOf('new flxruntimeshader') < 0
			&& lower.indexOf('createRuntimeShader') < 0)
			return null;
		if (lower.indexOf('new shaderfilter') < 0
			&& lower.indexOf('shaderfilter(') < 0)
			return null;
		var cameras:Array<String> = [];
		if (new EReg('\\b(?:game\\s*\\.\\s*|PlayState\\s*\\.\\s*instance\\s*\\.)?(?:camHUD|camHud)\\s*\\.\\s*filters\\b', 'm').match(source))
			cameras.push('camHUD');
		if (new EReg('\\b(?:game\\s*\\.\\s*|PlayState\\s*\\.\\s*instance\\s*\\.)?(?:camGame|camgame)\\s*\\.\\s*filters\\b', 'm').match(source))
			cameras.push('camGame');
		var dynamicCameraField = kind == 'stage' ? detectRegisteredStageCamera(source) : '';
		if (cameras.length == 0 && dynamicCameraField == '')
			return null;
		var shaderField = firstString(source,
			'\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_.<>]*)?\\s*=\\s*new\\s+FlxRuntimeShader');
		if (shaderField == '')
			shaderField = firstString(source,
				'\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_.<>]*)?\\s*=\\s*createRuntimeShader');
		var filterField = '';
		if (shaderField != '')
			filterField = firstString(source,
				'\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_.<>]*)?\\s*=\\s*new\\s+ShaderFilter\\s*\\(\\s*'
				+ shaderField + '\\s*\\)');
		var uniforms:Array<String> = collectMatches(source,
			'\\b' + (shaderField == '' ? '[A-Za-z_][A-Za-z0-9_]*' : shaderField)
				+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(\\s*["\\\']([^"\\\']+)', 1);
		var preferenceGuard:Dynamic = dynamicCameraField == '' || filterField == '' ? null
			: detectStageShaderPreferenceGuard(source, dynamicCameraField, filterField);
		var initialEnabled = true;
		if (new EReg('\\.filtersEnabled\\s*=\\s*false\\b', 'm').match(source))
			initialEnabled = false;
		var gateBucket = '';
		var gateField = '';
		var gateDefault = false;
		// Option-gated shader setup is carried as a data-only store bucket.  The
		// generated adapter reads the isolated compatibility store directly; it
		// never calls ModuleHandler or instantiates RabbitHoleOptions.
		var gate = new EReg('modOptions\\s*\\.\\s*get\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)', 'm');
		if (gate.match(source)) {
			gateBucket = gate.matched(1);
			var field = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*(?:\\.|\\[\\s*["\\\'])shadersEnabled', 'm');
			if (field.match(source))
				gateField = 'shadersEnabled';
			else if (new EReg('\\bshadersEnabled\\b', 'm').match(source))
				gateField = 'shadersEnabled';
		}
		var pulse = detectRuntimeShaderPulse(source, collectFunctions(source), shaderField,
			cameras, uniforms);
		var pulseHelper = pulse == null || Reflect.field(pulse, 'emittable') != true
			? '' : Std.string(Reflect.field(pulse, 'helperName'));
		var pulseDuration:Float = pulse == null ? 0.5 : cast Reflect.field(pulse, 'pulseDuration');
		// The descriptor is intentionally neutral about class/song names. The bloom
		// option in Rabbit Hole is merely one instance of the generic option-gated
		// camera-filter contract; Markov's pulse helper is recognized structurally.
		return {
			shaderName: fragment,
			cameras: cameras,
			shaderField: shaderField,
			filterField: filterField,
			dynamicCameraField: dynamicCameraField,
			preferenceGuard: preferenceGuard,
			deferCameraBinding: dynamicCameraField != '',
			uniforms: uniforms,
			initialEnabled: initialEnabled,
			pulseHelper: pulseHelper,
			pulseDuration: pulseDuration,
			pulseWarningHelper: pulse == null ? '' : Std.string(Reflect.field(pulse, 'helperName')),
			pulseComplete: pulse == null ? false : Reflect.field(pulse, 'complete') == true,
			pulseArguments: pulse == null ? [] : Reflect.field(pulse, 'arguments'),
			pulseHoldDuration: pulse == null ? '' : Std.string(Reflect.field(pulse, 'holdDuration')),
			pulseEase: pulse == null ? 'circOut' : Std.string(Reflect.field(pulse, 'ease')),
			pulseUniform: pulse == null ? 'alpha' : Std.string(Reflect.field(pulse, 'uniform')),
			pulseSoundParameter: pulse == null ? '' : Std.string(Reflect.field(pulse, 'soundParameter')),
			gate: gateField == '' ? null : {
				bucket: gateBucket,
				field: gateField,
				defaultValue: gateDefault
			}
		};
	}

	/** Recognize the portable parts of one HXC filter-pulse helper. A partial
	 * match still emits the bounded native pulse and keeps the remaining body in
	 * the diagnostics; arbitrary statements are never copied into generated code. */
	static function detectRuntimeShaderPulse(source:String, functions:Array<HxcCompatFunction>,
		shaderField:String, cameras:Array<String>, uniforms:Array<String>):Dynamic {
		if (functions == null)
			return null;
		var cameraPrefix = '(?:PlayState\\s*\\.\\s*instance\\s*\\.|game\\s*\\.\\s*)?';
		var cameraName = '(camGame|camHUD)';
		var enabledPattern = new EReg(cameraPrefix + cameraName
			+ '\\s*\\.\\s*filtersEnabled\\s*=\\s*true\\s*;', 'm');
		var timerPattern = new EReg('new\\s+FlxTimer\\s*\\(\\s*\\)\\s*\\.\\s*start\\s*\\(\\s*([^,]+?)\\s*,\\s*function\\s*\\([^)]*\\)\\s*\\{\\s*'
			+ cameraPrefix + cameraName + '\\s*\\.\\s*filtersEnabled\\s*=\\s*false\\s*;\\s*\\}\\s*\\)', 'm');
		var number = '(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)';
		var tweenPattern = new EReg('FlxTween\\s*\\.\\s*num\\s*\\(\\s*0(?:\\.0+)?\\s*,\\s*1(?:\\.0+)?\\s*,\\s*('
			+ number + ')\\s*,\\s*\\{\\s*ease\\s*:\\s*FlxEase\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\}\\s*,\\s*function\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)(?:\\s*:\\s*[A-Za-z_][A-Za-z0-9_.<>]*)?\\s*\\)\\s*\\{\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*\\3\\s*;\\s*\\}\\s*\\)', 'm');
		var soundPattern = new EReg('if\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*!=\\s*null\\s*&&\\s*\\1\\s*\\.\\s*length\\s*>\\s*0\\s*\\)\\s*\\{?\\s*FunkinSound\\s*\\.\\s*playOnce\\s*\\(\\s*Paths\\s*\\.\\s*sound\\s*\\(\\s*\\1\\s*\\)\\s*\\)\\s*;\\s*\\}?', 'm');
		var identifier = new EReg('^[A-Za-z_][A-Za-z0-9_]*$', 'm');
		var literalNumber = new EReg('^(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', 'm');
		for (method in functions) {
			if (method == null || method.name == null || method.body == null)
				continue;
			var methodArguments = method.arguments == null ? [] : method.arguments;
			var remaining = stripComments(method.body);
			var pulseHint = new EReg('\\bfiltersEnabled\\s*=\\s*(?:true|false)\\b|FlxTween\\s*\\.\\s*num\\s*\\(|new\\s+FlxTimer', 'm');
			if (!pulseHint.match(remaining))
				continue;

			var emittable = false;
			var enabledCamera = '';
			if (enabledPattern.match(remaining)) {
				enabledCamera = enabledPattern.matched(1);
				remaining = enabledPattern.replace(remaining, '');
			}
			var tweenDuration:Float = 0.5;
			var ease = 'circOut';
			var tweenTarget = '';
			var tweenMatched = tweenPattern.match(remaining);
			if (tweenMatched) {
				var parsedDuration = Std.parseFloat(tweenPattern.matched(1));
				if (!Math.isNaN(parsedDuration) && parsedDuration > 0)
					tweenDuration = parsedDuration;
				ease = tweenPattern.matched(2);
				tweenTarget = tweenPattern.matched(4);
				remaining = tweenPattern.replace(remaining, '');
			}
			var holdDuration = '';
			var timerCamera = '';
			if (timerPattern.match(remaining)) {
				holdDuration = StringTools.trim(timerPattern.matched(1));
				timerCamera = timerPattern.matched(2);
				remaining = timerPattern.replace(remaining, '');
			}
			var soundParameter = '';
			var soundMatched = soundPattern.match(remaining);
			if (soundMatched) {
				var candidateSoundParameter = soundPattern.matched(1);
				if (methodArguments.indexOf(candidateSoundParameter) >= 0) {
					soundParameter = candidateSoundParameter;
					remaining = soundPattern.replace(remaining, '');
				} else {
					soundMatched = false;
				}
			}
			var pulseUniform = '';
			if (shaderField != null && shaderField != '' && tweenTarget != '') {
				var updatePattern = new EReg('\\b' + EReg.escape(shaderField)
					+ '\\s*\\.\\s*setFloat\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*'
					+ EReg.escape(tweenTarget) + '\\s*\\)', 'm');
				if (updatePattern.match(source)) {
					var candidateUniform = updatePattern.matched(1);
					if (uniforms != null && uniforms.indexOf(candidateUniform) >= 0)
						pulseUniform = candidateUniform;
				}
			}
			var safeHoldDuration = identifier.match(holdDuration) && methodArguments.indexOf(holdDuration) >= 0
				? holdDuration : (literalNumber.match(holdDuration) ? holdDuration : '');
			var cameraOwned = enabledCamera != '' && enabledCamera == timerCamera
				&& cameras != null && cameras.indexOf(enabledCamera) >= 0;
			emittable = tweenMatched && cameraOwned && safeHoldDuration != '' && pulseUniform != '';
			var residue = new EReg('[\\s{};]', 'g').replace(remaining, '');
			var complete = emittable && residue == '';
			if (!emittable && enabledCamera == '' && !tweenMatched && timerCamera == '')
				continue;
			return {
				helperName: method.name,
				emittable: emittable,
				complete: complete,
				arguments: methodArguments.copy(),
				pulseDuration: tweenDuration,
				holdDuration: safeHoldDuration,
				ease: ease,
				uniform: pulseUniform == '' ? 'alpha' : pulseUniform,
				soundParameter: soundParameter,
				soundRecognized: soundMatched,
				remainingOperations: residue
			};
		}
		return null;
	}

	/**
		Find one stage-owned camera only when source constructs it and registers it
		with FlxG's camera list from buildStage. The runtime later repeats the
		registration check before attaching a filter, so a field name by itself is
		never enough to authorize a foreign camera object.
	*/
	static function detectRegisteredStageCamera(source:String):String {
		if (source == null || source == '')
			return '';
		var declarations = collectStateDeclarations(source);
		var functions = collectFunctions(source);
		for (declaration in declarations) {
			if (declaration == null || declaration.name == null || declaration.name == '')
				continue;
			var field = declaration.name;
			var typedCamera = new EReg('\\bvar\\s+' + EReg.escape(field)
				+ '\\s*:\\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*\\.)*)?(?:FunkinCamera|FlxCamera)\\s*;', 'm');
			if (!typedCamera.match(source))
				continue;
			var constructorPattern = '\\b' + EReg.escape(field)
				+ '\\s*=\\s*new\\s+FunkinCamera\\s*\\(\\s*(["\\\'])[^"\\\']+\\1\\s*\\)';
			var cameraConstructor = new EReg(constructorPattern, 'gm');
			var registrationPattern = '\\bFlxG\\s*\\.\\s*cameras\\s*\\.\\s*insert\\s*\\(\\s*'
				+ EReg.escape(field)
				+ '\\s*,\\s*FlxG\\s*\\.\\s*cameras\\s*\\.\\s*list\\s*\\.\\s*indexOf\\s*\\(\\s*'
				+ 'PlayState\\s*\\.\\s*instance\\s*\\.\\s*camGame\\s*\\)\\s*,\\s*false\\s*\\)';
			var cameraRegistration = new EReg(registrationPattern, 'gm');
			for (method in functions) {
				if (method == null || method.name == null || method.body == null
					|| method.name.toLowerCase() != 'buildstage')
					continue;
				if (countRegexMatches(method.body, constructorPattern) != 1
					|| countRegexMatches(method.body, registrationPattern) != 1
					|| !cameraConstructor.match(method.body)
					|| !cameraRegistration.match(method.body))
					continue;
				var constructorPosition = cameraConstructor.matchedPos();
				var registrationPosition = cameraRegistration.matchedPos();
				if (constructorPosition.pos >= registrationPosition.pos)
					continue;
				return field;
			}
		}
		return '';
	}

	/** Count non-overlapping source matches without depending on regexp state. */
	static function countRegexMatches(source:String, pattern:String):Int {
		if (source == null || pattern == null || pattern == '')
			return 0;
		var matcher = new EReg(pattern, 'g');
		var count = 0;
		var offset = 0;
		while (offset < source.length && matcher.match(source.substr(offset))) {
			var position = matcher.matchedPos();
			count++;
			offset += position.pos + (position.len <= 0 ? 1 : position.len);
		}
		return count;
	}

	/**
		Recognize a simple boolean preference check which directly owns the
		stage-camera filter write. The preference root must itself be assigned from
		the HXC namespace store in the stage constructor; HScript then uses a strict
		bool read so values such as the string "true" cannot enable the effect.
	*/
	static function detectStageShaderPreferenceGuard(source:String,
		cameraField:String, filterField:String):Dynamic {
		if (source == null || !isIdentifier(cameraField) || !isIdentifier(filterField))
			return null;
		var callback:HxcCompatFunction = null;
		for (method in collectFunctions(source))
			if (method != null && method.name != null
				&& method.name.toLowerCase() == 'oncountdownstart') {
				callback = method;
				break;
			}
		if (callback == null || callback.body == null)
			return null;
		var compact = compactExpression(stripComments(callback.body));
		var assignment = cameraField + '.filters=[' + filterField + '];';
		var assignmentPosition = compact.indexOf(assignment);
		if (assignmentPosition < 0
			|| compact.indexOf(assignment, assignmentPosition + assignment.length) >= 0)
			return null;
		var prefix = compact.substr(0, assignmentPosition);
		var ifPosition = prefix.lastIndexOf('if(');
		if (ifPosition < 0)
			return null;
		var open = ifPosition + 2;
		var close = matchingDelimiter(compact, open, '(', ')');
		if (close < 0 || close >= assignmentPosition)
			return {sourceBacked: false};
		var between = compact.substr(close + 1, assignmentPosition - close - 1);
		if (between != '' && between != '{') {
			// A branch with preceding work is deliberately not inferred as a guard;
			// this also distinguishes an earlier completed `if` from this write.
			if (between.indexOf(';') >= 0 || between.indexOf('}') >= 0)
				return null;
			return {sourceBacked: false};
		}
		var condition = compact.substr(open + 1, close - open - 1);
		var guardMatch = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\.([A-Za-z_][A-Za-z0-9_]*)$', 'm');
		if (!guardMatch.match(condition))
			return {sourceBacked: false};
		var saveField = guardMatch.matched(1);
		var preferenceField = guardMatch.matched(2);
		var suffix = compact.substr(assignmentPosition + assignment.length);
		if (between == '{') {
			if (!StringTools.startsWith(suffix, '}'))
				return {sourceBacked: false};
			suffix = suffix.substr(1);
		}
		if (StringTools.startsWith(suffix, 'else'))
			return {sourceBacked: false};
		return {
			saveField: saveField,
			field: preferenceField,
			sourceBacked: stageSaveViewBacked(source, saveField)
		};
	}

	/** Verify that a preference guard's root comes from the scoped Save view. */
	static function stageSaveViewBacked(source:String, saveField:String):Bool {
		if (source == null || !isIdentifier(saveField))
			return false;
		var expected = saveField + '=__hxcStore.getSave()';
		for (method in collectFunctions(source)) {
			if (method == null || method.name == null || method.name.toLowerCase() != 'new'
				|| method.body == null)
				continue;
			for (statement in splitTopLevel(method.body, ';')) {
				var translated = compactExpression(translateBody(statement, 'new', []));
				if (translated == expected)
					return true;
			}
		}
		return false;
	}

	/**
		A shader gate is source-backed only when a colocated Module carries the
		matching literal bool record, initializes it from its isolated modOptions
		bucket, and exposes that value through the ordinary preference checkbox
		shape. This does not accept a module/class name allow-list.
	*/
	static function completeRuntimeShaderOptionCompanion(companion:HxcCompatResult,
		source:String, moduleName:String, descriptor:Dynamic):Bool {
		if (companion == null || companion.kind != 'module' || source == null
			|| moduleName == null || moduleName == '' || descriptor == null)
			return false;
		var gate:Dynamic = Reflect.field(descriptor, 'gate');
		if (gate == null)
			return false;
		var bucket = Std.string(Reflect.field(gate, 'bucket'));
		var field = Std.string(Reflect.field(gate, 'field'));
		var defaultValue = Reflect.field(gate, 'defaultValue') == true;
		if (bucket == '' || field == '' || !isIdentifier(field)
			|| !new EReg('\\bclass\\s+' + EReg.escape(moduleName) + '\\s+extends\\s+Module\\b', 'm').match(source))
			return false;
		var key = '(["\\\']' + EReg.escape(bucket) + '["\\\'])';
		if (!new EReg('modOptions\\s*\\.\\s*get\\s*\\(\\s*' + key + '\\s*\\)', 'm').match(source)
			|| !new EReg('modOptions\\s*\\.\\s*set\\s*\\(\\s*' + key + '\\s*,', 'm').match(source)
			|| !new EReg('modOptions\\s*\\.\\s*get\\s*\\(\\s*' + key + '\\s*\\)\\s*==\\s*null', 'm').match(source)
			|| !new EReg('\\.\\s*flush\\s*\\(\\s*\\)', 'm').match(source)
			|| !new EReg('\\bcreatePrefItemCheckbox\\s*\\(', 'm').match(source))
			return false;
		var fieldInitializer = false;
		var recordName = '';
		var recordInitializer = '';
		for (initializer in companion.stateInitializers) {
			if (initializer == null || initializer.name == null || initializer.value == null)
				continue;
			if (initializer.name == field && initializer.value == (defaultValue ? 'true' : 'false'))
				fieldInitializer = true;
			var recordField = new EReg('(?:\\{|,)\\s*' + EReg.escape(field)
				+ '\\s*:\\s*(true|false)\\s*(?:,|\\})', 'm');
			if (initializer.value.startsWith('{') && recordField.match(initializer.value)
				&& (recordField.matched(1) == 'true') == defaultValue) {
				recordName = initializer.name;
				recordInitializer = initializer.value;
			}
		}
		if (!fieldInitializer || recordName == '' || recordInitializer == '')
			return false;
		var setter = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*' + EReg.escape(field)
			+ '\\s*=\\s*([A-Za-z_][A-Za-z0-9_]*)', 'm');
		if (!setter.match(source))
			return false;
		var callbackField = setter.matched(1);
		var boolArgument = setter.matched(2);
		if (callbackField != recordName
			|| !new EReg('\\b' + EReg.escape(field) + '\\s*=\\s*' + EReg.escape(recordName)
				+ '\\s*\\.\\s*' + EReg.escape(field), 'm').match(source)
			|| !new EReg('\\b' + EReg.escape(recordName) + '\\s*\\.\\s*' + EReg.escape(field)
				+ '\\s*=\\s*' + EReg.escape(boolArgument), 'm').match(source)
			|| !new EReg('modOptions\\s*\\.\\s*set\\s*\\(\\s*' + key
				+ '\\s*,\\s*' + EReg.escape(recordName) + '\\s*\\)', 'm').match(source))
			return false;
		var stateChange = false;
		for (callback in companion.callbackAdapters)
			if (callback != null && callback.sourceName != null
				&& callback.sourceName.toLowerCase() == 'onstatechangeend')
				stateChange = true;
		return stateChange;
	}

	/**
		Match only the complete ModuleHandler -> bool gate -> scoped shader/filter
		construction -> declared camera assignments. The caller emits the native
		shader descriptor hook in place of this donor body; an extra statement or
		unknown object access keeps the conservative warning.
	*/
	static function isCompleteRuntimeShaderCallback(method:HxcCompatFunction,
		descriptor:Dynamic, moduleNames:Array<String>):Bool {
		if (method == null || method.arguments == null || method.arguments.length == 0
			|| descriptor == null || moduleNames == null || moduleNames.length == 0)
			return false;
		var gate:Dynamic = Reflect.field(descriptor, 'gate');
		var shaderName = Std.string(Reflect.field(descriptor, 'shaderName'));
		var shaderField = Std.string(Reflect.field(descriptor, 'shaderField'));
		var filterField = Std.string(Reflect.field(descriptor, 'filterField'));
		var gateField = gate == null ? '' : Std.string(Reflect.field(gate, 'field'));
		var moduleName = firstString(method.body,
			'\\bModuleHandler\\s*\\.\\s*getModule\\s*\\(\\s*["\\\']([^"\\\']+)');
		var allowName = firstString(method.body,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*Bool\\s*=\\s*false');
		var moduleVar = firstString(method.body,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*ModuleHandler\\s*\\.\\s*getModule');
		var gameVar = firstString(method.body,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*PlayState\\s*\\.\\s*instance');
		var cameras:Dynamic = Reflect.field(descriptor, 'cameras');
		if (gate == null || shaderName == '' || !isIdentifier(shaderField)
			|| !isIdentifier(filterField) || gateField == '' || moduleName == ''
			|| moduleNames.indexOf(moduleName) < 0 || allowName == '' || moduleVar == ''
			|| gameVar == '' || !Std.isOfType(cameras, Array))
			return false;
		var arg = method.arguments[0];
		if (!isIdentifier(arg))
			return false;
		var camerasArray:Array<Dynamic> = cast cameras;
		if (camerasArray.length == 0)
			return false;
		var expected = 'super.onCountdownStart(' + arg + ');'
			+ 'var' + allowName + ':Bool=false;'
			+ 'var' + moduleVar + '=ModuleHandler.getModule(' + quote(moduleName) + ');'
			+ 'if(' + moduleVar + '!=null){' + allowName + '=' + moduleVar
			+ '.scriptGet(' + quote(gateField) + ');}'
			+ 'if(' + allowName + '&&Assets.exists(Paths.frag(' + quote(shaderName) + '))){'
			+ 'var' + gameVar + '=PlayState.instance;'
			+ shaderField + '=newFlxRuntimeShader(Assets.getText(Paths.frag(' + quote(shaderName) + ')));'
			+ filterField + '=newShaderFilter(' + shaderField + ');';
		for (camera in camerasArray) {
			var cameraName = camera == null ? '' : Std.string(camera);
			if (cameraName != 'camHUD' && cameraName != 'camGame')
				return false;
			expected += gameVar + '.' + cameraName + '.filters=[' + filterField + '];';
		}
		expected += '}';
		var actual = compactExpression(stripComments(method.body));
		return actual == expected;
	}

	/**
		A stage countdown callback may keep its complete donor behavior when its
		shader writes target one literal, manifest-scoped descriptor and every
		remaining operation already lowers to safe HScript. The descriptor must
		cover all camera/filter writes, uniform names and literal values; local
		helper calls must resolve to safe helpers emitted beside the callback.
	*/
	static function isCompleteStageRuntimeShaderCallback(method:HxcCompatFunction,
		callback:HxcCompatCallbackAdapter, descriptor:Dynamic,
		helperAdapters:Array<HxcCompatCallbackAdapter>):Bool {
		if (method == null || callback == null || descriptor == null
			|| method.name == null || method.name.toLowerCase() != 'oncountdownstart'
			|| callback.body == null || Reflect.field(descriptor, 'gate') != null)
			return false;
		var shaderFieldValue = Reflect.field(descriptor, 'shaderField');
		var filterFieldValue = Reflect.field(descriptor, 'filterField');
		var camerasValue = Reflect.field(descriptor, 'cameras');
		if (shaderFieldValue == null || filterFieldValue == null
			|| !isIdentifier(Std.string(shaderFieldValue))
			|| !isIdentifier(Std.string(filterFieldValue))
			|| camerasValue == null || !Std.isOfType(camerasValue, Array))
			return false;
		var shaderField = Std.string(shaderFieldValue);
		var filterField = Std.string(filterFieldValue);
		var cameras:Array<Dynamic> = cast camerasValue;
		var dynamicCameraValue:Dynamic = Reflect.field(descriptor, 'dynamicCameraField');
		var dynamicCameraField = dynamicCameraValue == null ? '' : Std.string(dynamicCameraValue);
		if (dynamicCameraField != '' && !isIdentifier(dynamicCameraField))
			return false;
		if (!runtimeShaderUniformWritesAreLiteral(method.body, descriptor, shaderField))
			return false;
		if (cameras.length == 0 && dynamicCameraField == '')
			return false;
		var expectedCameraWrites = 0;
		for (cameraValue in cameras) {
			var camera = cameraValue == null ? '' : Std.string(cameraValue);
			if (camera != 'camGame' && camera != 'camHUD')
				return false;
			var cameraWrite = new EReg('\\b(?:game\\s*\\.\\s*|PlayState\\s*\\.\\s*instance\\s*\\.)?'
				+ camera + '\\s*\\.\\s*filters\\s*=\\s*\\[\\s*'
				+ EReg.escape(filterField) + '\\s*\\]', 'm');
			if (cameraWrite.match(method.body))
				expectedCameraWrites++;
		}
		if (dynamicCameraField != '') {
			var dynamicWrite = new EReg('\\b' + EReg.escape(dynamicCameraField)
				+ '\\s*\\.\\s*filters\\s*=\\s*\\[\\s*'
				+ EReg.escape(filterField) + '\\s*\\]', 'm');
			if (!dynamicWrite.match(method.body))
				return false;
			expectedCameraWrites++;
			var preferenceGuard:Dynamic = Reflect.field(descriptor, 'preferenceGuard');
			if (preferenceGuard != null
				&& Reflect.field(preferenceGuard, 'sourceBacked') != true)
				return false;
		}
		if (expectedCameraWrites != cameras.length + (dynamicCameraField == '' ? 0 : 1))
			return false;
		// Filter writes inside the source callback must be limited to the exact
		// descriptor cameras and either the owned filter or an empty clear. Any
		// other target/value would need separate semantics before it can execute.
		var filterTargets = '(?:camGame|camHUD' + (dynamicCameraField == '' ? ''
			: '|' + EReg.escape(dynamicCameraField)) + ')';
		var filterAssignments = new EReg('\\b(?:game\\s*\\.\\s*|PlayState\\s*\\.\\s*instance\\s*\\.)?'
			+ filterTargets + '\\s*\\.\\s*filters\\s*=', 'gm');
		var filterAssignmentCount = 0;
		var offset = 0;
		while (offset < method.body.length && filterAssignments.match(method.body.substr(offset))) {
			var position = filterAssignments.matchedPos();
			var absolute = offset + position.pos;
			var equals = method.body.indexOf('=', absolute);
			var semicolon = method.body.indexOf(';', equals + 1);
			if (equals < 0 || semicolon < 0)
				return false;
			var value = StringTools.trim(method.body.substr(equals + 1, semicolon - equals - 1));
			if (value != '[]' && value != '[' + filterField + ']')
				return false;
			filterAssignmentCount++;
			offset = semicolon + 1;
		}
		if (filterAssignmentCount != expectedCameraWrites)
			return false;
		if (countRegexMatches(method.body, '\\b[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*filters\\s*=')
			!= filterAssignmentCount)
			return false;
		var residualShaderOperation = new EReg('new\\s+FlxRuntimeShader|new\\s+ShaderFilter|\\.filters\\b|\\b'
			+ EReg.escape(shaderField) + '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(', 'm');
		if (residualShaderOperation.match(callback.body)
			|| !isSafeTranslatedBody(callback.body)
			|| !runtimeShaderHelperCallsAreSafe(callback.body, helperAdapters))
			return false;
		return true;
	}

	/**
		Accept a countdown callback only when every shader write maps to one
		field-specific descriptor and every camera operation is owned by that
		descriptor's proven target. A source-backed boolean preference may select
		between two fully declared filter lists; arbitrary local/dynamic filter
		arrays and unknown host members keep the callback rejected.
	*/
	static function isCompleteShaderCallback(method:HxcCompatFunction,
		callback:HxcCompatCallbackAdapter, descriptors:Array<Dynamic>,
		helperAdapters:Array<HxcCompatCallbackAdapter>, stateFields:Array<String>,
		stateInitializers:Array<HxcCompatStateInitializer>, functions:Array<HxcCompatFunction>,
		kind:String):Bool {
		if (method == null || callback == null || descriptors == null || descriptors.length == 0
			|| method.name == null || method.name.toLowerCase() != 'oncountdownstart'
			|| callback.body == null || (kind != 'stage' && kind != 'song-script'))
			return false;
		var source = stripComments(method.body == null ? '' : method.body);
		var preferenceSwitch = parseShaderFilterSwitch(translateBody(source),
			descriptors, stateInitializers, functions);
		if (preferenceSwitch == null
			&& new EReg('\\b(?:save|[A-Za-z_][A-Za-z0-9_]*Preferences|Preferences|ModuleHandler|modOptions)\\b'
				+ '|\\bswitch\\s*\\(', 'm').match(source))
			return false;
		if (preferenceSwitch != null && new EReg('\\b(?:[A-Za-z_][A-Za-z0-9_]*Preferences|Preferences|ModuleHandler|modOptions)\\b', 'm').match(source))
			return false;
		if (preferenceSwitch != null
			&& (countRegexMatches(source, '\\.\\s*filters\\b') != 1
				|| countRegexMatches(source, '\\.\\s*filters\\s*=') != 1
				|| new EReg('\\.\\s*filtersEnabled\\b', 'm').match(source)))
			return false;
		var hasShaderOperation = false;
		for (descriptor in descriptors) {
			if (descriptor == null || Reflect.field(descriptor, 'gate') != null)
				return false;
			var shaderValue:Dynamic = Reflect.field(descriptor, 'shaderField');
			var filterValue:Dynamic = Reflect.field(descriptor, 'filterField');
			var shaderField = shaderValue == null ? '' : Std.string(shaderValue);
			var filterField = filterValue == null ? '' : Std.string(filterValue);
			if (!isIdentifier(shaderField) || !isIdentifier(filterField))
				return false;
			if (new EReg('\\b' + EReg.escape(shaderField)
				+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(', 'm').match(source)) {
				hasShaderOperation = true;
				if (!runtimeShaderUniformWritesAreLiteral(source, descriptor, shaderField))
					return false;
			}
			var filterPattern = new EReg('\\b' + EReg.escape(filterField) + '\\b', 'm');
			if (filterPattern.match(source))
				hasShaderOperation = true;
		}
		if (preferenceSwitch == null && !runtimeShaderFilterWritesSafe(source, descriptors))
			return false;
		if (!hasShaderOperation)
			return false;
		// The translation must have consumed all donor shader fields and filter
		// arrays. This closes cases where an extra indirect reference was left
		// behind after only one recognized write.
		var residualBody = stripStringLiterals(callback.body);
		for (descriptor in descriptors) {
			var shader = EReg.escape(Std.string(Reflect.field(descriptor, 'shaderField')));
			var filter = EReg.escape(Std.string(Reflect.field(descriptor, 'filterField')));
			if (new EReg('\\b' + shader + '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\('
				+ '|\\b' + filter + '\\b|\\.\\s*filters(?:Enabled)?\\b', 'm').match(residualBody))
				return false;
		}
		if (!isSafeTranslatedBody(callback.body))
			return false;
		if (!runtimeShaderHelperCallsAreSafe(callback.body, helperAdapters))
			return false;
		var allowedHelpers:Array<String> = ['__hxcShaderHandles', 'hxcAssetRoot'];
		if (!moduleBodyUsesSafeRoots(callback.body, method.arguments, stateFields,
			shaderCallbackSafeHelperNames(helperAdapters, allowedHelpers)))
			return false;
		if (!runtimeCameraHelperAritiesSafe(callback.body))
			return false;
		return true;
	}

	/** Add only helper names whose own translated bodies passed HXC safety analysis. */
	static function shaderCallbackSafeHelperNames(
		helperAdapters:Array<HxcCompatCallbackAdapter>, names:Array<String>):Array<String> {
		var result = names == null ? [] : names.copy();
		if (helperAdapters != null)
			for (helper in helperAdapters)
				if (helper != null && helper.safe && helper.sourceName != null
					&& isIdentifier(helper.sourceName))
					appendUnique(result, helper.sourceName);
		return result;
	}

	/** Check exact filters arrays and the one-descriptor ownership of clears. */
	static function runtimeShaderFilterWritesSafe(source:String,
		descriptors:Array<Dynamic>):Bool {
		if (source == null || descriptors == null)
			return false;
		var pattern = new EReg('(?:PlayState\\s*\\.\\s*instance\\s*\\.|game\\s*\\.)?'
			+ '(camGame|camHUD|[A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*filters\\s*=', 'gm');
		var assignments = 0;
		var offset = 0;
		while (offset < source.length && pattern.match(source.substr(offset))) {
			var position = pattern.matchedPos();
			var target = pattern.matched(1);
			var absolute = offset + position.pos;
			var equals = source.indexOf('=', absolute + position.len - 1);
			var end = equals < 0 ? -1 : filterAssignmentEnd(source, equals + 1);
			if (equals < 0 || end < 0)
				return false;
			var valueEnd = end > equals && source.charAt(end - 1) == ';' ? end - 1 : end;
			var value = StringTools.trim(source.substr(equals + 1, valueEnd - equals - 1));
			var ownerCount = 0;
			var matchingDescriptor:Dynamic = null;
			if (value == '[]') {
				for (descriptor in descriptors)
					if (descriptorAllowsShaderCamera(descriptor, target)) {
						ownerCount++;
						matchingDescriptor = descriptor;
					}
				if (ownerCount != 1)
					return false;
			} else {
				var filterMatch = new EReg('^\\[\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\]$', 'm');
				if (!filterMatch.match(value))
					return false;
				var filterField = filterMatch.matched(1);
				for (descriptor in descriptors)
					if (Std.string(Reflect.field(descriptor, 'filterField')) == filterField
						&& descriptorAllowsShaderCamera(descriptor, target)) {
						ownerCount++;
						matchingDescriptor = descriptor;
					}
				if (ownerCount != 1)
					return false;
			}
			if (matchingDescriptor == null)
				return false;
			assignments++;
			offset = end;
		}
		var allAssignments = countRegexMatches(source,
			'\\b[A-Za-z_][A-Za-z0-9_.]*\\s*\\.\\s*filters\\s*=');
		if (assignments != allAssignments)
			return false;
		// filtersEnabled is safe only if exactly one descriptor owns the target.
		var enabled = new EReg('(?:PlayState\\s*\\.\\s*instance\\s*\\.|game\\s*\\.)?'
			+ '([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*filtersEnabled\\s*=\\s*(true|false)', 'gm');
		offset = 0;
		while (offset < source.length && enabled.match(source.substr(offset))) {
			var position = enabled.matchedPos();
			var target = enabled.matched(1);
			if (shaderDescriptorTargetCount(descriptors, target) != 1)
				return false;
			offset += position.pos + position.len;
		}
		return true;
	}

	static function descriptorAllowsShaderCamera(descriptor:Dynamic, camera:String):Bool {
		if (descriptor == null || !isIdentifier(camera))
			return false;
		var dynamicCamera:Dynamic = Reflect.field(descriptor, 'dynamicCameraField');
		if (dynamicCamera != null && Std.string(dynamicCamera) == camera)
			return true;
		var cameras:Dynamic = Reflect.field(descriptor, 'cameras');
		if (cameras != null && Std.isOfType(cameras, Array))
			for (candidate in (cast cameras:Array<Dynamic>))
				if (candidate != null && Std.string(candidate) == camera)
					return true;
		return false;
	}

	/** The native camera bridge accepts exactly its three positional arguments. */
	static function runtimeCameraHelperAritiesSafe(source:String):Bool {
		if (source == null)
			return false;
		var call = new EReg('\\btweenCameraToPosition\\s*\\(', 'g');
		var offset = 0;
		while (offset < source.length && call.match(source.substr(offset))) {
			var position = call.matchedPos();
			var open = offset + position.pos + position.len - 1;
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0 || splitTopLevel(source.substr(open + 1, close - open - 1), ',').length > 3)
				return false;
			offset = close + 1;
		}
		return true;
	}

	/**
		V-Slice callers may include an easing callback with a zero-duration camera
		move. The native helper performs the move immediately in that case, so the
		easing value cannot affect its result. Drop only this pure, exact no-op
		argument pair; calls with nonzero durations or another expression retain
		their authored arity and remain outside the bounded adapter.
	*/
	static function lowerZeroDurationCameraEaseArgument(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = new StringBuf();
		var call = new EReg('\\btweenCameraToPosition\\s*\\(', 'g');
		var offset = 0;
		while (offset < source.length && call.match(source.substr(offset))) {
			var position = call.matchedPos();
			var absolute = offset + position.pos;
			var open = source.indexOf('(', absolute);
			var close = matchingDelimiter(source, open, '(', ')');
			if (open < 0 || close < 0) {
				output.add(source.substr(offset));
				return output.toString();
			}
			var arguments = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
			if (arguments.length == 4
				&& new EReg('^\\+?0(?:\\.0*)?(?:[eE][+-]?[0-9]+)?$', 'm')
					.match(StringTools.trim(arguments[2]))
				&& (StringTools.trim(arguments[3]) == 'FlxEase.instant'
					|| StringTools.trim(arguments[3]) == 'flixel.tweens.FlxEase.instant')) {
				output.add(source.substr(offset, open - offset + 1));
				output.add(StringTools.trim(arguments[0]) + ', '
					+ StringTools.trim(arguments[1]) + ', '
					+ StringTools.trim(arguments[2]) + ')');
				offset = close + 1;
			} else {
				var end = close + 1;
				output.add(source.substr(offset, end - offset));
				offset = end;
			}
		}
		output.add(source.substr(offset));
		return output.toString();
	}

	/** Match every shader uniform write, accepting only descriptor-declared names
	 * and literal scalar values. Dynamic donor expressions remain diagnostics. */
	static function runtimeShaderUniformWritesAreLiteral(source:String,
		descriptor:Dynamic, shaderField:String):Bool {
		if (source == null || descriptor == null || !isIdentifier(shaderField))
			return false;
		var uniformsValue = Reflect.field(descriptor, 'uniforms');
		var uniforms:Array<Dynamic> = uniformsValue != null && Std.isOfType(uniformsValue, Array)
			? cast uniformsValue : [];
		var callStart = new EReg('\\b' + EReg.escape(shaderField)
			+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(', 'g');
		var writeCount = 0;
		var offset = 0;
		while (offset < source.length && callStart.match(source.substr(offset))) {
			var position = callStart.matchedPos();
			var absolute = offset + position.pos;
			var open = source.indexOf('(', absolute);
			var close = matchingDelimiter(source, open, '(', ')');
			if (open < 0 || close < 0)
				return false;
			var arguments = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
			if (arguments.length != 2)
				return false;
			var nameMatch = new EReg('^["\\\']([A-Za-z_][A-Za-z0-9_]*)["\\\']$', 'm');
			var uniform = StringTools.trim(arguments[0]);
			var value = StringTools.trim(arguments[1]);
			if (!nameMatch.match(uniform))
				return false;
			var uniformName = nameMatch.matched(1);
			var declared = false;
			for (candidate in uniforms)
				if (candidate != null && Std.string(candidate) == uniformName) {
					declared = true;
					break;
				}
			var scalar = new EReg('^(?:[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][-+]?[0-9]+)?|true|false)$', 'm');
			if (!declared || !scalar.match(value))
				return false;
			writeCount++;
			offset = close + 1;
		}
		return writeCount > 0;
	}

	/** A stage shader callback cannot call an unsafe local helper implicitly. */
	static function runtimeShaderHelperCallsAreSafe(source:String,
		helperAdapters:Array<HxcCompatCallbackAdapter>):Bool {
		if (source == null)
			return false;
		if (helperAdapters == null)
			return true;
		for (helper in helperAdapters) {
			if (helper == null || helper.sourceName == null || helper.sourceName == '')
				continue;
			var bareCall = new EReg('(?:^|[^A-Za-z0-9_.])' + EReg.escape(helper.sourceName)
				+ '\\s*\\(', 'm');
			if (bareCall.match(source) && !helper.safe)
				return false;
		}
		return true;
	}

	/**
		Recognize an exact source-backed boolean choice of camera filters. The
		array entries must all name declared shader filter fields for that camera;
		an unrelated switch, variable use, or option source keeps the callback
		unsupported. The two authored array orders are preserved below.
	*/
	static function parseShaderFilterSwitch(source:String, descriptors:Array<Dynamic>,
		stateInitializers:Array<HxcCompatStateInitializer>,
		functions:Array<HxcCompatFunction>):HxcShaderFilterSwitch {
		if (source == null || descriptors == null || descriptors.length == 0)
			return null;
		var statement = new EReg('\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*switch\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\.([A-Za-z_][A-Za-z0-9_]*)\\s*\\)\\s*\\{\\s*case\\s+(true|false)\\s*:\\s*\\[([^\\[\\]{}]*)\\]\\s*;\\s*case\\s+(true|false)\\s*:\\s*\\[([^\\[\\]{}]*)\\]\\s*;?\\s*\\}', 'm');
		if (!statement.match(source))
			return null;
		var position = statement.matchedPos();
		var variable = statement.matched(1);
		var saveField = statement.matched(2);
		var preferenceField = statement.matched(3);
		var firstCase = statement.matched(4);
		var firstList = statement.matched(5);
		var secondCase = statement.matched(6);
		var secondList = statement.matched(7);
		if (firstCase == secondCase || countRegexMatches(source, '\\bswitch\\s*\\(') != 1)
			return null;
		var sourceBacked = false;
		if (stateInitializers != null)
			for (initializer in stateInitializers)
				if (initializer != null && initializer.name == saveField
					&& StringTools.trim(initializer.value) == '__hxcStore.getSave()')
					sourceBacked = true;
		if (!sourceBacked && functions != null)
			for (method in functions)
				if (method != null && method.name != null && method.name.toLowerCase() == 'new')
					for (part in splitTopLevel(method.body == null ? '' : method.body, ';'))
						if (compactExpression(translateBody(part, 'new', []))
							== saveField + '=__hxcStore.getSave()')
							sourceBacked = true;
		if (!sourceBacked)
			return null;
		var assignment = new EReg('\\bHxcCompatRuntime\\.assignFilters\\s*\\(\\s*(?:PlayState\\.instance\\.)?(camGame|camHUD)\\s*,\\s*'
			+ EReg.escape(variable) + '\\s*\\)', 'm');
		if (!assignment.match(source)
			|| countRegexMatches(source, '\\bHxcCompatRuntime\\.assignFilters\\s*\\(') != 1
			|| countRegexMatches(source, '\\b' + EReg.escape(variable) + '\\b') != 2)
			return null;
		var camera = assignment.matched(1);
		var firstFilters = parseShaderFilterList(firstList, descriptors, camera);
		var secondFilters = parseShaderFilterList(secondList, descriptors, camera);
		if (firstFilters == null || secondFilters == null)
			return null;
		return {
			variable: variable,
			saveField: saveField,
			preferenceField: preferenceField,
			camera: camera,
			trueFilters: firstCase == 'true' ? firstFilters : secondFilters,
			falseFilters: firstCase == 'false' ? firstFilters : secondFilters,
			start: position.pos,
			length: position.len
		};
	}

	static function parseShaderFilterList(source:String, descriptors:Array<Dynamic>,
		camera:String):Array<String> {
		var result:Array<String> = [];
		if (source == null)
			return null;
		if (StringTools.trim(source) == '')
			return result;
		for (part in source.split(',')) {
			var field = StringTools.trim(part);
			if (!isIdentifier(field) || result.indexOf(field) >= 0)
				return null;
			var owners = 0;
			for (descriptor in descriptors)
				if (descriptor != null && Std.string(Reflect.field(descriptor, 'filterField')) == field
					&& descriptorAllowsShaderCamera(descriptor, camera))
					owners++;
			if (owners != 1)
				return null;
			result.push(field);
		}
		return result;
	}

	static function shaderFilterHandleList(fields:Array<String>, descriptors:Array<Dynamic>,
		camera:String):String {
		var values:Array<String> = [];
		for (field in fields)
			for (descriptor in descriptors)
				if (descriptor != null && Std.string(Reflect.field(descriptor, 'filterField')) == field
					&& descriptorAllowsShaderCamera(descriptor, camera)) {
					values.push(shaderOperationHandle(descriptor, descriptors.length > 1));
					break;
				}
		return '[' + values.join(', ') + ']';
	}

	/** Lower only per-field shader operations which the opaque native handles expose. */
	static function translateRuntimeShaderOperations(source:String,
		descriptors:Array<Dynamic>,
		stateInitializers:Array<HxcCompatStateInitializer>,
		functions:Array<HxcCompatFunction>):String {
		if (source == null || descriptors == null || descriptors.length == 0)
			return source == null ? '' : source;
		var output = source;
		for (descriptor in descriptors) {
			if (descriptor == null)
				continue;
			var shaderValue:Dynamic = Reflect.field(descriptor, 'shaderField');
			var filterValue:Dynamic = Reflect.field(descriptor, 'filterField');
			var shaderField = shaderValue == null ? '' : Std.string(shaderValue);
			var filterField = filterValue == null ? '' : Std.string(filterValue);
			if (!isIdentifier(shaderField) || !isIdentifier(filterField))
				continue;
			var handle = shaderOperationHandle(descriptor, descriptors.length > 1);
			var uniformCall = new EReg('\\b' + EReg.escape(shaderField)
				+ '\\s*\\.\\s*set(?:Float|Int|Bool)\\s*\\(\\s*(["\\\'])([^"\\\']+)\\1\\s*,\\s*([^;\\n]+)\\)', 'g');
			output = uniformCall.replace(output,
				'HxcCompatRuntime.setShaderUniform(' + handle + ', "$2", $3)');

			for (camera in shaderDescriptorTargets(descriptor)) {
				var cameraField:Dynamic = Reflect.field(camera, 'field');
				var cameraName:Dynamic = Reflect.field(camera, 'name');
				var cameraToken = cameraField != null && Std.string(cameraField) != ''
					? Std.string(cameraField) : (cameraName == null ? '' : Std.string(cameraName));
				if (!isIdentifier(cameraToken))
					continue;
				var cameraExpression = cameraField != null && Std.string(cameraField) != ''
					? cameraToken : quote(cameraToken);
				var target = '(?:PlayState\\s*\\.\\s*instance\\s*\\.|game\\s*\\.\\s*)?'
					+ EReg.escape(cameraToken);
				var assignedFilter = new EReg('HxcCompatRuntime\\s*\\.\\s*assignFilters\\s*\\(\\s*'
					+ target + '\\s*,\\s*\\[\\s*' + EReg.escape(filterField) + '\\s*\\]\\s*\\)', 'g');
				output = assignedFilter.replace(output,
					'HxcCompatRuntime.bindShaderFilter(PlayState.instance, ' + handle + ', '
					+ cameraExpression + ', true)');
				// Clearing a camera is only attributable to this descriptor when it is
				// the sole shader graph allowed on that target.
				if (shaderDescriptorTargetCount(descriptors, cameraToken) == 1) {
					var assignedClear = new EReg('HxcCompatRuntime\\s*\\.\\s*assignFilters\\s*\\(\\s*'
						+ target + '\\s*,\\s*\\[\\s*\\]\\s*\\)', 'g');
					output = assignedClear.replace(output,
						'HxcCompatRuntime.bindShaderFilter(PlayState.instance, ' + handle + ', '
						+ cameraExpression + ', false)');
					var enabledPattern = new EReg(target + '\\s*\\.\\s*filtersEnabled\\s*=\\s*(true|false)', 'g');
					output = enabledPattern.replace(output,
						'HxcCompatRuntime.setShaderEnabled(' + handle + ', $1)');
				}
			}
			var preferenceGuard:Dynamic = Reflect.field(descriptor, 'preferenceGuard');
			if (preferenceGuard != null
				&& Reflect.field(preferenceGuard, 'sourceBacked') == true) {
				var saveField:Dynamic = Reflect.field(preferenceGuard, 'saveField');
				var preferenceField:Dynamic = Reflect.field(preferenceGuard, 'field');
				if (saveField != null && preferenceField != null
					&& isIdentifier(Std.string(saveField)) && isIdentifier(Std.string(preferenceField))) {
					var guard = new EReg('\\bif\\s*\\(\\s*' + EReg.escape(Std.string(saveField))
						+ '\\s*\\.\\s*' + EReg.escape(Std.string(preferenceField)) + '\\s*\\)', 'g');
					output = guard.replace(output, 'if (HxcCompatRuntime.preferenceEnabled('
						+ Std.string(saveField) + ', ' + quote(Std.string(preferenceField)) + '))');
				}
			}
		}
		var filterSwitch = parseShaderFilterSwitch(output, descriptors, stateInitializers, functions);
		if (filterSwitch != null) {
			var expression = 'var ' + filterSwitch.variable
				+ ' = (HxcCompatRuntime.preferenceEnabled(' + filterSwitch.saveField + ', '
				+ quote(filterSwitch.preferenceField) + ') ? '
				+ shaderFilterHandleList(filterSwitch.trueFilters, descriptors, filterSwitch.camera) + ' : '
				+ shaderFilterHandleList(filterSwitch.falseFilters, descriptors, filterSwitch.camera) + ');';
			output = output.substr(0, filterSwitch.start) + expression
				+ output.substr(filterSwitch.start + filterSwitch.length);
		}
		return output;
	}

	/** Static/dynamic targets proven by a literal filter assignment. */
	static function shaderDescriptorTargets(descriptor:Dynamic):Array<Dynamic> {
		var targets:Array<Dynamic> = [];
		if (descriptor == null)
			return targets;
		var cameras:Dynamic = Reflect.field(descriptor, 'cameras');
		if (cameras != null && Std.isOfType(cameras, Array))
			for (camera in (cast cameras:Array<Dynamic>))
				if (camera != null && (Std.string(camera) == 'camGame' || Std.string(camera) == 'camHUD'))
					targets.push({name: Std.string(camera), field: ''});
		var dynamicCamera:Dynamic = Reflect.field(descriptor, 'dynamicCameraField');
		if (dynamicCamera != null && isIdentifier(Std.string(dynamicCamera)))
			targets.push({name: '', field: Std.string(dynamicCamera)});
		return targets;
	}

	static function shaderDescriptorTargetCount(descriptors:Array<Dynamic>, camera:String):Int {
		var count = 0;
		if (descriptors == null || !isIdentifier(camera))
			return count;
		for (descriptor in descriptors)
			for (target in shaderDescriptorTargets(descriptor)) {
				var field:Dynamic = Reflect.field(target, 'field');
				var name:Dynamic = Reflect.field(target, 'name');
				if ((field != null && Std.string(field) == camera)
					|| (name != null && Std.string(name) == camera)) {
					count++;
					break;
				}
			}
		return count;
	}

	static function shaderOperationHandle(descriptor:Dynamic, multi:Bool):String {
		if (!multi)
			return '__hxcShaderHandle';
		var field = Std.string(Reflect.field(descriptor, 'shaderField'));
		return 'HxcCompatRuntime.ensureShaderHandle(PlayState.instance, __hxcShaderHandles, '
			+ quote(field) + ', ' + shaderDescriptorLiteral(descriptor) + ', hxcAssetRoot)';
	}

	/** Emit a data-only helper for one verified shader pulse descriptor. */
	static function shaderPulseHelperSource(descriptor:Dynamic, handleExpression:String):String {
		if (descriptor == null || handleExpression == null || handleExpression == '')
			return '';
		var pulseHelper:Dynamic = Reflect.field(descriptor, 'pulseHelper');
		if (pulseHelper == null || !isIdentifier(Std.string(pulseHelper)))
			return '';
		var pulseArguments:Array<String> = [];
		var rawPulseArguments:Dynamic = Reflect.field(descriptor, 'pulseArguments');
		if (rawPulseArguments != null && Std.isOfType(rawPulseArguments, Array))
			for (argument in (cast rawPulseArguments:Array<Dynamic>)) {
				if (argument == null || !isIdentifier(Std.string(argument)))
					return '';
				pulseArguments.push(Std.string(argument));
			}
		var lines:Array<String> = ['function ' + Std.string(pulseHelper)
			+ '(' + pulseArguments.join(', ') + ') {'];
		var soundParameter:Dynamic = Reflect.field(descriptor, 'pulseSoundParameter');
		if (soundParameter != null && isIdentifier(Std.string(soundParameter))) {
			var soundName = Std.string(soundParameter);
			// HXC calls can supply a numeric value despite a nominal String
			// parameter. Source behavior only plays a path for string values.
			lines.push('\tif (HxcCompatRuntime.isNonemptyString(' + soundName + '))');
			lines.push('\t\tHxcCompatRuntime.freeplayPlaySound(hxcPaths.sound(' + soundName + '));');
		}
		var holdDuration:Dynamic = Reflect.field(descriptor, 'pulseHoldDuration');
		var holdExpression = holdDuration == null || Std.string(holdDuration) == ''
			? '0' : Std.string(holdDuration);
		var pulseEase:Dynamic = Reflect.field(descriptor, 'pulseEase');
		var easeExpression = pulseEase == null || Std.string(pulseEase) == ''
			? 'FlxEase.circOut' : 'FlxEase.' + Std.string(pulseEase);
		var pulseUniform:Dynamic = Reflect.field(descriptor, 'pulseUniform');
		var uniformExpression = pulseUniform == null || Std.string(pulseUniform) == ''
			? '"alpha"' : quote(Std.string(pulseUniform));
		lines.push('\tHxcCompatRuntime.pulseShader(' + handleExpression + ', 0, 1, '
			+ numberLiteral(Reflect.field(descriptor, 'pulseDuration'), 0.5)
			+ ', ' + holdExpression + ', ' + easeExpression + ', ' + uniformExpression + ');');
		lines.push('}');
		return lines.join('\n');
	}

	/** Emit a small HScript object literal, never donor class code. */
	static function shaderDescriptorLiteral(descriptor:Dynamic):String {
		if (descriptor == null)
			return 'null';
		var shaderName = Reflect.field(descriptor, 'shaderName');
		var cameras:Dynamic = Reflect.field(descriptor, 'cameras');
		var output = '{shaderName: ' + quote(shaderName == null ? '' : Std.string(shaderName))
			+ ', cameras: [';
		if (cameras != null && Std.isOfType(cameras, Array)) {
			var first = true;
			for (camera in (cast cameras:Array<Dynamic>)) {
				if (!first)
					output += ', ';
				first = false;
				output += quote(camera == null ? '' : Std.string(camera));
			}
		}
		output += ']';
		var dynamicCamera:Dynamic = Reflect.field(descriptor, 'dynamicCameraField');
		if (dynamicCamera != null && isIdentifier(Std.string(dynamicCamera)))
			output += ', cameraRefs: [' + Std.string(dynamicCamera) + ']';
		var uniforms:Dynamic = Reflect.field(descriptor, 'uniforms');
		output += ', uniforms: [';
		if (uniforms != null && Std.isOfType(uniforms, Array)) {
			var firstUniform = true;
			for (uniform in (cast uniforms:Array<Dynamic>)) {
				if (uniform == null)
					continue;
				if (!firstUniform)
					output += ', ';
				firstUniform = false;
				output += quote(Std.string(uniform));
			}
		}
		output += ']';
		var field = Reflect.field(descriptor, 'shaderField');
		if (field != null && Std.string(field) != '')
			output += ', shaderField: ' + quote(Std.string(field));
		var filter = Reflect.field(descriptor, 'filterField');
		if (filter != null && Std.string(filter) != '')
			output += ', filterField: ' + quote(Std.string(filter));
		output += ', initialEnabled: ' + (Reflect.field(descriptor, 'initialEnabled') == false ? 'false' : 'true');
		if (Reflect.field(descriptor, 'deferCameraBinding') == true)
			output += ', deferCameraBinding: true';
		var pulse = Reflect.field(descriptor, 'pulseHelper');
		if (pulse != null && Std.string(pulse) != '') {
			output += ', pulseHelper: ' + quote(Std.string(pulse));
			output += ', pulseDuration: ' + numberLiteral(Reflect.field(descriptor, 'pulseDuration'), 0.5);
		}
		var gate:Dynamic = Reflect.field(descriptor, 'gate');
		if (gate != null) {
			output += ', gate: {bucket: ' + quote(Std.string(Reflect.field(gate, 'bucket')))
				+ ', field: ' + quote(Std.string(Reflect.field(gate, 'field')))
				+ ', defaultValue: ' + (Reflect.field(gate, 'defaultValue') == true ? 'true' : 'false') + '}';
		}
		return output + '}';
	}

	/** Translate actor-local fields and preserve native super animation calls. */
	static function translateCharacterBody(source:String, ?methodName:String,
		?arguments:Array<String>):String {
		var loweredName = methodName == null ? '' : methodName.toLowerCase();
		// DDTO++'s game-over hook is a data declaration, not a general donor
		// animation graph.  Lower the literal atlas/animation specification to the
		// native Character bridge before the ordinary field pass can mistake object
		// keys such as `flipX` for actor fields.
		if (loweredName == 'addgameoverassets') {
			var gameOverAssets = translateCharacterGameOverAssets(source);
			if (gameOverAssets != null && gameOverAssets != '')
				return gameOverAssets;
		}
		// Keep raw Sparrow construction visible long enough for the bounded game-over
		// overlay recognizer; lower the remaining generic V-Slice objects after it
		// has claimed its exact operation.
		// A character's explicit receiver refers to the live native actor for
		// shared FlxSprite/Character fields. Preserve that receiver before the
		// ordinary HXC syntax pass removes `this.` from script-owned fields.
		var actorSource = source;
		for (field in ['x', 'y', 'idleSuffix', 'isPixel', 'originalPosition', 'characterOrigin', 'zIndex',
			'offset', 'shader', 'antialiasing'])
			actorSource = new EReg('\\bthis\\s*\\.\\s*' + field + '\\b', 'g')
				.replace(actorSource, 'hxcCharacter().' + field);
		for (method in ['resetPosition', 'playAnimation', 'playSingAnimation'])
			actorSource = new EReg('\\bthis\\s*\\.\\s*' + method + '\\s*\\(', 'g')
				.replace(actorSource, 'hxcCharacter().' + method + '(');
		var output = translateBody(actorSource, methodName, arguments, true, true);
		// CharacterType is a donor enum; the native bridge exposes the live slot as
		// a stable string and never fabricates a foreign enum object.
		output = new EReg('\\bcharacterType\\b', 'g')
			.replace(output, 'HxcCompatRuntime.characterType(hxcCharacter())');
		// `this.animation` loses its qualifier in translateBody; bare reads route
		// back to the actor. The field pattern excludes dot-prefixed uses, so
		// other sprites' animation controllers (exSpikes.animation...) stay intact.
		var actorFields = ['color', 'flipX', 'holdTimer', 'isPlayer', 'alpha', 'visible', 'animation'];
		// Bare inherited fields have the same receiver in Haxe. A method-local
		// declaration shadows it, so leave that spelling alone when present.
		for (field in ['originalPosition', 'characterOrigin', 'zIndex'])
			if ((arguments == null || arguments.indexOf(field) < 0)
				&& !new EReg('\\b(?:var|final)\\s+' + field + '\\b', 'm').match(stripComments(source)))
				actorFields.push(field);
		if ((arguments == null || arguments.indexOf('isPixel') < 0)
			&& !new EReg('\\b(?:var|final)\\s+isPixel\\b', 'm').match(stripComments(source)))
			actorFields.push('isPixel');
		if (loweredName == 'getscreenposition')
			for (field in ['flipY', 'width', 'height', 'frameWidth', 'frameHeight', 'scale'])
				actorFields.push(field);
		for (field in actorFields) {
			var fieldPattern = new EReg('(^|[^A-Za-z0-9_.])' + field + '\\b', 'gm');
			output = fieldPattern.replace(output, '$1hxcCharacter().' + field);
		}
		// HXC exposes the active animation's offsets as a two-element array.  The
		// native Character keeps a name-keyed map, so route only the two indexed
		// reads used by the donor screen-position convention through its adapter.
		output = new EReg('\\banimOffsets\\s*\\[\\s*0\\s*\\]', 'g')
			.replace(output, 'HxcCompatRuntime.characterAnimationOffset(hxcCharacter(), 0)');
		output = new EReg('\\banimOffsets\\s*\\[\\s*1\\s*\\]', 'g')
			.replace(output, 'HxcCompatRuntime.characterAnimationOffset(hxcCharacter(), 1)');
		output = new EReg('\\bglobalOffsets\\s*\\[\\s*0\\s*\\]', 'g')
			.replace(output, 'HxcCompatRuntime.characterGlobalOffset(hxcCharacter(), 0)');
		output = new EReg('\\bglobalOffsets\\s*\\[\\s*1\\s*\\]', 'g')
			.replace(output, 'HxcCompatRuntime.characterGlobalOffset(hxcCharacter(), 1)');
		output = translateCharacterDeathOverlay(output);
		output = lowerHxcNativeObjects(output);
		return output;
	}

	/**
		Lower the small, engine-neutral overlay surface used by HXC game-over
		character hooks.  Imported scripts receive opaque native handles only; atlas
		loading, display-list ownership, camera movement, and teardown remain on
		GameOverSubstate.  The patterns intentionally depend on operation shape
		(death/overlay handle, Sparrow construction, camera/window call), never on a
		donor id or chart name.
	*/
	static function translateCharacterDeathOverlay(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		// Character companions also use createSparrow for gameplay effects (for
		// example an opponent's floor spikes). Only create an opaque game-over
		// handle when the assigned variable itself has an overlay/death role;
		// ordinary character sprites must flow to lowerHxcNativeObjects below.
		var overlay = '([A-Za-z_][A-Za-z0-9_]*(?:death[A-Za-z0-9_]*|overlay[A-Za-z0-9_]*)|(?:death|overlay)[A-Za-z0-9_]*)';
		output = new EReg('((?:var\\s+)?' + overlay + ')'
			+ '(?:\\s*:\\s*[^=;\\n]+)?\\s*=\\s*'
			+ '(?:[A-Za-z_][A-Za-z0-9_]*\\.)?createSparrow\\s*'
			+ '\\([^,]+,\\s*[^,]+,\\s*([^,)]+)\\)', 'gi')
			.replace(output, '$1 = HxcCompatRuntime.gameOverCreateOverlay(hxcAssetRoot, $3)');
		output = new EReg('\\bApplication\\s*\\.\\s*current\\s*\\.\\s*window\\s*'
			+ '\\s*\\.\\s*close\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverCloseWindow()');
		output = new EReg('\\bGameOverSubState\\s*\\.\\s*instance\\s*'
			+ '\\s*\\.\\s*resetCameraZoom\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverResetCameraZoom()');
		output = new EReg('\\bGameOverSubstate\\s*\\.\\s*instance\\s*'
			+ '\\s*\\.\\s*resetCameraZoom\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverResetCameraZoom()');
		output = new EReg('\\bGameOverSubState\\s*\\.\\s*instance\\s*'
			+ '\\s*\\.\\s*add\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverAddOverlay($1)');
		output = new EReg('\\bGameOverSubstate\\s*\\.\\s*instance\\s*'
			+ '\\s*\\.\\s*add\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverAddOverlay($1)');
		output = new EReg('\\bFlxG\\s*\\.\\s*state\\s*\\.\\s*subState\\s*\\.\\s*mustNotExit\\s*'
			+ '=\\s*([^;\\n]+)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverSetMustNotExit($1)');
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*tweenCameraToPosition\\s*'
			+ '\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*getGraphicMidpoint\\s*\\(\\s*\\)\\s*\\.\\s*x\\s*,'
			+ '\\s*\\1\\s*\\.\\s*getGraphicMidpoint\\s*\\(\\s*\\)\\s*\\.\\s*y\\s*,'
			+ '\\s*([^,)]+)\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.gameOverTweenCameraToOverlay($1, $2)');
		// HXC's Position object is donor-only; the overlay needs the live native
		// actor position with the same visual meaning.
		output = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*originalPosition\\s*\\.\\s*([xy])\\b', 'g')
			.replace(output, '$1.$2');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*screenCenter\\s*\\(\\s*\\)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverCenterOverlay($1)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*'
			+ '\\(\\s*([^,]+),\\s*([^,]+),\\s*([^,]+),\\s*([^,)]+)\\s*\\)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverAddOverlayAnimation($1, $2, $3, $4, $5)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*animation\\s*\\.\\s*play\\s*'
			+ '\\(\\s*([^,)]+)(?:,\\s*[^)]*)?\\)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverPlayOverlayAnimation($1, $2)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*alpha\\s*=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverSetOverlayAlpha($1, $2)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*visible\\s*=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverSetOverlayVisible($1, $2)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*x\\s*\\+=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverOffsetOverlay($1, $2, 0)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*x\\s*-=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverOffsetOverlay($1, -($2), 0)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*y\\s*\\+=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverOffsetOverlay($1, 0, $2)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*y\\s*-=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverOffsetOverlay($1, 0, -($2))');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*x\\s*=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverSetOverlayX($1, $2)');
		output = new EReg('\\b' + overlay + '\\s*\\.\\s*y\\s*=\\s*([^;\\n]+)', 'gi')
			.replace(output, 'HxcCompatRuntime.gameOverSetOverlayY($1, $2)');
		return output;
	}

	/**
		Lower the literal atlas animation shape used by imported game-over hooks.

		The parser deliberately accepts only a quoted Sparrow asset, an array of
		literal animation records, and literal offset adjustments.  This keeps the
		adapter generic across character packs without evaluating donor utility
		classes or arbitrary Haxe expressions.
	*/
	static function translateCharacterGameOverAssets(source:String):String {
		if (source == null || source == '')
			return null;
		var assetPath = firstString(source,
			'\\bPaths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		if (assetPath == '')
			assetPath = firstString(source,
				'\\bassetPath\\s*:\\s*["\\\']([^"\\\']+)["\\\']');
		if (assetPath == '')
			return null;
		var animationDeclaration = new EReg('\\b(?:var|final)\\s+animations\\s*=\\s*\\[', 'm');
		if (!animationDeclaration.match(source))
			return null;
		var declarationPos = animationDeclaration.matchedPos();
		var open = source.indexOf('[', declarationPos.pos);
		if (open < 0)
			return null;
		var close = matchingDelimiter(source, open, '[', ']');
		if (close < 0)
			return null;
		var records = collectCharacterAnimationRecords(source, open + 1, close);
		if (records.length == 0)
			return null;
		var xAdjust = characterGameOverOffset(source, 0);
		var yAdjust = characterGameOverOffset(source, 1);
		if (xAdjust == '' || yAdjust == '')
			return null;
		var output = 'HxcCompatRuntime.addCharacterAtlasAnimations(hxcCharacter(), '
			+ quote(assetPath) + ', [';
		var first = true;
		for (record in records) {
			var name = firstString(record, '\\bname\\s*:\\s*["\\\']([^"\\\']+)["\\\']');
			var prefix = firstString(record, '\\bprefix\\s*:\\s*["\\\']([^"\\\']+)["\\\']');
			if (name == '' || prefix == '')
				return null;
			var looped = firstString(record, '\\blooped\\s*:\\s*(true|false)');
			if (looped == '')
				looped = firstString(record, '\\bloop\\s*:\\s*(true|false)');
			if (looped == '')
				looped = 'false';
			var flipX = firstString(record, '\\bflipX\\s*:\\s*(true|false)');
			if (flipX == '')
				flipX = 'false';
			var flipY = firstString(record, '\\bflipY\\s*:\\s*(true|false)');
			if (flipY == '')
				flipY = 'false';
			var fps = firstString(record, '\\bfps\\s*:\\s*(-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))');
			if (fps == '')
				fps = '24';
			var recordAsset = firstString(record,
				'\\bassetPath\\s*:\\s*["\\\']([^"\\\']+)["\\\']');
			if (recordAsset == '')
				recordAsset = assetPath;
			var offsets = matchGroups(record,
				'\\boffsets\\s*:\\s*\\[\\s*(-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))\\s*,\\s*(-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))\\s*\\]');
			var offsetValue = offsets.length >= 2
				? '[' + offsets[0] + ', ' + offsets[1] + ']'
				: 'null';
			if (!first)
				output += ', ';
			first = false;
			output += '{name: ' + quote(name) + ', prefix: ' + quote(prefix)
				+ ', assetPath: ' + quote(recordAsset) + ', fps: ' + fps
				+ ', looped: ' + looped + ', flipX: ' + flipX + ', flipY: ' + flipY
				+ ', offsets: ' + offsetValue + '}';
		}
		return output + '], ' + xAdjust + ', ' + yAdjust + ', hxcAssetRoot);';
	}

	/** Return top-level anonymous records from an HXC array literal. */
	static function collectCharacterAnimationRecords(source:String, start:Int, end:Int):Array<String> {
		var output:Array<String> = [];
		var index = start;
		while (index < end) {
			var current = source.charAt(index);
			if (current == '{') {
				var close = matchingDelimiter(source, index, '{', '}');
				if (close < 0 || close > end)
					return [];
				output.push(source.substr(index, close - index + 1));
				index = close + 1;
			} else {
				index++;
			}
		}
		return output;
	}

	/** Parse one literal `anim.offsets[index] +/- number` adjustment. */
	static function characterGameOverOffset(source:String, index:Int):String {
		var groups = matchGroups(source,
			'\\banim\\s*\\.\\s*offsets\\s*\\[\\s*' + index
			+ '\\s*\\]\\s*([+-])\\s*(\\-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))');
		if (groups.length < 2)
			return '';
		var sign = groups[0] == '-' ? '-' : '';
		var number = groups[1];
		if (number != null && number.charAt(0) == '-')
			number = number.substr(1);
		return sign + number;
	}

	/** Reject donor-only roots while allowing the narrow actor surface above. */
	static function isSafeCharacterBody(source:String, ?methodName:String,
		?arguments:Array<String>):Bool {
		var translated = translateCharacterBody(source, methodName, arguments);
		if (unsupportedConstructs(translated).length > 0
			|| translated.indexOf('super.') >= 0 || translated.indexOf('this.') >= 0
			|| translated.indexOf('override function') >= 0
			|| translated.indexOf('public function') >= 0
			|| translated.indexOf('private function') >= 0
			|| translated.indexOf('protected function') >= 0)
			return false;
		// These donor classes mutate game-over/pause substate asset graphs which
		// the native Character bridge does not own. Their documented static suffix
		// fields are lowered above to HxcCompatRuntime; retain the broader donor
		// roots as explicit gaps while allowing that narrow audio-selection ABI.
		var gameOverAssetsSafe = methodName != null
			&& methodName.toLowerCase() == 'addgameoverassets'
			&& translateCharacterGameOverAssets(source) != null;
		var gameOverOverlaySafe = translated.indexOf('HxcCompatRuntime.gameOver') >= 0;
		// An authored texture warm-up can pass one literal image through the
		// manifest-scoped Paths proxy. Evaluating Paths.image decodes and caches
		// the owner's BitmapData before hxcCacheTexture receives it. Keep other
		// FunkinMemory/Paths operations behind the ordinary donor-root warning.
		var boundedTextureCache = new EReg('\\bFunkinMemory\\s*\\.\\s*cacheTexture\\s*\\(\\s*'
			+ 'Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\'][^"\\\']+["\\\']\\s*'
			+ '(?:,\\s*["\\\'][^"\\\']+["\\\']\\s*)?\\)\\s*\\)', 'g');
		var otherDonorCalls = boundedTextureCache.replace(source, '');
		// A death quote returns a sound path through the owner-scoped proxy.
		// Other Paths operations retain their existing explicit diagnostics.
		if (methodName != null && methodName.toLowerCase() == 'getdeathquote')
			otherDonorCalls = new EReg('\\bPaths\\s*\\.\\s*sound\\b', 'g')
				.replace(otherDonorCalls, 'hxcPaths.sound');
		for (root in ['FunkinMemory', 'FlxAnimationUtil', 'Paths'])
			if (new EReg('\\b' + root + '\\b', 'm').match(otherDonorCalls) && !gameOverAssetsSafe)
				return false;
		var donorSubstateMembers = new EReg('\\b(GameOverSubState|PauseSubState)\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\b', 'g');
		var offset = 0;
		while (offset < source.length && donorSubstateMembers.match(source.substr(offset))) {
			var owner = donorSubstateMembers.matched(1);
			var member = donorSubstateMembers.matched(2);
			if (owner == 'GameOverSubState') {
				if (member != 'musicSuffix' && member != 'blueBallSuffix'
					&& !(gameOverOverlaySafe && (member == 'instance'
						|| member == 'resetCameraZoom' || member == 'add')))
					return false;
			} else if (member != 'musicSuffix') {
				return false;
			}
			var position = donorSubstateMembers.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		return true;
	}

	/**
		Resolve character inheritance by class name inside the same donor
		characters tree. The traversal is bounded and read-only; an unresolved
		base simply leaves the wrapper's own diagnostics intact.
	*/
	static function collectCharacterInheritance(path:String, baseClass:String):HxcCompatInheritance {
		#if sys
		if (path == null || baseClass == null || StringTools.trim(baseClass) == '')
			return null;
		var normalized = StringTools.replace(path, '\\', '/');
		var marker = normalized.lastIndexOf('/characters/');
		var root = marker >= 0 ? normalized.substr(0, marker + '/characters'.length) : '';
		if (root == '' || !FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return null;
		var firstPath:{value:String} = {value: ''};
		var seenClasses:Map<String, Bool> = new Map();
		var stateDeclarations:Array<HxcCompatStateDeclaration> = [];
		var all = collectCharacterInheritanceFunctions(root, baseClass, seenClasses, 0, firstPath,
			stateDeclarations);
		return firstPath.value == '' ? null : {path: firstPath.value, functions: all,
			stateDeclarations: stateDeclarations};
		#else
		return null;
		#end
	}

	#if sys
	static function collectCharacterInheritanceFunctions(root:String, current:String,
		seenClasses:Map<String, Bool>, depth:Int, firstPath:{value:String},
		stateDeclarations:Array<HxcCompatStateDeclaration>):Array<HxcCompatCallbackAdapter> {
		var output:Array<HxcCompatCallbackAdapter> = [];
		if (current == null || StringTools.trim(current) == '' || depth >= 8)
			return output;
		var key = current.toLowerCase();
		if (seenClasses.exists(key))
			return output;
		seenClasses.set(key, true);
		var found = findCharacterClassFile(root, current, 0, {value: 0});
		if (found == null)
			return output;
		if (firstPath.value == '')
			firstPath.value = found.path;
		var clean = stripComments(found.source);
		var inheritedParent = firstString(clean,
			'\\bclass\\s+' + current + '\\s+extends\\s+([A-Za-z_][A-Za-z0-9_.]*)');
		// Walk ancestors once, then append the direct base. The wrapper's own
		// adapter is merged after this returned chain, giving ancestor -> base ->
		// wrapper order without replaying a parent at each loop level.
		for (item in collectCharacterInheritanceFunctions(root, inheritedParent,
			seenClasses, depth + 1, firstPath, stateDeclarations))
			output.push(item);
		for (declaration in collectStateDeclarations(clean))
			stateDeclarations.push(declaration);
		for (method in collectFunctions(clean)) {
			if (method == null || method.name.toLowerCase() == 'new')
				continue;
			var callbackName = lifecycleCallback(method.name);
			if (callbackName == '')
				callbackName = characterLifecycleCallback(method.name);
			var translated = translateCharacterBody(method.body, method.name, method.arguments);
			output.push({sourceName: method.name,
				canonicalName: callbackName == '' ? method.name : callbackName,
				arguments: method.arguments, argumentInfos: method.argumentInfos, body: translated,
				safe: kindOfCharacterMethod(method.name, callbackName)
					&& isSafeCharacterBody(method.body, method.name, method.arguments)});
		}
		return output;
	}
	#end

	static function kindOfCharacterMethod(name:String, callbackName:String):Bool {
		return callbackName != '' || !isHxcMetadataMethod(name);
	}

	#if sys
	static function findCharacterClassFile(root:String, className:String, depth:Int,
		budget:{value:Int}):HxcCompatCharacterFile {
		if (depth > 8 || budget.value++ > 512 || root == null || !FileSystem.exists(root))
			return null;
		var entries:Array<String> = [];
		try entries = FileSystem.readDirectory(root) catch (_:Dynamic) return null;
		entries.sort(function(a:String, b:String):Int return a < b ? -1 : (a > b ? 1 : 0));
		for (entry in entries) {
			var child = root + '/' + entry;
			try {
				if (FileSystem.isDirectory(child)) {
					var nested = findCharacterClassFile(child, className, depth + 1, budget);
					if (nested != null) return nested;
				} else if (entry.toLowerCase().endsWith('.hxc')) {
					var content = File.getContent(child);
					if (new EReg('\\bclass\\s+' + className + '\\b', 'm').match(stripComments(content)))
						return {path: child, source: content};
				}
			} catch (_:Dynamic) {}
		}
		return null;
	}
	#end

	static function callbackNames(callbacks:Array<HxcCompatCallbackAdapter>):Array<String> {
		var result:Array<String> = [];
		if (callbacks != null)
			for (callback in callbacks)
				appendUnique(result, callback.canonicalName);
		return result;
	}

	static function mergeCallbackAdapter(callbacks:Array<HxcCompatCallbackAdapter>, adapter:HxcCompatCallbackAdapter,
		prepend:Bool = false):Void {
		if (callbacks == null || adapter == null)
			return;
		for (existing in callbacks) {
			if (existing == null || existing.canonicalName != adapter.canonicalName)
				continue;
			if (prepend)
				existing.body = adapter.body + '\n' + existing.body;
			else
				existing.body += '\n' + adapter.body;
			existing.safe = existing.safe && adapter.safe;
			return;
		}
		callbacks.push(adapter);
	}

	/** Merge an inherited character method before the wrapper override. */
	static function mergeCharacterAdapter(callbacks:Array<HxcCompatCallbackAdapter>,
		helpers:Array<HxcCompatCallbackAdapter>, adapter:HxcCompatCallbackAdapter,
		?gaps:Array<String>):Void {
		if (adapter == null)
			return;
		if (adapter.canonicalName != null && adapter.canonicalName != ''
			&& (characterLifecycleCallback(adapter.sourceName) != ''
				|| lifecycleCallback(adapter.sourceName) != '')) {
			if (!adapter.safe) {
				if (gaps != null)
					appendUnique(gaps, adapter.sourceName);
				return;
			}
			for (existing in callbacks)
				if (existing != null && existing.canonicalName == adapter.canonicalName) {
					existing.body = adapter.body + '\n' + existing.body;
					return;
				}
			callbacks.push(adapter);
			return;
		}
		if (helpers == null || isHxcMetadataMethod(adapter.sourceName))
			return;
		if (!adapter.safe) {
			if (gaps != null)
				appendUnique(gaps, adapter.sourceName);
			return;
		}
		for (existing in helpers)
			if (existing != null && existing.sourceName == adapter.sourceName)
				return;
		helpers.push(adapter);
	}

	static function isHxcMetadataMethod(name:String):Bool {
		if (name == null)
			return true;
		switch (name.toLowerCase()) {
			case 'new' | 'handleevent' | 'gettitle' | 'geteventschema' | 'geticonpath' | 'issongnew'
				| 'fetchassetpaths' | 'listaltinstrumentalids' | 'jsonload' | 'changecharacter':
				return true;
			default:
				return false;
		}
	}

	/**
		Collect named Haxe methods without evaluating the donor source.  The HXC
		corpus uses ordinary balanced braces; a small scanner is more reliable than
		one regexp here because stage and character callbacks contain nested
		closures, switches, and object literals.
	*/
	static function collectFunctions(source:String):Array<HxcCompatFunction> {
		var result:Array<HxcCompatFunction> = [];
		if (source == null || source == '')
			return result;
		// A compact synthetic/ported class may place a constructor directly after
		// a field declaration (`var flag = true; function new()`). Treat the
		// semicolon as a declaration boundary too, otherwise constructor state is
		// skipped and a dynamic `active = flag` can be mistaken for a literal rule.
		var expression = new EReg('(?:^|[\\n\\r{};])\\s*(?:(?:public|private|protected|static|override|inline|macro)\\s+)*function\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', 'm');
		var offset = 0;
		while (offset < source.length) {
			var rest = source.substr(offset);
			if (!expression.match(rest))
				break;
			var matched = expression.matchedPos();
			var absolute = offset + matched.pos;
			var name = expression.matched(1);
			var open = source.indexOf('(', absolute);
			if (open < 0)
				break;
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0)
				break;
			var bodyStart = close + 1;
			while (bodyStart < source.length && isWhitespace(source.charAt(bodyStart)))
				bodyStart++;
			// Haxe permits a return type between the argument list and the body.
			if (bodyStart < source.length && source.charAt(bodyStart) == ':') {
				bodyStart++;
				while (bodyStart < source.length && source.charAt(bodyStart) != '{'
					&& source.charAt(bodyStart) != '=' && source.charAt(bodyStart) != ';')
					bodyStart++;
			}
			if (bodyStart < source.length && source.charAt(bodyStart) == '=') {
				// Arrow functions are not lifecycle callbacks themselves.  Keep the
				// method discoverable but do not guess an executable block.
				var arrowEnd = source.indexOf(';', bodyStart);
				if (arrowEnd < 0)
					arrowEnd = source.length;
				result.push({name: name, arguments: parseArgumentNames(source.substr(open + 1, close - open - 1)),
					argumentInfos: parseArgumentInfos(source.substr(open + 1, close - open - 1)),
					body: 'return ' + StringTools.trim(source.substr(bodyStart + 1, arrowEnd - bodyStart - 1)) + ';'});
				offset = arrowEnd + 1;
				continue;
			}
			if (bodyStart >= source.length || source.charAt(bodyStart) != '{') {
				offset = close + 1;
				continue;
			}
			var bodyEnd = matchingDelimiter(source, bodyStart, '{', '}');
			if (bodyEnd < 0)
				break;
			result.push({
				name: name,
				arguments: parseArgumentNames(source.substr(open + 1, close - open - 1)),
				argumentInfos: parseArgumentInfos(source.substr(open + 1, close - open - 1)),
				body: source.substr(bodyStart + 1, bodyEnd - bodyStart - 1)
			});
			offset = bodyEnd + 1;
		}
		return result;
	}

	static function parseArgumentNames(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || StringTools.trim(source) == '')
			return result;
		for (piece in splitTopLevel(source, ',')) {
			var value = StringTools.trim(piece);
			if (value.startsWith('?'))
				value = value.substr(1);
			var colon = value.indexOf(':');
			var equals = value.indexOf('=');
			var cut = value.length;
			if (colon >= 0 && colon < cut)
				cut = colon;
			if (equals >= 0 && equals < cut)
				cut = equals;
			value = StringTools.trim(value.substr(0, cut));
			if (value != '' && value != '...')
				result.push(value);
		}
		return result;
	}

	/**
		Parse the same parameter list as parseArgumentNames while keeping the
		donor's optionality markers. `?name` and `name = default` both become
		optional so the generated HScript declares them with hscript's `?`
		prefix and callers may omit them. Literal defaults are preserved for
		the null-guard prologue; non-literal defaults stay null-filled rather
		than being replayed out of context.
	*/
	static function parseArgumentInfos(source:String):Array<HxcCompatArgumentInfo> {
		var result:Array<HxcCompatArgumentInfo> = [];
		if (source == null || StringTools.trim(source) == '')
			return result;
		for (piece in splitTopLevel(source, ',')) {
			var value = StringTools.trim(piece);
			if (value == '' || value == '...')
				continue;
			var optional = false;
			if (value.startsWith('?')) {
				optional = true;
				value = StringTools.trim(value.substr(1));
			}
			var colon = value.indexOf(':');
			var equals = value.indexOf('=');
			var type = '';
			if (colon >= 0) {
				var typeEnd = equals > colon ? equals : value.length;
				type = StringTools.trim(value.substr(colon + 1, typeEnd - colon - 1));
			}
			var cut = value.length;
			if (colon >= 0 && colon < cut)
				cut = colon;
			if (equals >= 0 && equals < cut)
				cut = equals;
			var name = StringTools.trim(value.substr(0, cut));
			if (name == '')
				continue;
			var defaultValue = '';
			if (equals >= 0) {
				optional = true;
				var rawDefault = StringTools.trim(value.substr(equals + 1));
				if (isHxcDefaultLiteral(rawDefault))
					defaultValue = rawDefault;
			}
			result.push({name: name, optional: optional, defaultValue: defaultValue, type: type});
		}
		return result;
	}

	/** Accept only the default values which can be replayed verbatim in HScript. */
	static function isHxcDefaultLiteral(value:String):Bool {
		if (value == null || StringTools.trim(value) == '')
			return false;
		var clean = StringTools.trim(value);
		if (clean == 'true' || clean == 'false' || clean == 'null')
			return true;
		if (new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', 'm').match(clean))
			return true;
		if ((clean.startsWith('"') && clean.endsWith('"') && clean.length >= 2)
			|| (clean.startsWith("'") && clean.endsWith("'") && clean.length >= 2))
			return clean.indexOf('\\') < 0;
		return false;
	}

	static function argumentInfoByName(infos:Array<HxcCompatArgumentInfo>,
		name:String):HxcCompatArgumentInfo {
		if (infos == null || name == null)
			return null;
		for (info in infos)
			if (info != null && info.name == name)
				return info;
		return null;
	}

	static function splitTopLevel(source:String, delimiter:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == '(' || current == '[' || current == '{')
				depth++;
			else if (current == ')' || current == ']' || current == '}')
				depth--;
			else if (depth == 0 && source.substr(index, delimiter.length) == delimiter) {
				result.push(source.substr(start, index - start));
				start = index + delimiter.length;
			}
		}
		result.push(source.substr(start));
		return result;
	}

	static function matchingDelimiter(source:String, start:Int, open:String, close:String):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in start...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == open)
				depth++;
			else if (current == close) {
				depth--;
				if (depth == 0)
					return index;
			}
		}
		return -1;
	}

	static function collectStateFields(source:String):Array<String> {
		var result:Array<String> = [];
		for (declaration in collectStateDeclarations(source))
			if (declaration != null)
				appendUnique(result, declaration.name);
		return result;
	}

	/**
		Collect class-level declarations without treating constructor expressions as
		executable donor code. Fields can follow the constructor, so scan only
		class-level brace depth and retain initializer text for the literal adapter.
	*/
	static function collectStateDeclarations(source:String):Array<HxcCompatStateDeclaration> {
		var result:Array<HxcCompatStateDeclaration> = [];
		if (source == null || source == '')
			return result;
		var classPos = source.indexOf('class ');
		var classOpen = classPos < 0 ? -1 : source.indexOf('{', classPos);
		if (classOpen < 0)
			return result;
		var classClose = matchingDelimiter(source, classOpen, '{', '}');
		if (classClose < 0)
			classClose = source.length;
		var body = source.substr(classOpen + 1, classClose - classOpen - 1);
		var depth = 0;
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < body.length) {
			var current = body.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (current == '{') {
				depth++;
				index++;
				continue;
			}
			if (current == '}') {
				if (depth > 0)
					depth--;
				index++;
				continue;
			}
			if (depth == 0 && body.substr(index, 3) == 'var'
				&& (index == 0 || !isIdentifierPart(body.charAt(index - 1)))
				&& (index + 3 >= body.length || !isIdentifierPart(body.charAt(index + 3)))) {
				var nameStart = index + 3;
				while (nameStart < body.length && isWhitespace(body.charAt(nameStart)))
					nameStart++;
				var nameEnd = nameStart;
				if (nameStart < body.length && isIdentifierStart(body.charAt(nameStart))) {
					nameEnd++;
					while (nameEnd < body.length && isIdentifierPart(body.charAt(nameEnd)))
						nameEnd++;
					var declarationEnd = nameEnd;
					var declarationDepth = 0;
					var declarationQuote = '';
					var declarationEscaped = false;
					while (declarationEnd < body.length) {
						var declarationChar = body.charAt(declarationEnd);
						if (declarationQuote != '') {
							if (declarationEscaped)
								declarationEscaped = false;
							else if (declarationChar == '\\\\')
								declarationEscaped = true;
							else if (declarationChar == declarationQuote)
								declarationQuote = '';
							declarationEnd++;
							continue;
						}
						if (declarationChar == '"' || declarationChar == "'")
							declarationQuote = declarationChar;
						else if (declarationChar == '[' || declarationChar == '{' || declarationChar == '(')
							declarationDepth++;
						else if (declarationChar == ']' || declarationChar == '}' || declarationChar == ')')
							declarationDepth--;
						else if (declarationChar == ';' && declarationDepth == 0)
							break;
						declarationEnd++;
					}
					var declarationText = body.substr(nameEnd, declarationEnd - nameEnd);
					var equals = declarationText.indexOf('=');
					var initializer = equals < 0 ? '' : StringTools.trim(declarationText.substr(equals + 1));
					result.push({name: body.substr(nameStart, nameEnd - nameStart), initializer: initializer});
					index = declarationEnd < body.length ? declarationEnd + 1 : declarationEnd;
					continue;
				}
				index = nameEnd > index ? nameEnd : index + 3;
				continue;
			}
			index++;
		}
		return result;
	}

	/**
		Apply literal state plus the tiny process-local store protocol.  Imported
		modules commonly use `FlxSave.bind/data/flush` only to hold options; the
		translator maps that object to the isolated HXC store and replays direct
		key assignments.  Other constructor calls remain unsafe.
	*/
	/**
		Translate the constructor-only stage surface used by FPS Plus/BaseStage.

		The donor stage constructors in the selected corpus are intentionally
		boring: they set a zoom, move the three start-point records, construct
		Flixel/BGSprite props, tweak a few visual fields, and put those props in a
		background/foreground layer.  Keep this pass lexical and bounded.  It is
		important that an arbitrary HXC constructor cannot become executable just
		because it extends BaseStage.
	*/
	static function translateStageConstructor(functions:Array<HxcCompatFunction>):String {
		if (functions == null)
			return '';
		var lines:Array<String> = [];
		var constructed:Map<String, Bool> = new Map<String, Bool>();
		for (method in functions) {
			if (method == null || method.name == null || method.name.toLowerCase() != 'new')
				continue;
			for (statement in splitTopLevel(method.body == null ? '' : method.body, ';')) {
				var value = StringTools.trim(statement);
				if (value == '' || value == 'super()' || value.startsWith('super('))
					continue;
				var translated = translateStageConstructorStatement(value, constructed);
				if (translated != null && StringTools.trim(translated) != '')
					lines.push(StringTools.trim(translated));
			}
		}
		return lines.join('\n');
	}

	/** Translate one simple constructor statement, or return null when it is
		outside the generic stage adapter's explicit vocabulary. */
	static function translateStageConstructorStatement(source:String,
		constructed:Map<String, Bool>):String {
		if (source == null)
			return null;
		var value = StringTools.trim(source);
		if (value == '')
			return null;

		// BaseStage's start records are not native fields. Apply their authored
		// delta to StageHelper and to the already-created live actor, so a stage
		// loaded after characters still gets the same placement as the donor.
		var startPoint = new EReg('^(bfStart|gfStart|dadStart)\\s*\\.\\s*(x|y)\\s*(\\+=|-=|=)\\s*(.+)$', 'm');
		if (startPoint.match(value)) {
			var amount = StringTools.trim(startPoint.matched(4));
			if (!isStageNumberLiteral(amount))
				return null;
			var role = switch (startPoint.matched(1)) {
				case 'bfStart': 'bf';
				case 'gfStart': 'gf';
				default: 'dad';
			};
			var operation = startPoint.matched(3) == '=' ? 'set'
				: (startPoint.matched(3) == '-=' ? 'subtract' : 'add');
			return 'stage.applyStartOffset(' + quote(role) + ', ' + quote(startPoint.matched(2))
				+ ', ' + amount + ', ' + quote(operation) + ');';
		}

		// The native StageHelper stores this flag for parity with BaseStage. The
		// offsets above already apply to current actors, while the flag makes the
		// authored intent available to later stage swaps and diagnostics.
		if (new EReg('^useStartPoints\\s*=\\s*(true|false)$', 'm').match(value))
			return 'stage.useStartPoints = ' + startPointValue(value) + ';';

		var zoom = new EReg('^startingZoom\\s*=\\s*(.+)$', 'm');
		if (zoom.match(value)) {
			var zoomValue = StringTools.trim(zoom.matched(1));
			return isStageNumberLiteral(zoomValue) ? 'setDefaultZoom(' + zoomValue + ');' : null;
		}

		// A constructor may assign its authored name, but the chart's stage id is
		// already the canonical identity in this engine. Do not let a donor class
		// rename the native stage group.
		if (new EReg('^name\\s*=\\s*["\\\'][^"\\\']*["\\\']$', 'm').match(value))
			return null;

		// A stage can read the same root-scoped preference view as its modules.
		// Replay only a Save getter lowered by translateBody, never an arbitrary
		// donor static call from the constructor.
		var storeAssignment = StringTools.trim(translateBody(value, 'new', []));
		if (new EReg('^[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*__hxcStore\\.getSave\\(\\s*\\)$', 'm').match(storeAssignment))
			return storeAssignment + ';';

		var sprite = translateStageSpriteConstructor(value, constructed);
		if (sprite != null)
			return sprite;

		// Keep only visual property writes on sprites created by this constructor.
		// The values are restricted to literals/engine-owned blend aliases so a
		// donor constructor cannot smuggle arbitrary calls into the stage scope.
		var scroll = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*(scrollFactor|scale)\\s*\\.\\s*set\\s*\\((.*)\\)$', 'm');
		if (scroll.match(value) && constructed.exists(scroll.matched(1))) {
			var pair = splitTopLevel(scroll.matched(3), ',');
			if (pair.length == 2 && isStageNumberLiteral(StringTools.trim(pair[0]))
				&& isStageNumberLiteral(StringTools.trim(pair[1])))
				return value + ';';
			return null;
		}
		var property = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*(antialiasing|active|alpha|visible|x|y|zIndex|flipX|flipY|blend)\\s*=\\s*(.+)$', 'm');
		if (property.match(value) && constructed.exists(property.matched(1))) {
			var propertyValue = StringTools.trim(property.matched(3));
			if (isStageLiteral(propertyValue)) {
				var output = value;
				// BlendMode is imported by the donor source but is not a class seeded
				// into HScript. Reuse the engine's existing string adapter.
				output = new EReg('\\bBlendMode\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\b', 'g')
					.replace(output, 'blendModeFromString("$1")');
				return output + ';';
			}
		}

		// BaseStage exposes semantic layer helpers rather than requiring callers
		// to know the native PlayState member order. Map all known layer spellings
		// to addSprite(), whose host owns camera binding and actor-relative inserts.
		var layer = new EReg('^(addToBackground|addToBackgroundLayer|addToForeground|addToForegroundLayer|addToCharacterLayer)\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)$', 'm');
		if (layer.match(value) && constructed.exists(layer.matched(2))) {
			var layerName = layer.matched(1);
			var position = layerName == 'addToBackground' || layerName == 'addToBackgroundLayer'
				? 'BEHIND_ALL' : 'BEHIND_NONE';
			return 'addSprite(' + layer.matched(2) + ', ' + position + ');';
		}
		return null;
	}

	/** Materialize a direct BGSprite/FlxSprite constructor assignment. */
	static function translateStageSpriteConstructor(source:String,
		constructed:Map<String, Bool>):String {
		var declaration = new EReg('^(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)(?:\\s*:\\s*[^=]+)?\\s*=\\s*new\\s+(BGSprite|FlxSprite)\\s*\\(', 'm');
		var assignment = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+(BGSprite|FlxSprite)\\s*\\(', 'm');
		var match = declaration.match(source) ? declaration : (assignment.match(source) ? assignment : null);
		if (match == null)
			return null;
		var name = match.matched(1);
		var className = match.matched(2);
		var open = source.indexOf('(', match.matchedPos().pos);
		if (open < 0)
			return null;
		var close = matchingDelimiter(source, open, '(', ')');
		if (close < 0)
			return null;
		var args = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
		if (args.length == 1 && StringTools.trim(args[0]) == '')
			args = [];
		for (arg in args)
			if (!isStageConstructorArgument(StringTools.trim(arg), className == 'BGSprite'))
				return null;
		var tail = StringTools.trim(source.substr(close + 1));
		var call:String;
		if (className == 'BGSprite') {
			if (tail != '')
				return null;
			call = 'HxcCompatRuntime.createBGSprite(hxcAssetRoot';
			for (arg in args)
				call += ', ' + StringTools.trim(arg);
			call += ')';
		} else {
			var graphic:String = null;
			if (tail != '') {
				var load = new EReg('^\\.\\s*loadGraphic\\s*\\(', 'm');
				if (!load.match(tail))
					return null;
				var loadOpen = tail.indexOf('(', load.matchedPos().pos);
				var loadClose = matchingDelimiter(tail, loadOpen, '(', ')');
				if (loadOpen < 0 || loadClose < 0 || StringTools.trim(tail.substr(loadClose + 1)) != '')
					return null;
				graphic = StringTools.trim(tail.substr(loadOpen + 1, loadClose - loadOpen - 1));
				if (!isStageConstructorArgument(graphic, false))
					return null;
			}
			call = 'HxcCompatRuntime.createFunkinSprite(hxcAssetRoot';
			if (args.length > 0)
				call += ', ' + args.join(', ');
			if (graphic != null)
				call += (args.length == 0 ? ', 0, 0, ' : ', ') + graphic;
			call += ')';
		}
		constructed.set(name, true);
		var prefix = source.substr(0, match.matchedPos().pos);
		// The prefix contains only the declaration/assignment portion because the
		// regex starts at column zero; preserve `var name =` in a clean form.
		var isDeclaration = StringTools.trim(prefix) == '' && source.startsWith('var') || source.startsWith('final');
		return (isDeclaration ? 'var ' : '') + name + ' = ' + call + ';';
	}

	static function isStageConstructorArgument(value:String, bgSprite:Bool):Bool {
		if (value == null || StringTools.trim(value) == '')
			return false;
		var clean = StringTools.trim(value);
		if (isStageLiteral(clean) || isStageNumberLiteral(clean))
			return true;
		// Static image lookups are rewritten to hxcPaths by the runtime owner and
		// are safe only when the key is a literal expression.
		return new EReg('^(?:Paths|hxcPaths)\\s*\\.\\s*(?:image|file)\\s*\\(', 'm').match(clean)
			&& matchingDelimiter(clean, clean.indexOf('('), '(', ')') == clean.length - 1;
	}

	static function isStageLiteral(value:String):Bool {
		if (value == null || StringTools.trim(value) == '')
			return false;
		var clean = StringTools.trim(value);
		if (isStageNumberLiteral(clean) || clean == 'true' || clean == 'false' || clean == 'null')
			return true;
		if ((clean.startsWith('"') && clean.endsWith('"')) || (clean.startsWith("'") && clean.endsWith("'")))
			return true;
		return isSimpleLiteral(clean);
	}

	static function isStageNumberLiteral(value:String):Bool {
		return value != null && new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', 'm').match(StringTools.trim(value));
	}

	static function startPointValue(source:String):String {
		var equals = source == null ? '' : source.substr(source.indexOf('=') + 1);
		return StringTools.trim(equals);
	}

	static function applyConstructorState(functions:Array<HxcCompatFunction>,
		stateFields:Array<String>, stateInitializers:Array<HxcCompatStateInitializer>,
		constructorStatements:Array<String>):Bool {
		var safe = true;
		if (functions == null)
			return safe;
		for (method in functions) {
			if (method == null || method.name == null || method.name.toLowerCase() != 'new')
				continue;
			// Preference modules often initialize a literal options object through
			// Save.instance.modOptions. Extract the option object by its set/get
			// operation shape and seed the selected root's process-local store; no
			// module, setting, or donor key name selects this boundary.
			var preferenceDefaults = namespacedPreferenceDefaultsField(method.body, stateInitializers);
			if (preferenceDefaults != null) {
				appendUnique(stateFields, 'save');
				if (constructorStatements != null) {
					constructorStatements.push('HxcCompatRuntime.seedStoreDefaults(__hxcStore, '
						+ preferenceDefaults.field + ', ' + quote(preferenceDefaults.key) + ');');
					constructorStatements.push('save = __hxcStore.getSave();');
				}
				continue;
			}
			// A few modules disable themselves on mobile before any donor state is
			// touched.  HxcCompatRuntime.onMobile is a fixed native read (false on
			// this desktop target), so replay this tiny guard as constructor state.
			var translatedConstructor = StringTools.trim(translateBody(method.body, method.name, method.arguments));
			if (translatedConstructor.indexOf('HxcCompatRuntime.onMobile') >= 0
				&& unsupportedConstructs(translatedConstructor).length == 0
				&& new EReg('\\b(?:var\\s+)?[A-Za-z_][A-Za-z0-9_]*\\s*=|\\bif\\s*\\(', 'm').match(translatedConstructor)) {
				if (constructorStatements != null)
					constructorStatements.push(translatedConstructor);
				continue;
			}
			for (statement in splitTopLevel(method.body == null ? '' : method.body, ';')) {
				var value = StringTools.trim(statement);
				if (value == '')
					continue;
				if (value.startsWith('super(') && value.endsWith(')'))
					continue;
				var cacheCall = constructorLiteralCacheCall(value);
				if (cacheCall != null) {
					if (constructorStatements != null)
						constructorStatements.push(cacheCall);
					continue;
				}
				var translated = StringTools.trim(translateBody(value, method.name, method.arguments));
				// Desktop-only modules commonly disable themselves with the native
				// mobile guard before touching any donor singleton. Preserve that
				// control flow as a generated local rather than treating the guarded
				// assignment as an arbitrary constructor expression. The guard is a
				// host property, not a donor module name, so this applies uniformly to
				// sound trays, RPC helpers, and other optional UI modules.
				var mobileGuard = new EReg('^if\\s*\\(\\s*(?:FlxG\\s*\\.\\s*onMobile|HxcCompatRuntime\\s*\\.\\s*onMobile)\\s*\\)\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(.+)$', 'm');
				if (mobileGuard.match(translated)) {
					var guardedName = mobileGuard.matched(1);
					var guardedValue = StringTools.trim(mobileGuard.matched(2));
					if (isSimpleLiteral(guardedValue)) {
						appendUnique(stateFields, guardedName);
						if (constructorStatements != null)
							constructorStatements.push(translated + ';');
						continue;
					}
				}
				// Some modules guard their isolated preferences read with try/catch.
				// The store getter is namespaced and deterministic;
				// replay only that exact save/null fallback and discard the donor catch
				// graph. Other guarded constructors remain unsafe.
				if (isSafeGuardedStoreAssignment(translated, stateFields)) {
					if (constructorStatements != null)
						constructorStatements.push('save = __hxcStore.getSave();');
					continue;
				}
				// The isolated store's bind/flush calls have no filesystem side
				// effects. Keep them executable, but do not infer semantics for
				// arbitrary methods on a donor object.
				if (isSafeStoreCall(translated, stateFields)) {
					if (constructorStatements != null)
						constructorStatements.push(translated + ';');
					continue;
				}
				if (isSafeNativeConstructorCall(translated)) {
					if (constructorStatements != null)
						constructorStatements.push(translated + ';');
					continue;
				}
				var propertyAssignment = new EReg('^(?:this\\.)?([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)+)\\s*=\\s*(.+)$', 'm');
				if (propertyAssignment.match(translated)) {
					var propertyRoot = propertyAssignment.matched(1).split('.')[0];
					// Validate the authored state expression as well as the translated
					// one.  Null-coalescing is lowered to lazy helper closures before
					// this gate, so checking only the generated call would incorrectly
					// reject the otherwise safe `SaveData.flag ?? false` pattern.
					var rawPropertyValue = '';
					var rawPropertyAssignment = new EReg('^(?:this\\.)?([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)+)\\s*=\\s*(.+)$', 'm');
					if (rawPropertyAssignment.match(value))
						rawPropertyValue = StringTools.trim(rawPropertyAssignment.matched(2));
					if (stateFields.indexOf(propertyRoot) >= 0
						&& (isSafeConstructorExpression(StringTools.trim(propertyAssignment.matched(2)) )
							|| isSafeStateExpression(StringTools.trim(propertyAssignment.matched(2)), stateFields)
							|| (rawPropertyValue != '' && isSafeStateExpression(rawPropertyValue, stateFields)))) {
						if (constructorStatements != null)
							constructorStatements.push(translated + ';');
						continue;
					}
					safe = false;
					continue;
				}
				var assignment = new EReg('^(?:this\\.)?([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(.+)$', 'm');
				if (!assignment.match(translated)) {
					safe = false;
					continue;
				}
				var name = assignment.matched(1);
				var initializer = StringTools.trim(assignment.matched(2));
				var translatedInitializer = StringTools.trim(translateBody(initializer));
				if (!isSafeConstructorExpression(translatedInitializer)) {
					safe = false;
					continue;
				}
				appendUnique(stateFields, name);
				setStateInitializer(stateInitializers, name, translatedInitializer);
			}
		}
		return safe;
	}

	/** Replay only literal donor cache requests through the selected media root. */
	static function constructorLiteralCacheCall(source:String):String {
		if (source == null)
			return null;
		var call = new EReg('^FunkinMemory\\s*\\.\\s*permanentCacheTexture\\s*\\(', 'm');
		if (!call.match(source))
			return null;
		var callPosition = call.matchedPos();
		var open = source.indexOf('(', callPosition.pos + callPosition.len - 1);
		if (open < 0 || matchingDelimiter(source, open, '(', ')') != source.length - 1)
			return null;
		var inner = StringTools.trim(source.substr(open + 1, source.length - open - 2));
		var pathCall = new EReg('^Paths\\s*\\.\\s*(sound|image)\\s*\\(', 'm');
		if (!pathCall.match(inner))
			return null;
		var pathPosition = pathCall.matchedPos();
		var pathOpen = inner.indexOf('(', pathPosition.pos + pathPosition.len - 1);
		if (pathOpen < 0 || matchingDelimiter(inner, pathOpen, '(', ')') != inner.length - 1)
			return null;
		var args = splitTopLevel(inner.substr(pathOpen + 1, inner.length - pathOpen - 2), ',');
		if (args.length < 1 || args.length > 2)
			return null;
		var key = StringTools.trim(args[0]);
		if (!isQuotedLiteral(key) || (args.length == 2 && !isQuotedLiteral(StringTools.trim(args[1]))))
			return null;
		// The native operation is explicitly a texture cache. Some donor HXC
		// code uses Paths.sound as a string-key helper here even though the key
		// resolves to an image; keep the operation's asset kind authoritative.
		return 'HxcCompatRuntime.cacheFunkinTexture(hxcAssetRoot, ' + key + ');';
	}

	static function namespacedPreferenceDefaultsField(source:String,
		stateInitializers:Array<HxcCompatStateInitializer>):Dynamic {
		if (source == null || source == '' || stateInitializers == null
			|| !new EReg('\\.\\s*modOptions\\s*\\.\\s*exists\\s*\\(', 'm').match(source)
			|| !new EReg('\\.\\s*modOptions\\s*\\.\\s*set\\s*\\(', 'm').match(source)
			|| !new EReg('\\.\\s*modOptions\\s*\\.\\s*get\\s*\\(', 'm').match(source)
			|| !new EReg('\\.\\s*flush\\s*\\(', 'm').match(source))
			return null;
		var existsKey = firstString(source,
			'\\.\\s*modOptions\\s*\\.\\s*exists\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var getKey = firstString(source,
			'\\.\\s*modOptions\\s*\\.\\s*get\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		if (existsKey == '' || existsKey != getKey)
			return null;
		for (initializer in stateInitializers) {
			if (initializer == null || initializer.name == null || initializer.value == null
				|| !initializer.value.startsWith('{'))
				continue;
			var setPattern = new EReg('\\.\\s*modOptions\\s*\\.\\s*set\\s*\\(\\s*["\\\']'
				+ EReg.escape(existsKey) + '["\\\']\\s*,\\s*' + initializer.name + '\\s*\\)', 'm');
			if (setPattern.match(source))
				return {field: initializer.name, key: existsKey};
		}
		return null;
	}

	static function isSafeGuardedStoreAssignment(source:String, stateFields:Array<String>):Bool {
		if (source == null || stateFields == null || stateFields.indexOf('save') < 0)
			return false;
		return new EReg('^try\\s*\\{\\s*save\\s*=\\s*__hxcStore\\.getSave\\(\\s*\\)\\s*;?\\s*\\}\\s*catch\\s*\\([^)]*\\)\\s*\\{\\s*save\\s*=\\s*null\\s*;?\\s*\\}$', 'm').match(source);
	}

	static function isSafeStoreCall(source:String, stateFields:Array<String>):Bool {
		if (source == null || source == '')
			return false;
		var expression = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*(bind|flush)\\s*\\([^;{}]*\\)$', 'm');
		if (!expression.match(source))
			return false;
		var root = expression.matched(1);
		return root == '__hxcStore' || (stateFields != null && stateFields.indexOf(root) >= 0);
	}

	/** Native process-global calls which are safe to replay during module setup. */
	static function isSafeNativeConstructorCall(source:String):Bool {
		if (source == null)
			return false;
		return new EReg('^HxcCompatRuntime\\.disableFullscreen\\(\\s*\\)$', 'm').match(StringTools.trim(source));
	}

	static function isSafeConstructorExpression(source:String):Bool {
		if (source == null || StringTools.trim(source) == '')
			return false;
		var value = StringTools.trim(source);
		if (isSimpleLiteral(value))
			return true;
		if (isBoundedNoteStyleInitializer(value))
			return true;
		if (value == 'HxcCompatRuntime.lyricsEnabled'
			|| value == 'HxcCompatRuntime.vignetteEffects')
			return true;
		// Direct dynamic-store property reads are deterministic and remain inside
		// the generated module namespace. They do not invoke a donor singleton.
		return new EReg('^[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*data$', 'm').match(value);
	}

	/** Only a literal style id may be seeded from a selected imported root. */
	static function isBoundedNoteStyleInitializer(source:String):Bool {
		return source != null && new EReg('^HxcNoteStyleCompat\\.fetchEntry\\(\\s*hxcAssetRoot\\s*,\\s*["\\\'][A-Za-z0-9_-]+["\\\']\\s*\\)$', 'm')
			.match(StringTools.trim(source));
	}

	/**
		Validate a constructor assignment which only reads/writes the module's own
		state (for example `SaveData.flag = SaveData.flag ?? false`).  This is
		separate from literal state so a donor singleton or arbitrary function call
		cannot enter the generated HScript through a permissive expression check.
	*/
	static function isSafeStateExpression(source:String, stateFields:Array<String>):Bool {
		if (source == null || stateFields == null || stateFields.length == 0)
			return false;
		var value = StringTools.trim(source);
		if (value == '' || value.indexOf('=>') >= 0 || value.indexOf('->') >= 0
			|| value.indexOf('new ') >= 0 || value.indexOf(';') >= 0
			|| value.indexOf('{') >= 0 || value.indexOf('}') >= 0)
			return false;
		var quote = '';
		var escaped = false;
		var chainAllowed = false;
		var index = 0;
		while (index < value.length) {
			var current = value.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (isIdentifierStart(current)) {
				var tokenStart = index;
				index++;
				while (index < value.length && isIdentifierPart(value.charAt(index)))
					index++;
				var token = value.substr(tokenStart, index - tokenStart);
				if (token == 'true' || token == 'false' || token == 'null') {
					chainAllowed = false;
					continue;
				}
				if (!chainAllowed && stateFields.indexOf(token) < 0)
					return false;
				var next = skipWhitespaceForward(value, index);
				if (next < value.length && value.charAt(next) == '(')
					return false;
				chainAllowed = true;
				continue;
			}
			if (current == '.') {
				if (!chainAllowed)
					return false;
				index++;
				continue;
			}
			if (current == '(' || current == ')' || current == '?' || current == ':'
				|| current == '!' || current == '=' || current == '<' || current == '>'
				|| current == '+' || current == '-' || current == '*' || current == '/'
				|| current == '%' || current == '&' || current == '|' || isWhitespace(current)
				|| current == ',' ) {
				index++;
				continue;
			}
			return false;
		}
		return quote == '';
	}

	static function setStateInitializer(initializers:Array<HxcCompatStateInitializer>,
		name:String, value:String):Void {
		if (initializers == null || name == null || name == '')
			return;
		for (initializer in initializers) {
			if (initializer != null && initializer.name == name) {
				initializer.value = value;
				return;
			}
		}
		initializers.push({name: name, value: value});
	}

	static function clearStateInitializer(initializers:Array<HxcCompatStateInitializer>,
		name:String):Void {
		if (initializers == null || name == null || name == '')
			return;
		for (initializer in initializers.copy())
			if (initializer != null && initializer.name == name)
				initializers.remove(initializer);
	}

	/**
		Return true only for the authored literal module disable switch.  Dynamic
		option reads and expressions remain normal module-safety inputs; they must
		not suppress diagnostics merely because they happen to evaluate false in a
		particular save state.
	*/
	static function hasLiteralFalseActive(initializers:Array<HxcCompatStateInitializer>):Bool {
		if (initializers == null)
			return false;
		for (initializer in initializers)
			if (initializer != null && initializer.name == 'active'
				&& StringTools.trim(initializer.value) == 'false')
				return true;
		return false;
	}

	/**
		Return true only for a module whose entire routed lifecycle is already a
		single native compatibility call.  This is deliberately stricter than
		checking `callback.safe`: a normal safe HScript body must still honor an
		authored `active = false` gate, while a fully lowered host boundary is the
		replacement for the donor body and cannot be dispatched any other way.
	*/
	static function hasCompleteNativeModuleBoundary(
		callbacks:Array<HxcCompatCallbackAdapter>, helpers:Array<HxcCompatCallbackAdapter>):Bool {
		if (callbacks == null || callbacks.length == 0)
			return false;
		if (helpers != null && helpers.length > 0)
			return false;
		for (callback in callbacks)
			if (callback == null || !callback.safe || !isNativeBoundaryBody(callback.body))
				return false;
		return true;
	}

	/** Recognize only the direct host-call form emitted by module translators. */
	static function isNativeBoundaryBody(body:String):Bool {
		if (body == null)
			return false;
		return new EReg('^HxcCompatRuntime\\.[A-Za-z_][A-Za-z0-9_]*\\s*\\([\\s\\S]*\\)\\s*;?$', 'm')
			.match(StringTools.trim(body));
	}

	/**
		Recognize the complete V-Slice video-module contract by its state and
		operation graph. Class names, file paths, and donor module identifiers are
		intentionally absent from this boundary. Requiring every helper and
		lifecycle branch keeps a partial copy unsupported instead of masking a real
		semantic gap behind the native host.
	*/
	static function detectVideoModuleAdapter(source:String, functions:Array<HxcCompatFunction>,
		stateDeclarations:Array<HxcCompatStateDeclaration>):Bool {
		if (source == null || functions == null || stateDeclarations == null)
			return false;
		var expectedMethods = ['new', 'createVideo', 'checkResync', 'clearVideoSprites',
			'getDefaultConfig', 'onUpdate', 'onFocusGained', 'onStepHit', 'onPause', 'onResume',
			'onSongRetry', 'onGameOver', 'onSongEnd', 'onCountdownStart'];
		if (functions.length != expectedMethods.length)
			return false;
		var byName:Map<String, HxcCompatFunction> = new Map<String, HxcCompatFunction>();
		for (method in functions) {
			if (method == null || method.name == null || expectedMethods.indexOf(method.name) < 0
				|| byName.exists(method.name))
				return false;
			byName.set(method.name, method);
		}
		for (name in expectedMethods)
			if (!byName.exists(name))
				return false;

		var expectedFields = ['videoSpriteGroup', 'fadeHUD', 'fadeOutTween', 'fadeInTween', 'VIDEO_RESYNC_THRESHOLD'];
		if (stateDeclarations.length != expectedFields.length)
			return false;
		var fields:Map<String, HxcCompatStateDeclaration> = new Map<String, HxcCompatStateDeclaration>();
		for (field in stateDeclarations) {
			if (field == null || field.name == null || expectedFields.indexOf(field.name) < 0
				|| fields.exists(field.name))
				return false;
			fields.set(field.name, field);
		}
		for (name in expectedFields)
			if (!fields.exists(name))
				return false;
		var groupInitializer = StringTools.trim(fields.get('videoSpriteGroup').initializer);
		if (!new EReg('^new\\s+(?:[A-Za-z0-9_.]+\\.)?FlxTypedGroup\\s*\\(', 'm').match(groupInitializer)
			|| StringTools.trim(fields.get('fadeHUD').initializer).toLowerCase() != 'false'
			|| StringTools.trim(fields.get('VIDEO_RESYNC_THRESHOLD').initializer) != '550'
			|| StringTools.trim(fields.get('fadeOutTween').initializer) != ''
			|| StringTools.trim(fields.get('fadeInTween').initializer) != '')
			return false;

		var constructor = byName.get('new');
		var constructorBody = StringTools.trim(constructor.body);
		if (constructor.arguments.length != 0 || !StringTools.startsWith(constructorBody, 'super(')
			|| !(StringTools.endsWith(constructorBody, ')') || StringTools.endsWith(constructorBody, ');'))
			|| (constructorBody.indexOf("'") < 0 && constructorBody.indexOf('"') < 0))
			return false;
		if (!hasHxcVideoArguments(byName.get('createVideo'), ['filePath', 'config'], [false, true])
			|| !hasHxcVideoArguments(byName.get('checkResync'), ['video', 'instant', 'resume'], [false, true, true])
			|| !hasHxcVideoArguments(byName.get('clearVideoSprites'), [], [])
			|| !hasHxcVideoArguments(byName.get('getDefaultConfig'), [], []))
			return false;
		for (name in ['onUpdate', 'onFocusGained', 'onStepHit', 'onPause', 'onResume',
			'onSongRetry', 'onGameOver', 'onSongEnd', 'onCountdownStart'])
			if (!hasHxcVideoArguments(byName.get(name), ['event'], [false]))
				return false;

		var create = compactExpression(byName.get('createVideo').body).toLowerCase();
		if (!hasHxcVideoFragments(create, [
			'config==null', 'getDefaultConfig()', 'Objects.shallowCombine(getDefaultConfig(),config)',
			'newFunkinVideoSprite(0,0)', 'makeGraphic(FlxG.width,FlxG.height,0xFF000000)',
			'videoSprite.zIndex=config.zIndex', 'blackBars.zIndex=config.zIndex-1', 'filePath==null',
			'config.videoType==2', 'config.timestamp+=(config.hudFadeDuration*1000)',
			'onEncounteredError.add(', 'onEndReached.add(', 'onFormatSetup.add(',
			'videoSpriteGroup.add(', 'PlayState.instance.add(blackBars)',
			'PlayState.instance.add(videoSprite)', 'PlayState.instance.refresh()',
			'if(config.disableControls)', 'case2:', 'case3:', 'camCutscene',
			'camHUD.visible=false', 'videoSprite.load(', 'videoSprite.play()',
			'videoSprite.bitmap.volumeAdjust=', 'mute?0:1', 'returnvideoSprite'
		]))
			return false;
		var resync = compactExpression(byName.get('checkResync').body).toLowerCase();
		if (!hasHxcVideoFragments(resync, [
			'video?.videoSprite?.bitmap==null', 'Conductor.instance.songPosition',
			'Conductor.instance.combinedOffset', 'video.config.timestamp',
			'video.videoSprite.bitmap.time', 'instant||Math.abs(videoError)>VIDEO_RESYNC_THRESHOLD)',
			'video.videoSprite.pause()', 'video.videoSprite.bitmap.time=expectedVideoTime',
			'if(resume)video.videoSprite.resume()'
		]))
			return false;
		var clear = compactExpression(byName.get('clearVideoSprites').body).toLowerCase();
		if (!hasHxcVideoFragments(clear, ['videoSpriteGroup?.members', 'video?.videoSprite!=null',
			'video.videoSprite.destroy()', 'video.letterBoxing.destroy()', 'videoSpriteGroup.clear()']))
			return false;
		var defaults = compactExpression(byName.get('getDefaultConfig').body).toLowerCase();
		if (!hasHxcVideoFragments(defaults, ['videoType:1', 'disableControls:false', 'hudFadeDuration:1',
			'resync:true', 'zIndex:300', 'mute:false', 'timestamp:Conductor.instance.songPosition']))
			return false;
		var update = compactExpression(byName.get('onUpdate').body).toLowerCase();
		if (!hasHxcVideoFragments(update, ['videoSpriteGroup.members', 'letterBoxing.visible=video.videoSprite.visible',
			'letterBoxing.alpha=video.videoSprite.alpha']))
			return false;
		var focus = compactExpression(byName.get('onFocusGained').body).toLowerCase();
		if (!hasHxcVideoFragments(focus, ['videoSpriteGroup!=null', 'PlayState.instance?.isGamePaused',
			'video.videoSprite.pause()']))
			return false;
		var step = compactExpression(byName.get('onStepHit').body).toLowerCase();
		if (!hasHxcVideoFragments(step, ['video.config.resync', 'video.videoSprite?.bitmap?.isPlaying',
			'checkResync(video,false,true)']))
			return false;
		var pause = compactExpression(byName.get('onPause').body).toLowerCase();
		if (!hasHxcVideoFragments(pause, ['fadeOutTween.active=false', 'fadeInTween.active=false',
			'video.videoSprite.pause()', 'video.config.resync', 'checkResync(video,true,false)']))
			return false;
		var resume = compactExpression(byName.get('onResume').body).toLowerCase();
		if (!hasHxcVideoFragments(resume, ['fadeOutTween.active=true', 'fadeInTween.active=true',
			'video.videoSprite.resume()']))
			return false;
		var retry = compactExpression(byName.get('onSongRetry').body).toLowerCase();
		if (!hasHxcVideoFragments(retry, ['if(fadehud)', 'fadeOutTween.cancel()',
			'FlxTween.tween(PlayState.instance.camHUD,{alpha:1},0.5',
			'PlayState.instance.camHUD.visible=true', 'clearVideoSprites()']))
			return false;
		for (name in ['onGameOver', 'onSongEnd', 'onCountdownStart']) {
			var body = compactExpression(byName.get(name).body).toLowerCase();
			if (body.indexOf('clearvideosprites()') < 0)
				return false;
		}
		if (!new EReg('videoSpriteGroup\\s*:\\s*(?:[A-Za-z0-9_.]+\\.)?FlxTypedGroup\\s*<', 'm').match(source)
			|| !new EReg('onEncounteredError[\\s\\S]*new\\s+AtlasText[\\s\\S]*new\\s+FlxTimer[\\s\\S]*start\\s*\\(\\s*10', 'm').match(source))
			return false;
		return true;
	}

	static function hasHxcVideoArguments(method:HxcCompatFunction, names:Array<String>, optional:Array<Bool>):Bool {
		if (method == null || method.arguments == null || method.arguments.length != names.length)
			return false;
		for (index in 0...names.length) {
			if (method.arguments[index] != names[index])
				return false;
			var info = argumentInfoByName(method.argumentInfos, names[index]);
			if (optional[index] != (info != null && info.optional))
				return false;
		}
		return true;
	}

	static function hasHxcVideoFragments(source:String, fragments:Array<String>):Bool {
		if (source == null || fragments == null)
			return false;
		for (fragment in fragments)
			if (source.indexOf(fragment.toLowerCase()) < 0)
				return false;
		return true;
	}

	static function videoModuleCallbackAdapters():Array<HxcCompatCallbackAdapter> {
		var result:Array<HxcCompatCallbackAdapter> = [];
		var callbacks = [
			{source: 'onUpdate', canonical: 'update', host: 'videoModuleUpdate'},
			{source: 'onFocusGained', canonical: 'focusGained', host: 'videoModuleFocusGained'},
			{source: 'onStepHit', canonical: 'stepHit', host: 'videoModuleStepHit'},
			{source: 'onPause', canonical: 'pause', host: 'videoModulePause'},
			{source: 'onResume', canonical: 'resume', host: 'videoModuleResume'},
			{source: 'onSongRetry', canonical: 'songRetry', host: 'videoModuleSongRetry'},
			{source: 'onGameOver', canonical: 'gameOver', host: 'videoModuleGameOver'},
			{source: 'onSongEnd', canonical: 'songEnd', host: 'videoModuleSongEnd'},
			{source: 'onCountdownStart', canonical: 'countdownStart', host: 'videoModuleCountdownStart'}
		];
		for (callback in callbacks)
			result.push({sourceName: callback.source, canonicalName: callback.canonical,
				arguments: ['event'], body: 'HxcCompatRuntime.' + callback.host
					+ '(PlayState.instance, __hxcVideoModule, event);', safe: true});
		return result;
	}

	static function videoModuleHelperAdapters():Array<HxcCompatCallbackAdapter> {
		return [
			{sourceName: 'createVideo', canonicalName: 'createVideo', arguments: ['filePath', 'config'],
				argumentInfos: [{name:'filePath', optional:false, defaultValue:''},
					{name:'config', optional:true, defaultValue:''}],
				body: 'HxcCompatRuntime.videoModuleCreateVideo(PlayState.instance, __hxcVideoModule, filePath, config)', safe:true},
			{sourceName: 'getDefaultConfig', canonicalName: 'getDefaultConfig', arguments: [], body:
				'HxcCompatRuntime.videoModuleDefaults(PlayState.instance, __hxcVideoModule)', safe:true},
			{sourceName: 'checkResync', canonicalName: 'checkResync', arguments: ['video', 'instant', 'resume'],
				argumentInfos: [{name:'video', optional:false, defaultValue:''},
					{name:'instant', optional:true, defaultValue:'false'},
					{name:'resume', optional:true, defaultValue:'true'}],
				body: 'HxcCompatRuntime.videoModuleCheckResync(PlayState.instance, __hxcVideoModule, video, instant, resume)', safe:true},
			{sourceName: 'clearVideoSprites', canonicalName: 'clearVideoSprites', arguments: [], body:
				'HxcCompatRuntime.videoModuleClear(PlayState.instance, __hxcVideoModule)', safe:true}
		];
	}

	/**
		Accept the donor shader field-initializer shape: a FlxRuntimeShader built
		from literal (or scoped frag-text chain) arguments, or a ShaderFilter
		wrapping a bare state-field shader reference. Both constructors resolve
		to interpreter-seeded engine classes, so replaying them cannot run donor
		code; anything else (foreign classes, computed shader sources) stays a
		diagnostic instead of becoming state.
	*/
	static function isBoundedShaderInitializer(source:String):Bool {
		if (source == null || StringTools.trim(source) == '')
			return false;
		var value = StringTools.trim(source);
		// ShaderFilter only wraps an already-constructed shader field.
		if (new EReg('^new\\s+ShaderFilter\\s*\\(\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\)$', 'm').match(value))
			return true;
		var constructor = new EReg('^new\\s+FlxRuntimeShader\\s*\\(', 'm');
		if (!constructor.match(value))
			return false;
		var open = value.indexOf('(', constructor.matchedPos().pos);
		if (open < 0)
			return false;
		var close = matchingDelimiter(value, open, '(', ')');
		if (close != value.length - 1)
			return false;
		var args = splitTopLevel(value.substr(open + 1, close - open - 1), ',');
		if (args.length == 1 && StringTools.trim(args[0]) == '')
			return true;
		for (arg in args)
			if (!isBoundedShaderArgument(StringTools.trim(arg)))
				return false;
		return true;
	}

	/** Preserve a donor FlxPoint field without admitting arbitrary constructors. */
	static function boundedPointInitializer(source:String):Null<String> {
		if (source == null) return null;
		var value = StringTools.trim(source);
		var constructor = ~/^(?:FlxPoint\s*\.\s*get|new\s+FlxPoint)\s*\(/;
		if (!constructor.match(value)) return null;
		var open = value.indexOf('(', constructor.matchedPos().pos);
		var close = matchingDelimiter(value, open, '(', ')');
		if (close != value.length - 1) return null;
		var raw = StringTools.trim(value.substr(open + 1, close - open - 1));
		var values = raw == '' ? [] : splitTopLevel(raw, ',');
		if (values.length > 2) return null;
		for (part in values)
			if (!~/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.match(StringTools.trim(part))) return null;
		return 'HxcCompatRuntime.point(' + (values.length > 0 ? StringTools.trim(values[0]) : '0')
			+ ', ' + (values.length > 1 ? StringTools.trim(values[1]) : '0') + ')';
	}

	/** Literal or scoped-frag-chain arguments are safe to replay verbatim. */
	static function isBoundedShaderArgument(value:String):Bool {
		if (value == null || StringTools.trim(value) == '')
			return false;
		var clean = StringTools.trim(value);
		if (isStageLiteral(clean))
			return true;
		// The standard donor shader source: scoped frag text, in either the
		// authored spelling or the runtime proxy spelling the loader rewrites in.
		return new EReg('^(?:Assets|hxcAssets)\\s*\\.\\s*getText\\s*\\(\\s*(?:Paths|hxcPaths)\\s*\\.\\s*frag\\s*\\(\\s*(?:"[^"]*"|\'[^\']*\')\\s*\\)\\s*\\)$', 'm')
			.match(clean);
	}

	/**
		Validate the only state expressions which can be copied without running a
		donor constructor. Strings, numbers, booleans, null, arrays, and object
		literals are accepted; identifiers must be object keys or literals. Calls,
		new expressions, map arrows, and references to foreign state are rejected.
	*/
	static function isSimpleLiteral(source:String):Bool {
		if (source == null || StringTools.trim(source) == '')
			return false;
		var value = StringTools.trim(source);
		// Haxe uses hexadecimal integer literals for colors and bit masks. Keep
		// this exact scalar form in the same literal-only boundary as decimal
		// numbers; a wider expression still goes through the normal token gate.
		if (new EReg('^0[xX][0-9A-Fa-f]+$', 'm').match(value))
			return true;
		// A zero-argument native container has no donor side effects and is safe
		// to materialize in the generated HScript state.  Keep this deliberately
		// narrow: arbitrary `new` expressions may run foreign constructors or
		// capture donor-only registries and therefore remain unsupported.
		if (new EReg('^new\\s+(?:FlxTypedGroup|StringMap)\\s*\\(\\s*\\)$', 'm').match(value))
			return true;
		// These are interpreter-seeded compatibility values, not donor-side
		// constructors.  They are safe to capture in a module's initial state.
		if (value == '__hxcStore' || value == 'downscroll' || value == 'middlescroll'
			|| value == 'curStep' || value == 'curBeat' || value == 'bpm')
			return true;
		if (value == 'HxcCompatRuntime.lyricsEnabled'
			|| value == 'HxcCompatRuntime.vignetteEffects')
			return true;
		// Constants is lowered to this owner-scoped mutable facade.  Only its
		// declared fields may seed module state; arbitrary runtime calls and
		// foreign object reads remain outside the initializer boundary.
		if (new EReg('^HxcCompatRuntime\\s*\\.\\s*constantsForRoot\\s*\\(\\s*hxcAssetRoot\\s*\\)\\s*\\.\\s*(?:TITLE|VERSION|COLOR_HEALTH_BAR_GREEN|COLOR_HEALTH_BAR_RED|COUNTDOWN_VOLUME|DEFAULT_CAMERA_FOLLOW_RATE|DEFAULT_VARIATION|PIXELS_PER_MS|PIXEL_ART_SCALE|STRUMLINE_X_OFFSET|STRUMLINE_Y_OFFSET|DEFAULT_DIFFICULTY_LIST_FULL)$', 'm')
			.match(value))
			return true;
		if (new EReg('^__hxcStore\\.getSave\\(\\s*\\)$', 'm').match(value))
			return true;
		// lowerMapLiterals emits hxcMap for HXC's literal map syntax. The
		// adapter is a pure native container, so permit it as module state only
		// when every key/value pair is itself a literal or another hxcMap.
		if (value.startsWith('hxcMap(') && isSafeMapLiteral(value))
			return true;
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < value.length) {
			var current = value.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (isIdentifierStart(current)) {
				var tokenStart = index;
				index++;
				while (index < value.length && isIdentifierPart(value.charAt(index)))
					index++;
				var token = value.substr(tokenStart, index - tokenStart);
				var next = skipWhitespaceForward(value, index);
				var previous = tokenStart > 0 ? value.charAt(tokenStart - 1) : '';
				var isObjectKey = next < value.length && value.charAt(next) == ':';
				var isChainedField = previous == '.';
				// Calls can have otherwise harmless-looking roots (for example
				// Math.max), but evaluating arbitrary initializer calls would run
				// donor code.  The one namespaced store getter is translated before
				// this gate and is intentionally handled above.
				if (next < value.length && value.charAt(next) == '(' && !isObjectKey)
					return false;
			if (token != 'true' && token != 'false' && token != 'null'
				&& !isObjectKey && !isChainedField && !safeStateRoot(token))
				return false;
				continue;
			}
			if (current == '+' || current == '-') {
				index++;
				continue;
			}
			if (isDigit(current)) {
				index++;
				while (index < value.length && (isDigit(value.charAt(index))
					|| value.charAt(index) == '.'))
					index++;
				continue;
			}
			if (current == '[' || current == ']' || current == '{' || current == '}'
				|| current == '(' || current == ')' || current == ':' || current == ',') {
				index++;
				continue;
			}
			if (isWhitespace(current) || current == '.' || current == '*' || current == '/'
				|| current == '%' || current == '?' || current == '!' || current == '<'
				|| current == '>' || current == '&' || current == '|') {
				index++;
				continue;
			}
			return false;
		}
		return quote == '';
	}

	static function isSafeMapLiteral(value:String):Bool {
		var trimmed = StringTools.trim(value);
		if (!trimmed.startsWith('hxcMap(') || !trimmed.endsWith(')'))
			return false;
		var open = trimmed.indexOf('(');
		var close = matchingDelimiter(trimmed, open, '(', ')');
		if (open < 0 || close != trimmed.length - 1)
			return false;
		var payload = StringTools.trim(trimmed.substr(open + 1, close - open - 1));
		if (payload.length < 2 || payload.charAt(0) != '[' || payload.charAt(payload.length - 1) != ']')
			return false;
		var entries = splitTopLevel(payload.substr(1, payload.length - 2), ',');
		for (entry in entries) {
			var pair = StringTools.trim(entry);
			if (pair == '')
				continue;
			if (pair.charAt(0) != '[' || pair.charAt(pair.length - 1) != ']')
				return false;
			var values = splitTopLevel(pair.substr(1, pair.length - 2), ',');
			if (values.length != 2)
				return false;
			for (item in values) {
				var literal = StringTools.trim(item);
				if (literal.startsWith('hxcMap(')) {
					if (!isSafeMapLiteral(literal))
						return false;
				} else if (isSafeStateFactoryLiteral(literal)
					|| isSafeDeferredStateFactoryLiteral(literal)) {
					continue;
				} else if (!isSimpleLiteral(literal)) {
					return false;
				}
			}
		}
		return true;
	}

	static function isSafeStateFactoryLiteral(value:String):Bool {
		if (value == null)
			return false;
		return new EReg('^hxcStateFactory\\(\\s*["\\\'][A-Za-z_][A-Za-z0-9_]*(?:State|SubState)["\\\']\\s*,\\s*\\[\\s*\\]\\s*\\)$', 'm').match(StringTools.trim(value));
	}

	static function isSafeDeferredStateFactoryLiteral(value:String):Bool {
		if (value == null)
			return false;
		return new EReg('^hxcDeferredStateFactory\\(\\s*["\\\'][A-Za-z_][A-Za-z0-9_]*(?:State|SubState)["\\\']\\s*,\\s*\\[\\s*\\]\\s*\\)$', 'm').match(StringTools.trim(value));
	}

	/** Roots whose read-only values are seeded by the native interpreter. */
	static function safeStateRoot(name:String):Bool {
		if (name == null || name == '')
			return false;
		return switch (name) {
			case 'FlxG' | 'FlxColor' | 'Math' | 'Std' | 'Conductor' | 'PlayState'
				| 'HxcCompatRuntime' | 'SONG' | 'downscroll' | 'middlescroll'
				| 'curStep' | 'curBeat' | 'bpm' | 'MainMenuState' | 'StoryMenuState'
				| 'FreeplayState' | 'TitleState' | 'CreditsState' | 'SaveDataState': true;
			default: false;
		};
	}

	static function isDigit(value:String):Bool {
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	/**
		Modules are global side-effect containers, so lexical HScript syntax is not
		enough evidence that a callback can run. Resolve roots against the names
		actually seeded by PlayState/PluginManager and reject donor-only fields or
		unrouted `on*` methods. The gate is intentionally stricter than ordinary
		stage/song adapters: a module is marked safe only when every dispatched
		callback and every helper it calls has a native root.
	*/
	static function applyModuleSafety(functions:Array<HxcCompatFunction>,
		callbacks:Array<HxcCompatCallbackAdapter>, helpers:Array<HxcCompatCallbackAdapter>,
		stateFields:Array<String>, stateInitializers:Array<HxcCompatStateInitializer>,
		reasons:Array<String>, source:String):Bool {
		if (callbacks == null || callbacks.length == 0) {
			appendUnique(reasons, 'no routed lifecycle callback');
			return false;
		}
		var helperNames:Array<String> = [];
		var helperMap:Map<String, HxcCompatCallbackAdapter> = new Map();
		var callbackNames:Array<String> = [];
		var callbackMap:Map<String, HxcCompatCallbackAdapter> = new Map();
		if (callbacks != null)
			for (callback in callbacks)
				if (callback != null) {
					appendUnique(callbackNames, callback.sourceName);
					appendUnique(callbackNames, callback.canonicalName);
					callbackMap.set(callback.sourceName, callback);
					callbackMap.set(callback.canonicalName, callback);
				}
		if (helpers != null)
			for (helper in helpers)
				if (helper != null && helper.sourceName != null && helper.sourceName != '') {
					appendUnique(helperNames, helper.sourceName);
					helperMap.set(helper.sourceName, helper);
				}
		// Any `on*` method not in the centrally dispatched vocabulary is still a
		// live donor hook. Treating it as an ordinary helper would silently drop
		// state-change/substate behavior during import.
		if (functions != null)
			for (method in functions)
				if (method != null && method.name != null
					&& method.name.toLowerCase().startsWith('on')
					&& lifecycleCallback(method.name) == '') {
					appendUnique(reasons, 'unrouted lifecycle ' + method.name);
				}

		var playStateAliases = modulePlayStateAliases(callbacks, helpers);
		var safeMapFields = safeStateMapFields(stateInitializers);
		var unseededTypedGraphs = collectUnseededTypedContainerGraphs(source);
		var helperSafety:Map<String, Bool> = new Map();
		if (helpers != null)
			for (helper in helpers) {
				if (helper == null)
					continue;
				var helperSafe = helper.safe
				&& !moduleBodyTouchesTypedGraph(helper.body, unseededTypedGraphs)
				&& !moduleHelperUsesTypedGraphPayload(helper.argumentInfos, unseededTypedGraphs)
				&& moduleBodyUsesSafeRoots(helper.body, helper.arguments, stateFields,
					helperNames.concat(callbackNames), playStateAliases, safeMapFields);
				helper.safe = helperSafe;
				helperSafety.set(helper.sourceName, helperSafe);
			}
		// Helper bodies can call other helpers. A direct-root check alone used to
		// mark a wrapper safe while its omitted callee remained donor-only; the
		// generated callback then failed at runtime with EUnknownVariable.
		var changed = true;
		while (changed) {
			changed = false;
			if (helpers != null)
				for (helper in helpers) {
					if (helper == null || helper.sourceName == null
						|| helperSafety.get(helper.sourceName) != true)
						continue;
					for (called in collectUnqualifiedCalls(helper.body))
						if (helperMap.exists(called) && helperSafety.get(called) != true) {
							helper.safe = false;
							helperSafety.set(helper.sourceName, false);
							appendUnique(reasons, 'unsafe helper dependency '
								+ helper.sourceName + ' -> ' + called);
							changed = true;
							break;
						}
				}
		}

		var safeCallbacks = 0;
		for (callback in callbacks) {
			if (callback == null)
				continue;
			var callbackSafe = callback.safe
				&& !moduleBodyTouchesTypedGraph(callback.body, unseededTypedGraphs)
				&& moduleBodyUsesSafeRoots(callback.body, callback.arguments, stateFields,
					helperNames.concat(callbackNames), playStateAliases, safeMapFields);
			if (!callbackSafe)
				appendUnique(reasons, 'unsafe callback ' + callback.sourceName);
			for (callName in collectUnqualifiedCalls(callback.body)) {
				if (helperMap.exists(callName)) {
					if (helperSafety.get(callName) != true) {
						callbackSafe = false;
						appendUnique(reasons, 'unsafe helper ' + callName);
					}
				} else if (callbackMap.exists(callName)) {
					var calledCallback = callbackMap.get(callName);
					if (calledCallback == null || !calledCallback.safe) {
						callbackSafe = false;
						appendUnique(reasons, 'unsafe callback call ' + callName);
					}
				} else if (!moduleKnownCall(callName)) {
					callbackSafe = false;
					appendUnique(reasons, 'unseeded call ' + callName);
				}
			}
			callback.safe = callbackSafe;
			if (callbackSafe)
				safeCallbacks++;
		}
		return safeCallbacks == callbacks.length && reasons.length == 0;
	}

	/**
		Find parameterized Flixel groups whose item type is not a native HXC data
		type. The group constructor itself is a harmless native container, but its
		members may be donor-defined records which can carry foreign objects (for
		example a video sprite wrapping hxvlc). Callbacks which traverse one of
		these fields, and helpers typed to its items, must stay behind the module
		safety gate.
	*/
	static function collectUnseededTypedContainerGraphs(source:String):Array<HxcCompatTypedGraphRoot> {
		var result:Array<HxcCompatTypedGraphRoot> = [];
		if (source == null || source == '')
			return result;
		var expression = new EReg('\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*'
			+ '(?:[A-Za-z_][A-Za-z0-9_.]*\\.)?(FlxTypedGroup|FlxTypedSpriteGroup)'
			+ '\\s*<\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*>', 'gm');
		var offset = 0;
		while (offset < source.length) {
			if (!expression.match(source.substr(offset)))
				break;
			var field = expression.matched(1);
			var itemType = expression.matched(3);
			if (!isNativeTypedContainerItem(itemType))
				result.push({field:field, itemType:itemType});
			var position = expression.matchedPos();
			if (position.len <= 0)
				break;
			offset += position.pos + position.len;
		}
		return result;
	}

	static function isNativeTypedContainerItem(typeName:String):Bool {
		if (typeName == null || typeName == '')
			return false;
		var parts = typeName.split('.');
		var simple = parts[parts.length - 1];
		return switch (simple) {
			case 'Int' | 'Float' | 'Bool' | 'String' | 'Dynamic'
				| 'FlxBasic' | 'FlxObject' | 'FlxSprite' | 'FlxText' | 'FlxCamera' | 'FlxSound'
				| 'FlxTypedGroup' | 'FlxTypedSpriteGroup': true;
			default: false;
		};
	}

	static function moduleBodyTouchesTypedGraph(body:String,
		graphs:Array<HxcCompatTypedGraphRoot>):Bool {
		if (body == null || body == '' || graphs == null || graphs.length == 0)
			return false;
		for (graph in graphs)
			if (graph != null && graph.field != null
				&& new EReg('\\b' + graph.field + '\\b', 'm').match(body))
				return true;
		return false;
	}

	static function moduleHelperUsesTypedGraphPayload(arguments:Array<HxcCompatArgumentInfo>,
		graphs:Array<HxcCompatTypedGraphRoot>):Bool {
		if (arguments == null || graphs == null || graphs.length == 0)
			return false;
		for (argument in arguments) {
			if (argument == null || argument.type == null || argument.type == '')
				continue;
			var parts = argument.type.split('.');
			var simpleType = parts[parts.length - 1];
			for (graph in graphs)
				if (graph != null && graph.itemType != null) {
					var itemParts = graph.itemType.split('.');
					if (simpleType == itemParts[itemParts.length - 1])
						return true;
				}
		}
		return false;
	}

	/** Check translated roots, local lambda variables, and known PlayState fields. */
	static function moduleBodyUsesSafeRoots(body:String, arguments:Array<String>,
		stateFields:Array<String>, helperNames:Array<String>,
		?playStateAliases:Array<String>, ?safeMapFields:Array<String>):Bool {
		var translated = translateBody(body == null ? '' : body);
		if (unsupportedHxcApiMembers(body).length > 0
			|| unsupportedConstructs(translated).length > 0
			|| hasUnsafeDynamicNativeAssetCall(translated)) {
			return false;
		}
		var allowed:Map<String, Bool> = new Map();
		if (arguments != null)
			for (argument in arguments)
				if (argument != null && argument != '')
					allowed.set(argument, true);
		if (stateFields != null)
			for (field in stateFields)
				if (field != null && field != '')
					allowed.set(field, true);
		if (helperNames != null)
			for (name in helperNames)
				if (name != null && name != '')
					allowed.set(name, true);
		for (local in collectMatches(translated,
			'\\bfunction\\s*\\(([^)]*)\\)', 1))
				for (argument in parseArgumentNames(local))
					allowed.set(argument, true);
		for (local in collectMatches(translated,
			'\\b(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)', 1))
			allowed.set(local, true);
		for (local in collectMatches(translated,
			'\\bfor\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s+in\\b', 1))
			allowed.set(local, true);

		for (root in collectRootNames(translated))
			if (!allowed.exists(root) && !moduleKnownRoot(root)) {
				return false;
			}
		for (callName in collectUnqualifiedCalls(translated))
			if (!allowed.exists(callName) && !moduleKnownCall(callName)) {
				return false;
			}
		if (!modulePlayStateMembersSafe(translated, playStateAliases))
			return false;
		if (!moduleFreeplayMembersSafe(translated, arguments))
			return false;
		if (!moduleSongMembersSafe(translated))
			return false;
		if (!moduleStoreMembersSafe(translated, stateFields, safeMapFields))
			return false;
		return true;
	}

	/**
		Module media is resolved once at import time, so an HXC module may only
		materialize an asset when its key is a literal. A dynamic key can depend on
		an arbitrary event/save value and is not enough evidence for the manifest
		planner; song/stage scopes retain the runtime's root-scoped dynamic adapter,
		but global modules stay rejected instead of being relabelled executable.
	*/
	static function hasUnsafeDynamicNativeAssetCall(source:String):Bool {
		if (source == null || source == '')
			return false;
		var calls:Array<{var name:String; var keyIndex:Int;}> = [
			{name: 'createFunkinSprite', keyIndex: 3},
			{name: 'createFunkinSpriteSparrow', keyIndex: 3},
			{name: 'createFunkinSpriteTextureAtlas', keyIndex: 3},
			{name: 'cacheFunkinTexture', keyIndex: 1},
			{name: 'loadFunkinSound', keyIndex: 1}
		];
		for (call in calls) {
			var search = 0;
			var attempts = 0;
			while (attempts++ < 128 && search < source.length) {
				var expression = new EReg('\\bHxcCompatRuntime\\s*\\.\\s*'
					+ call.name + '\\s*\\(', 'm');
				var remaining = source.substr(search);
				if (!expression.match(remaining))
					break;
				var position = expression.matchedPos();
				var callStart = search + position.pos;
				var open = source.indexOf('(', callStart);
				if (open < 0)
					break;
				var close = matchingDelimiter(source, open, '(', ')');
				if (close < 0)
					break;
				var parts = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
				if (parts.length > call.keyIndex) {
					var key = StringTools.trim(parts[call.keyIndex]);
					if (key != '' && key != 'null' && !isQuotedLiteral(key))
						return true;
				}
				if (position.len <= 0 || callStart + position.len >= source.length)
					break;
				search = callStart + position.len;
			}
		}
		return false;
	}

	static function isQuotedLiteral(value:String):Bool {
		if (value == null || value.length < 2)
			return false;
		var first = value.charAt(0);
		var last = value.charAt(value.length - 1);
		return (first == '"' && last == '"') || (first == "'" && last == "'");
	}

	/** State maps materialized by the explicit pure hxcMap adapter may use nested get/set. */
	static function safeStateMapFields(initializers:Array<HxcCompatStateInitializer>):Array<String> {
		var fields:Array<String> = [];
		if (initializers == null)
			return fields;
		for (initializer in initializers)
			if (initializer != null && initializer.name != null && initializer.value != null
				&& StringTools.trim(initializer.value).startsWith('hxcMap('))
				fields.push(initializer.name);
		return fields;
	}

	/** Track local aliases whose initializer is visibly the seeded PlayState. */
	static function modulePlayStateAliases(callbacks:Array<HxcCompatCallbackAdapter>,
		helpers:Array<HxcCompatCallbackAdapter>):Array<String> {
		var aliases:Array<String> = [];
		var bodies:Array<String> = [];
		if (callbacks != null)
			for (callback in callbacks)
				if (callback != null && callback.body != null)
					bodies.push(callback.body);
		if (helpers != null)
			for (helper in helpers)
				if (helper != null && helper.body != null)
					bodies.push(helper.body);
		var joined = bodies.join('\\n');
		if (joined == '')
			return aliases;
		for (alias in collectMatches(joined,
			'\\b(?:var|final)?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(?:PlayState\\s*\\.\\s*instance|currentPlayState)\\s*(?:[;,\\)])', 1))
			appendUnique(aliases, alias);
		var attempts = 0;
		while (attempts++ < 8) {
			var changed = false;
			for (alias in aliases)
				for (child in collectMatches(joined,
					'\\b(?:var|final)?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*'
					+ alias + '\\s*(?:[;,\\)])', 1))
					if (aliases.indexOf(child) < 0) {
						aliases.push(child);
						changed = true;
					}
			if (!changed)
				break;
		}
		return aliases;
	}

	/**
		The namespaced store is intentionally a small key/value surface. A nested
		option object or donor highscore lookup would require donor defaults and is
		therefore not executable merely because the outer `get()` call is present.
	*/
	static function moduleStoreMembersSafe(source:String, stateFields:Array<String>, ?safeMapFields:Array<String>):Bool {
		if (source == null || source == '')
			return true;
		var roots:Array<String> = ['__hxcStore'];
		if (stateFields != null)
			for (field in stateFields)
				if (field != null && field != '' && roots.indexOf(field) < 0)
					roots.push(field);
		for (root in roots) {
			if (safeMapFields != null && safeMapFields.indexOf(root) >= 0)
				continue;
			var escapedRoot = root;
			if (new EReg('\\b' + escapedRoot + '\\s*(?:\\.\\s*modOptions)?\\s*\\.\\s*hasBeatenSong\\s*\\(', 'm').match(source))
				return false;
			if (new EReg('\\b' + escapedRoot + '\\s*(?:\\.\\s*modOptions)?\\s*\\.\\s*get\\s*\\([^)]*\\)\\s*\\.', 'm').match(source))
				return false;
		}
		return true;
	}

	/** Collect only the first identifier in each dotted chain. */
	static function collectRootNames(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		var index = 0;
		var quote = '';
		var escaped = false;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (!isIdentifierStart(source.charAt(index))) {
				index++;
				continue;
			}
			if (index > 0 && (isIdentifierPart(source.charAt(index - 1))
				|| source.charAt(index - 1) == '.')) {
				index++;
				continue;
			}
			var end = index + 1;
			while (end < source.length && isIdentifierPart(source.charAt(end)))
				end++;
			var next = skipWhitespaceForward(source, end);
			if (next < source.length && source.charAt(next) == '.')
				appendUnique(result, source.substr(index, end - index));
			index = end;
		}
		return result;
	}

	static function collectUnqualifiedCalls(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		// A regexp sees string fragments such as `"ms"` and the parenthesized
		// iterable in `for (item in (items))` as calls.  Scan outside literals and
		// require an actual opening parenthesis after an unqualified identifier.
		var index = 0;
		var quote = '';
		var escaped = false;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (!isIdentifierStart(current)) {
				index++;
				continue;
			}
			var start = index;
			index++;
			while (index < source.length && isIdentifierPart(source.charAt(index)))
				index++;
			var name = source.substr(start, index - start);
			var before = start - 1;
			var next = skipWhitespaceForward(source, index);
			var isMember = before >= 0 && source.charAt(before) == '.';
			if (!isMember && next < source.length && source.charAt(next) == '(') {
				if (name != 'if' && name != 'for' && name != 'while' && name != 'switch'
					&& name != 'catch' && name != 'function' && name != 'return' && name != 'new'
					&& name != 'in')
					appendUnique(result, name);
			}
		}
		return result;
	}

	/** Reject donor-only PlayState members even when the root class itself exists. */
	static function modulePlayStateMembersSafe(source:String,
		?aliases:Array<String>):Bool {
		if (source == null || source == '')
			return true;
		var forbidden = new EReg('\\.(?:currentChart)\\b', 'm');
		if (forbidden.match(source))
			return false;
		var owners:Array<String> = ['PlayState\\s*\\.\\s*instance', 'currentPlayState'];
		if (aliases != null)
			for (alias in aliases)
				if (alias != null && isIdentifier(alias))
					owners.push(alias);
		var expression = new EReg('\\b(?:' + owners.join('|')
			+ ')\\s*((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 'gm');
		var offset = 0;
		var allowedFirst = [
			'currentStageId', 'curStage', 'currentStage', 'camHUD', 'camGame', 'boyfriend',
			'dad', 'gf', 'notes', 'currentKey', 'strumLine', 'camFollow', 'songEvents',
			'iconP1', 'iconP2', 'health', 'defaultCamZoom', 'forceCamera', 'playerStrums',
			'enemyStrums', 'playerStrumline', 'opponentStrumline', 'songPositionBar', 'timeBar', 'timeBarBG', 'songPosBar',
			'healthBar', 'healthBarBG', 'timeTxt', 'members', 'needsReset', 'SONG', 'instance', 'currentState',
			'currentSong', 'hxcCurrentChartNotes', 'currentCameraZoom', 'cameraFollowPoint', 'cameraFocusPoint', 'cameraZoomRate',
			'isMinimalMode', 'playbackRate', 'scoreText', 'songScore', 'camCutscene', 'song',
			'startTimestamp',
			'camZoomRate', 'cancelCameraFollowTween', 'tweenCameraToPosition',
			'isInCountdown',
			'add', 'remove', 'insert', 'refresh', 'swapStage', 'hxcGetCharacterData', 'hxcChangeCharacter',
				'hxcOptionalField', 'hxcOptionalCall', 'hxcOptionalSet', 'hxcCoalesce', 'hxcMap'
		];
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!expression.match(remaining))
				break;
			var chain = StringTools.replace(expression.matched(1), ' ', '');
			chain = StringTools.replace(chain, '\\t', '');
			if (chain.startsWith('.'))
				chain = chain.substr(1);
			var first = chain.indexOf('.') < 0 ? chain : chain.substr(0, chain.indexOf('.'));
			if (allowedFirst.indexOf(first) < 0) {
				return false;
			}
			var position = expression.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		return true;
	}

	/** Keep the active chart adapter limited to fields present on SwagSong. */
	static function moduleSongMembersSafe(source:String):Bool {
		if (source == null || source == '')
			return true;
		var allowed = [
			'song', 'songArtist', 'album', 'notes', 'bpm', 'needsVoices', 'speed', 'events', 'vocalStems',
			'offsets', 'stickerPack', 'getDifficulty',
			'player1', 'player2', 'stage', 'gf', 'isMoody', 'cutsceneType', 'uiType',
			'isSpooky', 'isHey', 'isCheer', 'preferredNoteAmount', 'forceJudgements',
			'forceLayout', 'uiLayoutType', 'convertMineToNuke', 'mania', 'stageID'
		];
		for (chain in collectMatches(source,
			'\\b[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*currentSong((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 1)) {
			var normalized = StringTools.replace(chain, ' ', '');
			if (normalized.startsWith('.'))
				normalized = normalized.substr(1);
			var first = normalized.indexOf('.') < 0 ? normalized : normalized.substr(0, normalized.indexOf('.'));
			if (allowed.indexOf(first) < 0)
				return false;
		}
		return true;
	}

	/**
		FreeplayState has native selection/difficulty boundaries, but it does not
		expose the donor V-Slice capsule/substate object graph. Keep the generic
		hook route available while rejecting code that would silently dereference
		that missing graph.
	*/
	static function moduleFreeplayMembersSafeLegacy(source:String):Bool {
		if (source == null || source == '')
			return true;
		// Only the explicit native Freeplay view is inspected here. Generic
		// `event`, `capsule`, and `state` names belong to lifecycle payloads and
		// are validated by payloadAdapterSafe instead; treating them as host state
		// was the source of several false module-body gaps.
		var roots:Array<String> = ['currentFreeplayState'];
		for (alias in collectMatches(source,
			'\\b(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*currentFreeplayState\\b', 1))
			appendUnique(roots, alias);
		// The native view deliberately exposes no donor capsule graph. These names
		// are listed explicitly so a future shallow field cannot accidentally make
		// an authored `.weekType`/mover traversal executable.
		var forbidden = [
			'grpCapsules', 'weekType', 'currentVariation', 'freeplayData', 'pixelIcon',
			'exitMovers', 'backingCard', '_parentState', 'capsuleOnConfirmDefault',
			'onConfirm', 'members', 'setCharacter', 'offset'
		];
		// Helpers receive the native Freeplay view through a local parameter (for
		// example `sub`/`cap`), so their donor graph is no longer rooted at
		// `currentFreeplayState`. Reject these graph-only member names wherever
		// they occur; ordinary event payload fields are checked separately below.
		for (field in ['grpCapsules', 'weekType', 'freeplayData', 'pixelIcon',
			'exitMovers', 'backingCard', '_parentState', 'capsuleOnConfirmDefault'])
			if (new EReg('\\.\\s*' + field + '\\b', 'm').match(source))
				return false;
		var allowed = [
			'targetState', 'subState', 'curSelected', 'busy', 'controls',
			'curDifficulty', 'curCategory', 'persistentUpdate', 'persistentDraw',
			'exitingMenu', 'selectedLevel'
		];
		for (root in roots) {
			var expression = new EReg('\\b' + root
				+ '((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 'gm');
			var offset = 0;
			while (offset < source.length) {
				var remaining = source.substr(offset);
				if (!expression.match(remaining))
					break;
				var chain = StringTools.replace(expression.matched(1), ' ', '');
				chain = StringTools.replace(chain, '\\t', '');
				if (chain.startsWith('.'))
					chain = chain.substr(1);
				var first = chain.indexOf('.') < 0 ? chain : chain.substr(0, chain.indexOf('.'));
				if (forbidden.indexOf(first) >= 0 || allowed.indexOf(first) < 0)
					return false;
				var position = expression.matchedPos();
				offset += position.pos + (position.len > 0 ? position.len : 1);
			}
		}
		return true;
	}

	/** Validate the deliberately shallow Freeplay state and capsule facade. */
	static function moduleFreeplayMembersSafe(source:String, ?arguments:Array<String>):Bool {
		if (source == null || source == '')
			return true;
		var stateRoots:Array<String> = ['currentFreeplayState'];
		var capsuleRoots:Array<String> = [];
		for (alias in collectMatches(source,
			'\\b(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(?:currentFreeplayState|[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*targetState)\\s*(?:;|,|\\))', 1))
			appendUnique(stateRoots, alias);
		for (alias in collectMatches(source,
			'\\b(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*[^;]*grpCapsules\\s*\\.\\s*members', 1))
			appendUnique(capsuleRoots, alias);
		for (alias in collectMatches(source,
			'\\bfor\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s+in\\s+[^)]*grpCapsules\\s*\\.\\s*members', 1))
			appendUnique(capsuleRoots, alias);
		if (arguments != null)
			for (argument in arguments) {
				if (argument == null || argument == '')
					continue;
				if (new EReg('\\b' + argument
					+ '\\s*\\.\\s*(?:grpCapsules|currentVariation|curSelected|curDifficulty|curCategory|controls|persistentUpdate|persistentDraw)\\b', 'm').match(source))
					appendUnique(stateRoots, argument);
				if (new EReg('\\b' + argument
					+ '\\s*\\.\\s*(?:freeplayData|pixelIcon|weekType|alive|onConfirm)\\b', 'm').match(source))
					appendUnique(capsuleRoots, argument);
				if (new EReg('\\b' + argument + '\\s*\\.\\s*capsule\\s*\\.', 'm').match(source))
					appendUnique(capsuleRoots, argument + '.capsule');
			}
		var sensitive = new EReg('(?:grpCapsules|weekType|currentVariation|freeplayData|pixelIcon|'
			+ 'exitMovers|backingCard|_parentState|capsuleOnConfirmDefault|onConfirm|members|setCharacter|offset|alive|'
			+ 'curSelected|curDifficulty|curCategory|controls|persistentUpdate|persistentDraw|subState|openSubState|busy|selectedLevel|exitingMenu)', 'm');
		var unsupportedUnscopedGraph = new EReg('(?:grpCapsules|weekType|pixelIcon|exitMovers|backingCard|'
			+ '_parentState|capsuleOnConfirmDefault|onConfirm)', 'm');
		var chainPattern = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 'gm');
		var offset = 0;
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!chainPattern.match(remaining))
				break;
			var chain = StringTools.replace(chainPattern.matched(2), ' ', '');
			chain = StringTools.replace(chain, '\\t', '');
			var root = chainPattern.matched(1);
			var isStateRoot = stateRoots.indexOf(root) >= 0;
			var isCapsuleRoot = capsuleRoots.indexOf(root) >= 0;
			var isEventArgument = arguments != null && arguments.indexOf(root) >= 0;
			var supported = true;
			if (sensitive.match(chain)) {
				if (isStateRoot)
					supported = freeplayStateChainSupported(chain);
				else if (isCapsuleRoot)
					supported = freeplayCapsuleChainSupported(chain);
				else if (isEventArgument && (StringTools.startsWith(chain, root + '.targetState.')
					|| chain == root + '.targetState'))
					supported = freeplayStateChainSupported(chain.substr((root + '.targetState').length));
				else if (isEventArgument && (StringTools.startsWith(chain, root + '.capsule.')
					|| chain == root + '.capsule'))
					supported = freeplayCapsuleChainSupported(chain.substr((root + '.capsule').length));
				else if (unsupportedUnscopedGraph.match(chain))
					supported = false;
				// This validator is only responsible for the missing V-Slice Freeplay
				// graph. Common properties such as `members`, `controls`, or
				// `setCharacter` on unrelated, independently validated host objects
				// must not make an otherwise safe module fail.
			}
			if (!supported)
				return false;
			var position = chainPattern.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		// The first chain scan ends at an indexed member expression. Validate the
		// tail separately, for example `members[index].pixelIcon.setCharacter`.
		var indexedTail = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)*)\\s*\\[[^\\]]*\\]((?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)+)', 'gm');
		offset = 0;
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!indexedTail.match(remaining))
				break;
			var root = indexedTail.matched(1);
			var base = StringTools.replace(indexedTail.matched(2), ' ', '');
			var tail = StringTools.replace(indexedTail.matched(3), ' ', '');
			var stateCollection = stateRoots.indexOf(root) >= 0
				&& freeplayStateChainSupported(base) && base.indexOf('.grpCapsules.members') >= 0;
			var eventCollection = arguments != null && arguments.indexOf(root) >= 0
				&& StringTools.startsWith(base, '.targetState.grpCapsules.members');
			if ((stateCollection || eventCollection)
				&& sensitive.match(tail) && !freeplayCapsuleChainSupported(tail)) {
				return false;
			}
			if (unsupportedUnscopedGraph.match(base + tail)
				&& !stateCollection && !eventCollection)
				return false;
			var position = indexedTail.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		return true;
	}

	static function freeplayStateChainSupported(chain:String):Bool {
		if (chain == null || chain == '')
			return true;
		return chain == '.targetState' || chain == '.subState' || chain == '.grpCapsules'
			|| chain == '.grpCapsules.members' || chain == '.grpCapsules.members.length'
			|| chain == '.currentVariation' || chain == '.curSelected' || chain == '.curDifficulty'
			|| chain == '.curCategory' || chain == '.busy'
			|| chain == '.controls' || chain == '.controls.active'
			|| chain == '.persistentUpdate' || chain == '.persistentDraw'
			|| chain == '.exitingMenu' || chain == '.selectedLevel'
			|| chain == '.capsuleOnConfirmDefault' || chain == '.openSubState';
	}

	static function freeplayCapsuleChainSupported(chain:String):Bool {
		if (chain == null || chain == '')
			return true;
		return chain == '.alive' || chain == '.onConfirm'
			|| chain == '.freeplayData' || chain == '.freeplayData.levelId'
			|| chain == '.freeplayData.songCharacter' || chain == '.freeplayData.data'
			|| chain == '.freeplayData.data.id'
			|| chain == '.pixelIcon' || chain == '.pixelIcon.character'
			|| chain == '.pixelIcon.setCharacter' || chain == '.pixelIcon.offset'
			|| chain == '.pixelIcon.offset.x'
			|| chain == '.weekType' || chain == '.weekType.visible'
			|| chain == '.weekType.frames' || chain == '.weekType.animation'
			|| chain == '.weekType.animation.addByPrefix'
			|| chain == '.weekType.animation.play';
	}

	/**
		Recognize a complete main-menu graph by its data/lifecycle shape.

		The pass intentionally does not key this on a class name, donor root, or
		filename. A menu must declare a literal option array, have a create/update
		lifecycle, and expose both Story and Freeplay routes. Unknown labels remain
		selectable no-ops in the resulting data spec.
	*/
	static function detectMenuSpec(source:String, kind:String):Null<HxcCompatMenuPlan> {
		if (source == null || (kind != 'module' && kind != 'state'))
			return null;
		var options = collectMenuStringArray(source);
		if (options.length < 2)
			return null;
		if (!new EReg('\\b(?:function\\s+)?(?:onUpdate|update)\\s*\\(', 'm').match(source)
			|| !new EReg('\\b(?:function\\s+)?(?:onStateChangeEnd|create|start)\\s*\\(', 'm').match(source))
			return null;
		var items:Array<HxcMenuItemSpec> = [];
		var hasStory = false;
		var hasFreeplay = false;
		for (label in options) {
			var route = HxcMenuSpec.routeForLabel(label);
			if (route == HxcMenuSpec.ROUTE_STORY)
				hasStory = true;
			if (route == HxcMenuSpec.ROUTE_FREEPLAY)
				hasFreeplay = true;
			var target = menuTargetForLabel(source, label);
			items.push({id: HxcMenuSpec.normalize(label), label: label, route: target == '' ? route : HxcMenuSpec.ROUTE_IMPORTED,
				target: target});
		}
		if (!hasStory || !hasFreeplay)
			return null;

		var style = new EReg('(?:_button0|_button_sel0|menu/buttons)', 'i').match(source)
			? HxcMenuSpec.STYLE_BUTTON : HxcMenuSpec.STYLE_TEXT;
		var background = firstMenuAsset(source, 'image', '');
		var atlas = style == HxcMenuSpec.STYLE_BUTTON
			? firstMenuAsset(source, 'atlas', 'button') : '';
		var font = firstMenuAsset(source, 'font', '');
		if (background == '')
			return null;
		var required:Array<String> = ['images/' + stripExtension(background) + '.png'];
		if (style == HxcMenuSpec.STYLE_BUTTON && atlas != '') {
			required.push('images/' + stripExtension(atlas) + '.png');
			required.push('images/' + stripExtension(atlas) + '.xml');
		}
		if (font != '')
			required.push('fonts/' + font);
		return {
			id: 'hxc-main-menu',
			style: style,
			items: items,
			background: background,
			atlas: atlas,
			font: font,
			// These are suffixes applied to a normalized item id by the native
			// renderer (for example `story_button0`).  They are data, not donor
			// animation objects or executable frame names.
			itemPrefix: style == HxcMenuSpec.STYLE_BUTTON ? '_button0' : '',
			selectedPrefix: style == HxcMenuSpec.STYLE_BUTTON ? '_button_sel0' : '',
			fontSize: style == HxcMenuSpec.STYLE_BUTTON ? 28 : 27,
			requiredAssets: required
		};
	}

	/**
		Recognize the complete helper + substate-open shape used by imported pause
		modules.  The result contains only literal asset/configuration data; donor
		metadata, menu-entry callbacks, and character branches are intentionally not
		carried into the interpreter.
	*/
	static function detectPauseSpec(source:String, kind:String):Null<HxcCompatPausePlan> {
		if (source == null || kind != 'module')
			return null;
		var complete = new EReg('\\b(?:function\\s+)?createUniversalMenu\\s*\\(', 'm').match(source)
			&& new EReg('\\b(?:function\\s+)?onSubStateOpenEnd\\s*\\(', 'm').match(source)
			&& new EReg('\\b(?:function\\s+)?onSubStateCloseBegin\\s*\\(', 'm').match(source)
			&& source.indexOf('targetPauseState') >= 0
			&& source.indexOf('currentMenuEntries') >= 0
			&& source.indexOf('menuEntryText') >= 0
			&& source.indexOf('metadata') >= 0
			&& new EReg('\\bnew\\s+FlxText\\s*\\(', 'm').match(source)
			&& new EReg('Paths\\s*\\.\\s*image\\s*\\(', 'm').match(source)
			&& new EReg('Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(', 'm').match(source)
			&& new EReg('Paths\\s*\\.\\s*font\\s*\\(', 'm').match(source)
			&& new EReg('Change\\s+Difficulty', 'i').match(source);
		if (!complete)
			return null;
		var artPrefix = firstString(source,
			'Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']*)["\\\']\\s*\\+');
		if (artPrefix == '')
			return null;
		var logo = firstStaticPauseAsset(source, 'image');
		var atlas = firstMenuAsset(source, 'atlas', 'DDLCStart');
		var fonts = collectMatches(source,
			'Paths\\s*\\.\\s*font\\s*\\(\\s*["\\\']([^"\\\']+)', 1);
		var titleFont = fonts.length > 0 ? fonts[0] : '';
		var menuFont = fonts.length > 1 ? fonts[fonts.length - 1] : titleFont;
		var itemColor = literalInt(firstString(source,
			'\\b(?:var\\s+)?itmColor\\s*:\\s*Int\\s*=\\s*(0x[0-9A-Fa-f]+)'));
		var selectedColor = literalInt(firstString(source,
			'\\b(?:var\\s+)?selColor\\s*:\\s*Int\\s*=\\s*(0x[0-9A-Fa-f]+)'));
		var deathLabel = firstString(source,
			'var\\s+deathType\\s*=\\s*["\\\']([^"\\\']+)["\\\']');
		var practiceLabel = firstString(source,
			'new\\s+FlxText\\s*\\([^;]*["\\\'](Practice Mode)["\\\']');
		var hiddenLabels:Array<String> = [];
		for (label in collectMatches(source,
			'entry\\.text\\s*==\\s*["\\\']([^"\\\']+)["\\\']', 1))
			appendUnique(hiddenLabels, label);
		if (logo == '' || atlas == '' || titleFont == '' || menuFont == '')
			return null;
		var required:Array<String> = [
			'images/' + stripExtension(logo) + '.png',
			'images/' + stripExtension(atlas) + '.png',
			'images/' + stripExtension(atlas) + '.xml',
			'fonts/' + titleFont,
			'fonts/' + menuFont
		];
		return {
			id: 'hxc-pause-overlay',
			artPrefix: artPrefix,
			logo: logo,
			atlas: atlas,
			logoAnimation: 'logo bumpin',
			titleFont: titleFont,
			menuFont: menuFont,
			deathLabel: deathLabel,
			practiceLabel: practiceLabel,
			hiddenLabels: hiddenLabels,
			itemColor: itemColor,
			selectedColor: selectedColor,
			fontSize: 32,
			menuFontSize: 27,
			requiredAssets: required
		};
	}

	/**
		Extract the small perfect-hit text-cue vocabulary from any Module-shaped
		HXC file. The module/class/path names never choose this route: acceptance is
		based on the connected literal song/chance/line tables, nested judgement
		gate, text-construction style, and strict step-expiry shape.
	*/
	static function detectNoteTextSpec(source:String, kind:String):Null<HxcNoteTextSpecData> {
		if (source == null || kind != 'module')
			return null;
		var declarations = collectStateDeclarations(source);
		var declarationByName:Map<String, HxcCompatStateDeclaration> = new Map<String, HxcCompatStateDeclaration>();
		for (declaration in declarations)
			if (declaration != null && declaration.name != null)
				declarationByName.set(declaration.name, declaration);

		var chartSongId = 'PlayState\\s*\\.\\s*instance\\s*\\.\\s*currentChart\\s*\\.\\s*song\\s*\\.\\s*id';
		var songTables:Array<{var name:String; var values:Array<String>;}>=[];
		for (declaration in declarations) {
			if (declaration == null || declaration.name == null)
				continue;
			var values = parseLiteralStringArray(declaration.initializer);
			if (values == null || values.length == 0)
				continue;
			var lookup = new EReg('\\b' + declaration.name + '\\s*\\.\\s*indexOf\\s*\\(\\s*'
				+ chartSongId + '\\s*\\)', 'm');
			if (lookup.match(source))
				songTables.push({name:declaration.name, values:values});
		}
		if (songTables.length != 1)
			return null;
		var songTable = songTables[0];

		var methods = collectFunctions(source);
		var noteHit:HxcCompatFunction = null;
		var onUpdate:HxcCompatFunction = null;
		var getterByName:Map<String, HxcCompatFunction> = new Map<String, HxcCompatFunction>();
		for (method in methods) {
			if (method == null || method.name == null)
				continue;
			switch (method.name.toLowerCase()) {
				case 'onnotehit':
					if (noteHit != null) return null;
					noteHit = method;
				case 'onupdate':
					if (onUpdate != null) return null;
					onUpdate = method;
				default:
					getterByName.set(method.name, method);
			}
		}
		if (noteHit == null || onUpdate == null || noteHit.arguments == null || noteHit.arguments.length == 0)
			return null;
		var eventName = noteHit.arguments[0];
		var perfectGate = new EReg('\\b' + eventName + '\\s*\\.\\s*judgement\\s*==\\s*["\\\']perfect["\\\']', 'i');
		var perfectBlocks:Array<HxcCompatIfBlock> = [];
		for (block in collectIfBlocks(noteHit.body))
			if (perfectGate.match(block.condition))
				perfectBlocks.push(block);
		if (perfectBlocks.length == 0)
			return null;

		var chanceTables:Array<{var name:String; var values:Array<Float>;}>=[];
		for (declaration in declarations) {
			if (declaration == null || declaration.name == null)
				continue;
			var values = parseLiteralNumberArray(declaration.initializer);
			if (values == null || values.length != songTable.values.length)
				continue;
			var use = new EReg('\\brandom\\s*\\.\\s*bool\\s*\\(\\s*' + declaration.name
				+ '\\s*\\[\\s*' + songTable.name + '\\s*\\.\\s*indexOf\\s*\\(\\s*'
				+ chartSongId + '\\s*\\)\\s*\\]\\s*\\)', 'i');
			if (use.match(noteHit.body))
				chanceTables.push({name:declaration.name, values:values});
		}
		if (chanceTables.length != 1)
			return null;
		var chanceTable = chanceTables[0];
		var chanceBlocks:Array<HxcCompatIfBlock> = [];
		var chanceUse = new EReg('\\brandom\\s*\\.\\s*bool\\s*\\(\\s*'
			+ chanceTable.name + '\\s*\\[\\s*' + songTable.name
			+ '\\s*\\.\\s*indexOf\\s*\\(\\s*' + chartSongId + '\\s*\\)\\s*\\]\\s*\\)', 'i');
		for (perfectBlock in perfectBlocks)
			{
			for (block in collectIfBlocks(perfectBlock.body)) {
				if (chanceUse.match(block.condition))
					chanceBlocks.push(block);
			}
			}
		if (chanceBlocks.length == 0)
			return null;

		var latchName = '';
		for (declaration in declarations) {
			if (declaration == null || declaration.name == null
				|| StringTools.trim(declaration.initializer).toLowerCase() != 'false')
				continue;
			var usedAsChanceLatch = false;
			for (block in chanceBlocks)
				if (new EReg('!\\s*' + declaration.name + '\\b', 'm').match(block.condition))
					usedAsChanceLatch = true;
			if (usedAsChanceLatch) {
				if (latchName != '') return null;
				latchName = declaration.name;
			}
		}
		if (latchName == '')
			return null;

		var helperName = '';
		var lineGetterName = '';
		for (block in chanceBlocks) {
				var latchUse = new EReg('!\\s*' + latchName + '\\b', 'm');
				if (!latchUse.match(block.condition))
					continue;
				var textCall = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*'
					+ '([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*\\)\\s*,\\s*null\\s*,\\s*null\\s*\\)', 'm');
				if (!textCall.match(block.body))
					continue;
				if (helperName != '') return null;
				helperName = textCall.matched(1);
				lineGetterName = textCall.matched(2);
		}
		if (helperName == '' || lineGetterName == '')
			return null;
		var helper:HxcCompatFunction = getterByName.get(helperName);
		var lineGetter:HxcCompatFunction = getterByName.get(lineGetterName);
		if (helper == null || lineGetter == null || helper.arguments == null || helper.arguments.length < 3)
			return null;
		for (method in methods)
			if (method != null && method.name != null
				&& method.name.toLowerCase() != 'onnotehit'
				&& method.name.toLowerCase() != 'onnotemiss'
				&& method.name.toLowerCase() != 'onmissnote'
				&& new EReg('\\b' + helperName + '\\s*\\(', 'm').match(method.body))
				return null;

		var lineTable = parseNoteTextLineTable(lineGetter.body, songTable.name,
			chartSongId, songTable.values.length);
		if (lineTable == null)
			return null;
		var missRules = detectNoteTextMissRules(methods, declarations, helperName,
			latchName, songTable.values, chartSongId);
		var textStyle = extractNoteTextStyle(helper.body, helper.arguments[0]);
		if (textStyle == null)
			return null;
		var staticOverlay = extractNoteTextStaticOverlay(source, helper.body, helper.arguments[0]);
		if (new EReg('\\bnew\\s+FlxSprite\\s*\\(', 'm').match(source)
			&& staticOverlay == null)
			return null;

		var createTextStep = new EReg('\\b' + textStyle.stepField
			+ '\\s*=\\s*Conductor\\s*\\.\\s*instance\\s*\\.\\s*currentStep', 'm');
		var createTextLatch = new EReg('\\b' + latchName + '\\s*=\\s*true\\b', 'm');
		if (!createTextStep.match(helper.body) || !createTextLatch.match(helper.body))
			return null;

		var expiryFound = false;
		var lifetimeSteps = 0;
		for (block in collectIfBlocks(onUpdate.body)) {
			var expiry = new EReg('\\b' + latchName + '\\b[^\\n{};]*?\\b'
				+ textStyle.stepField + '\\s*\\+\\s*([0-9]+)\\s*<\\s*Conductor\\s*\\.\\s*instance'
				+ '\\s*\\.\\s*currentStep', 'm');
			if (!expiry.match(block.condition))
				continue;
			if (!hasCompleteNoteTextExpiry(source, block.body, textStyle.textField, latchName, declarations))
				continue;
			if (expiryFound)
				return null;
			expiryFound = true;
			lifetimeSteps = Std.parseInt(expiry.matched(1));
		}
		if (!expiryFound || lifetimeSteps < 1 || lifetimeSteps > HxcNoteTextSpec.MAX_LIFETIME_STEPS)
			return null;
		var stepDeclaration = declarationByName.get(textStyle.stepField);
		if (stepDeclaration == null || !new EReg('^[-+]?\\d+$', '').match(StringTools.trim(stepDeclaration.initializer)))
			return null;

		var rules:Array<HxcNoteTextRule> = [];
		for (index in 0...songTable.values.length)
			rules.push({songId:songTable.values[index], chancePercent:chanceTable.values[index], lines:lineTable[index]});
		var candidate:HxcNoteTextSpecData = {
			rules: rules,
			triggerJudgement: 'perfect',
			perfectOnly: true,
			onceAtATime: true,
			lifetimeSteps: lifetimeSteps,
			expireStrictlyAfter: true,
			anchor: 'opponent',
			xOffsetMin: textStyle.xMin,
			xOffsetMax: textStyle.xMax,
			yOffsetMin: textStyle.yMin,
			yOffsetMax: textStyle.yMax,
			font: textStyle.font,
			fontSize: textStyle.fontSize,
			color: textStyle.color,
			bold: true,
			zIndex: textStyle.zIndex,
			staticOverlay: staticOverlay
		};
		if (missRules != null)
			candidate.missRules = missRules;
		return HxcNoteTextSpec.fromDynamic(candidate);
	}

	/** Accept a literal, song-gated miss branch using the same text owner. */
	static function detectNoteTextMissRules(methods:Array<HxcCompatFunction>,
		declarations:Array<HxcCompatStateDeclaration>, helperName:String, latchName:String,
		songIds:Array<String>, chartSongId:String):Null<Array<HxcNoteTextRule>> {
		var miss:HxcCompatFunction = null;
		for (method in methods)
			if (method != null && method.name != null
				&& (method.name.toLowerCase() == 'onnotemiss' || method.name.toLowerCase() == 'onmissnote')) {
				if (miss != null) return null;
				miss = method;
			}
		if (miss == null)
			return null;
		var chanceGate = new EReg('^\\s*FlxG\\s*\\.\\s*random\\s*\\.\\s*bool\\s*\\(\\s*'
			+ chartSongId + '\\s*==\\s*["\\\']([^"\\\']+)["\\\']\\s*\\?\\s*'
			+ '([0-9]+(?:\\.[0-9]+)?)\\s*:\\s*0\\s*\\)\\s*&&\\s*!\\s*'
			+ latchName + '\\s*$', 'm');
		var helperCall = new EReg('\\b' + helperName
			+ '\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*,\\s*null\\s*,\\s*null\\s*\\)', 'm');
		var rules:Array<HxcNoteTextRule> = [];
		for (block in collectIfBlocks(miss.body)) {
			if (!chanceGate.match(block.condition) || !helperCall.match(block.body))
				continue;
			if (rules.length > 0)
				return null;
			var songId = chanceGate.matched(1);
			var chance = noteTextLiteralNumber(chanceGate.matched(2));
			var linesField = helperCall.matched(1);
			if (songIds.indexOf(songId) < 0 || chance == null || chance <= 0 || chance > 100)
				return null;
			var lines:Array<String> = null;
			for (declaration in declarations)
				if (declaration != null && declaration.name == linesField) {
					if (lines != null) return null;
					lines = parseLiteralStringArray(declaration.initializer);
				}
			if (lines == null || lines.length == 0)
				return null;
			rules.push({songId:songId, chancePercent:chance, lines:lines});
		}
		return rules.length == 1 ? rules : null;
	}

	/** Extract one complete literal animated overlay attached to a note cue. */
	static function extractNoteTextStaticOverlay(source:String, textHelper:String,
		textListParameter:String):Null<HxcNoteTextStaticOverlayData> {
		if (source == null || textHelper == null || textListParameter == null || textListParameter == '')
			return null;
		var spriteNames = collectMatches(source,
			'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+FlxSprite\\s*\\(\\s*\\)\\s*\\.\\s*loadGraphic\\s*\\(', 1);
		if (spriteNames.length != 1)
			return null;
		var sprite = spriteNames[0];
		var graphicArgs = noteTextCallArguments(source, new EReg('\\b' + sprite
			+ '\\s*=\\s*new\\s+FlxSprite\\s*\\(\\s*\\)\\s*\\.\\s*loadGraphic\\s*\\(', 'm'));
		if (graphicArgs == null || graphicArgs.length != 4 || StringTools.trim(graphicArgs[1]) != 'true')
			return null;
		var imageKey = firstString(graphicArgs[0], '^\\s*Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)\\s*$');
		var width = noteTextLiteralInt(graphicArgs[2]);
		var height = noteTextLiteralInt(graphicArgs[3]);
		if (imageKey == '' || width == null || height == null)
			return null;

		var animationArgs = noteTextCallArguments(source, new EReg('\\b' + sprite
			+ '\\s*\\.\\s*animation\\s*\\.\\s*add\\s*\\(', 'm'));
		if (animationArgs == null || animationArgs.length != 4)
			return null;
		var frameExpression = StringTools.trim(animationArgs[1]);
		if (frameExpression.length < 2 || frameExpression.charAt(0) != '['
			|| matchingDelimiter(frameExpression, 0, '[', ']') != frameExpression.length - 1)
			return null;
		var frames = literalIntArray(frameExpression.substr(1, frameExpression.length - 2));
		var fps = noteTextLiteralNumber(animationArgs[2]);
		var loopText = StringTools.trim(animationArgs[3]);
		if (frames == null || frames.length == 0 || fps == null
			|| (loopText != 'true' && loopText != 'false'))
			return null;

		var scaleArgs = noteTextCallArguments(source, new EReg('\\b' + sprite
			+ '\\s*\\.\\s*scale\\s*\\.\\s*set\\s*\\(', 'm'));
		if (scaleArgs == null || scaleArgs.length != 2)
			return null;
		var scaleX = noteTextLiteralNumber(scaleArgs[0]);
		var scaleY = noteTextLiteralNumber(scaleArgs[1]);
		if (scaleX == null || scaleY == null)
			return null;

		var cameraAssignments = collectMatches(source,
			'\\b' + sprite + '\\s*\\.\\s*cameras\\s*=\\s*\\[([^\\]]*)\\]', 1);
		if (cameraAssignments.length == 0)
			return null;
		var lastCameraAssignment = StringTools.replace(StringTools.trim(cameraAssignments[cameraAssignments.length - 1]), ' ', '');
		lastCameraAssignment = StringTools.replace(lastCameraAssignment, '\\t', '');
		if (lastCameraAssignment != 'PlayState.instance.camHUD' && lastCameraAssignment != 'camHUD')
			return null;

		var idleText = firstString(source, '\\b' + sprite + '\\s*\\.\\s*alpha\\s*=\\s*(0(?:\\.0*)?)\\b');
		var hitText = firstString(textHelper, '\\b' + sprite + '\\s*\\.\\s*alpha\\s*=\\s*'
			+ '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))');
		var flicker = new EReg('\\b' + sprite + '\\s*\\.\\s*alpha\\s*=\\s*FlxG\\s*\\.\\s*random\\s*\\.\\s*float\\s*\\(\\s*'
			+ '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))\\s*,\\s*'
			+ '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))\\s*\\)', 'm');
		if (idleText == '' || hitText == '' || !flicker.match(source))
			return null;
		var idleAlpha = noteTextLiteralNumber(idleText);
		var hitAlpha = noteTextLiteralNumber(hitText);
		var flickerMin = noteTextLiteralNumber(flicker.matched(1));
		var flickerMax = noteTextLiteralNumber(flicker.matched(2));
		if (idleAlpha == null || hitAlpha == null || flickerMin == null || flickerMax == null)
			return null;

		var emptyTextGate = new EReg('\\bif\\s*\\(\\s*' + textListParameter
			+ '\\s*\\.\\s*length\\s*>\\s*0\\s*\\)', 'm');
		var hitAssignment = new EReg('\\b' + sprite + '\\s*\\.\\s*alpha\\s*=\\s*'
			+ '[+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)', 'm');
		if (!emptyTextGate.match(textHelper) || !hitAssignment.match(textHelper)
			|| hitAssignment.matchedPos().pos > emptyTextGate.matchedPos().pos
			|| new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*(?:insert\\s*\\(\\s*[^,]+,\\s*'
				+ sprite + '\\s*\\)|add\\s*\\(\\s*' + sprite + '\\s*\\))', 'm').match(source) == false)
			return null;

		var soundKey = firstString(textHelper,
			'\\bFlxG\\s*\\.\\s*sound\\s*\\.\\s*play\\s*\\(\\s*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var sound = soundKey == '' ? '' : 'sounds/' + soundKey + '.ogg';
		var overlay:HxcNoteTextStaticOverlayData = {
			image: 'images/' + imageKey + '.png',
			frameWidth: width,
			frameHeight: height,
			frames: frames,
			fps: fps,
			loop: loopText == 'true',
			scaleX: scaleX,
			scaleY: scaleY,
			camera: 'hud',
			idleAlpha: idleAlpha,
			hitAlpha: hitAlpha,
			flickerMin: flickerMin,
			flickerMax: flickerMax
		};
		if (sound != '')
			overlay.sound = sound;
		return overlay;
	}

	static function noteTextCallArguments(source:String, callPattern:EReg):Array<String> {
		if (source == null || callPattern == null || !callPattern.match(source))
			return null;
		var position = callPattern.matchedPos();
		var matched = source.substr(position.pos, position.len);
		var open = position.pos + matched.lastIndexOf('(');
		var close = open < 0 ? -1 : matchingDelimiter(source, open, '(', ')');
		return close < 0 ? null : splitTopLevel(source.substr(open + 1, close - open - 1), ',');
	}

	static function noteTextLiteralInt(value:String):Null<Int> {
		var clean = StringTools.trim(value == null ? '' : value);
		if (!new EReg('^\\+?\\d+$', '').match(clean))
			return null;
		var parsed = Std.parseInt(clean);
		return parsed == null ? null : parsed;
	}

	static function noteTextLiteralNumber(value:String):Null<Float> {
		var clean = StringTools.trim(value == null ? '' : value);
		if (!new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', '').match(clean))
			return null;
		var parsed = Std.parseFloat(clean);
		return Math.isNaN(parsed) ? null : parsed;
	}

	static function hasCompleteNoteTextExpiry(source:String, body:String, textField:String, latchName:String,
		declarations:Array<HxcCompatStateDeclaration>):Bool {
		var remove = new EReg('\\.\\s*remove\\s*\\(\\s*' + textField + '\\s*\\)', 'm');
		var resetLatch = new EReg('\\b' + latchName + '\\s*=\\s*false\\b', 'm');
		var refresh = new EReg('\\.\\s*refresh\\s*\\(', 'm');
		if (!resetLatch.match(body) || !refresh.match(body))
			return false;
		var nestedRemoval = false;
		for (block in collectIfBlocks(body))
			if (remove.match(block.body)) {
				nestedRemoval = true;
				if (!resetLatch.match(block.body) || !refresh.match(block.body))
					continue;
				var condition = StringTools.trim(block.condition);
				var flag = new EReg('^(!)?\\s*([A-Za-z_][A-Za-z0-9_]*)$', 'm');
				if (!flag.match(condition))
					return false;
				var flagName = flag.matched(2);
				var declaration:HxcCompatStateDeclaration = null;
				for (candidate in declarations)
					if (candidate != null && candidate.name == flagName) {
						declaration = candidate;
						break;
					}
				if (declaration == null)
					return false;
				var initializer = StringTools.trim(declaration.initializer).toLowerCase();
				if (initializer != 'true' && initializer != 'false')
					return false;
				var expected = flag.matched(1) == '!' ? initializer != 'true' : initializer == 'true';
				if (!expected || !allBooleanAssignmentsEqual(source, flagName, initializer))
					return false;
				return true;
			}
		return !nestedRemoval && remove.match(body);
	}

	static function allBooleanAssignmentsEqual(source:String, name:String, expected:String):Bool {
		var assignments = new EReg('\\b' + name + '\\s*=\\s*(true|false)\\b', 'g');
		var anyAssignment = new EReg('\\b' + name + '\\s*=', 'g');
		var count = 0;
		var matchedCount = 0;
		var offset = 0;
		while (offset < source.length && assignments.match(source.substr(offset))) {
			var position = assignments.matchedPos();
			matchedCount++;
			count++;
			if (assignments.matched(1) != expected)
				return false;
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		offset = 0;
		while (offset < source.length && anyAssignment.match(source.substr(offset))) {
			var position = anyAssignment.matchedPos();
			count++;
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		// `count` includes both counters; each assignment must be a literal write.
		return matchedCount > 0 && count == matchedCount * 2;
	}

	static function parseLiteralNumberArray(expression:String):Array<Float> {
		if (expression == null)
			return null;
		var value = StringTools.trim(expression);
		if (value.length < 2 || value.charAt(0) != '['
			|| matchingDelimiter(value, 0, '[', ']') != value.length - 1)
			return null;
		var output:Array<Float> = [];
		for (part in splitTopLevel(value.substr(1, value.length - 2), ',')) {
			var item = StringTools.trim(part);
			if (!new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', '').match(item))
				return null;
			var number = Std.parseFloat(item);
			if (Math.isNaN(number) || number < 0 || number > 100)
				return null;
			output.push(number);
		}
		return output;
	}

	static function parseNoteTextLineTable(source:String, songTable:String,
		chartSongIdPattern:String, expectedCount:Int):Null<Array<Array<String>>> {
		var switchHeader = new EReg('\\bswitch\\s*\\(\\s*' + songTable
			+ '\\s*\\.\\s*indexOf\\s*\\(\\s*' + chartSongIdPattern
			+ '\\s*\\)\\s*\\)\\s*\\{', 'm');
		if (source == null || !switchHeader.match(source))
			return null;
		var switchPosition = switchHeader.matchedPos();
		var open = source.indexOf('{', switchPosition.pos);
		var close = open < 0 ? -1 : matchingDelimiter(source, open, '{', '}');
		if (close < 0)
			return null;
		var body = source.substr(open + 1, close - open - 1);
		if (new EReg('\\bdefault\\s*:', 'm').match(body))
			return null;
		var headers:Array<{var index:Int; var start:Int; var end:Int;}> = [];
		var caseHeader = new EReg('\\bcase\\s+([0-9]+)\\s*:', 'gm');
		var cursor = 0;
		while (cursor < body.length) {
			var rest = body.substr(cursor);
			if (!caseHeader.match(rest))
				break;
			var position = caseHeader.matchedPos();
			var start = cursor + position.pos;
			var end = start + position.len;
			var index = Std.parseInt(caseHeader.matched(1));
			headers.push({index:index, start:start, end:end});
			cursor = end;
		}
		if (headers.length != expectedCount)
			return null;
		var output:Array<Array<String>> = [];
		for (index in 0...expectedCount)
			output.push(null);
		for (caseIndex in 0...headers.length) {
			var header = headers[caseIndex];
			if (header.index < 0 || header.index >= expectedCount || output[header.index] != null)
				return null;
			var end = caseIndex + 1 < headers.length ? headers[caseIndex + 1].start : body.length;
			var value = StringTools.trim(body.substr(header.end, end - header.end));
			while (value.endsWith(';'))
				value = StringTools.trim(value.substr(0, value.length - 1));
			if (value.startsWith('return '))
				value = StringTools.trim(value.substr('return '.length));
			output[header.index] = parseLiteralStringArray(value);
			if (output[header.index] == null)
				return null;
		}
		for (lines in output)
			if (lines == null)
				return null;
		return output;
	}

	static function extractNoteTextStyle(source:String, textListParameter:String):Dynamic {
		if (source == null || textListParameter == null || textListParameter == '')
			return null;
		var selected = new EReg('\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*'
			+ textListParameter + '\\s*\\[\\s*FlxG\\s*\\.\\s*random\\s*\\.\\s*int\\s*\\(\\s*0\\s*,\\s*'
			+ textListParameter + '\\s*\\.\\s*length\\s*-\\s*1\\s*\\)\\s*\\]', 'm');
		if (!selected.match(source))
			return null;
		var lineVariable = selected.matched(1);
		var created = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+FlxText\\s*\\(', 'm');
		if (!created.match(source))
			return null;
		var textField = created.matched(1);
		var args = callArguments(source, 'FlxText', true);
		if (args == null || args.length < 2)
			return null;
		var x = parseOpponentOffset(args[0], 'x');
		var y = parseOpponentOffset(args[1], 'y');
		if (x == null || y == null)
			return null;
		var format = new EReg('\\.\\s*setFormat\\s*\\(\\s*Paths\\s*\\.\\s*font\\s*\\(\\s*["\\\']([^"\\\']+)'
			+ '["\\\']\\s*\\)\\s*,\\s*([0-9]+)\\s*,\\s*(0x[0-9a-fA-F]+|-?[0-9]+)', 'm');
		if (!format.match(source))
			return null;
		var font = format.matched(1);
		var fontSize = Std.parseInt(format.matched(2));
		var color = literalInt(format.matched(3));
		var zIndex = firstString(source, '\\b' + textField + '\\s*\\.\\s*zIndex\\s*=\\s*(-?[0-9]+)');
		if (zIndex == '' || !new EReg('\\b' + textField + '\\s*\\.\\s*bold\\s*=\\s*true', 'm').match(source)
			|| !new EReg('\\b' + textField + '\\s*\\.\\s*text\\s*=\\s*' + lineVariable + '\\b', 'm').match(source)
			|| !new EReg('\\.\\s*add\\s*\\(\\s*' + textField + '\\s*\\)', 'm').match(source)
			|| !new EReg('\\.\\s*refresh\\s*\\(', 'm').match(source))
			return null;
		return {
			textField: textField,
			stepField: firstString(source, '\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*Conductor\\s*\\.\\s*instance\\s*\\.\\s*currentStep'),
			font: font,
			fontSize: fontSize,
			color: color,
			zIndex: Std.parseInt(zIndex),
			xMin: x.min,
			xMax: x.max,
			yMin: y.min,
			yMax: y.max
		};
	}

	static function parseOpponentOffset(value:String, axis:String):Dynamic {
		var property = axis == 'x' ? 'x' : 'y';
		var expression = new EReg('stage\\s*\\.\\s*getDad\\s*\\(\\s*\\)\\s*\\.\\s*'
			+ property + '\\s*\\+\\s*FlxG\\s*\\.\\s*random\\s*\\.\\s*float\\s*\\(\\s*'
			+ '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))\\s*,\\s*'
			+ '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))\\s*\\)', 'm');
		if (!expression.match(value))
			return null;
		var min = Std.parseFloat(expression.matched(1));
		var max = Std.parseFloat(expression.matched(2));
		if (Math.isNaN(min) || Math.isNaN(max) || min < 0 || max < min
			|| max > HxcNoteTextSpec.MAX_OFFSET)
			return null;
		return {min:min, max:max};
	}

	static function callArguments(source:String, name:String, requireNew:Bool):Array<String> {
		if (source == null || name == null)
			return null;
		var prefix = requireNew ? '(?:new\\s+)?' : '';
		var expression = new EReg(prefix + '\\b' + name + '\\s*\\(', 'm');
		if (!expression.match(source))
			return null;
		var position = expression.matchedPos();
		var open = source.indexOf('(', position.pos);
		var close = open < 0 ? -1 : matchingDelimiter(source, open, '(', ')');
		return close < 0 ? null : splitTopLevel(source.substr(open + 1, close - open - 1), ',');
	}

	static function collectIfBlocks(source:String):Array<HxcCompatIfBlock> {
		var output:Array<HxcCompatIfBlock> = [];
		if (source == null || source == '')
			return output;
		var expression = new EReg('\\bif\\s*\\(', 'm');
		var offset = 0;
		while (offset < source.length) {
			var rest = source.substr(offset);
			if (!expression.match(rest))
				break;
			var position = expression.matchedPos();
			var start = offset + position.pos;
			var open = source.indexOf('(', start);
			var close = open < 0 ? -1 : matchingDelimiter(source, open, '(', ')');
			if (close < 0)
				break;
			var bodyStart = close + 1;
			while (bodyStart < source.length && isWhitespace(source.charAt(bodyStart)))
				bodyStart++;
			if (bodyStart < source.length && source.charAt(bodyStart) == '{') {
				var bodyEnd = matchingDelimiter(source, bodyStart, '{', '}');
				if (bodyEnd < 0)
					break;
				var body = source.substr(bodyStart + 1, bodyEnd - bodyStart - 1);
				output.push({condition:source.substr(open + 1, close - open - 1), body:body});
				for (child in collectIfBlocks(body))
					output.push(child);
				offset = bodyEnd + 1;
			} else {
				var bodyEnd = findStatementEnd(source, bodyStart);
				if (bodyEnd < 0)
					bodyEnd = source.length;
				var body = source.substr(bodyStart, bodyEnd - bodyStart);
				output.push({condition:source.substr(open + 1, close - open - 1), body:body});
				for (child in collectIfBlocks(body))
					output.push(child);
				offset = bodyEnd + (bodyEnd < source.length ? 1 : 0);
			}
		}
		return output;
	}

	static function findStatementEnd(source:String, start:Int):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in start...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'")
				quote = current;
			else if (current == '(' || current == '[' || current == '{')
				depth++;
			else if (current == ')' || current == ']' || current == '}')
				depth--;
			else if (current == ';' && depth == 0)
				return index;
		}
		return -1;
	}

	/** Keep incomplete pause helpers visible instead of silently treating them as ordinary modules. */
	static function looksLikePauseGraph(source:String):Bool {
		if (source == null)
			return false;
		return new EReg('\\b(?:function\\s+)?createUniversalMenu\\s*\\(', 'm').match(source)
			|| (new EReg('\\b(?:function\\s+)?onSubStateOpenEnd\\s*\\(', 'm').match(source)
				&& source.indexOf('targetPauseState') >= 0);
	}

	static function firstStaticPauseAsset(source:String, kind:String):String {
		var method = kind == 'image' ? 'image' : 'getSparrowAtlas';
		var expression = new EReg('Paths\\s*\\.\\s*' + method
			+ '\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)', 'g');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 128 && expression.match(remaining)) {
			var value = expression.matched(1);
			if (value != null && value != '' && !value.endsWith('/'))
				return value;
			var position = expression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		return '';
	}

	static function literalInt(value:String):Int {
		if (value == null || StringTools.trim(value) == '')
			return 0;
		var clean = StringTools.trim(value);
		try return Std.parseInt(clean) catch (_:Dynamic) return 0;
	}

	/** Extract one literal menu option array without evaluating donor code. */
	static function collectMenuStringArray(source:String):Array<String> {
		var output:Array<String> = [];
		if (source == null || source == '')
			return output;
		var declaration = new EReg('\\b(?:menuStrings|optionShit)\\s*(?::[^=;]+)?=\\s*\\[', 'm');
		if (!declaration.match(source))
			return output;
		var position = declaration.matchedPos();
		var open = source.indexOf('[', position.pos);
		if (open < 0)
			return output;
		var close = matchingDelimiter(source, open, '[', ']');
		if (close < 0)
			return output;
		for (part in splitTopLevel(source.substr(open + 1, close - open - 1), ',')) {
			var value = StringTools.trim(part);
			if (value.length < 2)
				continue;
			var first = value.charAt(0);
			var last = value.charAt(value.length - 1);
			if ((first == '"' && last == '"') || (first == "'" && last == "'"))
				output.push(value.substr(1, value.length - 2));
		}
		return output;
	}

	/**
		Read a literal state-factory target from the matching menu case.  This is
		structural and bounded to the case body; it never resolves or instantiates
		a donor class while analyzing the source.
	*/
	static function menuTargetForLabel(source:String, label:String):String {
		if (source == null || label == null || label == '')
			return '';
		var cases = new EReg('case\\s*["\\\']([^"\\\']+)["\\\']\\s*:', 'g');
		var remaining = source;
		var guard = 0;
		while (guard++ < 128 && cases.match(remaining)) {
			var caseLabel = cases.matched(1);
			var casePos = cases.matchedPos();
			var after = casePos.pos + casePos.len;
			var bodyEnd = remaining.length;
			var next = new EReg('\\bcase\\s*["\\\']', 'm');
			var body = remaining.substr(after);
			if (next.match(body))
				bodyEnd = after + next.matchedPos().pos;
			if (caseLabel == label) {
				// Keep the accepted vocabulary explicit: only a literal factory name
				// in this case body can become an imported route target.
				var factory = new EReg('(?:ScriptedMusicBeat(?:State|SubState)\\s*\\.\\s*init|hxcStateInit)\\s*\\(\\s*["\\\']([A-Za-z_][A-Za-z0-9_]*)["\\\']', 'm');
				if (factory.match(remaining.substr(after, bodyEnd - after)))
					return factory.matched(1);
				return '';
			}
			if (after <= 0 || after >= remaining.length)
				break;
			remaining = remaining.substr(after);
		}
		return '';
	}

	/** Find a literal Paths asset, optionally requiring a token in its key. */
	static function firstMenuAsset(source:String, kind:String, token:String):String {
		if (source == null)
			return '';
		var method = kind == 'image' ? 'image' : (kind == 'font' ? 'font' : 'getSparrowAtlas');
		var expression = new EReg('Paths\\s*\\.\\s*' + method
			+ '\\s*\\(\\s*["\\\']([^"\\\']+)', 'g');
		var remaining = source;
		var fallback = '';
		var attempts = 0;
		while (attempts++ < 128 && expression.match(remaining)) {
			var value = expression.matched(1);
			if (fallback == '')
				fallback = value;
			if (token == '' || value.toLowerCase().indexOf(token.toLowerCase()) >= 0)
				return value;
			var position = expression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		return fallback;
	}

	static function stripExtension(value:String):String {
		if (value == null)
			return '';
		var lower = value.toLowerCase();
		if (lower.endsWith('.png') || lower.endsWith('.xml') || lower.endsWith('.ttf'))
			return value.substr(0, value.length - 4);
		return value;
	}

	/** Replace an imported menu's donor callbacks with host-owned operations. */
	static function applyMenuSpecAdapters(spec:HxcCompatMenuPlan, kind:String,
		functions:Array<HxcCompatFunction>, callbacks:Array<HxcCompatCallbackAdapter>,
		helpers:Array<HxcCompatCallbackAdapter>, stateFields:Array<String>,
		stateInitializers:Array<HxcCompatStateInitializer>, constructorStatements:Array<String>):Void {
		if (spec == null)
			return;
		callbacks.resize(0);
		helpers.resize(0);
		stateFields.resize(0);
		stateInitializers.resize(0);
		constructorStatements.resize(0);
		if (kind == 'state')
			return;
		var names:Array<String> = [];
		if (functions != null)
			for (method in functions)
				if (method != null)
					appendUnique(names, lifecycleCallback(method.name));
		var literal = menuSpecLiteral(spec);
		if (names.indexOf('stateChangeEnd') >= 0)
			callbacks.push({sourceName:'onStateChangeEnd', canonicalName:'stateChangeEnd',
				arguments:['event'], body:'HxcCompatRuntime.mountMainMenuOverlay(event.targetState, '
					+ literal + ', hxcAssetRoot);', safe:true});
		if (names.indexOf('subStateCloseEnd') >= 0)
			callbacks.push({sourceName:'onSubStateCloseEnd', canonicalName:'subStateCloseEnd',
				arguments:['event'], body:'HxcCompatRuntime.clearMainMenuOverlay(event.targetState);', safe:true});
		if (names.indexOf('update') >= 0)
			callbacks.push({sourceName:'onUpdate', canonicalName:'update',
				arguments:['event'], body:'HxcCompatRuntime.tickMainMenuOverlay();', safe:true});
		if (names.indexOf('destroy') >= 0)
			callbacks.push({sourceName:'onDestroy', canonicalName:'destroy',
				arguments:[], body:'HxcCompatRuntime.clearMainMenuOverlay(null);', safe:true});
	}

	/** Replace a complete donor pause graph with one native PauseSubState ABI. */
	static function applyPauseSpecAdapters(spec:HxcCompatPausePlan, kind:String,
		functions:Array<HxcCompatFunction>, callbacks:Array<HxcCompatCallbackAdapter>,
		helpers:Array<HxcCompatCallbackAdapter>, stateFields:Array<String>,
		stateInitializers:Array<HxcCompatStateInitializer>, constructorStatements:Array<String>):Void {
		if (spec == null || kind != 'module')
			return;
		callbacks.resize(0);
		helpers.resize(0);
		stateFields.resize(0);
		stateInitializers.resize(0);
		constructorStatements.resize(0);
		var names:Array<String> = [];
		if (functions != null)
			for (method in functions)
				if (method != null)
					appendUnique(names, lifecycleCallback(method.name));
		var literal = pauseSpecLiteral(spec);
		if (names.indexOf('subStateOpenEnd') >= 0)
			callbacks.push({sourceName:'onSubStateOpenEnd', canonicalName:'subStateOpenEnd',
				arguments:['event'], body:'HxcCompatRuntime.applyPauseOverlay(event.targetState, hxcAssetRoot, '
					+ literal + ');', safe:true});
		if (names.indexOf('subStateCloseBegin') >= 0)
			callbacks.push({sourceName:'onSubStateCloseBegin', canonicalName:'subStateCloseBegin',
				arguments:['event'], body:'HxcCompatRuntime.clearPauseOverlay(event.targetState);', safe:true});
		if (names.indexOf('destroy') >= 0)
			callbacks.push({sourceName:'onDestroy', canonicalName:'destroy',
				arguments:[], body:'HxcCompatRuntime.clearPauseOverlay(null);', safe:true});
	}

	/** Replace a complete perfect-hit text cue with one owner-scoped ABI. */
	static function applyNoteTextSpecAdapters(spec:HxcNoteTextSpecData, kind:String,
		callbacks:Array<HxcCompatCallbackAdapter>, helpers:Array<HxcCompatCallbackAdapter>,
		stateFields:Array<String>, stateInitializers:Array<HxcCompatStateInitializer>,
		constructorStatements:Array<String>):Void {
		if (spec == null || kind != 'module')
			return;
		callbacks.resize(0);
		helpers.resize(0);
		stateFields.resize(0);
		stateInitializers.resize(0);
		constructorStatements.resize(0);
		var literal = noteTextSpecLiteral(spec);
		callbacks.push({sourceName:'onSongLoaded', canonicalName:'songLoaded', arguments:['event'],
			body:'if (__hxcNoteTextHandle != null) HxcCompatRuntime.clearNoteTextCue(PlayState.instance, __hxcNoteTextHandle);\n'
				+ '__hxcNoteTextHandle = HxcCompatRuntime.mountNoteTextCue(PlayState.instance, hxcAssetRoot, '
				+ literal + ');', safe:true});
		callbacks.push({sourceName:'onNoteHit', canonicalName:'noteHit', arguments:['event'],
			body:'HxcCompatRuntime.triggerNoteTextCue(PlayState.instance, __hxcNoteTextHandle, event);', safe:true});
		if (spec.missRules != null)
			callbacks.push({sourceName:'onNoteMiss', canonicalName:'noteMiss', arguments:['event'],
				body:'HxcCompatRuntime.triggerMissNoteTextCue(PlayState.instance, __hxcNoteTextHandle, event);', safe:true});
		callbacks.push({sourceName:'onSongRetry', canonicalName:'songRetry', arguments:['event'],
			body:'HxcCompatRuntime.resetNoteTextCue(PlayState.instance, __hxcNoteTextHandle);', safe:true});
		callbacks.push({sourceName:'onDestroy', canonicalName:'destroy', arguments:[],
			body:'HxcCompatRuntime.clearNoteTextCue(PlayState.instance, __hxcNoteTextHandle);\n'
				+ '__hxcNoteTextHandle = null;', safe:true});
	}

	static function noteTextSpecLiteral(spec:HxcNoteTextSpecData):String {
		if (spec == null)
			return 'null';
		var output = '{rules: [';
		var firstRule = true;
		for (rule in spec.rules) {
			if (!firstRule) output += ', ';
			firstRule = false;
			output += '{songId: ' + quote(rule.songId) + ', chancePercent: '
				+ numberLiteral(rule.chancePercent, 0) + ', lines: [';
			var firstLine = true;
			for (line in rule.lines) {
				if (!firstLine) output += ', ';
				firstLine = false;
				output += quote(line);
			}
			output += ']}';
		}
		output += '], triggerJudgement: ' + quote(spec.triggerJudgement);
		if (spec.missRules != null) {
			output += ', missRules: [';
			var firstMiss = true;
			for (rule in spec.missRules) {
				if (!firstMiss) output += ', ';
				firstMiss = false;
				output += '{songId: ' + quote(rule.songId) + ', chancePercent: '
					+ numberLiteral(rule.chancePercent, 0) + ', lines: [';
				var firstLine = true;
				for (line in rule.lines) {
					if (!firstLine) output += ', ';
					firstLine = false;
					output += quote(line);
				}
				output += ']}';
			}
			output += ']';
		}
		output += ', perfectOnly: true, onceAtATime: true'
			+ ', lifetimeSteps: ' + spec.lifetimeSteps
			+ ', expireStrictlyAfter: true, anchor: ' + quote(spec.anchor)
			+ ', xOffsetMin: ' + numberLiteral(spec.xOffsetMin, 0)
			+ ', xOffsetMax: ' + numberLiteral(spec.xOffsetMax, 0)
			+ ', yOffsetMin: ' + numberLiteral(spec.yOffsetMin, 0)
			+ ', yOffsetMax: ' + numberLiteral(spec.yOffsetMax, 0)
			+ ', font: ' + quote(spec.font)
			+ ', fontSize: ' + spec.fontSize + ', color: ' + spec.color
			+ ', bold: true, zIndex: ' + spec.zIndex;
		if (spec.staticOverlay != null) {
			var overlay = spec.staticOverlay;
			output += ', staticOverlay: {image: ' + quote(overlay.image)
				+ ', frameWidth: ' + overlay.frameWidth + ', frameHeight: ' + overlay.frameHeight
				+ ', frames: ' + intArrayLiteral(overlay.frames)
				+ ', fps: ' + numberLiteral(overlay.fps, 0)
				+ ', loop: ' + Std.string(overlay.loop)
				+ ', scaleX: ' + numberLiteral(overlay.scaleX, 1)
				+ ', scaleY: ' + numberLiteral(overlay.scaleY, 1)
				+ ', camera: ' + quote(overlay.camera)
				+ ', idleAlpha: ' + numberLiteral(overlay.idleAlpha, 0)
				+ ', hitAlpha: ' + numberLiteral(overlay.hitAlpha, 0)
				+ ', flickerMin: ' + numberLiteral(overlay.flickerMin, 0)
				+ ', flickerMax: ' + numberLiteral(overlay.flickerMax, 0);
			if (overlay.sound != null && overlay.sound != '')
				output += ', sound: ' + quote(overlay.sound);
			output += '}';
		}
		output += '}';
		return output;
	}

	static function pauseSpecLiteral(spec:HxcCompatPausePlan):String {
		var output = '{id: ' + quote(spec.id);
		for (field in [
			{name:'artPrefix', value:spec.artPrefix}, {name:'logo', value:spec.logo},
			{name:'atlas', value:spec.atlas}, {name:'logoAnimation', value:spec.logoAnimation},
			{name:'titleFont', value:spec.titleFont}, {name:'menuFont', value:spec.menuFont},
			{name:'titleLabel', value:spec.titleLabel}, {name:'deathLabel', value:spec.deathLabel},
			{name:'practiceLabel', value:spec.practiceLabel}
		])
			if (field.value != null && field.value != '')
				output += ', ' + field.name + ': ' + quote(field.value);
		for (field in [
			{name:'itemColor', value:spec.itemColor}, {name:'selectedColor', value:spec.selectedColor},
			{name:'fontSize', value:spec.fontSize}, {name:'menuFontSize', value:spec.menuFontSize}
		])
			if (field.value != null)
				output += ', ' + field.name + ': ' + Std.string(field.value);
		if (spec.hiddenLabels != null) {
			output += ', hiddenLabels: [';
			var first = true;
			for (label in spec.hiddenLabels) {
				if (!first) output += ', ';
				first = false;
				output += quote(label);
			}
			output += ']';
		}
		if (spec.requiredAssets != null) {
			output += ', requiredAssets: [';
			var first = true;
			for (asset in spec.requiredAssets) {
				if (!first) output += ', ';
				first = false;
				output += quote(asset);
			}
			output += ']';
		}
		return output + '}';
	}

	/** Emit only the native host calls for an imported MusicBeatState menu. */
	static function menuSpecLiteral(spec:HxcCompatMenuPlan):String {
		var output = '{id: ' + quote(spec.id) + ', style: ' + quote(spec.style)
			+ ', items: [';
		var first = true;
		for (item in spec.items) {
			if (!first)
				output += ', ';
			first = false;
			output += '{id: ' + quote(item.id) + ', label: ' + quote(item.label)
				+ ', route: ' + quote(item.route);
			if (item.target != null && item.target != '')
				output += ', target: ' + quote(item.target);
			output += '}';
		}
		output += ']';
		for (field in [
			{name:'background', value:spec.background}, {name:'atlas', value:spec.atlas},
			{name:'font', value:spec.font}, {name:'itemPrefix', value:spec.itemPrefix},
			{name:'selectedPrefix', value:spec.selectedPrefix}, {name:'foreground', value:spec.foreground},
			{name:'vignette', value:spec.vignette}
		])
			if (field.value != null && field.value != '')
				output += ', ' + field.name + ': ' + quote(field.value);
		if (spec.fontSize != null)
			output += ', fontSize: ' + Std.string(spec.fontSize);
		if (spec.requiredAssets != null) {
			output += ', requiredAssets: [';
			first = true;
			for (asset in spec.requiredAssets) {
				if (!first)
					output += ', ';
				first = false;
				output += quote(asset);
			}
			output += ']';
		}
		return output + '}';
	}

	static function moduleKnownRoot(name:String):Bool {
		if (name == null || name == '')
			return false;
		return switch (name) {
			case 'PlayState' | 'PlayStatePlaylist' | 'Conductor' | 'Countdown' | 'VideoCutscene' | 'CutsceneType' | 'FullScreenScaleMode'
				| 'FlxG' | 'FlxTimer' | 'FlxTween' | 'FlxEase'
				| 'FlxMath' | 'FlxSprite' | 'FlxObject' | 'FlxText' | 'FlxBar' | 'FlxCamera'
				| 'FlxSound' | 'FlxGroup' | 'FlxTiledSprite' | 'FlxBackdrop'
				| 'FlxAtlasFrames' | 'FlxAnimate' | 'FlxTypedGroup' | 'FlxColor' | 'FlxStringUtil'
				| 'FlxTypedSpriteGroup' | 'FlxFlicker' | 'Bitmap' | 'Assets' | 'StringMap'
				| 'FlxAnimateFrames' | 'FlxAngle' | 'FlxTypeText' | 'HealthIcon' | 'ShaderFilter'
				| 'FlxRuntimeShader' | 'FlxTrail' | 'FlxEffectSprite' | 'FlxGlitchEffect'
				| 'FlxButton' | 'FlxTextBorderStyle'
				| 'Math' | 'Std' | 'String' | 'StringTools' | 'Array' | 'Map' | 'Reflect'
				| 'Paths' | 'CoolUtil' | 'FNFAssets' | 'File' | 'FileSystem' | 'System'
				| 'TitleState' | 'MainMenuState' | 'CreditsState' | 'SaveDataState' | 'FreeplayState' | 'Character' | 'OptionsHandler' | 'DifficultyManager'
				| 'StageHelper' | 'EngineCompat' | 'HaxeState' | 'Json' | 'Sys' | 'Date'
				| 'HxcCompatRuntime' | '__hxcStore'
				| 'FlxTweenUtil'
				| 'hxcCharacterCache'
				| 'currentPlayState' | 'currentFreeplayState' | 'hxcFreeplayState' | 'stage' | 'boyfriend' | 'dad' | 'gf' | 'event' | 'SONG'
				| 'camHUD' | 'camGame' | 'vocals' | 'currentStage' | 'curStage' | 'paused' | 'PlayerSettings': true;
			default: false;
		};
	}

	static function moduleKnownCall(name:String):Bool {
		if (name == null || name == '')
			return false;
		return moduleKnownRoot(name) || switch (name) {
			case 'trace' | 'debug' | 'debugPrint' | 'setProperty' | 'getProperty'
				| 'setVar' | 'getVar' | 'updateHitbox' | 'remove' | 'add' | 'insert'
				| 'makeRangeArray' | 'coolTextFile' | 'soundPlaySafe' | 'preloadSound'
				| 'getGlobalSprite' | 'setGlobalSprite' | 'addSprite' | 'removeSprite'
				| 'addCharacter' | 'switchToChar' | 'swapStage' | 'changeStage'
				| 'setUIAlpha' | 'FocusCamera' | 'ZoomCamera' | 'SetCameraBop'
				| 'skipCountdown' | 'startShader' | 'createRuntimeShader'
				| 'hxcSetWindowTitle' | 'hxcSetWindowIcon' | 'instancePluginClass' | 'cancelCameraFollowTween'
					| 'hxcGetModule' | 'hxcGetCharacterData' | 'hxcChangeCharacter' | 'hxcOptionalField'
					| 'hxcOptionalCall' | 'hxcOptionalSet' | 'hxcCoalesce' | 'hxcMap'
				| 'hxcFreeplayPlaySound' | 'hxcFreeplayPlayMusic'
				| 'freeplayReturnToMenu' | 'reorderFreeplayDifficulties'
				| 'hxcPrepareCharacter' | 'hxcCacheTexture' | 'cast'
				| 'hxcStateInit' | 'hxcSubStateInit' | 'hxcStateFactory' | 'hxcSwitchState' | 'hxcStartExitState' | 'hxcOpenSubState'
				| 'hxcOpenSubStateOn'
				| 'openSubState' | 'hxcBack' | 'hxcResetState' | 'hxcFreeplayState'
				| 'isNull' | 'parseInt' | 'parseFloat': true;
			default: false;
		};
	}

	static function isSafeTranslatedBody(source:String):Bool {
		var translated = translateBody(source);
		return unsupportedHxcApiMembers(source).length == 0
			&& unsupportedConstructs(translated).length == 0
			&& translated.indexOf('super.') < 0 && translated.indexOf('this.') < 0
			&& translated.indexOf('override function') < 0
			&& translated.indexOf('public function') < 0
			&& translated.indexOf('private function') < 0
			&& translated.indexOf('protected function') < 0;
	}

	/** Return a comma-separated positional argument list for a generated helper. */
	static function callbackArgumentList(arguments:Array<String>):String {
		var output:Array<String> = [];
		if (arguments != null)
			for (argument in arguments)
				if (argument != null && isIdentifier(argument))
					output.push(argument);
		return output.join(', ');
	}

	/**
		Extract a complete capsule customization from its authored operations.
		The output contains only literal filters, icon rules and atlas animation
		metadata; class names, module paths and song/character identifiers never
		select this adapter. Unknown branches make the whole plan unavailable.
	*/
	static function freeplayCustomizationPlan(source:String):HxcCompatFreeplayPlan {
		if (source == null || source == '')
			return null;
		var levelIds:Array<String> = null;
		var levelIdsName = '';
		for (declaration in collectStateDeclarations(source)) {
			if (declaration == null || declaration.name == null || declaration.name == '')
				continue;
			var values = parseLiteralStringArray(declaration.initializer);
			if (values == null || values.length == 0)
				continue;
			if (new EReg('\\b' + declaration.name
				+ '\\s*\\.\\s*indexOf\\s*\\([^)]*\\.\\s*freeplayData\\s*\\.\\s*levelId\\s*\\)\\s*(?:!=|>=)\\s*-1', 'm').match(source)) {
				levelIds = values;
				levelIdsName = declaration.name;
				break;
			}
		}
		if (levelIds == null)
			return null;

		var iconBody:String = null;
		var displayBody:String = null;
		var iconMethodName = '';
		var displayMethodName = '';
		for (method in collectFunctions(source)) {
			if (method == null || method.body == null)
				continue;
			if (new EReg('\\.\\s*pixelIcon\\s*\\.\\s*setCharacter\\s*\\(', 'm').match(method.body)
				&& new EReg('\\.\\s*freeplayData\\s*\\.\\s*songCharacter\\b', 'm').match(method.body)
				&& new EReg('\\.\\s*freeplayData\\s*\\.\\s*data\\s*\\.\\s*id\\b', 'm').match(method.body)
				&& new EReg('\\bcurrentVariation\\b', 'm').match(method.body)) {
				if (iconBody != null)
					return null;
				iconBody = method.body;
				iconMethodName = method.name;
			}
			if (new EReg('\\.\\s*weekType\\s*\\.\\s*frames\\s*=\\s*Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(', 'm').match(method.body)
				&& new EReg('\\.\\s*weekType\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(', 'm').match(method.body)
				&& new EReg('\\.\\s*weekType\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(', 'm').match(method.body)) {
				if (displayBody != null)
					return null;
				displayBody = method.body;
				displayMethodName = method.name;
			}
		}
		if (iconBody == null || displayBody == null
			|| !new EReg('\\.\\s*pixelIcon\\s*\\.\\s*character\\s*!=', 'm').match(iconBody))
			return null;

		var characterExpression = firstString(iconBody,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*String)?\\s*=\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*freeplayData\\s*\\.\\s*songCharacter\\b');
		var songExpression = firstString(iconBody,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*String)?\\s*=\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*freeplayData\\s*\\.\\s*data\\s*\\.\\s*id\\b');
		if (characterExpression == '' || songExpression == '')
			return null;
		var targetExpression = firstString(iconBody,
			'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*String)?\\s*=\\s*' + characterExpression + '\\b');
		if (targetExpression == ''
			|| !new EReg('\\.\\s*pixelIcon\\s*\\.\\s*setCharacter\\s*\\(\\s*' + targetExpression + '\\s*\\)', 'm').match(iconBody))
			return null;
		var characterRules = parseFreeplaySwitch(iconBody, characterExpression, targetExpression, false);
		var songRules = parseFreeplaySwitch(iconBody, songExpression, targetExpression, true);
		if (characterRules == null || songRules == null)
			return null;
		var iconOffset = firstString(iconBody,
			'\\.\\s*pixelIcon\\s*\\.\\s*offset\\s*\\.\\s*x\\s*=\\s*(-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))');
		if (iconOffset == '')
			return null;

		var atlas = firstString(displayBody,
			'Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)');
		if (atlas == '' || atlas.startsWith('/') || atlas.indexOf('..') >= 0)
			return null;
		var animations:Array<{var name:String; var prefix:String; var fps:Float; var looped:Bool;}> = [];
		var addAnimation = new EReg('\\.\\s*weekType\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*["\\\']([^"\\\']+)["\\\']\\s*,\\s*(-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+))\\s*,\\s*(true|false)\\s*\\)', 'g');
		var offset = 0;
		while (offset < displayBody.length) {
			var remaining = displayBody.substr(offset);
			if (!addAnimation.match(remaining))
				break;
			var name = addAnimation.matched(1);
			var prefix = addAnimation.matched(2);
			var fps = Std.parseFloat(addAnimation.matched(3));
			var looped = addAnimation.matched(4) == 'true';
			if (name == '' || prefix == '' || Math.isNaN(fps) || fps <= 0)
				return null;
			animations.push({name: name, prefix: prefix, fps: fps, looped: looped});
			var position = addAnimation.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		if (animations.length == 0)
			return null;
		var defaultAnimation = firstString(displayBody,
			'\\belse\\s+(?:\\{\\s*)?[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*weekType\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var animationOverrides:Array<{var song:String; var animation:String;}> = [];
		var animationOverride = new EReg('if\\s*\\([^)]*\\.\\s*freeplayData\\s*\\.\\s*data\\s*\\.\\s*id\\s*==\\s*["\\\']([^"\\\']+)["\\\'][^)]*\\)\\s*(?:\\{\\s*)?[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*weekType\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
		offset = 0;
		while (offset < displayBody.length) {
			var remaining = displayBody.substr(offset);
			if (!animationOverride.match(remaining))
				break;
			animationOverrides.push({song: animationOverride.matched(1), animation: animationOverride.matched(2)});
			var position = animationOverride.matchedPos();
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		if (defaultAnimation == '' || animationOverrides.length == 0)
			return null;
		var animationNames:Array<String> = [];
		for (animation in animations)
			appendUnique(animationNames, animation.name);
		if (animationNames.indexOf(defaultAnimation) < 0)
			return null;
		for (entry in animationOverrides)
			if (animationNames.indexOf(entry.animation) < 0)
				return null;
		var characterIconRules:Array<{var key:String; var icon:String;}> = [];
		var songIconRules:Array<{var key:String; var icon:String;}> = [];
		for (rule in characterRules.direct)
			characterIconRules.push({key: rule.key, icon: rule.value});
		for (rule in songRules.direct)
			songIconRules.push({key: rule.key, icon: rule.value});

		return {
			levelIds: levelIds,
			levelIdsName: levelIdsName,
			iconMethodName: iconMethodName,
			displayMethodName: displayMethodName,
			characterRules: characterIconRules,
			songRules: songIconRules,
			variationRules: songRules.variation,
			iconOffsetX: Std.parseFloat(iconOffset),
			atlas: atlas,
			animations: animations,
			defaultAnimation: defaultAnimation,
			animationOverrides: animationOverrides
		};
	}

	/**
		Return helper methods whose complete call chain is replaced by a recognized
		literal Freeplay plan.  This keeps donor capsule graphs out of generated
		HScript while leaving partial or additionally referenced helpers visible to
		the ordinary safety gate.
	*/
	static function freeplayCustomizationOwnedHelpers(source:String):Array<String> {
		var plan = freeplayCustomizationPlan(source);
		if (plan == null || plan.levelIdsName == '' || plan.iconMethodName == ''
			|| plan.displayMethodName == '')
			return [];
		var functions = collectFunctions(stripComments(source));
		var aggregators:Array<HxcCompatFunction> = [];
		for (method in functions) {
			if (method == null || method.name == plan.iconMethodName
				|| method.name == plan.displayMethodName || method.body == null)
				continue;
			var calls = collectUnqualifiedCalls(method.body);
			if (method.body.indexOf('.grpCapsules.members') >= 0
				&& calls.indexOf(plan.iconMethodName) >= 0
				&& calls.indexOf(plan.displayMethodName) >= 0
				&& calls.length == 2
				&& new EReg('\\b' + plan.levelIdsName
					+ '\\s*\\.\\s*indexOf\\s*\\([^)]*\\.\\s*freeplayData\\s*\\.\\s*levelId\\s*\\)\\s*!=\\s*-1', 'm').match(method.body)
				&& new EReg('\\bfor\\s*\\(\\s*[A-Za-z_][A-Za-z0-9_]*\\s+in\\s+[^)]*grpCapsules\\s*\\.\\s*members', 'm').match(method.body))
				aggregators.push(method);
		}
		if (aggregators.length != 1)
			return [];
		var aggregateName = aggregators[0].name;
		var owned = [plan.iconMethodName, plan.displayMethodName, aggregateName];
		var hasOpen = false;
		var hasDifficulty = false;
		var hasSelection = false;
		var graphMembers = new EReg('\\.\\s*(?:grpCapsules|weekType|freeplayData|pixelIcon)\\b', 'm');
		for (method in functions) {
			if (method == null || method.name == null || method.body == null)
				continue;
			var calls = collectUnqualifiedCalls(method.body);
			if (owned.indexOf(method.name) >= 0) {
				if (method.name == aggregateName) {
					if (calls.length != 2 || calls.indexOf(plan.iconMethodName) < 0
						|| calls.indexOf(plan.displayMethodName) < 0)
						return [];
				} else if (calls.length > 0)
					return [];
				continue;
			}
			var callsOwned = false;
			for (name in owned)
				if (calls.indexOf(name) >= 0)
					callsOwned = true;
			if (callsOwned) {
				var argument = method.arguments == null || method.arguments.length == 0
					? '' : method.arguments[0];
				var hook = freeplayCustomizationHook(method.body, method.name, argument);
				var methodName = method.name.toLowerCase();
				if (methodName == 'onsubstateopenend' || methodName == 'ondifficultyswitch') {
					if (hook != 'all' || calls.length != 1 || calls[0] != aggregateName)
						return [];
					if (methodName == 'onsubstateopenend') hasOpen = true;
					if (methodName == 'ondifficultyswitch') hasDifficulty = true;
				} else if (methodName == 'oncapsuleselected') {
					if (hook != 'selected' || calls.length != 1
						|| calls[0] != plan.iconMethodName)
						return [];
					hasSelection = true;
				} else
					return [];
			} else if (graphMembers.match(method.body)) {
				// Graph reads outside the helpers above are accepted only when the
				// complete lifecycle recognizer replaces that callback as a whole.
				var argument = method.arguments == null || method.arguments.length == 0
					? '' : method.arguments[0];
				var hook = freeplayCustomizationHook(method.body, method.name, argument);
				if (hook == '')
					return [];
			}
		}
		return hasOpen && hasDifficulty && hasSelection ? owned : [];
	}

	static function parseLiteralStringArray(expression:String):Array<String> {
		if (expression == null)
			return null;
		var value = StringTools.trim(expression);
		if (value.length < 2 || value.charAt(0) != '[' || matchingDelimiter(value, 0, '[', ']') != value.length - 1)
			return null;
		var output:Array<String> = [];
		var contents = StringTools.trim(value.substr(1, value.length - 2));
		if (contents == '')
			return output;
		for (part in splitTopLevel(contents, ',')) {
			var item = StringTools.trim(part);
			if (item.length < 2 || (item.charAt(0) != '\'' && item.charAt(0) != '"')
				|| item.charAt(item.length - 1) != item.charAt(0) || item.indexOf('\\') >= 0)
				return null;
			output.push(item.substr(1, item.length - 2));
		}
		return output;
	}

	static function parseFreeplaySwitch(source:String, variable:String, target:String,
		allowVariation:Bool):Null<HxcCompatFreeplaySwitchRules> {
		var header = new EReg('\\bswitch\\s*\\(\\s*' + variable + '\\s*\\)\\s*\\{', 'm');
		if (!header.match(source))
			return null;
		var open = source.indexOf('{', header.matchedPos().pos);
		var close = open < 0 ? -1 : matchingDelimiter(source, open, '{', '}');
		if (close < 0)
			return null;
		var body = source.substr(open + 1, close - open - 1);
		var rules:HxcCompatFreeplaySwitchRules = {direct: [], variation: []};
		var caseHeader = new EReg('\\bcase\\s+([^:]+):', 'gm');
		var cursor = 0;
		while (cursor < body.length) {
			var rest = body.substr(cursor);
			if (!caseHeader.match(rest))
				break;
			var labels = caseHeader.matched(1);
			var position = caseHeader.matchedPos();
			var statementStart = cursor + position.pos + position.len;
			var tail = body.substr(statementStart);
			var next = new EReg('\\b(?:case\\s+[^:]+|default)\\s*:', 'm');
			var statementEnd = body.length;
			if (next.match(tail))
				statementEnd = statementStart + next.matchedPos().pos;
			var statement = StringTools.trim(body.substr(statementStart, statementEnd - statementStart));
			statement = new EReg('(?s)/\\*.*?\\*/|//[^\\r\\n]*', 'g').replace(statement, '');
			statement = StringTools.trim(statement);
			var direct = new EReg('^\\{?\\s*' + target + '\\s*=\\s*["\\\']([^"\\\']*)["\\\']\\s*;?\\s*\\}?$', 's');
			var variation = new EReg('^\\{?\\s*' + target + '\\s*=\\s*\\(?[^?;]*currentVariation\\s*==\\s*["\\\']([^"\\\']+)["\\\'][^?;]*\\)?\\s*\\?\\s*["\\\']([^"\\\']+)["\\\']\\s*:\\s*["\\\']([^"\\\']+)["\\\']\\s*;?\\s*\\}?$', 's');
			var value = '';
			var variationName = '';
			var matchIcon = '';
			var fallbackIcon = '';
			if (direct.match(statement))
				value = direct.matched(1);
			else if (allowVariation && variation.match(statement)) {
				variationName = variation.matched(1);
				matchIcon = variation.matched(2);
				fallbackIcon = variation.matched(3);
			} else
				return null;
			var keys = splitTopLevel(labels, ',');
			if (keys.length == 0)
				return null;
			for (rawKey in keys) {
				var key = StringTools.trim(rawKey);
				if (key.length < 2 || (key.charAt(0) != '\'' && key.charAt(0) != '"')
					|| key.charAt(key.length - 1) != key.charAt(0) || key.indexOf('\\') >= 0)
					return null;
				key = key.substr(1, key.length - 2);
				if (variationName != '')
					rules.variation.push({key: key, variation: variationName, matchIcon: matchIcon, fallbackIcon: fallbackIcon});
				else
					rules.direct.push({key: key, value: value});
			}
			cursor = statementEnd;
			if (cursor <= position.pos)
				return null;
		}
		return rules.direct.length + rules.variation.length > 0 ? rules : null;
	}

	static function freeplayCustomizationPlanLiteral(plan:HxcCompatFreeplayPlan):String {
	if (plan == null)
		return 'null';
	var output = '{levelIds: ' + stringArrayLiteral(plan.levelIds) + ', characterRules: [';
	var first = true;
	for (rule in plan.characterRules) {
		if (!first) output += ', ';
		first = false;
		output += '{key: ' + quote(rule.key) + ', icon: ' + quote(rule.icon) + '}';
	}
	output += '], songRules: [';
	first = true;
	for (rule in plan.songRules) {
		if (!first) output += ', ';
		first = false;
		output += '{key: ' + quote(rule.key) + ', icon: ' + quote(rule.icon) + '}';
	}
	output += '], variationRules: [';
	first = true;
	for (rule in plan.variationRules) {
		if (!first) output += ', ';
		first = false;
		output += '{key: ' + quote(rule.key) + ', variation: ' + quote(rule.variation)
			+ ', matchIcon: ' + quote(rule.matchIcon) + ', fallbackIcon: ' + quote(rule.fallbackIcon) + '}';
	}
	output += '], iconOffsetX: ' + Std.string(plan.iconOffsetX) + ', atlas: ' + quote(plan.atlas)
		+ ', animations: [';
	first = true;
	for (animation in plan.animations) {
		if (!first) output += ', ';
		first = false;
		output += '{name: ' + quote(animation.name) + ', prefix: ' + quote(animation.prefix)
			+ ', fps: ' + Std.string(animation.fps) + ', looped: ' + Std.string(animation.looped) + '}';
	}
	output += '], defaultAnimation: ' + quote(plan.defaultAnimation) + ', animationOverrides: [';
	first = true;
	for (animationRule in plan.animationOverrides) {
		if (!first) output += ', ';
		first = false;
		output += '{song: ' + quote(animationRule.song) + ', animation: ' + quote(animationRule.animation) + '}';
	}
	return output + ']}';
}

	/** Recognize lifecycle bodies which do only the capsule customization work. */
	static function freeplayCustomizationHook(source:String, methodName:String,
		argument:String):String {
	if (source == null || methodName == null || argument == null || argument == '')
		return '';
	var body = stripComments(source);
	body = new EReg('\\bsuper\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\([^;]*\\)\\s*;', 'g').replace(body, '');
	var name = methodName.toLowerCase();
	if (name == 'onsubstateopenend') {
		var pattern = new EReg('^\\s*if\\s*\\(\\s*!\\s*\\(\\s*' + argument
			+ '\\s*\\.\\s*targetState\\s+is\\s+FreeplayState\\s*\\)\\s*\\)\\s*return\\s*;\\s*'
			+ 'var\\s+([A-Za-z_][A-Za-z0-9_]*)(?:\\s*:\\s*Dynamic)?\\s*=\\s*' + argument
			+ '\\s*\\.\\s*targetState\\s*;\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\(\\s*\\1\\s*\\)\\s*;?\\s*$', 's');
		return pattern.match(body) ? 'all' : '';
	}
	if (name == 'ondifficultyswitch') {
		var pattern = new EReg('^\\s*var\\s+([A-Za-z_][A-Za-z0-9_]*)(?:\\s*:\\s*Dynamic)?\\s*=\\s*'
			+ 'FlxG\\s*\\.\\s*state\\s*\\.\\s*subState\\s*;\\s*'
			+ '[A-Za-z_][A-Za-z0-9_]*\\s*\\(\\s*\\1\\s*\\)\\s*;?\\s*$', 's');
		return pattern.match(body) ? 'all' : '';
	}
	if (name == 'oncapsuleselected') {
		var pattern = new EReg('^\\s*if\\s*\\(\\s*' + argument
			+ '\\s*\\.\\s*capsule\\s*!=\\s*null\\s*&&\\s*' + argument
			+ '\\s*\\.\\s*capsule\\s*\\.\\s*freeplayData\\s*!=\\s*null\\s*\\)\\s*\\{\\s*'
			+ 'if\\s*\\(\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*indexOf\\s*\\(\\s*' + argument
			+ '\\s*\\.\\s*capsule\\s*\\.\\s*freeplayData\\s*\\.\\s*levelId\\s*\\)\\s*!=\\s*-1\\s*\\)\\s*\\{\\s*'
			+ 'var\\s+([A-Za-z_][A-Za-z0-9_]*)(?:\\s*:\\s*Dynamic)?\\s*=\\s*FlxG\\s*\\.\\s*state\\s*\\.\\s*subState\\s*;\\s*'
			+ '[A-Za-z_][A-Za-z0-9_]*\\s*\\(\\s*' + argument
			+ '\\s*\\.\\s*capsule\\s*,\\s*\\1\\s*\\)\\s*;?\\s*\\}\\s*\\}\\s*$', 's');
		return pattern.match(body) ? 'selected' : '';
	}
	return '';
}

	/**
		Recognize the complete generic song-credit construction shape.  The body
		must provide both pixel/default literals, a literal `songCredits/` icon
		lookup, chart name/artist reads, and all three native display additions;
		partial donor UI graphs remain on the normal safety path.
	*/
	static function songCreditsPlan(source:String):HxcCompatSongCreditsPlan {
		if (source == null || source == '')
			return null;
		var defaults = matchGroups(source,
			'\\biconName\\s*(?::\\s*String)?\\s*=\\s*isPixel\\s*\\?\\s*["\\\']([^"\\\']+)["\\\']\\s*:\\s*["\\\']([^"\\\']+)["\\\']');
		if (defaults.length < 2 || !isSongCreditsIconLiteral(defaults[0])
			|| !isSongCreditsIconLiteral(defaults[1]))
			return null;
		if (!new EReg('\\bcurrentStageId\\s*\\.\\s*toLowerCase\\s*\\(\\s*\\)\\s*\\.\\s*indexOf\\s*\\(', 'm').match(source)
			|| !new EReg('\\bnoteStyle\\s*\\.\\s*id\\s*\\.\\s*toLowerCase\\s*\\(\\s*\\)', 'm').match(source)
			|| !new EReg('\\bFunkinSprite\\s*\\.\\s*create\\s*\\(', 'm').match(source)
			|| !new EReg('["\\\']songCredits/["\\\']\\s*\\+\\s*iconName', 'm').match(source)
			|| !new EReg('\\bcurrentChart\\s*\\.\\s*songName\\b', 'm').match(source)
			|| !new EReg('\\bcurrentChart\\s*\\.\\s*songArtist\\b', 'm').match(source)
			|| !new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*add\\s*\\(', 'm').match(source)
			|| !new EReg('\\bmanualCreditsSummon\\s*\\(\\s*\\)', 'm').match(source)
			|| source.indexOf('new FlxText') < 0
			|| !new EReg('\\bcleanup\\s*\\(\\s*\\)', 'm').match(source))
			return null;
		var overrides:Array<{var song:String; var icon:String;}> = [];
		var cases = new EReg('case\\s*["\\\']([^"\\\']+)["\\\']\\s*:\\s*iconName\\s*=\\s*["\\\']([^"\\\']+)["\\\']', 'g');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 128 && cases.match(remaining)) {
			var song = StringTools.trim(cases.matched(1));
			var icon = StringTools.trim(cases.matched(2));
			if (!isSongCreditsSongLiteral(song) || !isSongCreditsIconLiteral(icon))
				return null;
			var duplicate = false;
			for (existing in overrides)
				if (existing.song == song.toLowerCase()) {
					duplicate = true;
					break;
				}
			if (!duplicate)
				overrides.push({song: song.toLowerCase(), icon: icon});
			var position = cases.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		return {defaultIcon: defaults[1], pixelIcon: defaults[0], overrides: overrides};
	}

	static function isSongCreditsIconLiteral(value:String):Bool {
		return value != null && value.length > 0 && value.length <= 48
			&& new EReg('^[A-Za-z0-9_-]+$', '').match(value);
	}

	static function isSongCreditsSongLiteral(value:String):Bool {
		return value != null && value.length > 0 && value.length <= 96
			&& new EReg('^[A-Za-z0-9 _.-]+$', '').match(value);
	}

	static function translateSongCredits(plan:HxcCompatSongCreditsPlan):String {
		if (plan == null)
			return '';
		var output = 'HxcCompatRuntime.clearSongCredits(PlayState.instance); '
			+ 'var isPixel = HxcCompatRuntime.songCreditsPixel(PlayState.instance); '
			+ 'var iconKey = isPixel ? ' + quote(plan.pixelIcon) + ' : ' + quote(plan.defaultIcon) + '; '
			+ 'var songKey = SONG.song == null ? "" : Std.string(SONG.song).toLowerCase(); ';
		if (plan.overrides != null)
			for (iconOverride in plan.overrides)
				output += 'if (songKey == ' + quote(iconOverride.song) + ') iconKey = '
					+ quote(iconOverride.icon) + '; ';
		return output + 'HxcCompatRuntime.showSongCredits(PlayState.instance, SONG.song, '
			+ 'SONG.songArtist, isPixel, iconKey, hxcAssetRoot);';
	}

	static function isSongCreditsCleanupBody(source:String, methodName:String):Bool {
		if (source == null || methodName == null || methodName.toLowerCase() != 'cleanup')
			return false;
		return new EReg('\\btweenOutTimer\\b[\\s\\S]*\\bmetaName\\b[\\s\\S]*\\bmetaIcon\\b[\\s\\S]*\\bmetaArtist\\b', 'm').match(source)
			&& new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*remove\\s*\\(', 'm').match(source)
			&& new EReg('\\.(?:cancel|destroy)\\s*\\(', 'm').match(source)
			&& new EReg('=\\s*null', 'm').match(source);
	}

	static function isSongCreditsPauseBody(source:String, methodName:String, active:String):Bool {
		if (source == null || methodName == null || methodName.toLowerCase() != active)
			return false;
		return new EReg('\\btweenOutTimer\\b', 'm').match(source)
			&& new EReg('\\bmetaNameTween\\b', 'm').match(source)
			&& new EReg('\\bmetaIconTween\\b', 'm').match(source)
			&& new EReg('\\bmetaArtistTween\\b', 'm').match(source)
			&& new EReg('\\.active\\s*=\\s*(?:true|false)', 'm').match(source);
	}

	static function isSongCreditsRetryBody(source:String, methodName:String):Bool {
		if (source == null || methodName == null || methodName.toLowerCase() != 'onsongretry')
			return false;
		return new EReg('^\\s*super\\s*\\.\\s*onSongRetry\\s*\\(\\s*event\\s*\\)\\s*;?\\s*cleanup\\s*\\(\\s*\\)\\s*;?\\s*$', 'm').match(source);
	}

	/** Structural lyric helper detector; intentionally independent of donor ids. */
	static function isLyricHelperBody(source:String):Bool {
		return source != null
			&& new EReg('\\bnew\\s+FlxText\\s*\\(', 'm').match(source)
			&& new EReg('\\b(?:lyric|caption)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('\\.setFormat\\s*\\(', 'm').match(source)
			&& new EReg('\\.screenCenter\\s*\\(', 'm').match(source);
	}

	/** Structural lyric teardown detector; avoid matching createText's pre-clear. */
	static function isLyricClearBody(source:String):Bool {
		return source != null
			&& source.indexOf('new FlxText') < 0
			&& new EReg('\\b(?:lyric|caption)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('\\.(?:kill|destroy)\\s*\\(', 'm').match(source)
			&& new EReg('=\\s*null', 'm').match(source);
	}

	/** Structural setup/teardown/pause detectors for runtime vignette wrappers. */
	static function isVignetteSetupBody(source:String):Bool {
		return source != null
			&& new EReg('(?:ScriptedFlxRuntimeShader|createRuntimeShader)', 'm').match(source)
			&& new EReg('\\b(?:vign|vignette)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('new\\s+ShaderFilter', 'm').match(source)
			&& new EReg('\\.filters\\b', 'm').match(source)
			&& !new EReg('\\.(?:remove|cancel)\\s*\\(', 'm').match(source);
	}

	static function isVignetteClearBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:vign|vignette)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('\\.filters\\s*\\?*\\.remove|\\.filters\\.remove', 'm').match(source)
			&& new EReg('=\\s*null', 'm').match(source);
	}

	static function isVignettePauseBody(source:String):Bool {
		return source != null && new EReg('\\b(?:pauseTween|pause)Tween?\\s*\\(', 'i').match(source)
			&& new EReg('\\b(?:vign|vignette|intensity)[A-Za-z0-9_]*\\b', 'i').match(source);
	}

	static function isVignetteResumeBody(source:String):Bool {
		return source != null && new EReg('\\b(?:resumeTween|resume)Tween?\\s*\\(', 'i').match(source)
			&& new EReg('\\b(?:vign|vignette|intensity)[A-Za-z0-9_]*\\b', 'i').match(source);
	}

	static function isVignetteTweenBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:vign|vignette)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('\\b(?:FlxTween\\s*\\.\\s*num|setIntensity|intensity_tween)\\b', 'm').match(source)
			&& new EReg('\\b(?:intensity|duration)\\b', 'm').match(source)
			&& !isVignetteSetupBody(source) && !isVignetteClearBody(source);
	}

	static function isSoundTrayApplyBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:soundTray|soundtray)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('(?:Bitmap|Assets\\s*\\.\\s*getBitmapData)', 'm').match(source)
			&& new EReg('volume(?:Up|Down|Max)Sound', 'm').match(source)
			&& new EReg('\\b(?:currentStageId|currentStage)\\b', 'm').match(source)
			&& new EReg('\\b(?:onCountdown|countdown)', 'i').match(source);
	}

	static function isSoundTrayRestoreBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:soundTray|soundtray)[A-Za-z0-9_]*\\b', 'i').match(source)
			&& new EReg('(?:Bitmap|Assets\\s*\\.\\s*getBitmapData)', 'm').match(source)
			&& new EReg('volume(?:Up|Down|Max)Sound', 'm').match(source)
			&& new EReg('(?:reset|restore|remake)', 'i').match(source);
	}

	static function isPreferencePageBody(source:String):Bool {
		return source != null
			&& new EReg('\\bcreatePrefItem(?:Checkbox|Enum|String|Number)\\s*\\(', 'm').match(source)
			&& new EReg('\\b(?:preferencePage|optionsCodex|PreferencesMenu)\\b', 'm').match(source);
	}

	static function isPreferenceSeparatorBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:preferenceItems|preferenceDesc)\\b', 'm').match(source)
			&& new EReg('\\b(?:createItem|createSeparator)\\s*\\(', 'm').match(source);
	}

	/** Structural menu-back detector for modules that only inspect native input. */
	static function isMenuOverrideUpdateBody(source:String):Bool {
		return source != null
			&& new EReg('\\bPlayerSettings\\s*\\.\\s*player1\\s*\\.\\s*controls\\s*\\.\\s*BACK\\b', 'm').match(source)
			&& new EReg('\\b(?:exitingMenu|selectedLevel|controls\\s*\\.\\s*active)\\b', 'm').match(source)
			&& new EReg('\\b(?:customReturnMenu|FunkinSound\\s*\\.\\s*playOnce)\\s*\\(', 'm').match(source);
	}

	/** Structural state-change detector for menu redirection callbacks. */
	static function isMenuOverrideStateChangeBody(source:String):Bool {
		return source != null
			&& new EReg('\\b(?:MainMenuState|OptionsState)\\b', 'm').match(source)
			&& new EReg('\\b(?:FlxG\\s*\\.\\s*switchState|hxcSwitchState|ScriptedMusicBeatState\\s*\\.\\s*init)\\s*\\(', 'm').match(source)
			&& new EReg('\\b(?:optionsCodex|pages\\s*\\.\\s*get)\\b', 'm').match(source);
	}

	/** Structural state override helper detector; keep donor state graphs out. */
	static function isMenuRedirectHelperBody(source:String):Bool {
		return source != null
			&& new EReg('\\b_requestedSubState\\b', 'm').match(source)
			&& new EReg('\\bFlxG\\s*\\.\\s*game\\s*\\.\\s*_state\\b', 'm').match(source)
			&& new EReg('\\bredirectStates\\b', 'm').match(source);
	}

	/**
		Extract the finite roster and replacement id from a complete HXC
		GameOverSubState hand-off.  Only a literal class field array and a literal
		fetchCharacter argument qualify; dynamic expressions stay outside this
		adapter and remain subject to the regular module safety gate.
	*/
	static function gameOverReplacementData(source:String, moduleSource:String):Dynamic {
		if (source == null || moduleSource == null
			|| !new EReg('\\bGameOverSubState\\s*\\.\\s*instance\\b', 'm').match(source)
			|| !new EReg('\\bGameOverSubState\\s*\\.\\s*instance\\s*\\.\\s*boyfriend\\s*\\.\\s*destroy\\s*\\(', 'm').match(source))
			return null;

		var playerExpression = '';
		var rosterName = '';
		var rosterCalls = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*(?:contains|indexOf)\\s*\\(', 'g');
		var offset = 0;
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!rosterCalls.match(remaining))
				break;
			var callName = rosterCalls.matched(1);
			var callPos = rosterCalls.matchedPos();
			var open = remaining.indexOf('(', callPos.pos + callPos.len - 1);
			var close = open < 0 ? -1 : matchingDelimiter(remaining, open, '(', ')');
			if (close >= 0) {
				var argument = compactExpression(remaining.substr(open + 1, close - open - 1));
				if (argument == 'PlayState.instance.currentChart.characters.player'
					|| argument == 'currentChart.characters.player') {
					rosterName = callName;
					playerExpression = argument;
					break;
				}
			}
			var advance = callPos.pos + (callPos.len > 0 ? callPos.len : 1);
			offset += advance;
		}
		if (rosterName == '' || playerExpression == '')
			return null;

		var roster:Array<String> = null;
		for (declaration in collectStateDeclarations(moduleSource))
			if (declaration != null && declaration.name == rosterName) {
				roster = parseLiteralCharacterArray(declaration.initializer);
				break;
			}
		if (roster == null || roster.length == 0)
			return null;

		var fetch = new EReg('(?:CharacterDataParser\\s*\\.\\s*)?fetchCharacter\\s*\\(', 'g');
		offset = 0;
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!fetch.match(remaining))
				break;
			var position = fetch.matchedPos();
			var open = remaining.indexOf('(', position.pos + position.len - 1);
			var close = open < 0 ? -1 : matchingDelimiter(remaining, open, '(', ')');
			if (close >= 0) {
				var replacement = parseLiteralCharacterId(remaining.substr(open + 1, close - open - 1));
				var variableName = firstString(remaining.substr(0, position.pos),
					'\\bvar\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*$');
				if (replacement != '' && variableName != ''
					&& new EReg('\\bGameOverSubState\\s*\\.\\s*instance\\s*\\.\\s*boyfriend\\s*=\\s*'
						+ variableName + '\\b', 'm').match(source))
					return {roster: roster, replacement: replacement};
			}
			var advance = position.pos + (position.len > 0 ? position.len : 1);
			offset += advance;
		}
		return null;
	}

	static function compactExpression(value:String):String {
		return value == null ? '' : new EReg('\\s+', 'g').replace(value, '');
	}

	static function parseLiteralCharacterArray(expression:String):Array<String> {
		if (expression == null)
			return null;
		var value = StringTools.trim(expression);
		if (value.length < 2 || value.charAt(0) != '[')
			return null;
		var close = matchingDelimiter(value, 0, '[', ']');
		if (close != value.length - 1)
			return null;
		var output:Array<String> = [];
		for (part in splitTopLevel(value.substr(1, value.length - 2), ',')) {
			var id = parseLiteralCharacterId(part);
			if (id == '')
				return null;
			output.push(id);
		}
		return output;
	}

	static function parseLiteralCharacterId(expression:String):String {
		if (expression == null)
			return '';
		var value = StringTools.trim(expression);
		if (value.length < 3)
			return '';
		var quoteChar = value.charAt(0);
		if ((quoteChar != '\'' && quoteChar != '"') || value.charAt(value.length - 1) != quoteChar)
			return '';
		var id = value.substr(1, value.length - 2);
		return new EReg('^[A-Za-z0-9_.-]+$', '').match(id) ? id : '';
	}

	static function stringArrayLiteral(values:Array<String>):String {
		var output = '[';
		if (values != null)
			for (index in 0...values.length) {
				if (index > 0)
					output += ', ';
				output += quote(values[index]);
			}
		return output + ']';
	}

	/**
		Translate the small Freeplay-facing object view used by imported modules.

		V-Slice hosts Freeplay as a substate below a larger menu state, while this
		fork owns FreeplayState directly.  A module callback therefore receives a
		bounded `currentFreeplayState` alias rather than the donor's capsule graph.
		The alias is deliberately applied only to Module bodies; gameplay HXC and
		state scripts retain the normal FlxG state semantics.
	*/
	static function translateModuleBody(source:String, ?methodName:String,
		?arguments:Array<String>, ?moduleSource:String):String {
		var stageReplacement = lowerCompleteStageReplacement(source, arguments);
		if (stageReplacement != null)
			return stageReplacement;
		var output = translateBody(source, methodName, arguments);
		output = translateIndexedCharacterOffsetReads(output);
		var firstArgument = arguments == null || arguments.length == 0 ? 'event' : arguments[0];
		// TAKEOVER's Credits module builds a top-right song banner from native
		// chart metadata and a small literal icon switch.  Recognize the complete
		// operation structurally, then hand text/icon ownership to PlayState; no
		// donor FlxText/FunkinSprite graph is emitted into HScript.
		if (methodName != null && methodName.toLowerCase() == 'onsongstart') {
			var songCredits = songCreditsPlan(source);
			if (songCredits != null)
				return translateSongCredits(songCredits);
		}
		if (isSongCreditsCleanupBody(source, methodName))
			return 'HxcCompatRuntime.clearSongCredits(PlayState.instance);';
		if (isSongCreditsPauseBody(source, methodName, 'onpause'))
			return 'HxcCompatRuntime.pauseSongCredits(PlayState.instance);';
		if (isSongCreditsPauseBody(source, methodName, 'onresume'))
			return 'HxcCompatRuntime.resumeSongCredits(PlayState.instance);';
		if (isSongCreditsRetryBody(source, methodName))
			return 'HxcCompatRuntime.clearSongCredits(PlayState.instance);';
		// A V-Slice lyric helper is ultimately a request for the native PlayState
		// lyric line.  Do not execute donor FlxText construction or display-list
		// manipulation from imported HScript: recognize the operation by its
		// engine-neutral text/line shape and hand the positional payload to one
		// bounded native adapter.  The same structural route works for unrelated
		// packs which provide a two-line lyric module with different class names.
		if (isLyricHelperBody(source)) {
			var lyricArgs = callbackArgumentList(arguments);
			var second = new EReg('\\blyricObj2nd\\s*=\\s*new\\s+FlxText', 'm').match(source);
			return 'HxcCompatRuntime.setLyricText(PlayState.instance, [' + lyricArgs
				+ '], ' + (second ? 'true' : 'false') + ');';
		}
		// Lyric module teardown owns only its two text lines. Lower that lifecycle
		// operation to the native actor-owned line cleanup; arbitrary FlxText
		// destruction in unrelated HXC modules remains subject to the normal
		// safety gate.
		if (isLyricClearBody(source))
			return 'HxcCompatRuntime.clearLyricText(PlayState.instance);';
		// Vignette modules are a thin donor wrapper around the same runtime shader
		// and tween pair already owned by PlayState's native Vignette event route.
		// Recognize shader setup/teardown and pause/resume by their operations, not
		// by a donor class or script filename, and keep the actual shader/filter
		// objects behind the PlayState boundary.
		if (isVignetteSetupBody(source))
			return 'HxcCompatRuntime.prepareVignette(PlayState.instance);';
		if (isVignetteClearBody(source))
			return 'HxcCompatRuntime.clearVignette(PlayState.instance);';
		if (isVignettePauseBody(source))
			return 'HxcCompatRuntime.pauseVignette(PlayState.instance);';
		if (isVignetteResumeBody(source))
			return 'HxcCompatRuntime.resumeVignette(PlayState.instance);';
		if (isVignetteTweenBody(source)) {
			var vignetteArgs = callbackArgumentList(arguments);
			return 'HxcCompatRuntime.setVignette(PlayState.instance, [' + vignetteArgs + ']);';
		}
		// Imported sound-tray modules often contain large Bitmap/Assets loops for
		// bars and backing art. Keep those operations out of HScript and pass only
		// the authored stage allow-list/scale to a native tray boundary. The host
		// may apply a scoped theme when its tray supports it; otherwise it retains
		// the normal Disappointing Plus tray and reports a bounded no-op.
		if (isSoundTrayApplyBody(source))
			return 'resetSoundTray = true; HxcCompatRuntime.configureSoundTray(FlxG.sound.soundTray, PlayState.instance.currentStageId, ddtoStages, graphicScale, true);';
		if (isSoundTrayRestoreBody(source))
			return 'HxcCompatRuntime.configureSoundTray(FlxG.sound.soundTray, PlayState.instance.currentStageId, ddtoStages, graphicScale, false);';
		// Preference-page mutation is a donor UI graph. A native destination may
		// opt into the bounded adapter, but imported code never receives the donor
		// PreferencesMenu/OptionsCodex objects directly.
		if (isPreferencePageBody(source))
			return 'HxcCompatRuntime.applyPreferencePage(' + firstArgument + '.targetState, __hxcStore);';
		if (isPreferenceSeparatorBody(source)) {
			var separatorArgs = callbackArgumentList(arguments);
			return 'HxcCompatRuntime.addPreferenceSeparator([' + separatorArgs + ']);';
		}
		// Menu override modules inspect input and donor menu collections.  Keep
		// both operations behind a native boundary: the host may opt in to the
		// equivalent back action, while an ordinary imported menu gets a bounded
		// no-op instead of direct access to `FlxG.state`/`optionsCodex` graphs.
		if (isMenuOverrideUpdateBody(source))
			return 'HxcCompatRuntime.updateMenuOverrides(currentFreeplayState, save, ' + firstArgument + ');';
		if (isMenuOverrideStateChangeBody(source))
			return 'HxcCompatRuntime.applyMenuOverrides(' + firstArgument + '.targetState, __hxcStore);';
		if (methodName != null && methodName.toLowerCase() == 'switchstateoverride'
			&& isMenuRedirectHelperBody(source))
			return 'HxcCompatRuntime.applyMenuRedirect(' + firstArgument + ');';
		// Two mounted TAKEOVER modules target donor-owned state graphs which do
		// not have a safe object-by-object equivalent in this fork.  Recognize the
		// complete authored operation and route it through one bounded native
		// lifecycle adapter instead of exposing GameOverSubState internals or the
		// V-Slice menu collection to HScript.  Keep this pattern structural: a
		// partial/unknown callback remains subject to the normal module safety gate.
		if (methodName != null && methodName.toLowerCase() == 'onsubstateopenend') {
			var gameOverData = gameOverReplacementData(source, moduleSource);
			if (gameOverData != null)
				return 'HxcCompatRuntime.handleImportedGameOverReplacement(' + firstArgument
					+ ', hxcAssetRoot, ' + stringArrayLiteral(gameOverData.roster)
					+ ', ' + quote(gameOverData.replacement) + ');';
		}
		if (methodName != null && methodName.toLowerCase() == 'onstatechangeend'
			&& new EReg('\\bcreateMenuItem\\s*\\(', 'm').match(source)
			&& new EReg('\\brepositionMenuItems\\s*\\(', 'm').match(source)
			&& new EReg('["\\\']costumes["\\\']', 'm').match(source)
			&& new EReg('\\bcurrentState\\s*\\.\\s*menuItems\\s*\\.\\s*addItem\\s*\\(', 'm').match(source)
			&& new EReg('\\bScriptedMusicBeatState\\s*\\.\\s*init\\s*\\(\\s*["\\\']Costumes["\\\']\\s*\\)', 'm').match(source))
			return 'HxcCompatRuntime.addCostumeMenuItem(' + firstArgument
				+ '.targetState, hxcStateInit("Costumes"));';
		// A complete authored capsule filter/icon/atlas operation is lowered from
		// its literal data, independently of the donor module or content names.
		var freeplayPlan = freeplayCustomizationPlan(moduleSource);
		if (freeplayPlan != null && methodName != null) {
			var hookKind = freeplayCustomizationHook(source, methodName, firstArgument);
			var planLiteral = freeplayCustomizationPlanLiteral(freeplayPlan);
			if (hookKind == 'all' && methodName.toLowerCase() == 'onsubstateopenend')
				return 'HxcCompatRuntime.applyFreeplayCustomization(' + firstArgument
					+ '.targetState, null, ' + planLiteral + ');';
			if (hookKind == 'all' && methodName.toLowerCase() == 'ondifficultyswitch')
				return 'HxcCompatRuntime.applyFreeplayCustomization(currentFreeplayState, null, '
					+ planLiteral + ');';
			if (hookKind == 'selected' && methodName.toLowerCase() == 'oncapsuleselected')
				return 'HxcCompatRuntime.applyFreeplayCustomization(currentFreeplayState, '
					+ firstArgument + '.capsule, ' + planLiteral + ');';
		}
		// The native host owns FreeplayState directly. Only callbacks which are
		// visibly about the donor Freeplay graph may use that alias; ordinary
		// module/state callbacks keep FlxG.state so a generic state hook does not
		// accidentally acquire Freeplay-only semantics.
		if (isFreeplayModuleBody(source, methodName)) {
			output = new EReg('\\bFlxG\\s*\\.\\s*state\\s*\\.\\s*subState\\b', 'g')
				.replace(output, 'currentFreeplayState');
			output = new EReg('\\bFlxG\\s*\\.\\s*state\\b', 'g')
				.replace(output, 'currentFreeplayState');
			// The donor keeps these values on its FreeplayState instance, while
			// this fork stores them as statics. HScript reflection on an instance
			// cannot see Haxe static fields, so route the donor-shaped API through
			// explicit native getters/setters.
			output = new EReg('\\bcurrentFreeplayState\\s*\\.\\s*curSelected\\b', 'g')
				.replace(output, 'currentFreeplayState.hxcSelectedIndex');
			output = new EReg('\\bcurrentFreeplayState\\s*\\.\\s*curDifficulty\\b', 'g')
				.replace(output, 'currentFreeplayState.hxcDifficultyIndex');
			output = new EReg('\\bcurrentFreeplayState\\s*\\.\\s*curCategory\\b', 'g')
				.replace(output, 'currentFreeplayState.hxcCategoryId');
		}
		// HXC modules use FunkinSound as a process-global wrapper.  Keep the
		// operation inside the native compatibility host; arbitrary donor sound
		// singletons are never exposed to an imported interpreter.
		output = new EReg('\\bFunkinSound\\s*\\.\\s*playOnce\\s*\\(', 'g')
			.replace(output, 'hxcFreeplayPlaySound(');
		output = new EReg('\\bFunkinSound\\s*\\.\\s*playMusic\\s*\\(', 'g')
			.replace(output, 'hxcFreeplayPlayMusic(');
		output = new EReg('\\bFlxTransitionableState\\s*\\.\\s*skipNextTransIn\\b', 'g')
			.replace(output, 'HxcCompatRuntime.skipNextTransIn');
		output = new EReg('\\bFlxTransitionableState\\s*\\.\\s*skipNextTransOut\\b', 'g')
			.replace(output, 'HxcCompatRuntime.skipNextTransOut');
		// DifficultyOrderFix rebuilds donor-only DifficultyDot objects.  The
		// semantic boundary that survives this port is the authored difficulty
		// ordering; FreeplayState applies it to its native selector.  Do not copy
		// donor UI objects or DotType enum values into HScript.
		if (methodName != null && methodName.toLowerCase() != 'new'
			&& new EReg('\\bdifficultyDots\\b|\\bDifficultyDot\\b|\\bDotType\\b', 'm').match(source)) {
			var first = arguments == null || arguments.length == 0 ? 'currentFreeplayState' : arguments[0];
			return 'HxcCompatRuntime.reorderFreeplayDifficulties(' + first + ', ["easy", "normal", "hard", "erect", "nightmare"]);';
		}
		// FreeplayTransitionFix animates a donor-specific capsule graph before
		// closing.  The native host owns the same transition boundary but not those
		// V-Slice movers; route the close through one bounded native operation.
		if (methodName != null && methodName.toLowerCase() != 'new'
			&& new EReg('\\bexitMovers\\b|\\bbackingCard\\b|\\b_parentState\\b', 'm').match(source))
			return 'HxcCompatRuntime.freeplayReturnToMenu(currentFreeplayState);';
		return output;
	}

	/** V-Slice exposes animation/global offsets as two-element arrays. Native
	 * Character keeps animation offsets by animation name and stores authored
	 * global offsets on its imported character metadata, so lower indexed reads
	 * through the shared native adapter while preserving the receiver role. */
	static function translateIndexedCharacterOffsetReads(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		var receiver = '([A-Za-z_][A-Za-z0-9_]*(?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)*)';
		for (index in [0, 1]) {
			var animation = new EReg(receiver + '\\s*\\.\\s*animOffsets\\s*\\[\\s*'
				+ index + '\\s*\\]', 'g');
			output = animation.replace(output,
				'HxcCompatRuntime.characterAnimationOffset($1, ' + index + ')');
			var global = new EReg(receiver + '\\s*\\.\\s*globalOffsets\\s*\\[\\s*'
				+ index + '\\s*\\]', 'g');
			output = global.replace(output,
				'HxcCompatRuntime.characterGlobalOffset($1, ' + index + ')');
		}
		return output;
	}

	/** Lower only a complete V-Slice StageRegistry replacement to the native
	 * stage lifecycle. A partial graph or extra donor operation stays behind
	 * the module safety gate. Parameter/local names and module identity are free. */
	static function lowerCompleteStageReplacement(source:String, arguments:Array<String>):Null<String> {
		if (source == null || arguments == null || arguments.length != 1
			|| !isIdentifier(arguments[0]))
			return null;
		var body = compactExpression(stripComments(source));
		var loop = ~/for\(([A-Za-z_][A-Za-z0-9_]*)inPlayState\.instance\.currentStage\.group\)/;
		var directory = ~/var([A-Za-z_][A-Za-z0-9_]*)=PlayState\.instance\.currentStage\?\._data\?\.directory\?\?"shared";/;
		if (!loop.match(body) || !directory.match(body))
			return null;
		var spriteName = loop.matched(1);
		var directoryName = directory.matched(1);
		var complete = 'PlayState.instance.remove(PlayState.instance.currentStage);'
			+ 'PlayState.instance.currentStage.kill();'
			+ 'for(' + spriteName + 'inPlayState.instance.currentStage.group)'
			+ '{' + spriteName + '?.kill();PlayState.instance.currentStage.group.remove(' + spriteName + ');}'
			+ 'PlayState.instance.currentStage=StageRegistry.instance.fetchEntry(' + arguments[0] + ');'
			+ 'if(PlayState.instance.currentStage!=null)'
			+ '{var' + directoryName + '=PlayState.instance.currentStage?._data?.directory??"shared";'
			+ 'Paths.setCurrentLevel(' + directoryName + ');'
			+ 'PlayState.instance.currentStage.revive();'
			+ 'PlayState.instance.resetCameraZoom();'
			+ 'PlayState.instance.currentStage.buildStage();'
			+ 'PlayState.instance.currentStage.resetStage();'
			+ 'PlayState.instance.add(PlayState.instance.currentStage);}';
		return body == complete ? 'PlayState.instance.swapStage(' + arguments[0] + ');' : null;
	}

	/** Return whether one module body is explicitly targeting the donor Freeplay graph. */
	static function isFreeplayModuleBody(source:String, methodName:String):Bool {
		if (source == null)
			return false;
		var name = methodName == null ? '' : methodName.toLowerCase();
		if (name == 'ondifficultyswitch' || name == 'oncapsuleselected')
			return true;
		// State-open callbacks and update hooks can also target Freeplay, but only
		// when their source names the donor state/graph. This keeps generic
		// FlxG.state lifecycle code on its normal native route.
		if (new EReg('\\b(?:FreeplayState|SongMenuItem|grpCapsules|freeplayData|weekType|'
			+ 'capsuleOnConfirmDefault|exitMovers|backingCard)\\b', 'm').match(source)
			&& new EReg('\\bFlxG\\s*\\.\\s*state\\b|\\bcurrentFreeplayState\\b', 'm').match(source))
			return true;
		return false;
	}

	/**
		Haxe's private-access marker only affects compile-time visibility checks.
		HScript resolves fields dynamically, so retain the following expression but
		remove this marker before it reaches the HScript parser. Other metadata stays
		untouched and remains covered by the unsupported-syntax diagnostic.
	*/
	static function lowerPrivateAccessMetadata(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = new StringBuf();
		var token = '@:privateAccess';
		var index = 0;
		var quote = '';
		var escaped = false;
		var lineComment = false;
		var blockComment = false;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (lineComment) {
				output.add(current);
				if (current == '\n')
					lineComment = false;
				index++;
				continue;
			}
			if (blockComment) {
				output.add(current);
				if (current == '*' && next == '/') {
					output.add(next);
					index += 2;
					blockComment = false;
				} else {
					index++;
				}
				continue;
			}
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '/' && next == '/') {
				output.add('//');
				index += 2;
				lineComment = true;
				continue;
			}
			if (current == '/' && next == '*') {
				output.add('/*');
				index += 2;
				blockComment = true;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			var tokenEnd = index + token.length;
			var beforeIsBoundary = index == 0 || !isIdentifierPart(source.charAt(index - 1));
			var afterIsBoundary = tokenEnd >= source.length || !isIdentifierPart(source.charAt(tokenEnd));
			if (beforeIsBoundary && afterIsBoundary && source.substr(index, token.length) == token) {
				index = tokenEnd;
				continue;
			}
			output.add(current);
			index++;
		}
		return output.toString();
	}

	/** Translate only syntax whose semantics are unambiguous in HScript. */
	static function translateBody(source:String, ?methodName:String, ?arguments:Array<String>,
		keepCharacterSuper:Bool = false, skipNativeObjectLowering:Bool = false):String {
		var fullscreenHelper = methodName != null
			&& methodName.toLowerCase() == 'forcedisablefullscreen';
		var output = fullscreenHelper
			? 'HxcCompatRuntime.disableFullscreen();'
			: (source == null ? '' : source);
		output = lowerPrivateAccessMetadata(output);
		output = lowerHxcApiAliases(output);
		if (!skipNativeObjectLowering)
			output = lowerHxcNativeObjects(output);
		output = lowerQualifiedStateAliases(output);
		if (keepCharacterSuper) {
			output = new EReg('\\bsuper\\s*\\.\\s*playAnimation\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.playAnimation(hxcCharacter(),');
			output = new EReg('\\bsuper\\s*\\.\\s*playSingAnimation\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.playSingAnimation(hxcCharacter(),');
			output = new EReg('\\bsuper\\s*\\.\\s*dance\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.dance(hxcCharacter(),');
			output = new EReg('\\bsuper\\s*\\.\\s*getScreenPosition\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.characterBaseScreenPosition(hxcCharacter(),');
			// Character onNoteHit overrides are dispatched through the shared HXC
			// note payload before PlayState's native singer. Mark the callback as
			// owning the animation, and lower the inherited super call to the
			// native actor ABI instead of silently dropping it.
			if (methodName != null && methodName.toLowerCase() == 'onnotehit'
				&& arguments != null && arguments.length > 0
				&& isIdentifier(arguments[0])) {
				var noteEventArgument = arguments[0];
				output = new EReg('\\bsuper\\s*\\.\\s*onNoteHit\\s*\\(\\s*'
					+ noteEventArgument + '\\s*\\)', 'g')
					.replace(output, 'HxcCompatRuntime.characterDefaultNoteHit(hxcCharacter(), '
						+ noteEventArgument + ')');
				output = 'HxcCompatRuntime.markCharacterNoteHandled(' + noteEventArgument + ');\n'
					+ output;
			}
			// Character onNoteMiss overrides run through the same shared payload.
			// Lower the inherited super call to the native miss-sing surface so a
			// guarded `if (...) super.onNoteMiss(event);` keeps its body instead
			// of being stripped into an empty (unparseable) HScript branch.
			if (methodName != null && methodName.toLowerCase() == 'onnotemiss'
				&& arguments != null && arguments.length > 0
				&& isIdentifier(arguments[0])) {
				var missEventArgument = arguments[0];
				output = new EReg('\\bsuper\\s*\\.\\s*onNoteMiss\\s*\\(\\s*'
					+ missEventArgument + '\\s*\\)', 'g')
					.replace(output, 'HxcCompatRuntime.characterDefaultNoteMiss(hxcCharacter(), '
						+ missEventArgument + ')');
			}
		}
		var parentCall = new EReg('(^|[\\n;{}])[ \\t]*super\\.[A-Za-z_][A-Za-z0-9_]*\\s*\\([^;{}]*\\)\\s*;?', 'gm');
		output = parentCall.replace(output, '$1');
		var superCall = new EReg('(^|[\\n;{}])[ \\t]*super\\s*\\([^;{}]*\\)\\s*;?', 'gm');
		output = superCall.replace(output, '$1');
		output = StringTools.replace(output, 'this.', '');
		// Haxe local annotations are not part of HScript's expression grammar.
		// Keep the declaration/value while removing both simple and generic map
		// annotations.  This also removes function-type annotations such as
		// `Void->Void` before the arrow lowering pass sees them.
		var typedLocal = new EReg('\\b(var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*[A-Za-z_][A-Za-z0-9_.]*(?:<[^;=\\n]+>)?(?:\\s*->\\s*[A-Za-z_][A-Za-z0-9_.]*(?:<[^;=\\n]+>)?)?', 'g');
		output = typedLocal.replace(output, 'var $2');
		var finalLocal = new EReg('\\bfinal\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?==)', 'g');
		output = finalLocal.replace(output, 'var $1 ');
		output = lowerTypedMapSyntax(output);
		output = lowerFunctionArgumentTypes(output);
		output = lowerTypeChecks(output);
		output = lowerOptionalChains(output);
		output = lowerNullCoalescing(output);
		output = lowerLambdaArrows(output);
		// A literal map may carry a zero-argument imported state constructor. Route
		// that value through the manifest-scoped factory; arbitrary `new` calls stay
		// untouched and are rejected by the existing module safety gate.
		output = lowerStateConstructorValues(output);
		// Haxe map literals use `key => value`, which HScript parses neither as a
		// map nor as an arrow function.  Convert only bracket expressions whose
		// top-level entries are authored map pairs; ordinary arrays remain intact.
		output = lowerMapLiterals(output);
		output = lowerLifecycleCalls(output);
		output = lowerZeroDurationCameraEaseArgument(output);
		// A stage song-event callback may perform the same camera flash that the
		// native event route would perform.  Lower only direct camera flashes to a
		// bounded helper which claims the native half of the shared payload after
		// applying the authored HXC effect.  Stage-local overlays and other visual
		// effects remain ordinary callback code, so this is an ownership contract,
		// not a name/song allow-list.
		var firstArg = arguments == null || arguments.length == 0 ? '' : arguments[0];
		if (firstArg != '' && methodName != null && methodName.toLowerCase() == 'onsongEvent'.toLowerCase()) {
			output = new EReg('\\bFlxG\\s*\\.\\s*camera\\s*\\.\\s*flash\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.hxcCameraFlash(' + firstArg + ', FlxG.camera, ');
			output = new EReg('\\bgame\\s*\\.\\s*camGame\\s*\\.\\s*flash\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.hxcCameraFlash(' + firstArg + ', game.camGame, ');
			output = new EReg('\\bgame\\s*\\.\\s*camHUD\\s*\\.\\s*flash\\s*\\(', 'g')
				.replace(output, 'HxcCompatRuntime.hxcCameraFlash(' + firstArg + ', game.camHUD, ');
		}
		// V-Slice passes wrapper objects to these hooks while PlayState passes the
		// primitive value directly.  These rewrites preserve the common event
		// fields without inventing a foreign payload object at runtime.
		if (firstArg != '' && methodName != null) {
			switch (methodName.toLowerCase()) {
				case 'onupdate' | 'update':
					output = StringTools.replace(output, firstArg + '.elapsed', firstArg);
				case 'onbeathit' | 'beathit':
					output = StringTools.replace(output, firstArg + '.beat', firstArg);
				case 'onstephit' | 'stephit' | 'step':
					output = StringTools.replace(output, firstArg + '.step', firstArg);
			case 'onsectionhit' | 'sectionhit':
				output = StringTools.replace(output, firstArg + '.sectionIndex', firstArg);
				output = StringTools.replace(output, firstArg + '.section', firstArg);
		}
		}
		// Statement-dropping passes above (unsupported super calls and other
		// donor-only statements) can leave a control statement with no body,
		// which HScript rejects with EUnexpected(}).  Give any such branch an
		// explicit empty block so the generated script parses; the branch already
		// had no-op semantics, so this preserves them instead of failing the file.
		output = repairEmptyControlBodies(output);
		return output;
	}

	/**
	 * Insert an empty block after any `if`/`for`/`while`/`catch` header or bare
	 * `else` whose body was dropped, i.e. whose header is directly followed by
	 * the enclosing closing brace or by the end of the body text (the generator
	 * adds the closing brace afterwards).  Only the exact empty-body shape is
	 * touched; ordinary code never matches because a real body starts with `{`,
	 * a statement, or a semicolon before the closing brace.  A `while` that a
	 * `}` immediately precedes is left alone because that shape is how a
	 * do-while loop legitimately ends.
	 */
	static function repairEmptyControlBodies(output:String):String {
		if (output == null || output == '')
			return output;
		var withHeader = new EReg('(^|[^\\}])\\b(if|for|while|catch)\\s*\\(([^{}]*)\\)((?:[ \\t]*\\r?\\n)+[ \\t]*|[ \\t]+)\\}', 'g');
		output = withHeader.replace(output, '$1$2($3)$4{}$4}');
		var bareElse = new EReg('\\belse((?:[ \\t]*\\r?\\n)+[ \\t]*|[ \\t]+)\\}', 'g');
		output = bareElse.replace(output, 'else$1{}$1}');
		var trailing = new EReg('\\b(if|for|catch)\\s*\\(([^{}]*)\\)[ \\t]*(\\r?\\n[ \\t]*)*$', '');
		if (trailing.match(output))
			output += ' {}';
		var trailingElse = new EReg('\\belse[ \\t]*(\\r?\\n[ \\t]*)*$', '');
		if (trailingElse.match(output))
			output += ' {}';
		return output;
	}

	static function lowerStateConstructorValues(source:String):String {
		if (source == null || source.indexOf('=>') < 0 || source.indexOf('new ') < 0)
			return source == null ? '' : source;
		return new EReg('=>\\s*new\\s+([A-Za-z_][A-Za-z0-9_]*(?:State|SubState))\\s*\\(\\s*\\)', 'g')
			.replace(source, '=> hxcStateFactory("$1", [])');
	}

	/** Use the canonical generated name for calls between local lifecycle hooks. */
	static function lowerLifecycleCalls(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		for (name in lifecycleNames) {
			var canonical = lifecycleCallback(name);
			if (canonical == '' || canonical == name)
				continue;
			output = new EReg('\\b' + name + '\\s*\\(', 'g').replace(output, canonical + '(');
		}
		return output;
	}

	/**
		Lower the small V-Slice object surface which is genuinely shared by the
		selected imported graph.  The donor classes themselves are never exposed to
		HScript: constructors and process-wide sound calls become explicit native
		facades, while the caller's manifest root remains the only place from which
		an imported sprite/atlas may resolve media.

		Keep this pass separate from the character overlay pass.  Character death
		overlays are lowered first by translateCharacterBody, then the remaining
		ordinary FunkinSprite operations use the same generic adapter.
	*/
	static function lowerHxcNativeObjects(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = lowerHxcNativeStrumlineAssignments(source);
		// HScript's `new Foo(...)` resolves Foo through Type.resolveClass before
		// checking the interpreter variable map. The engine already has a native
		// Strumline class, so binding the donor name to the isolated extra-line
		// adapter is not enough: the native constructor wins and receives the
		// donor's (noteStyle, botplay) arguments. Keep the native player/opponent
		// assignment rewrite above, then route remaining donor constructors by
		// explicit class name.
		output = new EReg('\\bnew\\s+Strumline\\s*\\(', 'g')
			.replace(output, 'new ExtraStrumlineAdapter(');
		// HXC health icons are configured after construction. Their first id can
		// be a logical HUD slot, and a configured icon should not report that
		// short-lived placeholder as a missing source visual.
		output = new EReg('\\bnew\\s+HealthIcon\\s*\\(', 'g')
			.replace(output, 'new HxcHealthIconAdapter(');
		// Donor Strumline.add accepts any sprite. The native receptor group's
		// typed add(StrumNote) can erase a splash before its own runtime check.
		// Route only the known native PlayState strumline slots through the
		// explicitly FlxSprite-typed entry point.
		output = new EReg('\\b((?:(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*)?(?:playerStrumline|opponentStrumline|playerStrums|enemyStrums))\\s*\\.\\s*add\\s*\\(', 'g')
			.replace(output, '$1.addScriptSprite(');
		// A literal style lookup is resolved inside the caller's manifest root.
		// Dynamic registry expressions retain the existing bounded alias.
		output = new EReg('\\bNoteStyleRegistry\\s*\\.\\s*instance\\s*\\.\\s*fetchEntry\\s*\\(\\s*(["\\\'][A-Za-z0-9_-]+["\\\'])\\s*\\)', 'g')
			.replace(output, 'HxcNoteStyleCompat.fetchEntry(hxcAssetRoot, $1)');
		output = new EReg('\\bnew\\s+NoteSplash\\s*\\(', 'g')
			.replace(output, 'new HxcNoteSplashCompat(');
		// The native fork's DynamicSprite is the bounded equivalent of the
		// V-Slice FunkinSprite constructor.  Asset-bearing static constructors use
		// dedicated paths so Sparrow and Animate atlases cannot be mistaken for a
		// single PNG.
		output = new EReg('\\bFunkinSprite\\s*\\.\\s*createTextureAtlas\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinSpriteTextureAtlas(hxcAssetRoot, ');
		output = new EReg('\\bFunkinSprite\\s*\\.\\s*createSparrow\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinSpriteSparrow(hxcAssetRoot, ');
		output = new EReg('\\bFunkinSprite\\s*\\.\\s*create\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinSprite(hxcAssetRoot, ');
		// Match the zero-argument constructor first; inserting a positional root
		// comma into `new FunkinSprite()` would emit `(..., )`, which HScript
		// rejects before the native fallback can run.
		output = new EReg('\\bnew\\s+FunkinSprite\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinSprite(hxcAssetRoot)');
		output = new EReg('\\bnew\\s+FunkinSprite\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinSprite(hxcAssetRoot, ');
		// In-stage FunkinVideoSprite instances must remain ordinary sprites so
		// source cameras, z-order, seeking, looping and end callbacks keep control.
		// The native adapter bounds their media to this script's package owner.
		output = new EReg('\\bnew\\s+FunkinVideoSprite\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinVideoSprite(PlayState.instance, hxcAssetRoot)');
		output = new EReg('\\bnew\\s+FunkinVideoSprite\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinVideoSprite(PlayState.instance, hxcAssetRoot, ');
		output = new EReg('\\bFunkinSprite\\s*\\.\\s*cacheTexture\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.cacheFunkinTexture(hxcAssetRoot, ');
		// FunkinSprite.makeSolidColor is a convenience alias for the native
		// FlxSprite graphic builder.  Lower only that exact method name.
		output = new EReg('\\.\\s*makeSolidColor\\s*\\(', 'g')
			.replace(output, '.makeGraphic(');

		output = new EReg('\\bnew\\s+FunkinCamera\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinCamera(PlayState.instance)');
		output = new EReg('\\bnew\\s+FunkinCamera\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createFunkinCamera(PlayState.instance, ');
		// HXC TouchUtil's desktop predicate has no touch source in this native
		// build. Lower it to the compatibility facade so keyboard alternatives
		// remain available without leaving a donor class unresolved.
		output = new EReg('\\bTouchUtil\\s*\\.\\s*pressAction\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.touchPressAction(');
		output = new EReg('\\bFunkinSound\\s*\\.\\s*playOnce\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.freeplayPlaySound(');
		output = new EReg('\\bFunkinSound\\s*\\.\\s*playMusic\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.freeplayPlayMusic(');
		output = new EReg('\\bFunkinSound\\s*\\.\\s*stopAllAudio\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.stopAllAudio()');
		output = new EReg('\\bFunkinSound\\s*\\.\\s*load\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.loadFunkinSound(hxcAssetRoot, ');

		// Native WiggleEffect owns the shader and has the same update contract. The
		// generated object therefore remains updateable, while assignments to a
		// FlxSprite.shader receive only its engine-owned shader field.
		output = new EReg('\\bnew\\s+WiggleEffectRuntime\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.createWiggleEffect(');
		for (kind in ['DREAMY', 'WAVY', 'HEAT_WAVE_HORIZONTAL', 'HEAT_WAVE_VERTICAL', 'FLAG'])
			output = new EReg('\\bWiggleEffectType\\s*\\.\\s*' + kind + '\\b', 'g')
				.replace(output, '"' + kind + '"');
		output = new EReg('(\\.\\s*shader\\s*=\\s*)(wiggle[A-Za-z0-9_]*)\\b', 'g')
			.replace(output, '$1$2.shader');
		// A donor filter array may name a field whose initializer was not portable;
		// OpenFL dereferences every entry while rendering, so route the write
		// through a helper that drops null entries before they reach a camera.
		output = lowerFilterAssignments(output);
		// Donor tweens may target fields the native fork does not carry; the
		// native tween manager would throw outside every script try/catch.
		output = new EReg('\\bFlxTween\\s*\\.\\s*tween\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.safeTween(');
		return output;
	}

	/**
		Rewrite `<target>.filters = <array>;` writes to the null-stripping
		runtime helper. The scanner keeps balanced brackets and quotes while
		looking for the end of the assigned expression, so array literals with
		nested calls stay intact. Comparison operators (`==`, `!=`) and the
		`filtersEnabled` field never match the assignment pattern.
	*/
	static function lowerFilterAssignments(source:String):String {
		if (source == null || source.indexOf('.filters') < 0)
			return source;
		var expression = new EReg('([A-Za-z_][A-Za-z0-9_]*(?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)*)\\s*\\.\\s*filters\\s*=', '');
		var output = new StringBuf();
		var index = 0;
		while (index < source.length) {
			var remaining = source.substr(index);
			if (!expression.match(remaining))
				break;
			var position = expression.matchedPos();
			var equalsEnd = index + position.pos + position.len;
			// A following `=` means the donor wrote a `==` comparison, not an
			// assignment; copy the matched text verbatim and keep scanning.
			if (equalsEnd < source.length && source.charAt(equalsEnd) == '=') {
				output.add(source.substr(index, position.pos + position.len));
				index += position.pos + position.len;
				continue;
			}
			var target = StringTools.replace(expression.matched(1), ' ', '');
			var statementEnd = filterAssignmentEnd(source, equalsEnd);
			if (statementEnd < 0)
				break;
			var endedWithSemicolon = statementEnd > equalsEnd
				&& source.charAt(statementEnd - 1) == ';';
			var valueEnd = endedWithSemicolon ? statementEnd - 1 : statementEnd;
			var value = StringTools.trim(source.substr(equalsEnd, valueEnd - equalsEnd));
			if (value == '') {
				output.add(source.substr(index, position.pos + position.len));
				index += position.pos + position.len;
				continue;
			}
			output.add(source.substr(index, position.pos));
			// The original terminator (or its newline) is consumed below, so the
			// replacement always carries its own `;` to keep statement boundaries.
			output.add('HxcCompatRuntime.assignFilters(' + target + ', ' + value + ');');
			index = statementEnd;
		}
		output.add(source.substr(index));
		return output.toString();
	}

	/** Find the closing `;` (or newline) of one statement at bracket depth zero. */
	static function filterAssignmentEnd(source:String, from:Int):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in from...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == '(' || current == '[' || current == '{')
				depth++;
			else if (current == ')' || current == ']' || current == '}')
				depth--;
			else if (depth == 0 && current == ';')
				return index + 1;
			else if (depth == 0 && current == '\n')
				return index;
		}
		return -1;
	}

	/**
		V-Slice exposes the active receptor groups as assignable fields.  In this
		engine they are read-only views over the native PlayState groups, while the
		`Strumline` name in an imported interpreter is reserved for the isolated
		extra-line adapter.  Lower the one authored replacement shape to a native
		reconfiguration hook before the adapter constructor pass can see it.  The
		balanced scanner deliberately accepts only `new Strumline(...)` assigned to
		the two known PlayState slots; arbitrary object replacement remains visible
		to the HXC diagnostics instead of being reflected into the host.
	*/
	static function lowerHxcNativeStrumlineAssignments(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		for (side in ['player', 'opponent']) {
			var search = 0;
			var attempts = 0;
			while (attempts++ < 128 && search < output.length) {
				var pattern = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)'
					+ '\\s*\\.\\s*' + side + 'Strumline\\s*=\\s*new\\s+Strumline\\s*\\(', 'm');
				var remaining = output.substr(search);
				if (!pattern.match(remaining))
					break;
				var matched = pattern.matchedPos();
				var callStart = search + matched.pos;
				var open = output.indexOf('(', callStart);
				if (open < 0)
					break;
				var close = matchingDelimiter(output, open, '(', ')');
				if (close < 0)
					break;
				var parts = splitTopLevel(output.substr(open + 1, close - open - 1), ',');
				if (parts.length == 0 || StringTools.trim(parts[0]) == '') {
					search = close + 1;
					continue;
				}
				var style = StringTools.trim(parts[0]);
				var botplay = parts.length > 1 && StringTools.trim(parts[1]) != ''
					? StringTools.trim(parts[1]) : 'false';
				var speed = parts.length > 2 && StringTools.trim(parts[2]) != ''
					? StringTools.trim(parts[2]) : 'null';
				var replacement = 'HxcCompatRuntime.configureNativeStrumline(PlayState.instance, '
					+ quote(side) + ', ' + style + ', ' + botplay + ', ' + speed + ')';
				output = output.substr(0, callStart) + replacement + output.substr(close + 1);
				search = callStart + replacement.length;
			}
		}
		// The donor calls this after replacing both views to rebuild their receptors.
		// Reconfiguration already rebuilds the native group, but keep the lifecycle
		// boundary explicit so a future native host can refresh cameras/visibility.
		output = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)'
			+ '\\s*\\.\\s*initStrumlines\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.refreshNativeStrumlines(PlayState.instance)');
		// DDTO restores these donor static dimensions during teardown. They are
		// process-local compatibility values, not assignable fields on the native
		// Strumline class; keep the values bounded and isolated from normal groups.
		output = new EReg('\\bStrumline\\s*\\.\\s*STRUMLINE_SIZE\\b', 'g')
			.replace(output, 'HxcCompatRuntime.strumlineSize');
		output = new EReg('\\bStrumline\\s*\\.\\s*NOTE_SPACING\\b', 'g')
			.replace(output, 'HxcCompatRuntime.noteSpacing');
		return output;
	}

	/**
		Normalize donor object names which have a direct native equivalent.  The
		method names themselves stay intact: PlayState, StageHelper, and Character
		seed the corresponding HXC accessors, which also keeps chained expressions
		(`PlayState.instance.currentStage.getDad()`) readable in diagnostics.
	*/
	static function lowerHxcApiAliases(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		// Imported modules use ModuleHandler as a process-global registry. Route
		// calls through the PlayState-owned scope proxy instead; the proxy only
		// exposes generated HScript callbacks and cannot instantiate donor classes.
		output = new EReg('\\bModuleHandler\\s*\\.\\s*getModule\\s*\\(', 'g')
			.replace(output, 'hxcGetModule(');
		// HXC's ModStore facade is a process-global singleton in the donor. Each
		// generated module already receives its manifest-scoped key/value store as
		// `__hxcStore`, so preserve the API while keeping writes in that scope.
		output = new EReg('\\bModStore\\s*\\.\\s*stores\\b', 'g')
			.replace(output, '__hxcStore');
		output = new EReg('\\bModStore\\s*\\.\\s*(get|set)\\s*\\(', 'g')
			.replace(output, '__hxcStore.$1(');
		// Namespaced preference singletons expose a Save-like object. Preserve the
		// getter ABI over the selected HXC root's isolated key/value store without
		// naming a donor's module or static function.
		output = new EReg('\\b[A-Za-z_][A-Za-z0-9_]*Preferences\\s*\\.\\s*get[A-Za-z_][A-Za-z0-9_]*Save\\s*\\(\\s*\\)', 'g')
			.replace(output, '__hxcStore.getSave()');
		output = new EReg('\\bSave\\s*\\.\\s*instance\\b', 'g')
			.replace(output, '__hxcStore');
		// Imported event modules use one namespaced extra-events preference bag.
		// Expose only the two native gates owned by this fork; unknown donor option
		// fields remain ordinary store data and therefore stay behind the safety
		// boundary.
		output = new EReg('__hxcStore\\s*\\?\\.\\s*modOptions\\s*\\?\\.\\s*get\\s*\\(\\s*["\\\']extra-events["\\\']\\s*\\)\\s*\\?\\.\\s*isLyricsEnabled\\b', 'g')
			.replace(output, 'HxcCompatRuntime.lyricsEnabled');
		output = new EReg('__hxcStore\\s*\\?\\.\\s*modOptions\\s*\\?\\.\\s*get\\s*\\(\\s*["\\\']extra-events["\\\']\\s*\\)\\s*\\?\\.\\s*isVignEnabled\\b', 'g')
			.replace(output, 'HxcCompatRuntime.vignetteEffects');
		// Highscore.tallies is a per-song donor view, not persistent score data.
		// Bind only the native per-song counters exposed by HxcCompatRuntime;
		// unknown tally members remain visible to the safety audit.
		output = new EReg('\\bHighscore\\s*\\.\\s*tallies\\b', 'g')
			.replace(output, 'HxcCompatRuntime.tallies');
		// V-Slice character scripts select game-over/pause audio by assigning
		// static suffix fields on donor substates.  Those classes do not exist in
		// this fork, so lower only the documented suffix fields to the bounded
		// runtime hand-off.  Other donor substate members remain visible and are
		// still rejected by the character safety gate.
		for (field in [
			{owner: 'GameOverSubState', member: 'musicSuffix', setter: 'setGameOverMusicSuffix', getter: 'gameOverMusicSuffix'},
			{owner: 'GameOverSubState', member: 'blueBallSuffix', setter: 'setGameOverBlueBallSuffix', getter: 'gameOverBlueBallSuffix'},
			{owner: 'PauseSubState', member: 'musicSuffix', setter: 'setPauseMusicSuffix', getter: 'pauseMusicSuffix'}
		]) {
			var assignment = new EReg('\\b' + field.owner + '\\s*\\.\\s*' + field.member
				+ '\\s*=(?!=)\\s*', 'g');
			var assignmentOffset = 0;
			while (assignment.matchSub(output, assignmentOffset)) {
				var span = assignment.matchedPos();
				var expressionStart = span.pos + span.len;
				// Source assignments can contain multiline ternaries and quoted
				// semicolons. End at the statement boundary, not a physical line.
				var expressionLength = findTopLevelToken(output.substr(expressionStart), ';');
				if (expressionLength < 0) break;
				var expression = output.substr(expressionStart, expressionLength);
				var replacement = 'HxcCompatRuntime.' + field.setter + '(' + expression + ')';
				output = output.substr(0, span.pos) + replacement
					+ output.substr(expressionStart + expressionLength);
				assignmentOffset = span.pos + replacement.length;
			}
			output = new EReg('\\b' + field.owner + '\\s*\\.\\s*' + field.member + '\\b', 'g')
				.replace(output, 'HxcCompatRuntime.' + field.getter);
		}
		// The native PlayState seeds downscroll directly. This is the one preference
		// whose value is live and unambiguous here; controls/visual preferences are
		// intentionally left as donor-only diagnostics.
		output = new EReg('\\bPreferences\\s*\\.\\s*downscroll\\b', 'g')
			.replace(output, 'downscroll');
		// The native fork keeps strumline backgrounds fully opaque and does not
		// persist the donor's visual preference object. Expose that explicit
		// fallback through the isolated compatibility bag.
		output = new EReg('\\bPreferences\\s*\\.\\s*strumlineBackgroundOpacity\\b', 'g')
			.replace(output, 'HxcCompatRuntime.preferences.strumlineBackgroundOpacity');
		// V-Slice's rank helper consumes only the plain tally object assembled by
		// imported score modules. Route this one named operation to the bounded
		// native adapter; other Scoring methods stay unsupported.
		output = new EReg('\\bScoring\\s*\\.\\s*calculateRank\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.calculateRank(');
		// WindowUtil/Application are donor process globals. Keep title/icon writes
		// on the explicit native host bridge instead of exposing a mutable window.
		output = new EReg('\\bWindowUtil\\s*\\.\\s*setWindowTitle\\s*\\(', 'g')
			.replace(output, 'hxcSetWindowTitle(');
		output = lowerBareSetIconCalls(output);
		// CreditsDataHandler is a donor-side singleton.  The native CreditsState
		// consumes the same plain entry shape through this isolated process-local
		// list; no donor class or file path is resolved by imported HXC.
		output = new EReg('\\bCreditsDataHandler\\s*\\.\\s*CREDITS_DATA\\s*\\.\\s*entries\\b', 'g')
			.replace(output, 'HxcCompatRuntime.creditsEntries');
		// DDTO's RPC module writes only the two mutable presence strings. Keep those
		// writes on an engine-owned view while exposing the live native chart album.
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*discordRPCIcon\\b', 'g')
			.replace(output, 'HxcCompatRuntime.discordRPCIcon');
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*discordRPCAlbum\\b', 'g')
			.replace(output, 'HxcCompatRuntime.discordRPCAlbum');
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*currentChart\\s*\\.\\s*album\\b', 'g')
			.replace(output, 'HxcCompatRuntime.currentChartAlbum');
		// Character hooks may branch on the active variation.  The native chart
		// has no required variation field, so the runtime exposes a safe empty
		// string by default and a host-provided value when one exists.
		output = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*currentVariation\\b', 'g')
			.replace(output, 'HxcCompatRuntime.currentVariation');
		// Keep this read on the donor-facing FlxG surface.  The generated stage
		// can be executed by a small isolated interpreter (which supplies FlxG
		// directly) as well as the game interpreter; routing a constant constructor
		// guard through HxcCompatRuntime would make the former depend on a global
		// runtime object unrelated to the event handler.
		output = new EReg('\\bFlxG\\s*\\.\\s*onMobile\\b', 'g')
			.replace(output, 'FlxG.onMobile');
		// Date.now().getTime() is used only for cache-busting RPC URLs. Keep the
		// timestamp read on the native process boundary; the imported interpreter
		// never receives a Date singleton or arbitrary time API.
		output = new EReg('\\bDate\\s*\\.\\s*now\\s*\\(\\s*\\)\\s*\\.\\s*getTime\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.timestamp()');
		output = new EReg('\\bDate\\s*\\.\\s*now\\s*\\(\\s*\\)\\s*\\.\\s*getDay\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.weekday()');
		// PlayStatePlaylist and Countdown are V-Slice process facades rather than
		// objects which can safely be reflected into imported HXC. Route the small
		// read/control surface through the native owner, leaving any other member
		// visible to the diagnostic pass below.
		output = new EReg('\\bPlayStatePlaylist\\s*\\.\\s*isStoryMode\\b', 'g')
			.replace(output, 'HxcCompatRuntime.playStatePlaylistIsStoryMode');
		output = new EReg('\\bCountdown\\s*\\.\\s*skipCountdown\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.skipCountdown(PlayState.instance)');
		output = new EReg('\\bCountdown\\s*\\.\\s*stopCountdown\\s*\\(\\s*\\)', 'g')
			.replace(output, 'HxcCompatRuntime.stopCountdown(PlayState.instance)');
		output = new EReg('\\bFullScreenScaleMode\\s*\\.', 'g')
			.replace(output, 'HxcCompatRuntime.fullScreenScaleMode.');
		// VideoCutscene.play is a static donor helper. Parse its balanced argument
		// list instead of using a comma-limited regexp so Paths/Assets calls remain
		// intact. Only the explicit ENDING mode changes the native completion route.
		output = lowerVideoCutsceneCalls(output);
		output = lowerBareForceDisableFullscreenCalls(output);
		// The donor shader wrapper is a named constructor around the same runtime
		// shader object used by the native HScript seed. Do not lower arbitrary
		// shader classes or script methods.
		output = new EReg('\\bScriptedFlxRuntimeShader\\s*\\.\\s*init\\s*\\(', 'g')
			.replace(output, 'createRuntimeShader(');
		// V-Slice's Constants singleton is a read/write bag of engine defaults.
		// Keep only the generic values owned by this runtime; unknown donor classes
		// remain visible to the safety gate instead of being instantiated.
		output = new EReg('\\bConstants\\s*\\.', 'g')
			.replace(output, 'HxcCompatRuntime.constantsForRoot(hxcAssetRoot).');
		// Flixel bitmap reads require integer coordinates at the native boundary.
		// Route the common sprite pixel API through a bounded helper so imported
		// HScript can use Float sampling expressions without invoking BitmapData
		// methods directly or relying on interpreter-specific numeric coercion.
		output = new EReg('\\b((?:[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*)*[A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*pixels\\s*\\.\\s*getPixel32\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.spritePixelColor32($1, ');
		output = new EReg('\\bStringTools\\s*\\.\\s*contains\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.stringContains(');
		output = new EReg('\\bStringTools\\s*\\.\\s*startsWith\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.stringStartsWith(');
		output = lowerHxcStringStartsWith(output);
		// Costume modules load character JSON only to consume the preserved native
		// costume metadata. Route that read through Character's registry-backed
		// adapter and route swaps through PlayState's live character path.
		output = new EReg('\\bjsonLoad\\s*\\(', 'g').replace(output, 'hxcGetCharacterData(');
		output = new EReg('\\bchangeCharacter\\s*\\(', 'g').replace(output, 'hxcChangeCharacter(');
		// Costume modules warm a character through the donor parser before a
		// ChangeCharacter event. The native bridge performs the same warm-load and
		// exposes a data-only result for the donor's optional cache reads.
		output = new EReg('\\bCharacterDataParser\\s*\\.\\s*parseCharacterData\\s*\\(', 'g')
			.replace(output, 'hxcPrepareCharacter(');
		output = new EReg('\\bCharacterDataParser\\s*\\.\\s*fetchCharacterData\\s*\\(', 'g')
			.replace(output, 'hxcPrepareCharacter(');
		// CharacterDataParser's live registry/factory has a narrow native
		// equivalent. Keep the existence check tied to Character.characterExists
		// so unknown donor ids do not silently construct a fallback actor.
		output = new EReg('\\bCharacterDataParser\\s*\\.\\s*listCharacterIds\\s*\\(\\s*\\)\\s*\\.\\s*contains\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.characterExists(');
		output = new EReg('\\bCharacterDataParser\\s*\\.\\s*fetchCharacter\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.fetchCharacter(');
		output = new EReg('\\bCharacterDataParser\\s*\\.\\s*characterCache\\b', 'g')
			.replace(output, 'hxcCharacterCache');
		// Native Character has no donor set_characterType/initHealthIcon methods.
		// Their only safe mounted use is immediately around a StageHelper character
		// replacement; carry the role hint and let the canonical PlayState bridge
		// update the actual slot/icons. Unknown Character methods remain diagnosed.
		output = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*set_characterType\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.setCharacterType($1,');
		output = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*\\.\\s*initHealthIcon\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.initHealthIcon($1,');
		output = new EReg('\\bFunkinMemory\\s*\\.\\s*cacheTexture\\s*\\(', 'g')
			.replace(output, 'hxcCacheTexture(');
		// Sound pre-caching warms the same manifest-scoped loader the donor
		// plays through; there is no separate memory surface to expose.
		output = new EReg('\\bFunkinMemory\\s*\\.\\s*cacheSound\\s*\\(', 'g')
			.replace(output, 'hxcCacheSound(');
		// FlxSave is intentionally not instantiated from imported HXC. The
		// constructor adapter supplies an isolated store with the same data/bind/
		// flush surface, so no donor save file or singleton is touched.
		output = new EReg('\\bnew\\s+FlxSave\\s*\\(\\s*\\)', 'g').replace(output, '__hxcStore');
		// StageHelper.addCharacter(Character, CharacterType) is a donor method;
		// route only direct active-stage calls through the native PlayState-owned
		// slot replacement. Local/foreign stage graphs remain diagnostics.
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*currentStage\\s*\\.\\s*addCharacter\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.stageAddCharacter(PlayState.instance.currentStage,');
		output = new EReg('\\b(currentPlayState|game)\\s*\\.\\s*currentStage\\s*\\.\\s*addCharacter\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.stageAddCharacter($1.currentStage,');
		for (role in [
			{source: 'BF', value: 'bf'},
			{source: 'DAD', value: 'dad'},
			{source: 'GF', value: 'gf'},
			{source: 'OTHER', value: 'other'}
		]) {
			output = new EReg('\\bCharacterType\\s*\\.\\s*' + role.source + '\\b', 'g')
				.replace(output, '"' + role.value + '"');
		}
		// The donor's Song model calls the active chart `currentSong.id`, while
		// this engine stores that identity in SwagSong.song. Use the chart object
		// seeded into HScript so the comparison keeps its authored value instead
		// of reading a nonexistent `id` field from the native typedef.
		output = new EReg('\\bPlayState\\s*\\.\\s*instance\\s*\\.\\s*currentSong\\s*\\.\\s*id\\b', 'g')
			.replace(output, 'SONG.song');
		output = new EReg('\\b(?:currentPlayState|game)\\s*\\.\\s*currentSong\\s*\\.\\s*id\\b', 'g')
			.replace(output, 'SONG.song');
		// Donor FunkinSound exposes a player vocal bus, while the native chart
		// stores role-tagged stems in VocalTracks. Preserve the bus operation
		// without exposing the FlxSound or treating opponent stems as players.
		output = new EReg('\\b(PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*vocals\\s*\\.\\s*set_playerVolume\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.setPlayerVocalVolume($1, ');
		output = new EReg('\\b(PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*vocals\\s*\\.\\s*playerVolume\\s*=\\s*(?!=)([^;\\n]+);', 'g')
			.replace(output, 'HxcCompatRuntime.setPlayerVocalVolume($1, $2);');
		output = new EReg('\\b(PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*vocals\\s*\\.\\s*playerVolume\\b', 'g')
			.replace(output, 'HxcCompatRuntime.getPlayerVocalVolume($1)');
		output = new EReg('\\b(PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*vocals\\s*\\.\\s*opponentVoices\\b', 'g')
			.replace(output, 'HxcCompatRuntime.opponentVocalTracks($1)');
		// V-Slice modules also spell the active chart identity as
		// currentChart.song.id. The native SwagSong stores that identity directly
		// in SONG.song, so lower this exact donor field chain before HScript sees
		// the absent currentChart wrapper.
		output = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*currentChart\\s*\\.\\s*song\\s*\\.\\s*id\\b', 'g')
			.replace(output, 'SONG.song');
		// Common module code stores the seeded PlayState in a short `ps` alias
		// before reading the donor song id. This is the one additional local
		// spelling used by the mounted corpus; no arbitrary object reflection is
		// introduced for other aliases.
		output = new EReg('\\bps\\s*\\.\\s*song\\s*\\.\\s*id\\b', 'g')
			.replace(output, 'SONG.song');
		// Some modules first bind the seeded PlayState to a local (for example
		// `var ps = PlayState.instance`) and then use the donor Song object's
		// `id`. Preserve that exact identity through the native chart adapter,
		// without broadening this into reflection over arbitrary `song` fields.
		var localPlayStateAliases = collectMatches(output,
			'\\b(?:var|final)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(?:PlayState\\s*\\.\\s*instance|currentPlayState)\\b', 1);
		for (alias in localPlayStateAliases) {
			if (!isIdentifier(alias))
				continue;
			output = new EReg('\\b' + alias + '\\s*\\.\\s*song\\s*\\.\\s*id\\b', 'g')
				.replace(output, 'SONG.song');
			// The mounted modules also use `ps.song == null` as a guard. Lower only
			// that terminal comparison/read shape; deeper donor Song members remain
			// visible to the module safety gate instead of being guessed.
			output = new EReg('\\b' + alias + '\\s*\\.\\s*song\\s*(==|!=|&&|\\|\\||\\)|;|,)', 'g')
				.replace(output, 'SONG$1');
		}
		// A few V-Slice modules call the generated getter spelling directly. The
		// destination exposes the same live chart as SONG; lower only this named
		// accessor rather than reflecting over arbitrary PlayState methods.
		output = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*get_currentChart\\s*\\(\\s*\\)', 'g')
			.replace(output, 'SONG');
		// The native SwagSong stores the three active character ids directly. A
		// plain object preserves the donor `currentChart.characters` shape for
		// the one mounted retry path that reads all three roles at once.
		for (role in [
			{source: 'player', value: 'SONG.player1'},
			{source: 'opponent', value: 'SONG.player2'},
			{source: 'girlfriend', value: 'SONG.gf'}
		]) {
			output = new EReg('\\bSONG\\s*\\.\\s*characters\\s*\\.\\s*' + role.source + '\\b', 'g')
				.replace(output, role.value);
		}
		output = new EReg('\\bSONG\\s*\\.\\s*characters\\b', 'g')
			.replace(output, '{player: SONG.player1, opponent: SONG.player2, girlfriend: SONG.gf}');
		// A donor Song variation nests its character ids under two difficulty
		// maps. Both native chart selections are already resolved in PlayState, so
		// lower only this explicit character object to the active SwagSong fields.
		var variationCharacters = '\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*currentSong\\s*\\.\\s*difficulties\\s*\\.\\s*get\\s*\\([^)]*\\)\\s*\\.\\s*get\\s*\\([^)]*\\)\\s*\\.\\s*characters\\b';
		output = new EReg(variationCharacters, 'g')
			.replace(output, '{player: SONG.player1, opponent: SONG.player2, girlfriend: SONG.gf}');
		// Keep direct role reads equivalent when a module does not first bind the
		// variation's character object to a local.
		for (role in [
			{source: 'player', value: 'SONG.player1'},
			{source: 'opponent', value: 'SONG.player2'},
			{source: 'girlfriend', value: 'SONG.gf'}
		]) {
			var variationRole = '\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*currentSong\\s*\\.\\s*difficulties\\s*\\.\\s*get\\s*\\([^)]*\\)\\s*\\.\\s*get\\s*\\([^)]*\\)\\s*\\.\\s*characters\\s*\\.\\s*' + role.source + '\\b';
			output = new EReg(variationRole, 'g').replace(output, role.value);
		}
		// V-Slice names the active pause bit isGamePaused. PlayState already seeds
		// the live native value as paused in every gameplay HScript interpreter,
		// so this explicit alias keeps the read rooted without exposing a donor
		// singleton or inventing a second mutable state flag.
		output = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*isGamePaused\\b', 'g')
			.replace(output, 'paused');
		// V-Slice exposes the active chart as currentChart. These fields are the
		// same live values already carried by SwagSong; lower only the direct
		// identity/role/visual fields whose semantics are preserved. Opaque
		// sticker metadata and the read-only vocal-offset view are also native
		// chart fields; noteStyle remains intentionally visible to the safety gate.
		// playbackRate is a
		// fixed-rate host alias exposed on PlayState.
		var chartOwner = '(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)';
		output = new EReg('\\b(PlayState\\s*\\.\\s*instance|currentPlayState|game)\\s*\\.\\s*currentChart\\s*\\.\\s*notes\\b', 'g')
			.replace(output, '$1.hxcCurrentChartNotes()');
		output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentChart\\s*\\.\\s*characters\\s*\\.\\s*player\\b', 'g')
			.replace(output, 'SONG.player1');
		output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentChart\\s*\\.\\s*characters\\s*\\.\\s*opponent\\b', 'g')
			.replace(output, 'SONG.player2');
		output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentChart\\s*\\.\\s*characters\\s*\\.\\s*girlfriend\\b', 'g')
			.replace(output, 'SONG.gf');
		// V-Slice scripts read the donor StageData through currentStage._data
		// (DDTO's extra-opponent setup wants _data.characters.dad.position and
		// .cameraOffsets). StageHelper's persistent slot info already carries
		// those numbers, so lower to the runtime snapshot instead of a null
		// chain that later arithmetic would dereference.
		output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentStage\\s*\\.\\s*_data\\s*\\.\\s*characters\\s*\\.\\s*([A-Za-z0-9_\\-]+)\\b', 'g')
			.replace(output, 'HxcCompatRuntime.stageCharacterData("$1")');
		output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentStage\\s*\\.\\s*_data\\b(?!\\s*\\.\\s*characters)', 'g')
			.replace(output, 'HxcCompatRuntime.stageDataSnapshot()');
		for (field in ['songName', 'songArtist', 'album', 'stage', 'bpm', 'needsVoices', 'scrollSpeed', 'speed',
			'isSpooky', 'uiType', 'cutsceneType', 'gf', 'player1', 'player2', 'offsets', 'stickerPack']) {
			var replacement = switch (field) {
				case 'songName': 'SONG.song';
				case 'scrollSpeed' | 'speed': 'SONG.speed';
				case 'gf': 'SONG.gf';
				case 'player1': 'SONG.player1';
				case 'player2': 'SONG.player2';
				default: 'SONG.' + field;
			};
			output = new EReg('\\b' + chartOwner + '\\s*\\.\\s*currentChart\\s*\\.\\s*' + field + '\\b', 'g')
				.replace(output, replacement);
		}
		// V-Slice exposes timing through a Conductor singleton. This engine already
		// seeds the live MusicBeatState step into every HScript interpreter, so
		// route reads to the native clock and route the donor update call through a
		// bounded numeric setter/no-op facade. Other Conductor members remain
		// diagnosed until they have a native equivalent.
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*currentBeat\\b', 'g')
			.replace(output, 'curBeat');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*stepLengthMs\\b', 'g')
			.replace(output, 'HxcCompatRuntime.conductorStepLengthMs');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*beatLengthMs\\b', 'g')
			.replace(output, 'HxcCompatRuntime.conductorBeatLengthMs');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*songPosition\\b', 'g')
			.replace(output, 'HxcCompatRuntime.conductorSongPosition');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*combinedOffset\\b', 'g')
			.replace(output, 'HxcCompatRuntime.conductorCombinedOffset');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*update\\s*\\(', 'g')
			.replace(output, 'HxcCompatRuntime.conductorUpdate(');
		output = new EReg('\\bConductor\\s*\\.\\s*instance\\s*\\.\\s*currentStep\\b', 'g')
			.replace(output, 'curStep');
		// The native state calls its active stage curStage.  Keep currentStageId
		// unchanged because PlayState exposes that donor read-only alias too.
		output = new EReg('\\bcurrentStage\\b', 'g').replace(output, 'curStage');
		// StageHelper keeps named props in its live elements map.  This preserves
		// the donor's lookup/set behavior without inventing a detached registry.
		output = new EReg('\\.namedProps\\b', 'g').replace(output, '.elements');
		// ScriptedMusicBeatState/SubState.init are manifest-scoped donor factories.
		// Literal names are safe to resolve through HxcStateFactory; dynamic names
		// remain visible to the diagnostic pass and are rejected at runtime.
		for (stateName in ['MainMenuState', 'StoryMenuState', 'FreeplayState', 'TitleState', 'CreditsState', 'SaveDataState']) {
			var statePattern = new EReg("\\bScriptedMusicBeatState\\s*\\.\\s*init\\s*\\(\\s*[\"']"
				+ stateName + "[\"']\\s*\\)", 'g');
			output = statePattern.replace(output, 'hxcStateInit("' + stateName + '")');
		}
		for (quote in ['"', "'"]) {
			var statePattern = new EReg('\\bScriptedMusicBeatState\\s*\\.\\s*init\\s*\\(\\s*'
				+ quote + '([A-Za-z_][A-Za-z0-9_]*)' + quote + '\\s*\\)', 'g');
			output = statePattern.replace(output, 'hxcStateInit("$1")');
			var subStatePattern = new EReg('\\bScriptedMusicBeatSubState\\s*\\.\\s*init\\s*\\(\\s*'
				+ quote + '([A-Za-z_][A-Za-z0-9_]*)' + quote + '\\s*\\)', 'g');
			output = subStatePattern.replace(output, 'hxcSubStateInit("$1")');
		}
		// A dynamic name is still safe when it enters the manifest-owned resolver:
		// HxcStateFactory scans only the caller's selected root and never calls
		// Type.resolveClass on the authored value. Keep property expressions intact
		// so menu state variables can be selected at runtime.
		var dynamicStatePattern = new EReg('\\bScriptedMusicBeatState\\s*\\.\\s*init\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\)', 'g');
		output = dynamicStatePattern.replace(output, 'hxcStateInit($1)');
		var dynamicSubStatePattern = new EReg('\\bScriptedMusicBeatSubState\\s*\\.\\s*init\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\)', 'g');
		output = dynamicSubStatePattern.replace(output, 'hxcSubStateInit($1)');
		// V-Slice's transition helper is a state-owned switch boundary. Route only
		// the engine-owned currentState spelling through the caller-root adapter;
		// arbitrary object methods remain ordinary HScript and are not reflected.
		output = new EReg('\\bcurrentState\\s*\\.\\s*startExitState\\s*\\(', 'g')
			.replace(output, 'hxcStartExitState(');
		output = lowerStateTransitionFactories(output);
		// Route both the active native state and an already-open imported substate
		// through the same root-checked adapter.  The longer chain must be lowered
		// first so it cannot leave a dangling `.subState` access behind.
		// Retain the active substate chain as an explicit host argument. This
		// deliberately covers only engine-owned state aliases, never arbitrary
		// object reflection.
		var subStateHost = new EReg('\\b(FlxG\\s*\\.\\s*state|currentState|hxcState|state)\\s*\\.\\s*subState\\s*\\.\\s*openSubState\\s*\\(', 'g');
		output = subStateHost.replace(output, 'hxcOpenSubStateOn($1.subState, ');
		var stateHost = new EReg('\\bFlxG\\s*\\.\\s*state\\s*\\.\\s*openSubState\\s*\\(', 'g');
		output = stateHost.replace(output, 'hxcOpenSubStateOn(FlxG.state, ');
		output = new EReg('\\bFlxG\\s*\\.\\s*switchState\\s*\\(', 'g')
			.replace(output, 'hxcSwitchState(');
		output = new EReg('\\bFlxG\\s*\\.\\s*resetState\\s*\\(\\s*\\)', 'g')
			.replace(output, 'hxcResetState()');
		return output;
	}

	/** Lower instance startsWith calls so nullable HXC strings safely return false. */
	static function lowerHxcStringStartsWith(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		var search = 0;
		var attempts = 0;
		var member = '.startsWith';
		while (attempts++ < 128 && search < output.length) {
			var memberIndex = findOutsideToken(output, member, search);
			if (memberIndex < 0)
				break;
			var methodEnd = memberIndex + member.length;
			if (methodEnd < output.length && isIdentifierPart(output.charAt(methodEnd))) {
				search = methodEnd;
				continue;
			}
			var open = skipWhitespaceForward(output, methodEnd);
			if (open >= output.length || output.charAt(open) != '(') {
				search = methodEnd;
				continue;
			}
			var close = matchingDelimiter(output, open, '(', ')');
			if (close < 0)
				break;
			var args = splitTopLevel(output.substr(open + 1, close - open - 1), ',');
			if (args.length != 1 || StringTools.trim(args[0]) == '') {
				search = close + 1;
				continue;
			}
			var receiverEnd = skipWhitespaceBackward(output, memberIndex - 1);
			var receiverStart = scanHxcMemberReceiverStart(output, receiverEnd);
			if (receiverStart < 0 || receiverStart > receiverEnd) {
				search = close + 1;
				continue;
			}
			var receiver = StringTools.trim(output.substr(receiverStart, receiverEnd - receiverStart + 1));
			var replacement = 'HxcCompatRuntime.stringStartsWith(' + receiver + ', '
				+ StringTools.trim(args[0]) + ')';
			output = output.substr(0, receiverStart) + replacement + output.substr(close + 1);
			search = receiverStart + replacement.length;
		}
		return output;
	}

	/** Include a preceding member call/index when the receiver ends in `.field`. */
	static function scanHxcMemberReceiverStart(source:String, end:Int):Int {
		var start = scanLeftOperandStart(source, end);
		if (start < 0)
			return -1;
		var attempts = 0;
		var separator = skipWhitespaceBackward(source, start - 1);
		while (separator >= 0 && source.charAt(separator) == '.' && attempts++ < 64) {
			var prefixEnd = skipWhitespaceBackward(source, separator - 1);
			var prefixStart = scanLeftOperandStart(source, prefixEnd);
			if (prefixStart < 0)
				break;
			start = prefixStart;
			separator = skipWhitespaceBackward(source, start - 1);
		}
		return start;
	}

	/**
		Lower the bounded V-Slice VideoCutscene facade without evaluating donor
		classes. The scanner keeps nested Calls/arrays/strings in the first argument
		intact and accepts only CutsceneType.ENDING as the ending hand-off marker.
	*/
	static function lowerVideoCutsceneCalls(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		var search = 0;
		var pattern = new EReg('\\bVideoCutscene\\s*\\.\\s*play\\s*\\(', 'g');
		var attempts = 0;
		while (attempts++ < 128 && search < output.length) {
			var remaining = output.substr(search);
			if (!pattern.match(remaining))
				break;
			var matched = pattern.matchedPos();
			var callStart = search + matched.pos;
			var open = output.indexOf('(', callStart);
			if (open < 0)
				break;
			var close = matchingDelimiter(output, open, '(', ')');
			if (close < 0)
				break;
			var parts = splitTopLevel(output.substr(open + 1, close - open - 1), ',');
			if (parts.length == 0 || StringTools.trim(parts[0]) == '') {
				search = close + 1;
				continue;
			}
			var ending = false;
			if (parts.length > 1) {
				var mode = StringTools.trim(parts[1]);
				ending = mode == 'true'
					|| new EReg('^CutsceneType\\s*\\.\\s*ENDING$', 'm').match(mode);
			}
			var replacement = 'HxcCompatRuntime.playVideoCutscene(PlayState.instance, '
				+ StringTools.trim(parts[0]) + ', ' + (ending ? 'true' : 'false') + ')';
			output = output.substr(0, callStart) + replacement + output.substr(close + 1);
			search = callStart + replacement.length;
		}
		return output;
	}

	/**
		Lower only an unqualified setIcon call.  A mounted CustomTitleBar module
		also declares a local `function setIcon(...)`; rewriting that declaration
		would shadow the seeded native bridge or emit a duplicate helper name.
	*/
	static function lowerBareSetIconCalls(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = new StringBuf();
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			if (source.substr(index, 7) == 'setIcon') {
				var callOpen = index + 7;
				while (callOpen < source.length && isWhitespace(source.charAt(callOpen)))
					callOpen++;
				if (callOpen < source.length && source.charAt(callOpen) == '(') {
					var before = skipWhitespaceBackward(source, index - 1);
					var qualified = before >= 0 && source.charAt(before) == '.';
					var previousWordEnd = before;
					while (previousWordEnd >= 0 && isIdentifierPart(source.charAt(previousWordEnd)))
						previousWordEnd--;
					var previousWord = previousWordEnd < before
						? source.substr(previousWordEnd + 1, before - previousWordEnd) : '';
					if (!qualified && previousWord != 'function') {
						output.add('hxcSetWindowIcon');
						output.add(source.substr(index + 7, callOpen - index - 7));
						index = callOpen;
						continue;
					}
				}
			}
			output.add(current);
			index++;
		}
		return output.toString();
	}

	/**
		Lower calls to the mounted fullscreen helper without rewriting its local
		function declaration. The helper body itself is replaced centrally by
		translateBody, while constructor/callback call sites use the same native
		adapter directly.
	*/
	static function lowerBareForceDisableFullscreenCalls(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = new StringBuf();
		var quote = '';
		var escaped = false;
		var index = 0;
		var name = 'forceDisableFullscreen';
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			if (source.substr(index, name.length) == name) {
				var callOpen = skipWhitespaceForward(source, index + name.length);
				var before = skipWhitespaceBackward(source, index - 1);
				var previousWordEnd = before;
				while (previousWordEnd >= 0 && isIdentifierPart(source.charAt(previousWordEnd)))
					previousWordEnd--;
				var previousWord = previousWordEnd < before
					? source.substr(previousWordEnd + 1, before - previousWordEnd) : '';
				if (callOpen < source.length && source.charAt(callOpen) == '('
					&& previousWord != 'function') {
					output.add('HxcCompatRuntime.disableFullscreen');
					output.add(source.substr(index + name.length, callOpen - index - name.length));
					index = callOpen;
					continue;
				}
			}
			output.add(current);
			index++;
		}
		return output.toString();
	}

	/**
		Lower the narrow state-transition closure form used by V-Slice donors.
		Only a zero-argument closure returning `new Class(...)` is eligible.  The
		class name is passed to HxcStateFactory, which allows native aliases and a
		unique HXC state under the caller's manifest root; all other closures remain
		ordinary HScript functions and are rejected by the state-switch boundary.
	*/
	static function lowerStateTransitionFactories(source:String):String {
		if (source == null || source.indexOf('->') < 0 && source.indexOf('function') < 0)
			return source == null ? '' : source;
		var output = source;
		var closureWithArgs = new EReg('\\(\\s*\\)\\s*->\\s*new\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*([^(){};\\n]*)\\s*\\)', 'g');
		output = closureWithArgs.replace(output, 'hxcStateFactory("$1", [$2])');
		var functionWithArgs = new EReg('function\\s*\\(\\s*\\)\\s*\\{\\s*return\\s+new\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*([^(){};\\n]*)\\s*\\)\\s*;?\\s*\\}', 'g');
		output = functionWithArgs.replace(output, 'hxcStateFactory("$1", [$2])');
		return output;
	}

	/**
		Lower only the two qualified menu classes with audited native equivalents.
		This is deliberately not a package resolver: every other qualified class
		name remains visible to HxcCompat's unsupported-state diagnostics.
	*/
	static function lowerQualifiedStateAliases(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		output = new EReg('\\bfunkin\\s*\\.\\s*ui\\s*\\.\\s*credits\\s*\\.\\s*CreditsState\\b', 'g')
			.replace(output, 'CreditsState');
		output = new EReg('\\bfunkin\\s*\\.\\s*ui\\s*\\.\\s*options\\s*\\.\\s*OptionsState\\b', 'g')
			.replace(output, 'SaveDataState');
		return output;
	}

	/** Report the exact allow-listed qualified names before lowering them. */
	static function collectQualifiedStateAliases(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		if (new EReg('\\bfunkin\\s*\\.\\s*ui\\s*\\.\\s*credits\\s*\\.\\s*CreditsState\\b', 'm').match(source))
			result.push('funkin.ui.credits.CreditsState -> CreditsState');
		if (new EReg('\\bfunkin\\s*\\.\\s*ui\\s*\\.\\s*options\\s*\\.\\s*OptionsState\\b', 'm').match(source))
			result.push('funkin.ui.options.OptionsState -> SaveDataState');
		return result;
	}

	/** Remove generic parameters from map constructors that HScript can still resolve. */
	static function lowerTypedMapSyntax(source:String):String {
		if (source == null || source.indexOf('<') < 0)
			return source == null ? '' : source;
		var output = source;
		var constructor = new EReg('\\bnew\\s+(Map|StringMap|IntMap|ObjectMap)\\s*<[^>\\n]+>\\s*\\(', 'g');
		output = constructor.replace(output, 'new $1(');
		// Return types, field declarations, and helper signatures can carry the
		// same generic map spelling even when no constructor appears.  HScript
		// still understands the unparameterized runtime class; removing only the
		// type arguments preserves the declaration for the later function/field
		// lowering pass without falsely retaining a typed-map diagnostic.
		var annotation = new EReg('\\b(Map|StringMap|IntMap|ObjectMap)\\s*<[^>\\n]+>', 'g');
		output = annotation.replace(output, '$1');
		return output;
	}

	/**
		Lower property-only optional chains to guarded ternaries.  The scanner
		intentionally leaves optional calls alone: evaluating a call twice or
		calling the result of a null guard changes donor semantics, so those
		bodies remain diagnosed instead of being guessed at.
	*/
	static function lowerOptionalChains(source:String):String {
		if (source == null || source.indexOf('?.') < 0)
			return source == null ? '' : source;
		// Optional writes cannot be represented by assigning to the guarded
		// ternary emitted below.  Normalize the common field-assignment form to a
		// lazy engine setter before handling reads/calls.
		source = lowerOptionalAssignments(source);
		// Handle the Haxe form `factory()?.field` before walking ordinary
		// identifier chains.  The expression before `?.` is a call, so it cannot
		// be represented by the simpler dotted-chain scanner below.
		source = lowerOptionalCallProperties(source);
		// Haxe permits an optional property read from a zero-or-more argument
		// method call (`stage.getDad()?.cameraFocusPoint`).  Keep the call lazy and
		// evaluate it exactly once through the native optional-field bridge.  A
		// duplicated call would be harmless for a getter in today's corpus but
		// would make this adapter unsafe for arbitrary imported stages/modules.
		var output = new StringBuf();
		var index = 0;
		var quote = '';
		var escaped = false;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			if (!isIdentifierStart(current)) {
				output.add(current);
				index++;
				continue;
			}

			var baseStart = index;
			var baseEnd = index + 1;
			while (baseEnd < source.length && isIdentifierPart(source.charAt(baseEnd)))
				baseEnd++;
			// Dotted identifiers and direct index reads are side-effect-free
			// receiver expressions.  The indexed form is common in V-Slice UI
			// scripts (`members[0]?.graphic`) and must remain part of the guarded
			// base instead of leaving `?.` behind for diagnostics.
			while (true) {
				if (baseEnd + 1 < source.length && source.charAt(baseEnd) == '.'
					&& isIdentifierStart(source.charAt(baseEnd + 1))) {
					baseEnd += 2;
					while (baseEnd < source.length && isIdentifierPart(source.charAt(baseEnd)))
						baseEnd++;
					continue;
				}
				if (baseEnd < source.length && source.charAt(baseEnd) == '[') {
					var indexClose = matchingDelimiter(source, baseEnd, '[', ']');
					if (indexClose >= 0) {
						baseEnd = indexClose + 1;
						continue;
					}
				}
				break;
			}
			var chainEnd = baseEnd;
			var fields:Array<String> = [];
			var sawOptional = false;
			while (true) {
				var optionalMember = chainEnd + 2 < source.length && source.substr(chainEnd, 2) == '?.';
				var regularMember = chainEnd + 1 < source.length && source.charAt(chainEnd) == '.';
				if (!optionalMember && !regularMember)
					break;
				var fieldStart = optionalMember ? chainEnd + 2 : chainEnd + 1;
				if (fieldStart >= source.length || !isIdentifierStart(source.charAt(fieldStart)))
					break;
				var fieldEnd = fieldStart + 1;
				while (fieldEnd < source.length && isIdentifierPart(source.charAt(fieldEnd)))
					fieldEnd++;
				if (optionalMember)
					sawOptional = true;
				if (sawOptional)
					fields.push(source.substr(fieldStart, fieldEnd - fieldStart));
				chainEnd = fieldEnd;
			}
			if (!sawOptional || fields.length == 0) {
				output.add(source.substr(index, baseEnd - index));
				index = baseEnd;
				continue;
			}
			var afterChain = skipWhitespaceForward(source, chainEnd);
			if (afterChain < source.length && source.charAt(afterChain) == '(') {
				// Leave the final optional member for lowerOptionalCalls.  Earlier
				// members are still lowered here so `a?.b?.call()` becomes a guarded
				// receiver before the call adapter sees it.
				if (fields.length <= 1) {
					output.add(source.substr(index, chainEnd - index));
					index = chainEnd;
					continue;
				}
				var guarded = source.substr(baseStart, baseEnd - baseStart);
				for (fieldIndex in 0...(fields.length - 1)) {
					var field = fields[fieldIndex];
					guarded = '(' + guarded + ' == null ? null : ' + guarded + '.' + field + ')';
				}
				output.add(guarded + '?.' + fields[fields.length - 1]);
				index = chainEnd;
				continue;
			}
			var expression = source.substr(baseStart, baseEnd - baseStart);
			for (field in fields)
				expression = '(' + expression + ' == null ? null : ' + expression + '.' + field + ')';
			output.add(expression);
			index = chainEnd;
		}
		// Prefix lowering above intentionally leaves a final optional call marker.
		// Run the call pass after the receiver is normalized so nested chains such
		// as `save?.modOptions?.get('key')` are handled without duplicating getters.
		var loweredCalls = lowerOptionalCalls(output.toString());
		// Optional-call lowering can expose a second call-expression receiver,
		// e.g. `factory()?.field` after `factory()` itself was adapted.  Finish
		// that property form through the same lazy provider bridge.
		return lowerOptionalCallProperties(loweredCalls);
	}

	/** Lower simple optional field writes to the native null-safe setter. */
	static function lowerOptionalAssignments(source:String):String {
		if (source == null || source.indexOf('?.') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 128) {
			var optional = findOutsideToken(output, '?.', search);
			if (optional < 0)
				break;
			var receiverEnd = skipWhitespaceBackward(output, optional - 1) + 1;
			var receiverStart = scanLeftOperandStart(output, receiverEnd - 1);
			if (receiverStart < 0 || receiverStart >= receiverEnd) {
				search = optional + 2;
				continue;
			}
			var receiver = StringTools.trim(output.substr(receiverStart, receiverEnd - receiverStart));
			if (receiver.indexOf('?.') >= 0 || receiver.indexOf('(') >= 0 || receiver.indexOf('[') >= 0) {
				search = optional + 2;
				continue;
			}
			var cursor = optional;
			var fields:Array<String> = [];
			var sawOptional = false;
			while (cursor < output.length) {
				var isOptional = output.substr(cursor, 2) == '?.';
				var isRegular = output.charAt(cursor) == '.';
				if (!isOptional && !isRegular)
					break;
				var fieldStart = cursor + (isOptional ? 2 : 1);
				if (fieldStart >= output.length || !isIdentifierStart(output.charAt(fieldStart)))
					break;
				var fieldEnd = fieldStart + 1;
				while (fieldEnd < output.length && isIdentifierPart(output.charAt(fieldEnd)))
					fieldEnd++;
				fields.push(output.substr(fieldStart, fieldEnd - fieldStart));
				if (isOptional)
					sawOptional = true;
				cursor = fieldEnd;
			}
			if (!sawOptional || fields.length == 0) {
				search = optional + 2;
				continue;
			}
			var operatorStart = skipWhitespaceForward(output, cursor);
			var assignmentOperator = '';
			for (candidate in ['+=', '-=', '*=', '/=', '=']) {
				if (output.substr(operatorStart, candidate.length) == candidate) {
					assignmentOperator = candidate;
					break;
				}
			}
			if (assignmentOperator == '' || (assignmentOperator == '=' && output.substr(operatorStart, 2) == '==')) {
				search = cursor;
				continue;
			}
			var valueStart = skipWhitespaceForward(output, operatorStart + assignmentOperator.length);
			var valueEnd = scanStatementValueEnd(output, valueStart);
			if (valueStart >= output.length || valueEnd <= valueStart) {
				search = cursor;
				continue;
			}
			var path:Array<String> = [];
			for (field in fields)
				path.push(quote(field));
			var replacement = 'hxcOptionalSet(' + receiver + ', [' + path.join(', ') + '], '
				+ StringTools.trim(output.substr(valueStart, valueEnd - valueStart)) + ', ' + quote(assignmentOperator) + ')';
			output = output.substr(0, receiverStart) + replacement + output.substr(valueEnd);
			search = receiverStart + replacement.length;
		}
		return output;
	}

	/** Find an assignment RHS up to the authored statement terminator. */
	static function scanStatementValueEnd(source:String, start:Int):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		var index = start;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (current == '(' || current == '[' || current == '{')
				depth++;
			else if (current == ')' || current == ']' || current == '}') {
				if (depth == 0)
					return index;
				depth--;
			} else if (depth == 0 && (current == ';' || current == '\n' || current == '\r'))
				return index;
			index++;
		}
		return source.length;
	}

	/** Lower an optional property whose receiver is a method-call expression. */
	static function lowerOptionalCallProperties(source:String):String {
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 128) {
			var optional = findOutsideToken(output, '?.', search);
			if (optional < 0)
				break;
			var fieldStart = optional + 2;
			if (fieldStart >= output.length || !isIdentifierStart(output.charAt(fieldStart))) {
				search = optional + 2;
				continue;
			}
			var fieldEnd = fieldStart + 1;
			while (fieldEnd < output.length && isIdentifierPart(output.charAt(fieldEnd)))
				fieldEnd++;
			var afterField = skipWhitespaceForward(output, fieldEnd);
			// This is an optional invocation, not a property read. Leave it for
			// lowerOptionalCalls, which preserves the receiver/method ABI.
			if (afterField < output.length && output.charAt(afterField) == '(') {
				search = fieldEnd;
				continue;
			}
			var close = skipWhitespaceBackward(output, optional - 1);
			if (close < 0 || output.charAt(close) != ')') {
				search = fieldEnd;
				continue;
			}
			var open = matchingDelimiterBackward(output, close, '(', ')');
			if (open < 0) {
				search = fieldEnd;
				continue;
			}
			var calleeEnd = skipWhitespaceBackward(output, open - 1) + 1;
			var calleeStart = calleeEnd - 1;
			while (calleeStart >= 0 && (isIdentifierPart(output.charAt(calleeStart))
				|| output.charAt(calleeStart) == '.' || isWhitespace(output.charAt(calleeStart))))
				calleeStart--;
			calleeStart++;
			var callee = StringTools.trim(output.substr(calleeStart, calleeEnd - calleeStart));
			if (callee == '' || callee.startsWith('.') || callee.indexOf('?.') >= 0
				|| callee.indexOf('(') >= 0 || (calleeStart > 0 && output.charAt(calleeStart - 1) == '?')) {
				search = fieldEnd;
				continue;
			}
			var args = output.substr(open + 1, close - open - 1);
			var replacement = 'hxcOptionalField(function() { return ' + callee + '(' + args
				+ '); }, ' + quote(output.substr(fieldStart, fieldEnd - fieldStart)) + ')';
			output = output.substr(0, calleeStart) + replacement + output.substr(fieldEnd);
			search = 0;
		}
		return output;
	}

	/**
		Lower Haxe's optional method invocation (`value?.method(args)`) through a
		single engine-owned call bridge.  The receiver is evaluated exactly once by
		HScript before entering hxcOptionalCall, including when it is a previous
		optional-call/property expression.  Unsupported receiver syntax is retained
		so diagnostics remain honest rather than silently dropping a call.
	*/
	static function lowerOptionalCalls(source:String):String {
		if (source == null || source.indexOf('?.') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 256) {
			var optional = findOutsideToken(output, '?.', search);
			if (optional < 0)
				break;
			var methodStart = optional + 2;
			if (methodStart >= output.length || !isIdentifierStart(output.charAt(methodStart))) {
				search = optional + 2;
				continue;
			}
			var methodEnd = methodStart + 1;
			while (methodEnd < output.length && isIdentifierPart(output.charAt(methodEnd)))
				methodEnd++;
			var open = skipWhitespaceForward(output, methodEnd);
			if (open >= output.length || output.charAt(open) != '(') {
				search = methodEnd;
				continue;
			}
			var close = matchingDelimiter(output, open, '(', ')');
			if (close < 0) {
				search = methodEnd;
				continue;
			}
			var receiverEnd = skipWhitespaceBackward(output, optional - 1) + 1;
			var receiverStart = scanLeftOperandStart(output, receiverEnd - 1);
			if (receiverStart < 0 || receiverStart >= receiverEnd) {
				search = methodEnd;
				continue;
			}
			var receiver = StringTools.trim(output.substr(receiverStart, receiverEnd - receiverStart));
			// A receiver containing another unlowered optional marker cannot be
			// safely sliced by the lexical scanner.  The prefix pass will expose a
			// guarded receiver on the next iteration.
			if (receiver == '' || receiver.indexOf('?.') >= 0) {
				search = methodEnd;
				continue;
			}
			var args = output.substr(open + 1, close - open - 1);
			var replacement = 'hxcOptionalCall(' + receiver + ', ' + quote(output.substr(methodStart, methodEnd - methodStart))
				+ ', [' + args + '])';
			output = output.substr(0, receiverStart) + replacement + output.substr(close + 1);
			search = receiverStart + replacement.length;
		}
		return output;
	}

	/** Lower simple, side-effect-free null-coalescing operands to HScript ternaries. */
	static function lowerNullCoalescing(source:String):String {
		if (source == null || source.indexOf('??') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 128) {
			var operatorIndex = findOutsideToken(output, '??', search);
			if (operatorIndex < 0)
				break;
			var leftEnd = skipWhitespaceBackward(output, operatorIndex - 1) + 1;
			var leftStart = scanLeftOperandStart(output, leftEnd - 1);
			var rightStart = skipWhitespaceForward(output, operatorIndex + 2);
			var rightEnd = scanRightOperandEnd(output, rightStart);
			if (leftStart < 0 || rightEnd <= rightStart) {
				// An unsupported complex operand should not prevent a later simple
				// coalesce expression from being adapted.
				search = operatorIndex + 2;
				continue;
			}
			var left = StringTools.trim(output.substr(leftStart, leftEnd - leftStart));
			var right = StringTools.trim(output.substr(rightStart, rightEnd - rightStart));
			if (left == '' || right == '') {
				search = operatorIndex + 2;
				continue;
			}
			// Use lazy providers so neither operand is evaluated twice and the right
			// side keeps Haxe's short-circuit semantics even when it is a call or a
			// nested optional expression.
			var replacement = 'hxcCoalesce(function() { return ' + left + '; }, function() { return '
				+ right + '; })';
			output = output.substr(0, leftStart) + replacement + output.substr(rightEnd);
			search = 0;
		}
		return output;
	}

	/**
		Lower the V-Slice/Haxe single-argument arrow form (`value -> expr`) to an
		ordinary HScript function.  `=>` is deliberately not rewritten because
		donor files use it for Haxe map literals, not lambdas; those need a map
		representation bridge and remain explicit diagnostics.
	*/
	static function lowerLambdaArrows(source:String):String {
		if (source == null || source.indexOf('->') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 128) {
			var arrow = findOutsideToken(output, '->', search);
			if (arrow < 0)
				break;
			var parameterEnd = skipWhitespaceBackward(output, arrow - 1) + 1;
			if (parameterEnd <= 0) {
				search = arrow + 2;
				continue;
			}
			var parameterStart = parameterEnd - 1;
			var parameterSource = '';
			if (output.charAt(parameterStart) == ')') {
				var open = matchingDelimiterBackward(output, parameterStart, '(', ')');
				if (open < 0) {
					search = arrow + 2;
					continue;
				}
				parameterStart = open;
				parameterSource = output.substr(open + 1, parameterEnd - open - 2);
			} else if (isIdentifierPart(output.charAt(parameterStart))) {
				while (parameterStart >= 0 && isIdentifierPart(output.charAt(parameterStart)))
					parameterStart--;
				parameterStart++;
				parameterSource = output.substr(parameterStart, parameterEnd - parameterStart);
			} else {
				search = arrow + 2;
				continue;
			}
			var names = parseArgumentNames(parameterSource);
			var expressionStart = skipWhitespaceForward(output, arrow + 2);
			var expressionEnd = expressionStart;
			var expression = '';
			if (expressionStart < output.length && output.charAt(expressionStart) == '{') {
				var bodyEnd = matchingDelimiter(output, expressionStart, '{', '}');
				if (bodyEnd < 0) {
					search = arrow + 2;
					continue;
				}
				expressionEnd = bodyEnd + 1;
				expression = output.substr(expressionStart, expressionEnd - expressionStart);
			} else {
				expressionEnd = scanLambdaExpressionEnd(output, expressionStart);
				if (expressionEnd <= expressionStart) {
					search = arrow + 2;
					continue;
				}
				expression = '{ return ' + StringTools.trim(output.substr(expressionStart,
					expressionEnd - expressionStart)) + '; }';
			}
			var replacement = 'function(' + names.join(', ') + ') ' + expression;
			output = output.substr(0, parameterStart) + replacement + output.substr(expressionEnd);
			search = 0;
		}
		return output;
	}

	/**
		Lower Haxe map literals (`[key => value, ...]`) to the engine-owned
		HxcDynamicMap container.  The pass is deliberately limited to a bracket
		expression whose top-level entries all contain `=>`; ordinary arrays and
		object literals are left untouched.  Nested map literals are lowered first,
		so authored values may themselves be maps without a chart-specific rewrite.
	*/
	static function lowerMapLiterals(source:String):String {
		if (source == null || source.indexOf('=>') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 256) {
			var open = findOutsideToken(output, '[', search);
			if (open < 0)
				break;
			var close = matchingDelimiter(output, open, '[', ']');
			if (close < 0)
				break;
			var content = output.substr(open + 1, close - open - 1);
			var loweredContent = lowerMapLiterals(content);
			var pairs = splitTopLevel(loweredContent, ',');
			var mapPairs:Array<String> = [];
			var isMap = false;
			var valid = true;
			for (pair in pairs) {
				var value = StringTools.trim(pair);
				if (value == '')
					continue;
				var arrow = findTopLevelToken(value, '=>');
				if (arrow < 0) {
					valid = false;
					break;
				}
				var key = StringTools.trim(value.substr(0, arrow));
				var mapped = StringTools.trim(value.substr(arrow + 2));
				if (key == '' || mapped == '') {
					valid = false;
					break;
				}
				mapped = deferStateFactoryMapValue(mapped);
				isMap = true;
				mapPairs.push('[' + key + ', ' + mapped + ']');
			}
			if (!isMap || !valid) {
				// An ordinary array/object may contain a map literal several levels
				// down (event schemas commonly use `return [{keys: [...]}]`). Keep
				// walking inside the bracket instead of skipping the nested map.
				search = open + 1;
				continue;
			}
			var replacement = 'hxcMap([' + mapPairs.join(', ') + '])';
			output = output.substr(0, open) + replacement + output.substr(close + 1);
			search = open + replacement.length;
		}
		return output;
	}

	/** Defer state construction stored in a literal HXC map until its value is
	 * read. Module initialization often carries transition targets which are
	 * never used in Freeplay; eagerly resolving them walks and analyzes the
	 * entire manifest-owned HXC tree before the menu can open. HxcDynamicMap
	 * resolves this opaque value once when get() is called. */
	static function deferStateFactoryMapValue(value:String):String {
		if (value == null)
			return '';
		var trimmed = StringTools.trim(value);
		if (!trimmed.startsWith('hxcStateFactory('))
			return value;
		var open = trimmed.indexOf('(');
		var close = matchingDelimiter(trimmed, open, '(', ')');
		if (open < 0 || close != trimmed.length - 1)
			return value;
		return 'hxcDeferredStateFactory(' + trimmed.substr(open + 1, close - open - 1) + ')';
	}

	/** Find a token only when it is outside nested delimiters and quoted text. */
	static function findTopLevelToken(source:String, token:String):Int {
		if (source == null || token == null || token == '')
			return -1;
		var quote = '';
		var escaped = false;
		var depth = 0;
		var index = 0;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (current == '(' || current == '[' || current == '{') {
				depth++;
				index++;
				continue;
			}
			if (current == ')' || current == ']' || current == '}') {
				if (depth > 0)
					depth--;
				index++;
				continue;
			}
			if (depth == 0 && source.substr(index, token.length) == token)
				return index;
			index++;
		}
		return -1;
	}

	static function findOutsideToken(source:String, token:String, start:Int):Int {
		if (source == null || token == null || token == '')
			return -1;
		var quote = '';
		var escaped = false;
		var index = start < 0 ? 0 : start;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (source.substr(index, token.length) == token)
				return index;
			index++;
		}
		return -1;
	}

	static function scanLeftOperandStart(source:String, end:Int):Int {
		if (source == null || end < 0 || end >= source.length)
			return -1;
		var current = source.charAt(end);
		if (current == ')' || current == ']' || current == '}') {
			var open = matchingDelimiterBackward(source, end,
				current == ')' ? '(' : current == ']' ? '[' : '{', current);
			if (open < 0)
				return -1;
			var before = skipWhitespaceBackward(source, open - 1);
			if (before >= 0 && (isIdentifierPart(source.charAt(before)) || source.charAt(before) == '.')) {
				var target = before;
				while (target >= 0 && (isIdentifierPart(source.charAt(target)) || source.charAt(target) == '.'))
					target--;
				return target + 1;
			}
			return open;
		}
		if (current == '"' || current == "'")
			return scanQuoteStart(source, end, current);
		if (!isIdentifierPart(current))
			return -1;
		var start = end;
		while (start >= 0 && (isIdentifierPart(source.charAt(start)) || source.charAt(start) == '.'))
			start--;
		return start + 1;
	}

	static function scanRightOperandEnd(source:String, start:Int):Int {
		if (source == null || start < 0 || start >= source.length)
			return -1;
		var current = source.charAt(start);
		if (current == '"' || current == "'")
			return scanQuoteEnd(source, start);
		if (current == '(' || current == '[' || current == '{') {
			var close = current == '(' ? ')' : current == '[' ? ']' : '}';
			var end = matchingDelimiter(source, start, current, close);
			return end < 0 ? -1 : end + 1;
		}
		var end = start;
		if (current == '-' || current == '+')
			end++;
		while (end < source.length && (isIdentifierPart(source.charAt(end)) || source.charAt(end) == '.'))
			end++;
		if (end == start || (end == start + 1 && (current == '-' || current == '+')))
			return -1;
		var callStart = skipWhitespaceForward(source, end);
		if (callStart < source.length && source.charAt(callStart) == '(') {
			var callEnd = matchingDelimiter(source, callStart, '(', ')');
			if (callEnd >= 0)
				return callEnd + 1;
		}
		return end;
	}

	static function scanLambdaExpressionEnd(source:String, start:Int):Int {
		if (source == null || start < 0 || start >= source.length)
			return -1;
		var depth = 0;
		var quote = '';
		var escaped = false;
		var index = start;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (current == '(' || current == '[' || current == '{')
				depth++;
			else if (current == ')' || current == ']' || current == '}') {
				if (depth == 0)
					return index;
				depth--;
			} else if (depth == 0 && (current == ',' || current == ';'))
				return index;
			index++;
		}
		return source.length;
	}

	static function matchingDelimiterBackward(source:String, closeIndex:Int, open:String, close:String):Int {
		if (source == null || closeIndex < 0 || closeIndex >= source.length)
			return -1;
		var stack:Array<Int> = [];
		var quote = '';
		var escaped = false;
		for (index in 0...closeIndex + 1) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == open)
				stack.push(index);
			else if (current == close) {
				if (stack.length == 0)
					continue;
				var found = stack.pop();
				if (index == closeIndex)
					return found;
			}
		}
		return -1;
	}

	static function scanQuoteStart(source:String, end:Int, quote:String):Int {
		var index = end - 1;
		while (index >= 0) {
			if (source.charAt(index) == quote && (index == 0 || source.charAt(index - 1) != '\\\\'))
				return index;
			index--;
		}
		return -1;
	}

	static function scanQuoteEnd(source:String, start:Int):Int {
		var quote = source.charAt(start);
		var escaped = false;
		var index = start + 1;
		while (index < source.length) {
			var current = source.charAt(index);
			if (escaped)
				escaped = false;
			else if (current == '\\\\')
				escaped = true;
			else if (current == quote)
				return index + 1;
			index++;
		}
		return source.length;
	}

	static function skipWhitespaceForward(source:String, index:Int):Int {
		var output = index;
		while (source != null && output < source.length && isWhitespace(source.charAt(output)))
			output++;
		return output;
	}

	static function skipWhitespaceBackward(source:String, index:Int):Int {
		var output = index;
		while (source != null && output >= 0 && isWhitespace(source.charAt(output)))
			output--;
		return output;
	}

	/** HScript function expressions accept names but not Haxe parameter annotations. */
	static function lowerFunctionArgumentTypes(source:String):String {
		if (source == null || source.indexOf('function') < 0)
			return source == null ? '' : source;
		var output = source;
		var search = 0;
		var attempts = 0;
		while (attempts++ < 128) {
			var functionStart = findOutsideToken(output, 'function', search);
			if (functionStart < 0)
				break;
			if (functionStart > 0 && isIdentifierPart(output.charAt(functionStart - 1))) {
				search = functionStart + 8;
				continue;
			}
			var open = skipWhitespaceForward(output, functionStart + 8);
			if (open >= output.length || output.charAt(open) != '(') {
				search = functionStart + 8;
				continue;
			}
			var close = matchingDelimiter(output, open, '(', ')');
			if (close < 0)
				break;
			var names = parseArgumentNames(output.substr(open + 1, close - open - 1));
			var replacement = 'function(' + names.join(', ') + ')';
			var suffixStart = close + 1;
			var annotation = skipWhitespaceForward(output, suffixStart);
			if (annotation < output.length && output.charAt(annotation) == ':') {
				suffixStart = annotation + 1;
				while (suffixStart < output.length && output.charAt(suffixStart) != '{'
					&& output.charAt(suffixStart) != ';' && output.charAt(suffixStart) != ',')
					suffixStart++;
			}
			output = output.substr(0, functionStart) + replacement + output.substr(suffixStart);
			search = functionStart + replacement.length;
		}
		return output;
	}

	/** Haxe's `value is Type` check maps directly to the engine's HScript helper. */
	static function lowerTypeChecks(source:String):String {
		if (source == null || source.indexOf('is') < 0)
			return source == null ? '' : source;
		var output = source;
		var attempts = 0;
		var search = 0;
		while (attempts++ < 128) {
			var typeOperator = findOutsideToken(output, 'is', search);
			if (typeOperator < 0)
				break;
			var before = typeOperator - 1;
			var after = typeOperator + 2;
			if ((before >= 0 && isIdentifierPart(output.charAt(before)))
				|| (after < output.length && isIdentifierPart(output.charAt(after)))) {
				search = typeOperator + 2;
				continue;
			}
			var leftEnd = skipWhitespaceBackward(output, before) + 1;
			var leftStart = scanLeftOperandStart(output, leftEnd - 1);
			var rightStart = skipWhitespaceForward(output, after);
			var rightEnd = rightStart;
			while (rightEnd < output.length && isIdentifierPart(output.charAt(rightEnd)))
				rightEnd++;
			if (leftStart < 0 || rightEnd <= rightStart) {
				search = typeOperator + 2;
				continue;
			}
			var left = StringTools.trim(output.substr(leftStart, leftEnd - leftStart));
			var typeName = output.substr(rightStart, rightEnd - rightStart);
			output = output.substr(0, leftStart) + 'Std.isOfType(' + left + ', ' + typeName + ')'
				+ output.substr(rightEnd);
			search = 0;
		}
		return output;
	}

	static function unsupportedConstructs(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null)
			return result;
		if (findOutsideToken(source, '?.', 0) >= 0)
			result.push('optional-chaining (?.)');
		if (findOutsideToken(source, '??', 0) >= 0)
			result.push('null-coalescing (??)');
		if (findOutsideToken(source, '=>', 0) >= 0 || findOutsideToken(source, '->', 0) >= 0)
			result.push('lambda expressions');
		if (new EReg('\\b(?:Map|StringMap|IntMap|ObjectMap)\\s*<', '').match(source))
			result.push('typed maps');
		if (new EReg('\\b(?:@:|abstract\\s+)', '').match(source))
			result.push('Haxe metadata/abstracts');
		return result;
	}

	static function generateHscript(result:HxcCompatResult):String {
		if (result == null)
			return '';
		var lines:Array<String> = ['// HXC compatibility adapter; donor source is never executed directly.'];
		if (result.menuSpec != null && result.kind == 'state') {
			// A complete imported menu state is materialized by HxcStateFactory. Keep
			// the generated representation useful for audit/tests while ensuring a
			// direct interpreter path can only call the native host boundary.
			lines.push('function start() {');
			lines.push('\tHxcCompatRuntime.mountMainMenuOverlay(currentState, '
				+ menuSpecLiteral(result.menuSpec) + ', hxcAssetRoot);');
			lines.push('}');
			lines.push('function destroy(?event) {');
			lines.push('\tHxcCompatRuntime.clearMainMenuOverlay(currentState);');
			lines.push('}');
			return lines.join('\n');
		}
		if (result.videoModuleAdapter == true) {
			lines.push('var __hxcVideoModule = HxcCompatRuntime.createVideoModule(PlayState.instance, hxcAssetRoot);');
			lines.push('function getDefaultConfig() { return HxcCompatRuntime.videoModuleDefaults(PlayState.instance, __hxcVideoModule); }');
			lines.push('function createVideo(filePath, ?config) { return HxcCompatRuntime.videoModuleCreateVideo(PlayState.instance, __hxcVideoModule, filePath, config); }');
			lines.push('function checkResync(video, ?instant, ?resume) {');
			lines.push('\tif (instant == null) instant = false;');
			lines.push('\tif (resume == null) resume = true;');
			lines.push('\tHxcCompatRuntime.videoModuleCheckResync(PlayState.instance, __hxcVideoModule, video, instant, resume);');
			lines.push('}');
			lines.push('function clearVideoSprites() { HxcCompatRuntime.videoModuleClear(PlayState.instance, __hxcVideoModule); }');
			for (callback in result.callbackAdapters) {
				if (callback == null || !callback.safe)
					continue;
				var arg = callback.arguments != null && callback.arguments.length > 0 ? callback.arguments[0] : '';
				lines.push('function ' + callback.canonicalName + '(' + arg + ') {');
				lines.push('\tHxcCompatRuntime.' + videoModuleHostCallback(callback.canonicalName)
					+ '(PlayState.instance, __hxcVideoModule, ' + arg + ');');
				lines.push('}');
			}
			lines.push('function destroy(?event) { HxcCompatRuntime.videoModuleDestroy(PlayState.instance, __hxcVideoModule); }');
			return lines.join('\n');
		}
		if (result.storyMenuSpec != null) {
			var storySpec = result.storyMenuSpec;
			lines.push('var ' + storySpec.characterHelperField + ';');
			lines.push(HxcStoryMenuSpec.helperHscript(storySpec));
			return lines.join('\n');
		}
		// Keep the translated Save/Preferences view available before any carried
		// state initializers, but do not make ordinary HXC adapters depend on the
		// store class. The namespace is donor-root scoped so related scripts share
		// authored options while unrelated imports stay isolated.
		if (needsHxcStore(result))
			lines.push('var __hxcStore = HxcCompatRuntime.openStore(' + quote(runtimeNamespace(result.path)) + ');');
		var shaderDescriptor:Dynamic = result.runtimeShaderDescriptor;
		var shaderDescriptors:Array<Dynamic> = result.runtimeShaderDescriptors == null
			? [] : result.runtimeShaderDescriptors;
		var multiShaderHandles = shaderDescriptors.length > 1;
		if (multiShaderHandles)
			lines.push('var __hxcShaderHandles = {};');
		var shaderFieldValue:Dynamic = shaderDescriptor == null ? null : Reflect.field(shaderDescriptor, 'shaderField');
		var shaderFilterFieldValue:Dynamic = shaderDescriptor == null ? null : Reflect.field(shaderDescriptor, 'filterField');
		var shaderFieldName = shaderFieldValue == null ? '' : Std.string(shaderFieldValue);
		var shaderFilterFieldName = shaderFilterFieldValue == null ? '' : Std.string(shaderFilterFieldValue);
		var shaderGate:Dynamic = shaderDescriptor == null ? null : Reflect.field(shaderDescriptor, 'gate');
		var stageShaderCountdownCovered = result.kind == 'stage' && shaderDescriptor != null
			&& Reflect.field(shaderDescriptor, 'stageCountdownCovered') == true;
		var hasShaderHandle = !multiShaderHandles && shaderDescriptor != null && shaderFieldName != ''
			&& shaderGate == null;
		// Countdown shaders are created by their authored countdown callback.
		// Other stage shaders still need a handle before song/event callbacks
		// bind filters, even when no countdown callback owns construction.
		var lazyStageShaderHandle = hasShaderHandle && result.kind == 'stage'
			&& stageShaderCountdownCovered;
		var initializedFields:Map<String, Bool> = new Map<String, Bool>();
		if (result.stateInitializers != null)
			for (initializer in result.stateInitializers) {
				if (initializer == null || initializer.name == null || initializer.name == '')
					continue;
				lines.push('var ' + initializer.name + ' = ' + initializer.value + ';');
				initializedFields.set(initializer.name, true);
			}
		if (hasShaderHandle) {
			// Keep the actual FlxRuntimeShader/ShaderFilter graph behind an opaque
			// native-owned handle.  The donor field names remain aliases only so
			// translated callbacks can retain their authored shape in diagnostics.
			if (lazyStageShaderHandle) {
				// Stage constructors do not attach the donor filter until their
				// countdown hook.  Defer native construction so a stage's shader is
				// created at the same lifecycle point as its uniforms and filter write.
				lines.push('var __hxcShaderHandle = null;');
				lines.push('var ' + shaderFieldName + ';');
			} else {
				lines.push('var __hxcShaderHandle = HxcCompatRuntime.createShaderHandle(PlayState.instance, '
					+ shaderDescriptorLiteral(shaderDescriptor) + ', hxcAssetRoot);');
				lines.push('var ' + shaderFieldName + ' = __hxcShaderHandle;');
			}
			initializedFields.set(shaderFieldName, true);
			if (shaderFilterFieldName != '') {
				if (lazyStageShaderHandle)
					lines.push('var ' + shaderFilterFieldName + ';');
				else
					lines.push('var ' + shaderFilterFieldName + ' = __hxcShaderHandle;');
				initializedFields.set(shaderFilterFieldName, true);
			}
		}
		for (field in result.stateFields)
			if (field != null && !initializedFields.exists(field)
				&& !(hasShaderHandle && (field == shaderFieldName || field == shaderFilterFieldName)))
				// State field names are already identifier-validated by the scanner;
				// preserve case because translated callback bodies reference the
				// authored spelling verbatim.
				lines.push('var ' + field + ';');
		if (result.noteTextSpec != null)
			lines.push('var __hxcNoteTextHandle = null;');
		if (result.constructorStatements != null)
			for (statement in result.constructorStatements)
				if (statement != null && StringTools.trim(statement) != '')
					lines.push(StringTools.trim(statement));
		if (result.eventAdapters.length > 0) {
			lines.push('function routeHxcEvent(name, v1, v2, v3) {');
			for (adapter in result.eventAdapters) {
				lines.push('\tif (name == ' + quote(adapter.sourceName) + ') return {name: '
					+ quote(adapter.canonicalName) + ', v1: v1, v2: v2, v3: v3};');
			}
			lines.push('\treturn null;');
			lines.push('}');
		}
		var emitted:Map<String, Bool> = new Map<String, Bool>();
		var emittedCharacterAdd = false;
		var generatedAdapters:Array<HxcCompatCallbackAdapter> = [];
		if (result.helperAdapters != null)
			for (helper in result.helperAdapters)
				generatedAdapters.push(helper);
		if (result.callbackAdapters != null)
			for (callback in result.callbackAdapters)
				generatedAdapters.push(callback);
		// Shader setup is emitted as a synthetic lifecycle hook.  This lets the
		// bounded native filter survive even when the surrounding donor callback is
		// unsafe, while retaining that callback's diagnostics and never marking it
		// safe merely because a shader fragment was recognized.
		if (shaderDescriptor != null && !multiShaderHandles) {
			var shaderCameras:Dynamic = Reflect.field(shaderDescriptor, 'cameras');
			var shaderCountdownName = lifecycleCallback('onCountdownStart');
			if (shaderGate != null) {
				lines.push('function ' + shaderCountdownName + '(event) {');
				lines.push('\tHxcCompatRuntime.applyShaderDescriptor(PlayState.instance, '
					+ shaderDescriptorLiteral(shaderDescriptor) + ', __hxcStore, hxcAssetRoot);');
				lines.push('}');
				emitted.set(shaderCountdownName, true);
			} else if (hasShaderHandle && !lazyStageShaderHandle
				&& shaderCameras != null && Std.isOfType(shaderCameras, Array)) {
				lines.push('function ' + shaderCountdownName + '(event) {');
				for (camera in (cast shaderCameras:Array<Dynamic>))
					lines.push('\tHxcCompatRuntime.bindShaderFilter(PlayState.instance, __hxcShaderHandle, '
						+ quote(camera == null ? '' : Std.string(camera)) + ', '
						+ (Reflect.field(shaderDescriptor, 'initialEnabled') == true ? 'true' : 'false') + ');');
				lines.push('}');
				emitted.set(shaderCountdownName, true);
			}
			var pulseHelper:Dynamic = Reflect.field(shaderDescriptor, 'pulseHelper');
			if (hasShaderHandle && pulseHelper != null && StringTools.trim(Std.string(pulseHelper)) != '') {
				var pulseSource = shaderPulseHelperSource(shaderDescriptor, '__hxcShaderHandle');
				if (pulseSource != '')
					lines.push(pulseSource);
				emitted.set(Std.string(pulseHelper), true);
			}
		}
		if (multiShaderHandles)
			for (descriptor in shaderDescriptors) {
				var pulseHelper:Dynamic = descriptor == null ? null : Reflect.field(descriptor, 'pulseHelper');
				if (pulseHelper == null || StringTools.trim(Std.string(pulseHelper)) == ''
					|| emitted.exists(Std.string(pulseHelper)))
					continue;
				var pulseSource = shaderPulseHelperSource(descriptor, shaderOperationHandle(descriptor, true));
				if (pulseSource != '') {
					lines.push(pulseSource);
					emitted.set(Std.string(pulseHelper), true);
				}
			}
		var emittedCharacterInfo = false;
		var emittedStageConstructor = false;
		for (callback in generatedAdapters) {
			// A callback containing donor-only syntax is still reported in the
			// analysis result, but must not be emitted into a runtime HScript file:
			// one unsupported optional-chain or lambda must never prevent all other
			// lifecycle hooks from loading.
			if (callback == null || callback.canonicalName == ''
				|| emitted.exists(callback.canonicalName))
				continue;
			// A wrapper constructor is safe to replay even when its inherited onAdd
			// body retains donor game-over state. Emit the native definition bridge
			// alone in that case, while leaving the inherited callback diagnosed.
			if (!callback.safe && callback.canonicalName == 'onAdd'
				&& result.characterConstructor != null && result.characterConstructor != '') {
				emitted.set('onAdd', true);
				emittedCharacterAdd = true;
				lines.push('function onAdd(event) {');
				lines.push('\tHxcCompatRuntime.applyCharacterConstructor(hxcCharacter(), '
					+ quote(result.characterConstructor) + ');');
				lines.push('}');
				continue;
			}
			if (!callback.safe)
				continue;
			emitted.set(callback.canonicalName, true);
			if (callback.canonicalName == 'onAdd')
				emittedCharacterAdd = true;
			var args = callback.arguments == null ? [] : callback.arguments.copy();
			var safeArgs:Array<String> = [];
			var defaultGuards:Array<String> = [];
			for (arg in args) {
				if (!isIdentifier(arg))
					continue;
				var info = argumentInfoByName(callback.argumentInfos, arg);
				// hscript fills omitted optional parameters with null; donor
				// `?name`/`name = default` parameters must not stay required or
				// every native lifecycle dispatch with fewer arguments throws.
				if (info != null && info.optional) {
					safeArgs.push('?' + arg);
					if (info.defaultValue != '')
						defaultGuards.push('if (' + arg + ' == null) ' + arg + ' = ' + info.defaultValue + ';');
				} else
					safeArgs.push(arg);
			}
			if (callback.canonicalName == 'destroy' && safeArgs.length == 0)
				safeArgs.push('?event');
			lines.push('function ' + callback.canonicalName + '(' + safeArgs.join(', ') + ') {');
			for (guard in defaultGuards)
				lines.push('\t' + guard);
			var body = StringTools.trim(callback.body);
			if (lazyStageShaderHandle && callback.sourceName != null
				&& callback.sourceName.toLowerCase() == 'oncountdownstart') {
				body = 'if (__hxcShaderHandle == null) {\n'
					+ '\t__hxcShaderHandle = HxcCompatRuntime.createShaderHandle(PlayState.instance, '
					+ shaderDescriptorLiteral(shaderDescriptor) + ', hxcAssetRoot);\n'
					+ '\t' + shaderFieldName + ' = __hxcShaderHandle;\n'
					+ (shaderFilterFieldName == '' ? ''
						: '\t' + shaderFilterFieldName + ' = __hxcShaderHandle;\n')
					+ '}\n' + body;
			}
			if (result.kind == 'stage' && callback.canonicalName == 'start'
				&& result.stageConstructorBody != null
				&& StringTools.trim(result.stageConstructorBody) != '') {
				body = StringTools.trim(result.stageConstructorBody)
					+ (body == '' ? '' : '\n' + body);
				emittedStageConstructor = true;
			}
			if (callback.canonicalName == 'onAdd' && result.characterDefinition != null) {
				body = 'HxcCompatRuntime.applyCharacterInfo(hxcCharacter(), '
					+ characterDefinitionLiteral(result.characterDefinition)
					+ ', hxcAssetRoot);\n' + body;
				emittedCharacterInfo = true;
			}
			if (callback.canonicalName == 'onAdd'
				&& result.characterConstructor != null && result.characterConstructor != '')
				body = 'HxcCompatRuntime.applyCharacterConstructor(hxcCharacter(), '
					+ quote(result.characterConstructor) + ');\n' + body;
			if (body != '')
				for (line in body.split('\n'))
					lines.push('\t' + line);
			lines.push('}');
		}
		if (result.kind == 'stage' && !emittedStageConstructor
			&& result.stageConstructorBody != null
			&& StringTools.trim(result.stageConstructorBody) != '') {
			lines.push('function start() {');
			for (line in StringTools.trim(result.stageConstructorBody).split('\n'))
				lines.push('\t' + line);
			lines.push('}');
		}
		if (result.kind == 'character' && result.characterConstructor != null
			&& result.characterConstructor != '' && !emittedCharacterAdd) {
			lines.push('function onAdd(event) {');
			if (result.characterDefinition != null) {
				lines.push('\tHxcCompatRuntime.applyCharacterInfo(hxcCharacter(), '
					+ characterDefinitionLiteral(result.characterDefinition)
					+ ', hxcAssetRoot);');
				emittedCharacterInfo = true;
			}
			lines.push('\tHxcCompatRuntime.applyCharacterConstructor(hxcCharacter(), '
				+ quote(result.characterConstructor) + ');');
			lines.push('}');
		}
		if (result.kind == 'character' && result.characterDefinition != null && !emittedCharacterInfo) {
			lines.push('function onAdd(event) {');
			lines.push('\tHxcCompatRuntime.applyCharacterInfo(hxcCharacter(), '
				+ characterDefinitionLiteral(result.characterDefinition)
				+ ', hxcAssetRoot);');
			lines.push('}');
		}
		// Custom V-Slice SongEvent subclasses own one authored event kind and a
		// handleEvent body of ordinary engine calls. Emit a self-filtering
		// songEvent adapter: the runtime broadcasts every chart event to every
		// script scope, and this adapter runs the donor body only for its own
		// kind, with the native payload bound as `data` exactly as the donor
		// signature names it.
		if (result.kind == 'song-event' && result.customEventKind != null
			&& result.customEventKind != '' && result.customEventBody != null
			&& StringTools.trim(result.customEventBody) != '') {
			var translated = translateBody(result.customEventBody, 'handleEvent', ['data']);
			if (StringTools.trim(translated) != '') {
				lines.push('var hxcEventKind = ' + quote(result.customEventKind) + ';');
				lines.push('function songEvent(event) {');
				lines.push('\tif (event == null || event.eventKind != hxcEventKind) return;');
				lines.push('\tvar data = event;');
				for (line in translated.split('\n'))
					lines.push('\t' + line);
				lines.push('}');
			}
		}
		// A recognized HXC class can validly expose no PlayState lifecycle hooks
		// (for example a Song override used only by its freeplay metadata). Keep the
		// comment-only module parseable so it loads as an empty scope instead of
		// making PlayState treat the declaration as a missing HScript/Lua module.
		if (lines.length == 1)
			return lines[0];
		return lowerZIndexAccess(lines.join('\n'));
	}

	static function videoModuleHostCallback(canonicalName:String):String {
		return switch (canonicalName) {
			case 'update': 'videoModuleUpdate';
			case 'focusGained': 'videoModuleFocusGained';
			case 'stepHit': 'videoModuleStepHit';
			case 'pause': 'videoModulePause';
			case 'resume': 'videoModuleResume';
			case 'songRetry': 'videoModuleSongRetry';
			case 'gameOver': 'videoModuleGameOver';
			case 'songEnd': 'videoModuleSongEnd';
			case 'countdownStart': 'videoModuleCountdownStart';
			default: '';
		}
	}

	/**
		V-Slice exposes zIndex on every FunkinSprite/FlxText.  This fork keeps the
		field out of native Flixel types, so lower reads and writes to the shared
		engine adapter at the final HScript boundary.  Running this pass after all
		callback/stage-constructor emission also covers generated anonymous sort
		callbacks and state initializers, not just ordinary translated methods.
	*/
	static function lowerZIndexAccess(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = source;
		// Keep call arguments free of nested delimiters here.  A permissive
		// `[^;{}\\n]*` call matcher can consume across a ternary and rewrite
		// `getDad() != null ? getDad().zIndex` as one malformed receiver.
		var receiver = '[A-Za-z_][A-Za-z0-9_]*(?:\\s*\\([^(){};\\n]*\\))?(?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*'
			+ '(?:\\s*\\([^(){};\\n]*\\))?)*';
		var assignment = new EReg('\\b(' + receiver + ')'
			+ '\\s*\\.\\s*zIndex\\s*(=|\\+=|-=|\\*=|/=)\\s*([^;\\n]+)', 'g');
		var attempts = 0;
		while (attempts++ < 256 && assignment.match(output)) {
			var matched = assignment.matchedPos();
			var target = StringTools.trim(assignment.matched(1));
			var assignmentOperator = StringTools.trim(assignment.matched(2));
			var value = StringTools.trim(assignment.matched(3));
			var replacement = 'HxcCompatRuntime.setZIndex(' + target + ', ' + value + ', '
				+ quote(assignmentOperator) + ')';
			output = output.substr(0, matched.pos) + replacement
				+ output.substr(matched.pos + matched.len);
		}
		var read = new EReg('\\b(' + receiver + ')'
			+ '\\s*\\.\\s*zIndex\\b', 'g');
		return read.replace(output, 'HxcCompatRuntime.getZIndex($1)');
	}

	/** Emit only literal FPS Plus character metadata into generated HScript. */
	static function characterDefinitionLiteral(definition:Dynamic):String {
		if (definition == null)
			return 'null';
		var output = '{name: ' + quote(Std.string(Reflect.field(definition, 'name')))
			+ ', spritePath: ' + quote(Std.string(Reflect.field(definition, 'spritePath')))
			+ ', frameLoadType: ' + quote(Std.string(Reflect.field(definition, 'frameLoadType')))
			+ ', iconName: ' + quote(Std.string(Reflect.field(definition, 'iconName')));
		var focus:Dynamic = Reflect.field(definition, 'focusOffset');
		output += ', focusOffset: ' + numberArrayLiteral(focus);
		var animations:Dynamic = Reflect.field(definition, 'animations');
		output += ', animations: [';
		if (animations != null && Std.isOfType(animations, Array)) {
			var first = true;
			for (animation in (cast animations:Array<Dynamic>)) {
				if (animation == null)
					continue;
				if (!first)
					output += ', ';
				first = false;
				output += '{name: ' + quote(Std.string(Reflect.field(animation, 'name')))
					+ ', kind: ' + quote(Std.string(Reflect.field(animation, 'kind')))
					+ ', prefix: ' + quote(Std.string(Reflect.field(animation, 'prefix')))
					+ ', indicesPrefix: ' + quote(Std.string(Reflect.field(animation, 'indicesPrefix')))
					+ ', fps: ' + numberLiteral(Reflect.field(animation, 'fps'), 24)
					+ ', loop: ' + (Reflect.field(animation, 'loop') == true ? 'true' : 'false')
					+ ', looped: ' + (Reflect.field(animation, 'loop') == true ? 'true' : 'false')
					+ ', offsets: ' + numberArrayLiteral({
						value: [Reflect.field(animation, 'offsetX'), Reflect.field(animation, 'offsetY')]
					})
					+ ', indices: ' + intArrayLiteral(Reflect.field(animation, 'indices')) + '}';
			}
		}
		output += ']';
		var extras:Dynamic = Reflect.field(definition, 'extraData');
		output += ', extraData: [';
		if (extras != null && Std.isOfType(extras, Array)) {
			var firstExtra = true;
			for (extra in (cast extras:Array<Dynamic>)) {
				if (extra == null)
					continue;
				if (!firstExtra)
					output += ', ';
				firstExtra = false;
				output += '{name: ' + quote(Std.string(Reflect.field(extra, 'name')))
					+ ', values: ' + numberArrayLiteral(Reflect.field(extra, 'values')) + '}';
			}
		}
		return output + ']}';
	}

	static function numberLiteral(value:Dynamic, fallback:Float):String {
		if (value == null)
			return Std.string(fallback);
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? Std.string(fallback) : Std.string(parsed);
	}

	static function numberArrayLiteral(value:Dynamic):String {
		var values:Dynamic = value;
		if (value != null && !Std.isOfType(value, Array))
			values = Reflect.field(value, 'value');
		if (values == null || !Std.isOfType(values, Array))
			return '[0, 0]';
		var array:Array<Dynamic> = cast values;
		var output = '[';
		for (index in 0...array.length) {
			if (index > 0)
				output += ', ';
			output += numberLiteral(array[index], 0);
		}
		return output + ']';
	}

	static function intArrayLiteral(value:Dynamic):String {
		if (value == null || !Std.isOfType(value, Array))
			return '[]';
		var output = '[';
		var array:Array<Dynamic> = cast value;
		for (index in 0...array.length) {
			if (index > 0)
				output += ', ';
			output += Std.string(Std.int(array[index]));
		}
		return output + ']';
	}

	static function needsHxcStore(result:HxcCompatResult):Bool {
		if (result == null)
			return false;
		// A shader gate is emitted as a read from the generated isolated store,
		// even when the donor Module constructor itself is not replayed. Keep the
		// store declaration generic so any future bucket/field descriptor gets the
		// same scoped backing object without routing through ModuleHandler.
		if (result.runtimeShaderDescriptor != null
			&& Reflect.field(result.runtimeShaderDescriptor, 'gate') != null)
			return true;
		if (result.stageConstructorBody != null
			&& result.stageConstructorBody.indexOf('__hxcStore') >= 0)
			return true;
		if (result.stateInitializers != null)
			for (initializer in result.stateInitializers)
				if (initializer != null && initializer.value != null
					&& initializer.value.indexOf('__hxcStore') >= 0)
					return true;
		if (result.constructorStatements != null)
			for (statement in result.constructorStatements)
				if (statement != null && statement.indexOf('__hxcStore') >= 0)
					return true;
		for (callback in result.callbackAdapters)
			if (callback != null && callback.body != null && callback.body.indexOf('__hxcStore') >= 0)
				return true;
		for (helper in result.helperAdapters)
			if (helper != null && helper.body != null && helper.body.indexOf('__hxcStore') >= 0)
				return true;
		return false;
	}

	/**
		Derive a stable, opaque-ish store namespace without exposing the donor path
		as an interpreter global. Scripts under one `scripts/` root share the same
		Save-like key/value view, matching the donor singleton's scope.
	*/
	static function runtimeNamespace(path:String):String {
		var normalized = path == null ? '' : StringTools.replace(path, '\\', '/');
		var marker = normalized.indexOf('/scripts/');
		var root = marker >= 0 ? normalized.substr(0, marker) : normalized;
		if (root == '')
			root = 'default';
		return 'hxc_' + safeIdentifier(root);
	}

	static function isIdentifier(value:String):Bool {
		if (value == null || value == '')
			return false;
		if (!isIdentifierStart(value.charAt(0)))
			return false;
		for (index in 1...value.length)
			if (!isIdentifierPart(value.charAt(index)))
				return false;
		return true;
	}

	static function isIdentifierStart(value:String):Bool {
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || value == '_';
	}

	static function isIdentifierPart(value:String):Bool {
		if (isIdentifierStart(value))
			return true;
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	static function isWhitespace(value:String):Bool {
		return value == ' ' || value == '\t' || value == '\r' || value == '\n';
	}

	static function isLifecycle(name:String):Bool {
		if (name == null)
			return false;
		for (candidate in lifecycleNames)
			if (candidate.toLowerCase() == name.toLowerCase())
				return true;
		return false;
	}

	static function firstString(source:String, pattern:String):String {
		var groups = matchGroups(source, pattern);
		return groups.length == 0 || groups[0] == null ? '' : groups[0];
	}

	static function matchGroups(source:String, pattern:String):Array<String> {
		var output:Array<String> = [];
		var expression = new EReg(pattern, 'm');
		if (source == null || !expression.match(source))
			return output;
		for (index in 1...8) {
			try {
				var value = expression.matched(index);
				if (value == null)
					break;
				output.push(value);
			} catch (_:Dynamic) {
				break;
			}
		}
		return output;
	}

	static function collectMatches(source:String, pattern:String, group:Int):Array<String> {
		var output:Array<String> = [];
		if (source == null || source == '')
			return output;
		var offset = 0;
		while (offset < source.length) {
			var expression = new EReg(pattern, 'm');
			var remaining = source.substr(offset);
			if (!expression.match(remaining))
				break;
			var value:String = null;
			try {
				value = expression.matched(group);
			} catch (_:Dynamic) {}
			if (value != null)
				appendUnique(output, value);
			var position = expression.matchedPos();
			var advance = position.pos + (position.len > 0 ? position.len : 1);
			offset += advance;
		}
		return output;
	}

	static function stripStringLiterals(source:String):String {
		if (source == null || source == '')
			return source == null ? '' : source;
		var output = new StringBuf();
		var quote = '';
		var escaped = false;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (current == '\n' || current == '\r')
					output.add(current);
				else
					output.add(' ');
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				output.add(' ');
			} else
				output.add(current);
		}
		return output.toString();
	}

	static function stripComments(source:String):String {
		var output = new StringBuf();
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '\"' || current == "'") {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			if (current == '~' && next == '/') {
				var end = HxcScriptIdentity.regexLiteralEnd(source, index);
				output.add(source.substring(index, end));
				index = end;
				continue;
			}
			if (current == '/' && next == '/') {
				output.add(' ');
				index += 2;
				while (index < source.length && source.charAt(index) != '\n' && source.charAt(index) != '\r')
					index++;
				continue;
			}
			if (current == '/' && next == '*') {
				// Comments separate tokens and Haxe allows nested block comments.
				// Removing only through the first */ can expose a false class owner.
				output.add(' ');
				index += 2;
				var depth = 1;
				while (index < source.length && depth > 0) {
					var commentCurrent = source.charAt(index);
					var commentNext = index + 1 < source.length ? source.charAt(index + 1) : '';
					if (commentCurrent == '/' && commentNext == '*') {
						depth++;
						index += 2;
					} else if (commentCurrent == '*' && commentNext == '/') {
						depth--;
						index += 2;
					} else {
						if (commentCurrent == '\n' || commentCurrent == '\r')
							output.add(commentCurrent);
						index++;
					}
				}
				continue;
			}
			output.add(current);
			index++;
		}
		return output.toString();
	}

	static function appendUnique(values:Array<String>, value:String):Void {
		if (value != null && value != '' && values.indexOf(value) < 0)
			values.push(value);
	}

	static function safeIdentifier(value:String):String {
		if (value == null || value == '')
			return 'unknown';
		var output = new StringBuf();
		for (index in 0...value.length) {
			var character = value.charAt(index);
			if ((character >= 'a' && character <= 'z') || (character >= 'A' && character <= 'Z')
				|| (character >= '0' && character <= '9') || character == '_' || character == '-')
				output.add(character.toLowerCase());
			else
				output.add('-');
		}
		return output.toString();
	}

	static function quote(value:String):String {
		if (value == null)
			value = '';
		return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"';
	}

	/**
		Keep recognized donor facades visible when a member is outside the bounded
		adapter. Member calls are intentionally excluded from the ordinary
		unknown-function scanner, so these explicit diagnostics prevent a donor-only
		Conductor member or facade operation from disappearing silently.
	*/
	static function unsupportedHxcApiMembers(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		var facadeMembers:Dynamic = {
			PlayStatePlaylist: ['isStoryMode'],
			Countdown: ['skipCountdown', 'stopCountdown'],
			VideoCutscene: ['play'],
			CutsceneType: ['ENDING', 'INTRO'],
			FullScreenScaleMode: ['enabled', 'gameCutoutSize', 'wideScale', 'removeCutouts'],
			FunkinSprite: ['create', 'createSparrow', 'createTextureAtlas', 'cacheTexture'],
			FunkinCamera: [],
			FunkinSound: ['playOnce', 'playMusic', 'stopAllAudio', 'load'],
			WiggleEffectRuntime: [],
			WiggleEffectType: ['DREAMY', 'WAVY', 'HEAT_WAVE_HORIZONTAL', 'HEAT_WAVE_VERTICAL', 'FLAG']
		};
		for (owner in ['PlayStatePlaylist', 'Countdown', 'VideoCutscene', 'FunkinSprite', 'FunkinCamera',
			'FunkinSound', 'WiggleEffectRuntime']) {
			var members = collectMatches(source,
				'\\b' + owner + '\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', 1);
			for (member in members) {
				var allowed:Array<String> = cast Reflect.field(facadeMembers, owner);
				if (allowed == null || allowed.indexOf(member) < 0)
					appendUnique(result, owner + '.' + member + '(...) has no bounded native adapter.');
			}
		}
		var scaleMembers = collectMatches(source,
			'\\bFullScreenScaleMode\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\b', 1);
		for (member in scaleMembers) {
			var allowedScale:Array<String> = cast Reflect.field(facadeMembers, 'FullScreenScaleMode');
			if (allowedScale == null || allowedScale.indexOf(member) < 0)
				appendUnique(result, 'FullScreenScaleMode.' + member + ' has no bounded native adapter.');
		}
		var enumMembers = collectMatches(source,
			'\\bCutsceneType\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\b', 1);
		for (member in enumMembers) {
			var allowed:Array<String> = cast Reflect.field(facadeMembers, 'CutsceneType');
			if (allowed == null || allowed.indexOf(member) < 0)
				appendUnique(result, 'CutsceneType.' + member + ' has no bounded native adapter.');
		}
		var wiggleEnumMembers = collectMatches(source,
			'\\bWiggleEffectType\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\b', 1);
		for (member in wiggleEnumMembers) {
			var allowedWiggle:Array<String> = cast Reflect.field(facadeMembers, 'WiggleEffectType');
			if (allowedWiggle == null || allowedWiggle.indexOf(member) < 0)
				appendUnique(result, 'WiggleEffectType.' + member + ' has no bounded native adapter.');
		}
		// PlayState's native strumline properties are read-only. The exact
		// `new Strumline(...)` replacement shape is lowered to the in-place native
		// configurator; any other assignment must remain an explicit diagnostic so
		// a donor object cannot be smuggled into the host graph.
		for (side in ['player', 'opponent']) {
			var assignment = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)'
				+ '\\s*\\.\\s*' + side + 'Strumline\\s*=\\s*([^;\\n]+)', 'm');
			var remaining = source;
			var attempts = 0;
			while (attempts++ < 128 && assignment.match(remaining)) {
				var rhs = '';
				try rhs = StringTools.trim(assignment.matched(1)) catch (_:Dynamic) {}
				// The deliberately simple assignment scanner can also see the first
				// `=` in `==`/`!=` comparisons. Those begin with another `=` in the
				// captured RHS and are not property writes.
				if (rhs != '' && rhs.charAt(0) != '=' && !new EReg('^new\\s+Strumline\\s*\\(', 'm').match(rhs))
					appendUnique(result, 'PlayState.instance.' + side
						+ 'Strumline assignment is read-only; only new Strumline(...) can use the bounded native reconfiguration adapter.');
				var position = assignment.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		}
		var initStrumline = new EReg('\\b(?:PlayState\\s*\\.\\s*instance|currentPlayState|game)'
			+ '\\s*\\.\\s*initStrumlines\\s*\\(([^)]*)\\)', 'm');
		if (initStrumline.match(source)) {
			var initArgs = '';
			try initArgs = StringTools.trim(initStrumline.matched(1)) catch (_:Dynamic) {}
			if (initArgs != '')
				appendUnique(result, 'PlayState.instance.initStrumlines(...) has no bounded native adapter for arguments.');
		}
		return result;
	}

	static function makeDiagnostic(severity:String, code:String, message:String):HxcCompatDiagnostic {
		return {severity: severity, code: code, message: message};
	}
}
