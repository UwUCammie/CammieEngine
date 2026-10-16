"""Section navigation preserves native option indices and hidden settings."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class OptionsCategoriesTest(unittest.TestCase):
    def test_compact_spacing_retains_default_menu_geometry(self):
        source = (ROOT / 'source/Alphabet.hx').read_text()
        start = source.index('\tfunction menuTargetY(')
        target = source[start:source.index('\n\tfunction updateCShapeX(', start)]
        self.run_haxe({'Main.hx': '''class FlxG {public static var height=720;}
class Main {
 var targetY:Float=0;
 var menuRowSpacing:Float=156;
 function new() {}
''' + target + '''
 static function main():Void {
  var row=new Main(); row.targetY=1;
  if(Math.abs(row.menuTargetY(0.48)-501.6)>0.001) throw "ordinary menu spacing changed";
  row.menuRowSpacing=96;
  var previous:Float=0;
  for(index in -2...3) {
   row.targetY=index;
   var position=row.menuTargetY(0.48);
   if(index!=-2 && Math.abs(position-previous-96)>0.001) throw "uneven compact spacing";
   if(index==0 && Math.abs(position-345.6)>0.001) throw "selection lost its centered position";
   previous=position;
  }
 }
}'''})

    def test_sections_scroll_like_options_and_use_menu_sound_packs(self):
        source = (ROOT / 'source/SaveDataState.hx').read_text()
        section_rows = source[source.index('var sectionNames ='):source.index('// Labels over the two columns')]
        self.assertIn('new MenuCard(sectionNames[index], SIDEBAR_WIDTH', section_rows)
        self.assertIn('tab.moveTo(optionsX + SIDEBAR_X, SIDEBAR_TOP + index * (TAB_HEIGHT + TAB_GAP), snap);', source)
        self.assertIn('MenuStyle.stackTop(position,', source)
        self.assertIn('MenuStyle.fitsRegion(cardTop,', source)
        self.assertNotIn('Alphabet', source)
        self.assertNotIn('categoryCursor', source)
        root_nav = source[source.index('} else if (!inOptionCategory) {', source.index('function changeSelection')):]
        self.assertIn("playMenuSound('scroll');", root_nav.split('} else {', 1)[0])
        self.assertIn("playMenuSound('confirm');", source[source.index('function openOptionCategory'):])
        back = source[source.index('if (controls.BACK)'):source.index('if (inOptionsMenu ||')]
        self.assertIn("playMenuSound('cancel');", back)
        start = source.index('\tfunction playMenuSound(')
        sounds = source[start:source.index('\n\tfunction swapMenus(', start)]
        self.run_haxe({'Main.hx': '''class FlxG {
 public static var paths:Array<String>=[];
 public static var sound:Dynamic={play:function(path:String,volume:Float):Void paths.push(path)};
}
class TitleState {public static var soundExt=".ogg";}
class FNFAssets {
 public static function exists(path:String):Bool return path.indexOf("custom_menu_sounds/Default/")>=0;
}
class Main {
 var sfxJson:Dynamic={customMenuScroll:"Default",customMenuConfirm:"Default"};
 function new() {}
''' + sounds + '''
 static function main():Void {
  var menu=new Main();
  menu.playMenuSound("scroll"); menu.playMenuSound("confirm"); menu.playMenuSound("cancel");
  if(FlxG.paths.join("|")!="assets/sounds/custom_menu_sounds/Default/scrollMenu.ogg|"
   +"assets/sounds/custom_menu_sounds/Default/confirmMenu.ogg|assets/sounds/cancelMenu.ogg")
   throw "section navigation missed configured sounds or the missing-cancel fallback";
  menu.sfxJson={customMenuScroll:"Missing"}; menu.playMenuSound("scroll");
  if(FlxG.paths[3]!="assets/sounds/scrollMenu.ogg") throw "missing sound pack did not fall back";
 }
}'''})

    def run_haxe(self, files):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, contents in files.items():
                path = Path(folder) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sections_partition_all_native_rows_and_wrap_by_global_index(self):
        source = (ROOT / 'source/SaveDataState.hx').read_text()
        fields = re.findall(r'intName\s*:\s*[\'"]([^\'"]+)', source)
        self.assertNotIn('allowDonate', fields)
        self.run_haxe({'OptionsCategories.hx': (ROOT / 'source/OptionsCategories.hx').read_text(),
            'Main.hx': '''class Main {
 static function check(ok:Bool,msg:String):Void if(!ok) throw msg;
 static function main():Void {
  var names=OptionsCategories.names();
  check(names.join("|")=="Gameplay|Controls & Timing|Graphics & Performance|Audio|Interface|Compatibility",
   "section names changed");
  names[0]="mutated";
  check(OptionsCategories.names()[0]=="Gameplay","caller mutated shared sections");
  var fields:Array<String>=''' + str(fields).replace("'", '"') + ''';
  var rows:Array<Dynamic>=[for(field in fields) {intName:field}];
  var visited:Array<Int>=[];
  for(name in OptionsCategories.names()) for(index in OptionsCategories.indices(rows,name)) {
   check(visited.indexOf(index)<0,"option belongs to multiple sections");
   visited.push(index);
  }
  check(visited.length==rows.length,"native option was unreachable");
  var controls=OptionsCategories.indices([{intName:"offset"},{intName:"fpsCap"},{intName:"controls"}],
   "Controls & Timing");
  check(controls.join(",")=="0,2","section lost global indices");
  check(OptionsCategories.move(controls,0,-1)==2 && OptionsCategories.move(controls,2,1)==0,
   "selection failed to wrap inside section");
  check(OptionsCategories.move([],0,1)==-1,"empty section invented a selection");
  check(OptionsCategories.sectionFor("future-setting")=="Compatibility","new setting was lost");
 }
}'''.replace('True', 'true').replace('False', 'false')})

    def test_row_filter_shows_only_the_section_and_saving_keeps_hidden_settings(self):
        source = (ROOT / 'source/SaveDataState.hx').read_text()
        start = source.index('\tfunction layoutStack(')
        layout = source[start:source.index('\n\tfunction refreshSaveRows(', start)]
        start = source.index('\tfunction isActionRow(')
        filtering = source[start:source.index('\n\tfunction refreshCategoryRows(', start)]
        start = source.index('\tfunction saveOptions(')
        saving = source[start:source.index('\n\tfunction toggleSelection(', start)]
        self.run_haxe({'MenuStyle.hx': (ROOT / 'source/MenuStyle.hx').read_text(), 'OptionsCategories.hx': (ROOT / 'source/OptionsCategories.hx').read_text(), 'Main.hx': '''class FlxG {
 public static var height=720;
}
class MenuCard {
 public var exists=true; public var selected=false; public var top=0.0; public var shownValue=""; public var shownSwitch:Null<Bool>=null;
 public var idleHeight=44; public var selectedHeight=92; public var opacity=1.0;
 public function new() {}
 public function present(isSelected:Bool, disabled:Bool=false):Void selected=isSelected;
 public function moveTo(x:Float, y:Float, snap:Bool=false):Void top=y;
 public function setValue(text:String, color:Int=0, width:Int=220):Void {shownValue=text; shownSwitch=null;}
 public function setSwitch(on:Bool):Void {shownSwitch=on;}
}
class OptionsHandler {
 public static var options:Dynamic={showFPS:true,showMemory:false,hiddenPalette:"kept",allowDonate:false,
  useSaveDataMenu:false,importType:"Auto",importPath:"retained"};
}
class CodenameOptionsMenuModel {
 public static function copyOptions(options:Dynamic):Dynamic {
  var copy:Dynamic={}; for(field in Reflect.fields(options))
   Reflect.setField(copy,field,Reflect.field(options,field)); return copy;
 }
}
class ImportSettings {
 public static function getSelectedType():String return "Auto";
 public static function getSourcePath():String return "retained";
}
class Main {
 public static var fpsCounter:Dynamic={visible:false};
 public static var memoryCounter:Dynamic={visible:true};
 var optionCards:Array<MenuCard>=[new MenuCard(),new MenuCard(),new MenuCard()];
 var numberDisplays:Array<Dynamic>=[{text:""},{text:""},{text:"60"}];
 static inline var LIST_TOP:Int=100; static inline var LIST_BOTTOM:Int=640; static inline var LIST_GAP:Int=4; static inline var LIST_X:Int=344;
 var categorySelected=1;
 var optionList:Array<Dynamic>=[{intName:"showTimings",value:false,amount:null},{intName:"controls",value:false,amount:null},{intName:"fpsCap",value:true,amount:60.0}];
 var mappedOptions:Dynamic={showMemory:{value:false},fpsCap:{value:true,amount:1501.0}};
 var preferredSave=0;
 var categoryOptions=[0,1];
 var optionsSelected=0;
 var inOptionCategory=false;
 var optionsX=1280.0;
 function new() {}
''' + layout + filtering + saving + '''
 static function check(ok:Bool,msg:String):Void if(!ok) throw msg;
 static function main():Void {
  var state=new Main();
  state.refreshOptionRows();
  check(state.optionCards[0].exists && state.optionCards[1].exists && !state.optionCards[2].exists,
   "the section list did not preview the highlighted section");
  check(!state.optionCards[0].selected && state.optionCards[0].opacity<1,"the preview is not quiet");
  state.inOptionCategory=true;
  state.refreshOptionRows();
  check(state.optionCards[0].exists && state.optionCards[1].exists && !state.optionCards[2].exists,
   "a section showed another section's rows");
  check(state.optionCards[0].selected && !state.optionCards[1].selected && state.optionCards[0].opacity==1,"the selected row is not marked");
  check(state.optionCards[0].shownSwitch==false && state.optionCards[1].shownValue=="OPEN",
   "a switch or an action row was drawn wrongly");
  check(state.optionCards[1].top>state.optionCards[0].top+state.optionCards[0].selectedHeight-1,"rows are not stacked under the selection");
  state.categoryOptions=[2];state.optionsSelected=2;
  state.refreshOptionRows();
  check(state.optionCards[2].exists && state.optionCards[2].shownValue=="60" && !state.optionCards[0].exists,
   "numeric row did not show its value");
  state.saveOptions();
  check(OptionsHandler.options.hiddenPalette=="kept" && !OptionsHandler.options.allowDonate
   && !OptionsHandler.options.useSaveDataMenu,"saving sections reset hidden preferences");
  check(OptionsHandler.options.fpsCap==1501 && !Main.memoryCounter.visible && Main.fpsCounter.visible,
   "saving lost modified values or counter visibility");
 }
}'''})

if __name__ == '__main__':
    unittest.main()
