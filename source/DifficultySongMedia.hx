package;
import haxe.io.Path;
import ImportFileSystem as FileSystem;

/** Select only the authored song's alternate media within this source audio tree. */
class DifficultySongMedia {
 public static function plan(audioRoot:String, baseSong:String, authoredSong:String,
  chartFile:String, destinationFolder:String):Dynamic {
  if (audioRoot == null || !FileSystem.isDirectory(audioRoot) || authoredSong == null) return null;
  var song = PsychSongNameCompat.format(authoredSong);
  if (song == '' || song == PsychSongNameCompat.format(baseSong)) return null;
  if (song.indexOf('/') >= 0 || song.indexOf('\\') >= 0 || song.indexOf('..') >= 0) return null;
  var folder:String = null;
  for (entry in FileSystem.readDirectory(audioRoot)) if (entry.toLowerCase() == song.toLowerCase()
   && FileSystem.isDirectory(Path.join([audioRoot,entry]))) {
   if (folder != null) throw 'Ambiguous authored song audio directory: ' + song;
   folder = Path.join([audioRoot,entry]);
  }
  if (folder == null) return null;
  var root = StringTools.replace(FileSystem.fullPath(audioRoot), '\\', '/'); var physical = StringTools.replace(FileSystem.fullPath(folder), '\\', '/');
  #if windows
  physical = physical.toLowerCase(); root = root.toLowerCase();
  #end
  if (!StringTools.startsWith(physical, root + '/'))
   throw 'Authored difficulty audio escapes the selected source tree.';
  var key = Path.withoutExtension(chartFile).toLowerCase();
  var prefix = destinationFolder.toLowerCase() + '-';
  var difficulty = key == destinationFolder.toLowerCase() ? 'normal' : StringTools.startsWith(key,prefix) ? key.substr(prefix.length) : '';
  if (difficulty == '' || difficulty.indexOf('/') >= 0 || difficulty.indexOf('..') >= 0) return null;
  var files:Map<String,String> = [];
  for (entry in FileSystem.readDirectory(folder)) {
   var lower = entry.toLowerCase(); var path = Path.join([folder,entry]);
   if (FileSystem.isDirectory(path)) continue;
   if (files.exists(lower)) throw 'Ambiguous authored difficulty media file: ' + entry;
   files.set(lower,path);
  }
  var inst = files.get('inst.ogg');
  if (inst == null) throw 'Authored alternate song is missing Inst.ogg: ' + song;
  var outputs:Array<Dynamic> = [{source:inst,destination:'Inst-' + difficulty + '.ogg'}];
  var stems:Array<Dynamic> = [];
  var voices = files.get('voices.ogg');
  if (voices != null) {
   outputs.push({source:voices,destination:'Voices-' + difficulty + '.ogg'});
   stems.push({id:'shared',role:'shared',file:'Voices-' + difficulty + '.ogg'});
  } else for (name in [for (name in files.keys()) name]) {
   if (!StringTools.startsWith(name,'voices-') && !StringTools.startsWith(name,'voices_')) continue;
   if (Path.extension(name) != 'ogg') continue;
   var id = Path.withoutExtension(name).substr(7);
   var destination = 'Voices-' + id + '-' + difficulty + '.ogg';
   outputs.push({source:files.get(name),destination:destination});
   stems.push({id:id,role:id == 'opponent' || id == 'opp' ? 'opponent' : id == 'player' ? 'player' : 'shared',file:destination});
  }
  stems.sort(function(a,b) return Reflect.compare(a.id,b.id));
  return {files:outputs,stems:stems,song:song,difficulty:difficulty};
 }
}
