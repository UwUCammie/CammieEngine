package;

import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;

/** Exercise both public text dialects on disposable native labels. */
@:access(PlayState)
class RuntimeSmokeTextProperties {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState, legacy:LuaCompatInterp):Void {
		var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		var oldVariables = state.psychScriptVariables;
		var label = state.compatMakeLuaText('__textProperties', 'first', 180);
		var sibling = new FlxText(0, 0, 90, 'sprite sibling');
		state.modchartSprites.set('__textProperties', sibling);
		var cleanup = function() {
			state.nightmareVisionLegacyFieldCameras = oldLegacy;state.psychScriptVariables = oldVariables;
			state.modchartTexts.remove('__textProperties');state.modchartSprites.remove('__textProperties');
			label.destroy();sibling.destroy();
		};
		try {
			label.borderStyle = SHADOW;
			legacy.execute(new hscript.Parser().parseString('if(setTextWidth("__textProperties",144)!=null||getTextWidth("__textProperties")!=144)throw "legacy text width namespace/return";if(setTextSize("__textProperties",22)!=null||getTextSize("__textProperties")!=22)throw "legacy text size";setTextItalic("__textProperties",true);setTextAlignment("__textProperties","justify");setTextBorder("__textProperties",3,"FFFFFF");setTextColor("__textProperties","FFFFFF");if(getTextFont("__missingText")!=null||getTextSize("__missingText")!=-1||getTextWidth("__missingText")!=0)throw "legacy missing text defaults";', '__legacy_text_properties'));
			check(label.fieldWidth == 144 && sibling.fieldWidth == 90 && label.italic && label.alignment == 'left'
				&& label.borderStyle == SHADOW && label.borderSize == 3 && label.borderColor == 0xffffffff, 'Historical text namespace and style policy');
			// Historical colors take a bare RGB or 0x-prefixed ARGB string.
			check(SourceTextStyle.historicalColor('FFFFFF') == 0xffffffff && SourceTextStyle.historicalColor('0x80112233') == 0x80112233, 'Historical ARGB bits');
			state.nightmareVisionLegacyFieldCameras = false;state.psychScriptVariables = [];
			state.psychScriptVariables.set('__textRoot', {child:label});
			var psych = new LuaCompatInterp();new PsychSourceBindings(state).install(psych);
			psych.execute(new hscript.Parser().parseString('if(setTextString("__textRoot.child","modern")!=true||getTextString("__textRoot.child")!="modern")throw "Psych nested text result";if(setTextWidth("__textRoot.child",210)!=true||getTextWidth("__textRoot.child")!=210)throw "Psych text width";if(setTextSize("__textRoot.child",20)!=true||getTextSize("__textRoot.child")!=20)throw "Psych text size";if(setTextAlignment("__textRoot.child","justify")!=true)throw "Psych alignment return";if(setTextBorder("__textRoot.child",4,"#80112233","shadow")!=true)throw "Psych border return";if(setTextColor("__textRoot.child","FFFFFFFF")!=true)throw "Psych color return";if(setTextString("__missingText","ignored")!=false||getTextFont("__missingText")!=null||getTextWidth("__missingText")!=0)throw "Psych missing text defaults";', '__psych_text_properties'));
			check(label.text == 'modern' && label.alignment == 'justify' && label.borderStyle == SHADOW
				&& label.borderSize == 4 && label.borderColor == 0x80112233, 'Psych native setters');
			check(SourceTextStyle.psychColor('FFFFFFFF') == 0xffffffff && SourceTextStyle.psychColor('#80112233') == 0x80112233
				&& SourceTextStyle.psychColor('0x80112233') == 0xff112233 && SourceTextStyle.psychColor('invalid') == 0xffffffff, 'Psych source color prefix and fallback policy');
			psych.variables.clear();
			@:privateAccess RuntimeSmokeHarness.emit('source_text_properties_native_verified', {historicalNamespace:true,historicalReturns:true,psychNestedTarget:true,psychReturns:true,nativeStyleSetters:true,missingDefaults:true,argbBits:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
