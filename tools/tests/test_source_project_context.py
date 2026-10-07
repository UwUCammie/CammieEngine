"""Bounded, project-local Lime define/value semantics."""

from haxe_test_support import HAXE_COMMAND, TEST_TMP

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
LIME_TOOLS = ROOT / ".haxelib" / "lime" / "8,3,2" / "src" / "lime" / "tools"


def extract_haxe_function(source: str, signature: str) -> str:
    """Extract one pinned Lime method with a small comment/string-aware brace scan."""
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    i = opening
    while i < len(source):
        char = source[i]
        following = source[i + 1] if i + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                i += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            i += 1
        elif char == "/" and following == "*":
            block_comment = True
            i += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f"Could not find the end of pinned method {signature}")

MAIN = r'''import sys.io.File;
import SourceProjectContext.SourceProjectContextResolution;
import SourceProjectContext.SourceProjectContextValue;
class Main {
 static function require(ok:Bool, message:String):Void {
  if (!ok) throw "SourceProjectContext: " + message;
 }

 static function pack(value:SourceProjectContextResolution):Dynamic {
  return {state:value.state, value:value.value, boolValue:value.boolValue,
   diagnosticCodes:[for (item in value.diagnostics) item.code]};
 }

 static function limeDifferential(input:String, values:Array<SourceProjectContextValue>):Dynamic {
  var parser = new lime.tools.ProjectXMLParserReference();
  for (item in values) parser.defines.set(item.name, item.value);
  var expected = parser.substitute(input);
  var context = SourceProjectContext.seed([], values, true);
  var actual = context.interpolate(input);
  return {input:input, expected:expected, actual:actual.value, state:actual.state};
 }

 static function limeCommandCondition(condition:String, command:String):Bool {
  var parser = new lime.tools.ProjectXMLParserReference();
  parser.command = command;
  var element = new haxe.xml.Access(Xml.parse('<asset if="' + condition + '"/>').firstElement());
  return parser.isValidElement(element, "");
 }

 static function main():Void {
  var result:Dynamic = {};

  var partial = SourceProjectContext.seed([
   {name:"FLAG_ONLY", state:"enabled", provenance:"build:flag"}
  ], [], false);
  result.partialMissing = partial.lookup("NOT_CAPTURED");
  result.partialBare = pack(partial.condition("NOT_CAPTURED", null));
  result.flagOnlyBare = pack(partial.condition("FLAG_ONLY", null));
  result.flagOnlyLookup = partial.lookup("FLAG_ONLY");
  result.flagOnlyValue = pack(partial.interpolate("${FLAG_ONLY}"));

  var complete = SourceProjectContext.seed([
   {name:"FLAG_ONLY", state:"enabled", provenance:"build:flag"},
   {name:"FALSE_TEXT", state:"enabled", provenance:"build:flag"}
  ], [
   {name:"FALSE_TEXT", value:"false", provenance:"build:value"}
  ], true, "");
  result.completeMissing = complete.lookup("NOT_CAPTURED");
  result.completeBareMissing = pack(complete.condition("NOT_CAPTURED", null));
  result.completeMissingValue = pack(complete.interpolate("${NOT_CAPTURED}"));
  result.completeMissingCompare = pack(complete.interpolate("${NOT_CAPTURED==NOT_CAPTURED}"));
  result.partialMissingCompare = pack(partial.interpolate("${NOT_CAPTURED==NOT_CAPTURED}"));
  result.unlessAbsent = pack(complete.condition(null, "NOT_CAPTURED"));
  result.falseTextBare = pack(complete.condition("FALSE_TEXT", null));
  result.falseTextExpanded = pack(complete.condition("${FALSE_TEXT}", null));
  var commandContext = SourceProjectContext.seed([
   {name:"LIME_COMMAND", state:"disabled", provenance:"project:unset"}
  ], [], true, "native");
  result.commandMatchesUnset = pack(commandContext.condition("native", null));
  result.commandDoesNotMatch = pack(commandContext.condition("other", null));
  var unknownCommand = SourceProjectContext.seed([], [], true);
  result.unknownCommand = pack(unknownCommand.condition("native", null));
  result.commandMatchesPinnedParser = limeCommandCondition("native", "native");

  var uncertain = new SourceProjectContext();
  uncertain.apply("define", "KEPT", "before", "root:1");
  uncertain.markValueUnresolved("KEPT", "include:conditional-value");
  result.valueUncertainty = uncertain.lookup("KEPT");
  result.valueUncertaintyBare = pack(uncertain.condition("KEPT", null));
  result.valueUncertaintyExpanded = pack(uncertain.interpolate("${KEPT}"));
  uncertain.apply("define", "STALE", "old", "root:2");
  uncertain.markUnresolved("STALE", "include:conditional-remove");
  result.presenceUncertainty = uncertain.lookup("STALE");
  result.presenceUncertaintyExpanded = pack(uncertain.interpolate("${STALE}"));
  uncertain.markAllUnresolved("include:dynamic-name");
  result.taintedMissing = uncertain.lookup("NEVER_SEEN");

  var unknownInclude = SourceProjectContext.seed([
   {name:"PRESERVED", state:"enabled", provenance:"build"},
   {name:"MAYBE_ADDED", state:"disabled", provenance:"build"}
  ], [{name:"PRESERVED", value:"known", provenance:"build"}], true);
  unknownInclude.markMissingUnresolved("root:include-unavailable");
  result.unknownIncludeComplete = unknownInclude.flagsComplete;
  result.unknownIncludeEnabled = unknownInclude.lookup("PRESERVED");
  result.unknownIncludeAbsent = unknownInclude.lookup("MAYBE_ADDED");
  result.unknownIncludeMissing = unknownInclude.lookup("NOT_LISTED");

  var unresolvedParent = SourceProjectContext.seed([
   {name:"ROOT_TARGET", state:"enabled", provenance:"parent"},
   {name:"MAY_ADD", state:"disabled", provenance:"parent:unset"}
  ], [{name:"ROOT_TARGET", value:"parent-value", provenance:"parent"}], true);
  var unresolvedChild = unresolvedParent.clone();
  unresolvedChild.markUnresolved("MAY_ADD", "child:unresolved-gate");
  unresolvedChild.markUnresolved("NEW_FROM_CHILD", "child:unresolved-gate");
  unresolvedParent.mergeUnresolved(unresolvedChild, "include:unresolved-gate");
  result.unresolvedMergeParent = unresolvedParent.lookup("ROOT_TARGET");
  result.unresolvedMergeOldAbsent = unresolvedParent.lookup("MAY_ADD");
  result.unresolvedMergeNew = unresolvedParent.lookup("NEW_FROM_CHILD");

  var dynamicParent = SourceProjectContext.seed([
   {name:"ROOT_TARGET", state:"enabled", provenance:"parent"},
   {name:"MAY_ADD", state:"disabled", provenance:"parent:unset"}
  ], [{name:"ROOT_TARGET", value:"parent-value", provenance:"parent"}], true);
  var dynamicChild = dynamicParent.clone();
  dynamicChild.markAllUnresolved("child:dynamic-name");
  dynamicParent.mergeUnresolved(dynamicChild, "include:dynamic-name");
  result.dynamicMergeComplete = dynamicParent.flagsComplete;
  result.dynamicMergeParent = dynamicParent.lookup("ROOT_TARGET");
  result.dynamicMergeOldAbsent = dynamicParent.lookup("MAY_ADD");
  result.dynamicMergeMissing = dynamicParent.lookup("NOT_LISTED");

  var ordered = new SourceProjectContext();
  ordered.apply("define", "ORDERED", "first", "project:define1");
  ordered.apply("set", "ORDERED", "second", "project:set");
  ordered.apply("setenv", "ENV_DEFAULT", null, "project:setenv");
  ordered.apply("unset", "ORDERED", null, "project:unset");
  ordered.apply("define", "ORDERED", "third", "project:define2");
  ordered.apply("undefine", "ORDERED", null, "project:undefine");
  ordered.apply("haxedef", "COMPILER_ONLY", "1", "project:haxedef");
  result.ordered = ordered.lookup("ORDERED");
  result.setenvDefault = ordered.lookup("ENV_DEFAULT");
  result.compilerOnlyCondition = pack(ordered.condition("COMPILER_ONLY", null));
  result.opaque = ordered.opaque;

  var originalEnv = Sys.getEnv("CAMMIE_SOURCE_CONTEXT_SENTINEL");
  ordered.apply("setenv", "CAMMIE_SOURCE_CONTEXT_SENTINEL", "changed", "project:setenv");
  result.environmentBefore = originalEnv;
  result.environmentAfter = Sys.getEnv("CAMMIE_SOURCE_CONTEXT_SENTINEL");

  var interpolation = new SourceProjectContext();
  interpolation.apply("define", "ROOT_DIR", "build", "root:1");
  var chained = interpolation.interpolate("${ROOT_DIR}/out");
  interpolation.apply("define", "OUTPUT_DIR", chained.value, "root:2");
  interpolation.apply("define", "VERSION", "10", "root:3");
  interpolation.apply("define", "EMPTY", "", "root:4");
  interpolation.apply("define", "CYCLE_A", "${CYCLE_B}", "root:5");
  interpolation.apply("define", "CYCLE_B", "${CYCLE_A}", "root:6");
  result.chained = pack(interpolation.interpolate("${OUTPUT_DIR}/bundle"));
  result.stringCompare = pack(interpolation.interpolate("${VERSION>=2}"));
  result.emptyCompare = pack(interpolation.interpolate("${EMPTY==}"));
  result.projectProperty = pack(interpolation.interpolate("${project.workingDirectory}"));
  result.projectDirectory = pack(interpolation.interpolate("${projectDirectory}"));
  result.haxelib = pack(interpolation.interpolate("${haxelib:lime}"));
  result.cycle = pack(interpolation.interpolate("${CYCLE_A}"));

  var projectOverrides = SourceProjectContext.seed([
   {name:"projectDirectory", state:"enabled", provenance:"source:project-value"},
   {name:"app.file", state:"enabled", provenance:"source:project-value"}
  ], [
   {name:"projectDirectory", value:"captured/project", provenance:"source:project-value"},
   {name:"app.file", value:"captured-app.xml", provenance:"source:project-value"}
  ], true);
  result.projectDirectoryOverride = pack(projectOverrides.interpolate("${projectDirectory}"));
  result.appFileOverride = pack(projectOverrides.interpolate("${app.file}"));
  result.appFileCompare = pack(projectOverrides.interpolate("${app.file==captured-app.xml}"));
  result.uncapturedAppFile = pack(complete.interpolate("${app.file}"));
  result.uncapturedProjectDirectoryComplete = pack(complete.interpolate("${projectDirectory}"));

  var aliases = new SourceProjectContext();
  aliases.apply("define", "TARGET", "resolved-target", "project:target");
  aliases.apply("define", "ALIAS", "TARGET", "project:alias");
  aliases.apply("define", "NORMAL", "ordinary-value", "project:normal");
  result.doubleAlias = pack(aliases.interpolate("$${ALIAS}"));
  result.doubleAliasOrder = pack(aliases.interpolate("${NORMAL}|$${ALIAS}|${TARGET}"));
  result.unknownDoubleAlias = pack(aliases.interpolate("$${MISSING_ALIAS}"));
  aliases.apply("define", "UNKNOWN_TARGET_ALIAS", "MISSING_TARGET", "project:unknown-target");
  result.unknownDoubleTarget = pack(aliases.interpolate("$${UNKNOWN_TARGET_ALIAS}"));
  result.emptyDoubleAlias = pack(aliases.interpolate("$${}"));
  result.invalidDoubleAlias = pack(aliases.interpolate("$${bad alias}"));
  var doubleCycle = new SourceProjectContext(null, null, true);
  doubleCycle.apply("define", "DOUBLE_CYCLE_A", "${DOUBLE_CYCLE_B}", "cycle:a");
  doubleCycle.apply("define", "DOUBLE_CYCLE_B", "${DOUBLE_CYCLE_A}", "cycle:b");
  result.doubleAliasCycle = pack(doubleCycle.interpolate("$${DOUBLE_CYCLE_A}"));

  result.limeDifferentials = [
   limeDifferential("${A}", [{name:"A", value:"assets"}]),
   limeDifferential("${A}/bundle", [
    {name:"A", value:"${B}"}, {name:"B", value:"C"}, {name:"C", value:"assets"}
   ]),
   limeDifferential("$${A}", [
    {name:"A", value:"TARGET"}, {name:"TARGET", value:"mapped-target"}
   ]),
   limeDifferential("$${A}", [
    {name:"A", value:"${B}"}, {name:"B", value:"C"}, {name:"C", value:"assets"}
   ]),
   limeDifferential("${${A}}", [{name:"A", value:"B"}, {name:"B", value:"nested-value"}]),
   limeDifferential("${VERSION>=2}", [{name:"VERSION", value:"10"}]),
   limeDifferential("${ A }", [{name:"A", value:"trimmed-value"}]),
   limeDifferential("$${}", []),
   limeDifferential("$${bad alias}", []),
   limeDifferential("${NORMAL}|$${ALIAS}|${TARGET}", [
    {name:"NORMAL", value:"plain"}, {name:"ALIAS", value:"TARGET"}, {name:"TARGET", value:"mapped"}
   ])
  ];

  var injected = SourceProjectContext.seed([
   {name:"LEFT", state:"disabled", provenance:"build"},
   {name:"RIGHT", state:"enabled", provenance:"build"}
  ], [{name:"INJECTED", value:"LEFT || RIGHT", provenance:"project"}], true, "");
  result.injectedIf = pack(injected.condition("${INJECTED}", null));
  result.injectedUnless = pack(injected.condition(null, "${INJECTED}"));

  var mergeParent = SourceProjectContext.seed([
   {name:"ROOT_TARGET", state:"enabled", provenance:"parent"},
   {name:"CAN_ADD", state:"disabled", provenance:"parent:unset"},
   {name:"UNKNOWN_PARENT", state:"unresolved", provenance:"parent:unknown"}
  ], [{name:"ROOT_TARGET", value:"parent-value", provenance:"parent"}], true);
  var mergeChild = mergeParent.clone();
  mergeChild.apply("define", "ROOT_TARGET", "child-value", "child");
  mergeChild.apply("define", "CHILD_ONLY", "child-value", "child");
  mergeChild.apply("define", "CAN_ADD", "after-unset", "child");
  mergeChild.apply("define", "UNKNOWN_PARENT", "unsafe-child", "child");
  mergeParent.mergeNonOverwriting(mergeChild);
  result.mergePreserved = mergeParent.lookup("ROOT_TARGET");
  result.mergeNew = mergeParent.lookup("CHILD_ONLY");
  result.mergeExplicitAbsent = mergeParent.lookup("CAN_ADD");
  result.mergeUncertain = mergeParent.lookup("UNKNOWN_PARENT");
  result.mergeValues = mergeParent.valuesSnapshot();
  result.completeClone = mergeParent.clone().flagsComplete;

  var partialParent = SourceProjectContext.seed([], [], false);
  var partialChild = partialParent.clone();
  partialChild.apply("define", "POSSIBLE_BUILD_INPUT", "child", "child");
  partialParent.mergeNonOverwriting(partialChild);
  result.partialMerge = partialParent.lookup("POSSIBLE_BUILD_INPUT");

  File.saveContent("result.json", haxe.Json.stringify(result));
 }
}'''


class SourceProjectContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="source-project-context-", dir=TEST_TMP)
        cls.addClassCleanup(temp.cleanup)
        work = Path(temp.name)
        lime_helper = (LIME_TOOLS / "ProjectHelper.hx").read_text(encoding="utf-8")
        lime_parser = (LIME_TOOLS / "ProjectXMLParser.hx").read_text(encoding="utf-8")
        replace_variable = extract_haxe_function(
            lime_helper, "public static function replaceVariable(project:HXProject, string:String):String"
        )
        substitute = extract_haxe_function(lime_parser, "private function substitute(string:String):String")
        substitute = substitute.replace("private function", "public function", 1)
        is_valid_element = extract_haxe_function(lime_parser, "private function isValidElement(element:Access, section:String):Bool")
        is_valid_element = is_valid_element.replace("private function", "public function", 1)
        regex_fields = []
        for field in ("doubleVarMatch", "varMatch"):
            match = re.search(rf"\tprivate static var {field} = .*?;", lime_parser)
            if match is None:
                raise AssertionError(f"Pinned Lime parser no longer declares {field}")
            regex_fields.append(match.group(0).replace("\tprivate static", "\tstatic", 1))
        lime_dir = work / "lime" / "tools"
        lime_dir.mkdir(parents=True)
        (lime_dir / "HXProject.hx").write_text(
            "package lime.tools;\n"
            "class HXProject {\n"
            " public var defines:Map<String, Dynamic> = new Map();\n"
            " public var environment:Map<String, Dynamic> = null;\n"
            " public var workingDirectory:String = \"unused\";\n"
            " public var command:String = \"\";\n"
            "}\n", encoding="utf-8", newline="\n"
        )
        (lime_dir / "Haxelib.hx").write_text(
            "package lime.tools;\n"
            "class Haxelib { public function new(name:String) {} public static function getPath(lib:Haxelib, force:Bool):String throw \"unused host lookup\"; }\n",
            encoding="utf-8", newline="\n"
        )
        (lime_dir / "Path.hx").write_text(
            "package lime.tools;\nclass Path { public static function standardize(path:String):String return path; }\n",
            encoding="utf-8", newline="\n"
        )
        (lime_dir / "Log.hx").write_text(
            "package lime.tools;\nclass Log { public static function info(message:String, ?details:Dynamic):Void {} }\n",
            encoding="utf-8", newline="\n"
        )
        (lime_dir / "ProjectHelper.hx").write_text(
            "package lime.tools;\nclass ProjectHelper {\n" + replace_variable + "\n}\n",
            encoding="utf-8", newline="\n"
        )
        (lime_dir / "ProjectXMLParserReference.hx").write_text(
            "package lime.tools;\nimport haxe.xml.Access;\nclass ProjectXMLParserReference extends HXProject {\n"
            + " public function new() {}\n" + "\n".join(regex_fields) + "\n"
            + substitute + "\n" + is_valid_element + "\n}\n",
            encoding="utf-8", newline="\n"
        )
        (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["CAMMIE_SOURCE_CONTEXT_SENTINEL"] = "original"
        run = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
            cwd=work, env=env, text=True, capture_output=True, timeout=90,
        )
        if run.returncode != 0:
            raise AssertionError(run.stdout + run.stderr)
        cls.result = json.loads((work / "result.json").read_text(encoding="utf-8"))

    def test_partial_and_complete_build_context_are_distinct(self):
        result = self.result
        self.assertEqual(result["partialMissing"]["state"], "unresolved")
        self.assertEqual(result["partialBare"]["state"], "unresolved")
        self.assertEqual(result["flagOnlyBare"]["boolValue"], True)
        self.assertEqual(result["flagOnlyLookup"]["valueState"], "unresolved")
        self.assertEqual(result["flagOnlyValue"]["state"], "unresolved")
        self.assertTrue(result["completeClone"])
        self.assertEqual(result["completeMissing"]["state"], "disabled")
        self.assertEqual(result["completeBareMissing"]["boolValue"], False)
        self.assertEqual(result["completeMissingValue"]["state"], "known")
        self.assertEqual(result["completeMissingValue"]["value"], "NOT_CAPTURED")
        self.assertEqual(result["completeMissingCompare"]["value"], "true")
        self.assertEqual(result["partialMissingCompare"]["state"], "unresolved")

    def test_flag_presence_is_separate_from_false_string_value(self):
        result = self.result
        self.assertEqual(result["falseTextBare"]["boolValue"], True)
        self.assertEqual(result["falseTextExpanded"]["boolValue"], False)
        self.assertEqual(result["valueUncertainty"]["state"], "enabled")
        self.assertEqual(result["valueUncertainty"]["valueState"], "unresolved")
        self.assertEqual(result["valueUncertaintyBare"]["boolValue"], True)
        self.assertEqual(result["valueUncertaintyExpanded"]["state"], "unresolved")
        self.assertEqual(result["presenceUncertainty"]["state"], "unresolved")
        self.assertEqual(result["presenceUncertaintyExpanded"]["state"], "unresolved")
        self.assertEqual(result["taintedMissing"]["state"], "unresolved")
        self.assertFalse(result["unknownIncludeComplete"])
        self.assertEqual(result["unknownIncludeEnabled"]["value"], "known")
        self.assertEqual(result["unknownIncludeAbsent"]["state"], "unresolved")
        self.assertEqual(result["unknownIncludeMissing"]["state"], "unresolved")
        self.assertEqual(result["unresolvedMergeParent"]["value"], "parent-value")
        self.assertEqual(result["unresolvedMergeOldAbsent"]["state"], "unresolved")
        self.assertEqual(result["unresolvedMergeNew"]["state"], "unresolved")
        self.assertFalse(result["dynamicMergeComplete"])
        self.assertEqual(result["dynamicMergeParent"]["value"], "parent-value")
        self.assertEqual(result["dynamicMergeOldAbsent"]["state"], "unresolved")
        self.assertEqual(result["dynamicMergeMissing"]["state"], "unresolved")

    def test_command_is_an_explicit_condition_input_independent_of_unset_flags(self):
        result = self.result
        self.assertTrue(result["commandMatchesUnset"]["boolValue"])
        self.assertFalse(result["commandDoesNotMatch"]["boolValue"])
        self.assertEqual(result["unknownCommand"]["state"], "unresolved")
        self.assertTrue(result["commandMatchesPinnedParser"])

    def test_ordered_operations_are_local_and_haxedef_is_opaque(self):
        result = self.result
        self.assertEqual(result["ordered"]["state"], "disabled")
        self.assertEqual(result["setenvDefault"]["value"], "1")
        self.assertEqual(result["compilerOnlyCondition"]["state"], "unresolved")
        self.assertTrue(any(item["operation"] == "haxedef" for item in result["opaque"]))
        self.assertTrue(any(item["operation"] == "undefine-haxedef" for item in result["opaque"]))
        self.assertEqual(result["environmentBefore"], "original")
        self.assertEqual(result["environmentAfter"], "original")

    def test_interpolation_comparisons_and_unsupported_host_inputs(self):
        result = self.result
        self.assertEqual(result["chained"]["value"], "build/out/bundle")
        self.assertEqual(result["stringCompare"]["value"], "false")
        self.assertEqual(result["emptyCompare"]["value"], "true")
        self.assertEqual(result["cycle"]["state"], "unresolved")
        self.assertIn("variable-cycle", result["cycle"]["diagnosticCodes"])
        self.assertEqual(result["projectProperty"]["state"], "unresolved")
        self.assertEqual(result["projectDirectory"]["state"], "unresolved")
        self.assertEqual(result["haxelib"]["state"], "unresolved")
        self.assertEqual(result["projectDirectoryOverride"]["value"], "captured/project")
        self.assertEqual(result["appFileOverride"]["value"], "captured-app.xml")
        self.assertEqual(result["appFileCompare"]["value"], "true")
        self.assertEqual(result["uncapturedAppFile"]["state"], "unresolved")
        self.assertEqual(result["uncapturedProjectDirectoryComplete"]["state"], "unresolved")

    def test_double_variable_alias_substitutes_before_normal_variables(self):
        result = self.result
        self.assertEqual(result["doubleAlias"]["value"], "resolved-target")
        self.assertEqual(result["doubleAliasOrder"]["value"],
                         "ordinary-value|resolved-target|resolved-target")
        self.assertEqual(result["unknownDoubleAlias"]["state"], "unresolved")
        self.assertEqual(result["unknownDoubleTarget"]["state"], "unresolved")
        self.assertEqual(result["emptyDoubleAlias"]["state"], "unresolved")
        self.assertEqual(result["invalidDoubleAlias"]["state"], "unresolved")
        self.assertEqual(result["doubleAliasCycle"]["state"], "unresolved")
        self.assertIn("variable-cycle", result["doubleAliasCycle"]["diagnosticCodes"])

    def test_interpolation_matches_extracted_pinned_lime_methods(self):
        for case in self.result["limeDifferentials"]:
            with self.subTest(input=case["input"]):
                self.assertEqual(case["state"], "known", case)
                self.assertEqual(case["actual"], case["expected"], case)

    def test_if_and_unless_preserve_lime_split_order(self):
        self.assertEqual(self.result["injectedIf"]["boolValue"], False)
        self.assertEqual(self.result["injectedUnless"]["boolValue"], False)
        self.assertEqual(self.result["unlessAbsent"]["boolValue"], True)

    def test_include_merge_is_non_overwriting_and_conservative(self):
        result = self.result
        self.assertEqual(result["mergePreserved"]["value"], "parent-value")
        self.assertEqual(result["mergeNew"]["value"], "child-value")
        self.assertEqual(result["mergeExplicitAbsent"]["value"], "after-unset")
        self.assertEqual(result["mergeUncertain"]["state"], "unresolved")
        self.assertEqual(result["partialMerge"]["state"], "unresolved")
        names = [item["name"] for item in result["mergeValues"]]
        self.assertEqual(names, sorted(names))
        self.assertIn("CHILD_ONLY", names)
        self.assertNotIn("UNKNOWN_PARENT", names)


if __name__ == "__main__":
    unittest.main()
