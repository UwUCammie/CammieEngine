"""Full immutable NV Alphabet and actual atlas geometry versus typed classes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_alphabet_fixture_support import nv_alphabet_fixture_files

ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import DonorNVAlphabet.DonorNVAlphaCharacter;import flixel.util.FlxAxes;import flixel.util.FlxTimer;
class Main {
 static function ok(b:Bool,m:String)if(!b)throw m;
 static function snapshot(s:Dynamic):String {
  var r:Array<Dynamic>=[s.x,s.y,s.text,s.textSize,s.isBold,s.finishedText,s.curRow,s.lettersArray.length];
  for(l in (Reflect.getProperty(s,"members"):Array<flixel.FlxSprite>))if(l!=null)r.push([l.x,l.y,l.width,l.height,l.frameWidth,l.frameHeight,l.offset.x,l.offset.y,l.scale.x,l.scale.y,Reflect.field(l,'row'),l.animation.name,l.animation.curAnim==null?null:l.animation.curAnim.frames,l.exists,l.alive,l.destroyed]);
  return haxe.Json.stringify(r);
 }
 static function main(){
  for(bold in [false,true])for(size in [.6,1.,1.3,0.,-1.])for(value in ['', 'aB 1', 'a_ b', '(?).!-', 'a\\nb', 'abc abc abc', 'unknowné']){
   var a=new NvAlphabetIO();var b=new NvAlphabetIO();Paths.io=a;var ctx=new NightmareVisionAlphabetContext(b.owner());
   var d=new DonorNVAlphabet(13,29,value,bold,size);var h=new NightmareVisionAlphabet(13,29,value,bold,size,ctx);
   ok(snapshot(d)==snapshot(h) && a.loads==b.loads,'constructor actual atlas '+value+':'+size);
   ok(h.finishedText==(value==''),'nonempty immediate construction leaves finished false');
   var first=h.members.copy();var dfirst=d.members.copy();var count=h.lettersArray.length;
   d.text='plain-only';h.text='plain-only';d.delay=h.delay=0;d.paused=h.paused=true;d.update(10);h.update(10);
   ok(snapshot(d)==snapshot(h) && h.lettersArray.length==count,'plain text/delay/paused do not rebuild or schedule');
   d.changeText(value);h.changeText(value);ok(snapshot(d)==snapshot(h),'changeText');
   for(g in first)if(g!=null)ok(g.destroyed==1,'source owned immediate glyph destroyed');
   for(g in dfirst)if(g!=null)ok(g.destroyed==1,'donor owned immediate glyph destroyed');
   var td=new FlxTimer();var th=new FlxTimer();td.loops=th.loops=value.length;
   var prior=h.lettersArray.length;
   for(i in 0...value.length+2){d.timerCheck(td);h.timerCheck(th);ok(snapshot(d)==snapshot(h) && td.loops==th.loops,'manual cursor '+value+':'+i);}
   ok(h.lettersArray.length==prior,'timerCheck children are not appended to public array');
   var revealed=[for(g in h.members)if(g!=null && h.lettersArray.indexOf(cast g)<0)g];
   d.changeText('b');h.changeText('b');ok(snapshot(d)==snapshot(h),'rebuild retains revealed children');
   for(g in revealed)ok(h.members.indexOf(g)>=0 && g.destroyed==0,'manual child remains group-owned');
   d.destroy();h.destroy();ok(th.destroyed==0 && td.destroyed==0,'passed timer borrowed');
   for(g in revealed)ok(g.destroyed==1,'group teardown owns retained revealed children');
  }
  var a=new NvAlphabetIO();var b=new NvAlphabetIO();Paths.io=a;var ctx=new NightmareVisionAlphabetContext(b.owner());
  var d=new DonorNVAlphabet(0,0,'abc abc abc',false);var h=new NightmareVisionAlphabet(0,0,'abc abc abc',false,1,ctx);
  flixel.FlxG.width=120;var td=new FlxTimer();var th=new FlxTimer();td.loops=th.loops=20;
  for(i in 0...15){d.timerCheck(td);h.timerCheck(th);ok(snapshot(d)==snapshot(h)&&td.loops==th.loops,'automatic break arithmetic');}
  flixel.FlxG.width=1280;
  for(axis in [FlxAxes.X,FlxAxes.Y,FlxAxes.XY,FlxAxes.NONE])for(force in [Math.NEGATIVE_INFINITY,75.25]){
   d.changeAxis=h.changeAxis=axis;d.forceX=h.forceX=force;d.isMenuItem=h.isMenuItem=true;d.targetY=h.targetY=-2.5;d.yMult=h.yMult=81;d.xAdd=h.xAdd=7;d.yAdd=h.yAdd=-13;
   d.update(.031);h.update(.031);ok(snapshot(d)==snapshot(h),'menu axes/force');d.snapToTarget();h.snapToTarget();ok(snapshot(d)==snapshot(h),'snap disregards axes');
  }
  for(size in [.7,1.,0.])for(symbol in ['a','A','1','(',')','.',"'",'-','?','!','#',',']){
   var dg=new DonorNVAlphaCharacter(4,9,size);var hg=new NightmareVisionAlphaCharacter(4,9,size,ctx);
   for(method in ['createBoldLetter','createBoldNumber','createBoldSymbol','createLetter','createNumber','createSymbol']){
    Reflect.callMethod(dg,Reflect.field(dg,method),[symbol]);Reflect.callMethod(hg,Reflect.field(hg,method),[symbol]);
    ok(haxe.Json.stringify([dg.x,dg.y,dg.width,dg.height,dg.offset.x,dg.offset.y,dg.animation.name,dg.frameWidth,dg.frameHeight])==haxe.Json.stringify([hg.x,hg.y,hg.width,hg.height,hg.offset.x,hg.offset.y,hg.animation.name,hg.frameWidth,hg.frameHeight]),'direct glyph source method '+method);
   }
   dg.destroy();hg.destroy();
  }
  NightmareVisionAlphaCharacter.alphabet='global-poison';NightmareVisionAlphaCharacter.numbers='!';NightmareVisionAlphaCharacter.symbols='z';
  var clean=new NightmareVisionAlphabetContext(b.owner());ok(clean.alphabet=='abcdefghijklmnopqrstuvwxyz'&&clean.numbers=='1234567890'&&clean.symbols=="!#$%&'()*+,-.:;<=>?@[]^_|~",'context literal defaults isolated from global statics');
  ctx.alphabet='z';ctx.numbers='';ctx.symbols='';DonorNVAlphaCharacter.alphabet='z';DonorNVAlphaCharacter.numbers='';DonorNVAlphaCharacter.symbols='';
  d.changeText('az');h.changeText('az');ok(snapshot(d)==snapshot(h),'mutable context charsets');
  var held=ctx.alphabet;var old=b.loads;var next=new NvAlphabetIO();ctx.rebindOwner(next.owner());var g=new NightmareVisionAlphaCharacter(0,0,1,ctx);ok(ctx.alphabet==held&&b.loads==old&&next.loads==1,'rebind preserves strings and changes atlas IO');g.destroy();ctx.release();ok(ctx.alphabet==held,'release preserves charsets');var error='';try new NightmareVisionAlphaCharacter(0,0,1,ctx)catch(e:Dynamic)error=Std.string(e);ok(error.indexOf('released')>=0,'released IO diagnostic');
  var fail=new NvAlphabetIO();fail.fail=true;Paths.io=fail;var failedContext=new NightmareVisionAlphabetContext(fail.owner());var de='';var he='';try new DonorNVAlphabet(0,0,'z')catch(e:Dynamic)de=Std.string(e);try new NightmareVisionAlphabet(0,0,'z',false,1,failedContext)catch(e:Dynamic)he=Std.string(e);ok(de=='missing-atlas'&&he==de,'native atlas failure propagates');
  var valid=new NvAlphabetIO();Paths.io=valid;var validContext=new NightmareVisionAlphabetContext(valid.owner());
  var dn=new DonorNVAlphabet(0,0,'');var hn=new NightmareVisionAlphabet(0,0,'',false,1,validContext);dn.timerCheck();hn.timerCheck();ok(snapshot(dn)==snapshot(hn),'null timer and empty cursor');
  de='';he='';try dn.changeText(null)catch(e:Dynamic)de=Std.string(e);try hn.changeText(null)catch(e:Dynamic)he=Std.string(e);ok(de!=''&&he!=''&&snapshot(dn)==snapshot(hn),'null text error preserves matching partial state');dn.destroy();hn.destroy();
  var charsetOwner=new NightmareVisionAlphabetContext(valid.owner());charsetOwner.symbols=null;DonorNVAlphaCharacter.symbols=null;de='';he='';try new DonorNVAlphabet(0,0,'z')catch(e:Dynamic)de=Std.string(e);try new NightmareVisionAlphabet(0,0,'z',false,1,charsetOwner)catch(e:Dynamic)he=Std.string(e);ok(de!=''&&he!=''&&charsetOwner.symbols==null,'authored null charset is not repaired');
  d.destroy();h.destroy();
 }
}
'''

class NightmareVisionAlphabetContractTest(unittest.TestCase):
    def test_full_donor_classes_actual_atlas_eval_and_cpp(self):
        files = nv_alphabet_fixture_files()
        files['Main.hx'] = MAIN
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-7000:])
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*command, '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-7000:])
            for name, fields in [('NightmareVisionAlphaCharacter',['alphabet','numbers','symbols','createBoldLetter','createSymbol']),('NightmareVisionAlphabet',['text','lettersArray','timerCheck','changeText','snapToTarget'])]:
                generated=(temp/'cpp/src'/f'{name}.cpp').read_text(encoding='utf-8')
                for field in fields:self.assertIn(f'HX_FIELD_EQ(inName,"{field}")', generated)
