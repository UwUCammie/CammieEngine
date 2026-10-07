"""Execute full pinned Psych Alphabet and AttachedText against typed adapters."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from source_alphabet_fixture_support import alphabet_fixture_files

ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import DonorAlphabet.DonorAlphaCharacter;import PsychSourceAlphabet.PsychSourceAlphabetAlignment;
import flixel.FlxSprite;
class Main {
 static function ok(b:Bool,m:String)if(!b)throw m;
 static function snapshot(s:Dynamic):String {
  var r:Array<Dynamic>=[s.x,s.y,s.rows,s.scale.x,s.scale.y,s.letters.length];
  for(l in (s.letters:Array<Dynamic>))r.push([l.x,l.y,l.width,l.height,l.offset.x,l.offset.y,l.scale.x,l.scale.y,l.row,l.rowWidth,l.alignOffset,l.letterOffset,l.character,l.animation.name,l.exists,l.alive]);
  return haxe.Json.stringify(r);
 }
 static function main(){
  var untouched=new AlphabetIO();var uninitialized=new PsychAlphabetContext(untouched.owner());
  var empty=new PsychSourceAlphabet(0,0,'',true,uninitialized);ok(uninitialized.allLetters==null && untouched.log.length==0,'empty constructor does not bootstrap metadata');empty.destroy();
  var seed=new PsychSourceAlphaCharacter(uninitialized);ok(uninitialized.allLetters==null && untouched.log.join('|')=='atlas:alphabet','glyph constructor only loads atlas');seed.destroy();
  for(bold in [false,true])for(text in ['','aB c','a\nb1','a\\nb_?','abc abc abc','???',' a   b ','a\n\nb']) {
   var a=new AlphabetIO();var b=new AlphabetIO();Paths.io=a;DonorAlphaCharacter.loadAlphabetData();
   var context=new PsychAlphabetContext(b.owner());context.initialize();
   var d=new DonorAlphabet(15,27,text,bold);var h=new PsychSourceAlphabet(15,27,text,bold,context);
   ok(snapshot(d)==snapshot(h),'initial '+text);
   Sys.println('ALPHABET_RESULT|'+snapshot(h));
   d.compareScale(new flixel.math.FlxPoint(1.3,.7));h.compareScale(new flixel.math.FlxPoint(1.3,.7));ok(snapshot(d)==snapshot(h),'actual parent scale transform');
   for(alignment in ['left','centered','right',' nonsense ']){d.setAlignmentFromString(alignment);h.setAlignmentFromString(alignment);ok(snapshot(d)==snapshot(h),'alignment');}
   d.setScale(.7,1.3);h.setScale(.7,1.3);ok(snapshot(d)==snapshot(h),'independent scale');
   d.scaleX=1.2;h.scaleX=1.2;d.scaleY=.8;h.scaleY=.8;ok(snapshot(d)==snapshot(h),'scale properties');
   Sys.println('ALPHABET_RESULT|'+snapshot(h));
   var old=h.letters.copy();var donorOld=d.letters.copy();d.text='cA';h.text='cA';ok(snapshot(d)==snapshot(h),'text reload');
   Sys.println('ALPHABET_RESULT|'+snapshot(h));
   for(l in old)ok(!l.exists && l.destroyed==0 && h.members.indexOf(l)<0,'removed glyph stays killed not destroyed');
   for(l in donorOld)ok(!l.exists && l.destroyed==0 && d.members.indexOf(l)<0,'donor old glyph lifetime');
   d.isMenuItem=h.isMenuItem=true;d.targetY=h.targetY=2;d.changeX=h.changeX=false;d.update(.03);h.update(.03);ok(snapshot(d)==snapshot(h),'menu update');
   d.changeX=h.changeX=true;d.snapToPosition();h.snapToPosition();ok(snapshot(d)==snapshot(h),'menu snap');
   d.clearLetters();h.clearLetters();ok(snapshot(d)==snapshot(h),'clear rows');d.destroy();h.destroy();
  }
  var io=new AlphabetIO();Paths.io=io;DonorAlphaCharacter.loadAlphabetData();
  var context=new PsychAlphabetContext(io.owner());context.initialize();
  var poolD=new DonorAlphabet(11,23,'');var poolH=new PsychSourceAlphabet(11,23,'',true,context);
  var deadD=new DonorAlphaCharacter();var deadH=new PsychSourceAlphaCharacter(context);poolD.add(deadD);poolH.add(deadH);deadD.kill();deadH.kill();
  poolD.text='a';poolH.text='a';ok(poolD.letters[0]==deadD && poolH.letters[0]==deadH && snapshot(poolD)==snapshot(poolH),'real member recycle revive and final preAdd');poolD.destroy();poolH.destroy();
  var dg=new DonorAlphaCharacter();var hg=new PsychSourceAlphaCharacter(context);
  for(value in ['a','b','A','unknown'])for(bold in [true,false]){
   dg.setupAlphaCharacter(12.5,17.25,value,bold);hg.setupAlphaCharacter(12.5,17.25,value,bold);
   ok(dg.animation.name==hg.animation.name && dg.offset.x==hg.offset.x && dg.offset.y==hg.offset.y && dg.letterOffset.join(',')==hg.letterOffset.join(','),'direct glyph setup and persistent offsets');
  }
  var de='';var he='';try dg.image='replacement'catch(e:Dynamic)de=Std.string(e);try hg.image='replacement'catch(e:Dynamic)he=Std.string(e);
  ok(de!='' && he!='' && dg.image==hg.image,'standalone reload parent error and partial state');dg.destroy();hg.destroy();
  var d=new DonorAttachedText('ab',3,-7,false,.8);var h=new PsychSourceAttachedText('ab',3,-7,false,.8,context);
  var tracker=new FlxSprite(91,74);tracker.alpha=.4;tracker.visible=false;d.sprTracker=h.sprTracker=tracker;d.copyAlpha=h.copyAlpha=true;
  d.update(.1);h.update(.1);ok(snapshot(d)==snapshot(h)&&h.alpha==d.alpha&&h.visible==d.visible,'attached pre-super');
  var dt=new FlxSprite(10,20);var ht=new FlxSprite(10,20);d.sprTracker=dt;h.sprTracker=ht;
  d.letters[0].onUpdate=function(){dt.x=99;};h.letters[0].onUpdate=function(){ht.x=99;};
  d.update(.1);h.update(.1);ok(snapshot(d)==snapshot(h) && h.x==13 && ht.x==99,'AttachedText tracks before parent child callbacks');
  d.destroy();h.destroy();ok(tracker.destroyed==0,'text tracker borrowed');
  var first=context.allLetters;var loader=context.loadAlphabetData;context.allLetters=null;context.rebindOwner(new AlphabetIO().owner());context.initialize();ok(context.allLetters==null && loader==context.loadAlphabetData,'rebind does not reload authored null');
  context.loadAlphabetData('missing');ok(context.allLetters!=first && first.exists('a'),'metadata replacement preserves old map');
  var held=context.allLetters;context.release();ok(held==context.allLetters,'release preserves metadata references');var error='';try context.loadAlphabetData()catch(e:Dynamic)error=Std.string(e);ok(error.indexOf('released')>=0,'released IO diagnostic');
  var fresh=new AlphabetIO();fresh.fail=true;var c=new PsychAlphabetContext(fresh.owner());c.initialize();ok(c.allLetters.exists('?') && !c.allLetters.exists('a'),'failed metadata question fallback');
  var dc=new AlphabetIO();dc.fail=true;Paths.io=dc;DonorAlphaCharacter.loadAlphabetData();ok(haxe.Json.stringify(c.allLetters)==haxe.Json.stringify(DonorAlphaCharacter.allLetters),'actual donor failed loader');
  var a=new AlphabetIO();var b=new AlphabetIO();b.data='{"allowed":"z","characters":{}}';var ca=new PsychAlphabetContext(a.owner());var cb=new PsychAlphabetContext(b.owner());ca.initialize();cb.initialize();ok(ca.allLetters.exists('a')&&!cb.allLetters.exists('a')&&cb.allLetters.exists('z'),'distinct owner metadata');
  var glyph=new PsychSourceAlphaCharacter(ca);Reflect.callMethod(PsychSourceAlphaCharacter,Reflect.field(PsychSourceAlphaCharacter,'loadAlphabetData'),['alphabet',ca]);ok(Reflect.hasField(PsychSourceAlphaCharacter,'allLetters'),'actual static schema');
  ok(PsychSourceAlphaCharacter.isTypeAlphabet('é')==DonorAlphaCharacter.isTypeAlphabet('é'),'unicode classifier');glyph.destroy();
  for(mask in 0...4){
   var loaded:Array<String>=[];
   SourceAlphabetAssets.atlas(function(p){return (StringTools.endsWith(p,'.png')?(mask&1)!=0:(mask&2)!=0)?'owned/'+p:null;},function(image,xml){loaded=[image,xml];return new flixel.graphics.frames.FlxAtlasFrames();});
   ok(loaded[0]==((mask&1)!=0?'owned/images/alphabet.png':'assets/images/source_compat/psych/alphabet.png'),'independent image fallback');
   ok(loaded[1]==((mask&2)!=0?'owned/images/alphabet.xml':'assets/images/source_compat/psych/alphabet.xml'),'independent XML fallback');
   DonorPathsAtlas.mask=mask;DonorPathsAtlas.getSparrowAtlas('alphabet');ok(loaded.join('|')==flixel.graphics.frames.FlxAtlasFrames.lastLoad.join('|'),'actual donor independent image XML selection');
  }
  ok(SourceAlphabetAssets.stockPath('images/custom.json')==null && SourceAlphabetAssets.stockPath('images/alphabet.json')!=null,'narrow JSON fallback');
 }
}
'''

class SourceAlphabetContractTest(unittest.TestCase):
    def test_full_donor_classes_eval_and_cpp(self):
        import json
        receipt = json.loads((ROOT / 'tmp/upstream-flixel-5.6.1/source-receipt.json').read_text())
        for row in receipt['files']:
            self.assertEqual(hashlib.sha256((ROOT / 'tmp/upstream-flixel-5.6.1' / row['path']).read_bytes()).hexdigest(), row['sha256'])
        outputs = [self.run_donor_fixture(version) for version in ['6.1.2', '5.6.1']]
        self.assertTrue(outputs[0])
        self.assertEqual(outputs[0], outputs[1], 'Pinned parent methods differ for the exercised glyph/group behavior')

    def run_donor_fixture(self, version):
        files = alphabet_fixture_files(version)
        files['Main.hx'] = MAIN
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-7000:])
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*command, '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-6000:])
            generated=(temp/'cpp/src/PsychSourceAlphaCharacter.cpp').read_text()
            for field in ['allLetters','loadAlphabetData','isTypeAlphabet','image','setupAlphaCharacter']:
                self.assertIn(f'HX_FIELD_EQ(inName,"{field}")', generated)
            return [line for line in result.stdout.splitlines() if line.startswith('ALPHABET_RESULT|')]

    def test_exact_stock_assets_and_narrow_fallback(self):
        for extension in ['png', 'xml', 'json']:
            donor=ROOT.parent/'fnf_sources/FNF-PsychEngine/assets/shared/images'/f'alphabet.{extension}'
            host=ROOT/'assets/images/source_compat/psych'/f'alphabet.{extension}'
            self.assertEqual(host.read_bytes(), donor.read_bytes())
