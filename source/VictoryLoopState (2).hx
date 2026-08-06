package;

import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSubState;
import flixel.math.FlxPoint;
import flixel.util.FlxColor;
import flixel.util.FlxTimer;
import flixel.text.FlxText;
import lime.system.System;
import flixel.FlxSprite;
import flixel.FlxCamera;
import lime.utils.Assets;
#if sys
import sys.io.File;
import sys.FileSystem;
import haxe.io.Path;
import Song.SwagSong;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import flash.media.Sound;
#end
import haxe.Json;
import tjson.TJSON;
using StringTools;
class VictoryLoopState extends MusicBeatSubstate {
	var bf:Character;
	var gf:Character;
	var dad:Character;

	var dancer:Character;
	var otherGuy:Character;

	var camFollow:FlxObject;
	var stageSuffix:String = "";
	var victoryTxt:Alphabet;
	var retryTxt:Alphabet;
	var continueTxt:Alphabet;
	var scoreTxt:Alphabet;
	var rating:Alphabet;
	var selectingRetry:Bool = false;

	var accuracy:Float;

	var accuracyTxt:FlxText;
	var camHUD:FlxCamera;
	public function new(x:Float, y:Float, gfX:Float, gfY:Float, accuracy:Float, score:Int, dadX:Float, dadY:Float) {
		trace('in victoryloopstate');
		//var background:FlxSprite = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.PINK);
		//add(background);
		var daStage = PlayState.curStage;
		this.accuracy = accuracy;
		
		victoryTxt = new Alphabet(10, 10, "Victory", true);

				gf = new Character(gfX, gfY, PlayState.SONG.gf);
		add(gf);
		
		/*if (PlayState.opponentPlayer)
			bf = new Character(dadX, dadY, PlayState.SONG.player2);
		else*/
			bf = new Character(x, y, PlayState.SONG.player1, true);
		bf.beingControlled = true;
		bf.beNormal = false;
		if (PlayState.opponentPlayer) {
			bf.visible = false;
		}
		add(bf);

		dad = new Character(dadX, dadY, PlayState.SONG.player2);
		dad.beingControlled = true;
		dad.beNormal = false;
		if (!PlayState.duoMode && !PlayState.opponentPlayer) {
			dad.visible = false;
		}
		add(dad);

		retryTxt = new Alphabet(10, FlxG.height, "Replay", true);
		retryTxt.y -= retryTxt.height;
		retryTxt.alpha = 0.6;

		continueTxt = new Alphabet(10, FlxG.height - retryTxt.height, "Continue", true);
		continueTxt.y -= scoreTxt.height;

		scoreTxt = new Alphabet(10, victoryTxt.y + victoryTxt.height, Std.string(score), true);

		/*var sickTxt = new Alphabet(10, scoreTxt.y + scoreTxt.height, Std.string(PlayState.sicks), true);
		add(sickTxt);
		var goodTxt = new Alphabet(10, sickTxt.y + sickTxt.height, Std.string(PlayState.goods), true);
		add(goodTxt);
		var badTxt = new Alphabet(10, goodTxt.y + goodTxt.height, Std.string(PlayState.bads), true);
		add(badTxt);
		var shitTxt = new Alphabet(10, badTxt.y + badTxt.height, Std.string(PlayState.shits), true);
		add(shitTxt);
		var missTxt = new Alphabet(10, shitTxt.y + shitTxt.height, Std.string(PlayState.misses), true);
		add(missTxt);*/

		rating = new Alphabet(10, FlxG.height/2, "", true, 90, 0.48, true);
		rating.setGraphicSize(3);
		rating.updateHitbox();
		rating.text = Ratings.GenerateLetterRank(accuracy);
		rating.addText();

		accuracyTxt = new FlxText(10, rating.y + rating.height,0 , "ACCURACY: "+ HelperFunctions.truncateFloat(accuracy, 2) + "%");
		accuracyTxt.setFormat("assets/fonts/vcr.ttf", 26, FlxColor.WHITE, RIGHT);

		var interp = Character.getAnimInterp(PlayState.SONG.player1);
		if (interp.variables.exists("isPixel") && interp.variables.get("isPixel")) {
			stageSuffix = '-pixel';
		}
		super();
		trace('victoryloopstate super');

		Conductor.songPosition = 0;
		
		if (PlayState.opponentPlayer) {
			dancer = dad;
			otherGuy = bf;
		} else {
			dancer = bf;
			otherGuy = dad;
		}
		if (PlayState.duoMode) {
			camFollow = new FlxObject(gf.getGraphicMidpoint().x, gf.getGraphicMidpoint().y, 1, 1);
		} else {
			camFollow = new FlxObject(dancer.getGraphicMidpoint().x, dancer.getGraphicMidpoint().y, 1, 1);
		}

		trace('victoryloopstate before adding');

		add(camFollow);
		add(victoryTxt);
		add(retryTxt);
		add(scoreTxt);
		add(continueTxt);
		add(rating);
		add(accuracyTxt);
		retryTxt.visible = false;
		continueTxt.visible = false;
		rating.visible = false;
		scoreTxt.visible = false;
		accuracyTxt.visible = false;
		// make files seperate to allow modding
		if (accuracy >= 65) {
			Conductor.changeBPM(150);
			FlxG.sound.playMusic('assets/music/goodScore' + TitleState.soundExt);
		} else if (accuracy >= 50) {
			Conductor.changeBPM(100);
			FlxG.sound.playMusic('assets/music/mehScore' + TitleState.soundExt);
		} else {
			Conductor.changeBPM(100);
			FlxG.sound.playMusic('assets/music/badScore' + TitleState.soundExt);
		}

		// FlxG.camera.followLerp = 1;
		// FlxG.camera.focusOn(FlxPoint.get(FlxG.width / 2, FlxG.height / 2));
		FlxG.camera.scroll.set();
		FlxG.camera.target = null;
		FlxG.camera.follow(camFollow, LOCKON, 0.01);
		FlxG.camera.x = camFollow.x;
		FlxG.camera.y = camFollow.y;
		dancer.playAnim('idle');

		trace('victoryloopstate past everything');
	}

	override function update(elapsed:Float) {
		super.update(elapsed);

		if (controls.ACCEPT) {
			if (selectingRetry && !PlayState.isStoryMode) {
				endBullshit();
			} else {
				FlxG.sound.music.stop();

				if (PlayState.isStoryMode)
					LoadingState.loadAndSwitchState(new StoryMenuState());
				else
					LoadingState.loadAndSwitchState(new FreeplayState());
			}
		}

		if ((controls.UP_MENU || controls.DOWN_MENU)) {
			selectingRetry = !selectingRetry;
			if (selectingRetry) {
				retryTxt.alpha = 1;
				continueTxt.alpha = 0.6;
			} else {
				retryTxt.alpha = 0.6;
				continueTxt.alpha = 1;
			}
		}
		if (FlxG.sound.music.playing) {
			Conductor.songPosition = FlxG.sound.music.time;
		}
	}

	override function beatHit() {
		super.beatHit();
		switch(curBeat) {
			case 3:
				scoreTxt.visible = true;
			case 5:
				rating.visible = true;
				accuracyTxt.visible = true;
			case 8:
				retryTxt.visible = true;
				continueTxt.visible = true;
		}
		if (accuracy >= 0.65) {
			gf.dance();
		} else {
			gf.playAnim('sad');
			if (gf.animation.curAnim.name != 'sad') {
				// boogie if no sad anim, looks kinda silly
				gf.dance();
			}
		}

		FlxG.log.add('beat');
		if (curBeat % 2 == 0 && accuracy >= 65) {
			switch(dancer.animation.curAnim.name) {
				case "idle":
					dancer.sing(2);
					otherGuy.sing(1);
				case "singLEFT":
					dancer.sing(2);
					otherGuy.sing(1);
				case "singUP":
					dancer.sing(3);
					otherGuy.sing(0);
				case "singRIGHT":
					dancer.sing(1);
					otherGuy.sing(2);
				case "singDOWN":
					dancer.sing(0);
					otherGuy.sing(3);
			}
		} else if (curBeat % 2 == 0){
			// funny look he misses now
			switch(dancer.animation.curAnim.name) {
				case "idle":
					dancer.sing(2, true);
					otherGuy.sing(1, true);
				case "singLEFTmiss":
					dancer.sing(2, true);
					otherGuy.sing(1, true);
				case "singUPmiss":
					dancer.sing(3, true);
					otherGuy.sing(1, true);
				case "singRIGHTmiss":
					dancer.sing(1, true);
					otherGuy.sing(1, true);
				case "singDOWNmiss":
					dancer.sing(0, true);
					otherGuy.sing(1, true);
			}
		}
	}

	var isEnding:Bool = false;
	function endBullshit():Void {
		if (!isEnding) {
			isEnding = true;
			FlxG.sound.music.stop();
			FlxG.sound.play('assets/music/gameOverEnd' + stageSuffix + TitleState.soundExt);
			if (PlayState.isStoryMode) {
				// most variables should already be set?
				PlayState.storyPlaylist = StoryMenuState.storySongPlaylist;
				trace(PlayState.storyPlaylist);
				var diffic = DifficultyIcons.getEndingFP(PlayState.storyDifficulty);
				for (peckUpAblePath in PlayState.storyPlaylist) {
					if (!FNFAssets.exists('assets/data/'+peckUpAblePath.toLowerCase()+'/'+peckUpAblePath.toLowerCase() + diffic+'.json')) {
						// probably messed up difficulty
						trace("UH OH DIFFICULTY DOESN'T EXIST FOR A SONG");
						trace("CHANGING TO DEFAULT DIFFICULTY");
						diffic = "";
						PlayState.storyDifficulty = DifficultyIcons.getDefaultDiffFP();
					}
				}
				PlayState.SONG = Song.loadFromJson(StoryMenuState.storySongPlaylist[0].toLowerCase() + diffic, StoryMenuState.storySongPlaylist[0].toLowerCase());
				PlayState.campaignScore = 0;
				PlayState.campaignAccuracy = 0;
			}
			new FlxTimer().start(0.7, function(tmr:FlxTimer) {
				FlxG.camera.fade(FlxColor.BLACK, 2, false, function() {
					LoadingState.loadAndSwitchState(new PlayState());
				});
			});
		}
	}
}
