"""Real decoder checks on a private, never activated Windows desktop.

Uses only a disposable extracted runtime below the checkout tmp directory.
Never changes the donor clip or the playing install. No desktop activation.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes as w
import os
import shutil
import subprocess

import argparse
import hashlib
import json
import sys
import time

parser = argparse.ArgumentParser(description='Run the legacy video decoder contract on a private Windows desktop.')
parser.add_argument('--runtime', required=True, type=Path, help='Disposable extracted runtime below this checkout tmp directory')
parser.add_argument('--clip', required=True, type=Path, help='Read-only video fixture lasting at least 5 and at most 30 seconds')
parser.add_argument('--fps', type=int, choices=(0,60), default=60)
args = parser.parse_args()
r = Path(__file__).resolve().parents[1]
runtime = args.runtime.resolve()
if os.name != 'nt': raise SystemExit('This private-desktop runner requires Windows')
if not runtime.is_relative_to((r/'tmp').resolve()) or not (runtime/'assets/data/options.json').is_file():
    raise SystemExit('Runtime must be an extracted, disposable game below this checkout tmp directory')
clip=args.clip.resolve()
if not clip.is_file(): raise SystemExit('Video fixture does not exist')
for name in ('Funkin.exe','lime.ndll'):
    destination=runtime/name
    if not destination.resolve().is_relative_to(runtime): raise SystemExit('Runtime link escapes fixture directory')
    shutil.copyfile(r/'export/release/windows/bin'/name,destination)
for target in (runtime/'tmp',runtime/'assets/data/options.json'):
    if not target.resolve().is_relative_to(runtime): raise SystemExit('Fixture path escapes disposable runtime')
(runtime/'tmp').mkdir(exist_ok=True)
for owner in ('generated-video-a','generated-video-b'):
    dest=runtime/'assets/imported_mods'/owner/'videos/clip.mp4'
    if not dest.resolve().is_relative_to(runtime): raise SystemExit('Generated owner link escapes fixture directory')
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(clip,dest)

class STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR),
                ('lpTitle', w.LPWSTR), ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD), ('dwXCountChars', w.DWORD),
                ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', ctypes.POINTER(w.BYTE)), ('hStdInput', w.HANDLE),
                ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]

class PROCESSINFO(ctypes.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]

u = ctypes.WinDLL('user32', use_last_error=True)
k = ctypes.WinDLL('kernel32', use_last_error=True)
u.CreateDesktopW.argtypes = [w.LPCWSTR, w.LPCWSTR, ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.c_void_p]
u.CreateDesktopW.restype = w.HANDLE
u.CloseDesktop.argtypes = [w.HANDLE]
k.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                            w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                            ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESSINFO)]
k.CreateProcessW.restype = w.BOOL
k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
k.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
k.CloseHandle.argtypes = [w.HANDLE]
desktop_name = 'CammieVideoComponent_' + str(os.getpid())
desk = u.CreateDesktopW(desktop_name, None, None, 0, 0x10000000, None)
if not desk:
    raise ctypes.WinError(ctypes.get_last_error())
si = STARTUPINFO(); si.cb = ctypes.sizeof(si); si.lpDesktop = desktop_name
pi = PROCESSINFO()
import msvcrt
fps=args.fps
options=runtime/'assets/data/options.json'
original_options=options.read_bytes()
config=json.loads(options.read_text()); config['fpsCap']=max(60,fps); config['unlimitedFPS']=(fps==0); config['backgroundDim']=0; config['highwayDim']=0
options.write_text(json.dumps(config))
log_path=runtime/f'tmp/legacy-video-component-{fps}.jsonl'
command = [str(runtime / 'Funkin.exe'), '--smoke-runtime-root', str(runtime),
           '--smoke-freeplay', '--smoke-freeplay-wait-ms', '120000',
           '--smoke-duration-ms', '90000', '--smoke-log', str(log_path)]
os.environ['CAMMIE_LEGACY_VIDEO_SMOKE']='1'
os.environ['CAMMIE_SMOKE_SAVE_ROOT']='tmp/legacy-video-component-save'
output=(runtime/f'tmp/legacy-video-component-{fps}.process.log').open('w')
null_input=open('NUL','r')
for file in (output,null_input): os.set_handle_inheritable(msvcrt.get_osfhandle(file.fileno()),True)
si.dwFlags=0x100
si.hStdInput=msvcrt.get_osfhandle(null_input.fileno())
si.hStdOutput=si.hStdError=msvcrt.get_osfhandle(output.fileno())

os.environ['CAMMIE_IMPORT_REFRESH_TRACE']='1'
try:
    if not k.CreateProcessW(None, ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),
                            None, None, True, 0x08000000, None, str(runtime),
                            ctypes.byref(si), ctypes.byref(pi)):
        raise ctypes.WinError(ctypes.get_last_error())
    print('Muted native gameplay on private desktop; PID', pi.dwProcessId, flush=True)
    deadline=time.monotonic()+180
    while k.WaitForSingleObject(pi.hProcess,2000)!=0:
        if time.monotonic()>deadline:
            k.TerminateProcess(pi.hProcess,1)
            k.WaitForSingleObject(pi.hProcess,5000)
            raise TimeoutError('Private video probe exceeded deadline')
    code = w.DWORD(); k.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    print('EXIT', code.value)
    if code.value != 0: raise RuntimeError('Native component failed: '+str(code.value))
    events=[json.loads(line.split('|',1)[1]) for line in log_path.read_text().splitlines() if line.startswith('RUNTIME_SMOKE|')]
    verified=[event for event in events if event.get('event')=='legacy_video_native_verified']
    if len(verified)!=1 or not any(event.get('event')=='success' for event in events):
        raise RuntimeError('Native process did not complete the requested lifecycle contract')
    proof={'requestedFPS':fps,'executableSHA256':hashlib.sha256((runtime/'Funkin.exe').read_bytes()).hexdigest(),
           'clipSHA256':hashlib.sha256(clip.read_bytes()).hexdigest(),'verified':verified[0]}
    proof_path=runtime/f'tmp/legacy-video-component-{fps}.proof.json'
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof,indent=2))

finally:
    if pi.hProcess and k.WaitForSingleObject(pi.hProcess,0)!=0:
        k.TerminateProcess(pi.hProcess,1)
        k.WaitForSingleObject(pi.hProcess,5000)
    options.write_bytes(original_options)
    output.close(); null_input.close()
    if pi.hThread: k.CloseHandle(pi.hThread)
    if pi.hProcess: k.CloseHandle(pi.hProcess)
    u.CloseDesktop(desk)
