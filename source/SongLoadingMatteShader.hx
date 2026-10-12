package;

import openfl.filters.BitmapFilterShader;

/** Matte only the bundled loading artwork's flat chartreuse backdrop.
	Other greens in the characters lie outside this narrow key range. */
class SongLoadingMatteShader extends BitmapFilterShader {
	@:glFragmentSource('
		#pragma header
		vec3 key = vec3(202.0 / 255.0, 1.0, 77.0 / 255.0);
		vec4 mattePixel(vec2 coordinate) {
			vec4 source = texture2D(openfl_Texture, coordinate);
			float difference = distance(source.rgb, key);
			if (difference < 0.04) return vec4(0.0);
			// Flattened antialiasing against lime also leaves warm yellow pixels
			// with red above green. Both channels exceed the old blue value.
			// Pale green highlights contain much more blue and are excluded.
			bool keyEdge = source.g > source.b * 1.40 && source.r > source.b * 1.15;
			if (keyEdge) {
				vec2 pixel = 1.0 / openfl_TextureSize;
				for (int y = -3; y <= 3; y++) {
					for (int x = -3; x <= 3; x++) {
						vec3 neighbor = texture2D(openfl_Texture, coordinate + vec2(float(x), float(y)) * pixel).rgb;
						if (distance(neighbor, key) < 0.04) return vec4(0.0);
					}
				}
			}
			float matte = smoothstep(0.04, 0.20, difference);
			vec3 edge = clamp((source.rgb - key * (1.0 - matte)) / max(matte, 0.001), 0.0, 1.0);
			return vec4(edge * source.a * matte, source.a * matte);
		}
		void main() {
			vec4 color = mattePixel(openfl_TextureCoordv);
			// Character silhouettes occupy the left half. The graffiti letters
			// begin beyond this gap and retain the original sharp matte output.
			if (openfl_TextureCoordv.x < 0.50) {
				vec2 pixel = 0.85 / openfl_TextureSize;
				vec4 right = mattePixel(openfl_TextureCoordv + vec2(pixel.x, 0.0));
				vec4 left = mattePixel(openfl_TextureCoordv - vec2(pixel.x, 0.0));
				vec4 down = mattePixel(openfl_TextureCoordv + vec2(0.0, pixel.y));
				vec4 up = mattePixel(openfl_TextureCoordv - vec2(0.0, pixel.y));
				float minimum = min(color.a, min(min(right.a, left.a), min(down.a, up.a)));
				float maximum = max(color.a, max(max(right.a, left.a), max(down.a, up.a)));
				// Blend only silhouettes, including the immediately adjacent outside
				// pixels. Premultiplied clean matte samples cannot add a key-colored
				// or black transparent halo. Opaque internal linework bypasses this.
				if (minimum < 0.999 && maximum > 0.001)
					color = color * 0.5 + (right + left + down + up) * 0.125;
			}
			gl_FragColor = color;
		}
	')
	public function new() {super();}
}
