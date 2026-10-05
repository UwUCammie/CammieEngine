@echo off
lime build html5 -xml -Dtypebuild
if errorlevel 1 exit /b %errorlevel%
haxelib run dox -i export/release/html5/types.xml -o docs
if errorlevel 1 exit /b %errorlevel%
python tools/normalize_api_docs.py --docs docs
exit /b %errorlevel%
