"""Compare actual attachment classes against complete pinned source classes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from source_attachment_fixture_support import attachment_fixture_files

ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import flixel.FlxSprite;import flixel.FlxObject;import flixel.util.FlxAxes;
import DonorNVAttachedNode.DonorNVAttachedSprite;
class Main {
 static function ok(v:Bool,m:String)if(!v)throw m;
 static function snap(s:FlxObject):String return ([s.x,s.y,s.angle,s.visible,s.scrollFactor.x,s.scrollFactor.y,Std.isOfType(s,FlxSprite)?(cast s:FlxSprite).alpha:0]:Array<Dynamic>).join(',');
 static function main(){
  for(c in 0...5){
   var a=new AttachmentContext();var b=new AttachmentContext();a.aa=b.aa=c%2==0;
   var file=c==0?null:'owned';var anim=c>=2?'idle':null;var folder=c==3?'shared':null;
   if(c==4)file=null;
   Paths.ctx=a;var d=new DonorPsychAttachedSprite(file,anim,folder,c==3);
   var h=new PsychSourceAttachedSprite(file,anim,folder,c==3,b.owner());
   ok(a.log.join('|')==b.log.join('|'),'owner forwarding '+c);
   ok(d.antialiasing==h.antialiasing && snap(d)==snap(h),'constructor '+c);
   if(anim!=null)ok(d.animation.curAnim.frames.join(',')==h.animation.curAnim.frames.join(',') && d.animation.curAnim.frameDuration==h.animation.curAnim.frameDuration && d.animation.curAnim.looped==h.animation.curAnim.looped,'prefix animation');
   for(flags in 0...8){
    var t=new FlxSprite(19.25,-31.5);t.angle=37;t.alpha=.75;t.visible=false;t.scrollFactor.set(.3,.7);
    for(s in [(cast d:Dynamic),(cast h:Dynamic)]){s.sprTracker=t;s.xAdd=8.5;s.yAdd=-4.25;s.angleAdd=-9;s.alphaMult=2;s.copyAngle=(flags&1)!=0;s.copyAlpha=(flags&2)!=0;s.copyVisible=(flags&4)!=0;}
    d.update(.01);h.update(.01);ok(snap(d)==snap(h),'Psych flags '+flags);
   }
   d.sprTracker=null;h.sprTracker=null;d.update(.01);h.update(.01);ok(snap(d)==snap(h),'null Psych tracker');
   var t=new FlxSprite(90,70);d.onUpdate=function()d.sprTracker=t;h.onUpdate=function()h.sprTracker=t;
   d.update(.01);h.update(.01);ok(snap(d)==snap(h) && h.x==98.5,'super callback before tracking');
   d.destroy();h.destroy();ok(t.destroyed==0,'Psych tracker borrowed');
  }
  for(animated in [false,true]) {
   var a=new AttachmentContext();var b=new AttachmentContext();a.fail=b.fail=true;Paths.ctx=a;
   var donorError='';var hostError='';
   try new DonorPsychAttachedSprite('broken',animated?'idle':null,'library') catch(e:Dynamic)donorError=Std.string(e);
   try new PsychSourceAttachedSprite('broken',animated?'idle':null,'library',false,b.owner()) catch(e:Dynamic)hostError=Std.string(e);
   ok(donorError=='load-failed' && hostError==donorError && a.log.join('|')==b.log.join('|'),'constructor failure ordering');
  }
  for(spriteRoot in [false,true])for(spriteTracked in [false,true])for(axis in [FlxAxes.X,FlxAxes.Y,FlxAxes.XY,FlxAxes.NONE])for(flags in 0...8){
   var dr:FlxObject=spriteRoot?new FlxSprite():new FlxObject();var hr:FlxObject=spriteRoot?new FlxSprite():new FlxObject();
   var t:FlxObject=spriteTracked?new FlxSprite(25.5,48.25):new FlxObject(25.5,48.25);t.angle=62;t.visible=false;t.scrollFactor.set(.2,.4);
   if(spriteTracked)(cast t:FlxSprite).alpha=.7;
   var d=new DonorNVAttachedNode(dr,t);var h=new NightmareVisionAttachedNode(hr,t);
   for(n in [(cast d:Dynamic),(cast h:Dynamic)]){n.copyAxis=axis;n.positionOffset.set(-4.5,2.75);n.angleOffset=13;n.alphaMultiplier=.5;n.copyAngle=(flags&1)!=0;n.copyAlpha=(flags&2)!=0;n.copyVisibility=(flags&4)!=0;}
   d.update(.1);h.update(.1);ok(snap(dr)==snap(hr),'NV axes flags types');
   ok(hr.scrollFactor.x==1,'NV does not copy scrollFactor');
   d.tracked=null;h.tracked=null;d.update(.1);h.update(.1);ok(snap(dr)==snap(hr),'null node tracker');
   d.root=null;h.root=null;d.tracked=t;h.tracked=t;d.update(.1);h.update(.1);
   var dp=d.positionOffset;var hp=h.positionOffset;d.destroy();h.destroy();ok(dp.puts==1 && hp.puts==1 && t.destroyed==0 && hr.destroyed==0,'node borrowed lifetime');
  }
  var t=new FlxSprite(9,12);var d=new DonorNVAttachedSprite(t);var h=new NightmareVisionAttachedSprite(t);
  d.attachedNode.positionOffset.set(5,6);h.attachedNode.positionOffset.set(5,6);
  var next=new FlxSprite(99,100);d.onUpdate=function()d.attachedNode.tracked=next;h.onUpdate=function()h.attachedNode.tracked=next;
  d.update(.1);h.update(.1);ok(snap(d)==snap(h) && h.x==104 && h.updates==1 && h.attachedNode.updates==1,'wrapper order once');
  var point=h.attachedNode.positionOffset;h.destroy();d.destroy();ok(point.puts==1 && h.attachedNode.destroyed==1 && next.destroyed==0,'wrapper owns node only');
  var empty=new NightmareVisionAttachedSprite();empty.update(0);empty.destroy();
  var oldRoot=new FlxSprite();var replacement=new FlxSprite();var tracked=new FlxSprite(51,64);
  var donorNode=new DonorNVAttachedNode(oldRoot,tracked);var hostNode=new NightmareVisionAttachedNode(oldRoot,tracked);
  donorNode.onUpdate=function()donorNode.root=replacement;hostNode.onUpdate=function()hostNode.root=replacement;
  donorNode.update(0);hostNode.update(0);ok(replacement.x==51 && oldRoot.x==0,'node live root after super');
  donorNode.destroy();hostNode.destroy();ok(oldRoot.destroyed==0 && replacement.destroyed==0 && tracked.destroyed==0,'replaced root remains borrowed');
  var n=new NightmareVisionAttachedNode(new FlxObject(),new FlxObject());
  Reflect.setProperty(n,'copyAxis',FlxAxes.X);Reflect.setProperty(n,'tracked',new FlxSprite(71,93));Reflect.callMethod(n,Reflect.field(n,'update'),[0]);ok(n.root.x==71 && n.root.y==0,'reflected getters and methods');n.destroy();
 }
}
'''

class SourceAttachmentContractTest(unittest.TestCase):
    def test_complete_donor_attachment_classes(self):
        files = attachment_fixture_files()
        files['Main.hx'] = MAIN
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-6000:])
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*command, '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-6000:])
            for name, fields in [('NightmareVisionAttachedNode',['root','tracked','copyAxis','positionOffset']),('NightmareVisionAttachedSprite',['attachedNode']),('PsychSourceAttachedSprite',['sprTracker','xAdd','alphaMult'])]:
                generated=(temp/'cpp/src'/f'{name}.cpp').read_text()
                for field in fields:self.assertIn(f'HX_FIELD_EQ(inName,"{field}")', generated)
