package;

import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.addons.display.FlxGridOverlay;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import lime.utils.Assets;
import DifficultyIcons;
import flixel.addons.ui.FlxInputText;
import flixel.addons.ui.FlxUI9SliceSprite;
import flixel.addons.ui.FlxUI;
import flixel.addons.ui.FlxUICheckBox;
import flixel.addons.ui.FlxUIDropDownMenu;
import flixel.addons.ui.FlxUIInputText;
import flixel.addons.ui.FlxUINumericStepper;
import flixel.ui.FlxButton;
import flixel.addons.ui.FlxUIButton;
import flixel.ui.FlxSpriteButton;
import flixel.addons.ui.FlxUITabMenu;
import lime.system.System;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;

#end
import lime.ui.FileDialog;
import lime.app.Event;
import haxe.Json;
import tjson.TJSON;
import Song.SwagSong;
import openfl.net.FileReference;
import openfl.utils.ByteArray;
import lime.ui.FileDialogType;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
using StringTools;
typedef TDifficulty = {
	var offset:Int;
	var anim:String;
	var name:String;
}
typedef TDifficulties = {
	var difficulties:Array<TDifficulty>;
	var defaultDiff:Int;
}
class NewSongState extends MusicBeatState
{
	var addCharUi:FlxUI;
	var nameText:FlxUIInputText;
	var diffButtons:FlxTypedSpriteGroup<FlxUIButton>;
	var instButton:FlxUIButton;
	var voiceButton:FlxUIButton;
	var dialogButton:FlxUIButton;
	var modchartButton:FlxUIButton;
	var infoButton:FlxUIButton;
	var coolDiffFiles:Array<String> = [];
	var instPath:String;
	var voicePath:String;
	var dialogPath:String;
	var modchartPath:String;
	var p1Text:FlxUIInputText;
	var p2Text:FlxUIInputText;
	var gfText:FlxUIInputText;
	var stageText:FlxUIInputText;
	var stageID:FlxUINumericStepper;
	var cutsceneText:FlxUIInputText;
	var uiText:FlxUIInputText;
	var isHey:FlxUICheckBox;
	var isCheer:FlxUICheckBox;
	var isMoody:FlxUICheckBox;
	var isSpooky:FlxUICheckBox;
	var categoryText:FlxUIInputText;
	var weekText:FlxUIInputText;
	var charText:FlxUIInputText;
	var displayText:FlxUIInputText;
	var importText:FlxUIInputText;
	var importButton:FlxUIButton;
	var exportText:FlxUIInputText;
	var exportButton:FlxUIButton;
	var finishButton:FlxButton;
	var cancelButton:FlxUIButton;
	var coolFile:FileReference;
	var coolData:ByteArray;
	var epicFiles:Dynamic;
	private var grpSongs:FlxTypedGroup<Alphabet>;
	private var curPlaying:Bool = false;

	override function create() {
		addCharUi = new FlxUI();
		FlxG.mouse.visible = true;

		var bg:FlxSprite = new FlxSprite().loadGraphic('assets/images/menuBGBlue.png');
		add(bg);

		diffButtons = new FlxTypedSpriteGroup<FlxUIButton>(0,0);
		var diffJson:TDifficulties = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_difficulties/difficulties"));

		nameText = new FlxUIInputText(100,10,70,"bopeebo");
		p1Text = new FlxUIInputText(100, 50, 70,"bf");
		p2Text = new FlxUIInputText(100,90,70,"dad");
		gfText = new FlxUIInputText(100,130,70,"gf");
		stageText = new FlxUIInputText(100,180,70,"stage");
		stageID = new FlxUINumericStepper(100,195,1,0,0,10);
		cutsceneText = new FlxUIInputText(100,220,70,"none");
		uiText = new FlxUIInputText(100,260,70,"normal");
		categoryText = new FlxUIInputText(100,290,70,"Base Game");
		isHey = new FlxUICheckBox(100,340, null, null, "Do HEY! Poses");
		isCheer = new FlxUICheckBox(100,390, null, null, "Do Cheer Pose");
		isMoody = new FlxUICheckBox(100,440,null,null, "Girls Scared");
		isSpooky = new FlxUICheckBox(100,490,null,null,"Background Trail");
		weekText = new FlxUIInputText(280,10,70,"0");
		charText = new FlxUIInputText(280,50,70,"null");
		displayText = new FlxUIInputText(280,90,70,"null");

		importText = new FlxUIInputText(400,10,70,"Ugh");
		importButton = new FlxUIButton(400,50, "Import Song", function():Void {
			ImportSettings.ensureImportDirectories();
			var basePath:String = haxe.io.Path.join([ImportSettings.getImportPath('songs'), importText.text]);
			if (!FileSystem.isDirectory(basePath)) {
				trace('Unable to import song: folder not found.');
				return;
			}
			var importedSong = ModuleFunctions.songImportFromFolder(basePath);
			if (ModuleFunctions.validateSongImport(importedSong) != null) {
				trace('Unable to import song: Inst.ogg and a valid chart are required.');
				return;
			}
			applySongImport(importedSong);
		});

		exportText = new FlxUIInputText(490,10,70,"Dadbattle");
		exportButton = new FlxUIButton(490,50, "Export Song", function():Void {
			ModuleFunctions.exportSong(exportText.text);
		});

		for (i in 0...diffJson.difficulties.length) {
			var coolDiffButton = new FlxUIButton(10, 10 + (i * 50), diffJson.difficulties[i].name + " json", function():Void {
				var coolDialog = new FileDialog();
				coolDialog.browse(FileDialogType.OPEN);
				coolDialog.onSelect.add(function (path:String):Void {
					coolDiffFiles[i] = path;
				});
			});
			diffButtons.add(coolDiffButton);
		}
		add(nameText);
		add(p1Text);
		add(p2Text);
		add(gfText);
		add(stageText);
		add(cutsceneText);
		add(categoryText);
		add(uiText);
		add(isHey);
		add(isCheer);
		add(isMoody);
		add(isSpooky);
		add(weekText);
		add(charText);
		add(displayText);
		add(importText);
		add(importButton);
		add(stageID);
		add(diffButtons);
		finishButton = new FlxButton(FlxG.width - 170, FlxG.height - 50, "Finish", function():Void {
			if (writeCharacters())
				LoadingState.loadAndSwitchState(new SaveDataState());
			else
				trace('Unable to save song: Inst.ogg and at least one valid chart are required.');
		});
		instButton = new FlxUIButton(190, 10, "Instruments", function():Void {
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN);
			coolDialog.onSelect.add(function (path:String):Void {
				instPath = path;
			});
		});
		voiceButton = new FlxUIButton(190, 60, "Vocals", function():Void {
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN);
			coolDialog.onSelect.add(function (path:String):Void {
				voicePath = path;
			});
		});
		dialogButton = new FlxUIButton(190, 110, "Dialog", function():Void {
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN);
			coolDialog.onSelect.add(function (path:String):Void {
				dialogPath = path;
			});
		});
		modchartButton = new FlxUIButton(190, 160, "Modchart", function():Void {
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN);
			coolDialog.onSelect.add(function (path:String):Void {
				modchartPath = path;
			});
		});
		infoButton = new FlxUIButton(190, 210, "Song Info", function():Void {
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN);
			coolDialog.onSelect.add(function (path:String):Void {
				getInfo(path);
			});
		});
		cancelButton = new FlxUIButton(FlxG.width - 300, FlxG.height - 50, "Cancel", function():Void {
			// go back
			LoadingState.loadAndSwitchState(new SaveDataState());
		});
		add(instButton);
		add(voiceButton);
		add(dialogButton);
		add(modchartButton);
		add(infoButton);
		add(finishButton);
		add(cancelButton);
		super.create();
	}

	override function update(elapsed:Float) {
		super.update(elapsed);
	}
	function convertToBool(theInfo:String) { // im too lazy to find a built-in converter lol
		var daBool:Bool = false;
		switch(theInfo) {
			case 'false':
				daBool = false;
			case 'true':
				daBool = true;
		}
		return daBool;
	}
	function applySongImport(songData:ModuleFunctions.SongImport):Void {
		if (songData == null)
			return;
		nameText.text = songData.name;
		p1Text.text = songData.p1;
		p2Text.text = songData.p2;
		gfText.text = songData.gf;
		stageText.text = songData.stage;
		uiText.text = songData.ui;
		cutsceneText.text = songData.cutscene;
		categoryText.text = songData.category;
		isHey.checked = songData.isHey;
		isCheer.checked = songData.isCheer;
		isMoody.checked = songData.isMoody;
		isSpooky.checked = songData.isSpooky;
		stageID.value = songData.stageID;
		weekText.text = Std.string(songData.week);
		charText.text = songData.char;
		displayText.text = songData.display;
		instPath = songData.inst;
		voicePath = songData.voices;
		dialogPath = songData.dialog;
		modchartPath = songData.modchart;
		coolDiffFiles = songData.diffFiles == null ? [] : songData.diffFiles.copy();
	}
	function getInfo(infoPath:String) {
		var info = ModuleFunctions.processInfo(infoPath);
		nameText.text = ModuleFunctions.getInfoValue(info, 'songname', nameText.text);
		p1Text.text = ModuleFunctions.getInfoValue(info, 'player1', p1Text.text);
		p2Text.text = ModuleFunctions.getInfoValue(info, 'player2', p2Text.text);
		gfText.text = ModuleFunctions.getInfoValue(info, 'gf', gfText.text);
		stageText.text = ModuleFunctions.getInfoValue(info, 'stage', stageText.text);
		uiText.text = ModuleFunctions.getInfoValue(info, 'uiType', uiText.text);
		cutsceneText.text = ModuleFunctions.getInfoValue(info, 'cutsceneType', cutsceneText.text);
		categoryText.text = ModuleFunctions.getInfoValue(info, 'category', categoryText.text);
		isHey.checked = ModuleFunctions.getInfoBool(info, 'isHey', isHey.checked);
		isCheer.checked = ModuleFunctions.getInfoBool(info, 'isCheer', isCheer.checked);
		isMoody.checked = ModuleFunctions.getInfoBool(info, 'isMoody', isMoody.checked);
		isSpooky.checked = ModuleFunctions.getInfoBool(info, 'isSpooky', isSpooky.checked);
		stageID.value = ModuleFunctions.getInfoInt(info, 'stageID', Std.int(stageID.value));
		weekText.text = ModuleFunctions.getInfoValue(info, 'week', weekText.text);
		charText.text = ModuleFunctions.getInfoValue(info, 'char', charText.text);
		displayText.text = ModuleFunctions.getInfoValue(info, 'display', displayText.text);
	}
	function writeCharacters():Bool {
		var parsedWeek = Std.parseInt(weekText.text);
		var daData:ModuleFunctions.SongImport = {
			name: nameText.text,
			p1: p1Text.text,
			p2: p2Text.text,
			gf: gfText.text,
			stage: stageText.text,
			ui: uiText.text,
			cutscene: cutsceneText.text,
			category: categoryText.text,
			isHey: isHey.checked,
			isCheer: isCheer.checked,
			isMoody: isMoody.checked,
			isSpooky: isSpooky.checked,
			stageID: Std.int(stageID.value),
			week: parsedWeek == null ? -1 : parsedWeek,
			char: charText.text,
			display: displayText.text,
			inst: instPath,
			voices: voicePath,
			dialog: dialogPath,
			modchart: modchartPath,
			diffFiles: coolDiffFiles
		}
		return ModuleFunctions.importSong(daData);
	}


	function oldwriteCharacters() {
		// check to see if directory exists
		#if sys
		if (!FileSystem.exists('assets/data/' + nameText.text.toLowerCase())) {
			FileSystem.createDirectory('assets/data/' + nameText.text.toLowerCase());
		}
		for (i in 0...coolDiffFiles.length) {
			if (coolDiffFiles[i] != null) {
				var coolSong:Dynamic = CoolUtil.parseJson(File.getContent(coolDiffFiles[i]));
				var coolSongSong:Dynamic = coolSong.song;
				coolSongSong.song = nameText.text;
				coolSongSong.player1 = p1Text.text;
				coolSongSong.player2 = p2Text.text;
				coolSongSong.gf = gfText.text;
				coolSongSong.stage = stageText.text;
				coolSongSong.stageID = Std.int(stageID.value);
				coolSongSong.uiType = uiText.text;
				coolSongSong.cutsceneType = cutsceneText.text;
				coolSongSong.isHey = isHey.checked;
				coolSongSong.isCheer = isCheer.checked;
				coolSongSong.isMoody = isMoody.checked;
				coolSongSong.isSpooky = isSpooky.checked;
				coolSong.song = coolSongSong;

				File.saveContent('assets/data/'+nameText.text.toLowerCase()+'/'+nameText.text.toLowerCase()+DifficultyIcons.getEndingFP(i)+'.json',CoolUtil.stringifyJson(coolSong));
			}
		}
		// probably breaks on non oggs haha weeeeeeeeeee
		if (!FileSystem.exists('assets/songs/' + nameText.text.toLowerCase())) {
			FileSystem.createDirectory('assets/songs/' + nameText.text.toLowerCase());
		}
		File.copy(instPath,'assets/songs/' + nameText.text.toLowerCase() + '/' + nameText.text + '_Inst.ogg');
		if (voicePath != null) {
			File.copy(voicePath,'assets/songs/' + nameText.text.toLowerCase() + '/' + nameText.text + '_Voices.ogg');
		}
		if (dialogPath != null) {
			File.copy(dialogPath,'assets/data/' + nameText.text.toLowerCase() + '/dialog.txt');
		}
		if (modchartPath != null) {
			File.copy(modchartPath,'assets/data/' + nameText.text.toLowerCase() + '/modchart.hscript');
		}
		if (charText.text == 'null')
			charText.text = p2Text.text;
		var coolSongListFile:Array<Dynamic> = cast FreeplayRegistry.getJson();
		var foundSomething:Bool = false;
		for (coolCategory in coolSongListFile) {
			if (coolCategory.name == categoryText.text) {
				foundSomething = true; 
				if (displayText.text == 'null')
					coolCategory.songs.push({"name": nameText.text, "character": charText.text, "week": Std.parseFloat(weekText.text)});
				else
					coolCategory.songs.push({"name": nameText.text, "character": charText.text, "week": Std.parseFloat(weekText.text), "display": displayText.text});
				break;
			}
		}
		if (!foundSomething) {
			// must be a new category
			if (displayText.text == 'null')
				coolSongListFile.push({"name": categoryText.text, "songs": [{"name": nameText.text, "character": charText.text, "week": Std.parseFloat(weekText.text)}]});
			else
				coolSongListFile.push({"name": categoryText.text, "songs": [{"name": nameText.text, "character": charText.text, "week": Std.parseFloat(weekText.text), "display": displayText.text}]});
		}
		FreeplayRegistry.saveJson(coolSongListFile);
		#end
	}
}
