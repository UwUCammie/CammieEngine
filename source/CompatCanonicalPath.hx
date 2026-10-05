package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

/** Resolve an existing physical path, including Windows junction targets. */
#if (cpp && windows)
@:cppInclude("windows.h")
@:cppInclude("vector")
#end
class CompatCanonicalPath {
	#if sys
	public static function resolve(path:String):Null<String> {
		#if (cpp && windows)
		// fullPath on Windows is lexical. Resolve the final filesystem target.
		var result:String = untyped __cpp__('([](::String value) -> ::String {
			HANDLE handle = CreateFileW(value.wchar_str(), 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
				NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
			if (handle == INVALID_HANDLE_VALUE) return ::String();
			DWORD needed = GetFinalPathNameByHandleW(handle, NULL, 0, FILE_NAME_NORMALIZED);
			if (!needed) { CloseHandle(handle); return ::String(); }
			std::vector<wchar_t> buffer(needed + 1);
			DWORD length = GetFinalPathNameByHandleW(handle, buffer.data(), (DWORD)buffer.size(), FILE_NAME_NORMALIZED);
			CloseHandle(handle);
			if (!length || length >= buffer.size()) return ::String();
			return ::String::create(buffer.data(), length);
		})({0})', path);
		#else
		var result = FileSystem.fullPath(path);
		#end
		if (result == null) return null;
		result = result.replace('\\', '/');
		if (result.startsWith('//?/UNC/')) result = '//' + result.substr(8);
		else if (result.startsWith('//?/')) result = result.substr(4);
		result = Path.normalize(result);
		return Sys.systemName() == 'Windows' ? result.toLowerCase() : result;
	}
	#else
	public static function resolve(path:String):Null<String> return null;
	#end
}
