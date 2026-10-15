"""Script translation is remembered per source and path, and every caller gets its own copy."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TranslationMemoTest(unittest.TestCase):
    def run_fixture(self, name, body, extra=''):
        fixture = ('class ' + name + ' {\n static function fail(message:String):Void throw message;\n'
                   ' static function ser(v:Dynamic):String { var s = new haxe.Serializer(); s.useCache = false; s.serialize(v); return s.toString(); }\n'
                   ' static function main() {\n' + body + '\n  Sys.println("OK");\n }\n}\n' + extra)
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / (name + ".hx")).write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", name],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_repeat_analysis_is_a_fresh_identical_copy(self):
        self.run_fixture("HxcMemoRepeatFixture", r'''
  var source = "class Owner extends Module { function new() { super('owner'); }"
   + " override function onUpdate(event) { PlayState.instance.camHUD.alpha = 0.5; }"
   + " override function onBeatHit(event) { if (event.beat > 2) { FlxTween.tween(PlayState.instance.camHUD, {alpha: 0}, 1); } } }";
  TranslationMemo.clear();
  var first = HxcCompat.analyze(source, 'scripts/modules/Owner.hxc');
  var expected = ser(first);
  var compiled = RegexCache.compiledOnThisThread();
  var second = HxcCompat.analyze(source, 'scripts/modules/Owner.hxc');
  if (TranslationMemo.hits != 1) fail('the repeat was translated again');
  if (ser(second) != expected) fail('the remembered result differs from the first analysis');
  if (second == first || second.callbackAdapters == first.callbackAdapters) fail('callers share one mutable result');
  if (RegexCache.compiledOnThisThread() != compiled) fail('the repeat ran the rewrite passes');
  // A caller changing its copy must not change what the next caller gets.
  second.callbackAdapters[0].safe = false;
  second.diagnostics.push(null);
  second.generatedHscript = '';
  var third = HxcCompat.analyze(source, 'scripts/modules/Owner.hxc');
  if (ser(third) != expected) fail('a caller edit leaked into the memo');
  first.callbackAdapters.splice(0, 1);
  if (ser(HxcCompat.analyze(source, 'scripts/modules/Owner.hxc')) != expected) fail('editing the first result leaked into the memo');
''')

    def test_key_needs_the_same_text_and_path(self):
        self.run_fixture("HxcMemoKeyFixture", r'''
  // Same length, different text: the length in the key must not make them collide.
  var a = "class Owner extends Module { function new() { super('aaaaa'); } }";
  var b = "class Owner extends Module { function new() { super('bbbbb'); } }";
  if (a.length != b.length) fail('fixture texts must be the same length');
  TranslationMemo.clear();
  if (HxcCompat.analyze(a, 'scripts/modules/Owner.hxc').identifier != 'aaaaa') fail('first identifier');
  if (HxcCompat.analyze(b, 'scripts/modules/Owner.hxc').identifier != 'bbbbb') fail('a different text got the remembered result');
  if (TranslationMemo.hits != 0) fail('different text counted as a repeat');
  // The path takes part in the analysis (class selection, classification), so it is part of the key.
  var stagePath = HxcCompat.analyze(a, 'scripts/stages/Owner.hxc');
  if (TranslationMemo.hits != 0) fail('a different path counted as a repeat');
  if (stagePath.path != 'scripts/stages/Owner.hxc') fail('result carries another path');
  // One entry per path and length: the newer text replaced the older one.
  if (HxcCompat.analyze(b, 'scripts/modules/Owner.hxc').identifier != 'bbbbb') fail('repeat identifier');
  if (TranslationMemo.hits != 1) fail('same text and path was not remembered');
''')

    def test_character_wrappers_are_always_analyzed_again(self):
        # They read base classes from other files, which can change on their own.
        self.run_fixture("HxcMemoCharacterFixture", r'''
  var source = "class Wrapper extends MultiSparrowCharacter { function new() { super('actor'); } }";
  TranslationMemo.clear();
  var first = HxcCompat.analyze(source, 'data/characters/Wrapper.hxc');
  if (first.kind != 'character') fail('fixture must be a character, got ' + first.kind);
  HxcCompat.analyze(source, 'data/characters/Wrapper.hxc');
  if (TranslationMemo.stores != 0 || TranslationMemo.hits != 0) fail('a character result was remembered');
''')

    def test_a_remembered_translation_does_not_count_toward_the_collect_budget(self):
        # Only a real translation leaves dead patterns behind for the collector.
        self.run_fixture("MemoBudgetFixture", r'''
  var collects = 0;
  EngineMemory.collector = function(major:Bool) collects++;
  EngineMemory.reset();
  TranslationMemo.clear();
  var line = 'function onUpdate(elapsed) setProperty("boyfriend.alpha", 1) end\n';
  var lua = '';
  while (lua.length < EngineMemory.TRANSLATION_COLLECT_CHARS) lua += line;
  LuaCompat.translate(lua, 'big.lua');
  if (collects != 1) fail('a Lua file over the budget should collect once, got ' + collects);
  LuaCompat.translate(lua, 'big.lua');
  if (TranslationMemo.hits != 1) fail('the Lua repeat was translated again');
  if (collects != 1) fail('a remembered Lua translation counted toward the budget');
  var hxc = "class Owner extends Module { function new() { super('owner'); } }";
  while (hxc.length < EngineMemory.TRANSLATION_COLLECT_CHARS) hxc += '\n// padding line for size';
  HxcCompat.analyze(hxc, 'scripts/modules/Owner.hxc');
  if (collects != 2) fail('an HXC file over the budget should collect once, got ' + (collects - 1));
  HxcCompat.analyze(hxc, 'scripts/modules/Owner.hxc');
  if (TranslationMemo.hits != 2) fail('the HXC repeat was analyzed again');
  if (collects != 2) fail('a remembered HXC analysis counted toward the budget');
''')

    def test_memo_is_bounded(self):
        self.run_fixture("HxcMemoBoundFixture", r'''
  TranslationMemo.clear();
  var big = new StringBuf();
  for (i in 0...(TranslationMemo.MAX_SOURCE_CHARS >> 1) + 1) big.add('x');
  var half = big.toString();
  if (!TranslationMemo.store(half, 'one', {kind: 'module'})) fail('store refused');
  if (!TranslationMemo.store(half, 'two', {kind: 'module'})) fail('store refused');
  // The second store crossed the limit, so only it is left.
  if (TranslationMemo.lookup(half, 'one') != null) fail('the memo grew past its limit');
  var kept:Dynamic = TranslationMemo.lookup(half, 'two');
  if (kept == null || kept.kind != 'module') fail('the newest entry was dropped');
''')

    def test_lua_translation_is_remembered_per_origin_and_option(self):
        self.run_fixture("LuaMemoFixture", r'''
  var lua = 'local count = 0\nfunction onUpdate(elapsed)\n  count = count + 1\n  setProperty("boyfriend.alpha", 0.5)\nend\n';
  TranslationMemo.clear();
  var first = LuaCompat.translate(lua, 'mods/a/script.lua');
  var second = LuaCompat.translate(lua, 'mods/a/script.lua');
  if (TranslationMemo.hits != 1) fail('the repeat was translated again');
  if (ser(second) != ser(first) || second == first || second.diagnostics == first.diagnostics)
   fail('the repeat is not an identical, separate copy');
  var noted = second.diagnostics.length + 1;
  second.diagnostics.push('caller note');
  // The copy's diagnostics are a real string array the caller can add to.
  if (second.diagnostics.length != noted || second.diagnostics[noted - 1] != 'caller note') fail('a caller edit to its copy was lost');
  if (ser(LuaCompat.translate(lua, 'mods/a/script.lua')) != ser(first)) fail('a caller edit leaked into the memo');
  // Diagnostics name the origin and the option changes the output, so both are part of the key.
  var other = LuaCompat.translate(lua, 'mods/b/script.lua');
  var embedded = LuaCompat.translate(lua, 'mods/a/script.lua', true);
  if (TranslationMemo.hits != 2) fail('another origin or option counted as a repeat');
  if (ser(other) != ser(new LuaMemoFresh().run(lua, 'mods/b/script.lua', false))) fail('other origin result differs from a fresh translation');
  if (ser(embedded) != ser(new LuaMemoFresh().run(lua, 'mods/a/script.lua', true))) fail('embedded result differs from a fresh translation');
  // An HXC script with the same path and text is a different translation.
  if (TranslationMemo.lookup(lua, 'hxc:mods/a/script.lua') != null) fail('Lua and HXC share a key');
''', extra='''
class LuaMemoFresh {
 public function new() {}
 public function run(source:String, origin:String, embedded:Bool):Dynamic {
  TranslationMemo.clear();
  var result = LuaCompat.translate(source, origin, embedded);
  TranslationMemo.clear();
  return result;
 }
}
''')


if __name__ == "__main__":
    unittest.main()
