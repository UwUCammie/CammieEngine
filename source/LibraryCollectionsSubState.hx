package;

/** Registry collections live inside the browser alongside categories and sorting. */
class LibraryCollectionsSubState extends LibraryMenuSubState {
 var current:String;
 var selectCollection:String->Void;
 public function new(current:String, selectCollection:String->Void) {
  super(); this.current = current; this.selectCollection = selectCollection;
 }
 override function create():Void {
  super.create();
  var entries:Array<LibraryMenuSubState.LibraryMenuAction> = [];
  var registry:Array<Dynamic> = cast FreeplayRegistry.getJson();
  if (registry != null) for (entry in registry) {
   var name:String = entry.name;
   entries.push({label:(name == current ? '* ' : '') + name, run:function() selectCollection(name)});
  }
  entries.push({label:'Return', run:function() close()});
  showActions('Song collections', entries);
 }
}
