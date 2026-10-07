package;

/** One common preset for gameplay, persistent plugins, gameover and substates. */
class NightmareVisionAlphabetBindings {
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths):Void {
		var owner:NightmareVisionAlphabetOwner = {atlas:function(name) return paths.getSparrowAtlas(name),
			spriteOwner:NightmareVisionSpriteRegistry.capture(paths)};
		var context = NightmareVisionAlphabetRegistry.get(paths.root, owner);
		var scope = interp.sourceClassScope();
		interp.variables.set('Alphabet', NightmareVisionAlphabet);
		interp.variables.set('AlphaCharacter', NightmareVisionAlphaCharacter);
		interp.bindImport('funkin.objects.Alphabet', NightmareVisionAlphabet);
		interp.bindImport('funkin.objects.Alphabet.AlphaCharacter', NightmareVisionAlphaCharacter);
		interp.bindImport('Reflect', Reflect); interp.bindImport('Type', Type);
		interp.variables.set('Reflect', Reflect); interp.variables.set('Type', Type);
		scope.bindRuntimeClass('funkin.objects.Alphabet', NightmareVisionAlphabet);
		scope.bindRuntimeClass('funkin.objects.AlphaCharacter', NightmareVisionAlphaCharacter);
		scope.bindStaticField(NightmareVisionAlphaCharacter, 'alphabet', function() return context.alphabet,
			function(value) return context.alphabet = value);
		scope.bindStaticField(NightmareVisionAlphaCharacter, 'numbers', function() return context.numbers,
			function(value) return context.numbers = value);
		scope.bindStaticField(NightmareVisionAlphaCharacter, 'symbols', function() return context.symbols,
			function(value) return context.symbols = value);
		interp.bindConstructorFactory(NightmareVisionAlphabet, function(args:Array<Dynamic>):Dynamic {
			return new NightmareVisionAlphabet(args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0,
				args.length > 2 ? args[2] : '', args.length > 3 ? args[3] : false,
				args.length > 4 ? args[4] : 1, context);
		}, null);
		interp.bindConstructorFactory(NightmareVisionAlphaCharacter, function(args:Array<Dynamic>):Dynamic {
			return new NightmareVisionAlphaCharacter(args[0], args[1], args[2], context);
		}, null);
	}
}
