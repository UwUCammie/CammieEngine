package;
/** One directory enumeration with file-type metadata. No persistent filesystem cache.
 * Reparse points retain the host filesystem's live target classification. */
#if sys
import sys.FileSystem;
#end
typedef DirectoryEntry = {
	var name:String;
	// Null means the caller must query the live filesystem when it visits this entry.
	var isDirectory:Null<Bool>;
}

#if (cpp && windows)
@:cppFileCode('
#include <windows.h>
#include <string>
namespace cammie_directory {
 static ::Array< ::String > read(::String input) {
  hx::strbuf buffer;
  std::wstring path(input.wchar_str(&buffer));
  const wchar_t slash=92;
  for(auto& c:path) if(c==47)c=slash;
  const std::wstring extended=std::wstring(2,slash)+L"?"+slash;
  const std::wstring device=std::wstring(2,slash)+L"."+slash;
  if(path.compare(0,4,extended)!=0 && path.compare(0,4,device)!=0 && path.size()+4>=MAX_PATH) {
   if(path.compare(0,2,std::wstring(2,slash))==0)path=extended+L"UNC"+slash+path.substr(2);
   else if(path.size()>2 && path[1]==58 && path[2]==slash)path=extended+path;
   else return null();
  }
  if(path.empty() || path.back()!=slash)path+=slash;
  path+=L"*.*";
  WIN32_FIND_DATAW data;
  hx::EnterGCFreeZone();
  HANDLE handle=FindFirstFileW(path.c_str(),&data);
  hx::ExitGCFreeZone();
  if(handle==INVALID_HANDLE_VALUE)return null();
  struct Close {HANDLE value;~Close(){FindClose(value);}} close{handle};
  ::Array< ::String > result=::Array_obj< ::String >::__new();
  for(;;) {
   if(data.cFileName[0]!=46 || (data.cFileName[1]!=0 && (data.cFileName[1]!=46 || data.cFileName[2]!=0))) {
    const wchar_t tag=(data.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)?114:((data.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)?100:102);
    std::wstring entry(1,tag);entry+=data.cFileName;
    result->push(::String::create(entry.c_str()));
   }
   hx::EnterGCFreeZone();
   BOOL more=FindNextFileW(handle,&data);
   DWORD error=more?ERROR_SUCCESS:GetLastError();
   hx::ExitGCFreeZone();
   if(!more) {if(error!=ERROR_NO_MORE_FILES)return null();break;}
  }
  return result;
 }
}
')
#end
class NativeDirectoryListing {
	public static function read(path:String):Array<DirectoryEntry> {
		#if (cpp && windows)
		var encoded:Array<String> = null;
		// Preserve empty and drive-current-directory semantics through the portable path.
		if (path != null && path != '' && !(path.length == 2 && path.charAt(1) == ':'))
			encoded = untyped __cpp__('cammie_directory::read({0})', path);
		if (encoded != null) return [for (entry in encoded) {
			name: entry.substr(1),
			isDirectory: entry.charAt(0) == 'r' ? null : entry.charAt(0) == 'd'
		}];
		#end
		#if sys
		// Failed/partial native enumeration cannot publish incomplete metadata.
		// The portable path retains ordinary failures and defers type queries so
		// bounded traversals do not stat entries they will never visit.
		return [for (name in FileSystem.readDirectory(path)) {
			name: name, isDirectory: null
		}];
		#else
		return [];
		#end
	}
}
