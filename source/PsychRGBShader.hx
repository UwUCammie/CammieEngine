package;

import flixel.system.FlxAssets.FlxShader;

/** Psych 0.7.x channel palette shader shared by notes with the same palette. */
class PsychRGBShader extends FlxShader {
	@:glFragmentHeader('
		#pragma header
		uniform vec3 r;
		uniform vec3 g;
		uniform vec3 b;
		uniform float mult;
	')
	@:glFragmentSource('
		#pragma header
		void main() {
			vec4 color = flixel_texture2D(bitmap, openfl_TextureCoordv);
			if (color.a > 0.0 && mult > 0.0) {
				vec3 mapped = min(color.r * r + color.g * g + color.b * b, vec3(1.0));
				color.rgb = mix(color.rgb, mapped, mult);
			}
			gl_FragColor = color;
		}
	')
	public function new() {
		super();
	}
}
