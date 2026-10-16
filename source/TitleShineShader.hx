package;

import flixel.system.FlxAssets.FlxShader;
import openfl.display.BitmapData;

/**
	Light gliding across the neon CAMMIE ENGINE lettering of the title logo.

	The logo atlas has a twin, assets/images/logoBumpinShine.png, with the same
	size and layout (see tools/generate_title_logo.py). Its red channel is how
	much the shine applies at that pixel (1 on the neon tube, a few percent on
	its glow, 0 on the lettering above and the splash) and its green channel is the position along
	the text line, 0 at the left end and 1 at the right end in every bump frame.

	A soft band centred on `uShineCenter` (in those 0..1 units, `uShineWidth`
	to each side) moves the neon pixels toward light blue, pink,
	white, pink and light blue from one edge of the band to the other. Outside
	the band, and wherever the mask is 0, the pixel is the logo unchanged.
	OpenFL textures are premultiplied, so the tint is scaled by the pixel's
	alpha before it is mixed.
**/
class TitleShineShader extends FlxShader
{
	/** Band centre that no pixel can reach: the shine is off. */
	public static inline var IDLE:Float = -10.0;

	@:glFragmentSource('
		#pragma header
		uniform sampler2D uShineMask;
		uniform float uShineCenter;
		uniform float uShineWidth;
		uniform float uShineStrength;

		const vec3 SHINE_BLUE = vec3(0.3569, 0.8078, 0.9804);
		const vec3 SHINE_PINK = vec3(0.9608, 0.6627, 0.7216);

		vec3 shineTint(float edge)
		{
			vec3 core = mix(vec3(1.0), SHINE_PINK, smoothstep(0.1, 0.3, edge));
			return mix(core, SHINE_BLUE, smoothstep(0.4, 0.62, edge));
		}

		void main()
		{
			vec4 base = flixel_texture2D(bitmap, openfl_TextureCoordv);
			vec2 mask = texture2D(uShineMask, openfl_TextureCoordv).rg;
			float edge = abs(mask.g - uShineCenter) / uShineWidth;
			float amount = (1.0 - smoothstep(0.8, 1.0, edge)) * mask.r * uShineStrength;
			gl_FragColor = vec4(mix(base.rgb, shineTint(edge) * base.a, amount), base.a);
		}')
	public function new()
	{
		super();
		uShineCenter.value = [IDLE];
		uShineWidth.value = [0.12];
		uShineStrength.value = [0.92];
	}

	public function setMask(mask:BitmapData):Void
	{
		uShineMask.input = mask;
		uShineMask.filter = LINEAR;
	}

	public function setCenter(center:Float):Void
	{
		uShineCenter.value = [center];
	}
}
