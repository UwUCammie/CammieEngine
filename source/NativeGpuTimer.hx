package;

/** Windows desktop timer queries bypass Lime's GLES3-disabled query stubs. */
#if (cpp && windows)
@:cppFileCode('
#include <windows.h>
namespace cammie_gpu_timer {
 typedef void (APIENTRY *Gen)(int,unsigned int*);
 typedef void (APIENTRY *Begin)(unsigned int,unsigned int);
 typedef void (APIENTRY *End)(unsigned int);
 typedef void (APIENTRY *Get)(unsigned int,unsigned int,int*);
 typedef void (APIENTRY *Result)(unsigned int,unsigned int,unsigned long long*);
 typedef PROC (WINAPI *Lookup)(LPCSTR);
 static Gen gen = nullptr; static Begin begin = nullptr; static End end = nullptr;
 static Get get = nullptr, ready = nullptr; static Result result = nullptr;
 static void* address(Lookup lookup,const char* name) {
  auto p = lookup(name); auto value = reinterpret_cast<INT_PTR>(p);
  return value > 3 && value != -1 ? reinterpret_cast<void*>(p) : nullptr;
 }
 static int initialize() {
  HMODULE module = GetModuleHandleW(L"opengl32.dll"); if (!module) return 0;
  auto lookup = reinterpret_cast<Lookup>(GetProcAddress(module,"wglGetProcAddress")); if (!lookup) return 0;
  gen = reinterpret_cast<Gen>(address(lookup,"glGenQueries"));
  begin = reinterpret_cast<Begin>(address(lookup,"glBeginQuery"));
  end = reinterpret_cast<End>(address(lookup,"glEndQuery"));
  get = reinterpret_cast<Get>(address(lookup,"glGetQueryiv"));
  ready = reinterpret_cast<Get>(address(lookup,"glGetQueryObjectiv"));
  result = reinterpret_cast<Result>(address(lookup,"glGetQueryObjectui64v"));
  if (!gen || !begin || !end || !get || !ready || !result) return 0;
  int bits=0;get(0x88BF,0x8864,&bits);return bits;
 }
 static int create() {unsigned int id=0;gen(1,&id);return static_cast<int>(id);}
 static bool available(int id) {int value=0;ready(id,0x8867,&value);return value!=0;}
 static double milliseconds(int id) {unsigned long long value=0;result(id,0x8866,&value);return static_cast<double>(value)/1000000.0;}
}
')
#end
class NativeGpuTimer {
	public static function initialize():Int {
		#if (cpp && windows)
		return untyped __cpp__('cammie_gpu_timer::initialize()');
		#else
		return 0;
		#end
	}
	public static function create():Int {
		#if (cpp && windows)
		return untyped __cpp__('cammie_gpu_timer::create()');
		#else
		return 0;
		#end
	}
	public static function available(id:Int):Bool {
		#if (cpp && windows)
		return untyped __cpp__('cammie_gpu_timer::available({0})', id);
		#else
		return false;
		#end
	}
	public static function milliseconds(id:Int):Float {
		#if (cpp && windows)
		return untyped __cpp__('cammie_gpu_timer::milliseconds({0})', id);
		#else
		return 0;
		#end
	}
	public static function begin(id:Int):Void {
		#if (cpp && windows)
		untyped __cpp__('cammie_gpu_timer::begin(0x88BF,{0})', id);
		#end
	}
	public static function end():Void {
		#if (cpp && windows)
		untyped __cpp__('cammie_gpu_timer::end(0x88BF)');
		#end
	}
}
