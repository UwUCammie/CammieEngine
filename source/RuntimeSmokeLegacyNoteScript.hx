package;

/** Isolated native proof of historical note attachments and source registry reflection. */
class RuntimeSmokeLegacyNoteScript {
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_NOTE_SCRIPT_SMOKE') != '1') return;
		var state = PlayState.instance;
		var runtime = @:privateAccess state.nightmareVisionNoteTypes;
		if (runtime == null || !runtime.legacyNoteScripts) throw 'Historical note runtime is unavailable';
		var note:Note = null;
		for (candidate in @:privateAccess state.unspawnNotes)
			if (candidate != null && !candidate.isSustainNote && candidate.noteType == '') {note = candidate;break;}
		if (note == null) throw 'Native note attachment probe requires an ordinary pending tap';
		var originalType = note.noteType;
		var originalScript = note.noteScript;
		var colors = note.nightmareVisionLegacyColors;
		var originalAssigned = @:privateAccess colors.assignedType;
		var originalColors = [note.colorSwap.hue, note.colorSwap.saturation, note.colorSwap.brightness,
			note.noteSplashHue, note.noteSplashSat, note.noteSplashBrt];
		var originalSplash = note.noteSplashTexture;
		var events:Array<String> = [];
		var errors:Array<String> = [];
		var modules:Array<NightmareVisionScriptModule> = [];
		var names = ['__native_note_owner_one', '__native_note_owner_two'];
		for (name in names) {
			if (state.notetypeScripts.exists(name)) throw 'Native note probe registry collision';
			var module = NightmareVisionScriptModule.fromSource(name,
				"function registryCheck() { return notetypeScripts == game.notetypeScripts && Reflect.getProperty(game,'notetypeScripts') == notetypeScripts; }"
				+ "function assign(n,name) { n.noteType=name; } function attach(n,m) { Reflect.setProperty(n,'noteScript',m); }"
				+ "function setupNote(n) { if(this!=n || n.noteScript!=script || script.scriptType!='hscript') throw 'setup attachment'; record('setup',n); }"
				+ "function update(n,e) { if(this!=n) throw 'update receiver'; record('update',n); }"
				+ "function loadNoteAnims(n) { if(this!=n) throw 'animation receiver'; record('animation',n); }",
				state, null, function(interp) {
					@:privateAccess state.seedNightmareVision(interp, {scope:'smoke',name:name,path:name,relative:name}, null);
					interp.variables.set('record', function(phase:String,n:Note) {
						if (n != note) throw 'Native attached callback note identity mismatch';
						events.push(phase+':'+name);
					});
				}, function(n,p,e) errors.push(p+': '+Std.string(e)));
			modules.push(module);state.notetypeScripts.set(name,module);
		}
		var restore = function() {
			note.sourceKind = originalType;note.noteScript = originalScript;
			@:privateAccess colors.assignedType = originalAssigned;
			note.colorSwap.hue=originalColors[0];note.colorSwap.saturation=originalColors[1];note.colorSwap.brightness=originalColors[2];
			note.noteSplashHue=originalColors[3];note.noteSplashSat=originalColors[4];note.noteSplashBrt=originalColors[5];
			note.noteSplashTexture=originalSplash;
			for (name in names) state.notetypeScripts.remove(name);
			for (module in modules) module.destroy();
		};
		try {
			if (modules[0].callValue('registryCheck') != true) throw 'Native historical registry reflection mismatch';
			modules[0].callValue('assign',[note,names[0]]);
			if (note.noteScript != modules[0]) throw 'Native setter did not capture script';
			state.notetypeScripts.set(names[0],modules[1]);runtime.update(note,0);
			modules[0].callValue('assign',[note,names[0]]);
			if (note.noteScript != null) throw 'Native same-type setter did not clear attachment';
			runtime.update(note,0);
			modules[0].callValue('assign',[note,names[1]]);
			modules[0].callValue('attach',[note,modules[0]]);runtime.update(note,0);
			runtime.loadLegacyAnimations(note,false,function()throw 'Native animation attachment was ignored');
			var expected=['setup:'+names[0],'update:'+names[0],'setup:'+names[1],'update:'+names[0],'animation:'+names[0]];
			if (events.join(',') != expected.join(',') || errors.length > 0)
				throw 'Native historical attachment sequence mismatch: '+events.join(',')+' '+errors.join(',');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_note_script_native_verified',
				{registryIdentity:true,capturedIdentity:true,sameTypeClear:true,reflectedAttachment:true,receiverIdentity:true,animationAttachment:true,callbacks:events.length});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
