package;
import flixel.FlxG;
/** Muted, private-save verification using the actual held keyboard controls. */
@:access(FreeplayState)
@:access(MainMenuState)
@:access(LibraryMenuSubState)
@:access(RuntimeSmokeHarness)
@:access(ImportRefreshManager)
class RuntimeFreeplayScrollProbe {
 public static var active(default,null):Bool = false;
 static var phase:Int = 0;
 static var at:Float = 0;
 static var start:Int = 0;
 static var order:Array<Int>;
 static var captureName:String = '';
 static var release:Int = 0;
 static var normal:Int = 0;
 static var accelerated:Int = 0;
 static var holdingFastTest:Bool = false;
 static var sawPositionTween:Bool = false;
 static var sawCardTween:Bool = false;
 static var capturedTransition:Bool = false;
 static var captureDelay:Float = 0.5;
 static var registryBytes:haxe.io.Bytes;
 static var registryPath:String;
 static var liveState:FreeplayState;
 static var liveRow:Dynamic;
 static var liveIcon:Dynamic;
 static var liveStar:Dynamic;
 static var liveCamera:Dynamic;
 static var liveMusic:Dynamic;
 static var liveKey:String;
 static var liveIndex:Int;
 static var liveDifficulty:String;
 static var liveSearch:String;
 static var liveSave:String;
 static function restoreRegistry():Void {
  #if sys
  if(registryBytes!=null) { sys.io.File.saveBytes(registryPath,registryBytes); registryBytes=null; ImportRefreshManager.generation++; }
  #end
 }
 static function check(ok:Bool, text:String):Void { if (!ok) throw text; }
 public static function install():Void {
  #if sys
  if (!RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--verify-freeplay-scroll') < 0) return;
  if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'Scroll probe requires a private save';
  active = true; FlxG.signals.postUpdate.add(update); FlxG.signals.postDraw.add(capture);
  #end
 }
 static function key(code:Int, down:Bool):Void {
  FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN : openfl.events.KeyboardEvent.KEY_UP,true,false,code,code));
 }
 static function tap(code:Int):Void { key(code,true); release=code; }
 static function next():Void { phase++; at=haxe.Timer.stamp(); }
 static function menu():FreeplayState { check(Std.isOfType(FlxG.state,FreeplayState),'Expected chart browser, phase '+phase); return cast FlxG.state; }
 static function steps():Int { var current=order.indexOf(FreeplayState.curSelected); return (current-start+order.length)%order.length; }
 static function update():Void {
  if (!active || RuntimeSmokeHarness.finished) return;
  FlxG.sound.muted=true;
  if(release!=0) { key(release,false); release=0; }
  if(captureName!='')return;
  var dt=haxe.Timer.stamp()-at;
  try switch(phase) {
   case 0:
    if(!Std.isOfType(FlxG.state,FreeplayState))return;
    if(ImportRefreshManager.browseTick().busy)return;
    check(menu().denseBrowser,'Host browser absent'); tap(27);next();
   case 1:
    if(!Std.isOfType(FlxG.state,MainMenuState))return;
    var main:MainMenuState=cast FlxG.state;
    MainMenuState.curSelected=main.optionShit.indexOf('freeplay');check(MainMenuState.curSelected>=0,'Freeplay menu item absent');tap(13);next();
   case 2:
    if(!Std.isOfType(FlxG.state,FreeplayState)) { check(!Std.isOfType(FlxG.state,CategoryState),'Main routed through redundant category chooser');return; }
    if(dt<1)return;
    var m=menu();order=m.orderedVisibleSongs();check(order.length>60,'Probe requires broad song list');
    FreeplayState.curSelected=order[30];m.changeSelection(0,true);start=30;key(40,true);next();
   case 3:
    var row:FreeplayBrowserRow=cast menu().songRows[FreeplayState.curSelected];
    if(row!=null && row.motion.focus>0 && row.motion.focus<1) {
     sawCardTween=true;
     if(Math.abs(row.y-row.motion.targetY)>0.1)sawPositionTween=true;
     if(!capturedTransition) { capturedTransition=true; captureDelay=0; captureName='card-transition'; }
    }
    if(dt<0.18)return;
    check(steps()==1,'Hold repeated before initial delay');
    check(sawPositionTween&&sawCardTween,'Position or selected-card transition snapped');next();
   case 4:
    if(dt<1.82)return;
    normal=steps();key(40,false);check(normal>=17&&normal<=20,'Normal hold count '+normal);
    RuntimeSmokeHarness.emit('scroll_hold',{normal:normal,seconds:2});next();
   case 5:
    if(dt<0.7)return;
    var m=menu(); var pos=m.rowSongIndices.indexOf(FreeplayState.curSelected);var row=m.songRows[FreeplayState.curSelected];
    check(Math.abs(row.y+(cast row:FreeplayBrowserRow).motion.height/2-FlxG.height/2)<0.05,'Selection did not settle to center');
    captureName='centered';start=order.indexOf(FreeplayState.curSelected);next();
   case 6:
    if(!holdingFastTest) { key(40,true); holdingFastTest=true; at=haxe.Timer.stamp(); return; }
    if(dt<0.6)return;key(16,true);next();
   case 7:
    if(dt<1)return;accelerated=steps();key(40,false);key(16,false);
    check(accelerated>=32&&accelerated<=37,'Live Shift hold count '+accelerated);next();
   case 8:
    if(dt<0.7)return;
    var m=menu();var found=false;
    for(index in order)if(m.songs[index].songName.toLowerCase() != 'random-song' && DifficultyManager.getSupportedDiffs(m.songs[index].songName).length>1&&m.availabilityAllowsSelection(index)) {
     FreeplayState.curSelected=index;m.changeSelection(0,true);m.buildIconFor(index);m.applyListLayout();m.updateBrowserDetails();found=true;break;
    }
    check(found,'No multi-difficulty chart');captureName='rating-grid';next();
   case 9:
    if(dt<0.6)return;tap(9);next();
   case 10:
    if(dt<0.6)return;
    var m=menu();check(Std.isOfType(m.subState,LibraryActionsSubState),'Library actions did not open');
    var actions:LibraryMenuSubState=cast m.subState;var found=false;
    for(entry in actions.actions)if(entry.label.indexOf('Song collection:')==0){entry.run();found=true;break;}
    check(found,'Embedded collections absent');next();
   case 11:
    if(dt<0.6)return;
    var actions:LibraryMenuSubState=cast menu().subState;var child:LibraryMenuSubState=cast actions.subState;
    check(Std.isOfType(child,LibraryCollectionsSubState),'Collection picker absent');
    var found=false;for(entry in child.actions)if(entry.label=='Base Game'){entry.run();found=true;break;}
    check(found,'Base Game collection absent');next();
   case 12:
    if(!Std.isOfType(FlxG.state,FreeplayState)||dt<1)return;
    var m=menu();check(FreeplayState.curCategory=='Base Game','Collection filter not applied');
    check(m.songs.length<order.length,'Collection did not narrow songs');captureName='base-collection';next();
   case 13:
    #if sys
    check(Sys.getCwd().split('\\').join('/').toLowerCase().indexOf('/tmp/')>=0,'Live registry probe requires a copied tmp runtime');
    var m=menu();
    registryPath=FreeplayRegistry.getPath();registryBytes=sys.io.File.getBytes(registryPath);
    liveState=m;liveIndex=FreeplayState.curSelected;liveKey=m.refreshSelectionKey(liveIndex);
    liveSearch=m.songs[liveIndex].songName;m.searchString=liveSearch;m.applySearchFilter();
    liveRow=m.songRows[liveIndex];liveIcon=m.iconArray[liveIndex];liveStar=m.starArray[liveIndex][0];
    liveCamera=m.camUI;liveMusic=FlxG.sound.music;liveDifficulty=DifficultyManager.getDiffName(FreeplayState.curDifficulty);liveSave=UserLibrary.data().encode();
    var categories:Array<Dynamic>=cast FreeplayRegistry.getJson();
    for(category in categories)if(category.name=='Base Game') {
     var entries:Array<Dynamic>=cast category.songs;
     for(entry in entries)if(entry.name==liveSearch)entry.display=liveSearch+' (refreshed)';
     entries.unshift({name:'live-nav-new',display:'Live added fixture',week:0,character:'bf'});
    }
    sys.io.File.saveContent(registryPath,haxe.Json.stringify(categories));ImportRefreshManager.generation++;next();
    #end
   case 14:
    if(dt<0.5)return;
    var m=menu();var selected=FreeplayState.curSelected;
    check(m==liveState && m.camUI==liveCamera && FlxG.sound.music==liveMusic,'Live refresh recreated state/camera/music');
    check(selected==liveIndex+1 && m.refreshSelectionKey(selected)==liveKey,'Live refresh lost reindexed selection identity');
    check(m.songRows[selected]==liveRow && m.iconArray[selected]==liveIcon && m.starArray[selected][0]==liveStar,'Unchanged visuals recreated during live refresh');
    check(m.songs[selected].displayTitle==liveSearch+' (refreshed)' && m.songRows[selected].text==m.songs[selected].displayTitle,'Retained row caption did not update');
    check(m.searchString==liveSearch && DifficultyManager.getDiffName(FreeplayState.curDifficulty)==liveDifficulty && UserLibrary.data().encode()==liveSave,'Live refresh lost view or changed saves');
    var added=false;for(song in m.songs)if(song.songName=='live-nav-new')added=true;check(added,'Published registry row did not appear live');
    RuntimeSmokeHarness.emit('freeplay_live_verified',{sameState:true,rowRetained:true,iconRetained:true,starRetained:true,metadataUpdated:true,reindexedSelection:true,searchAndDifficulty:true});
    captureName='live-refresh';next();
   case 15:
    #if sys
    var categories:Array<Dynamic>=cast FreeplayRegistry.getJson();for(category in categories)if(category.name=='Base Game')category.songs=[];
    sys.io.File.saveContent(registryPath,haxe.Json.stringify(categories));ImportRefreshManager.generation++;next();
    #end
   case 16:
    if(dt<0.5)return;
    var m=menu();check(m==liveState && m.songs.length==0 && m.browserEmpty.visible,'Empty live collection left the browser');
    check(FlxG.sound.music==liveMusic && UserLibrary.data().encode()==liveSave,'Empty refresh reset audio or save');
    captureName='live-empty';next();
   case 17: restoreRegistry();next();
   case 18:
    if(dt<0.5)return;check(menu()==liveState && menu().songs.length>0,'Restored registry did not update existing browser');
    RuntimeSmokeHarness.emit('freeplay_scroll_verified',{normalSteps:normal,acceleratedSteps:accelerated,directMainEntry:true,centered:true,collectionFilter:true,smoothPosition:sawPositionTween,cardTransition:sawCardTween,liveRefresh:true,liveEmpty:true});RuntimeSmokeHarness.succeed();
  } catch(error:Dynamic) { restoreRegistry(); RuntimeSmokeHarness.fail('freeplay-scroll-probe',Std.string(error)); }
 }
 static function capture():Void {
  #if sys
  if(captureName==''||haxe.Timer.stamp()-at<captureDelay)return;
  try {
   var image=lime.app.Application.current.window.readPixels();check(image!=null,'Empty framebuffer');
   var path=RuntimeSmokeHarness.config().logPath+'.scroll-'+captureName+'.png';RuntimeSmokeHarness.ensureParent(path);sys.io.File.saveBytes(path,image.encode());
   RuntimeSmokeHarness.emit('scroll_capture',{path:path});captureName='';captureDelay=0.5;
  } catch(error:Dynamic) {restoreRegistry();RuntimeSmokeHarness.fail('freeplay-scroll-capture',Std.string(error));}
  #end
 }
}
