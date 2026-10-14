package shaders;

import flixel.system.FlxAssets.FlxShader;

/**
	Hue, saturation, brightness and contrast, matching the Animate/Flash "Adjust
	Color" filter. V-Slice stages and song scripts build this class by name and
	set the four values directly, so the engine provides it as a base-game shader
	that every script layer can construct.

	The colour maths is the same as assets/shaders/adjustColor.frag and the adjust
	part of DropShadowShader: the shader takes the raw values and does every
	conversion itself. The uniforms carry a `u` prefix because the plain names
	are the public properties scripts write.
**/
class AdjustColorShader extends FlxShader
{
	/** Hue rotation in degrees. */
	public var hue(default, set):Float = 0;

	/** Saturation, -100 to 100. */
	public var saturation(default, set):Float = 0;

	/** Brightness, -255 to 255. */
	public var brightness(default, set):Float = 0;

	/** Contrast, -100 to 100. */
	public var contrast(default, set):Float = 0;

	function set_hue(value:Float):Float
	{
		hue = value;
		uHue.value = [value];
		return value;
	}

	function set_saturation(value:Float):Float
	{
		saturation = value;
		uSaturation.value = [value];
		return value;
	}

	function set_brightness(value:Float):Float
	{
		brightness = value;
		uBrightness.value = [value];
		return value;
	}

	function set_contrast(value:Float):Float
	{
		contrast = value;
		uContrast.value = [value];
		return value;
	}

	@:glFragmentSource('
		#pragma header

		uniform float uHue;
		uniform float uSaturation;
		uniform float uBrightness;
		uniform float uContrast;

		const vec3 grayscaleValues = vec3(0.3098039215686275, 0.607843137254902, 0.0823529411764706);
		const float e = 2.718281828459045;

		vec3 applyHueRotate(vec3 aColor, float aHue){
			float angle = radians(aHue);

			mat3 m1 = mat3(0.213, 0.213, 0.213, 0.715, 0.715, 0.715, 0.072, 0.072, 0.072);
			mat3 m2 = mat3(0.787, -0.213, -0.213, -0.715, 0.285, -0.715, -0.072, -0.072, 0.928);
			mat3 m3 = mat3(-0.213, 0.143, -0.787, -0.715, 0.140, 0.715, 0.928, -0.283, 0.072);
			mat3 m = m1 + cos(angle) * m2 + sin(angle) * m3;

			return m * aColor;
		}

		vec3 applySaturation(vec3 aColor, float value){
			if(value > 0.0){ value = value * 3.0; }
			value = (1.0 + (value / 100.0));
			vec3 grayscale = vec3(dot(aColor, grayscaleValues));
			return clamp(mix(grayscale, aColor, value), 0.0, 1.0);
		}

		vec3 applyContrast(vec3 aColor, float value){
			value = (1.0 + (value / 100.0));
			if(value > 1.0){
				value = (((0.00852259 * pow(e, 4.76454 * (value - 1.0))) * 1.01) - 0.0086078159) * 10.0;
				value += 1.0;
			}
			return clamp((aColor - 0.25) * value + 0.25, 0.0, 1.0);
		}

		vec3 applyHSBCEffect(vec3 color){
			color = color + ((uBrightness) / 255.0);
			color = applyHueRotate(color, uHue);
			color = applyContrast(color, uContrast);
			color = applySaturation(color, uSaturation);
			return color;
		}

		void main(){
			vec4 textureColor = flixel_texture2D(bitmap, openfl_TextureCoordv);
			// Lime premultiplies alpha, so adjust the straight colour and premultiply again.
			vec3 unpremultipliedColor = textureColor.a > 0.0 ? textureColor.rgb / textureColor.a : textureColor.rgb;
			vec3 outColor = applyHSBCEffect(unpremultipliedColor);
			gl_FragColor = vec4(outColor * textureColor.a, textureColor.a);
		}
	')
	public function new()
	{
		super();
		// Uniforms have no value until set; write all four so the first draw is neutral.
		hue = 0;
		saturation = 0;
		brightness = 0;
		contrast = 0;
	}
}
