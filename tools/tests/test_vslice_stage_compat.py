"""Old generated V-Slice stage props gain the donor hitbox rule at runtime."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class VSliceStageCompatTest(unittest.TestCase):
    def test_scoped_structural_repair_is_idempotent(self):
        source = r'''
class Main {
 static function same(a:Dynamic,b:Dynamic):Void if(a!=b) throw 'mismatch: '+a+' != '+b;
 static function main():Void {
  var owner=CompatScriptManifest.create('/donor/visuals',ImportEngine.V_SLICE);
  var other=CompatScriptManifest.create('/donor/visuals',ImportEngine.PSYCH);
  var vars:Map<String,Dynamic>=new Map();
  var sayori={id:'sayori'};
  vars.set('vSliceProp_bg_sayori_2',sayori);
  vars.set('unrelated_bg_sayori_2',{id:'other'});
  same(VSliceStageCompat.legacyGeneratedProp('BG Sayori',vars),sayori);
  same(VSliceStageCompat.legacyGeneratedProp('BG Yuri',vars),null);
  vars.set('vSliceProp_bg_sayori_9',{id:'duplicate'});
  same(VSliceStageCompat.legacyGeneratedProp('BG Sayori',vars),null);
  var old='var vSliceProp_back_0;\nvar vSliceProp_glow_1;\nvar vSliceProp_front_2;\nvar vSliceProp_solid_3;\nfunction start(song) {\n'
   +'    stage.setCharacterZ("bf", 300);\n    stage.setCharacterZ("dad", 200);\n    stage.setCharacterZ("gf", 100);\n'
   +'    vSliceProp_back_0 = new FlxSprite(-1400, -2100);\n'
   +'    vSliceProp_back_0.frames = FlxAtlasFrames.fromSparrow(hscriptPath + "prop-back-0.png", hscriptPath + "prop-back-0.xml");\n'
   +'    vSliceProp_back_0.scale.set(4, 4);\n'
   +'    vSliceProp_back_0.scrollFactor.set(0.95, 0.95);\n'
   +'    addSprite(vSliceProp_back_0, BEHIND_ALL);\n'
   +'    vSliceProp_glow_1 = new FlxSprite(-1376, -1024);\n'
   +'    vSliceProp_glow_1.loadGraphic(hscriptPath + "prop-glow-1.png");\n'
   +'    vSliceProp_glow_1.scale.set(1.9, 1.9);\n'
   +'    vSliceProp_glow_1.scrollFactor.set(1, 1);\n'
   +'    addSprite(vSliceProp_glow_1, BEHIND_BF);\n'
   +'    vSliceProp_front_2 = new FlxSprite(20, 30);\n'
   +'    vSliceProp_front_2.loadGraphic(hscriptPath + "prop-front-2.png");\n'
   +'    vSliceProp_front_2.scale.set(1.5, 1.5);\n'
   +'    vSliceProp_front_2.scrollFactor.set(1, 1);\n'
   +'    addSprite(vSliceProp_front_2, BEHIND_BF);\n'
   +'    vSliceProp_solid_3 = new FlxSprite(0, 0);\n'
   +'    vSliceProp_solid_3.makeGraphic(1, 1, 0xFF000000);\n'
   +'    vSliceProp_solid_3.scale.set(2, 2);\n'
   +'    vSliceProp_solid_3.scrollFactor.set(1, 1);\n'
   +'    addSprite(vSliceProp_solid_3, BEHIND_ALL);\n'
   +'    custom.scale.set(3, 3);\n    custom.scrollFactor.set(1, 1);\n}\n';
  same(VSliceStageCompat.normalizeGeneratedPropHitboxes(old,other,true),old);
  same(VSliceStageCompat.normalizeGeneratedPropHitboxes(old,owner,false),old);
  same(VSliceStageCompat.normalizeGeneratedPropHitboxes(old,null,true),old);
  var normalized=VSliceStageCompat.normalizeGeneratedPropHitboxes(old,owner,true);
  if(normalized==old) throw 'old generated props were not repaired';
  same(normalized.split('vSliceProp_back_0.updateHitbox();').length,2);
  same(normalized.split('vSliceProp_glow_1.updateHitbox();').length,2);
  same(normalized.split('vSliceProp_front_2.updateHitbox();').length,2);
  same(normalized.split('vSliceProp_solid_3.updateHitbox();').length,2);
  same(normalized.split('custom.updateHitbox();').length,1);
  if(normalized.indexOf('scale.set(4, 4);\n    vSliceProp_back_0.updateHitbox();\n    vSliceProp_back_0.scrollFactor')<0)
   throw 'donor scale-hitbox-scroll order changed';
  same(VSliceStageCompat.normalizeGeneratedPropHitboxes(normalized,owner,true),normalized);
  same(VSliceStageCompat.normalizeGeneratedPropLayers(normalized,other,true),normalized);
  same(VSliceStageCompat.normalizeGeneratedPropLayers(normalized,owner,false),normalized);
  var layered=VSliceStageCompat.normalizeGeneratedPropLayers(normalized,owner,true);
  if(layered.indexOf('stage.setZIndex(vSliceProp_back_0, 100);\n    addSprite(vSliceProp_back_0, BEHIND_ALL);')<0)
   throw 'old back prop lost actor-relative depth';
  if(layered.indexOf('stage.setZIndex(vSliceProp_glow_1, 300);\n    addSprite(vSliceProp_glow_1, BEHIND_BF);')<0)
   throw 'old foreground prop cannot occlude dad while staying behind bf';
  if(layered.indexOf('stage.setZIndex(vSliceProp_front_2, 300);\n    addSprite(vSliceProp_front_2, BEHIND_BF);')<0)
   throw 'second prop cannot preserve foreground order';
  if(layered.indexOf('addSprite(vSliceProp_glow_1, BEHIND_BF);\n    stage.elements.set("vSliceProp_glow_1", vSliceProp_glow_1);')<0)
   throw 'old generated prop was not registered for HXC lookup';
  if(layered.indexOf('addSprite(vSliceProp_solid_3, BEHIND_ALL);\n    stage.elements.set("vSliceProp_solid_3", vSliceProp_solid_3);')<0)
   throw 'hex-color solid prop was not registered for HXC lookup';
  same(layered.split('stage.elements.set("vSliceProp_glow_1", vSliceProp_glow_1);').length,2);
  same(VSliceStageCompat.normalizeGeneratedPropLayers(layered,owner,true),layered);
  // The actual refresh uses insertion sorting with strict greater-than. At
  // equal depth it retains the addSprite order before the actor.
  var members=['back','gf','dad','glow','front','bf'];
  var depths=[100,100,200,300,300,300];
  for(i in 1...members.length) {
   var member=members[i]; var depth=depths[i]; var j=i-1;
   while(j>=0 && depths[j]>depth) { members[j+1]=members[j]; depths[j+1]=depths[j]; j--; }
   members[j+1]=member; depths[j+1]=depth;
  }
  same(members.join(','),'back,gf,dad,glow,front,bf');
  var custom=StringTools.replace(old,'vSliceProp_back_0.frames = FlxAtlasFrames.fromSparrow',
    'vSliceProp_back_0.frames = customAtlas');
  var repairedCustom=VSliceStageCompat.normalizeGeneratedPropHitboxes(custom,owner,true);
  if(repairedCustom.indexOf('vSliceProp_back_0.updateHitbox();')>=0)
   throw 'handwritten prop block was modified';
  if(VSliceStageCompat.normalizeGeneratedPropLayers(repairedCustom,owner,true).indexOf('stage.setZIndex(vSliceProp_back_0,')>=0)
   throw 'handwritten graphic was layered';
  var dynamicScale=StringTools.replace(old,'vSliceProp_back_0.scale.set(4, 4)',
    'vSliceProp_back_0.scale.set(getScale(), 4)');
  var repairedScale=VSliceStageCompat.normalizeGeneratedPropHitboxes(dynamicScale,owner,true);
  if(repairedScale.indexOf('vSliceProp_back_0.updateHitbox();')>=0)
   throw 'computed scale was modified';
  if(VSliceStageCompat.normalizeGeneratedPropLayers(repairedScale,owner,true).indexOf('stage.setZIndex(vSliceProp_back_0,')>=0)
   throw 'computed scale was layered';
  var dynamicScroll=StringTools.replace(old,'vSliceProp_back_0.scrollFactor.set(0.95, 0.95)',
    'vSliceProp_back_0.scrollFactor.set(getScroll(), 0.95)');
  var repairedScroll=VSliceStageCompat.normalizeGeneratedPropHitboxes(dynamicScroll,owner,true);
  if(repairedScroll.indexOf('vSliceProp_back_0.updateHitbox();')>=0)
   throw 'computed scroll was modified';
  if(VSliceStageCompat.normalizeGeneratedPropLayers(repairedScroll,owner,true).indexOf('stage.setZIndex(vSliceProp_back_0,')>=0)
   throw 'computed scroll was layered';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(source)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
