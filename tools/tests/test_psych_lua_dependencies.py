from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychLuaDependenciesTest(unittest.TestCase):
    def test_literal_recursive_dependencies_and_safe_layout(self):
        module = (ROOT / 'source/ModuleFunctions.hx').read_text()
        self.assertIn('PsychLuaScriptDependencies.discover(root.base)', module)
        self.assertIn('copyImportFileNonOverwriting(dependency.source,', module)
        self.assertIn('if (!isImportFile(Path.join([destination, relative])))', module)
        fixture = '''import sys.FileSystem;
        import sys.io.File;
        import haxe.io.Path;
        class DependencyTest {
            static function check(ok:Bool, label:String):Void if (!ok) throw label;
            static function write(path:String, text:String):Void {
                var dir=Path.directory(path);
                if(!FileSystem.exists(dir)) FileSystem.createDirectory(dir);
                File.saveContent(path,text);
            }
            static function main():Void {
                var root="__DONOR__";
                write(Path.join([root,"data","song","script.lua"]),
                    "addLuaScript('epicScripts/first')\\n-- addLuaScript('ignored/comment')\\n"
                    + "addLuaScript(variable)\\naddLuaScript('../unsafe')\\n");
                write(Path.join([root,"epicScripts","first.lua"]),
                    "addLuaScript(\\\"epicScripts/second.lua\\\", true)\\n");
                write(Path.join([root,"epicScripts","second.lua"]),
                    "addLuaScript('epicScripts/first')\\n");
                write(Path.join([root,"ignored","comment.lua"]), "");
                var scan=PsychLuaScriptDependencies.discover(root);
                check(scan.complete,"bounded dependency walk incomplete");
                check(scan.files.length==2,"literal recursion or dedup failed: "+scan.files.length);
                check(scan.files[0].relative=="epicScripts/first.lua"
                    && scan.files[1].relative=="epicScripts/second.lua","relative layout changed");
                check(PsychLuaScriptDependencies.relativeLuaPath("../outside")==null,
                    "traversal accepted");
                check(PsychLuaScriptDependencies.relativeLuaPath("assets/imported_mods/other/file")==null,
                    "other namespace accepted");
                check(PsychLuaScriptDependencies.relativeLuaPath("folder/file.hscript")==null,
                    "non-Lua target accepted");
                var refs=PsychLuaScriptDependencies.literalReferences(
                    "-- addLuaScript('comment')\\naddLuaScript('one')\\naddLuaScript(foo)\\n");
                check(refs.length==1 && refs[0]=="one.lua", "literal parser accepted comment/dynamic call");
            }
        }'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            source = Path(folder) / 'PsychLuaScriptDependencies.hx'
            source.write_text((ROOT / 'source/PsychLuaScriptDependencies.hx').read_text(), newline='\n')
            donor = Path(folder) / 'donor'
            donor.mkdir()
            (Path(folder) / 'DependencyTest.hx').write_text(
                fixture.replace('__DONOR__', str(donor).replace('\\', '/')), newline='\n')
            run = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                  '-main', 'DependencyTest', '--interp'],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
