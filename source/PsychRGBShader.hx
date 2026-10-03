package;

import flixel.system.FlxAssets.FlxShader;

/** Psych 0.7.x channel palette shader shared by notes with the same palette. */
@:access(openfl.display.Shader)
class PsychRGBShader extends FlxShader {
	@:glFragmentHeader('
		#pragma header
		uniform vec3 r;
		uniform vec3 g;
		uniform vec3 b;
		uniform float mult;
		uniform float u_alpha;
		uniform float u_flash;
	')
	@:glFragmentSource('
		#pragma header
		void main() {
			vec4 color = flixel_texture2D(bitmap, openfl_TextureCoordv);
			if (color.a > 0.0 && mult > 0.0) {
				vec3 mapped = min(color.r * r + color.g * g + color.b * b, vec3(1.0));
				color.rgb = mix(color.rgb, mapped, mult);
			}
			// Nightmare Vision extends the same Psych palette mapping with
			// draw alpha and stealth flash; identity defaults preserve Psych.
			if (u_flash != 0.0)
				color = mix(color, vec4(1.0), u_flash) * color.a;
			gl_FragColor = color * u_alpha;
		}
	')
	public function new() {
		super();
		// Ensure generated parameters exist before assigning identity defaults,
		// independently of the shader macro's appended initialization.
		__isGenerated = true;
		__initGL();
		if (r == null || g == null || b == null || mult == null || u_alpha == null || u_flash == null) {
			var diagnosticSource = glFragmentSource == null ? '' : glFragmentSource;
			var declarations = [
				'uniform vec3 r', 'uniform vec3 g', 'uniform vec3 b',
				'uniform float mult', 'uniform float u_alpha', 'uniform float u_flash'
			];
			var declarationPositions:Array<String> = [];
			for (declaration in declarations)
				declarationPositions.push(declaration + '=' + diagnosticSource.indexOf(declaration));
			var sourcePreview = diagnosticSource.substr(0, 3000);
			throw '[psych-rgb-shader-bindings] Missing generated parameters; data=' + Reflect.fields(__data).join(',')
				+ ' floats=' + __paramFloat.length + ' sourceLength=' + diagnosticSource.length
				+ ' declarations=' + declarationPositions.join(',') + ' source=' + sourcePreview;
		}
		u_alpha.value = [1.0];
		u_flash.value = [0.0];
	}
}
