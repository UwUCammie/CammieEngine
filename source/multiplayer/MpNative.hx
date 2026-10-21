package multiplayer;

import haxe.io.Bytes;

/** The native network calls multiplayer needs: an HTTPS JSON POST and a WebSocket.
 *
 * On Windows both go through WinHTTP, so certificates are checked against the Windows
 * store and the system proxy settings apply, like the updater's URLMon download. Every
 * call here blocks: callers run them on worker threads (MpHttp, MpSocket). Blocking
 * happens inside a GC-free zone with the data already copied to native buffers, so a
 * collection on another thread never waits for the network. */
#if (cpp && windows)
@:cppFileCode('
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <cstring>
namespace cammie_mp_native {
 struct Socket {
  HINTERNET session = NULL;
  HINTERNET connect = NULL;
  HINTERNET socket = NULL;
  int lastKind = -1;
  int lastError = 0;
 };
 static std::mutex lock;
 static std::map<int, Socket*> sockets;
 static int nextId = 1;
 static const int MAX_MESSAGE = 1 << 20;

 static std::wstring wide(::String value) {
  hx::strbuf buffer;
  return std::wstring(value.wchar_str(&buffer));
 }
 static Socket* find(int id) {
  std::lock_guard<std::mutex> guard(lock);
  auto it = sockets.find(id);
  return it == sockets.end() ? nullptr : it->second;
 }
 static HINTERNET openSession() {
  HINTERNET session = WinHttpOpen(L"CammieEngine", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
   WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
  if (session) WinHttpSetTimeouts(session, 10000, 10000, 20000, 20000);
  return session;
 }

 // POST a JSON body. Returns the status, a newline, then the body: the HTTP status, or a negative
 // Windows error code when no response arrived. No shared state, so any thread may call it.
 static ::String post(::String host, int port, bool secure, ::String path, ::String body, ::String headers) {
  const std::wstring wideHost = wide(host);
  const std::wstring widePath = wide(path);
  const std::wstring wideHeaders = wide(headers);
  hx::strbuf bodyBuffer;
  const char* utf8 = body.utf8_str(&bodyBuffer);
  const std::string payload(utf8 == nullptr ? "" : utf8);
  std::string out;
  int status = -1;
  hx::EnterGCFreeZone();
  HINTERNET session = openSession();
  HINTERNET connect = session ? WinHttpConnect(session, wideHost.c_str(), (INTERNET_PORT)port, 0) : NULL;
  HINTERNET request = connect ? WinHttpOpenRequest(connect, L"POST", widePath.c_str(), NULL, WINHTTP_NO_REFERER,
   WINHTTP_DEFAULT_ACCEPT_TYPES, secure ? WINHTTP_FLAG_SECURE : 0) : NULL;
  if (request && WinHttpSendRequest(request, wideHeaders.c_str(), (DWORD)-1L, (LPVOID)payload.data(),
    (DWORD)payload.size(), (DWORD)payload.size(), 0) && WinHttpReceiveResponse(request, NULL)) {
   DWORD code = 0, size = sizeof(code);
   WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX,
    &code, &size, WINHTTP_NO_HEADER_INDEX);
   status = (int)code;
   DWORD available = 0;
   while (WinHttpQueryDataAvailable(request, &available) && available > 0 && out.size() < (size_t)MAX_MESSAGE) {
    size_t at = out.size();
    out.resize(at + available);
    DWORD read = 0;
    if (!WinHttpReadData(request, &out[at], available, &read)) { out.resize(at); break; }
    out.resize(at + read);
   }
  } else {
   status = -(int)GetLastError();
  }
  if (request) WinHttpCloseHandle(request);
  if (connect) WinHttpCloseHandle(connect);
  if (session) WinHttpCloseHandle(session);
  hx::ExitGCFreeZone();
  const std::string framed = std::to_string(status) + "\\n" + out;
  return ::String::create(framed.c_str(), (int)framed.size());
 }

 // Open a WebSocket (over TLS when secure). Returns a positive id, or a negative Windows error code.
 static int open(::String host, int port, bool secure, ::String path) {
  const std::wstring wideHost = wide(host);
  const std::wstring widePath = wide(path);
  int result = 0;
  Socket* made = new Socket();
  hx::EnterGCFreeZone();
  made->session = openSession();
  made->connect = made->session ? WinHttpConnect(made->session, wideHost.c_str(), (INTERNET_PORT)port, 0) : NULL;
  HINTERNET request = made->connect ? WinHttpOpenRequest(made->connect, L"GET", widePath.c_str(), NULL,
   WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, secure ? WINHTTP_FLAG_SECURE : 0) : NULL;
  if (request && WinHttpSetOption(request, WINHTTP_OPTION_UPGRADE_TO_WEB_SOCKET, NULL, 0)
    && WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0, NULL, 0, 0, 0)
    && WinHttpReceiveResponse(request, NULL)) {
   DWORD code = 0, size = sizeof(code);
   WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX,
    &code, &size, WINHTTP_NO_HEADER_INDEX);
   if (code == 101) made->socket = WinHttpWebSocketCompleteUpgrade(request, NULL);
   result = made->socket ? 0 : (code != 0 ? -(int)code : -(int)GetLastError());
  } else {
   result = -(int)GetLastError();
  }
  if (request) WinHttpCloseHandle(request);
  hx::ExitGCFreeZone();
  if (result != 0 || made->socket == NULL) {
   if (made->connect) WinHttpCloseHandle(made->connect);
   if (made->session) WinHttpCloseHandle(made->session);
   delete made;
   return result == 0 ? -1 : result;
  }
  std::lock_guard<std::mutex> guard(lock);
  int id = nextId++;
  sockets[id] = made;
  return id;
 }

 // Send one whole message. Returns 0 or a Windows error code. One sender at a time.
 static int send(int id, Array<unsigned char> data, bool binary) {
  Socket* socket = find(id);
  if (socket == nullptr) return 6;
  std::vector<unsigned char> copy(data->length);
  if (data->length > 0) std::memcpy(copy.data(), data->GetBase(), data->length);
  hx::EnterGCFreeZone();
  DWORD error = WinHttpWebSocketSend(socket->socket, binary ? WINHTTP_WEB_SOCKET_BINARY_MESSAGE_BUFFER_TYPE
   : WINHTTP_WEB_SOCKET_UTF8_MESSAGE_BUFFER_TYPE, copy.empty() ? NULL : copy.data(), (DWORD)copy.size());
  hx::ExitGCFreeZone();
  return (int)error;
 }

 // Receive one whole message (fragments joined). lastKind: 0 text, 1 binary, 2 closed, -1 error.
 static Array<unsigned char> receive(int id) {
  Socket* socket = find(id);
  std::vector<unsigned char> message;
  int kind = -1;
  int error = 0;
  if (socket != nullptr) {
   std::vector<unsigned char> buffer(65536);
   hx::EnterGCFreeZone();
   while (true) {
    DWORD read = 0;
    WINHTTP_WEB_SOCKET_BUFFER_TYPE type;
    DWORD status = WinHttpWebSocketReceive(socket->socket, buffer.data(), (DWORD)buffer.size(), &read, &type);
    if (status != NO_ERROR) { kind = -1; error = (int)status; break; }
    if (type == WINHTTP_WEB_SOCKET_CLOSE_BUFFER_TYPE) { kind = 2; break; }
    message.insert(message.end(), buffer.begin(), buffer.begin() + read);
    if (message.size() > (size_t)MAX_MESSAGE) { kind = -1; error = 1; break; }
    if (type == WINHTTP_WEB_SOCKET_UTF8_MESSAGE_BUFFER_TYPE) { kind = 0; break; }
    if (type == WINHTTP_WEB_SOCKET_BINARY_MESSAGE_BUFFER_TYPE) { kind = 1; break; }
   }
   hx::ExitGCFreeZone();
   socket->lastKind = kind;
   socket->lastError = error;
  }
  Array<unsigned char> result = Array_obj<unsigned char>::__new((int)message.size(), (int)message.size());
  if (!message.empty()) std::memcpy(result->GetBase(), message.data(), message.size());
  return result;
 }

 static int lastKind(int id) { Socket* socket = find(id); return socket == nullptr ? -1 : socket->lastKind; }
 static int lastError(int id) { Socket* socket = find(id); return socket == nullptr ? 6 : socket->lastError; }

 // Ask the server to close; a blocked receive then returns with kind 2.
 static void shutdown(int id) {
  Socket* socket = find(id);
  if (socket == nullptr) return;
  hx::EnterGCFreeZone();
  WinHttpWebSocketShutdown(socket->socket, WINHTTP_WEB_SOCKET_SUCCESS_CLOSE_STATUS, NULL, 0);
  hx::ExitGCFreeZone();
 }

 // Free the handles. Only after the receiving thread has returned.
 static void release(int id) {
  Socket* socket = nullptr;
  {
   std::lock_guard<std::mutex> guard(lock);
   auto it = sockets.find(id);
   if (it == sockets.end()) return;
   socket = it->second;
   sockets.erase(it);
  }
  if (socket->socket) WinHttpCloseHandle(socket->socket);
  if (socket->connect) WinHttpCloseHandle(socket->connect);
  if (socket->session) WinHttpCloseHandle(socket->session);
  delete socket;
 }
}
')
@:buildXml("<target id='haxe' if='HXCPP_MINGW'><lib name='-lwinhttp'/></target><target id='haxe' unless='HXCPP_MINGW'><lib name='winhttp.lib'/></target>")
#end
class MpNative {
	public static inline var ORIGIN:String = 'https://uwucammie.com';

	/** POST `json` to `path` on an endpoint. Returns the status (negative: no response) and body. */
	public static function post(endpoint:MpEndpoint, path:String, json:String):{status:Int, body:String} {
		#if (cpp && windows)
		var headers = 'Content-Type: application/json\r\nOrigin: ' + ORIGIN + '\r\n';
		var framed:String = untyped __cpp__('cammie_mp_native::post({0}, {1}, {2}, {3}, {4}, {5})', endpoint.host, endpoint.port,
			endpoint.secure, path, json, headers);
		var newline = framed.indexOf('\n');
		var status = Std.parseInt(newline < 0 ? framed : framed.substr(0, newline));
		return {status: status == null ? -1 : status, body: newline < 0 ? '' : framed.substr(newline + 1)};
		#else
		return {status: -1, body: ''};
		#end
	}

	/** Open a WebSocket on an endpoint. A positive id, or a negative error code. */
	public static function open(endpoint:MpEndpoint, path:String):Int {
		#if (cpp && windows)
		return untyped __cpp__('cammie_mp_native::open({0}, {1}, {2}, {3})', endpoint.host, endpoint.port, endpoint.secure, path);
		#else
		return -1;
		#end
	}

	/** Send one message; 0 on success. */
	public static function send(id:Int, data:Bytes, binary:Bool):Int {
		#if (cpp && windows)
		return untyped __cpp__('cammie_mp_native::send({0}, {1}, {2})', id, data.getData(), binary);
		#else
		return -1;
		#end
	}

	/** Block for the next message. `kind` 0 text, 1 binary, 2 closed, -1 error. */
	public static function receive(id:Int):{kind:Int, data:Bytes, error:Int} {
		#if (cpp && windows)
		var data:haxe.io.BytesData = untyped __cpp__('cammie_mp_native::receive({0})', id);
		var kind:Int = untyped __cpp__('cammie_mp_native::lastKind({0})', id);
		var error:Int = untyped __cpp__('cammie_mp_native::lastError({0})', id);
		return {kind: kind, data: Bytes.ofData(data), error: error};
		#else
		return {kind: -1, data: Bytes.alloc(0), error: -1};
		#end
	}

	public static function shutdown(id:Int):Void {
		#if (cpp && windows)
		untyped __cpp__('cammie_mp_native::shutdown({0})', id);
		#end
	}

	public static function release(id:Int):Void {
		#if (cpp && windows)
		untyped __cpp__('cammie_mp_native::release({0})', id);
		#end
	}

	/** True where the native transport exists (Windows builds). */
	public static inline function available():Bool {
		#if (cpp && windows)
		return true;
		#else
		return false;
		#end
	}
}
