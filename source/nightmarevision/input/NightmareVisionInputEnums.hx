package nightmarevision.input;

/** Source Nightmare Vision action names carried through the FlxAction API. */
enum abstract Action(String) to String from String {
	var UI_UP = "ui_up";
	var UI_LEFT = "ui_left";
	var UI_RIGHT = "ui_right";
	var UI_DOWN = "ui_down";
	var UI_UP_P = "ui_up-press";
	var UI_LEFT_P = "ui_left-press";
	var UI_RIGHT_P = "ui_right-press";
	var UI_DOWN_P = "ui_down-press";
	var UI_UP_R = "ui_up-release";
	var UI_LEFT_R = "ui_left-release";
	var UI_RIGHT_R = "ui_right-release";
	var UI_DOWN_R = "ui_down-release";

	var NOTE_UP = "note_up";
	var NOTE_LEFT = "note_left";
	var NOTE_RIGHT = "note_right";
	var NOTE_DOWN = "note_down";
	var NOTE_UP_P = "note_up-press";
	var NOTE_LEFT_P = "note_left-press";
	var NOTE_RIGHT_P = "note_right-press";
	var NOTE_DOWN_P = "note_down-press";
	var NOTE_UP_R = "note_up-release";
	var NOTE_LEFT_R = "note_left-release";
	var NOTE_RIGHT_R = "note_right-release";
	var NOTE_DOWN_R = "note_down-release";

	var NOTE_DODGE = "note_dodge";
	var NOTE_DODGE_P = "note_dodge-press";
	var NOTE_DODGE_R = "note_dodge-release";

	var ACCEPT = "accept";
	var BACK = "back";
	var PAUSE = "pause";
	var RESET = "reset";
	var FULLSCREEN = "fullscreen";
	var SWITCH_DEBUG_DISPLAY = "switch_debug_display";
	var SOFT_RELOAD = "soft_reload";
	var HARD_RELOAD = "hard_reload";
}

enum Device {
	Keys;
	Gamepad(id:Int);
}

/** Rebinding groups that share inputs across held, press, and release actions. */
enum Control {
	UI_UP;
	UI_LEFT;
	UI_RIGHT;
	UI_DOWN;
	NOTE_UP;
	NOTE_LEFT;
	NOTE_RIGHT;
	NOTE_DOWN;
	NOTE_DODGE;
	RESET;
	ACCEPT;
	BACK;
	PAUSE;
	FULLSCREEN;
	SWITCH_DEBUG_DISPLAY;
	SOFT_RELOAD;
	HARD_RELOAD;
}

enum KeyboardScheme {
	Solo;
	Duo(first:Bool);
	None;
	Custom;
}
