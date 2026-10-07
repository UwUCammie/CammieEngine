package;

import flixel.util.FlxAxes;

import flixel.sound.FlxSound;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup;
import flixel.math.FlxMath;
import flixel.util.FlxTimer;

/**
 * Loosley based on FlxTypeText lolol
 */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionAlphabet extends FlxSpriteGroup
{
	public var delay:Float = 0.05;
	public var paused:Bool = false;

	public var changeAxis:FlxAxes = XY;

	// for menu shit
	public var forceX:Float = Math.NEGATIVE_INFINITY;
	public var targetY:Float = 0;
	public var yMult:Float = 120;
	public var xAdd:Float = 0;
	public var yAdd:Float = 0;
	public var isMenuItem:Bool = false;
	public var textSize:Float = 1.0;

	public var text:String = "";

	var _finalText:String = "";
	var yMulti:Float = 1;

	// custom shit
	// amp, backslash, question mark, apostrophy, comma, angry faic, period
	var lastSprite:Null<NightmareVisionAlphaCharacter> = null;
	var xPosResetted:Bool = false;

	var splitWords:Array<String> = [];

	public var isBold:Bool = false;
	public var lettersArray:Array<NightmareVisionAlphaCharacter> = [];

	public var finishedText:Bool = false;

	var context:NightmareVisionAlphabetContext;
	public function new(x:Float, y:Float, text:String = "", bold:Bool = false, textSize:Float = 1, ?context:NightmareVisionAlphabetContext)
	{
		super(x, y);
		if (context == null) throw "[nightmare-vision-alphabet] Missing selected context";
		this.context = context;
		NightmareVisionSpriteMethods.bind(this, context.getSpriteOwner());
		forceX = Math.NEGATIVE_INFINITY;
		this.textSize = textSize;

		_finalText = text;
		this.text = text;
		isBold = bold;

		if (text != "")
		{
			addText();
		}
		else
		{
			finishedText = true;
		}
	}

	public function changeText(newText:String)
	{
		for (i in 0...lettersArray.length)
		{
			var letter = lettersArray[0];
			letter.destroy();
			remove(letter);
			lettersArray.remove(letter);
		}
		lettersArray = [];
		splitWords = [];
		loopNum = 0;
		xPos = 0;
		curRow = 0;
		consecutiveSpaces = 0;
		xPosResetted = false;
		finishedText = false;
		lastSprite = null;

		var lastX = x;
		x = 0;
		_finalText = newText;
		text = newText;

		if (text != "")
		{
			addText();
		}
		else
		{
			finishedText = true;
		}
		x = lastX;
	}

	public function addText()
	{
		doSplitWords();

		var xPos:Float = 0;
		for (character in splitWords)
		{
			// if (character.fastCodeAt() == " ")
			// {
			// }

			var spaceChar:Bool = (character == " " || (isBold && character == "_"));
			if (spaceChar)
			{
				consecutiveSpaces++;
			}

			var isNumber:Bool = context.numbers.indexOf(character) != -1;
			var isSymbol:Bool = context.symbols.indexOf(character) != -1;
			var isAlphabet:Bool = context.alphabet.indexOf(character.toLowerCase()) != -1;
			if ((isAlphabet || isSymbol || isNumber) && (!isBold || !spaceChar))
			{
				if (lastSprite != null)
				{
					xPos = lastSprite.x + lastSprite.width;
				}

				if (consecutiveSpaces > 0)
				{
					xPos += 40 * consecutiveSpaces * textSize;
				}
				consecutiveSpaces = 0;

				// var letter:NightmareVisionAlphaCharacter = new NightmareVisionAlphaCharacter(30 * loopNum, 0, textSize);
				var letter:NightmareVisionAlphaCharacter = new NightmareVisionAlphaCharacter(xPos, 0, textSize, context);

				if (isBold)
				{
					if (isNumber)
					{
						letter.createBoldNumber(character);
					}
					else if (isSymbol)
					{
						letter.createBoldSymbol(character);
					}
					else
					{
						letter.createBoldLetter(character);
					}
				}
				else
				{
					if (isNumber)
					{
						letter.createNumber(character);
					}
					else if (isSymbol)
					{
						letter.createSymbol(character);
					}
					else
					{
						letter.createLetter(character);
					}
				}

				add(letter);
				lettersArray.push(letter);

				lastSprite = letter;
			}

			// loopNum += 1;
		}
	}

	function doSplitWords():Void
	{
		splitWords = _finalText.split("");
	}

	var loopNum:Int = 0;
	var xPos:Float = 0;

	public var curRow:Int = 0;

	var dialogueSound:FlxSound = null;

	var consecutiveSpaces:Int = 0;

	var LONG_TEXT_ADD:Float = -24; // text is over 2 rows long, make it go up a bit

	public function timerCheck(?tmr:FlxTimer = null)
	{
		var autoBreak:Bool = false;
		if ((loopNum <= splitWords.length - 2 && splitWords[loopNum] == "\\" && splitWords[loopNum + 1] == "n")
			|| ((autoBreak = true) && xPos >= FlxG.width * 0.65 && splitWords[loopNum] == ' '))
		{
			if (autoBreak)
			{
				if (tmr != null) tmr.loops -= 1;
				loopNum += 1;
			}
			else
			{
				if (tmr != null) tmr.loops -= 2;
				loopNum += 2;
			}
			yMulti += 1;
			xPosResetted = true;
			xPos = 0;
			curRow += 1;
			if (curRow == 2) y += LONG_TEXT_ADD;
		}

		if (loopNum <= splitWords.length && splitWords[loopNum] != null)
		{
			var spaceChar:Bool = (splitWords[loopNum] == " " || (isBold && splitWords[loopNum] == "_"));
			if (spaceChar)
			{
				consecutiveSpaces++;
			}

			var isNumber:Bool = context.numbers.indexOf(splitWords[loopNum]) != -1;
			var isSymbol:Bool = context.symbols.indexOf(splitWords[loopNum]) != -1;
			var isAlphabet:Bool = context.alphabet.indexOf(splitWords[loopNum].toLowerCase()) != -1;

			if ((isAlphabet || isSymbol || isNumber) && (!isBold || !spaceChar))
			{
				if (lastSprite != null && !xPosResetted)
				{
					lastSprite.updateHitbox();
					xPos += lastSprite.width + 3;
					// if (isBold)
					// xPos -= 80;
				}
				else
				{
					xPosResetted = false;
				}

				if (consecutiveSpaces > 0)
				{
					xPos += 20 * consecutiveSpaces * textSize;
				}
				consecutiveSpaces = 0;

				// var letter:NightmareVisionAlphaCharacter = new NightmareVisionAlphaCharacter(30 * loopNum, 0, textSize);
				var letter:NightmareVisionAlphaCharacter = new NightmareVisionAlphaCharacter(xPos, 55 * yMulti, textSize, context);
				letter.row = curRow;
				if (isBold)
				{
					if (isNumber)
					{
						letter.createBoldNumber(splitWords[loopNum]);
					}
					else if (isSymbol)
					{
						letter.createBoldSymbol(splitWords[loopNum]);
					}
					else
					{
						letter.createBoldLetter(splitWords[loopNum]);
					}
				}
				else
				{
					if (isNumber)
					{
						letter.createNumber(splitWords[loopNum]);
					}
					else if (isSymbol)
					{
						letter.createSymbol(splitWords[loopNum]);
					}
					else
					{
						letter.createLetter(splitWords[loopNum]);
					}
				}
				letter.x += 90;

				add(letter);

				lastSprite = letter;
			}
		}

		loopNum++;
		if (loopNum >= splitWords.length)
		{
			finishedText = true;
		}
	}

	override public function update(elapsed:Float)
	{
		if (isMenuItem)
		{
			var scaledY = FlxMath.remapToRange(targetY, 0, 1, 0, 1.3);

			final lerpRate = FlxMath.getElapsedLerp(0.16, elapsed);

			if (changeAxis.y) y = FlxMath.lerp(y, (scaledY * yMult) + (FlxG.height * 0.48) + yAdd, lerpRate);
			if (forceX != Math.NEGATIVE_INFINITY)
			{
				if (changeAxis.x) x = forceX;
			}
			else
			{
				if (changeAxis.x) x = FlxMath.lerp(x, (targetY * 20) + 90 + xAdd, lerpRate);
			}
		}

		super.update(elapsed);
	}

	public function snapToTarget()
	{
		if (isMenuItem)
		{
			final scaledY = FlxMath.remapToRange(targetY, 0, 1, 0, 1.3);

			y = (scaledY * yMult) + (FlxG.height * 0.48) + yAdd;
			if (forceX != Math.NEGATIVE_INFINITY)
			{
				x = forceX;
			}
			else
			{
				x = (targetY * 20) + 90 + xAdd;
			}
		}
	}
}
