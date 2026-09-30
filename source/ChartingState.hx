package;

import Section.SwagSection;
import Song.SwagSong;
import Conductor.BPMChangeEvent;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.addons.display.FlxGridOverlay;
import flixel.addons.ui.FlxInputText;
import flixel.addons.ui.FlxUI9SliceSprite;
import flixel.addons.ui.FlxUI;
import flixel.addons.ui.FlxUICheckBox;
import flixel.addons.ui.FlxUIDropDownMenu;
import flixel.addons.ui.FlxUIInputText;
import flixel.addons.ui.FlxUINumericStepper;
import flixel.addons.ui.FlxUITabMenu;
import flixel.addons.ui.FlxUITooltip.FlxUITooltipStyle;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.group.FlxGroup;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.math.FlxMath;
import flixel.math.FlxPoint;
import flixel.sound.FlxSound;
import flixel.text.FlxText;
import flixel.ui.FlxButton;
import flixel.ui.FlxSpriteButton;
import flixel.util.FlxColor;
import haxe.Json;
import lime.utils.Assets;
import openfl.events.Event;
import openfl.events.IOErrorEvent;
import openfl.events.IOErrorEvent;
import openfl.events.IOErrorEvent;
import openfl.media.Sound;
import openfl.net.FileReference;
import lime.ui.FileDialog;
import lime.ui.FileDialogType;
import openfl.utils.ByteArray;
import lime.system.System;
#if sys
import sys.io.File;
import haxe.io.Path;
import tjson.TJSON;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;
#end

using StringTools;

enum abstract NoteTypes(Int) from Int to Int {
	@:op(A == B) static function _(_, _):Bool;

	var Normal;
	var Lift;
	var Mine;
	var Death;
}
class ChartingState extends MusicBeatState {
	//var _file:FileReference;

	public var playClaps:Bool = false;
	var claps:Array<EdtNote> = [];

	var UI_box:FlxUITabMenu;

	/**
	 * Array of notes showing when each section STARTS in STEPS
	 * Usually rounded up??
	 */
	var curSection:Int = 0;
	var stepperSection:FlxUINumericStepper;
	var copySecLock:Bool = false;

	public static var lastSection:Int = 0;

	var bpmTxt:FlxText;

	var strumLine:FlxSprite;
	var curSong:String = 'Dadbattle';
	var amountSteps:Int = 0;
	var bullshitUI:FlxGroup;
	var noteTypeText:FlxText;
	var highlight:FlxSprite;

	var GRID_SIZE:Int = 40;
	var zoomFactor:Int = 1;

	var dummyArrow:FlxSprite;
	var gridSnap:Int = 16;
	var gridSnapTxt:FlxText;
	var snapMilestones:Array<Int> = [4, 8, 12, 16, 20, 24, 32, 48, 64, 96, 192];

	var curRenderedNotes:FlxTypedGroup<EdtNote>;
	var curRenderedSustains:FlxTypedGroup<FlxSprite>;
	var curRenderedEvents:FlxTypedGroup<FlxText>;
	var renderedEventRefs:Array<Dynamic> = [];
	var eventLaneBG:FlxSprite;
	var eventLanePrevBG:FlxSprite;
	var eventLaneNextBG:FlxSprite;

	var prevGrid:FlxSprite;
	var nextGrid:FlxSprite;
	var showPrevNext:Bool = true;
	var gridBG:FlxSprite;
	var gridBlackLine:FlxSprite;
	var gridBeatLines:Array<FlxSprite> = [];

	public static var _song:SwagSong;
	var noteType:Int = Normal;
	var typingShit:FlxInputText;
	var player1TextField:FlxInputText;
	var player2TextField:FlxInputText;
	var gfTextField:FlxInputText;
	var cutsceneTextField:FlxInputText;
	var uiTextField:FlxInputText;
	var layoutTextField:FlxInputText;
	var stageTextField:FlxInputText;
	var stageID:FlxUINumericStepper;
	var isAltNoteCheck:FlxUICheckBox;
	var chartEventTimeField:FlxUIInputText;
	var chartEventNameField:FlxUIInputText;
	var chartEventValue1Field:FlxUIInputText;
	var chartEventValue2Field:FlxUIInputText;
	var chartEventValue3Field:FlxUIInputText;
	var chartEventSelectionText:FlxText;
	var selectedChartEvent:Dynamic;

	var charDropdown:ChartCharDropdown;
	
	/*
	 * WILL BE THE CURRENT / LAST PLACED NOTE
	**/
	var curSelectedNote:Array<Dynamic>;

	var tempBpm:Float = 0;

	var vocals:FlxSound;
	var editorVocalTracks:VocalTracks;
	var chartEditorSmokePending:Bool = false;

	function pauseEditorVocals():Void {
		if (editorVocalTracks != null)
			editorVocalTracks.pause();
	}

	function playEditorVocals():Void {
		if (editorVocalTracks != null)
			editorVocalTracks.play();
	}

	function stopEditorVocals():Void {
		if (editorVocalTracks != null)
			editorVocalTracks.stop();
	}

	function seekEditorVocals(time:Float):Void {
		if (editorVocalTracks != null)
			editorVocalTracks.seek(time);
	}

	function destroyEditorVocals():Void {
		if (editorVocalTracks == null)
			return;
		editorVocalTracks.stop();
		for (track in editorVocalTracks.tracks)
			FlxG.sound.list.remove(track);
		editorVocalTracks.destroy();
		editorVocalTracks = null;
		vocals = null;
	}

	var leftIcon:HealthIcon;
	var rightIcon:HealthIcon;

	var useLiftNote:Bool = false;
	var sideChoosen = 0;

	override function create() {
		curSection = lastSection;

		PlayState.startingPosition = 0;

		gridBG = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, GRID_SIZE * 8, GRID_SIZE * 16);
		add(gridBG);

		prevGrid = gridBG.clone();
		prevGrid.alpha = 0.5;
		prevGrid.y = gridBG.y - prevGrid.height;
		add(prevGrid);

		nextGrid = prevGrid.clone();
		nextGrid.alpha = 0.5;
		nextGrid.y = gridBG.y + nextGrid.height;
		add(nextGrid);

		leftIcon = new HealthIcon('bf');
		rightIcon = new HealthIcon('dad');
		leftIcon.scrollFactor.set(1, 1);
		rightIcon.scrollFactor.set(1, 1);

		leftIcon.setGraphicSize(0, 45);
		rightIcon.setGraphicSize(0, 45);

		add(leftIcon);
		add(rightIcon);

		leftIcon.setPosition(gridBG.x + gridBG.width / 4 - leftIcon.width / 2, -100);
		rightIcon.setPosition(gridBG.x + 3*gridBG.width / 4 - rightIcon.width / 2, -100);

		gridBlackLine = new FlxSprite(gridBG.x + gridBG.width / 2 - 1, -gridBG.height).makeGraphic(2, Std.int(gridBG.height), FlxColor.BLACK);
		add(gridBlackLine);

		for (i in 1...11) {
			var beatLine = new FlxSprite(gridBG.x, prevGrid.y + gridBG.height / 4 * i - 1).makeGraphic(Std.int(gridBG.width), 2, FlxColor.BLACK);
			switch(i) {
				case 3 | 7:
					// section line
				default:
					beatLine.alpha = 0.5;
			}
			add(beatLine);
			gridBeatLines.push(beatLine);
		}

		curRenderedNotes = new FlxTypedGroup<EdtNote>();
		curRenderedSustains = new FlxTypedGroup<FlxSprite>();
		curRenderedEvents = new FlxTypedGroup<FlxText>();

		if (PlayState.SONG != null)
			_song = PlayState.SONG;
		else {
			_song = {
				song: 'Test',
				notes: [],
				bpm: 150,
				needsVoices: true,
				player1: 'bf',
				player2: 'dad',
				stage: 'stage',
				gf: 'gf',
				isHey: false,
				isCheer: false,
				isSpooky: false,
				isMoody: false,
				speed: 1,
				cutsceneType: "none",
				uiType: 'normal',
				forceLayout: 'none',
				preferredNoteAmount: 4,
				forceJudgements: false,
				convertMineToNuke: false,
				mania: 0,
				stageID: 0
			};
		}
		// Gameplay normalizes legacy note lanes in memory. The chart editor
		// needs the selected file's authored rows so an unchanged Quick Save
		// does not rewrite Modding Plus lift lanes or other source note payloads.
		loadRawEditorNotes();
		EditorSectionLengthCompat.normalize(cast _song.notes);
		ChartEventModel.normalizeSong(_song);
		var eventPath = 'assets/data/' + Song.storageFolder(_song) + '/events.json';
		if (FNFAssets.exists(eventPath)) {
			var eventData:Dynamic = CoolUtil.parseJson(FNFAssets.getText(eventPath));
			ChartEventModel.mergeCompanion(_song, eventData);
		}

		FlxG.mouse.visible = true;
		//FlxG.save.bind('save1', 'bulbyVR');
		// i don't know why we need to rebind our save
		tempBpm = _song.bpm;

		addSection();

		// sections = _song.notes;

		updateGrid();

		loadSong(_song.song);
		Conductor.changeBPM(_song.bpm);
		Conductor.mapBPMChanges(_song);
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_bpm_map');

		bpmTxt = new FlxText(800, 50, 0, "", 16);
		bpmTxt.scrollFactor.set();
		add(bpmTxt);

		gridSnapTxt = new FlxText(20, 50, 0, "Grid Snap: 16th", 16);
		gridSnapTxt.scrollFactor.set();
		add(gridSnapTxt);

		strumLine = new FlxSprite(0, 50).makeGraphic(Std.int(FlxG.width / 2), 4);
		add(strumLine);

		dummyArrow = new FlxSprite().makeGraphic(GRID_SIZE, GRID_SIZE);
		add(dummyArrow);
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_grid_controls');

		var tabs = [
			{name: "Song", label: 'Song'},
			{name: "Section", label: 'Section'},
			{name: "Events", label: 'Events'},
			{name: "Note", label: 'Note'},
			{name: "Char", label: 'Char'}
		];

		UI_box = new FlxUITabMenu(null, tabs, true);

		UI_box.resize(300, 400);
		UI_box.x = FlxG.width * (3 / 4);
		UI_box.y = 20;
		add(UI_box);

		noteTypeText = new FlxText(FlxG.width / 2, FlxG.height, 0, "<(I) Normal Note (O)>", 16);
		noteTypeText.y -= noteTypeText.height;
		noteTypeText.scrollFactor.set();
		add(noteTypeText);

		addSongUI();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_song_panel');
		addSectionUI();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_section_panel');
		addEventUI();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_event_panel');
		addNoteUI();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_note_panel');
		addCharsUI();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_char_panel');

		add(curRenderedNotes);
		add(curRenderedSustains);
		add(curRenderedEvents);

		RuntimeSmokeHarness.markChartEditorCreatePhase('before_change_section');
		changeSection(curSection);
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_change_section');

		super.create();
		RuntimeSmokeHarness.markChartEditorCreatePhase('after_super_create');
		// A real Quick Save/Load is triggered by an editor update, after create
		// returns to Flixel. Resetting the state recursively inside create can
		// leave the old grid/atlas lifecycle unfinished in native builds.
		chartEditorSmokePending = RuntimeSmokeHarness.chartEditorSmokeEnabled();
	}

	/** Exercise the real event editor controls and Quick Save reload in an
	 * isolated native smoke process only. */
	function runChartEditorRoundTripSmoke():Void {
		try {
			var request = RuntimeSmokeHarness.config();
			var expectedFolder = request.songFolder.toLowerCase();
			var expectedChart = request.chart.toLowerCase();
			var storageFolder = Song.storageFolder(_song);
			var loadedChart:Dynamic = Reflect.field(_song, 'compatChartFileName');
			if (storageFolder != expectedFolder)
				throw 'loaded owner folder changed: expected ' + expectedFolder + ', got ' + storageFolder;
			if (loadedChart == null || Std.string(loadedChart).toLowerCase() != expectedChart)
				throw 'selected difficulty chart changed: expected ' + expectedChart + ', got ' + loadedChart;
			if (PlayState.storyDifficulty != DifficultyManager.getDiffNum(request.difficulty))
				throw 'selected difficulty changed before editor round-trip';
			var selectedChartPath = 'assets/data/' + storageFolder + '/' + expectedChart + '.json';
			var selectedChart:Dynamic = CoolUtil.parseJson(FNFAssets.getText(selectedChartPath));
			var selectedSong:Dynamic = Reflect.field(selectedChart, 'song');
			var sourceHasUnrouted = selectedSong != null && Reflect.hasField(selectedSong, 'vSliceUnroutedNotes');
			var loadedHasUnrouted = Reflect.hasField(_song, 'vSliceUnroutedNotes');
			var sourceUnroutedJson = sourceHasUnrouted ? comparableEditorJson(Reflect.field(selectedSong, 'vSliceUnroutedNotes')) : '';
			var loadedUnroutedJson = loadedHasUnrouted ? comparableEditorJson(Reflect.field(_song, 'vSliceUnroutedNotes')) : '';
			if (sourceHasUnrouted != loadedHasUnrouted
				|| (sourceHasUnrouted && sourceUnroutedJson != loadedUnroutedJson))
				throw 'selected chart raw unrouted notes changed during editor load or Quick Save reload: source='
					+ sourceUnroutedJson.substr(0, 240) + ' loaded=' + loadedUnroutedJson.substr(0, 240);

			var sidecarPath = 'assets/data/' + storageFolder + '/events.json';
			if (!FNFAssets.exists(sidecarPath))
				throw 'editor smoke companion sidecar is missing: ' + sidecarPath;
			var sidecar:Dynamic = CoolUtil.parseJson(FNFAssets.getText(sidecarPath));
			RuntimeSmokeHarness.markChartEditorLoaded({
				storageFolder: storageFolder,
				chart: loadedChart,
				difficulty: request.difficulty,
				unroutedNoteCount: sourceHasUnrouted ? (cast Reflect.field(_song, 'vSliceUnroutedNotes') : Array<Dynamic>).length : 0,
				eventCount: ChartEventModel.list(_song.events).length,
				reload: RuntimeSmokeHarness.chartEditorReloadExpected()
			});

			if (RuntimeSmokeHarness.chartEditorReloadExpected()) {
				var validation = RuntimeSmokeChartEditorCheck.validateRoundTrip(_song, sidecar);
				if (validation != '')
					throw validation;
				RuntimeSmokeHarness.markChartEditorRuntimeCollection({
					storageFolder: storageFolder,
					chart: loadedChart,
					status: 'edited event collected once; deleted event suppressed'
				});
				RuntimeSmokeHarness.markChartEditorReloadComplete(sidecarPath, {
					storageFolder: storageFolder,
					chart: loadedChart,
					difficulty: request.difficulty
				});
				return;
			}

			var initialValidation = RuntimeSmokeChartEditorCheck.validateLoaded(_song.events);
			if (initialValidation != '')
				throw initialValidation;
			var editReference = RuntimeSmokeChartEditorCheck.uniqueEditorEvent(_song.events,
				RuntimeSmokeChartEditorCheck.SOURCE_EDIT);
			var deleteReference = RuntimeSmokeChartEditorCheck.uniqueEditorEvent(_song.events,
				RuntimeSmokeChartEditorCheck.SOURCE_DELETE);

			selectedChartEvent = Reflect.field(editReference, 'event');
			chartEventTimeField.text = Std.string(RuntimeSmokeChartEditorCheck.EDITED_TIME);
			chartEventNameField.text = RuntimeSmokeChartEditorCheck.EDITED_NAME;
			chartEventValue1Field.text = RuntimeSmokeChartEditorCheck.EDITED_VALUE_1;
			chartEventValue2Field.text = RuntimeSmokeChartEditorCheck.EDITED_VALUE_2;
			chartEventValue3Field.text = RuntimeSmokeChartEditorCheck.EDITED_VALUE_3;
			saveSelectedChartEvent();
			selectedChartEvent = Reflect.field(deleteReference, 'event');
			deleteSelectedChartEvent();
			var editedValidation = RuntimeSmokeChartEditorCheck.validateRoundTrip(_song, sidecar);
			if (editedValidation != '')
				throw 'editor handlers failed before Quick Save: ' + editedValidation;
			RuntimeSmokeHarness.markChartEditorEdited({
				storageFolder: storageFolder,
				chart: loadedChart,
				editedEvent: RuntimeSmokeChartEditorCheck.EDITED_NAME,
				deletedEvent: RuntimeSmokeChartEditorCheck.SOURCE_DELETE
			});
			RuntimeSmokeHarness.markChartEditorQuickSave(sidecarPath, {
				storageFolder: storageFolder,
				chart: loadedChart
			});
			autosaveSong();
			loadAutosave();
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('chart-editor', Std.string(error));
		}
	}

	/** Ignore object field iteration order when comparing authored JSON through
	 * the native editor's load, autosave and reload paths. */
	static function comparableEditorJson(value:Dynamic):String {
		if (Std.isOfType(value, Array)) {
			var items:Array<Dynamic> = cast value;
			return '[' + items.map(comparableEditorJson).join(',') + ']';
		}
		if (value != null && Reflect.isObject(value) && !Std.isOfType(value, String)) {
			var fields = Reflect.fields(value);
			fields.sort(function(a, b) return Reflect.compare(a, b));
			return '{' + fields.map(function(field) return Json.stringify(field) + ':'
				+ comparableEditorJson(Reflect.field(value, field))).join(',') + '}';
		}
		return Json.stringify(value);
	}

	function addSongUI():Void {
		var UI_songTitle = new FlxUIInputText(10, 10, 70, _song.song, 8);
		typingShit = UI_songTitle;

		var check_voices = new FlxUICheckBox(10, 30, null, null, "Has voice track", 100);
		check_voices.checked = _song.needsVoices;
		check_voices.callback = function() {
			_song.needsVoices = check_voices.checked;
			trace('CHECKED!');
		};

		var check_mute_inst = new FlxUICheckBox(10, 200, null, null, "Mute Instrumental (in editor)", 100);
		check_mute_inst.checked = false;
		check_mute_inst.callback = function() {
			var vol:Float = 1;

			if (check_mute_inst.checked)
				vol = 0;

			FlxG.sound.music.volume = vol;
		};

		var saveButton:FlxButton = new FlxButton(110, 8, "Save", function() {
			//saveLevel();
			saveLevelTo();
		});

		/*var saveToButton:FlxButton = new FlxButton(110, 38, "Save As", function() {
			saveLevelTo();
		});*/

		var eventButton:FlxButton = new FlxButton(10, 250, "Events to Hscript", function() {
			psychEventsToHScript();
		});

		var reloadSong:FlxButton = new FlxButton(saveButton.x + saveButton.width + 10, saveButton.y, "Reload Audio", function() {
			loadSong(_song.song);
		});

		var reloadSongJson:FlxButton = new FlxButton(reloadSong.x, saveButton.y + 30, "Reload JSON", function() {
			loadJson(editorChartFileName());
		});
		var saveAutosaveBtn:FlxButton = new FlxButton(saveButton.x, saveButton.y + 30, 'Quick Save', autosaveSong);
		var loadAutosaveBtn:FlxButton = new FlxButton(reloadSongJson.x, reloadSongJson.y + 30, 'Load Autosave', loadAutosave);

		var stepperSpeed:FlxUINumericStepper = new FlxUINumericStepper(10, 80, 0.1, 1, 0.1, 10, 1);
		stepperSpeed.value = _song.speed;
		stepperSpeed.name = 'song_speed';

		var stepperBPM:FlxUINumericStepper = new FlxUINumericStepper(10, 65, 1, 1, 1, 339, 0);
		stepperBPM.value = Conductor.bpm;
		stepperBPM.name = 'song_bpm';

		var stepperNotes:FlxUINumericStepper = new FlxUINumericStepper(10, 95, 1, 4, 1, 9, 0);
		stepperNotes.value = _song.preferredNoteAmount;
		stepperNotes.name = 'song_notes';

		var hitsounds = new FlxUICheckBox(10, 300, null, null, "Play hitsounds", 100); //stole this because charting is a pain without it lol
		hitsounds.checked = false;
		hitsounds.callback = function() {
			playClaps = hitsounds.checked;
		};

		var isHeyCheck = new FlxUICheckBox(10, 150, null, null, "Is Hey", 65);
		var isCheerCheck = new FlxUICheckBox(100, 150, null, null, "Is Cheer", 65);
		var isMoodyCheck = new FlxUICheckBox(10, 170, null, null, "Is Moody", 65);
		var isSpookyCheck = new FlxUICheckBox(100, 170, null, null, "Is Spooky", 65);
		isHeyCheck.name = "isHey";
		isCheerCheck.name = "isCheer";
		isMoodyCheck.name = "isMoody";
		isSpookyCheck.name = 'isSpooky';
		isHeyCheck.checked = _song.isHey;
		isCheerCheck.checked = _song.isCheer;
		isMoodyCheck.checked = _song.isMoody;
		isSpookyCheck.checked = _song.isSpooky;

		var tab_group_song = new FlxUI(null, UI_box);
		tab_group_song.name = "Song";
		tab_group_song.add(UI_songTitle);
		
		tab_group_song.add(check_voices);
		tab_group_song.add(check_mute_inst);
		tab_group_song.add(isMoodyCheck);
		tab_group_song.add(isSpookyCheck);
		tab_group_song.add(isHeyCheck);
		tab_group_song.add(isCheerCheck);
		tab_group_song.add(saveButton);
		//tab_group_song.add(saveToButton);
		tab_group_song.add(eventButton);
		tab_group_song.add(reloadSong);
		tab_group_song.add(reloadSongJson);
		tab_group_song.add(saveAutosaveBtn);
		tab_group_song.add(loadAutosaveBtn);
		tab_group_song.add(stepperBPM);
		tab_group_song.add(stepperSpeed);
		tab_group_song.add(stepperNotes);
		tab_group_song.add(hitsounds);

		UI_box.addGroup(tab_group_song);
		UI_box.scrollFactor.set();

		FlxG.camera.follow(strumLine);
	}

	function addCharsUI():Void {
		player1TextField = new FlxUIInputText(10, 100, 70, _song.player1, 8);
		gfTextField = new FlxUIInputText(10, 140, 70, _song.gf, 8);
		uiTextField = new FlxUIInputText(10, 180, 70, _song.uiType, 8);
		layoutTextField = new FlxUIInputText(10, 220, 70, _song.forceLayout, 8);

		player2TextField = new FlxUIInputText(120, 100, 70, _song.player2, 8);
		stageTextField = new FlxUIInputText(120, 140, 70, _song.stage, 8);
		stageID = new FlxUINumericStepper(120, 180, 1, _song.stageID, 0, 999, 0);
		cutsceneTextField = new FlxUIInputText(120, 220, 70, _song.cutsceneType, 8);
		
		var playerText = new FlxText(player1TextField.x + 70, player1TextField.y, 0, "Player", 8, false);
		var gfText = new FlxText(gfTextField.x + 70, gfTextField.y, 0, "GF", 8, false);
		var uiText = new FlxText(uiTextField.x + 70, uiTextField.y, 0, "UI", 8, false);
		var layoutText = new FlxText(layoutTextField.x + 70, layoutTextField.y, 0, "Layout", 8, false);

		var enemyText = new FlxText(player2TextField.x + 70, player2TextField.y, 0, "Enemy", 8, false);
		var stageText = new FlxText(stageTextField.x + 70, stageTextField.y, 0, "Stage", 8, false);
		var stageIDText = new FlxText(stageID.x + 70, stageID.y, 0, "Stage ID", 8, false);
		var cutsceneText = new FlxText(cutsceneTextField.x + 70, cutsceneTextField.y, 0, "Cutscene", 8, false);

		var player1Button:FlxButton = new FlxButton(10, 115, "Browse", function() {
			doCharDropdown('bf');
		});
		var player2Button:FlxButton = new FlxButton(120, 115, "Browse", function() {
			doCharDropdown('dad');
		});
		var gfButton:FlxButton = new FlxButton(10, 155, "Browse", function() {
			doCharDropdown('gf');
		});
		var stageButton:FlxButton = new FlxButton(120, 155, "Browse", function() {
			doCharDropdown('stage');
		});

		var tab_group_char = new FlxUI(null, UI_box);
		tab_group_char.name = "Char";

		tab_group_char.add(playerText);
		tab_group_char.add(enemyText);
		tab_group_char.add(gfText);
		tab_group_char.add(stageText);
		tab_group_char.add(cutsceneText);
		tab_group_char.add(layoutText);
		tab_group_char.add(layoutTextField);
		tab_group_char.add(uiText);
		tab_group_char.add(uiTextField);
		tab_group_char.add(cutsceneTextField);
		tab_group_char.add(stageTextField);
		tab_group_char.add(stageID);
		tab_group_char.add(stageIDText);
		tab_group_char.add(gfTextField);
		tab_group_char.add(player1TextField);
		tab_group_char.add(player2TextField);
		tab_group_char.add(player1Button);
		tab_group_char.add(player2Button);
		tab_group_char.add(gfButton);
		tab_group_char.add(stageButton);

		UI_box.addGroup(tab_group_char);
		UI_box.scrollFactor.set();
	}

	function doCharDropdown(dropType:String = 'bf') {
		if (charDropdown == null) {
			charDropdown = new ChartCharDropdown(450, 150, dropType);
			charDropdown.scrollFactor.set();
		} else
			charDropdown.charType = dropType;
		add(charDropdown);
	}

	var stepperLength:FlxUINumericStepper;
	var stepperAltAnim:FlxUINumericStepper;
	var check_mustHitSection:FlxUICheckBox;
	var check_changeBPM:FlxUICheckBox;
	var stepperSectionBPM:FlxUINumericStepper;
	var check_altAnim:FlxUICheckBox;

	function addSectionUI():Void {
		var tab_group_section = new FlxUI(null, UI_box);
		tab_group_section.name = 'Section';

		stepperLength = new FlxUINumericStepper(10, 10, 4, 0, 0, 999, 0);
		stepperLength.value = _song.notes[curSection].lengthInSteps;
		stepperLength.name = "section_length";

		stepperSectionBPM = new FlxUINumericStepper(10, 80, 1, Conductor.bpm, 0, 999, 0);
		stepperSectionBPM.value = Conductor.bpm;
		stepperSectionBPM.name = 'section_bpm';

		var sectionText = new FlxText(160, 10, 0, "Section Number", 8, false);

		stepperSection = new FlxUINumericStepper(160, 30, 1, 0, -999, 999, 0);
		var sectionButton:FlxButton = new FlxButton(160, 50, "Go to", function() {
			if (Std.int(stepperSection.value) >= 0)
				changeSection(Std.int(stepperSection.value));
		});
		var copyLastButton:FlxButton = new FlxButton(160, 70, "Copy last section", function() {
			if (Std.int(stepperSection.value) != 0)
				copySection(Std.int(stepperSection.value));
		});

		var check_lockSec = new FlxUICheckBox(160, 100, null, null, "Lock Section", 100);
		check_lockSec.checked = false;
		check_lockSec.callback = function() {
			copySecLock = check_lockSec.checked;
		};

		var clearSectionButton:FlxButton = new FlxButton(10, 100, "Clear", clearSection);

		var swapSection:FlxButton = new FlxButton(10, 120, "Swap section", function() {
			for (i in 0..._song.notes[curSection].sectionNotes.length) {
				var note = _song.notes[curSection].sectionNotes[i];
				var baseNote = (note[1] + _song.preferredNoteAmount) % (_song.preferredNoteAmount * 2);
				var specialValue = note[1] - ((baseNote + _song.preferredNoteAmount) % (_song.preferredNoteAmount * 2)); //lol
				if (specialValue < 0)
					specialValue = 0;
				note[1] = baseNote + specialValue;
				updateGrid();
			}
		});

		// sonic.exe triple trouble 4k converter because lol
		// imagine not having 5k lol
		/*var funnyButton:FlxButton = new FlxButton(10, 300, "Triple Trouble", function() {
			for (i in 0..._song.notes[curSection].sectionNotes.length) {
				var note = _song.notes[curSection].sectionNotes[i];
				switch(note[1]) {
					case 2|7:
						note[1] = -1; // these are the ring notes
					case 3|4|5|6:
						note[1] -= 1;
					case 8|9:
						note[1] -= 2;
				}
				switch(note[3]) {
					case 2: //static
						note[1] += 48;
					case 3: //phantom
						note[1] += 40;
				}
				note[3] = 0;
				note[4] = 0;
				updateGrid();
			}
		});*/

		check_mustHitSection = new FlxUICheckBox(10, 30, null, null, "Must hit section", 100);
		check_mustHitSection.name = 'check_mustHit';
		check_mustHitSection.checked = true;

		check_altAnim = new FlxUICheckBox(10, 150, null, null, "Alt Animation", 100);
		check_altAnim.name = 'check_altAnim';

		stepperAltAnim = new FlxUINumericStepper(10, 170, 1, Conductor.bpm, 0, 999, 0);
		stepperAltAnim.value = 0;
		stepperAltAnim.name = 'alt_anim_number';

		check_changeBPM = new FlxUICheckBox(10, 60, null, null, 'Change BPM', 100);
		check_changeBPM.name = 'check_changeBPM';

		var showSections = new FlxUICheckBox(10, 250, null, null, "Show prev/next section", 100);
		showSections.checked = true;
		showSections.callback = function() {
			showPrevNext = showSections.checked;
			updateGrid();
		};

		tab_group_section.add(stepperLength);
		tab_group_section.add(stepperSectionBPM);
		tab_group_section.add(check_mustHitSection);
		tab_group_section.add(check_altAnim);
		tab_group_section.add(stepperAltAnim);
		tab_group_section.add(check_changeBPM);
		tab_group_section.add(sectionText);
		tab_group_section.add(stepperSection);
		tab_group_section.add(check_lockSec);
		tab_group_section.add(sectionButton);
		tab_group_section.add(copyLastButton);
		tab_group_section.add(clearSectionButton);
		tab_group_section.add(swapSection);
		//tab_group_section.add(funnyButton);
		tab_group_section.add(showSections);

		UI_box.addGroup(tab_group_section);
	}

	var stepperSusLength:FlxUINumericStepper;
	var stepperAltNote:FlxUINumericStepper;
	var roundStrumTimeButton:FlxButton;
	var rawNoteTxt:FlxText;
	function addNoteUI():Void {
		var tab_group_note = new FlxUI(null, UI_box);
		tab_group_note.name = 'Note';

		var lengthTxt = new FlxText(10, 10, 0, 'Note Length', 8, false);
		stepperSusLength = new FlxUINumericStepper(10, 30, Conductor.stepCrochet / 2, 0, 0, Conductor.stepCrochet * 16);
		stepperSusLength.value = 0;
		stepperSusLength.name = 'note_susLength';

		isAltNoteCheck = new FlxUICheckBox(10, 70, null, null, "Alt Anim Note", 100);
		isAltNoteCheck.name = "isAltNote";
		stepperAltNote = new FlxUINumericStepper(10, 90, 1, 0, 0, 999, 0);
		stepperAltNote.value = 0;
		stepperAltNote.name = 'alt_anim_note';

		var roundStrumTimeButton:FlxButton = new FlxButton(10, 200, "Round Strum Time", function() {
			if (curSelectedNote == null) return;
			curSelectedNote[0] = Math.round(curSelectedNote[0]);
			updateNoteUI();
			updateGrid();
		});

		var noteTypeButton:FlxButton = new FlxButton(10, 130, "Change Type", function() {
			if (curSelectedNote == null) return;
			curSelectedNote[1] %= _song.preferredNoteAmount * 2; // this looks so strange but it works
			switch (noteType) {
				case Mine: 
					curSelectedNote[1] += _song.preferredNoteAmount * 2;
				case Lift: 
					curSelectedNote[1] += _song.preferredNoteAmount * 4;
				case Death: 
					curSelectedNote[1] += _song.preferredNoteAmount * 6;
				case 4:
					// drained
				case key: 
					curSelectedNote[1] += _song.preferredNoteAmount * 2 * key;
			}
			updateNoteUI();
			updateGrid();
		});

		rawNoteTxt = new FlxText(10, 180, 0, '[]', 10, false);

		tab_group_note.add(lengthTxt);
		tab_group_note.add(stepperSusLength);
		tab_group_note.add(isAltNoteCheck);
		tab_group_note.add(stepperAltNote);
		tab_group_note.add(roundStrumTimeButton);
		tab_group_note.add(noteTypeButton);
		tab_group_note.add(rawNoteTxt);
		UI_box.addGroup(tab_group_note);
	}

	function addEventUI():Void {
		var tab_group_events = new FlxUI(null, UI_box);
		tab_group_events.name = 'Events';

		tab_group_events.add(new FlxText(10, 10, 0, 'Timestamp (ms)', 8, false));
		chartEventTimeField = new FlxUIInputText(10, 27, 125, '0', 8);
		tab_group_events.add(chartEventTimeField);

		tab_group_events.add(new FlxText(10, 56, 0, 'Event name', 8, false));
		chartEventNameField = new FlxUIInputText(10, 73, 265, 'Focus Camera', 8);
		tab_group_events.add(chartEventNameField);

		tab_group_events.add(new FlxText(10, 102, 0, 'Value 1', 8, false));
		chartEventValue1Field = new FlxUIInputText(10, 119, 265, '', 8);
		tab_group_events.add(chartEventValue1Field);

		tab_group_events.add(new FlxText(10, 148, 0, 'Value 2', 8, false));
		chartEventValue2Field = new FlxUIInputText(10, 165, 265, '', 8);
		tab_group_events.add(chartEventValue2Field);

		tab_group_events.add(new FlxText(10, 194, 0, 'Value 3', 8, false));
		chartEventValue3Field = new FlxUIInputText(10, 211, 265, '', 8);
		tab_group_events.add(chartEventValue3Field);

		var previousEvent = new FlxButton(10, 245, 'Previous', function() {
			selectChartEvent(-1);
		});
		var nextEvent = new FlxButton(105, 245, 'Next', function() {
			selectChartEvent(1);
		});
		chartEventSelectionText = new FlxText(10, 273, 260, 'No events', 8, false);
		tab_group_events.add(previousEvent);
		tab_group_events.add(nextEvent);
		tab_group_events.add(chartEventSelectionText);

		var addEvent = new FlxButton(10, 300, 'Add at playhead', addChartEventAtPlayhead);
		var saveEvent = new FlxButton(10, 330, 'Save Event', saveSelectedChartEvent);
		var deleteEvent = new FlxButton(150, 330, 'Delete Event', deleteSelectedChartEvent);
		tab_group_events.add(addEvent);
		tab_group_events.add(saveEvent);
		tab_group_events.add(deleteEvent);
		UI_box.addGroup(tab_group_events);
		refreshChartEventEditor();
	}

	function chartEventReferences():Array<Dynamic> {
		return ChartEventModel.list(_song.events);
	}

	function refreshChartEventEditor():Void {
		if (chartEventTimeField == null)
			return;
		var entries = chartEventReferences();
		var selectedIndex = -1;
		if (selectedChartEvent != null) {
			for (index in 0...entries.length) {
				if (Reflect.field(entries[index], 'event') == selectedChartEvent) {
					selectedIndex = index;
					break;
				}
			}
		}

		if (selectedIndex < 0 && entries.length > 0) {
			selectedIndex = 0;
			selectedChartEvent = Reflect.field(entries[0], 'event');
		}
		if (selectedIndex < 0) {
			selectedChartEvent = null;
			chartEventTimeField.text = '';
			chartEventNameField.text = 'Focus Camera';
			chartEventValue1Field.text = '';
			chartEventValue2Field.text = '';
			chartEventValue3Field.text = '';
			chartEventSelectionText.text = 'No events (0)';
			return;
		}

		var reference:Dynamic = entries[selectedIndex];
		var group:Array<Dynamic> = cast Reflect.field(reference, 'group');
		var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
		chartEventTimeField.text = Std.string(group[0]);
		chartEventNameField.text = event[0] == null ? '' : Std.string(event[0]);
		chartEventValue1Field.text = event.length > 1 && event[1] != null ? Std.string(event[1]) : '';
		chartEventValue2Field.text = event.length > 2 && event[2] != null ? Std.string(event[2]) : '';
		chartEventValue3Field.text = event.length > 3 && event[3] != null ? Std.string(event[3]) : '';
		chartEventSelectionText.text = 'Event ' + (selectedIndex + 1) + ' of ' + entries.length;
	}

	function selectChartEvent(direction:Int):Void {
		var entries = chartEventReferences();
		if (entries.length == 0)
			return;
		var current = 0;
		for (index in 0...entries.length)
			if (Reflect.field(entries[index], 'event') == selectedChartEvent) {
				current = index;
				break;
			}
		current = (current + direction + entries.length) % entries.length;
		selectedChartEvent = Reflect.field(entries[current], 'event');
		refreshChartEventEditor();
		jumpToChartEvent(entries[current]);
	}

	function jumpToChartEvent(reference:Dynamic):Void {
		if (reference == null || FlxG.sound.music == null)
			return;
		var time:Float = Math.max(0, Reflect.field(reference, 'time'));
		// Imported events can extend past the last authored note section.
		while (_song.notes.length < 4096
			&& time >= ChartEventModel.sectionStart(cast _song.notes, _song.bpm, _song.notes.length))
			addSection();
		var section = ChartEventModel.sectionAtTime(cast _song.notes, _song.bpm, time);
		FlxG.sound.music.pause();
		FlxG.sound.music.time = time;
		if (_song.needsVoices && vocals != null) {
			pauseEditorVocals();
			seekEditorVocals(time);
		}
		Conductor.songPosition = time;
		if (section != curSection)
			changeSection(section, false);
		else
			updateGrid();
		updateCurStep();
	}

	function addChartEventAtPlayhead():Void {
		if (StringTools.trim(chartEventNameField.text) == '')
			return;
		var created = ChartEventModel.add(_song.events, Conductor.songPosition,
			chartEventNameField.text, chartEventValue1Field.text,
			chartEventValue2Field.text, chartEventValue3Field.text);
		_song.events = Reflect.field(created, 'groups');
		selectedChartEvent = Reflect.field(created, 'event');
		refreshChartEventEditor();
		updateGrid();
	}

	function saveSelectedChartEvent():Void {
		if (selectedChartEvent == null)
			return;
		var timestamp = Std.parseFloat(StringTools.trim(chartEventTimeField.text));
		if (Math.isNaN(timestamp))
			return;
		var reference:Dynamic = null;
		for (entry in chartEventReferences())
			if (Reflect.field(entry, 'event') == selectedChartEvent) {
				reference = entry;
				break;
			}
		if (ChartEventModel.update(_song.events, reference, timestamp,
			chartEventNameField.text, chartEventValue1Field.text,
			chartEventValue2Field.text, chartEventValue3Field.text)) {
			refreshChartEventEditor();
			updateGrid();
		}
	}

	function deleteSelectedChartEvent():Void {
		if (selectedChartEvent == null)
			return;
		var reference:Dynamic = null;
		for (entry in chartEventReferences())
			if (Reflect.field(entry, 'event') == selectedChartEvent) {
				reference = entry;
				break;
			}
		if (ChartEventModel.removeSongEvent(_song, reference)) {
			selectedChartEvent = null;
			refreshChartEventEditor();
			updateGrid();
		}
	}

	function changeKeyType(change:Int) {
		noteType += change;
		noteType = cast FlxMath.wrap(noteType, 0, 99);
		noteTypeText.text = '<[I] ';
		switch (noteType) {
			case Normal:
				noteTypeText.text += "Normal Note";
			case Lift:
				noteTypeText.text += "Lift Note";
			case Mine:
				noteTypeText.text += "Mine Note";
			case Death:
				noteTypeText.text += "Death Note";
			case 4: // drain
				noteTypeText.text += "Drain Note";
			default:
				var noteChecked = false;
				if (FileSystem.exists('assets/data/${Song.storageFolder(_song)}/noteInfo.json')) {
					var noteJson = CoolUtil.parseJson(FNFAssets.getText('assets/data/${Song.storageFolder(_song)}/noteInfo.json'));
					if ((noteType - 4) - 1 < noteJson.length) {
						var thingie = noteJson[(noteType - 4) - 1];
						if (thingie.noteName != null) {
							noteTypeText.text += thingie.noteName + ' (${noteType - 4})';
							noteChecked = true;
						}
					} 
				}
				if (!noteChecked)
					noteTypeText.text += 'Custom Note ${noteType - 4}';
				// made it better lol
		}
		noteTypeText.text += ' [O]>';
	}

	function loadSong(daSong:String):Void {
		var audioFolder = Song.storageFolder(_song);
		destroyEditorVocals();
		if (FlxG.sound.music != null) {
			FlxG.sound.music.stop();
		}
		#if sys
		var inst;
		if (OptionsHandler.options.stressTankmen)
			inst = CoolUtil.getSongFile(_song.song + "Shit", "assets/songs/" + audioFolder + '/');

		inst = CoolUtil.getSongFile(_song.song, "assets/songs/" + audioFolder + '/', true, '-' + DifficultyManager.getDefaultForDiff(PlayState.storyDifficulty));

		if (inst == null)
			inst = CoolUtil.getSongFile(_song.song, "assets/songs/" + audioFolder + '/');

		FlxG.sound.playMusic(SongAudioNormalizer.prepare(Sound.fromFile(inst), inst,
			OptionsHandler.options.normalizeSongAudio), 0.6);
		#else
		FlxG.sound.playMusic('assets/songs/' + audioFolder + '/' + daSong + "_Inst" + TitleState.soundExt, 0.6);
		#end
		if (_song.needsVoices) {
			var vocalPaths:Array<String> = [];
			if (_song.vocalStems != null)
				for (entry in _song.vocalStems) {
					if (entry == null) continue;
					var file:Dynamic = Std.isOfType(entry, String) ? entry : Reflect.field(entry, 'file');
					if (file == null && !Std.isOfType(entry, String))
						file = Reflect.field(entry, 'path');
					if (file == null) continue;
					var clean = StringTools.replace(StringTools.trim(Std.string(file)), '\\', '/');
					var path = clean.toLowerCase().startsWith('assets/') ? clean
						: 'assets/songs/' + audioFolder + '/' + haxe.io.Path.withoutDirectory(clean);
					if (!FNFAssets.exists(path)) continue;
					var duplicate = false;
					for (index in 0...vocalPaths.length)
						if (VocalStemSelection.sameStem(vocalPaths[index], path)) {
							if (VocalStemSelection.prefer(path, vocalPaths[index], TitleState.soundExt))
								vocalPaths[index] = path;
							duplicate = true;
							break;
						}
					if (!duplicate)
						vocalPaths.push(path);
				}
			#if sys
			if (vocalPaths.length == 0) {
				var vocalSound = CoolUtil.getSongFile(_song.song,
					'assets/songs/' + audioFolder + '/', false,
					'-' + DifficultyManager.getDefaultForDiff(PlayState.storyDifficulty));
				if (vocalSound == null)
					vocalSound = CoolUtil.getSongFile(_song.song, 'assets/songs/' + audioFolder + '/', false);
				if (vocalSound != null)
					vocalPaths.push(vocalSound);
			}
			#else
			if (vocalPaths.length == 0)
				vocalPaths.push('assets/songs/' + audioFolder + '/' + daSong + '_Voices' + TitleState.soundExt);
			#end
			for (path in vocalPaths) try {
				var track = new FlxSound().loadEmbedded(SongAudioNormalizer.prepare(
					FNFAssets.getSound(path), path, OptionsHandler.options.normalizeSongAudio));
				if (editorVocalTracks == null) {
					vocals = track;
					editorVocalTracks = new VocalTracks(track);
				} else
					editorVocalTracks.add(track);
				FlxG.sound.list.add(track);
			} catch (error:Dynamic) {
				trace('[chart-editor-vocal-error] ' + path + ': ' + error);
			}
		}

		FlxG.sound.music.pause();
		pauseEditorVocals();

		FlxG.sound.music.onComplete = function() {
			pauseEditorVocals();
			seekEditorVocals(0);

			FlxG.sound.music.pause();
			FlxG.sound.music.time = 0;
			changeSection();
		};
	}

	function generateUI():Void {
		while (bullshitUI.members.length > 0)
			bullshitUI.remove(bullshitUI.members[0], true);

		// general shit
		var title:FlxText = new FlxText(UI_box.x + 20, UI_box.y + 20, 0);
		bullshitUI.add(title);
		/*
			var loopCheck = new FlxUICheckBox(UI_box.x + 10, UI_box.y + 50, null, null, "Loops", 100, ['loop check']);
			loopCheck.checked = curNoteSelected.doesLoop;
			tooltips.add(loopCheck, {title: 'Section looping', body: "Whether or not it's a simon says style section", style: tooltipType});
			bullshitUI.add(loopCheck);
		 */
	}

	override function getEvent(id:String, sender:Dynamic, data:Dynamic, ?params:Array<Dynamic>) {
		if (id == FlxUICheckBox.CLICK_EVENT) {
			var check:FlxUICheckBox = cast sender;
			var label = check.getLabel().text;
			switch (label) {
				case 'Must hit section':
					_song.notes[curSection].mustHitSection = check.checked;
					updateHeads();
				case 'Change BPM':
					_song.notes[curSection].changeBPM = check.checked;
					FlxG.log.add('changed bpm shit');
				case "Alt Animation":
					_song.notes[curSection].altAnim = check.checked;
					if (_song.notes[curSection].altAnim && _song.notes[curSection].altAnimNum == 0)
						_song.notes[curSection].altAnimNum = 1;
					else if (!_song.notes[curSection].altAnim)
						_song.notes[curSection].altAnimNum = 0;
					updateSectionUI();
				case "Is Moody":
					_song.isMoody = check.checked;
				case "Is Spooky":
					_song.isSpooky = check.checked;
				case "Is Hey":
					_song.isHey = check.checked;
				case 'Alt Anim Note':
					if (curSelectedNote != null)
						curSelectedNote[3] = check.checked ? 1 : 0;
					updateNoteUI();
				case 'Is Cheer':
					_song.isCheer = check.checked;
			}
		} else if (id == FlxUINumericStepper.CHANGE_EVENT && (sender is FlxUINumericStepper)) {
			var nums:FlxUINumericStepper = cast sender;
			var wname = nums.name;
			FlxG.log.add(wname);
			switch(wname) {
				case 'section_length':
					_song.notes[curSection].lengthInSteps = Std.int(nums.value);
					updateGrid();
				case 'song_speed':
					_song.speed = nums.value;
				case 'song_bpm':
					tempBpm = nums.value;
					Conductor.mapBPMChanges(_song);
					Conductor.changeBPM(nums.value);
				case 'song_notes':
					_song.preferredNoteAmount = Std.int(nums.value);
					updateGrid();
					updateHeads();
				case 'note_susLength':
					curSelectedNote[2] = nums.value;
					updateGrid();
				case 'section_bpm':
					_song.notes[curSection].bpm = nums.value;
					updateGrid();
				case 'alt_anim_number':
					_song.notes[curSection].altAnimNum = Std.int(nums.value); 
					_song.notes[curSection].altAnim = _song.notes[curSection].altAnimNum == 0 ? false : true;
					updateSectionUI();
				case 'alt_anim_note':
					if (curSelectedNote != null)
						curSelectedNote[3] = nums.value;
					updateNoteUI();
			}
		}

		// FlxG.log.add(id + " WEED " + sender + " WEED " + data + " WEED " + params);
	}

	var updatedSection:Bool = false;

	/* this function got owned LOL
	function lengthBpmBullshit():Float
	{
		if (_song.notes[curSection].changeBPM)
			return _song.notes[curSection].lengthInSteps * (_song.notes[curSection].bpm / _song.bpm);
		else
			return _song.notes[curSection].lengthInSteps;
	}*/

	function sectionStartTime(?offset:Int = 0):Float {
		var daBPM:Float = _song.bpm;
		var daPos:Float = 0;
		for (i in 0...curSection + offset) {
			if (_song.notes[i].changeBPM) {
				daBPM = _song.notes[i].bpm;
			}
			if (_song.notes[i].lengthInSteps <= 0) _song.notes[i].lengthInSteps = 16;
			daPos += (_song.notes[i].lengthInSteps / 4) * (1000 * 60 / daBPM);
		}
		return daPos;
	}

	function sectionStartStep(?offset:Int = 0):Int {
		var daSteps:Int = 0;
		var heyguesswhatthisisnull:Null<Int> = null; // im going to go insane
		for (i in 0...curSection + offset) {
			if (_song.notes[i].lengthInSteps <= 0 || _song.notes[i].lengthInSteps == heyguesswhatthisisnull) _song.notes[i].lengthInSteps = 16;
			daSteps += _song.notes[i].lengthInSteps;
		}
		return daSteps;
	}

	/*function checkForBads() { // like spell check but for charts
		_song.notes.forEach(function(note:EdtNote) {
			_song.notes.forEach(function(checknote:EdtNote) {
				if (note[0] == checknote[0] && note[1] == checknote[1])
					_song.notes[curSection].sectionNotes.remove();
			});
		});
	}*/

	override function update(elapsed:Float) {
		if (chartEditorSmokePending) {
			chartEditorSmokePending = false;
			runChartEditorRoundTripSmoke();
			return;
		}
		curStep = recalculateSteps();

		Conductor.songPosition = FlxG.sound.music.time;
		_song.song = typingShit.text;
		if (settingVars) {
			player1TextField.text = _song.player1;
			player2TextField.text = _song.player2;
			gfTextField.text = _song.gf;
			stageTextField.text = _song.stage;
			remove(charDropdown);
			settingVars = false;
		} else {
			_song.player1 = player1TextField.text;
			_song.player2 = player2TextField.text;
			_song.gf = gfTextField.text;
			if (_song.stage != stageTextField.text)
				Reflect.setField(_song, 'compatStageAuthored', true);
			_song.stage = stageTextField.text;
		}
		_song.stageID = Std.parseInt(Std.string(stageID.value)); // what
		_song.cutsceneType = cutsceneTextField.text;
		_song.uiType = uiTextField.text;
		_song.forceLayout = layoutTextField.text;
		strumLine.y = getYfromStrum((Conductor.songPosition - sectionStartTime()) % (Conductor.stepCrochet * _song.notes[curSection].lengthInSteps));

		if (playClaps) {
			curRenderedNotes.forEach(function(note:EdtNote) {
				if (FlxG.sound.music.playing) {
					FlxG.overlap(strumLine, note, function(_, _) {
						if(!claps.contains(note)) {
							claps.push(note);
							FlxG.sound.play('assets/sounds/hitSound.ogg');
						}
					});
				}
			});
		}

		if (curStep % 4 == 0 && curStep >= sectionStartStep(1)) {
			trace(curStep);
			trace((_song.notes[curSection].lengthInSteps) * (curSection + 1));
			trace('DUMBSHIT');

			if (_song.notes[curSection + 1] == null)
				addSection();

			changeSection(curSection + 1, false);
		} else if (curStep < sectionStartStep())
			changeSection(curSection - 1, false);

		if (FlxG.mouse.justPressed) {
			var clickedEvent = false;
			for (index in 0...renderedEventRefs.length) {
				if (FlxG.mouse.overlaps(curRenderedEvents.members[index])) {
					selectedChartEvent = Reflect.field(renderedEventRefs[index], 'event');
					refreshChartEventEditor();
					jumpToChartEvent(renderedEventRefs[index]);
					clickedEvent = true;
					break;
				}
			}
			if (clickedEvent) {
				// The event lane is for selection, never note placement.
			} else if (FlxG.mouse.overlaps(curRenderedNotes)) {
				curRenderedNotes.forEach(function(note:EdtNote) {
					if (FlxG.mouse.overlaps(note)) {
						deleteNote(note);
					}
				});
			} else {
				if (FlxG.mouse.x > gridBG.x
					&& FlxG.mouse.x < gridBG.x + gridBG.width
					&& FlxG.mouse.y > gridBG.y
					&& FlxG.mouse.y < gridBG.y + (GRID_SIZE * _song.notes[curSection].lengthInSteps * zoomFactor)) {
					FlxG.log.add('added note');
					addNote();
				}
			}
		}

		if (FlxG.mouse.justPressedRight) {
			if (FlxG.mouse.overlaps(curRenderedNotes)) {
				curRenderedNotes.forEach(function(note:EdtNote) {
					if (FlxG.mouse.overlaps(note)) {
						selectNote(note);
					}
				});
			}
		}

		if (FlxG.mouse.x > gridBG.x
			&& FlxG.mouse.x < gridBG.x + gridBG.width
			&& FlxG.mouse.y > gridBG.y
			&& FlxG.mouse.y < gridBG.y + (GRID_SIZE * _song.notes[curSection].lengthInSteps * zoomFactor))
		{
			dummyArrow.visible = true;
			dummyArrow.x = Math.floor(FlxG.mouse.x / GRID_SIZE) * GRID_SIZE;
			if (FlxG.keys.pressed.SHIFT)
				dummyArrow.y = FlxG.mouse.y;
			else {
				final snapFactor = GRID_SIZE * (16 / gridSnap);
				dummyArrow.y = Math.floor(FlxG.mouse.y / snapFactor) * snapFactor;
			}
		} else {
			dummyArrow.visible = false;
		}

		if (FlxG.keys.justPressed.ENTER && !chartEventInputsFocused()) {
			lastSection = curSection;

			if (FlxG.keys.pressed.SHIFT)
				PlayState.startingPosition = Conductor.songPosition;

			if (charDropdown != null)
				charDropdown.destroy();

			PlayState.SONG = _song;
			FlxG.sound.music.stop();
			if (_song.needsVoices)
				stopEditorVocals();
			FlxG.mouse.visible = false;
			autosaveSong();
			LoadingState.loadAndSwitchState(new PlayState());
		}

		if (!typingShit.hasFocus && !player1TextField.hasFocus 
		&& !player2TextField.hasFocus && !gfTextField.hasFocus 
		&& !stageTextField.hasFocus && !cutsceneTextField.hasFocus 
		&& !uiTextField.hasFocus && !chartEventInputsFocused()
		&& (charDropdown == null || !charDropdown.searchBox.hasFocus)) {
			if (FlxG.keys.justPressed.E) 
				changeNoteSustain(Conductor.stepCrochet);
			if (FlxG.keys.justPressed.Q)
				changeNoteSustain(-Conductor.stepCrochet);

			if (FlxG.keys.justPressed.TAB) {
				var tabDirection = FlxG.keys.pressed.SHIFT ? -1 : 1;
				UI_box.selected_tab = (UI_box.selected_tab + tabDirection + UI_box.numTabs) % UI_box.numTabs;
			}
			var shiftThing:Int = 1;
			if (FlxG.keys.justPressed.SPACE) {
				if (FlxG.sound.music.playing) {
					FlxG.sound.music.pause();
					if (_song.needsVoices) {
						pauseEditorVocals();
					}
					claps.splice(0, claps.length);
				} else {
					if (_song.needsVoices) {
						playEditorVocals();
					}
					FlxG.sound.music.play();
				}
			}

			if (FlxG.keys.justPressed.Z) {
				zoomFactor += 1;
				if (zoomFactor >= 4)
					zoomFactor = 3;
				updateGrid();
			}
			if (FlxG.keys.justPressed.X) {
				zoomFactor -= 1;
				if (zoomFactor <= 0)
					zoomFactor = 1;
				updateGrid();
			}

			if (FlxG.keys.justPressed.B) {
				if (FlxG.keys.pressed.SHIFT)
					gridSnap += 1;
				else {
					var milestone = snapMilestones.indexOf(gridSnap) + 1;
					gridSnap = milestone != 0 ? snapMilestones[milestone] : 4;
				}
				gridSnapTxt.text = "Grid Snap: " + gridSnap + "th";
			}
			if (FlxG.keys.justPressed.V) {
				if (FlxG.keys.pressed.SHIFT)
					gridSnap -= 1;
				else {
					var milestone = snapMilestones.indexOf(gridSnap) - 1;
					gridSnap = milestone != -2 ? snapMilestones[milestone] : 4;
				}
				if (gridSnap <= 0)
					gridSnap = 4;
				gridSnapTxt.text = "Grid Snap: " + gridSnap + "th";
			}

			if (FlxG.keys.justPressed.R) {
				if (FlxG.keys.pressed.SHIFT)
					resetSection(true);
				else
					resetSection();
			}

			if (FlxG.mouse.wheel != 0) {
				FlxG.sound.music.pause();
				if (_song.needsVoices) {
					pauseEditorVocals();
				}


				FlxG.sound.music.time -= (FlxG.mouse.wheel * Conductor.stepCrochet * 0.4);
				if (_song.needsVoices) {
					seekEditorVocals(FlxG.sound.music.time);
				}

			}
			if (FlxG.keys.justPressed.RIGHT || FlxG.keys.justPressed.D)
				changeSection(curSection + shiftThing);
			if (FlxG.keys.justPressed.LEFT || FlxG.keys.justPressed.A)
				changeSection(curSection - shiftThing);
			if (FlxG.keys.pressed.SHIFT)
				shiftThing = 4;
			if (!FlxG.keys.pressed.SHIFT) {
				if (FlxG.keys.pressed.W || FlxG.keys.pressed.S) {
					FlxG.sound.music.pause();
					if (_song.needsVoices) {
						pauseEditorVocals();
					}

					var daTime:Float = 700 * FlxG.elapsed;

					if (FlxG.keys.pressed.W) {
						FlxG.sound.music.time -= daTime;
					} else
						FlxG.sound.music.time += daTime;

					if (_song.needsVoices) {
						seekEditorVocals(FlxG.sound.music.time);
					}
				}
			} else {
				if (FlxG.keys.justPressed.W || FlxG.keys.justPressed.S) {
					FlxG.sound.music.pause();
					if (_song.needsVoices) {
						pauseEditorVocals();
					}

					var daTime:Float = Conductor.stepCrochet * 2;

					if (FlxG.keys.justPressed.W) {
						FlxG.sound.music.time -= daTime;
					} else
						FlxG.sound.music.time += daTime;

					if (_song.needsVoices) {
						seekEditorVocals(FlxG.sound.music.time);
					}
				}
			}

			/* if (FlxG.keys.justPressed.UP)
				Conductor.changeBPM(Conductor.bpm + 1);
				if (FlxG.keys.justPressed.DOWN)
					Conductor.changeBPM(Conductor.bpm - 1); */

			if (FlxG.keys.justPressed.I)
				changeKeyType(-1);
			else if (FlxG.keys.justPressed.O)
				changeKeyType(1);
		}

		_song.bpm = tempBpm;

		bpmTxt.text = Std.string(FlxMath.roundDecimal(Conductor.songPosition / 1000, 2))
			+ " / "
			+ Std.string(FlxMath.roundDecimal(FlxG.sound.music.length / 1000, 2))
			+ "\nSection: " + curSection
			+ '\ncurBeat: ' + Std.string(curBeat) 
			+ '\ncurStep: ' + Std.string(curStep);
		super.update(elapsed);
		RuntimeSmokeHarness.tick(elapsed);
	}

	function chartEventInputsFocused():Bool {
		return (chartEventTimeField != null && chartEventTimeField.hasFocus)
			|| (chartEventNameField != null && chartEventNameField.hasFocus)
			|| (chartEventValue1Field != null && chartEventValue1Field.hasFocus)
			|| (chartEventValue2Field != null && chartEventValue2Field.hasFocus)
			|| (chartEventValue3Field != null && chartEventValue3Field.hasFocus);
	}

	function changeNoteSustain(value:Float):Void {
		if (curSelectedNote != null) {
			if (curSelectedNote[2] != null) {
				curSelectedNote[2] += value;
				curSelectedNote[2] = Math.max(curSelectedNote[2], 0);
				if (curSelectedNote[2] < 1 && curSelectedNote.length == 3) curSelectedNote.pop();
			}
		}

		updateNoteUI();
		updateGrid();
	}
	function toggleNoteAnim():Void {
		if (curSelectedNote != null) {
			if (curSelectedNote[3] != null) {
				curSelectedNote[3] = curSelectedNote[3] == 1 ? 0 : 1;
			} else {
				curSelectedNote[3] = 1;
			}
		}
		updateNoteUI();
	}

	static var settingVars = false; // im either bad at coding or silly workarounds are just standard
	public static function setCharacter(char:String, charType:String = 'bf') {
		settingVars = true;
		switch(charType) {
			case 'bf':
				_song.player1 = char;
			case 'dad':
				_song.player2 = char;
			case 'gf':
				_song.gf = char;
			case 'stage':
				Reflect.setField(_song, 'compatStageAuthored', true);
				_song.stage = char;
		}
	}

	function recalculateSteps():Int {
		var lastChange:BPMChangeEvent = {
			stepTime: 0,
			songTime: 0,
			bpm: 0
		}
		for (i in 0...Conductor.bpmChangeMap.length) {
			if (FlxG.sound.music.time > Conductor.bpmChangeMap[i].songTime)
				lastChange = Conductor.bpmChangeMap[i];
		}

		curStep = lastChange.stepTime + Math.floor((FlxG.sound.music.time - lastChange.songTime) / Conductor.stepCrochet);
		updateBeat();

		return curStep;
	}

	function resetSection(songBeginning:Bool = false):Void {
		updateGrid();

		FlxG.sound.music.pause();
		if (_song.needsVoices) {
			pauseEditorVocals();
		}

		// Basically old shit from changeSection???
		FlxG.sound.music.time = sectionStartTime();

		if (songBeginning) {
			FlxG.sound.music.time = 0;
			curSection = 0;
		}
		if (_song.needsVoices) {
			seekEditorVocals(FlxG.sound.music.time);
		}

		updateCurStep();

		updateGrid();
		updateSectionUI();
	}

	function changeSection(sec:Int = 0, ?updateMusic:Bool = true):Void {
		trace('changing section' + sec);

		var oldSection = curSection;

		if (_song.notes[sec] != null) {
			curSection = sec;
			if (copySecLock) {
				stepperSection.value += curSection - oldSection;
			}

			if (updateMusic) {
				FlxG.sound.music.pause();
				if (_song.needsVoices) {
					pauseEditorVocals();
				}


				/*var daNum:Int = 0;
				var daLength:Float = 0;
				while (daNum <= sec)
				{
					daLength += lengthBpmBullshit();
					daNum++;
				}*/

				FlxG.sound.music.time = sectionStartTime() + 1;
				if (_song.needsVoices) {
					seekEditorVocals(FlxG.sound.music.time);
				}

				updateCurStep();
			}

			var pleasehelpme:Null<Int> = null; // I funking LOVE doing weird work arounds for ABSOLUTELY no reason (my favorite is currentKey and currrentKey in PlayState :)
			if (_song.notes[curSection].lengthInSteps == pleasehelpme)
				_song.notes[curSection].lengthInSteps = 16;

			var direction = oldSection > curSection ? 1 : -1;

			updateGrid();
			updateSectionUI();
			updateHeads(true, direction);
		}
	}

	function copySection(?sectionNum:Int = 1) {
		var daSec = FlxMath.maxInt(curSection, sectionNum);

		for (note in _song.notes[daSec - sectionNum].sectionNotes) {
			var strum = note[0] + Conductor.stepCrochet * (_song.notes[daSec].lengthInSteps * sectionNum);

			var copiedNote:Array<Dynamic> = ChartNoteRowCopy.withTimestamp(note, strum);
			_song.notes[daSec].sectionNotes.push(copiedNote);
		}

		updateGrid();
	}

	function updateSectionUI():Void {
		var sec = _song.notes[curSection];

		stepperLength.value = sec.lengthInSteps;
		check_mustHitSection.checked = sec.mustHitSection;
		check_altAnim.checked = sec.altAnim;
		check_changeBPM.checked = sec.changeBPM;
		// note that 0 implies regular anim and 1 implies default alt 
		if (sec.altAnimNum == null)
			sec.altAnimNum = sec.altAnim ? 1 : 0;
		stepperAltAnim.value = sec.altAnimNum;
		stepperSectionBPM.value = sec.bpm;
	}

	function updateHeads(transition:Bool = false, ?direction:Int):Void {
		var positionBefore = transition == true ? direction * gridBG.height : 0;
		if (!showPrevNext)
			positionBefore = 0;
		if (check_mustHitSection.checked) {
			leftIcon.setPosition(gridBG.x + gridBG.width / 4 - leftIcon.width / 2, -100 + positionBefore);
			rightIcon.setPosition(gridBG.x + 3*gridBG.width / 4 - rightIcon.width / 2, -100 + positionBefore);
		} else {
			rightIcon.setPosition(gridBG.x + gridBG.width / 4 - rightIcon.width / 2, -100 + positionBefore);
			leftIcon.setPosition(gridBG.x + 3*gridBG.width / 4 - leftIcon.width / 2, -100 + positionBefore);
		}
		if (transition && showPrevNext) {
			FlxTween.tween(rightIcon, {y: -100}, 0.5, {ease: FlxEase.circOut});
			FlxTween.tween(leftIcon, {y: -100}, 0.5, {ease: FlxEase.circOut});
		}
	}

	function updateNoteUI():Void {
		if (curSelectedNote != null) {
			stepperSusLength.value = curSelectedNote[2];
			// null is falsy
			isAltNoteCheck.checked = cast curSelectedNote[3];
			stepperAltNote.value = curSelectedNote[3] != null ? curSelectedNote[3] : 0;
			rawNoteTxt.text = curSelectedNote.toString();
		}
	}

	function updateGrid():Void {
		while (curRenderedEvents.members.length > 0) {
			var marker = curRenderedEvents.remove(curRenderedEvents.members[0], true);
			marker.destroy();
		}
		renderedEventRefs = [];
		while (curRenderedNotes.members.length > 0)
			curRenderedNotes.remove(curRenderedNotes.members[0], true);

		while (curRenderedSustains.members.length > 0)
			curRenderedSustains.remove(curRenderedSustains.members[0], true);

		//var normalcubeamount = _song.notes[curSection].lengthInSteps != 0 ? _song.notes[curSection].lengthInSteps : 16;
		remove(gridBG);
		gridBG = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, GRID_SIZE * _song.preferredNoteAmount * 2, GRID_SIZE * zoomFactor * _song.notes[curSection].lengthInSteps);
		gridBG.x = GRID_SIZE * 4 - gridBG.width / 2;
		add(gridBG);

		remove(prevGrid);
		var legsInStops = curSection - 1 < 0 ? 16 : _song.notes[curSection - 1].lengthInSteps;
		prevGrid = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, GRID_SIZE * _song.preferredNoteAmount * 2, GRID_SIZE * zoomFactor * legsInStops);
		prevGrid.alpha = 0.5;
		prevGrid.setPosition(gridBG.x, gridBG.y - prevGrid.height);
		if (curSection - 1 < 0 || !showPrevNext)
			prevGrid.visible = false;
		add(prevGrid);

		remove(nextGrid);
		legsInStops = _song.notes[curSection + 1] == null ? 16 : _song.notes[curSection + 1].lengthInSteps;
		nextGrid = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, GRID_SIZE * _song.preferredNoteAmount * 2, GRID_SIZE * zoomFactor * legsInStops);
		nextGrid.alpha = 0.5;
		nextGrid.setPosition(gridBG.x, gridBG.y + gridBG.height);
		if (_song.notes[curSection + 1] == null || !showPrevNext)
			nextGrid.visible = false;
		add(nextGrid);
		renderChartEventLane();

		remove(gridBlackLine);
		gridBlackLine = new FlxSprite(gridBG.x + gridBG.width / 2 - 1, -gridBG.height).makeGraphic(2, Std.int(gridBG.height*3), FlxColor.BLACK);
		add(gridBlackLine);

		for (i in 0...gridBeatLines.length) { // needs to be fixed for lengthInSteps being different
			remove(gridBeatLines[i]);
			var newline = new FlxSprite(gridBG.x, prevGrid.y + gridBG.height / 4 * (i+1) - 1).makeGraphic(Std.int(gridBG.width), 2, FlxColor.BLACK);
			switch(i) {
				case 3 | 7:
					// section line
				default:
					newline.alpha = 0.5;
			}
			gridBeatLines[i] = newline;
			add(gridBeatLines[i]);
		}

		var sectionInfo:Array<Dynamic> = _song.notes[curSection].sectionNotes;

		if (_song.notes[curSection].changeBPM && _song.notes[curSection].bpm > 0) {
			Conductor.changeBPM(_song.notes[curSection].bpm);
			FlxG.log.add('CHANGED BPM!');
		} else {
			//get last bpm
			var daBPM:Float = _song.bpm;
			for (i in 0...curSection)
				if (_song.notes[i].changeBPM)
					daBPM = _song.notes[i].bpm;
			Conductor.changeBPM(daBPM);
		}

		// these are literally never used why is it called every time the grid updates
		//var yummyPng = FNFAssets.getBitmapData('assets/images/custom_ui/ui_packs/normal/NOTE_assets.png');
		//var yummyXml = FNFAssets.getText('assets/images/custom_ui/ui_packs/normal/NOTE_assets.xml');
		for (i in sectionInfo) {
			renderNewNote(i);
		}

		if (_song.notes[curSection + 1] != null && showPrevNext) {
			var nextSecInfo:Array<Dynamic> = _song.notes[curSection+1].sectionNotes;
			for (i in nextSecInfo) {
				var daStrumTime = i[0];
				var daNoteInfo = i[1];
				var daSus = i[2] != null ? i[2] : 0;
			
				var note:EdtNote = new EdtNote(daStrumTime, daNoteInfo);
				note.sustainLength = daSus;
				note.setGraphicSize(GRID_SIZE, GRID_SIZE);
				note.updateHitbox();
				final sideSwap = _song.notes[curSection+1].mustHitSection != _song.notes[curSection].mustHitSection ? _song.preferredNoteAmount : 0;
				note.x = gridBG.x + Math.floor(((daNoteInfo + sideSwap) % (_song.preferredNoteAmount * 2)) * GRID_SIZE);
		 		note.y = Math.floor(getYfromStrum((daStrumTime - sectionStartTime(1)) % (Conductor.stepCrochet * _song.notes[curSection+1].lengthInSteps))) + gridBG.height;
				note.alpha = 0.5;

				curRenderedNotes.add(note);

				if (daSus > 0) {
					var sustainVis:FlxSprite = new FlxSprite(note.x + (GRID_SIZE / 2),
						note.y + GRID_SIZE).makeGraphic(8, Math.floor(FlxMath.remapToRange(daSus, 0, Conductor.stepCrochet * _song.notes[curSection+1].lengthInSteps, 0, nextGrid.height)));
					sustainVis.alpha = 0.5;
					curRenderedSustains.add(sustainVis);
				}
			}
		}

		if (curSection - 1 >= 0 && showPrevNext) {
			var prevSecInfo:Array<Dynamic> = _song.notes[curSection-1].sectionNotes;
			for (i in prevSecInfo) {
				var daStrumTime = i[0];
				var daNoteInfo = i[1];
				var daSus = i[2] != null ? i[2] : 0;
			
				var note:EdtNote = new EdtNote(daStrumTime, daNoteInfo);
				note.sustainLength = daSus;
				note.setGraphicSize(GRID_SIZE, GRID_SIZE);
				note.updateHitbox();
				final sideSwap = _song.notes[curSection-1].mustHitSection != _song.notes[curSection].mustHitSection ? _song.preferredNoteAmount : 0;
				note.x = gridBG.x + Math.floor(((daNoteInfo + sideSwap) % (_song.preferredNoteAmount * 2)) * GRID_SIZE);
		 		note.y = Math.floor(getYfromStrum((daStrumTime - sectionStartTime(-1)) % (Conductor.stepCrochet * _song.notes[curSection-1].lengthInSteps))) - prevGrid.height;
				note.alpha = 0.5;

				curRenderedNotes.add(note);

				if (daSus > 0) {
					var sustainVis:FlxSprite = new FlxSprite(note.x + (GRID_SIZE / 2),
						note.y + GRID_SIZE).makeGraphic(8, Math.floor(FlxMath.remapToRange(daSus, 0, Conductor.stepCrochet * _song.notes[curSection-1].lengthInSteps, 0, prevGrid.height)));
					sustainVis.alpha = 0.5;
					curRenderedSustains.add(sustainVis);
				}
			}
		}
	}

	function renderChartEventLane():Void {
		if (eventLaneBG != null) {
			remove(eventLaneBG);
			eventLaneBG.destroy();
		}
		if (eventLanePrevBG != null) {
			remove(eventLanePrevBG);
			eventLanePrevBG.destroy();
		}
		if (eventLaneNextBG != null) {
			remove(eventLaneNextBG);
			eventLaneNextBG.destroy();
		}
		var laneX = gridBG.x - 112;
		// Restart the checker at each section boundary, just as the note grids
		// do. Reverse the horizontal colour phase so the lane's final partial
		// cell alternates with the first note cell across the four-pixel gap.
		eventLanePrevBG = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, 108,
			Std.int(prevGrid.height), true, 0xffd9d5d5, 0xffe7e6e6);
		eventLanePrevBG.setPosition(laneX, prevGrid.y);
		eventLanePrevBG.alpha = prevGrid.alpha;
		eventLanePrevBG.visible = prevGrid.visible;
		eventLaneBG = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, 108,
			Std.int(gridBG.height), true, 0xffd9d5d5, 0xffe7e6e6);
		eventLaneBG.setPosition(laneX, gridBG.y);
		eventLaneNextBG = FlxGridOverlay.create(GRID_SIZE, GRID_SIZE, 108,
			Std.int(nextGrid.height), true, 0xffd9d5d5, 0xffe7e6e6);
		eventLaneNextBG.setPosition(laneX, nextGrid.y);
		eventLaneNextBG.alpha = nextGrid.alpha;
		eventLaneNextBG.visible = nextGrid.visible;
		var markerLayer = members.indexOf(curRenderedEvents);
		if (markerLayer < 0) {
			add(eventLanePrevBG);
			add(eventLaneBG);
			add(eventLaneNextBG);
		} else {
			insert(markerLayer, eventLanePrevBG);
			insert(markerLayer + 1, eventLaneBG);
			insert(markerLayer + 2, eventLaneNextBG);
		}
		var lastTime = Math.NaN;
		var sameTime = 0;
		for (reference in chartEventReferences()) {
			var time:Float = Reflect.field(reference, 'time');
			var section = ChartEventModel.sectionAtTime(cast _song.notes, _song.bpm, time);
			if (section < curSection - 1 || section > curSection + 1
				|| (section != curSection && !showPrevNext))
				continue;
			var start = ChartEventModel.sectionStart(cast _song.notes, _song.bpm, section);
			var end = ChartEventModel.sectionStart(cast _song.notes, _song.bpm, section + 1);
			var sectionY = section == curSection ? gridBG.y : (section < curSection ? prevGrid.y : nextGrid.y);
			var height = section == curSection ? gridBG.height : (section < curSection ? prevGrid.height : nextGrid.height);
			var y = sectionY + (time - start) / (end - start) * height;
			if (time == lastTime)
				sameTime++;
			else {
				lastTime = time;
				sameTime = 0;
			}
			y = Math.max(sectionY, Math.min(sectionY + height - 13, y + sameTime * 12));
			var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
			var title = event.length > 0 ? Std.string(event[0]) : 'Event';
			if (title.length > 14)
				title = title.substr(0, 11) + '...';
			var marker = new FlxText(laneX + 3, y, 102, '> ' + title, 9);
			marker.color = event == selectedChartEvent ? FlxColor.YELLOW : FlxColor.WHITE;
			marker.alpha = section == curSection ? 1 : 0.55;
			curRenderedEvents.add(marker);
			renderedEventRefs.push(reference);
		}
	}

	private function renderNewNote(note:Array<Dynamic>, offset:Int = 0) {
		var newnote:EdtNote = new EdtNote(note[0], note[1]);
		newnote.sustainLength = note[2];
		newnote.setGraphicSize(GRID_SIZE, GRID_SIZE);
		newnote.updateHitbox();
		newnote.x = gridBG.x + Math.floor((note[1] % (_song.preferredNoteAmount * 2)) * GRID_SIZE);
		newnote.y = Math.floor(getYfromStrum((note[0] - sectionStartTime(offset)) % (Conductor.stepCrochet * _song.notes[curSection + offset].lengthInSteps)));

		curRenderedNotes.add(newnote);

		if (note[2] > 0) {
			var sustainVis:FlxSprite = new FlxSprite(newnote.x + (GRID_SIZE / 2),
				newnote.y + GRID_SIZE).makeGraphic(8, Math.floor(FlxMath.remapToRange(note[2], 0, Conductor.stepCrochet * _song.notes[curSection + offset].lengthInSteps, 0, gridBG.height)));
			curRenderedSustains.add(sustainVis);
		}
	}

	private function addSection(lengthInSteps:Int = 16):Void {
		var sec:SwagSection = {
			lengthInSteps: lengthInSteps,
			bpm: _song.bpm,
			changeBPM: false,
			mustHitSection: true,
			sectionNotes: [],
			altAnim: false,
			altAnimNum: 0
		};

		_song.notes.push(sec);
	}

	function selectNote(note:EdtNote):Void {
		var swagNum:Int = 0;
		
		for (i in _song.notes[curSection].sectionNotes) {
			if (i[0] == note.strumTime && i[1] % (_song.preferredNoteAmount*2) == note.noteData % (_song.preferredNoteAmount*2)) {
				curSelectedNote = _song.notes[curSection].sectionNotes[swagNum];
			}
			swagNum += 1;
		}

		if (UI_box.selected_tab_id != 'Note')
			UI_box.selected_tab_id = 'Note';

		updateGrid();
		updateNoteUI();
	}

	function deleteNote(note:EdtNote):Void {
		for (i in _song.notes[curSection].sectionNotes) {
			if (i[0] == note.strumTime && i[1] % (_song.preferredNoteAmount*2) == note.noteData % (_song.preferredNoteAmount*2)) {
				FlxG.log.add('FOUND EVIL NUMBER');
				_song.notes[curSection].sectionNotes.remove(i);
			}
		}

		updateGrid();
	}

	function clearSection():Void {
		_song.notes[curSection].sectionNotes = [];

		updateGrid();
	}

	function clearSong():Void {
		for (daSection in 0..._song.notes.length)
			_song.notes[daSection].sectionNotes = [];

		updateGrid();
	}

	private function addNote():Void {
		var daNote = [getStrumTime(dummyArrow.y) + sectionStartTime()];
		var noteData = Math.floor((FlxG.mouse.x - gridBG.x) / GRID_SIZE);
		var noteTypeData:Int = 0;
		switch (noteType) {
			case Mine: 
				noteTypeData = _song.preferredNoteAmount * 2;
			case Lift: 
				noteTypeData = _song.preferredNoteAmount * 4;
			case Death: 
				noteTypeData = _song.preferredNoteAmount * 6;
			case key: 
				noteTypeData = _song.preferredNoteAmount * 2 * key;
		}
		daNote[1] = noteData + noteTypeData;
		_song.notes[curSection].sectionNotes.push(daNote);

		curSelectedNote = _song.notes[curSection].sectionNotes[_song.notes[curSection].sectionNotes.length - 1];
		renderNewNote(curSelectedNote);

		if (FlxG.keys.pressed.CONTROL) {
			var dupeNote = [daNote[0], (noteData + _song.preferredNoteAmount) % (_song.preferredNoteAmount * 2) + noteTypeData];
			_song.notes[curSection].sectionNotes.push(dupeNote);
			renderNewNote(dupeNote);
		}

		//updateGrid();
		updateNoteUI();

		//autosaveSong();
	}

	function getStrumTime(yPos:Float):Float {
		return FlxMath.remapToRange(yPos, gridBG.y, gridBG.y + gridBG.height, 0, _song.notes[curSection].lengthInSteps * Conductor.stepCrochet);
	}

	function getYfromStrum(strumTime:Float):Float {
		return FlxMath.remapToRange(strumTime, 0, _song.notes[curSection].lengthInSteps * Conductor.stepCrochet, gridBG.y, gridBG.y + gridBG.height);
	}

	/*
	function calculateSectionLengths(?sec:SwagSection):Int
	{
		var daLength:Int = 0;

		for (i in _song.notes)
		{
			var swagLength = i.lengthInSteps;

			if (i.typeOfSection == Section.COPYCAT)
				swagLength * 2;

			daLength += swagLength;

			if (sec != null && sec == i)
			{
				trace('swag loop??');
				break;
			}
		}

		return daLength;
	}*/

	function psychEventsToHScript() {
		var coolDialog = new FileDialog();
		coolDialog.browse(FileDialogType.OPEN);
		coolDialog.onSelect.add(function (path:String):Void {
			var dajson:Dynamic = CoolUtil.parseJson(File.getContent(path));
			var dasong = dajson.song;
			var events:Array<Dynamic> = dasong.events;
			var dasteps:Array<Float> = [];
			var eventnotes:Array<String> = [];
			for (event in events) {
				dasteps.push(Conductor.timeToSteps(event[0]));
				var danote = '';
				var sillyEvents:Array<Dynamic> = event[1];
				for (silly in sillyEvents) {
					switch(silly[0]) {
						//case 'Add Camera Zoom':
							
						case 'Change Scroll Speed':
							danote += 'tweenScrollSpeed({scroll: ' + silly[1] + ', duration: Conductor.timeToSteps(' + Std.parseFloat(silly[2]) * 1000 + ', false)});';
						default:
							danote += '// ' + silly[0] + ' [' + silly[1] + '] [' + silly[2] + ']\n';
					}
				}
				eventnotes.push(danote);
			}

			var hscriptlayout = 'function stepHit(step) {\n    switch(step) {';
			for (entry in 0...dasteps.length) {
				hscriptlayout += '\n	case ' + dasteps[entry] + ':\n		' + eventnotes[entry];
			}
			hscriptlayout += '\n    }\n}';
			File.saveContent('assets/data/hscriptreadout.txt', hscriptlayout);
			System.openFile('assets/data/hscriptreadout.txt');
		});
	}

	private var daSpacing:Float = 0.3;

	function loadLevel():Void {
		trace(_song.notes);
	}

	function getNotes():Array<Dynamic> {
		var noteData:Array<Dynamic> = [];

		for (i in _song.notes)
			noteData.push(i.sectionNotes);

		return noteData;
	}

	function loadJson(song:String):Void {
		PlayState.SONG = Song.loadFromJson(song.toLowerCase(), Song.storageFolder(_song));
		FlxG.resetState();
	}

	function loadRawEditorNotes():Void {
		var folder = Song.storageFolder(_song);
		if (folder == '') return;
		var path = 'assets/data/' + folder + '/' + editorChartFileName() + '.json';
		if (!FNFAssets.exists(path)) return;
		try {
			var source:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			var sourceSong:Dynamic = source == null ? null : Reflect.field(source, 'song');
			var sourceNotes:Dynamic = sourceSong == null ? null : Reflect.field(sourceSong, 'notes');
			if (!Std.isOfType(sourceNotes, Array)) return;
			var editorCopy:Dynamic = Reflect.copy(_song);
			Reflect.setField(editorCopy, 'notes', sourceNotes);
			_song = cast editorCopy;
		} catch (error:Dynamic) {
			trace('Unable to load authored editor note rows from ' + path + ': ' + error);
		}
	}

	/** The chart filename belongs to the loaded owner, even if its authored
	 * title is edited in the UI. */
	function editorChartFileName():String {
		var loaded:Dynamic = Reflect.field(_song, 'compatChartFileName');
		if (loaded != null) {
			var name = StringTools.trim(Std.string(loaded)).toLowerCase();
			if (name != '' && name != '.' && name != '..' && name.indexOf('/') < 0
				&& name.indexOf('\\') < 0 && name.indexOf(':') < 0)
				return name;
		}
		return Song.storageFolder(_song) + DifficultyIcons.getEndingFP(PlayState.storyDifficulty);
	}

	/** Loader provenance is an in-memory routing aid, not authored chart data. */
	function editorSongData():Dynamic {
		var data:Dynamic = Reflect.copy(_song);
		Reflect.deleteField(data, 'compatStorageFolder');
		Reflect.deleteField(data, 'compatChartFileName');
		Reflect.deleteField(data, 'compatStageAuthored');
		return data;
	}

	function loadAutosave():Void {
		PlayState.SONG = Song.parseJSONshit(FlxG.save.data.autosave, true);
		FlxG.resetState();
	}

	function autosaveSong():Void {
		FlxG.save.data.autosave = Json.stringify({
			"song": _song
		});
		FlxG.save.flush();
	}

	private function saveLevel() {
		var json = {
			"song": editorSongData()
		};

		var data:String = CoolUtil.stringifyJson(json);

		if ((data != null) && (data.length > 0)) {
			//FNFAssets.askToSave(_song.song.toLowerCase() + '.json', data);
			File.saveContent('assets/data/' + Song.storageFolder(_song) + '/' + editorChartFileName() + '.json', data);
		}
	}

	private function saveLevelTo() {
		var json = {
			"song": editorSongData()
		};

		var data:String = CoolUtil.stringifyJson(json);

		if ((data != null) && (data.length > 0)) {
			FNFAssets.askToSave(_song.song.toLowerCase() + '.json', data);
		}
	}

	override public function destroy() {
		destroyEditorVocals();
		super.destroy();
	}
}
