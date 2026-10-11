package;

import haxe.io.Bytes;

/** Optional system SHA-256 acceleration. Callers retain the portable implementation as fallback. */
#if (cpp && windows)
@:cppFileCode('
#include <windows.h>
#include <bcrypt.h>
namespace cammie_sha256 {
 struct Api {
  HMODULE library; BCRYPT_ALG_HANDLE algorithm;
  decltype(&BCryptCreateHash) create; decltype(&BCryptHashData) update;
  decltype(&BCryptFinishHash) finish; decltype(&BCryptDestroyHash) destroy;
  Api():library(nullptr),algorithm(nullptr),create(nullptr),update(nullptr),finish(nullptr),destroy(nullptr) {
   // Never search the working directory or a mod package for this system DLL.
   library=LoadLibraryExW(L"bcrypt.dll",nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32);
   if(!library) return;
   auto open=reinterpret_cast<decltype(&BCryptOpenAlgorithmProvider)>(GetProcAddress(library,"BCryptOpenAlgorithmProvider"));
   create=reinterpret_cast<decltype(create)>(GetProcAddress(library,"BCryptCreateHash"));
   update=reinterpret_cast<decltype(update)>(GetProcAddress(library,"BCryptHashData"));
   finish=reinterpret_cast<decltype(finish)>(GetProcAddress(library,"BCryptFinishHash"));
   destroy=reinterpret_cast<decltype(destroy)>(GetProcAddress(library,"BCryptDestroyHash"));
   if(open && create && update && finish && destroy) {
    if(open(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0) algorithm=nullptr;
   }
  }
 };
 // C++ static initialization is synchronized. The provider is process-wide;
 // mutable hash objects are private to each stream, including worker threads.
 static Api& api() {static Api value;return value;}
 static void* create() {
  auto& a=api();if(!a.algorithm)return nullptr;
  BCRYPT_HASH_HANDLE hash=nullptr;
  if(a.create(a.algorithm,&hash,nullptr,0,nullptr,0,0)<0)return nullptr;
  return hash;
 }
 static bool update(void* hash,void* data,int count) {
  return api().update(hash,static_cast<PUCHAR>(data),static_cast<ULONG>(count),0)>=0;
 }
 static bool finish(void* hash,void* result) {return api().finish(hash,static_cast<PUCHAR>(result),32,0)>=0;}
 static void destroy(void* hash) {if(hash)api().destroy(hash);}
}
')
#end
class NativeStreamingSha256 {
	#if (cpp && windows)
	var handle:cpp.RawPointer<cpp.Void>;
	function new() {
		handle = untyped __cpp__('cammie_sha256::create()');
		if (handle != null) cpp.vm.Gc.setFinalizer(this, cpp.Function.fromStaticFunction(finalize));
	}
	@:void static function finalize(value:NativeStreamingSha256):Void {
		if (value != null) value.close();
	}
	#else
	function new() {}
	#end
	public static function create():Null<NativeStreamingSha256> {
		#if (cpp && windows)
		var value = new NativeStreamingSha256();
		return value.handle == null ? null : value;
		#else
		return null;
		#end
	}
	public function update(bytes:Bytes, position:Int, length:Int):Void {
		#if (cpp && windows)
		if (handle == null || bytes == null || length < 0 || position < 0 || position > bytes.length - length)
			throw 'Invalid native SHA-256 input.';
		if (length == 0) return;
		var ok:Bool = untyped __cpp__('cammie_sha256::update({0},{1}->GetBase()+{2},{3})', handle, bytes.getData(), position, length);
		if (!ok) {close();throw 'System SHA-256 update failed.';}
		#else
		throw 'System SHA-256 unavailable.';
		#end
	}
	public function digestHex():String {
		#if (cpp && windows)
		if (handle == null) throw 'Native SHA-256 stream is closed.';
		var bytes = Bytes.alloc(32);
		var ok:Bool = untyped __cpp__('cammie_sha256::finish({0},{1}->GetBase())',handle,bytes.getData());
		close();
		if (!ok) throw 'System SHA-256 finalization failed.';
		return bytes.toHex();
		#else
		throw 'System SHA-256 unavailable.';
		#end
	}
	public function close():Void {
		#if (cpp && windows)
		if (handle != null) {
			untyped __cpp__('cammie_sha256::destroy({0})',handle);
			handle = null;
		}
		#end
	}
}
