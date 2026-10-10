package;

import hscript.AbstractScriptClass;
import hscript.ScriptClass;
import hscript.ScriptClassScope;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Owner-scoped executor for Psych Haxe BaseStage subclasses. */
class PsychCompiledStageRuntime {
	static final CALLBACKS:Array<String> = [
		'create', 'createPost', 'update', 'countdownTick', 'startSong',
		'beatHit', 'stepHit', 'sectionHit', 'openSubState', 'closeSubState',
		'eventCalled', 'eventPushed', 'eventPushedUnique', 'goodNoteHit',
		'opponentNoteHit', 'noteMiss', 'noteMissPress', 'destroy'
	];

	final ownerRoot:String;
	final className:String;
	final stageHost:Dynamic;
	final context:SourceStageContext;
	final construction:PsychStageConstruction;
	final sharedSession:PsychSourceClassSession;
	final providedBindings:Map<String, Dynamic>;
	final providedSymbols:Map<String, Dynamic>;
	var classScope:ScriptClassScope;
	var stageClass:AbstractScriptClass;
	var baseStage:PsychBaseStageCompat;
	var attempted:Bool = false;
	var created:Bool = false;
	var destroyed:Bool = false;
	var faulted:Bool = false;
	var mappedAnimsPrepared:Bool = false;
	final _diagnostics:Array<String> = [];
	final _sourceUseDiagnostics:Array<String> = [];

	public function new(ownerRoot:String, className:String, stageHost:Dynamic,
		?bindings:Map<String, Dynamic>, ?symbols:Map<String, Dynamic>, ?context:SourceStageContext, ?session:PsychSourceClassSession) {
		this.ownerRoot = ownerRoot;
		this.className = className;
		this.stageHost = stageHost;
		this.context = context;
		sharedSession = session;
		construction = new PsychStageConstruction(stageHost, context, true);
		providedBindings = copyMap(bindings);
		providedSymbols = copyMap(symbols);
	}

	public var diagnostics(get, never):Array<String>;
	function get_diagnostics():Array<String> return _diagnostics.copy();

	public var sourceUseDiagnostics(get, never):Array<String>;
	function get_sourceUseDiagnostics():Array<String> return _sourceUseDiagnostics.copy();

	public var sourceObject(get, never):Dynamic;
	function get_sourceObject():Dynamic return stageClass;
	public var active(get, never):Bool;
	function get_active():Bool return created && !destroyed && !faulted && stageClass != null;

	/** Load one selected-owner class and run its authored BaseStage.create hook. */
	public function create():Bool {
		if (attempted) return active;
		attempted = true;
		if (ownerRoot == null || ownerRoot.trim() == '')
			return fail('an owner root is required');
		if (className == null || className.trim() == '')
			return fail('an owner class path is required');

		var ownerImports = [className];
		// Haxe's source/import.hx contributes this module to every Psych source
		// file, but it is not written in StageWeek1/PhillyStreets themselves.
		// Register its source descriptor only when the selected owner actually
		// retained it; never borrow the module from another root.
		if (PsychSourceStageCompat.sourceModuleExists(ownerRoot, 'objects.BGSprite'))
			ownerImports.push('objects.BGSprite');
		var loaded:CodenameScriptClassLoader.CodenameScriptClassLoad = null;
		if (sharedSession != null) {
			if (providedBindings.keys().hasNext() || providedSymbols.keys().hasNext())
				return fail('shared stage sessions use their established binding policy');
			try loaded = sharedSession.importStageClasses(ownerRoot, ownerImports)
			catch (error:Dynamic) return fail(Std.string(error));
		} else {
			var bindings = copyMap(providedBindings);
			if (!bindExact(bindings, 'BaseStage', PsychBaseStageCompat)
				|| !bindExact(bindings, 'backend.BaseStage', PsychBaseStageCompat)
				|| !bindExact(bindings, 'ClientPrefs', PsychClientPrefsCompat)
				|| !bindExact(bindings, 'backend.ClientPrefs', PsychClientPrefsCompat))
				return false;
			var symbols = copyMap(providedSymbols);
			symbols.set('BaseStage', PsychBaseStageCompat);
			symbols.set('backend.BaseStage', PsychBaseStageCompat);
			for (name in bindings.keys()) symbols.set(name, bindings.get(name));
			loaded = CodenameScriptClassLoader.load(ownerRoot, ownerImports, bindings, symbols);
		}
		for (diagnostic in loaded.diagnostics) _diagnostics.push(diagnostic);
		for (diagnostic in loaded.sourceUseDiagnostics) _sourceUseDiagnostics.push(diagnostic);
		if (_diagnostics.length > 0) {
			if (sharedSession == null) loaded.scope.release();
			return false;
		}
		classScope = loaded.scope;
		construction.bind(classScope, sharedSession == null);
		var creationHost = context == null ? stageHost : context.state();
		var membersBeforeCreate = snapshotHostMembers(creationHost);
		try {
			stageClass = construction.withActive(function() return classScope.createInstance(className, [stageHost]));
			var nativeBase = stageClass == null ? null : classScope.unwrapNativeArgument(stageClass);
			if (!Std.isOfType(nativeBase, PsychBaseStageCompat))
				throw 'owner class ' + className + ' does not extend the Psych BaseStage adapter';
			baseStage = cast nativeBase;
			created = true;
			return true;
		} catch (error:Dynamic) {
			fail('could not instantiate ' + className + ': ' + Std.string(error));
			destroy();
			for (i in 0...construction.stages.length) construction.registries[i].remove(construction.stages[i]);
			cleanupMembersAddedSince(membersBeforeCreate, creationHost);
			return false;
		}
	}

	public function beginPostCreate():Void construction.beginPostCreate();

	/** Psych calls createPost after actors, notes and state members are ready. */
	public function createPost():Bool return dispatch('createPost', []);

	public function update(elapsed:Float):Bool return dispatch('update', [elapsed]);

	/** Dispatch a named Psych BaseStage callback with the authored argument list. */
	public function dispatch(name:String, ?args:Array<Dynamic>, admitted:Bool = false):Bool {
		if (!active) return false;
		if (CALLBACKS.indexOf(name) < 0)
			return fail('unsupported BaseStage callback ' + Std.string(name));
		try {
			if (name == 'createPost') beginPostCreate();
			if (name != 'create' && !admitted && !SourceStageCallbacks.enabled(stageClass, PsychStageObject.read)) return true;
			SourceStageCallbacks.publish(stageHost, stageClass, name, PsychStageObject.read, PsychStageObject.write);
			if (name == 'createPost') {
				if (!prepareSourceMappedCharacterAnims()) return false;
			}
			construction.withActive(function() return stageClass.callFunction(name, args == null ? [] : args));
			return true;
		} catch (error:Dynamic) {
			return fail('callback ' + name + ' failed: ' + Std.string(error));
		}
	}

	/** A Psych source Character constructor can hand a companion chart's note
	 * rows to a stage class. Read that declaration from this owner and retain
	 * the same array on the native actor and owner-scoped static field. */
	function prepareSourceMappedCharacterAnims():Bool {
		if (mappedAnimsPrepared) return true;
		mappedAnimsPrepared = true;
		#if cpp
		var relative = CodenameScriptDiscovery.resolveScopedRelative(ownerRoot, 'source/objects/Character.hx');
		if (relative == null) return true;
		var sourcePath = Path.join([ownerRoot, relative]);
		if (FileSystem.stat(sourcePath).size > 1024 * 1024)
			return fail('owner Character source exceeds the mapped animation source limit');
		var mapping = PsychMappedAnimsSource.discover(File.getContent(sourcePath));
		if (mapping == null) return true;
		var actors:Array<Dynamic> = [];
		var group:Dynamic = Reflect.field(stageHost, 'gfGroup');
		var members:Dynamic = group == null ? null : Reflect.field(group, 'members');
		if (Std.isOfType(members, Array))
			for (member in (cast members:Array<Dynamic>)) if (member != null) actors.push(member);
		var gf = Reflect.field(stageHost, 'gf');
		if (gf != null && actors.indexOf(gf) < 0) actors.push(gf);
		var matched:Array<Dynamic> = [];
		for (actor in actors)
			if (Reflect.field(actor, 'curCharacter') == mapping.character) matched.push(actor);
		if (matched.length == 0) return true;

		var folder = Song.storageFolder(PlayState.SONG);
		if (!CodenameScriptDiscovery.safeName(folder))
			return fail('mapped animation chart has no safe selected song folder');
		var chartRoot = 'assets/data/' + folder;
		var chartFile = CodenameScriptDiscovery.resolveScopedRelative(chartRoot, mapping.chart + '.json');
		var chartPath = chartRoot + '/' + (chartFile == null ? mapping.chart + '.json' : chartFile);
		if (chartFile == null || !FNFAssets.exists(chartPath))
			return fail('selected owner mapped animation chart is missing: ' + chartPath);
		var parsed:Dynamic = CoolUtil.parseJson(FNFAssets.getText(chartPath));
		var sections:Dynamic = Reflect.field(parsed, 'notes');
		if (!Std.isOfType(sections, Array)) {
			var wrapper:Dynamic = Reflect.field(parsed, 'song');
			sections = wrapper == null ? null : Reflect.field(wrapper, 'notes');
		}
		if (!Std.isOfType(sections, Array))
			return fail('mapped animation chart has no note sections: ' + chartPath);
		var animationNotes:Array<Dynamic> = [];
		for (section in (cast sections:Array<Dynamic>)) {
			var rows:Dynamic = section == null ? null : Reflect.field(section, 'sectionNotes');
			if (!Std.isOfType(rows, Array)) continue;
			for (row in (cast rows:Array<Dynamic>))
				if (Std.isOfType(row, Array) && (cast row:Array<Dynamic>).length >= 2)
					animationNotes.push(row);
		}
		animationNotes.sort(function(a:Dynamic, b:Dynamic):Int {
			var left:Float = (cast a:Array<Dynamic>)[0];
			var right:Float = (cast b:Array<Dynamic>)[0];
			return left < right ? -1 : left > right ? 1 : 0;
		});
		if (!classScope.setOwnerStaticField(mapping.className, mapping.field, animationNotes))
			return fail('mapped animation target is not a loaded owner static field: '
				+ mapping.className + '.' + mapping.field);
		for (actor in matched) {
			Reflect.setField(actor, 'animationNotes', animationNotes);
			if (mapping.skipDance) Reflect.setField(actor, 'skipDance', true);
			if (mapping.initialAnim != null) {
				var animation = Reflect.field(actor, 'animation');
				var exists = animation == null ? null : Reflect.field(animation, 'exists');
				if (Reflect.isFunction(exists)
					&& Reflect.callMethod(animation, exists, [mapping.initialAnim]) == true) {
					var playAnim = Reflect.field(actor, 'playAnim');
					if (Reflect.isFunction(playAnim))
						Reflect.callMethod(actor, playAnim, [mapping.initialAnim, true]);
					if (StringTools.startsWith(mapping.initialAnim, 'shoot'))
						Reflect.setField(actor, 'hasGun', true);
				}
			}
		}
		#end
		return true;
	}

	/** Run authored destruction once; shared descriptors live until owner-session teardown. */
	public function destroy(admitted:Bool = false, release:Bool = true):Void {
		if (!destroyed) {
			destroyed = true;
			// Host list traversal owns callback order. Keep the scope alive until
			// it has visited nested siblings after the selected stage.
			var targets:Array<Dynamic> = release ? construction.stages : [stageClass];
			for (stage in targets) {
				try {
					if (stage != null && ((stage == stageClass && admitted)
						|| SourceStageCallbacks.enabled(stage, PsychStageObject.read)))
						construction.withActive(function() return PsychStageObject.call(stage, 'destroy', []));
				} catch (error:Dynamic) fail('callback destroy failed: ' + Std.string(error));
			}
		}
		if (!release) return;
		for (adapter in construction.adapters) adapter.exists = false;
		created = false;
		stageClass = null;
		baseStage = null;
		releaseScope();
	}

	/** Host traversal already chose and invoked its live stage callbacks. */
	public function releaseAfterHostTraversal():Void {
		destroyed = true;
		destroy();
	}

	function bindExact(bindings:Map<String, Dynamic>, path:String, value:Dynamic):Bool {
		if (bindings.exists(path) && bindings.get(path) != value)
			return fail('owner runtime binding conflicts with required class ' + path);
		bindings.set(path, value);
		return true;
	}

	function releaseScope():Void {
		if (classScope != null && sharedSession == null) classScope.release();
		classScope = null;
	}

	function fail(message:String):Bool {
		_diagnostics.push('[psych-stage] ' + message);
		faulted = true;
		return false;
	}

	/** A failed create must not leave sprites/groups from a half-built stage in
	 * the PlayState member list while the neutral or scripted fallback starts.
	 * Successful stages remain owned by the parent state and are destroyed with
	 * its normal member teardown after this runtime releases its class scope.
	 */
	function snapshotHostMembers(host:Dynamic):Array<Dynamic> {
		if (host == null) return [];
		var value:Dynamic = null;
		try value = Reflect.field(host, 'members') catch (_:Dynamic) return [];
		if (!Std.isOfType(value, Array)) return [];
		return (cast value:Array<Dynamic>).copy();
	}

	function cleanupMembersAddedSince(before:Array<Dynamic>, host:Dynamic):Void {
		if (host == null) return;
		var after = snapshotHostMembers(host);
		var remove:Dynamic = null;
		try remove = Reflect.field(host, 'remove') catch (_:Dynamic) {}
		for (object in after) {
			if (object == null || (before != null && before.indexOf(object) >= 0)) continue;
			if (Reflect.isFunction(remove)) try Reflect.callMethod(host, remove, [object, true]) catch (_:Dynamic) {}
			var destroy:Dynamic = null;
			try destroy = Reflect.field(object, 'destroy') catch (_:Dynamic) {}
			if (Reflect.isFunction(destroy)) try Reflect.callMethod(object, destroy, []) catch (_:Dynamic) {}
		}
	}

	static function copyMap(source:Map<String, Dynamic>):Map<String, Dynamic> {
		var result:Map<String, Dynamic> = new Map();
		if (source != null) for (name in source.keys()) result.set(name, source.get(name));
		return result;
	}
}
