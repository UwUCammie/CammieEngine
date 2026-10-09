"""Compiled Lime manifests share the receipt-backed Psych/NV asset profile."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
import test_psych_asset_profile as profile_fixture
import test_source_mapped_asset_publisher as publisher_fixture
ROOT=Path(__file__).resolve().parents[2]

class CompiledAssetManifestTest(unittest.TestCase):
    def test_serialized_and_json_tables_with_data_only_limits(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            p=Path(d)
            (p/'Main.hx').write_text(r'''class Main {
 static function check(v:Bool,s:String):Void {if(!v)throw s;}
 static function main(){
 var assets:Array<Dynamic>=[{id:"alias",path:"assets/image.png",type:"IMAGE",size:4,preload:false},
 {id:"embedded",className:"__ASSET__font",type:"FONT",size:8}];
 var serial=haxe.Serializer.run(assets);
 for(version in [2,3]) {
 var data:Dynamic={version:version,rootPath:"../",libraryType:null,libraryArgs:[],assets:version==2?cast serial:cast assets};
 var parsed=SourceCompiledAssetManifest.parse(haxe.Json.stringify(data));
 check(parsed.assets[0].id=="alias"&&parsed.assets[1].className=="__ASSET__font","preserve source identities");
 }
 for(serial in ["au2147483647h","acy4:Mainh","ao y1:xgh","ar0h","ao y1:xnah","aohTRAILING"]){
 var failed=false;try SourceCompiledAssetManifest.parse(haxe.Json.stringify({version:2,assets:serial}))catch(_:Dynamic)failed=true;
 check(failed,"reject malformed, allocating, typed or cyclic payload: "+serial);
 }
 check(SourceCompiledAssetProfile.relativePath("manifest","../",true)=="","source manifest parent is allowed within root");
 check(SourceCompiledAssetProfile.relativePath("manifest","../../",true)==null,"root traversal rejected");
 check(SourceCompiledAssetProfile.relativePath("","C:/host",false)==null,"absolute path rejected");
 }
}''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',d,'--main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def profile(self, manifests, engine="Nightmare Vision", **options):
        return profile_fixture.PsychAssetProfileTest.run_profile(self,None,project_text=None,
            engine=engine,project_files=manifests,**options)[0]

    def test_receipt_backed_file_aliases_and_embedded_gap_for_both_engines(self):
        manifest={"version":3,"rootPath":"../","assets":[
            {"id":"art-alias","path":"assets/pixels.bin","type":"IMAGE","size":4},
            {"id":"embedded-font","className":"__ASSET__font","type":"FONT","size":10}]}
        for engine in ["Psych Engine","Nightmare Vision"]:
            with self.subTest(engine=engine):
                out=self.profile({"manifest/default.json":json.dumps(manifest),"assets/pixels.bin":b"RGBA"},engine)
                p=out['profile']
                self.assertEqual(p['provenance'],'receipt-bound')
                self.assertFalse(p['complete'])
                self.assertFalse(p['librariesComplete'])
                self.assertFalse(p['mappingScopeUnknown'])
                self.assertEqual(len(p['candidates']),1)
                self.assertEqual(p['candidates'][0]['assetId'],'art-alias')
                self.assertEqual(out['mappedEvents'][0]['sourceRelative'],'assets/pixels.bin')
                self.assertEqual(out['mappedEvents'][0]['assetId'],'art-alias')
                self.assertEqual(out['mappedWalk']['status'],'incomplete')
                self.assertTrue(any('manifest-embedded-unavailable' in x for x in p['diagnostics']))

    def test_manifest_escape_and_custom_libraries_are_not_published(self):
        for path in ['../../outside','/absolute','C:/absolute']:
            out=self.profile({'manifest/default.json':json.dumps({'version':3,'rootPath':'../','assets':[
                {'id':'bad','path':path,'type':'IMAGE'}]})})
            self.assertEqual(out['profile']['provenance'],'invalid')
            self.assertEqual(out['mappedEvents'],[])
        out=self.profile({'manifest/default.json':json.dumps({'version':3,'rootPath':'../','libraryType':'custom.Library','assets':[]})})
        self.assertFalse(out['profile']['complete'])
        self.assertEqual(out['profile']['candidates'],[])
        self.assertTrue(any('manifest-library-unsupported' in x for x in out['profile']['diagnostics']))


    def test_shared_publisher_preserves_named_ids_and_unlisted_disk_assets(self):
        for engine, scope in [("Psych Engine", "package"), ("Nightmare Vision", "package"), ("Nightmare Vision", "core")]:
            for embedded in [False, True]:
                with self.subTest(engine=engine, scope=scope, embedded=embedded):
                    assets=[{"id":"atlas-json","path":"assets/images/Animation.json","type":"TEXT"}]
                    if embedded: assets.append({"id":"compiled-font","className":"__ASSET__font","type":"FONT"})
                    files={
                        "manifest/default.json":json.dumps({"version":3,"rootPath":"../","assets":assets}).encode(),
                        "manifest/shared.json":json.dumps({"version":3,"rootPath":"../","assets":[
                            {"id":"atlas-image","path":"assets/images/pixels.png","type":"IMAGE"}]}).encode(),
                        "assets/images/Animation.json":b"fixture bytes",
                        "assets/images/pixels.png":b"fixture bytes",
                        "assets/images/unlisted.png":b"disk only mod asset"}
                    out=publisher_fixture.SourceMappedAssetPublisherTest.run_fixture(self,"compiled-identity",None,
                        files,engine=engine,scope=scope)
                    self.assertFalse(out['failed'],out['diagnostics'])
                    self.assertEqual(out['published'],2)
                    self.assertEqual(out['profileComplete'],not embedded)

    def test_duplicate_shadowing_manifest_tampering_and_project_priority(self):
        assets=[{"id":"duplicate","path":"assets/pixels.bin","type":"IMAGE"},
                {"id":"duplicate","className":"__ASSET__latest","type":"IMAGE"}]
        files={"manifest/default.json":json.dumps({"version":3,"rootPath":"../","assets":assets}),
               "assets/pixels.bin":b"RGBA"}
        out=self.profile(files)
        self.assertEqual(out['profile']['candidates'],[])
        self.assertFalse(out['profile']['complete'])
        tampered=self.profile(files,tamper_included_project="manifest/default.json")
        self.assertEqual(tampered['profile']['provenance'],'invalid')
        self.assertEqual(tampered['mappedEvents'],[])
        out=self.profile(files,cancel_after=3)
        self.assertTrue(out['resolverCancellation']['caught'])
        preferred,_=profile_fixture.PsychAssetProfileTest.run_profile(self,None,
            project_text='<project><assets path="assets/pixels.bin" /></project>',project_files=files)
        self.assertEqual(preferred['profile']['projectRelative'],'nested/root/Project.xml')
        self.assertNotEqual(preferred['profile'].get('compiledManifests'),True)


    def test_declared_raw_types_in_media_directories_replace_only_verified_outputs(self):
        for engine,scope in [("Psych Engine","package"),("Nightmare Vision","package"),("Nightmare Vision","core")]:
            with self.subTest(engine=engine,scope=scope):
                files={
                    "manifest/default.json":json.dumps({"version":3,"rootPath":"../","assets":[
                        {"id":"atlas-json","path":"assets/images/data.csv","type":"TEXT"}]}).encode(),
                    "manifest/shared.json":json.dumps({"version":3,"rootPath":"../","assets":[
                        {"id":"atlas-image","path":"assets/images/clip.mp4","type":"BINARY"}]}).encode(),
                    "assets/images/data.csv":b"fixture bytes","assets/images/clip.mp4":b"fixture bytes"}
                prefix="assets/imported_mods/source-mapped-assets-fixture/"+("__nmv_core/" if scope=="core" else "")
                out=publisher_fixture.SourceMappedAssetPublisherTest.run_fixture(self,"compiled-identity",None,files,
                    engine=engine,scope=scope,masked=[prefix+"images/data.csv",prefix+"images/clip.mp4"])
                self.assertFalse(out['failed'],out['diagnostics'])
                self.assertEqual(out['published'],2)

if __name__=='__main__':unittest.main()
