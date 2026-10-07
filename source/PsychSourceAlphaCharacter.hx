package;
import flixel.FlxSprite;
using StringTools;
@:keep
class PsychSourceAlphaCharacter extends FlxSprite
{
	//public static var alphabet:String = "abcdefghijklmnopqrstuvwxyz";
	//public static var numbers:String = "1234567890";
	//public static var symbols:String = "|~#$%()*+-:;<=>@[]^_.,'!?";

	public var image(default, set):String;

	public static var allLetters:Map<String, Null<PsychAlphabetLetter>>;

	/** Unscoped native calls require an explicit owner context. Script scopes bind this real API. */
	public static function loadAlphabetData(request:String = 'alphabet', ?context:PsychAlphabetContext):Void {
		if (context == null) throw '[source-alphabet] Static loader requires a selected context';
		context.loadAlphabetData(request);
	}

	var parent:PsychSourceAlphabet;
	public var alignOffset:Float = 0; //Don't change this
	public var letterOffset:Array<Float> = [0, 0];

	public var row:Int = 0;
	public var rowWidth:Float = 0;
	public var character:String = '?';
	var context:PsychAlphabetContext;
	public function new(?context:PsychAlphabetContext)
	{
		super(x, y);
		if (context == null) throw '[source-alphabet] Missing selected context';
		this.context = context;
		image = 'alphabet';
		antialiasing = context.antialiasing();
	}

	public var curLetter:PsychAlphabetLetter = null;
	public function setupAlphaCharacter(x:Float, y:Float, ?character:String = null, ?bold:Null<Bool> = null)
	{
		this.x = x;
		this.y = y;

		if(parent != null)
		{
			if(bold == null)
				bold = parent.bold;
			this.scale.x = parent.scaleX;
			this.scale.y = parent.scaleY;
		}

		if(character != null)
		{
			this.character = character;
			curLetter = null;
			var lowercase:String = this.character.toLowerCase();
			if(context.allLetters.exists(lowercase)) curLetter = context.allLetters.get(lowercase);
			else curLetter = context.allLetters.get('?');

			var postfix:String = '';
			if(!bold)
			{
				if(isTypeAlphabet(lowercase))
				{
					if(lowercase != this.character)
						postfix = ' uppercase';
					else
						postfix = ' lowercase';
				}
				else postfix = ' normal';
			}
			else postfix = ' bold';

			var alphaAnim:String = lowercase;
			if(curLetter != null && curLetter.anim != null) alphaAnim = curLetter.anim;

			var anim:String = alphaAnim + postfix;
			animation.addByPrefix(anim, anim, 24);
			animation.play(anim, true);
			if(animation.curAnim == null)
			{
				if(postfix != ' bold') postfix = ' normal';
				anim = 'question' + postfix;
				animation.addByPrefix(anim, anim, 24);
				animation.play(anim, true);
			}
		}
		updateHitbox();
	}

	public static function isTypeAlphabet(c:String) // thanks kade
	{
		var ascii = StringTools.fastCodeAt(c, 0);
		return (ascii >= 65 && ascii <= 90)
			|| (ascii >= 97 && ascii <= 122)
			|| (ascii >= 192 && ascii <= 214)
			|| (ascii >= 216 && ascii <= 246)
			|| (ascii >= 248 && ascii <= 255);
	}

	private function set_image(name:String)
	{
		if(frames == null) //first setup
		{
			image = name;
			frames = context.atlas(name);
			return name;
		}

		var lastAnim:String = null;
		if (animation != null)
		{
			lastAnim = animation.name;
		}
		image = name;
		frames = context.atlas(name);
		this.scale.x = parent.scaleX;
		this.scale.y = parent.scaleY;
		alignOffset = 0;

		if (lastAnim != null)
		{
			animation.addByPrefix(lastAnim, lastAnim, 24);
			animation.play(lastAnim, true);

			updateHitbox();
		}
		return name;
	}

	public function updateLetterOffset()
	{
		if (animation.curAnim == null)
		{
			trace(character);
			return;
		}

		var add:Float = 110;
		if(animation.curAnim.name.endsWith('bold'))
		{
			if(curLetter != null && curLetter.offsetsBold != null)
			{
				letterOffset[0] = curLetter.offsetsBold[0];
				letterOffset[1] = curLetter.offsetsBold[1];
			}
			add = 70;
		}
		else
		{
			if(curLetter != null && curLetter.offsets != null)
			{
				letterOffset[0] = curLetter.offsets[0];
				letterOffset[1] = curLetter.offsets[1];
			}
		}
		add *= scale.y;
		offset.x += letterOffset[0] * scale.x;
		offset.y += letterOffset[1] * scale.y - (add - height);
	}

	override public function updateHitbox()
	{
		super.updateHitbox();
		updateLetterOffset();
	}
}
