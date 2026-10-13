"""Retained identity adoption and same-instance refresh guards."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class RegistryReconcileTest(unittest.TestCase):
 def test_unique_identity_reorder_promotion_deletion_and_ambiguity(self):
  fixture=r'''class Main {
   static function check(ok:Bool,text:String){if(!ok)throw text;}
   static function main(){
    var retained=FreeplayRegistryReconcile.retained(['native:a','owner-a:source','owner-b:source'],['owner-b:source','native:new','owner-a:source']);
    check(retained.join(',')=='2,-1,1','source identity replaced by position/title');
    check(FreeplayRegistryReconcile.retained(['owner:pending-source'],['owner:pending-source']).join(',')=='0','pending-to-published identity lost');
    check(FreeplayRegistryReconcile.retained(['same','same'],['same']).join(',')=='-1','ambiguous old identity borrowed a row');
    check(FreeplayRegistryReconcile.retained(['same'],['same','same']).join(',')=='-1,-1','ambiguous new identity borrowed a row twice');
    check(FreeplayRegistryReconcile.retained(['','native:a'],['','native:a']).join(',')=='-1,1','unknown identity borrowed a row');
    check(FreeplayRegistryReconcile.retained(['native:a'],[]).length==0,'empty registry retained a removed row');
   }
  }'''
  with tempfile.TemporaryDirectory()as folder:
   Path(folder,'Main.hx').write_text(fixture,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_live_refresh_does_not_replace_audio_cameras_or_state(self):
  from test_freeplay_random_difficulty import extract_method
  source=(ROOT/'source/FreeplayState.hx').read_text(encoding='utf-8')
  refresh=extract_method(source,'function reloadAfterImport(')
  for forbidden in ['loadAndSwitchState','new FreeplayState','playMusic','setupUICamera']:
   self.assertNotIn(forbidden,refresh)
  self.assertLess(refresh.index('Metadata preparation failed'),refresh.index('currentSongList = registry'))
  self.assertLess(refresh.index('restoreRefreshSelection();'),refresh.index('refreshImportAvailability(true);'))
  self.assertIn('nextSongs.push(pendingSongMetadata(candidate))',refresh)
  self.assertIn('rowSongIndices = [for (previous in oldVisible)',refresh)
  self.assertIn('FlxTween.cancelTweensOf(star)',refresh)
  availability=extract_method(source,'function refreshImportAvailability(')
  self.assertNotIn('returnFromEmptySongList()',availability)
  self.assertNotIn('loadAndSwitchState',availability)
  append=extract_method(source,'function appendPendingSong(')
  remove=extract_method(source,'function removeSongAt(')
  self.assertIn('isPixelIcon.push(false)',append)
  self.assertIn('isPixelIcon.splice(index, 1)',remove)
  self.assertIn('previous > index ? previous - 1 : previous',remove)
  stars=extract_method(source,'function refreshRankStarsFor(')
  self.assertIn('star.updateDensity',stars)
  self.assertLess(stars.index('if (same)'),stars.index('star.destroy()'))

 def test_refresh_relocates_hidden_selection_without_scroll_sound(self):
  from test_freeplay_random_difficulty import extract_method
  source=(ROOT/'source/FreeplayState.hx').read_text(encoding='utf-8')
  filter_method=extract_method(source,'function applySearchFilter(')
  change=extract_method(source,'function changeSelection(')
  start=change.index('if (!refreshOnly)\n\t\t\tcurSelected =')
  end=change.index(';',start)+1
  selection=change[start:end]
  fixture=r'''class Browser {
   public var curSelected=0;
   var searchFocused=false;var searchInput:Dynamic=null;var searchString='visible';var soundTest=false;var libraryViewId='';var favoritesOnly=false;var categoryFilters:Array<String>=[];
   var denseBrowser=true;var songs=[0,1];
   var searchText:Dynamic={text:'',alpha:1.0};var scoreText:Dynamic={visible:false};var diffText:Dynamic={text:''};var infoPanel:Dynamic={visible:true};var previewTimer=0.0;
   public var sounds=0;public var changes=0;public var layouts=0;
   public function new(){}
   function songMatches(index:Int):Bool return index==1;
   function anyVisible():Bool return true;
   function orderedVisibleSongs():Array<Int> return [1];
   function nextVisibleSelection(current:Int,change:Int,count:Int,matches:Int->Bool):Int return 1;
   function changeSelection(change:Int=0,refreshOnly:Bool=false):Void {
    if(!refreshOnly)sounds++;
    SELECTION
   }
   function rebuildVisibleRows():Void layouts++;
   function rebuildIconQueue():Void {}
   function updateBrowserDetails():Void{}
   function changeDiff():Void changes++;
   function stopPreviewSound():Void{}
   FILTER
   public function apply(refresh:Bool):Void applySearchFilter(refresh);
  }
  class Main {
   static function main(){
    var browser=new Browser();browser.apply(true);
    if(browser.curSelected!=1)throw 'Refreshed hidden selection was not relocated to a matching row';
    if(browser.sounds!=0)throw 'Live metadata refresh played scroll audio';
    browser.apply(true);if(browser.curSelected!=1||browser.sounds!=0)throw 'Unchanged matching selection reset';
    var typed=new Browser();typed.apply(false);if(typed.curSelected!=1||typed.sounds!=1)throw 'Ordinary search selection no longer works';
   }
  }'''.replace('SELECTION',selection).replace('FILTER',filter_method)
  with tempfile.TemporaryDirectory()as folder:
   Path(folder,'Main.hx').write_text(fixture,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
