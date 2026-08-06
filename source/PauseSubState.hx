package;

import Controls.Control;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.FlxSubState;
import flixel.addons.transition.FlxTransitionableState;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.input.keyboard.FlxKey;
import flixel.sound.FlxSound;
import flixel.util.FlxColor;
import flixel.FlxCamera;

class PauseSubState extends MusicBeatSubstate {
	var grpMenuShit:FlxTypedGroup<Alphabet>;

	var songNameTxt:FlxText;
	var curDiffTxt:FlxText;
	var deathsTxt:FlxText;

	var menuItems:Array<String> = ['Resume', 'Restart Song', 'Change Difficulty', 'Change Modifiers', 'Change Options', 'Charting', 'Exit to menu'];
	var curSelected:Int = 0;

	var inDiffs:Bool = false;
	var diffNames:Array<String> = ['Back', 'Hard', 'Normal', 'Easy'];
	var diffs:Array<Int> = [];

	var pauseMusic:FlxSound;

	public function new(x:Float, y:Float, camera:FlxCamera) {
		super();

		pauseMusic = new FlxSound().loadEmbedded('assets/music/breakfast' + TitleState.soundExt, true, true);
		pauseMusic.volume = 0;
		pauseMusic.play(false, FlxG.random.int(0, Std.int(pauseMusic.length / 2)));
		FlxG.sound.list.add(pauseMusic);

		var bg:FlxSprite = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
		bg.alpha = 0.6;
		bg.scrollFactor.set();
		add(bg);

		grpMenuShit = new FlxTypedGroup<Alphabet>();
		add(grpMenuShit);

		if (PlayState.SONG.cutsceneType != 'none')
			menuItems.insert(2, "Replay Cutscene");

		makeMenuItems(menuItems);

		songNameTxt = new FlxText(0, 20, FlxG.width - 10, PlayState.SONG.song, 32);
		songNameTxt.font = "assets/fonts/vcr.ttf";
		songNameTxt.alignment = RIGHT;
		add(songNameTxt);

		curDiffTxt = new FlxText(0, 55, FlxG.width - 10, "Difficulty: " + PlayState.storyDifficultyText, 32);
		curDiffTxt.font = "assets/fonts/vcr.ttf";
		curDiffTxt.alignment = RIGHT;
		add(curDiffTxt);

		deathsTxt = new FlxText(0, 90, FlxG.width - 10, PlayState.balls + " Blue Balls", 32);
		deathsTxt.font = "assets/fonts/vcr.ttf";
		deathsTxt.alignment = RIGHT;
		add(deathsTxt);

		changeSelection();

		cameras = [camera];
	}

	function makeMenuItems(items) {
		grpMenuShit.clear();

		for (i in 0...items.length) {
			var songText:Alphabet = new Alphabet(0, (70 * i) + 30, items[i], true, false);
			songText.isMenuItem = true;
			songText.targetY = i;
			grpMenuShit.add(songText);
		}
	}

	override function update(elapsed:Float) {
		if (pauseMusic.volume < 0.5)
			pauseMusic.volume += 0.01 * elapsed;

		super.update(elapsed);

		var upP = controls.UP_MENU;
		var downP = controls.DOWN_MENU;
		var accepted = controls.ACCEPT;

		if (upP)
			changeSelection(-1);
		if (downP)
			changeSelection(1);

		if (accepted) {
			if (!inDiffs) {
				var daSelected:String = menuItems[curSelected];

				switch (daSelected) {
					case "Resume":
						close();
					case "Restart Song":
						FlxG.resetState();
					case "Replay Cutscene":
						PlayState.watchedCutscene = false;
						FlxG.resetState();
					case "Charting":
						LoadingState.loadAndSwitchState(new ChartingState());
					case "Exit to menu":
						if (PlayState.isStoryMode)
							LoadingState.loadAndSwitchState(new StoryMenuState());
						else
							LoadingState.loadAndSwitchState(new FreeplayState());
					case "Change Modifiers":
						LoadingState.loadAndSwitchState(new ModifierState());
					case "Change Options":
						SaveDataState.prevPath = 'freeplay';
						LoadingState.loadAndSwitchState(new SaveDataState());
					case "Change Difficulty":
						diffs = DifficultyManager.supportedDiff.get(PlayState.SONG.song.toLowerCase());
						diffNames = ["Back"];
						for (diff in diffs) {
							diffNames.push(DifficultyManager.getDiffName(diff).toUpperCase());
						}
						inDiffs = true;
						makeMenuItems(diffNames);
						curSelected = 0;
						changeSelection();
				}
			} else {
				var daSelected:String = diffNames[curSelected];

				if (daSelected == 'Back') {
					makeMenuItems(menuItems);
					inDiffs = false;
					curSelected = 0;
					changeSelection();
				} else {
					PlayState.SONG = daSelected.toLowerCase() == 'normal'
						? Song.loadFromJson(PlayState.SONG.song.toLowerCase(), PlayState.SONG.song.toLowerCase())
						: Song.loadFromJson(PlayState.SONG.song.toLowerCase() + '-' + daSelected.toLowerCase(), PlayState.SONG.song.toLowerCase());
					PlayState.storyDifficulty = diffs[curSelected - 1];
					FlxG.resetState();
				}
			}
		}

		if (FlxG.keys.justPressed.J) {
			// for reference later!
			// PlayerSettings.player1.controls.replaceBinding(Control.LEFT, Keys, FlxKey.J, null);
		}
	}

	override function destroy() {
		pauseMusic.destroy();

		super.destroy();
	}

	function changeSelection(change:Int = 0):Void {
		curSelected += change;

		if (curSelected < 0)
			curSelected = grpMenuShit.length - 1;
		if (curSelected >= grpMenuShit.length)
			curSelected = 0;

		var bullShit:Int = 0;

		for (item in grpMenuShit.members) {
			item.targetY = bullShit - curSelected;
			bullShit++;

			item.alpha = 0.6;
			// item.setGraphicSize(Std.int(item.width * 0.8));

			if (item.targetY == 0) {
				item.alpha = 1;
				// item.setGraphicSize(Std.int(item.width));
			}
		}
	}
}
