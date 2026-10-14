"""Named script shaders: one registry for sources, the shader option and typed uniforms."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import copy_sources, play_state_method
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
class StubShader {
 public var fragment:String; public var vertex:String; public var name:String;
 public var values:Map<String, Dynamic> = [];
 public function new(fragment:String, vertex:String, name:String) { this.fragment = fragment; this.vertex = vertex; this.name = name; }
 public function setFloat(key:String, value:Float):Void values.set('float:' + key, value);
 public function getFloat(key:String):Null<Float> return values.get('float:' + key);
 public function setBool(key:String, value:Bool):Void values.set('bool:' + key, value);
 public function getBool(key:String):Null<Bool> return values.get('bool:' + key);
 public function setIntArray(key:String, value:Array<Int>):Void values.set('ints:' + key, value);
 public function getIntArray(key:String):Array<Int> return values.get('ints:' + key);
 public function setSampler2D(key:String, value:Dynamic):Void values.set('sampler:' + key, value);
 public function setInt(key:String, value:Int):Void throw 'driver said no';
}
class Sprite { public var shader:Dynamic = null; public function new() {} }
class RegistryProbe {
 static function check(value:Bool, label:String):Void if (!value) throw label;
 static function main() {
  var on = true;
  var lookups:Array<String> = [];
  var built = 0;
  var files:Map<String, Array<String>> = ['glow' => ['GLOW_FRAG', 'GLOW_VERT'], 'wave' => ['WAVE_FRAG', null],
   'bend' => [null, 'BEND_VERT'], 'empty' => [null, null]];
  var resolve = function(name:String):Array<String> { lookups.push(name); return files.get(name); };
  var registry = new RuntimeShaderRegistry(function() return on,
   function(fragment:String, vertex:String, name:String):Dynamic { built++; return new StubShader(fragment, vertex, name); });

  // Sources are read once per name, as a pair.
  check(registry.init('glow', resolve) && registry.init('glow', resolve) && lookups.join(',') == 'glow', 'sources must be read once');
  check(registry.sources.get('glow').join('|') == 'GLOW_FRAG|GLOW_VERT', 'fragment and vertex are kept together');
  check(registry.init('wave', resolve) && registry.sources.get('wave')[1] == null, 'fragment-only shader');
  check(registry.init('bend', resolve) && registry.sources.get('bend')[0] == null, 'vertex-only shader');
  check(!registry.init('empty', resolve) && !registry.init('nowhere', resolve) && !registry.sources.exists('nowhere'),
   'a name with no files is not registered');
  check(!registry.init(null, resolve) && !registry.init('  ', resolve) && !registry.init('later', null), 'bad arguments');
  var throwing = function(name:String):Array<String> throw 'disk error';
  check(!registry.init('boom', throwing), 'a failing lookup is a missing shader, not a crash');

  // Creating builds from the cached pair and loads on first use.
  lookups = [];
  var glow:StubShader = registry.create('glow');
  check(glow != null && glow.fragment == 'GLOW_FRAG' && glow.vertex == 'GLOW_VERT' && glow.name == 'glow' && lookups.length == 0,
   'create must use the cached sources');
  files.set('late', ['LATE_FRAG', null]);
  var late:StubShader = registry.create('late', resolve);
  check(late != null && late.fragment == 'LATE_FRAG' && lookups.join(',') == 'late', 'create loads an unseen name');
  check(registry.create('nowhere', resolve) == null && registry.create('unseen') == null, 'unknown name creates nothing');
  check(registry.create('glow') != glow, 'every create is a new shader object');

  // Per-owner scope is just a different resolver and a different registry.
  var other = new RuntimeShaderRegistry(function() return true, function(f, v, n):Dynamic return new StubShader(f, v, n));
  check(!other.sources.exists('glow') && other.create('glow', function(name) return null) == null,
   'one registry must not see names loaded through another');

  // Putting a shader on an object and taking it off.
  var sprite = new Sprite();
  check(registry.setOn(sprite, 'wave') && (cast sprite.shader:StubShader).fragment == 'WAVE_FRAG', 'setOn');
  check(!registry.setOn(sprite, 'nowhere', resolve) && (cast sprite.shader:StubShader).fragment == 'WAVE_FRAG',
   'a missing shader leaves the old one in place');
  check(!registry.setOn(null, 'wave'), 'no object');
  check(RuntimeShaderRegistry.remove(sprite) && sprite.shader == null && !RuntimeShaderRegistry.remove(null), 'remove');

  // The player's shader option stops loading and building, and nothing else.
  on = false;
  var before = built;
  check(!registry.isEnabled() && !registry.init('glow', resolve) && registry.create('glow') == null
   && !registry.setOn(sprite, 'glow') && sprite.shader == null && built == before, 'option off must build nothing');
  on = true;
  check(registry.create('glow') != null, 'option back on');

  // Typed uniform access goes to the matching setter or getter.
  var shader = new StubShader('F', 'V', 'typed');
  check(RuntimeShaderRegistry.setValue(shader, 'amount', 0.5, 'Float') && RuntimeShaderRegistry.getValue(shader, 'amount', 'Float') == 0.5, 'float');
  check(RuntimeShaderRegistry.setValue(shader, 'enabled', true, 'Bool') && RuntimeShaderRegistry.getValue(shader, 'enabled', 'Bool') == true, 'bool');
  check(RuntimeShaderRegistry.setValue(shader, 'steps', [1, 2, 3], 'IntArray')
   && RuntimeShaderRegistry.getValue(shader, 'steps', 'IntArray').join(',') == '1,2,3', 'int array');
  check(shader.values.exists('float:amount') && !shader.values.exists('bool:amount'), 'kind picks the setter');
  check(!RuntimeShaderRegistry.setValue(null, 'amount', 1, 'Float') && RuntimeShaderRegistry.getValue(null, 'amount', 'Float') == null, 'no shader');
  check(!RuntimeShaderRegistry.setValue(shader, null, 1, 'Float') && RuntimeShaderRegistry.getValue(shader, null, 'Float') == null, 'no uniform name');
  check(!RuntimeShaderRegistry.setValue(shader, 'x', 1, 'Matrix') && RuntimeShaderRegistry.getValue(shader, 'x', 'Matrix') == null, 'unknown kind');
  check(!RuntimeShaderRegistry.setValue(shader, 'count', 3, 'Int'), 'a setter that throws reports failure');
  check(RuntimeShaderRegistry.getValue(shader, 'never', 'Float') == null, 'unset uniform');
  check(RuntimeShaderRegistry.setSampler(shader, 'mask', 'BITMAP') && shader.values.get('sampler:mask') == 'BITMAP'
   && !RuntimeShaderRegistry.setSampler(shader, 'mask', null) && !RuntimeShaderRegistry.setSampler(null, 'mask', 'BITMAP'), 'sampler');
  Sys.println('REGISTRY_OK');
 }
}
'''


class RuntimeShaderRegistryTest(unittest.TestCase):
    def test_sources_option_scope_and_typed_values(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "RegistryProbe.hx").write_text(FIXTURE, newline="\n")
            copy_sources(folder, "RuntimeShaderRegistry.hx")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "RegistryProbe", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("REGISTRY_OK", result.stdout)

    def test_lua_and_state_shader_calls_go_through_the_registry(self):
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        self.assertNotIn("new ShaderHandler.CoolRuntimeShader", bindings)
        self.assertNotIn("psychEaseName", bindings)
        self.assertIn("return shaders.init(name, ownerShaderSources);", bindings)
        self.assertIn("return shaders.setOn(sprite, shaderName);", bindings)
        self.assertIn("RuntimeShaderRegistry.getValue(shaderFor(tag), property, kind)", bindings)
        self.assertIn("RuntimeShaderRegistry.setValue(shaderFor(tag), property, value, kind)", bindings)
        self.assertIn("RuntimeShaderRegistry.setSampler(shader, property, bitmap)", bindings)
        # Owner scoping stays in the resolver the binding passes in.
        owner = bindings[bindings.index("function ownerShaderSources("):]
        owner = owner[:owner.index("\n\t}") + 3]
        self.assertIn("PsychOwnerAssetPath.ownerReferenceAllowed(ownerRoot, name)", owner)
        self.assertIn("'shaderFragment'", owner)
        self.assertIn("'shaderVertex'", owner)

        self.assertIn("scriptShaderRegistry().init(name, compatShaderSources)", play_state_method("public function initLuaShader("))
        create = play_state_method("public function createRuntimeShader(")
        self.assertIn("scriptShaderRegistry().create(name, compatShaderSources)", create)
        self.assertNotIn("$frag", create)
        self.assertIn("scriptShaderRegistry().setOn(object, shaderName, compatShaderSources)",
                      play_state_method("function compatSetSpriteShader("))
        self.assertIn("RuntimeShaderRegistry.setValue(shader, variable, value, 'Float')",
                      play_state_method("function compatSetShaderFloat("))
        sources = play_state_method("function compatShaderSources(")
        self.assertIn("Path.withExtension(fragPath, 'vert')", sources)
        registry = play_state_method("function scriptShaderRegistry(")
        self.assertIn("OptionsHandler.options.gameplayShaders", registry)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("public var runtimeShaders(get, never):Map<String, Array<String>>;", play)


if __name__ == "__main__":
    unittest.main()
