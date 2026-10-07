"""Dependency fixture for unrelated extracted Psych preset contracts.

The real standard services and owner lifetimes have their own contract/native
checks. These fixtures retain the preset's actual forwarding calls.
"""
from pathlib import Path

STANDARD_SERVICES = """class PsychStandardServices {
 public static var hscriptCalls:Array<Array<Dynamic>>=[];
 public static var luaCalls:Array<Array<Dynamic>>=[];
 public static var scopeCalls:Array<Array<Dynamic>>=[];
 public static function installHscript(host:Dynamic,interp:Dynamic,origin:String):Void hscriptCalls.push([host,interp,origin]);
 public static function installLua(host:Dynamic,interp:Dynamic,origin:String):Void luaCalls.push([host,interp,origin]);
 public static function installScope(host:Dynamic,scope:Dynamic,paths:Dynamic):Void scopeCalls.push([host,scope,paths]);
}
"""


def write_standard_services_stub(folder: Path):
    (folder / "PsychStandardServices.hx").write_text(STANDARD_SERVICES, encoding="utf-8", newline="\n")
