import re

"""Injected async-owner contracts for tests of unrelated interpreter bindings.

The real timer/tween/audio lifetime implementations have native acceptance and
extracted behavioral coverage in test_imported_menu_async_resources.
"""

def menu_async_contract_files():
    return {
        'CodenamePaths.hx':'class CodenamePaths {public function new(root:String){}}',
        'CodenameScriptInterp.hx':'class CodenameScriptInterp {public function new(p:CodenamePaths){}public function ownTimer(v:Dynamic):Dynamic return v;public function ownTween(v:Dynamic):Dynamic return v;public function ownSound(v:Dynamic):Dynamic return v;public function release():Void{}}',
    }

def add_menu_async_contracts(files, native_flixel=False):
    for name,source in menu_async_contract_files().items(): files.setdefault(name,source)
    if not native_flixel:
        files.setdefault('flixel/util/FlxTimer.hx','package flixel.util;class FlxTimer {}')
        files.setdefault('flixel/tweens/FlxTween.hx','package flixel.tweens;class FlxTween {}')
        files.setdefault('flixel/sound/FlxSound.hx','package flixel.sound;class FlxSound {}')
        files.setdefault('flixel/FlxG.hx','package flixel;class FlxG {}')
        if 'var sound' not in files['flixel/FlxG.hx']:
            files['flixel/FlxG.hx']=re.sub(r'class FlxG\s*\{', 'class FlxG {public static var sound:Dynamic=null;', files['flixel/FlxG.hx'])
    return files

def install_menu_async_contracts(work, native_flixel=False):
    files=add_menu_async_contracts({},native_flixel)
    for name,source in files.items():
        path=work/name
        if path.exists():
            if name=='flixel/FlxG.hx' and 'var sound' not in path.read_text():
                path.write_text(path.read_text().replace('class FlxG {','class FlxG {public static var sound:Dynamic=null;'))
            continue
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
