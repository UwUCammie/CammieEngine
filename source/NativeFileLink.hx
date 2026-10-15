package;

/** Hard links, in-place replacement and file identity, used to store
 * identical imported files once. Every call returns false where the platform
 * or filesystem cannot do it, and callers then keep their separate copies. */
#if (cpp && windows)
@:cppFileCode('
#include <windows.h>
#include <string>
namespace cammie_file_link {
 static std::wstring widen(::String input) {
  hx::strbuf buffer;
  std::wstring path(input.wchar_str(&buffer));
  const wchar_t slash=92;
  for(auto& c:path) if(c==47)c=slash;
  const std::wstring extended=std::wstring(2,slash)+L"?"+slash;
  if(path.size()+12>=MAX_PATH && path.compare(0,4,extended)!=0) {
   if(path.compare(0,2,std::wstring(2,slash))==0)path=extended+L"UNC"+slash+path.substr(2);
   else if(path.size()>2 && path[1]==58 && path[2]==slash)path=extended+path;
  }
  return path;
 }
 static bool link(::String existing, ::String created) {
  std::wstring from=widen(existing), to=widen(created);
  hx::EnterGCFreeZone();
  BOOL ok=CreateHardLinkW(to.c_str(),from.c_str(),NULL);
  hx::ExitGCFreeZone();
  return ok!=0;
 }
 static bool replace(::String source, ::String target) {
  std::wstring from=widen(source), to=widen(target);
  hx::EnterGCFreeZone();
  BOOL ok=MoveFileExW(from.c_str(),to.c_str(),MOVEFILE_REPLACE_EXISTING);
  hx::ExitGCFreeZone();
  return ok!=0;
 }
 static bool identity(const std::wstring& path, BY_HANDLE_FILE_INFORMATION* info) {
  HANDLE handle=CreateFileW(path.c_str(),0,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS,NULL);
  if(handle==INVALID_HANDLE_VALUE)return false;
  BOOL ok=GetFileInformationByHandle(handle,info);
  CloseHandle(handle);
  return ok!=0;
 }
 static bool same(::String left, ::String right) {
  std::wstring a=widen(left), b=widen(right);
  BY_HANDLE_FILE_INFORMATION x, y;
  hx::EnterGCFreeZone();
  bool ok=identity(a,&x) && identity(b,&y);
  hx::ExitGCFreeZone();
  return ok && x.dwVolumeSerialNumber==y.dwVolumeSerialNumber
   && x.nFileIndexHigh==y.nFileIndexHigh && x.nFileIndexLow==y.nFileIndexLow;
 }
 static int links(::String path) {
  std::wstring a=widen(path);
  BY_HANDLE_FILE_INFORMATION x;
  hx::EnterGCFreeZone();
  bool ok=identity(a,&x);
  hx::ExitGCFreeZone();
  return ok ? (int)x.nNumberOfLinks : 0;
 }
}
')
#end
class NativeFileLink {
	/** Create `created` as another name for the existing file `existing`. */
	public static function link(existing:String, created:String):Bool {
		#if (cpp && windows)
		return untyped __cpp__('cammie_file_link::link({0}, {1})', existing, created);
		#else
		return false;
		#end
	}

	/** Move `source` over `target` in one step, replacing it. */
	public static function replace(source:String, target:String):Bool {
		#if (cpp && windows)
		return untyped __cpp__('cammie_file_link::replace({0}, {1})', source, target);
		#else
		return false;
		#end
	}

	/** True when both paths name the same stored file. */
	public static function sameFile(left:String, right:String):Bool {
		#if (cpp && windows)
		return untyped __cpp__('cammie_file_link::same({0}, {1})', left, right);
		#else
		return false;
		#end
	}

	/** Number of names the stored file has, or 0 when unknown. */
	public static function linkCount(path:String):Int {
		#if (cpp && windows)
		return untyped __cpp__('cammie_file_link::links({0})', path);
		#else
		return 0;
		#end
	}
}
