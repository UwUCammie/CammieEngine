"""Exercise the selected-owner metadata loader, including reload and isolation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    start = source.index('\tfunction ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameSongViewTest(unittest.TestCase):
    def test_real_loader_uses_selected_owner_and_preserves_metadata_edits(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(method(source, name) for name in (
            'codenameSelectedRoot', 'codenameSourceFolder', 'codenameDifficulty', 'getCodenameSongView'))
        fixture = r'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CompatScriptManifest.CompatScriptManifestData;
class CodenameModRuntime {
 public static function activeRoot():String return '';
}
class FNFAssets {
 public static function exists(path:String):Bool return FileSystem.exists(path);
 public static function getText(path:String):String return File.getContent(path);
}
class Song {
 public static function storageFolder(chart:Dynamic):String return chart.song;
}
class Main {
 static var SONG:Dynamic={song:"fixture",speed:1};
 var manifest:CompatScriptManifestData;
 var cachedCodenameSongView:CodenameSongView=null;
 var storyDifficultyText:String="normal";
 public function new(selected:String,engine:String="Codename Engine") {
  manifest={version:1,selectedRoot:selected,roots:[
   {path:"assets/imported_mods/a",engine:engine},
   {path:"assets/imported_mods/b",engine:engine}]};
 }
 function getCompatScriptManifest():CompatScriptManifestData return manifest;
 function getCodenameScriptPlan():Dynamic return {stages:{normal:"room",Hard:"room"}};
 static function check(ok:Bool, message:String):Void if(!ok) throw message;
''' + methods + r'''
 static function save(root:String,source:String,title:String):String {
  var file=CodenameSongMetadata.path(root,source);
  FileSystem.createDirectory(Path.directory(file));
  File.saveContent(file,CodenameSongMetadata.stringify(CodenameSongMetadata.create(source,
   {name:source,displayName:title,custom:{array:([1,null,false]:Array<Dynamic>),edited:true}})));
  return file;
 }
 static function main():Void {
  var a="assets/imported_mods/a", b="assets/imported_mods/b";
  var firstFile=save(a,"Fixture","First title");
  var secondFile=save(b,"Fixture","Second title");
  var first=new Main(a); var second=new Main(b);
  var view=first.getCodenameSongView();
  check(view.getField("meta").displayName=="First title","first owner");
  check(second.getCodenameSongView().getField("meta").displayName=="Second title","selected second owner");
  view.getField("meta").custom.edited=false;
  check(first.getCodenameSongView()==view && !first.getCodenameSongView().getField("meta").custom.edited,
   "script scope must share mutable metadata");
  check(!Reflect.hasField(SONG,"meta"),"foreign data polluted native chart");
  var edited=Json.parse(File.getContent(firstFile)); edited.meta.displayName="User edit";
  File.saveContent(firstFile,Json.stringify(edited));
  check(new Main(a).getCodenameSongView().getField("meta").displayName=="User edit","reload must read preserved edit");
  check(view.getField("meta").displayName=="First title","old state metadata mutated on reload");
  FileSystem.deleteFile(firstFile);
  check(new Main(a).getCodenameSongView().getField("meta")==null,"missing owner borrowed foreign metadata");
  check(new Main(b,"Psych Engine").getCodenameSongView().getField("meta")==null,"foreign engine metadata exposed");
  File.saveContent(firstFile,File.getContent(secondFile));
  var invalid=Json.parse(File.getContent(firstFile)); invalid.song="AnotherSong";
  File.saveContent(firstFile,Json.stringify(invalid));
  check(new Main(a).getCodenameSongView().getField("meta")==null,"wrong song metadata accepted");
  File.saveContent(firstFile,"{broken");
  check(new Main(a).getCodenameSongView().getField("meta")==null,"malformed metadata accepted");
  FileSystem.deleteFile(firstFile);
  FileSystem.createDirectory(a+"/songs/FIXTURE");
  check(new Main(a).getCodenameSongView().getField("meta")==null,"ambiguous source case accepted");
  FileSystem.deleteDirectory(a+"/songs/FIXTURE");
  save(a,"Fixture","Legacy title");
  var entries:Dynamic={normal:{selectedFile:"meta.json",fileMeta:{bpm:120},inlineMeta:null},
   Hard:{selectedFile:"meta-Hard.json",fileMeta:{name:"authored-alias",displayName:"Hard title",bpm:150},
    inlineMeta:{bpm:175,displayName:null}}};
  var resolvedFile=CodenameSongMetadata.resolvedPath(a,"Fixture");
  var resolved=CodenameSongMetadata.createResolved("Fixture",["normal","Hard"],entries);
  File.saveContent(resolvedFile,CodenameSongMetadata.stringifyResolved(resolved));
  var hard=new Main(a); hard.storyDifficultyText="hard";
  var hardMeta=hard.getCodenameSongView().getField("meta");
  check(hardMeta.bpm==175 && hardMeta.displayName=="Hard title" && hardMeta.name=="Fixture",
   "selected difficulty defaults/file/inline precedence");
  check(new Main(a).getCodenameSongView().getField("meta").bpm==120,"normal difficulty isolation");
  resolved.difficulties.Hard.resolved.bpm=99;
  File.saveContent(resolvedFile,Json.stringify(resolved));
  check(new Main(a).getCodenameSongView().getField("meta")==null,"inconsistent sibling borrowed raw metadata");
  Reflect.setField(entries,"hARD",{selectedFile:"meta-hARD.json",fileMeta:{bpm:180},inlineMeta:null});
  resolved=CodenameSongMetadata.createResolved("Fixture",["normal","Hard","hARD"],entries);
  File.saveContent(resolvedFile,CodenameSongMetadata.stringifyResolved(resolved));
  hard=new Main(a); hard.storyDifficultyText="hard";
  check(hard.getCodenameSongView().getField("meta")==null,"ambiguous difficulty borrowed base metadata");
  resolved.song="AnotherSong";
  File.saveContent(resolvedFile,Json.stringify(resolved));
  check(new Main(a).getCodenameSongView().getField("meta")==null,"foreign sibling accepted");
 }
}'''
        fixture = fixture.replace('class Main {', 'class SongViewFixture {').replace(
            'new Main(', 'new SongViewFixture(')
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'SongViewFixture.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(work),
                '-cp', str(ROOT / 'source'), '--run', 'SongViewFixture'], cwd=work, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
