"""Script translators compile each fixed rewrite pattern once per thread."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RegexCacheTest(unittest.TestCase):
    def run_fixture(self, name, body):
        fixture = 'class ' + name + ' {\n static function fail(message:String):Void throw message;\n static function main() {\n' + body + '\n  Sys.println("OK");\n }\n}'
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / (name + ".hx")).write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "--run", name],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_patterns_are_shared_per_key_and_bounded(self):
        self.run_fixture("RegexCacheFixture", r'''
  var a = RegexCache.get('\\bfoo\\s*\\(', 'g');
  var b = RegexCache.get('\\bfoo\\s*\\(', 'g');
  if (a != b) fail('the same pattern was compiled twice');
  if (RegexCache.get('\\bfoo\\s*\\(', 'gm') == a) fail('flags were not part of the key');
  // A cached pattern behaves exactly like a fresh one.
  var text = 'foo (1); xfoo(2); bar.foo(3)';
  if (a.replace(text, 'call(') != new EReg('\\bfoo\\s*\\(', 'g').replace(text, 'call('))
   fail('cached replace differs from a fresh pattern');
  if (a.replace(text, 'call(') != a.replace(text, 'call(')) fail('a second replace saw leftover state');
  // Names from scripts make the key space open ended; the table starts over instead of growing.
  var before = RegexCache.compiledOnThisThread();
  for (i in 0...(RegexCache.MAX_PATTERNS + 10)) RegexCache.get('name' + i, 'g');
  if (RegexCache.compiledOnThisThread() - before != RegexCache.MAX_PATTERNS + 10) fail('distinct patterns were not compiled');
  var again = RegexCache.compiledOnThisThread();
  RegexCache.get('name' + (RegexCache.MAX_PATTERNS + 9), 'g');
  if (RegexCache.compiledOnThisThread() != again) fail('a recent pattern was dropped');
  // Another thread gets its own table, so two translators never share match state.
  var lock = new sys.thread.Lock();
  var other:EReg = null;
  sys.thread.Thread.create(function() {
   other = RegexCache.get('\\bfoo\\s*\\(', 'g');
   lock.release();
  });
  if (!lock.wait(10)) fail('worker thread did not finish');
  if (other == null || other == RegexCache.get('\\bfoo\\s*\\(', 'g')) fail('threads shared one compiled pattern');
''')

    def test_hxc_rewrite_passes_reuse_compiled_patterns(self):
        # Before the cache a 280 KB pack compiled about 347000 patterns, only
        # about 1100 of them distinct. A second translation of the same source
        # must not compile any of the cached passes' patterns again.
        self.run_fixture("HxcRegexCacheFixture", r'''
  var source = "class Owner extends Module { function new() { super('owner'); }"
   + " override function onUpdate(event) { PlayState.instance.vocals.playerVolume = 1; ModStore.get('a'); var s = new FunkinSprite(1, 2); s.loadTexture('x'); onBeatHit(null); }"
   + " override function onBeatHit(event) { if (event.beat > 2) { FlxTween.tween(PlayState.instance.camHUD, {alpha: 0}, 1); } } }";
  var first = HxcCompat.analyze(source, 'scripts/modules/Owner.hxc');
  var compiled = RegexCache.compiledOnThisThread();
  if (compiled == 0) fail('the rewrite passes do not use the shared patterns');
  // Forget the remembered analysis so the repeat really runs the passes again.
  TranslationMemo.clear();
  var second = HxcCompat.analyze(source, 'scripts/modules/Owner.hxc');
  if (RegexCache.compiledOnThisThread() != compiled)
   fail('a repeat translation compiled ' + (RegexCache.compiledOnThisThread() - compiled) + ' cached patterns again');
  if (first.generatedHscript != second.generatedHscript) fail('repeat translation changed its output');
  if (first.generatedHscript.indexOf('HxcCompatRuntime.safeTween(') < 0) fail('a cached rewrite did not run');
  // Passes that read match positions in a loop (video cutscenes, camera
  // tweens) also reuse their patterns and still rewrite every call.
  var looped = "class Clip extends Module { function new() { super('clip'); }"
   + " override function onSongStart(event) { VideoCutscene.play(Paths.videos('a')); VideoCutscene.play(Paths.videos('b'), CutsceneType.ENDING);"
   + " PlayState.instance.tweenCameraToPosition(1, 2, 0, FlxEase.instant); PlayState.instance.tweenCameraToPosition(3, 4, 0, FlxEase.instant); } }";
  var loopedFirst = HxcCompat.analyze(looped, 'scripts/modules/Clip.hxc');
  var loopedCompiled = RegexCache.compiledOnThisThread();
  TranslationMemo.clear();
  var loopedSecond = HxcCompat.analyze(looped, 'scripts/modules/Clip.hxc');
  if (RegexCache.compiledOnThisThread() != loopedCompiled)
   fail('looped passes compiled ' + (RegexCache.compiledOnThisThread() - loopedCompiled) + ' patterns again');
  if (loopedFirst.generatedHscript != loopedSecond.generatedHscript) fail('looped repeat changed its output');
  var plays = loopedSecond.generatedHscript.split('HxcCompatRuntime.playVideoCutscene(').length - 1;
  if (plays != 2) fail('expected both cutscene calls rewritten, got ' + plays);
''')

    def test_lua_line_patterns_reuse_compiled_patterns(self):
        # Boolean checks run once per Lua line; they compile once per thread now.
        lua = r'''
local count = 0
function onUpdate(elapsed)
  if count > 2 then
    for i = 1, 3 do setProperty('boyfriend.alpha', i / 3) end
  elseif count == 0x1F then
    count = count + 1
  end
  local a, b = 1, 2
end
'''
        body = '  var source = ' + json.dumps(lua) + r''';
  var first = LuaCompat.translate(source, 'probe.lua');
  var compiled = RegexCache.compiledOnThisThread();
  if (compiled == 0) fail('the Lua line checks do not use the shared patterns');
  // Forget the remembered translation so the repeat really runs the line checks again.
  TranslationMemo.clear();
  var second = LuaCompat.translate(source, 'probe.lua');
  if (RegexCache.compiledOnThisThread() != compiled) fail('a repeat Lua translation compiled cached patterns again');
  if (first.hscript != second.hscript) fail('repeat translation changed its output');
  if (first.hscript.indexOf('else if (') < 0 || first.hscript.indexOf('makeRangeArray') < 0)
   fail('keyword-gated patterns stopped matching: ' + first.hscript);
'''
        self.run_fixture("LuaRegexCacheFixture", body)

    def test_keyword_gated_lua_patterns_still_match_every_form(self):
        # translateLine only builds its anchored statement patterns when the line
        # starts with their keyword. Every statement form must still be found,
        # and names that merely start with a keyword must stay plain names.
        lua = r'''local iffy = 1
local format = 2
whilst = 3
functional = 4
local t = {1, 2}
function onCreate()
  while iffy < 3 do iffy = iffy + 1 end
  for k, v in ipairs(t) do format = v end
  for w in string.gmatch('a,b', '([^,]+)') do whilst = w end
  for a, b in next, t do functional = a end
  for i = 1.5, 3 do whilst = i end
  local function helper(x) return x end
  local function inl(y)return y end
  if iffy == 3 then
    whilst = 1
  elseif format == 2 then
    whilst = 2
  end
end
'''
        body = '  var out = LuaCompat.translate(' + json.dumps(lua) + r''', 'gate.lua').hscript;
  for (expected in ['var iffy = 1;', 'var format = 2;', '\nwhilst = 3;', '\nfunctional = 4;', 'while (iffy < 3) {',
   'luaIpairsLength(', 'for (w in luaStringGmatch(', 'luaIterator(next, t)', '__luaForStart', 'var helper; helper = function(?x)',
   'var inl; inl = function(?y)', 'if (iffy == 3 ) {', '} else if (format == 2 ) {'])
   if (out.indexOf(expected) < 0) fail('missing ' + expected + ' in:\n' + out);
'''
        self.run_fixture("LuaKeywordGateFixture", body)


if __name__ == "__main__":
    unittest.main()
