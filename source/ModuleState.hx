package;

import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxObject;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import lime.utils.Assets;
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
import flixel.sound.FlxSound;
import openfl.media.Sound;
import flixel.addons.ui.FlxUITabMenu;
import flixel.FlxCamera;
import lime.system.System;
import lime.ui.FileDialog;
import lime.app.Event;
import haxe.Json;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;
#end
import tjson.TJSON;
import openfl.net.FileReference;
import openfl.utils.ByteArray;
import lime.ui.FileDialogType;
using StringTools;
import NewSongState.TDifficulty;
import NewSongState.TDifficulties;
import Song.SwagSong;

typedef ImportBox = {
	var background:FlxSprite;
	var icon:HealthIcon;
	var nameText:FlxText;
	var importButton:FlxUIButton;
	var miscButton:FlxUIButton;
}

class ModuleState extends MusicBeatState {
	var ModuleUi:FlxUI;
	var newChar:FlxUIButton;
	var newStage:FlxUIButton;
	var newSong:FlxUIButton;
	var newWeek:FlxUIButton;
	var importSongs:FlxUIInputText;
	var importSongsButton:FlxUIButton;
	var songVocals:FlxSound;
	var selectMode:FlxText;

	var songs:Array<String> = [];
	var characters:Array<String> = [];
	var moduleStages:Array<String> = [];
	var weeks:Array<String> = [];

	var songBoxes:Array<ModuleBox> = [];
	var charBoxes:Array<ImportBox> = [];
	var stageBoxes:Array<ImportBox> = [];
	var weekBoxes:Array<ImportBox> = [];

	var songsLoaded = false;
	var moduleMode:String = 'none';
	var transferPath:String = '';
	var importButton:FlxUIButton;
	var exportButton:FlxUIButton;
	var transferButton:FlxUIButton;

	var camFollow:FlxObject;
	var gameFollow:FlxObject;
	var scrollNum:Array<Float> = [0, 0, 0, 0];
	var section:Int = 0;

	var camHUD:FlxCamera;
	var camGame:FlxCamera;

	var bf:Character;
	var gf:Character;
	override function create() {
		ModuleUi = new FlxUI();
		FlxG.mouse.visible = true;

		camGame = new FlxCamera();
		camHUD = new FlxCamera();
		camHUD.bgColor.alpha = 0;
		FlxG.cameras.reset(camGame);
		FlxG.cameras.add(camHUD);
		FlxG.cameras.setDefaultDrawTarget(camGame, false);

		//FlxCamera.defaultCameras = [camHUD];

		var bg:FlxSprite = new FlxSprite().loadGraphic('assets/images/menuBGBlue.png');
		bg.scrollFactor.set();
		bg.cameras = [camGame];
		add(bg);

		gf = new Character(-150, 0, 'gf');
		gf.beingControlled = true;
		gf.scrollFactor.set(0.95, 0.95);
		gf.cameras = [camGame];
		add(gf);

		bf = new Character(250, 350, 'bf', true);
		bf.beingControlled = true;
		bf.cameras = [camGame];
		add(bf);

		newChar = new FlxUIButton(10, 10, "New Char", function():Void {
			LoadingState.loadAndSwitchState(new NewCharacterState());
		});
		newStage = new FlxUIButton(10, 40, "New Stage", function():Void {
			LoadingState.loadAndSwitchState(new NewStageState());
		});
		newSong = new FlxUIButton(10, 70, "New Song", function():Void {
			LoadingState.loadAndSwitchState(new NewSongState());
		});
		newWeek = new FlxUIButton(10, 100, "New Week", function():Void {
			LoadingState.loadAndSwitchState(new NewWeekState());
		});

		selectMode = new FlxText(0, 200, FlxG.width, "Select Module Mode");
		selectMode.setFormat("VCR OSD Mono", 32, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		selectMode.alignment = 'center';

		importButton = new FlxUIButton(500, (FlxG.height / 2) - 100, "Import", function():Void {
			selectMode.text = 'Loading...';
			moduleMode = 'Import';
			generateStuff();
			removeModeButtons();
			remove(selectMode);
			songsLoaded = true;
		});
		exportButton = new FlxUIButton(600, (FlxG.height / 2) - 100, "Export", function():Void {
			selectMode.text = 'Loading...';
			moduleMode = 'Export';
			generateStuff();
			removeModeButtons();
			remove(selectMode);
			songsLoaded = true;
		});
		transferButton = new FlxUIButton(700, (FlxG.height / 2) - 100, "Transfer", function():Void {
			selectMode.text = 'Select assets folder of Modding Plus to transfer.';
			var coolDialog = new FileDialog();
			coolDialog.browse(FileDialogType.OPEN_DIRECTORY);
			coolDialog.onSelect.add(function (path:String):Void {
				if (StringTools.endsWith(path, 'assets')) {
					selectMode.text = 'Loading...';
					moduleMode = 'Transfer';
					transferPath = path;
					generateStuff();
					removeModeButtons();
					remove(selectMode);
					songsLoaded = true;
				} else {
					selectMode.text = 'Incorrect File. Please try again.';
				}
			});
		});
		add(selectMode);
		add(importButton);
		add(exportButton);
		add(transferButton);
		add(newChar);
		add(newStage);
		add(newSong);
		add(newWeek);

		camFollow = new FlxObject(0, 0, 1, 1);
		camFollow.setPosition(FlxG.width / 2, FlxG.height / 2);
		add(camFollow);

		camHUD.follow(camFollow, LOCKON, 0.04);
		camHUD.focusOn(camFollow.getPosition());

		gameFollow = new FlxObject(0, 0, 1, 1);
		gameFollow.setPosition(FlxG.width / 2, FlxG.height / 2);
		add(gameFollow);

		camGame.follow(gameFollow, LOCKON, 0.04);
		camGame.focusOn(gameFollow.getPosition());

		super.create();
	}
	function removeModeButtons() {
		remove(importButton);
		remove(exportButton);
		remove(transferButton);
	}
	function generateStuff() {
		if (moduleMode == 'Import')
			ImportSettings.ensureImportDirectories();
		generateSongs();
		generateChars();
		generateStages();
		generateWeeks();
		generateOther();
	}
	var currentBoxNum = 0;
	override function update(elapsed:Float) {
		Conductor.songPosition += FlxG.elapsed * 1000;

		if (FlxG.keys.justPressed.G)
			syncVocals();

		if (FlxG.keys.justPressed.R && bf.animation.curAnim.name != 'firstDeath') {
			bf.playAnim('firstDeath', true);
			FlxG.sound.play('assets/sounds/fnf_loss_sfx' + TitleState.soundExt, 0.5);
		}

		if (FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE) {
			FlxG.mouse.visible = false;
			LoadingState.loadAndSwitchState(new SaveDataState());
		}

		switch(section) {
			case 0:
				currentBoxNum = songBoxes.length + 1;
			case 1:
				currentBoxNum = charBoxes.length + 1;
			case 2:
				currentBoxNum = stageBoxes.length + 1;
			case 3:
				currentBoxNum = weekBoxes.length + 1;
		}

		if (songsLoaded) {
			if (FlxG.keys.pressed.DOWN || FlxG.keys.pressed.S) {
				if (currentBoxNum > 4) {
					scrollNum[section] -= 10;
					if (FlxG.keys.pressed.SHIFT)
						scrollNum[section] -= 15;
					if (scrollNum[section] < -150 * (currentBoxNum - 5) - 60)
						scrollNum[section] = -150 * (currentBoxNum - 5) - 60;
				}
			} else if (FlxG.keys.pressed.UP || FlxG.keys.pressed.W) {
				scrollNum[section] += 10;
				if (FlxG.keys.pressed.SHIFT)
					scrollNum[section] += 15;
				if (scrollNum[section] > 0)
					scrollNum[section] = 0;
			}

			if (FlxG.keys.justPressed.LEFT || FlxG.keys.justPressed.A) {
				if (section > -1) {
					section -= 1;
					FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);
				}
			} else if (FlxG.keys.justPressed.RIGHT || FlxG.keys.justPressed.D) {
				if (section < 4) {
					section += 1;
					FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);
				}
			}
		}

		camFollow.setPosition(FlxG.width / 2 + FlxG.width * section, FlxG.height / 2);
		if (section == -1) {
			gameFollow.setPosition(300, 375); // 301.5, 324 + 50
		} else {
			gameFollow.setPosition(FlxG.width / 2, FlxG.height / 2);
		}

		for (i in 0...songBoxes.length) {
			songBoxes[i].y = 60 + (180 * i) + scrollNum[0];
		}
		
		/*for (ibox in 0...3) {
			var curBox = switch(ibox) {
				case 0:
					songBoxes;
				case 1:
					charBoxes;
				case 2:
					stageBoxes;
				case 3:
					weekBoxes;
				default:
					[];
			}
			if (curBox.length > 0) {
				for (i in 0...curBox.length) {
					var daBox = curBox[i];
					daBox.background.y = 60 + (180 * i) + scrollNum[ibox];
					daBox.icon.y = daBox.background.y + 10;
					daBox.nameText.y = daBox.background.y + 10;
					daBox.importButton.x = daBox.background.x + daBox.background.width - 120 - camHUD.scroll.x;
					daBox.importButton.y = daBox.background.y + 20;
					daBox.miscButton.x = daBox.background.x + daBox.background.width - 120 - camHUD.scroll.x;
					daBox.miscButton.y = daBox.background.y + 60;

					if (daBox.background.y > FlxG.height || daBox.background.y + daBox.background.height < 0-FlxG.height 
						|| daBox.background.x - camHUD.scroll.x  > FlxG.width || daBox.background.x + daBox.background.width - camHUD.scroll.x < 0-FlxG.width) {
						// this feels like its overcomplicated
						daBox.background.active = false;
						daBox.background.visible = false;
						daBox.icon.active = false;
						daBox.icon.visible = false;
						daBox.nameText.active = false;
						daBox.nameText.visible = false;
						daBox.importButton.active = false;
						daBox.importButton.visible = false;
						daBox.miscButton.active = false;
						daBox.miscButton.visible = false;
					} else {
						daBox.background.active = true;
						daBox.icon.active = true;
						daBox.nameText.active = true;
						daBox.importButton.active = true;
						daBox.miscButton.active = true;

						daBox.background.visible = true;
						daBox.icon.visible = true;
						daBox.nameText.visible = true;
						daBox.importButton.visible = true;
						daBox.miscButton.visible = true;
					}
				}
			}
		}*/

		super.update(elapsed);
	}
	/*function generateSection(sectionNum:Int = 0) {
		// 0 = songs, 1 = chars, 2 = stages, 3 = weeks, 4 = misc
		var daName;
		var daIcon = 'dad';
		var daBox:ImportBox = {
			background: null,
			icon: null,
			nameText: null,
			importButton: null,
			miscButton: null
		}; 
		daBox.background = new FlxSprite(650, 10 + (180 * songs.indexOf(path))).loadGraphic('assets/images/plainbox.png');
		daBox.icon = new HealthIcon(daIcon);
		daBox.icon.x = daBox.background.x + 5;
		daBox.icon.scrollFactor.set(1, 1);
		daBox.nameText = new FlxText(daBox.background.x + 180, daBox.background.y, daBox.background.width - 240, daName);
		daBox.nameText.setFormat('assets/fonts/vcr.otf', 40, 0xFFFFFFFF, 'left');
		daBox.importButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 20, moduleMode + " Song", function():Void {
			if (moduleMode != 'Export')
				importSong(song);
			else
				ModuleFunctions.exportSong(songName);
		});
		daBox.miscButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 60, "Listen", function():Void {
			switch(sectionNum) {
				case 0:
					if (songPlaying != song)
						listenSong(path, song);
					else
						endSong();
				case 1:
					
			}
		});
		add(daBox);
		//add(daBox.background);
		//add(daBox.icon);
		//add(daBox.nameText);
		//add(daBox.importButton);
		//add(daBox.miscButton);
		songBoxes.push(daBox);
	}*/
	function generateSongs() {
		var daFolding:String = '';
		switch(moduleMode) {
			case 'Import':
				daFolding = ModuleFunctions.importRoot();
			case 'Export':
				daFolding = 'assets/';
			case 'Transfer':
				daFolding = transferPath;
		}
		if (FileSystem.exists(haxe.io.Path.join([daFolding, 'songs']))) {
			var songFolder = haxe.io.Path.join([daFolding, 'songs']);
			for (song in FileSystem.readDirectory(songFolder)) {
				var path = haxe.io.Path.join([songFolder, song]);
				if (moduleMode != 'Import' || (sys.FileSystem.isDirectory(path) && moduleMode == 'Import' && FileSystem.exists(haxe.io.Path.join([path, 'info.txt'])))) {
					songs.push(path);
					var songName = 'null';
					var iconP2 = 'bf';
					if (moduleMode == 'Import') {
						var info = ModuleFunctions.processInfo(haxe.io.Path.join([path, 'info.txt']));
						songName = ModuleFunctions.getInfoValue(info, 'songname', song);
						iconP2 = ModuleFunctions.getInfoValue(info, 'player2', 'bf');
					} else {
						var data = null;
					if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json'])));
					} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json'])));
					} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json'])));
						}
						if (data != null) {
							songName = data.song;
							iconP2 = data.player2;
						}
					}
					var daBox:ModuleBox = new ModuleBox(650, 10 + (180 * songs.indexOf(path)), 'song', songName, iconP2);
					daBox.MainButton(moduleMode + " Song", function():Void {
						if (moduleMode != 'Export')
							importSong(song);
						else
							ModuleFunctions.exportSong(songName);
					});
					daBox.SecondaryButton("Listen", function():Void {
						if (songPlaying != song)
							listenSong(path, song);
						else
							endSong();
					});
					add(daBox);
					songBoxes.push(daBox);
				}
			}
		} else if (moduleMode != 'Import') {
			var dataFolder = haxe.io.Path.join([daFolding, 'data/']);
			if (!FileSystem.isDirectory(dataFolder))
				return;
			for (song in FileSystem.readDirectory(dataFolder)) {
				var path = haxe.io.Path.join([dataFolder, song]);
				if (sys.FileSystem.isDirectory(path)) {
					songs.push(path);
					var data = null;
					if (FileSystem.exists(haxe.io.Path.join([path, '/' + song + '-hard.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '/' + song + '-hard.json'])));
					} else if (FileSystem.exists(haxe.io.Path.join([path, '/' + song + '.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '/' + song + '.json'])));
					} else if (FileSystem.exists(haxe.io.Path.join([path, '/' + song + '-easy.json']))) {
						data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '/' + song + '-easy.json'])));
					}
						var songName = data != null && data.song != null ? data.song : song;
						var iconP2 = data != null && data.player2 != null ? data.player2 : 'bf';

					var daBox:ModuleBox = new ModuleBox(650, 10 + (180 * songs.indexOf(path)), 'song', songName, iconP2);
					daBox.MainButton(moduleMode + " Song", function():Void {
						if (moduleMode != 'Export')
							checkFile(songName.toLowerCase(), 'song', daFolding);
						else
							ModuleFunctions.exportSong(songName);
					});
					daBox.SecondaryButton("Listen", function():Void {
						if (songPlaying != song)
							listenSong(path, song);
						else
							endSong();
					});
					add(daBox);
					songBoxes.push(daBox);
				}
			}
		}

		var backdrop = new FlxSprite(650, 0).makeGraphic(FlxG.width - 650, 50, 0xFF808080);
		backdrop.alpha = 0.7;
		add(backdrop);

		var songText = new FlxText(650, 0, FlxG.width - 650, "Songs", 40);
		songText.alignment = 'center';
		add(songText);
	}
	function generateChars() {
		var daFolding:String = '';
		switch(moduleMode) {
			case 'Import':
				daFolding = ImportSettings.getImportPath('characters');
			case 'Export':
				daFolding = 'assets/images/custom_chars/';
			case 'Transfer':
				daFolding =  haxe.io.Path.join([transferPath, 'images/custom_chars/']);
		}
		if (!FileSystem.exists(daFolding) || !FileSystem.isDirectory(daFolding))
			return;
		if (FileSystem.isDirectory(daFolding))
		for (char in FileSystem.readDirectory(daFolding)) {
			var path = haxe.io.Path.join([daFolding, char]);
			if (sys.FileSystem.isDirectory(path)) {
				if (moduleMode != 'Import' || (moduleMode == 'Import' && FileSystem.exists(haxe.io.Path.join([path, 'info.txt'])))) {
					characters.push(path);
					var charName = 'null';
					var iconNum1 = 0;
					if (moduleMode == 'Import') {
						var info = ModuleFunctions.processInfo(haxe.io.Path.join([path, 'info.txt']));
						charName = ModuleFunctions.getInfoValue(info, 'charname', char);
						var iconNums = ModuleFunctions.getInfoValue(info, 'iconnums', '0,1,2,3').split(',');
						iconNum1 = Std.int(Std.parseFloat(iconNums[0]));
					} else {
						charName = char;
						/*if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json'])));
							songName = data.song;
							iconP2 = data.player2;
						} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json'])));
							songName = data.song;
							iconP2 = data.player2;
						} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json'])));
							songName = data.song;
							iconP2 = data.player2;
						}*/
					}
					var daBox:ImportBox = {
						background: null,
						icon: null,
						nameText: null,
						importButton: null,
						miscButton: null
					}; 
					daBox.background = new FlxSprite(650 + FlxG.width, 60 + (180 * characters.indexOf(path))).loadGraphic('assets/images/plainbox.png');
					daBox.icon = new HealthIcon(charName);
					daBox.icon.x = daBox.background.x + 5;
					daBox.icon.scrollFactor.set(1, 1);
					daBox.nameText = new FlxText(daBox.background.x + 180, daBox.background.y, daBox.background.width - 240, charName);
					daBox.nameText.setFormat('assets/fonts/vcr.otf', 40, 0xFFFFFFFF, 'left');
					daBox.importButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 20, moduleMode + " Char", function():Void {
						if (moduleMode != 'Export')
							importChar(char);
						else {
							ModuleFunctions.exportChar(charName);
						}
					});
					daBox.miscButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 60, "Load Character", function():Void {
						if (songPlaying != null)
							endSong();
						var newbf = new Character(250, 350, charName, true);
						newbf.beingControlled = true;
						newbf.cameras = [camGame];
						newbf.x += newbf.playerOffsetX;
						newbf.y += newbf.playerOffsetY;
						var oldbf = bf;
						remove(bf);
						bf = newbf;
						oldbf.destroy();
						add(bf);
					});
					add(daBox.background);
					add(daBox.icon);
					add(daBox.nameText);
					add(daBox.importButton);
					add(daBox.miscButton);
					charBoxes.push(daBox);
				}
			}
		}

		var backdrop = new FlxSprite(650 + FlxG.width, 0).makeGraphic(FlxG.width - 650, 50, 0xFF808080);
		backdrop.alpha = 0.7;
		add(backdrop);

		var charText = new FlxText(650 + FlxG.width, 0, FlxG.width - 650, "Characters", 40);
		charText.alignment = 'center';
		add(charText);
	}
	function generateStages() {
		var daFolding:String = '';
		switch(moduleMode) {
			case 'Import':
				daFolding = ImportSettings.getImportPath('stages');
			case 'Export':
				daFolding = 'assets/images/custom_stages/';
			case 'Transfer':
				daFolding =  haxe.io.Path.join([transferPath, 'images/custom_stages/']);
		}
		if (!FileSystem.exists(daFolding) || !FileSystem.isDirectory(daFolding))
			return;
		if (FileSystem.isDirectory(daFolding))
		for (stage in FileSystem.readDirectory(daFolding)) {
			var path = haxe.io.Path.join([daFolding, stage]);
			if (sys.FileSystem.isDirectory(path)) {
				if (moduleMode != 'Import' || (moduleMode == 'Import' && FileSystem.exists(haxe.io.Path.join([path, 'info.txt'])))) {
					moduleStages.push(path);
					var stageName = 'null';
					if (moduleMode == 'Import') {
						var info = ModuleFunctions.processInfo(haxe.io.Path.join([path, 'info.txt']));
						stageName = ModuleFunctions.getInfoValue(info, 'stagename', stage);
					} else {
						stageName = stage;
						/*if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-hard.json'])));
							songName = data.song;
							iconP2 = data.player2;
						} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '.json'])));
							songName = data.song;
							iconP2 = data.player2;
						} else if (FileSystem.exists(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json']))) {
							var data = Song.parseJSONshit(File.getContent(haxe.io.Path.join([path, '../../data/' + song + '/' + song + '-easy.json'])));
							songName = data.song;
							iconP2 = data.player2;
						}*/
					}
					var daBox:ImportBox = {
						background: null,
						icon: null,
						nameText: null,
						importButton: null,
						miscButton: null
					}; 
					daBox.background = new FlxSprite(650 + FlxG.width*2, 10 + (180 * moduleStages.indexOf(path))).loadGraphic('assets/images/plainbox.png');
					daBox.icon = new HealthIcon('bf');
					daBox.icon.x = daBox.background.x + 5;
					daBox.icon.scrollFactor.set(1, 1);
					daBox.nameText = new FlxText(daBox.background.x + 180, daBox.background.y, daBox.background.width - 240, stageName);
					daBox.nameText.setFormat('assets/fonts/vcr.otf', 40, 0xFFFFFFFF, 'left');
					daBox.importButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 20, moduleMode + " Stage", function():Void {
						if (moduleMode != 'Export')
							importStage(stage);
						else {
							ModuleFunctions.exportStage(stageName);
						}
					});
					daBox.miscButton = new FlxUIButton(daBox.background.x + daBox.background.width - 120, daBox.background.y + 60, "Nothing", function():Void {
						// just cuz
					});
					add(daBox.background);
					add(daBox.icon);
					add(daBox.nameText);
					add(daBox.importButton);
					add(daBox.miscButton);
					stageBoxes.push(daBox);
				}
			}
		}

		var backdrop = new FlxSprite(650 + FlxG.width*2, 0).makeGraphic(FlxG.width - 650, 50, 0xFF808080);
		backdrop.alpha = 0.7;
		add(backdrop);

		var stageText = new FlxText(650 + FlxG.width*2, 0, FlxG.width - 650, "Stages", 40);
		stageText.alignment = 'center';
		add(stageText);
	}
	function generateWeeks() {
		var backdrop = new FlxSprite(650 + FlxG.width*3, 0).makeGraphic(FlxG.width - 650, 50, 0xFF808080);
		backdrop.alpha = 0.7;
		add(backdrop);

		var weekText = new FlxText(650 + FlxG.width*3, 0, FlxG.width - 650, "Weeks", 40);
		weekText.alignment = 'center';
		add(weekText);
	}
	function generateOther() {
		var backdrop = new FlxSprite(650 + FlxG.width*4, 0).makeGraphic(FlxG.width - 650, 50, 0xFF808080);
		backdrop.alpha = 0.7;
		add(backdrop);

		var otherText = new FlxText(650 + FlxG.width*4, 0, FlxG.width - 650, "Other", 40);
		otherText.alignment = 'center';
		add(otherText);
	}
	function removeDaBox(box) {
		remove(box.background);
		remove(box.icon);
		remove(box.nameText);
		remove(box.importButton);
		remove(box.miscButton);
	}
	function checkFile(daName:String, pathType:String, path:String) {
		switch(pathType) {
			case 'song':
				var songPath = 'assets/songs/';
				var dataPath = 'assets/data/';
				if (moduleMode == 'Import') {
					var importSongPath = haxe.io.Path.join([ModuleFunctions.importSongsPath(), daName]);
					if (FileSystem.exists(haxe.io.Path.join([importSongPath, 'info.txt']))) {
						if (FileSystem.exists(songPath + daName) || FileSystem.exists(dataPath + daName)) {
							var daSongName = 'Null';
							var info = ModuleFunctions.processInfo(haxe.io.Path.join([importSongPath, 'info.txt']));
							daSongName = ModuleFunctions.getInfoValue(info, 'songname', daName);
							
						} else {
							importSong(daName);
						}
					}
				} else {
					if (FileSystem.exists(songPath + daName) || FileSystem.exists(dataPath + daName)) {
						
					} else {
						importSong(daName, null, path);
					}
				}
			case 'week':
			
			case 'stage':

			case 'char':
				var charPath = 'assets/images/custom_chars/';
				if (FileSystem.exists(charPath + daName)) {
					var daCharName = 'Null';
					var charImportPath = haxe.io.Path.join([ImportSettings.getImportPath('characters'), daName]);
					var info = ModuleFunctions.processInfo(haxe.io.Path.join([charImportPath, 'info.txt']));
					daCharName = ModuleFunctions.getInfoValue(info, 'charname', daName);
					
				} else {
					importChar(daName);
				}
		}
	}

	var songPlaying = null;
	function listenSong(path:String, song:String) {
		songPlaying = song;
		FlxG.sound.music.stop();
		if (songVocals != null)
			songVocals.stop();
		var inst:String = '';
		var voices:String = '';
		var songJson:SwagSong = null;
		trace('about to load songs');
		if (moduleMode == 'Import') {
			inst = haxe.io.Path.join([path, 'Inst.ogg']);
			voices = haxe.io.Path.join([path, 'Voices.ogg']);
			// Prefer hard, then normal, then easy.  The old two-item range
			// never reached the easy case.
			for (difficulty in ['hard', 'normal', 'easy']) {
				var chartPath = haxe.io.Path.join([path, difficulty + '.json']);
				if (sys.FileSystem.exists(chartPath)) {
					songJson = Song.parseJSONshit(File.getContent(chartPath));
					break;
				}
			}
		} else {
			inst = CoolUtil.getSongFile(song, path);
			voices = CoolUtil.getSongFile(song, path, false);
			for (chartName in [song + '-hard.json', song + '.json', song + '-easy.json']) {
				var chartPath = haxe.io.Path.join([path, '../../data', song, chartName]);
				if (sys.FileSystem.exists(chartPath)) {
					songJson = Song.parseJSONshit(File.getContent(chartPath));
					break;
				}
			}
		}
		trace('song loaded');
		if (!sys.FileSystem.exists(inst) || songJson == null) {
			selectMode.text = 'Unable to listen: missing audio or chart.';
			songPlaying = null;
			return;
		}
		var songInst = Sound.fromFile(inst);
		if (voices != null && sys.FileSystem.exists(voices)) {
			var tempVocalsPath = haxe.io.Path.join(['assets', 'module', 'tempVocals.ogg']);
			File.copy(voices, tempVocalsPath); // FlxSound has no direct Sound path swap.
			var vocalSound = Sound.fromFile(tempVocalsPath);
			songVocals = new FlxSound().loadEmbedded(vocalSound);
			FlxG.sound.list.add(songVocals);
		}
		FlxG.sound.playMusic(songInst);
		if (songVocals != null)
			songVocals.play();
		Conductor.mapBPMChanges(songJson);
		Conductor.changeBPM(songJson.bpm);
		syncVocals();

		FlxG.sound.music.onComplete = endSong;

		bf.loadMappedAnims(songJson, 'bf');
		gf.loadMappedAnims(songJson, 'dad');
	}
	var musicJson:Dynamic = CoolUtil.parseJson(FNFAssets.getText("assets/music/custom_menu_music/custom_menu_music.json"));
	function endSong() {
		songPlaying = null;
		FlxG.sound.music.stop();
		if (songVocals != null)
			songVocals.pause();
		bf.animationNotes = [];
		gf.animationNotes = [];
		Conductor.changeBPM(125);
		FlxG.sound.playMusic(FNFAssets.getSound('assets/music/custom_menu_music/'
			+ musicJson.Options
			+ '/options'
			+ TitleState.soundExt));
	}
	override function stepHit() {
		super.stepHit();
		if (songVocals != null) {
			if (songVocals.time > Conductor.songPosition + 10 || songVocals.time < Conductor.songPosition - 10) {
				syncVocals();
			}
		}
	}

	override function beatHit() {
		super.beatHit();
		if ((!bf.animation.curAnim.name.startsWith("sing") && bf.animation.curAnim.name != 'firstDeath') || bf.animation.finished)
			bf.dance();
		if (!gf.animation.curAnim.name.startsWith("sing") || gf.animation.finished)
			gf.dance();
	}

	function convertToBool(theInfo:String) { //this is stupid but i don't know the proper function
		var daBool:Bool = false;
		switch(theInfo) {
			case 'false':
				daBool = false;
			case 'true':
				daBool = true;
		}
		return daBool;
	}

	function importSong(path:String, rename = null, ?assets:String) {
		#if sys
		if (moduleMode == 'Import') {
			ImportSettings.ensureImportDirectories();
			var basePath = haxe.io.Path.join([ModuleFunctions.importSongsPath(), path]);
			var promptSongs:Array<Dynamic> = [
				{source:ImportSettings.normalizeSourcePath(basePath), willImport:true}
			];
			var requests = ImportPackageNamePrompt.collectUnnamedRoots(promptSongs);
			if (requests.length > 0) {
				selectMode.text = 'Name this package before importing.';
				openSubState(new ImportPackageNameSubState(requests, function(packageNames:Map<String, String>):Void {
					if (packageNames == null) {
						selectMode.text = 'Import cancelled before writing any files.';
						return;
					}
					importSongPackage(basePath, packageNames);
				}));
			} else {
				importSongPackage(basePath, null);
			}
		} else {
			var targetSongFolder = haxe.io.Path.join(['assets', 'songs', path]);
			var targetDataFolder = haxe.io.Path.join(['assets', 'data', path]);
			if (!FileSystem.exists(targetSongFolder))
				FileSystem.createDirectory(targetSongFolder);

			//File.copy(CoolUtil.getSongFile(path, haxe.io.Path.join([assets, 'songs/' + path + '/'])), 'assets/songs/' + path + '/Inst.ogg');
			//File.copy(CoolUtil.getSongFile(path, haxe.io.Path.join([assets, 'songs/' + path + '/']), false), 'assets/songs/' + path + '/Voices.ogg');
			
			var sourceInst:String = null;
			for (candidate in [
				haxe.io.Path.join([assets, 'songs', path, 'Inst.ogg']),
				haxe.io.Path.join([assets, 'songs', path, path + '_Inst.ogg']),
				haxe.io.Path.join([assets, 'music', path + '_Inst.ogg'])
			]) {
				if (candidate != null && FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate)) {
					sourceInst = candidate;
					break;
				}
			}
			if (sourceInst == null) {
				selectMode.text = 'Unable to import: missing instrument audio.';
				return;
			}
			File.copy(sourceInst, haxe.io.Path.join([targetSongFolder, 'Inst.ogg']));

			var sourceVoices:String = null;
			for (candidate in [
				haxe.io.Path.join([assets, 'songs', path, 'Voices.ogg']),
				haxe.io.Path.join([assets, 'songs', path, path + '_Voices.ogg']),
				haxe.io.Path.join([assets, 'music', path + '_Voices.ogg'])
			]) {
				if (candidate != null && FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate)) {
					sourceVoices = candidate;
					break;
				}
			}
			if (sourceVoices != null)
				File.copy(sourceVoices, haxe.io.Path.join([targetSongFolder, 'Voices.ogg']));

			if (!FileSystem.exists(targetDataFolder))
				FileSystem.createDirectory(targetDataFolder);
			if (FileSystem.exists(haxe.io.Path.join([assets, 'data', path, 'dialog.txt'])))
				File.copy(haxe.io.Path.join([assets, 'data', path, 'dialog.txt']), haxe.io.Path.join([targetDataFolder, 'dialog.txt']));
			if (FileSystem.exists(haxe.io.Path.join([assets, 'data', path, 'modchart.hscript'])))
				File.copy(haxe.io.Path.join([assets, 'data', path, 'modchart.hscript']), haxe.io.Path.join([targetDataFolder, 'modchart.hscript']));

			var diffJson:TDifficulties = CoolUtil.parseJson(FNFAssets.getText("assets/images/custom_difficulties/difficulties.json"));
			for (i in 0...diffJson.difficulties.length) {
				switch(diffJson.difficulties[i].name) {
					case 'normal':
						if (FileSystem.exists(haxe.io.Path.join([assets, 'data', path, path + '.json'])))
							File.copy(haxe.io.Path.join([assets, 'data', path, path + '.json']), haxe.io.Path.join([targetDataFolder, path + '.json']));
					default:
						if (FileSystem.exists(haxe.io.Path.join([assets, 'data', path, path + '-' + diffJson.difficulties[i].name + '.json'])))
							File.copy(haxe.io.Path.join([assets, 'data', path, path + '-' + diffJson.difficulties[i].name + '.json']), haxe.io.Path.join([targetDataFolder, path + '-' + diffJson.difficulties[i].name + '.json']));
				}
			}
		}
		#end
	}

	/** Keep the legacy per-song module screen on the same ownership-aware path
	 * as Import Settings. The batch importer retains the source owner, plans a
	 * safe destination for collisions, and writes the matching Freeplay label. */
	function importSongPackage(basePath:String, packageNames:Map<String, String>):Void {
		var result = ModuleFunctions.importSongsFromPath(basePath, ImportSettings.MODDING_PLUS, null, packageNames);
		selectMode.text = ModuleFunctions.importBatchSummary(result, true);
	}

	function importChar(path:String, rename = null, ?assets:String) {
		#if sys
		if (moduleMode == 'Import') {
			ImportSettings.ensureImportDirectories();
			var basePath = haxe.io.Path.join([ImportSettings.getImportPath('characters'), path]);
			if (!FileSystem.isDirectory(basePath)) {
				selectMode.text = 'Unable to import character: folder not found.';
				return;
			}

			var info = ModuleFunctions.processInfo(haxe.io.Path.join([basePath, 'info.txt']));

			var numArray:Array<Float> = [];

			var theNums = ModuleFunctions.getInfoValue(info, 'iconnums', '0,1,2,3').split(',');
			for (i in 0...theNums.length)
				numArray.push(Std.parseFloat(theNums[i]));

			var charAssets = {
				"charpng": null,
				"charxml": null,
				"deadpng": null,
				"deadxml": null,
				"crazyxml": null,
				"crazypng": null,
				"icons": null
			};

			charAssets.charpng = haxe.io.Path.join([basePath, 'char.png']);
			if (FileSystem.exists(haxe.io.Path.join([basePath, 'char.txt'])))
				charAssets.charxml = haxe.io.Path.join([basePath, 'char.txt']);
			else
				charAssets.charxml = haxe.io.Path.join([basePath, 'char.xml']);
			if (!FileSystem.exists(charAssets.charpng) || !FileSystem.exists(charAssets.charxml)
				|| FileSystem.isDirectory(charAssets.charpng) || FileSystem.isDirectory(charAssets.charxml)) {
				selectMode.text = 'Unable to import character: char.png and char.xml/txt are required.';
				return;
			}

			if (FileSystem.exists(haxe.io.Path.join([basePath, 'dead.png'])))
				charAssets.deadpng = haxe.io.Path.join([basePath, 'dead.png']);
			if (FileSystem.exists(haxe.io.Path.join([basePath, 'dead.xml'])))
				charAssets.deadxml = haxe.io.Path.join([basePath, 'dead.xml']);

			if (FileSystem.exists(haxe.io.Path.join([basePath, 'crazy.png'])))
				charAssets.crazypng = haxe.io.Path.join([basePath, 'crazy.png']);
			if (FileSystem.exists(haxe.io.Path.join([basePath, 'crazy.xml'])))
				charAssets.crazyxml = haxe.io.Path.join([basePath, 'crazy.xml']);

			if (FileSystem.exists(haxe.io.Path.join([basePath, 'icons.png'])))
				charAssets.icons = haxe.io.Path.join([basePath, 'icons.png']);

			var likePath = null;

			if (FileSystem.exists(haxe.io.Path.join([basePath, 'like.hscript'])))
				likePath = haxe.io.Path.join([basePath, 'like.hscript']);

			var charData:ModuleFunctions.CharImport = {
				name: ModuleFunctions.getInfoValue(info, 'charname', path),
				like: ModuleFunctions.getInfoValue(info, 'like', path),
				likePath: likePath,
				assets: charAssets,
				iconNums: numArray,
				colors: ModuleFunctions.getInfoValue(info, 'colors', '255,255,255')
			};

			ModuleFunctions.importChar(charData);
		} else {
			var basePath = haxe.io.Path.join([assets, 'images/custom_chars/' + path]);

			/*if (FileSystem.exists(haxe.io.Path.join([assets, 'songs/' + path + '/Inst.ogg']))) {
				File.copy(haxe.io.Path.join([assets, 'songs/' + path + '/Inst.ogg']), 'assets/songs/' + path + '/Inst.ogg');
			*/
		}
		#end
	}
	function importStage(path:String, rename = null) {
		#if sys
		if (moduleMode != 'Import')
			return;
		ImportSettings.ensureImportDirectories();
		var basePath = haxe.io.Path.join([ImportSettings.getImportPath('stages'), path]);
		if (!FileSystem.isDirectory(basePath)) {
			selectMode.text = 'Unable to import stage: folder not found.';
			return;
		}
		var info = ModuleFunctions.processInfo(haxe.io.Path.join([basePath, 'info.txt']));
		var stageAssets:Array<String> = [];
		for (entry in FileSystem.readDirectory(basePath)) {
			var entryPath = haxe.io.Path.join([basePath, entry]);
			if (FileSystem.isDirectory(entryPath)) {
				// Exported modules place stage files in an assets/ subfolder.
				if (entry == 'assets') {
					for (asset in FileSystem.readDirectory(entryPath)) {
						var assetPath = haxe.io.Path.join([entryPath, asset]);
						if (!FileSystem.isDirectory(assetPath))
							stageAssets.push(assetPath);
					}
				}
			} else if (entry != 'info.txt' && entry != 'like.hscript') {
				stageAssets.push(entryPath);
			}
		}
		var stageData:ModuleFunctions.StageImport = {
			name: rename != null && StringTools.trim(rename) != '' ? StringTools.trim(rename) : ModuleFunctions.getInfoValue(info, 'stagename', path),
			like: ModuleFunctions.getInfoValue(info, 'like', path),
			likePath: FileSystem.exists(haxe.io.Path.join([basePath, 'like.hscript'])) ? haxe.io.Path.join([basePath, 'like.hscript']) : null,
			assets: stageAssets
		};
		ModuleFunctions.importStage(stageData);
		#end
	}
	function importWeek(path:String, rename = null) {
		
	}
	function syncVocals() {
		if (songPlaying != null && songVocals != null) {
			songVocals.pause();

			FlxG.sound.music.play();
			Conductor.songPosition = FlxG.sound.music.time;
			songVocals.time = Conductor.songPosition;
			songVocals.play();
		}
	}

	override public function destroy() {
		if (songVocals != null) {
			songVocals.stop();
			FlxG.sound.list.remove(songVocals);
			songVocals.destroy();
		}
		super.destroy();
	}
}
