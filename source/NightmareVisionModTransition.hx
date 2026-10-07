package;

/** Source-compatible transition selected by Nightmare Vision mod metadata. */
enum NightmareVisionModTransition {
	SWIPE;
	FADE;
	SCRIPTED(key:String);
	NONE;
	ENGINE_DEFAULT;
}
