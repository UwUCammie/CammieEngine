package;

import flixel.math.FlxMath;
import Highscore.FCLevel;
import flixel.text.FlxText;
import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;

import Judge.Jury;
enum abstract DisplayOptions(Int) from Int to Int {
    var BestScore;
    var Recent;
    var BestAccuracy;
    var BestFc;
    var BestOverall;
    @:op(A > B) static function _(_,_):Bool;
	@:op(A >= B) static function _(_, _):Bool;
	@:op(A < B) static function _(_, _):Bool;
	@:op(A <= B) static function _(_, _):Bool;
	@:op(A == B) static function _(_, _):Bool;
    @:op(A + B) static function _(_,_):DisplayOptions;
    @:from static public function fromString(s:String) {
        return switch (s) {
            case "best-score":
                BestScore;
            case "recent":
                Recent;
            case "best-accuracy":
                BestAccuracy;
            case "best-fullcombo":
                BestFc;
            case "best":
                BestOverall;
            default:
                Recent;
        }
    }
    @:to static public function toString(d:DisplayOptions):String {
        return switch(d) {
            case BestScore:
                "best-score";
            case Recent:
                "recent";
            case BestAccuracy:
                "best-accuracy";
            case BestFc:
                "best-fullcombo";
            case BestOverall:
                "best";
        }
    }
}
class SongInfoPanel extends FlxTypedSpriteGroup<FlxSprite> {
    var backpanel:FlxSprite;
    var scoreTxt:FlxText;
    var accuracyTxt:FlxText;
    var fcTxt:FlxText;
    var judgeTxt:FlxText;
    var displaying:String = "best";
    var browser:Bool = false;
    var curSong:String = "tutorial";
    var displayTxt:FlxText;
    var curDiff:Int = 1;
    public function new(X:Float, Y:Float, song:String, diff:Int) {
        super(X, Y);

        curSong = song;
        curDiff = diff;
        backpanel = new FlxSprite().makeGraphic(400, 400, 0xCC000000);
        scoreTxt = new FlxText(20, 20, 350, "a", 22);
        accuracyTxt = new FlxText(20, 80, 0, "a", 22);
        fcTxt = new FlxText(20, 140, 0, "a", 22);
		judgeTxt = new FlxText(20, 200, 0,"a", 22);
        displayTxt = new FlxText(20, 260, 0, displaying, 22);
        add(backpanel);
        add(scoreTxt);
        //add(accuracyTxt);
        //add(fcTxt);
        //add(judgeTxt);
        add(displayTxt);
    }   
    public function setBrowserSize(panelWidth:Int, panelHeight:Int):Void {
        browser = true; displaying = "best-score";
        backpanel.makeGraphic(panelWidth, panelHeight, 0xCC101622);
        scoreTxt.font = 'assets/fonts/vcr.ttf'; displayTxt.font = scoreTxt.font;
        // Five score lines fill the card, so the Q / E mode label shares the first row.
        scoreTxt.size = 16; scoreTxt.fieldWidth = panelWidth - 32;
        scoreTxt.setPosition(x + 12, y + 8);
        displayTxt.size = 16; displayTxt.setPosition(x + panelWidth - 214, y + 8);
    }
    public function changeSong(song:String, diff:Int) {
        curSong = song;
        curDiff = diff;
        scoreTxt.text = "Score: " + Highscore.getScore(song, diff, displaying);
        //accuracyTxt.text = "Accuracy: " + CoolUtil.truncateFloat(Highscore.getAccuracy(song, diff, displaying) * 100, 2);
		var savedRank = Highscore.getRank(song, diff, displaying);
		scoreTxt.text += '\n' + "Accuracy: " + CoolUtil.truncateFloat(Highscore.getAccuracy(song, diff, displaying) * 100, 2)
			+ (savedRank == '' ? '' : ' (' + savedRank + ')');
        var fcUse:String = "FC Level:";
        switch (cast (Highscore.getFCLevel(song, diff, displaying) : FCLevel)) {
            case Sick:
                fcUse += "Sick";
            case Good:
                fcUse += "Good";
            case Bad:
                fcUse += "Bad";
            case Sdcb:
                fcUse += "Sdcb";
            case Clear:
                fcUse += "Clear";
            case None:
                fcUse += "None";
        } 
        scoreTxt.text += '\n' + fcUse;
        if (browser) scoreTxt.text += '\n' + PlayPerformance.label(Highscore.peekPerformance(song, diff, displaying));
        var sussyjudge = switch (cast (Highscore.getJudge(song, diff, displaying) : Judge.Jury)) {
            case Judge9:
                "Judge JUSTICE";
            case Classic:
                "Classic Judge";
            case Hard:
                "Hard Judge";
            case judgeee:
                "Judge " + (cast (judgeee : Int) + 1);
        }
		var songOptions = Highscore.getOptionsUsed(song, diff, displaying);
        var modifierUsed = Highscore.getModifiersUsed(song, diff, displaying);
        if (displaying != 'best' && !browser) {
			scoreTxt.text += '\n' + sussyjudge;
            // Purge references to ignore shitty timing :)
            /*
			if (songOptions.ignoreShittyTiming)
				scoreTxt.text += '\nUses virgin ignore shitty timing';
			else
				scoreTxt.text += '\nDoes not ignore shitties :)';
            */
            if (modifierUsed.mfc.value || modifierUsed.gfc.value || modifierUsed.fc.value) {
                scoreTxt.text += "\nTotally grinded for this lmao";
            }
        }
            
       
        displayTxt.text = (browser ? 'Q / E: ' : '') + displaying;
     }
     public function changeDisplay(change:Int=0) {
         var sussyOption:DisplayOptions = cast (displaying : DisplayOptions);
         sussyOption += change;
         sussyOption = FlxMath.wrap(sussyOption, 0, BestOverall);
		displaying = switch (sussyOption)
		{
			case BestScore:
				"best-score";
			case Recent:
				"recent";
			case BestAccuracy:
				"best-accuracy";
			case BestFc:
				"best-fullcombo";
			case BestOverall:
				"best";
		};
        changeSong(curSong, curDiff);
     }
}