@echo off
rem Native Windows build/run entry point for Disappointing Plus.
rem
rem   run.bat                 build release and launch 64-bit Windows
rem   run.bat debug            build debug and launch 64-bit Windows
rem   run.bat build            build release, do not launch
rem   run.bat rebuild          rebuild release, do not launch
rem   run.bat build32          build 32-bit, do not launch
rem   run.bat server           start the Haxe compilation server
rem   run.bat nobuild          launch an existing build
rem
rem This script intentionally uses a native Windows hxcpp/Visual Studio
rem toolchain. It does not use Wine to cross-compile Windows binaries.
setlocal EnableExtensions EnableDelayedExpansion

rem %~dp0 is the directory containing this script, even when invoked from a
rem different working directory. The game itself is later launched from its
rem export bin directory because its assets and saves are cwd-relative.
set "ROOT=%~dp0"
if "!ROOT:~-1!"=="\" set "ROOT=!ROOT:~0,-1!"
cd /d "!ROOT!"
if errorlevel 1 (
	echo ERROR: Could not change to the project directory: !ROOT! 1>&2
	exit /b 1
)

rem Keep Haxe, archive and compiler scratch files on the project drive rather
rem than a potentially space-constrained system TEMP directory.
set "PROJECT_TMP=!ROOT!\tmp"
if not exist "!PROJECT_TMP!" mkdir "!PROJECT_TMP!"
set "TEMP=!PROJECT_TMP!"
set "TMP=!PROJECT_TMP!"

set "MODE=release"
set "DEBUG=0"
set "ARCH=64"
set "HAXE_DEBUG_FLAG="
set "LIME_ARCH_FLAGS="
set "HAXE_VERSION="

:parse_args
if "%~1"=="" goto args_done
set "ARG=%~1"
if /I "!ARG!"=="debug" (
	set "DEBUG=1"
	shift
	goto parse_args
)
if /I "!ARG!"=="release" (
	set "MODE=release"
	shift
	goto parse_args
)
if /I "!ARG!"=="build" (
	set "MODE=build"
	shift
	goto parse_args
)
if /I "!ARG!"=="rebuild" (
	set "MODE=rebuild"
	shift
	goto parse_args
)
if /I "!ARG!"=="nobuild" (
	set "MODE=nobuild"
	shift
	goto parse_args
)
if /I "!ARG!"=="server" (
	set "MODE=server"
	shift
	goto parse_args
)
if /I "!ARG!"=="build32" (
	set "MODE=build"
	set "ARCH=32"
	shift
	goto parse_args
)
if /I "!ARG!"=="rebuild32" (
	set "MODE=rebuild"
	set "ARCH=32"
	shift
	goto parse_args
)
if /I "!ARG!"=="help" goto usage
if /I "!ARG!"=="-h" goto usage
if /I "!ARG!"=="--help" goto usage
echo ERROR: Unknown argument: !ARG! 1>&2
goto usage_error

:args_done
if "!DEBUG!"=="1" set "HAXE_DEBUG_FLAG=-debug"
if "!ARCH!"=="32" set "LIME_ARCH_FLAGS=-D32bit -32"
if "!ARCH!"=="32" (
	set "BUILD_ROOT=export\32bit"
) else if "!DEBUG!"=="1" (
	set "BUILD_ROOT=export\debug"
) else (
	set "BUILD_ROOT=export\release"
)
set "BIN=!ROOT!\!BUILD_ROOT!\windows\bin\Funkin.exe"

rem nobuild is deliberately dependency-free, matching run.sh's contract.
if /I "!MODE!"=="nobuild" goto launch

call :ensure_toolchain
if errorlevel 1 exit /b 1
call :ensure_astc_decoder
if errorlevel 1 exit /b 1
call :ensure_haxelibs
if errorlevel 1 exit /b 1
call :ensure_shared_haxelib_patches
if errorlevel 1 exit /b 1
call :patch_haxelibs
if errorlevel 1 exit /b 1
call :ensure_asset_scaffolding
if errorlevel 1 exit /b 1

if /I "!MODE!"=="server" goto start_server

:do_build
if /I "!MODE!"=="nobuild" goto launch
if /I "!MODE!"=="server" goto start_server
if /I not "!MODE!"=="release" if /I not "!MODE!"=="build" if /I not "!MODE!"=="rebuild" goto usage_error

call :ensure_native_compiler
if errorlevel 1 exit /b 1

set "LIVE_OPTS=!ROOT!\!BUILD_ROOT!\windows\bin\assets\data\options.json"
set "OPTS_BAK="
if exist "!LIVE_OPTS!" (
	set "OPTS_BAK=%TEMP%\disappointing-plus-options-!RANDOM!.json"
	copy /Y "!LIVE_OPTS!" "!OPTS_BAK!" >nul
)

echo ^>^> building Windows !ARCH!-bit (!MODE!!HAXE_DEBUG_FLAG!)...
call haxelib run lime build windows !LIME_ARCH_FLAGS! !HAXE_DEBUG_FLAG!
set "BUILD_RESULT=!ERRORLEVEL!"

if defined OPTS_BAK (
	if exist "!OPTS_BAK!" copy /Y "!OPTS_BAK!" "!LIVE_OPTS!" >nul
	del /Q "!OPTS_BAK!" >nul 2>&1
)
if not "!BUILD_RESULT!"=="0" (
	echo ERROR: Lime failed with exit code !BUILD_RESULT!. 1>&2
	exit /b !BUILD_RESULT!
)
call :sync_astc_decoder
if errorlevel 1 exit /b 1

if /I "!MODE!"=="build" goto build_done
if /I "!MODE!"=="rebuild" goto build_done
goto launch

:build_done
if exist "!BIN!" (
	echo ^>^> built !BIN!
	exit /b 0
)
echo ERROR: Lime completed but no Windows executable was found at !BIN! 1>&2
exit /b 1

:start_server
tasklist /FI "IMAGENAME eq haxe.exe" 2>nul | findstr /I /C:"haxe.exe" >nul
if not errorlevel 1 (
	echo ^>^> a Haxe process is already running; leaving it in place
	exit /b 0
)
start "CammieEngine Haxe server" /B haxe --wait 6000
if errorlevel 1 (
	echo ERROR: Could not start the Haxe compilation server on port 6000. 1>&2
	exit /b 1
)
echo ^>^> compilation server started on port 6000
exit /b 0

:launch
if not exist "!BIN!" (
	echo ERROR: No Windows executable at !BIN!; run run.bat build first. 1>&2
	exit /b 1
)
pushd "!ROOT!\!BUILD_ROOT!\windows\bin"
if errorlevel 1 (
	echo ERROR: Could not change to the Windows runtime directory. 1>&2
	exit /b 1
)
echo ^>^> running !BIN!
Funkin.exe
set "GAME_RESULT=!ERRORLEVEL!"
popd
exit /b !GAME_RESULT!

:ensure_toolchain
set "TOOLS=!ROOT!\.tools"
set "HAXEPATH=!TOOLS!\haxe"
set "NEKOPATH=!TOOLS!\neko"
set "HAXELIB_PATH=!ROOT!\.haxelib"
set "PATH=!HAXEPATH!;!NEKOPATH!;!PATH!"
where powershell.exe >nul 2>&1
if errorlevel 1 (
	echo ERROR: PowerShell is required to bootstrap the portable Windows Haxe/Neko archives. 1>&2
	exit /b 1
)

if not exist "!HAXEPATH!\haxe.exe" goto install_haxe
for /f "tokens=1" %%V in ('"!HAXEPATH!\haxe.exe" --version 2^>nul') do set "HAXE_VERSION=%%V"
if "!HAXE_VERSION!"=="4.3.6" goto haxe_ready

:install_haxe
echo ^>^> downloading portable Haxe 4.3.6 (one time)...
call :download_tool haxe "https://github.com/HaxeFoundation/haxe/releases/download/4.3.6/haxe-4.3.6-win64.zip" "!HAXEPATH!" haxe.exe
if errorlevel 1 exit /b 1

:haxe_ready
where haxelib >nul 2>&1
if errorlevel 1 (
	echo ERROR: Portable Haxe archive did not provide haxelib. 1>&2
	exit /b 1
)
if not exist "!NEKOPATH!\neko.exe" (
	echo ^>^> downloading portable Neko 2.3.0 ^(one time^)...
	call :download_tool neko "https://github.com/HaxeFoundation/neko/releases/download/v2-3-0/neko-2.3.0-win64.zip" "!NEKOPATH!" neko.exe
	if errorlevel 1 exit /b 1
)

if not exist "!HAXELIB_PATH!" mkdir "!HAXELIB_PATH!"
if not exist "%USERPROFILE%\.haxelib" (
	>"%USERPROFILE%\.haxelib" echo !HAXELIB_PATH!
)
exit /b 0

:ensure_native_compiler
rem Lime can initialize MSVC itself through the Visual Studio Installer's
rem vswhere.exe, so a normal Command Prompt does not need cl.exe on PATH.
where cl.exe >nul 2>&1
if not errorlevel 1 exit /b 0
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "!VSWHERE!" (
	echo ERROR: MSVC was not found. Install the Visual Studio C++ workload and Windows SDK, then rerun. 1>&2
	exit /b 1
)
"!VSWHERE!" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | findstr /R /C:"." >nul
if errorlevel 1 (
	echo ERROR: Visual Studio is installed, but its C++ x86/x64 tools are missing. 1>&2
	exit /b 1
)
exit /b 0

:download_tool
set "TOOL_NAME=%~1"
set "TOOL_URL=%~2"
set "TOOL_DEST=%~3"
set "TOOL_REQUIRED=%~4"
set "TOOL_TEMP=%TEMP%\disappointing-plus-!TOOL_NAME!-!RANDOM!"
set "DP_TOOL_TEMP=!TOOL_TEMP!"
set "DP_TOOL_URL=!TOOL_URL!"
set "DP_TOOL_DEST=!TOOL_DEST!"
set "DP_TOOL_REQUIRED=!TOOL_REQUIRED!"
set "DP_TOOL_SHA256=%~5"
if not exist "!TOOL_TEMP!" mkdir "!TOOL_TEMP!"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $zip=Join-Path $env:DP_TOOL_TEMP 'tool.zip'; Invoke-WebRequest -UseBasicParsing -Uri $env:DP_TOOL_URL -OutFile $zip; if ($env:DP_TOOL_SHA256) { $actual=(Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant(); if ($actual -ne $env:DP_TOOL_SHA256.ToLowerInvariant()) { throw ('Archive checksum mismatch: expected ' + $env:DP_TOOL_SHA256 + ', found ' + $actual) } }; $unpack=Join-Path $env:DP_TOOL_TEMP 'unpack'; Expand-Archive -Force $zip $unpack; $item=Get-ChildItem -Path $unpack -Filter $env:DP_TOOL_REQUIRED -File -Recurse | Select-Object -First 1; if ($null -eq $item) { throw ('Archive did not contain ' + $env:DP_TOOL_REQUIRED) }; if (Test-Path $env:DP_TOOL_DEST) { Remove-Item -Recurse -Force $env:DP_TOOL_DEST }; New-Item -ItemType Directory -Force $env:DP_TOOL_DEST | Out-Null; Copy-Item -Recurse -Force (Join-Path $item.Directory.FullName '*') $env:DP_TOOL_DEST"
set "TOOL_RESULT=!ERRORLEVEL!"
rmdir /S /Q "!TOOL_TEMP!" >nul 2>&1
if not "!TOOL_RESULT!"=="0" (
	echo ERROR: Could not download or unpack !TOOL_NAME!. Check network access and the URL in run.bat. 1>&2
	exit /b !TOOL_RESULT!
)
if not exist "!TOOL_DEST!\!TOOL_REQUIRED!" (
	echo ERROR: !TOOL_NAME! archive unpacked without !TOOL_REQUIRED!. 1>&2
	exit /b 1
)
exit /b 0

:ensure_astc_decoder
set "ASTCENC_DIR=!TOOLS!\astcenc"
set "ASTCENC_SOURCE=!ASTCENC_DIR!\astcenc-sse2.exe"
set "ASTCENC_VERSION_FILE=!ASTCENC_DIR!\version"
if exist "!ASTCENC_SOURCE!" if exist "!ASTCENC_VERSION_FILE!" (
	findstr /X /C:"3.7" "!ASTCENC_VERSION_FILE!" >nul 2>&1
	if not errorlevel 1 exit /b 0
)
echo ^>^> downloading portable astcenc 3.7 (one time)...
call :download_tool astcenc "https://github.com/ARM-software/astc-encoder/releases/download/3.7/astcenc-3.7-windows-x64.zip" "!ASTCENC_DIR!" astcenc-sse2.exe ecb0e1a5dcbfbaca8a38630e427638380b9d337c266660b39738260e1df5244a
if errorlevel 1 exit /b !ERRORLEVEL!
>"!ASTCENC_VERSION_FILE!" echo 3.7
exit /b !ERRORLEVEL!

:sync_astc_decoder
if not exist "!ASTCENC_SOURCE!" (
	echo ERROR: Portable astcenc decoder is missing: !ASTCENC_SOURCE! 1>&2
	exit /b 1
)
set "ASTCENC_RUNTIME=!ROOT!\!BUILD_ROOT!\windows\bin\tools"
if not exist "!ASTCENC_RUNTIME!" mkdir "!ASTCENC_RUNTIME!"
copy /Y "!ASTCENC_SOURCE!" "!ASTCENC_RUNTIME!\astcenc.exe" >nul
if errorlevel 1 (
	echo ERROR: Could not copy astcenc into the Windows runtime. 1>&2
	exit /b 1
)
copy /Y "!ROOT!\tools\licenses\astcenc-LICENSE.txt" "!ASTCENC_RUNTIME!\astcenc-LICENSE.txt" >nul
if errorlevel 1 (
	echo ERROR: Could not copy the astcenc license into the Windows runtime. 1>&2
	exit /b 1
)
exit /b 0

:ensure_haxelibs
echo ^>^> checking pinned haxelibs in !HAXELIB_PATH!...
call :ensure_lib hxcpp 4.3.2
if errorlevel 1 exit /b 1
call :ensure_lib lime 8.3.2
if errorlevel 1 exit /b 1
call :ensure_lib openfl 9.5.2
if errorlevel 1 exit /b 1
call :ensure_lib flixel 6.1.2
if errorlevel 1 exit /b 1
call :ensure_lib funkin-modchart 1.2.5
if errorlevel 1 exit /b 1
call :ensure_lib flixel-addons 4.0.2
if errorlevel 1 exit /b 1
call :ensure_lib flixel-ui 2.6.5
if errorlevel 1 exit /b 1
call :ensure_lib flixel-animate 1.5.0
if errorlevel 1 exit /b 1
call :ensure_lib hscript 2.5.0
if errorlevel 1 exit /b 1
call :ensure_lib hscript-iris 1.1.3
if errorlevel 1 exit /b 1
call :ensure_lib hxvlc 2.3.1
if errorlevel 1 exit /b 1
call :ensure_lib tjson
if errorlevel 1 exit /b 1
call :ensure_git_lib hscript-ex https://github.com/ianharrigan/hscript-ex
if errorlevel 1 exit /b 1
call :ensure_git_lib discord_rpc https://github.com/Aidan63/linc_discord-rpc
if errorlevel 1 exit /b 1
exit /b 0

:ensure_shared_haxelib_patches
rem Match the source-safe setup used by run.sh before compiling on Windows.
call :ensure_python
if errorlevel 1 exit /b 1
call :run_python_script tools\patch_hxcpp_large_free.py
if errorlevel 1 exit /b 1
call :run_python_script tools\install_codename_3d.py
if errorlevel 1 exit /b 1
call :run_python_script tools\patch_openfl_context3d_readback.py
if errorlevel 1 exit /b 1
call :run_python_script tools\patch_openfl_shader_version.py
if errorlevel 1 exit /b 1
call :run_python_script tools\patch_hscript_compat.py
if errorlevel 1 exit /b 1
call :run_python_script tools\patch_hscript_ex_owner_scope.py
if errorlevel 1 exit /b 1
exit /b 0

:ensure_python
where py.exe >nul 2>&1
if not errorlevel 1 (
	set "PYTHON_COMMAND=py -3"
	exit /b 0
)
where python.exe >nul 2>&1
if not errorlevel 1 (
	set "PYTHON_COMMAND=python"
	exit /b 0
)
echo ERROR: Python 3 is required to apply the pinned shared library patches. 1>&2
exit /b 1

:run_python_script
call !PYTHON_COMMAND! "!ROOT!\%~1"
if errorlevel 1 (
	echo ERROR: Shared library setup failed: %~1 1>&2
	exit /b 1
)
exit /b 0

:ensure_lib
set "LIB_NAME=%~1"
set "LIB_VERSION=%~2"
if defined LIB_VERSION (
	haxelib list 2>nul | findstr /R /B /C:"!LIB_NAME!:.*\[!LIB_VERSION!\]" >nul
) else (
	haxelib list 2>nul | findstr /R /B /C:"!LIB_NAME!:" >nul
)
if not errorlevel 1 exit /b 0
if defined LIB_VERSION (
	echo ^>^> installing !LIB_NAME! !LIB_VERSION!...
	call haxelib install "!LIB_NAME!" "!LIB_VERSION!" --always
	if errorlevel 1 exit /b 1
	call haxelib set "!LIB_NAME!" "!LIB_VERSION!" >nul 2>&1
) else (
	echo ^>^> installing !LIB_NAME!...
	call haxelib install "!LIB_NAME!" --always
	if errorlevel 1 exit /b 1
)
exit /b 0

:ensure_git_lib
set "LIB_NAME=%~1"
set "LIB_URL=%~2"
haxelib list 2>nul | findstr /R /B /C:"!LIB_NAME!:" >nul
if not errorlevel 1 exit /b 0
where git.exe >nul 2>&1
if errorlevel 1 (
	echo ERROR: Git is required to install !LIB_NAME!. Install Git for Windows and rerun. 1>&2
	exit /b 1
)
echo ^>^> installing !LIB_NAME! from !LIB_URL!...
call haxelib git "!LIB_NAME!" "!LIB_URL!" --always
if errorlevel 1 exit /b 1
exit /b 0

:patch_haxelibs
rem Keep the native empty-frame crash fix in parity with run.sh.  The
rem rapidjson workaround is Linux/gcc-specific and is intentionally omitted
rem from the MSVC build path.
set "FLIXEL_SOURCE=!HAXELIB_PATH!\flixel\6,1,2\flixel\FlxSprite.hx"
if not exist "!FLIXEL_SOURCE!" (
	echo ERROR: Pinned flixel 6.1.2 source was not found at !FLIXEL_SOURCE!. 1>&2
	exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "!ROOT!\tools\patch_flixel_fallback.ps1" -Path "!FLIXEL_SOURCE!"
if errorlevel 1 (
	echo ERROR: Could not apply the flixel empty-frame fallback patch. 1>&2
	exit /b 1
)
set "MODCHART_UTIL=!HAXELIB_PATH!\funkin-modchart\1,2,5\modchart\backend\util\ModchartUtil.hx"
if not exist "!MODCHART_UTIL!" (
	echo ERROR: Pinned funkin-modchart 1.2.5 source was not found at !MODCHART_UTIL!. 1>&2
	exit /b 1
)
call !PYTHON_COMMAND! "!ROOT!\tools\patch_funkin_modchart_uv.py" "!MODCHART_UTIL!"
if errorlevel 1 (
	echo ERROR: Could not apply the funkin-modchart hold-UV and camera patch. 1>&2
	exit /b 1
)
exit /b 0

:ensure_asset_scaffolding
rem Lime errors when a declared <assets path="..."> mount point is absent.
for %%D in (images videos data shaders music songs sounds module discord fonts scripts) do (
	if not exist "!ROOT!\assets\%%D\" mkdir "!ROOT!\assets\%%D"
)
exit /b 0

:usage_error
echo. 1>&2
call :usage 1>&2
exit /b 2

:usage
echo Usage: run.bat [debug^|release^|build^|rebuild^|nobuild^|server^|build32^|rebuild32]
echo.
echo Default builds and launches a 64-bit release Windows executable.
echo Native Windows requires Haxe 4.3.x, the pinned haxelibs, and a Visual
echo Studio C++ toolchain supported by hxcpp. Portable Haxe and Neko are
echo downloaded into .tools; no Wine cross-compiler is used.
exit /b 0
