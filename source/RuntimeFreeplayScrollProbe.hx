package;
import flixel.FlxG;
/** Muted, private-save verification using the actual held keyboard controls. */
@:access(FreeplayState)
@:access(MainMenuState)
@:access(LibraryMenuSubState)
@:access(RuntimeSmokeHarness)
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
    if(dt<0.18)return;
    check(steps()==1,'Hold repeated before initial delay');next();
   case 4:
    if(dt<1.82)return;
    normal=steps();key(40,false);check(normal>=17&&normal<=20,'Normal hold count '+normal);
    RuntimeSmokeHarness.emit('scroll_hold',{normal:normal,seconds:2});next();
   case 5:
    if(dt<0.7)return;
    var m=menu(); var pos=m.rowSongIndices.indexOf(FreeplayState.curSelected);var row=m.songRows[FreeplayState.curSelected];
    check(Math.abs(row.y+m.selectedCardHeight()/2-FlxG.height/2)<0.05,'Selection did not settle to center');
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
    RuntimeSmokeHarness.emit('freeplay_scroll_verified',{normalSteps:normal,acceleratedSteps:accelerated,directMainEntry:true,centered:true,collectionFilter:true});RuntimeSmokeHarness.succeed();
  } catch(error:Dynamic) RuntimeSmokeHarness.fail('freeplay-scroll-probe',Std.string(error));
 }
 static function capture():Void {
  #if sys
  if(captureName==''||haxe.Timer.stamp()-at<0.5)return;
  try {
   var image=lime.app.Application.current.window.readPixels();check(image!=null,'Empty framebuffer');
   var path=RuntimeSmokeHarness.config().logPath+'.scroll-'+captureName+'.png';RuntimeSmokeHarness.ensureParent(path);sys.io.File.saveBytes(path,image.encode());
   RuntimeSmokeHarness.emit('scroll_capture',{path:path});captureName='';
  } catch(error:Dynamic)RuntimeSmokeHarness.fail('freeplay-scroll-capture',Std.string(error));
  #end
 }
}
