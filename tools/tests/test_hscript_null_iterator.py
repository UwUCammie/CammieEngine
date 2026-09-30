"""Pins for the vendored hscript null for-in / null-call guards and the
imported-substate host fixes behind the DDTO++ CatfightPopup SIGSEGV.

Crash chain (TAKEOVER-PLUS-PLUS-V10): the translated CatfightPopup substate
runs `for (touch in FlxG.touches.list)` every frame once its buttons unlock.
The desktop interpreter host (PluginManager.HscriptGlobals) carried no
`touches` member, so the chain evaluated to null, the null-access shim
returned null for `.list`, and hscript's makeIterator called `.iterator()` on
a null Dynamic - which on hxcpp dereferences the null object and SIGSEGVs
before any Haxe exception can surface.

The pins exercise the real vendored Interp source (`.haxelib/hscript/2,5,0`,
patched by the shared setup tool) under the portable interpreter, the same
extract-and-interpret style as the other engine suites. Migration coverage
uses the clean pinned-source fixture and invokes that tool through its CLI.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT_LIB = ROOT / ".haxelib/hscript/2,5,0"
INTERP_SOURCE = HSCRIPT_LIB / "hscript/Interp.hx"
RUN_SH = ROOT / "run.sh"
RUN_BAT = ROOT / "run.bat"
PATCHER = ROOT / "tools/patch_hscript_compat.py"
UPSTREAM_INTERP = ROOT / "tools/tests/fixtures/hscript-2.5.0-Interp.hx"
PLUGIN_MANAGER = ROOT / "source/PluginManager.hx"
IMPORTED_RUNTIME = ROOT / "source/HxcImportedRuntime.hx"
SMOKE_HARNESS = ROOT / "source/RuntimeSmokeHarness.hx"
STATE_FACTORY = ROOT / "source/HxcStateFactory.hx"
DONOR_POPUP = (ROOT / "export/release/linux/bin/assets/imported_mods"
               / "v-slice-ddto-v10-release-2dbdf01f44/scripts/states/CatfightPopup.hxc")

NULL_ITERATOR_DIAGNOSTIC = (
    '[hscript-null-iterator] for-in used a null value and was treated as an '
    'empty loop so the script can continue')


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HscriptNullIteratorTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [str(HAXE),
                       "-cp", str(ROOT / "source"),
                       "-cp", str(HSCRIPT_LIB),
                       "-cp", folder,
                       "-main", "Main", "--interp"]
            return subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=300)

    SCRIPT = (
        "var iterations = 0;\n"
        "function update() {\n"
        "  for (touch in FlxG.touches.list) iterations++;\n"
        "  for (x in null) iterations++;\n"
        "  return iterations;\n"
        "}\n"
        "function normalSum() {\n"
        "  var total = 0;\n"
        "  for (item in items) total = total + item;\n"
        "  return total;\n"
        "}\n"
        "function callOnNull() {\n"
        "  var missing = null;\n"
        "  return missing.doThing(1);\n"
        "}\n"
        "function callAbsentMethod() {\n"
        "  var present = {a: 1};\n"
        "  return present.notDefinedHere();\n"
        "}\n"
        "function nonIterableStillThrows() {\n"
        "  try {\n"
        "    for (x in {a: 1}) return 'iterated';\n"
        "  } catch (e:Dynamic) {\n"
        "    return 'caught';\n"
        "  }\n"
        "  return 'none';\n"
        "}\n"
        # Regression pins for the hscript-stop-catch patch: the rewritten loop
        # and try/catch handlers must keep real Stop semantics working.
        "function loopControl() {\n"
        "  var seen = '';\n"
        "  for (item in items) {\n"
        "    if (item == 1) continue;\n"
        "    if (item == 3) break;\n"
        "    seen = seen + item;\n"
        "  }\n"
        "  return seen;\n"
        "}\n"
        "function tryCatchInClosure() {\n"
        "  var handler = function() {\n"
        "    try {\n"
        "      ModStore.set('x', 1);\n"
        "      return 'no-throw';\n"
        "    } catch (e:Dynamic) {\n"
        "      return 'caught';\n"
        "    }\n"
        "  };\n"
        "  return handler();\n"
        "}\n"
        "function errorAfterTryStillPropagates() {\n"
        "  var handled = 'no';\n"
        "  try {\n"
        "    ModStore.set('x', 1);\n"
        "    handled = 'yes';\n"
        "  } catch (e:Dynamic) {\n"
        "    handled = 'caught';\n"
        "  }\n"
        "  missingVariableAfterTry;\n"
        "  return handled;\n"
        "}\n"
        # hxcpp cannot safely call Type.enumConstructor on arbitrary Dynamic
        # errors; the native target SIGSEGVs before an Haxe catch can run.
        "function throwPlainObject() {\n"
        "  throw {marker: 'plain-dynamic-error'};\n"
        "}\n")

    MAIN = '''import hscript.Interp;
import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var interp = new Interp();
    // Mirror HxcImportedRuntime's host: a FlxG surrogate without 'touches'.
    interp.variables.set("FlxG", {{}});
    interp.variables.set("items", [1, 2, 3]);
    interp.execute(new Parser().parseString({script}));
    interp.variables.set("__compatDiagnosticSource", "scripts/Soretro.hx");
    interp.variables.set("__compatDiagnosticCallback", "update");
    if (interp.variables.get("update")() != 0)
      fail("for-in over a null value must be an empty loop");
    if (interp.variables.get("update")() != 0)
      fail("repeated for-in over a null value must remain an empty loop");
    interp.variables.set("__compatDiagnosticCallback", "onCreate");
    if (interp.variables.get("update")() != 0)
      fail("for-in over a null value must remain an empty loop across callbacks");
    if (interp.variables.get("normalSum")() != 6)
      fail("normal array iteration regressed");
    if (interp.variables.get("callOnNull")() != null)
      fail("method call on a null object must degrade to null");
    if (interp.variables.get("callAbsentMethod")() != null)
      fail("call through a missing method must degrade to null");
    if (interp.variables.get("nonIterableStillThrows")() != 'caught')
      fail("for-in over a non-iterable value must still raise EInvalidIterator");
    // hscript-stop-catch regression pins: real break/continue semantics and
    // closure try/catch must survive the rewritten loop catch handlers.
    if (interp.variables.get("loopControl")() != '2')
      fail("loop break/continue semantics regressed: " + interp.variables.get("loopControl")());
    if (interp.variables.get("tryCatchInClosure")() != 'caught')
      fail("try/catch inside a closure must catch script errors");
    var propagated = false;
    try {{
      interp.variables.get("errorAfterTryStillPropagates")();
    }} catch (e:Dynamic) {{
      propagated = true;
    }}
    if (!propagated)
      fail("an error after a handled try must still surface");
    var thrownObject:Dynamic = null;
    try {{
      interp.variables.get("throwPlainObject")();
    }} catch (e:Dynamic) {{
      thrownObject = e;
    }}
    if (thrownObject == null || Reflect.field(thrownObject, "marker") != 'plain-dynamic-error')
      fail("a non-enum Dynamic error must propagate without being treated as a Stop signal");
  }}
}}'''

    def test_null_for_in_is_empty_loop_and_normal_iteration_survives(self):
        result = self.run_fixture(self.MAIN.format(script=hx_string(self.SCRIPT)))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # The null chain (FlxG.touches -> null, .list on null) produces the
        # null-access read diagnostic once and the empty-loop diagnostic once;
        # dedupe must keep each to a single line.
        self.assertIn(
            NULL_ITERATOR_DIAGNOSTIC + " (scripts/Soretro.hx#update)", result.stdout)
        self.assertIn(
            NULL_ITERATOR_DIAGNOSTIC + " (scripts/Soretro.hx#onCreate)", result.stdout)
        self.assertEqual(result.stdout.count('[hscript-null-iterator]'), 2,
                         "null-iterator diagnostics must dedupe per callback context:\n" + result.stdout)
        self.assertIn('[hscript-null-access] read to "list"', result.stdout)
        self.assertEqual(result.stdout.count('[hscript-null-iterator]'), 2)
        # Method call on a null object: one diagnosed null return (the ECall
        # handler degrades before any field read happens).
        self.assertIn('[hscript-null-access] call to "doThing"', result.stdout)
        self.assertNotIn('read to "doThing"', result.stdout)
        # Missing method on a real object: only the call degrades.
        self.assertIn('[hscript-null-access] call to "notDefinedHere"', result.stdout)

    def test_vendored_interp_carries_idempotent_patch_markers(self):
        source = INTERP_SOURCE.read_text()
        for marker in ("hscript-null-iterator", "hscript-null-fcall",
                       "hscript-null-ecall", "hscript-null-access",
                       "hscript-null-operand", "hscript-null-iterator-context",
                       "hscript-stop-catch",
                       "hscript-stop-safe-enum"):
            self.assertIn(marker, source, f"vendored Interp.hx lost the {marker} patch")
        self.assertIn("isHscriptStop", source)
        stop_matcher = source[source.index("function isHscriptStop"):source.index("private enum Stop")]
        self.assertIn("case TEnum(_)" , stop_matcher)
        self.assertLess(stop_matcher.index("case TEnum(_)"), stop_matcher.index("Type.enumConstructor(v)"))
        # The guard must run before the native .iterator() call on the value.
        make_iterator = source[source.index("function makeIterator"):]
        self.assertLess(make_iterator.index("if( v == null )"),
                        make_iterator.index("try v = v.iterator()"))
        # The Stop catches must match dynamically: hxcpp's typed enum catch
        # wrongly grabs hscript.Error values and corrupted control flow.
        self.assertNotIn("catch( err : Stop )", source)
        self.assertNotIn("catch( e : Stop )", source)

    def test_build_scripts_run_the_shared_guard_patcher(self):
        run_sh = RUN_SH.read_text()
        run_bat = RUN_BAT.read_text()
        patcher = PATCHER.read_text()
        self.assertIn("python3 tools/patch_hscript_compat.py", run_sh)
        self.assertIn("tools\\patch_hscript_compat.py", run_bat)
        for marker in ("hscript-null-iterator", "hscript-null-fcall",
                       "hscript-null-ecall", "hscript-null-iterator-context",
                       "hscript-stop-safe-enum"):
            self.assertIn(marker, patcher,
                          f"shared patcher lost the idempotent guard for {marker}")

    def test_shared_patcher_upgrades_existing_iterator_context_idempotently(self):
        with tempfile.TemporaryDirectory(prefix="hscript-iterator-context-") as folder:
            target = Path(folder) / "Interp.hx"
            shutil.copyfile(UPSTREAM_INTERP, target)
            command = [sys.executable, str(PATCHER), "--path", str(target)]
            initial = subprocess.run(command, cwd=ROOT, capture_output=True,
                                     text=True, timeout=30)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)

            source = target.read_text(encoding="utf-8")
            current_start = source.index("\tfunction nullIteratorDiagnose() : Void {")
            current_end = source.index("\n\t}", current_start) + len("\n\t}")
            legacy = '''\tfunction nullIteratorDiagnose() : Void {
\t\t#if sys
\t\tvar key = "iterator:null";
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-iterator] for-in used a null value and was treated as an empty loop so the script can continue');
\t\t}
\t\t#end
\t}'''
            target.write_text(source[:current_start] + legacy + source[current_end:],
                              encoding="utf-8")

            first = subprocess.run(command, cwd=ROOT, capture_output=True,
                                   text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            upgraded = target.read_text(encoding="utf-8")
            self.assertIn("hscript-null-iterator-context", upgraded)
            self.assertIn('var key = "iterator:null:" + context;', upgraded)
            self.assertIn('variables.get("__compatDiagnosticSource")', upgraded)
            self.assertIn('variables.get("__compatDiagnosticCallback")', upgraded)
            self.assertIn("if( v == null ) {\n\t\t\tnullIteratorDiagnose();", upgraded)
            self.assertIn("return emptyIterator;", upgraded)

            second = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), upgraded,
                             "reapplying the shared iterator-context upgrade must be stable")

    def test_imported_host_materializes_touch_frontend_and_close(self):
        plugin_manager = PLUGIN_MANAGER.read_text()
        self.assertIn("public static var touches(get, never):HscriptTouchFrontEnd;",
                      plugin_manager)
        self.assertIn("class HscriptTouchFrontEnd", plugin_manager)
        # The surrogate mirrors the two members donor menus touch: the desktop
        # touch list is empty and getFirst() has nothing to return.
        self.assertIn("public var list:Array<Dynamic> = [];", plugin_manager)
        self.assertIn("public function getFirst():Dynamic", plugin_manager)
        imported_runtime = IMPORTED_RUNTIME.read_text()
        # Donor substates call their own close(); without this seed the popup
        # can never dismiss itself (EUnknownVariable(close)).
        self.assertIn("interp.variables.set('close'", imported_runtime)
        # Failing callbacks are poisoned after one diagnosed failure instead of
        # re-running broken state every frame.
        self.assertIn("poisonedCallbacks", imported_runtime)
        self.assertIn("poisonedCallbacks.exists(name)", imported_runtime)
        self.assertIn("skipped until the state reloads", imported_runtime)

    def test_smoke_harness_and_factory_audit_hooks_exist(self):
        harness = SMOKE_HARNESS.read_text()
        self.assertIn("--smoke-freeplay-accept-ms", harness)
        self.assertIn("freeplay_accept_begin", harness)
        self.assertIn("freeplay_popup_open", harness)
        self.assertIn("freeplay_popup_confirm_begin", harness)
        self.assertIn("freeplay_popup_close", harness)
        self.assertIn("simulateAccept", harness)
        # Scrolling must not drive a state frozen under an open popup.
        self.assertIn("popup == null && cfg.freeplayScrollMs > 0", harness)
        factory = STATE_FACTORY.read_text()
        self.assertIn("DUMP_GENERATED_HXC", factory)

    def test_donor_catfight_popup_crash_site_is_pinned(self):
        if not DONOR_POPUP.exists():
            self.skipTest("DDTO++ donor fixture is not mounted")
        donor_source = DONOR_POPUP.read_text(errors="ignore")
        self.assertIn("for (touch in FlxG.touches.list)", donor_source)
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(DONOR_POPUP))}), {hx_string(str(DONOR_POPUP))});
    var generated = result.generatedHscript;
    if (result.kind != "substate")
      fail("CatfightPopup classified as " + result.kind);
    if (generated.indexOf("for (touch in FlxG.touches.list)") < 0)
      fail("generated popup lost the donor touch loop: " + generated);
    if (generated.indexOf("close()") < 0)
      fail("generated popup quit() lost the donor close call: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
