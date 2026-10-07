"""Live NV option tables, private save selection and source flush boundaries."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class NvModOptionsSessionTest(unittest.TestCase):
    def test_live_callbacks_shared_values_and_authorized_owner_switch(self):
        main = r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main() {
  var a='assets/imported_mods/alpha'; var b='assets/imported_mods/beta';
  var stored:Map<String,Dynamic>=[]; var writes:Array<String>=[];
  function save(root:String):Dynamic return {
   ownerKey:root,
   getField:function(name:String):Dynamic return stored.get(root),
   setField:function(name:String,value:Dynamic):Dynamic {
    writes.push(root); stored.set(root,haxe.Json.parse(haxe.Json.stringify(value))); return value;
   }, flush:function():Void {}
  };
  var options=new NightmareVisionSourceOptions(a,save(a));
  options.bindFamily(function(name) return name=='alpha'?a:name=='beta'?b:null,save,function() return ['global']);
  options.init('alpha');
	 var api=new NightmareVisionModOptionsFacade(options);
  var calls=0;
  var settings:Dynamic={onChange:function():Void calls++,callback:function():Void calls++};
  options.addForMod('foreign','bad','bool',true);
  check(options.get('bad')==null,'unrelated script admission');
  api.add('alpha','quality','bool',true,settings);
  options.addForMod('global','extra','int');
  check(options.list.length==2,'current and enabled globals may register');
	 check(api.currentMod=='alpha' && api.options==options.options && api.list.length==2,'source facade getters share live backend');
  check(options.get('extra').value==0,'numeric default');
  var quality=options.get('quality');
  check(quality.settings.onChange==settings.onChange,'callback retained live');
  quality.settings.callback();
  check(calls==1,'callback executable');
  check(Reflect.field(Reflect.field(stored.get(a),'quality'),'settings').onChange==null,'callback excluded from save');
  var writesBefore=writes.length;
  options.setValue('quality',false);
  check(options.getValue('quality')==false,'live value set');
  check(writes.length==writesBefore,'setValue is not an implicit flush');
  options.addForMod('alpha','quality','bool',true);
  check(options.get('quality')==quality,'duplicate preserves live metadata identity');
  options.init('beta');
  check(writes[writes.length-1]==a,'old nonempty mod flushed on selection change');
  check(options.get('quality')==null && options.ownerRoot==a,'isolated target and immutable lease');
  options.addForMod('beta','quality','bool',true);
  options.setValue('quality',false);
  options.init('alpha');
  check(options.getValue('quality')==false,'first mod value restored');
  check(options.get('quality')!=quality,'init reconstructs options');
  check(options.get('quality').settings.callback==null,'saved callback is not executable after reload');
  var rejected=false;
  try options.init('foreign') catch(error:Dynamic) rejected=true;
  check(rejected && options.currentMod=='alpha','foreign selection preserves current table');
  var replacement=new NightmareVisionSourceOptions(a,save(a));
  check(replacement.getValue('quality')==false,'new owner session loads private values');
  options.release();
  rejected=false; try options.getValue('quality') catch(error:Dynamic) rejected=true;
  check(rejected,'departed view retired');
 }
}'''
        self.run_haxe(main)

    def test_saved_order_repaired_and_failed_init_preserves_source_partial_state(self):
        self.run_haxe(r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main() {
  var root='assets/imported_mods/owner'; var fail=false; var flushes=0;
  var stored:Dynamic={x:{type:'int',value:2,idx:-1,settings:{}},y:{type:'bool',value:true,idx:0,settings:{}}};
  var save:Dynamic={ownerKey:root,getField:function(name:String):Dynamic {if(fail) throw 'read failure';return stored;},
   setField:function(name:String,value:Dynamic):Dynamic {stored=value;return value;},flush:function():Void flushes++};
  var options=new NightmareVisionSourceOptions(root,save);
  options.bindFamily(function(name) return root,function(key) return save,function() return []);
  options.init('first');
  check(options.list[0].idx!=options.list[1].idx,'source validateOrder repairs duplicate/negative order');
  check(options.get('x').settings.description=='No description provided.','option settings defaults');
  var before=flushes;
  fail=true; var rejected=false;
  try options.init('second') catch(error:Dynamic) rejected=true;
  check(rejected && flushes==before+1,'previous mod flushed before read failure');
  check(options.currentMod=='second' && options.list.length==0,'failed init preserves assigned mod and cleared table');
 }
}''')

    def test_failed_family_bind_never_flushes_into_previous_owner(self):
        self.run_haxe(r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main() {
  var a='assets/imported_mods/alpha', b='assets/imported_mods/beta';
  var stored:Map<String,Dynamic>=[]; var fail=true;
  function save(root:String):Dynamic return {ownerKey:root,getField:function(name:String):Dynamic return stored.get(root),
   setField:function(name:String,value:Dynamic):Dynamic {stored.set(root,haxe.Json.parse(haxe.Json.stringify(value)));return value;},flush:function():Void {}};
  var options=new NightmareVisionSourceOptions(a,save(a));
  options.bindFamily(function(name) return name=='alpha'?a:name=='beta'?b:null,
   function(root) return fail && root==b ? save(a) : save(root),function() return []);
  options.init('alpha'); options.addForMod('alpha','original','bool',true);
  var before=haxe.Json.stringify(stored.get(a)); var rejected=false;
  try options.init('beta') catch(error:Dynamic) rejected=true;
  check(rejected && options.currentMod=='beta' && options.list.length==0,'source partial current/table state');
  rejected=false; try options.addForMod('beta','target','bool',true) catch(error:Dynamic) rejected=true;
  check(rejected && haxe.Json.stringify(stored.get(a))==before && !stored.exists(b),'failed bind cannot use old save');
  fail=false; options.flush();
  check(Reflect.field(stored.get(b),'target')!=null && haxe.Json.stringify(stored.get(a))==before,'retry binds only target namespace');
 }
}''')

    def run_haxe(self, main):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            path = FixturePath(temp)
            (path / 'Main.hx').write_text(main, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(path),
                                     '--interp', '-main', 'Main'], cwd=temp, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
