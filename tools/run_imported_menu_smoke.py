#!/usr/bin/env python3
"""Real-converter imported menu acceptance on a private Windows desktop.

--prepare copies metadata/code and hardlinks immutable native media from an
already-private complete runtime. --run starts only the explicit built binary,
imports authored fixture inputs, then verifies the action plan at 60/unlimited.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_root(path):
    result=path.resolve()
    if not result.is_relative_to(ROOT/'tmp') or result.is_symlink():raise ValueError('Use a physical private root below project tmp')
    return result

def prepare(seed,output):
    seed=check_root(seed);output=check_root(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Prepare requires a new output directory')
    runtime=output/'runtime';runtime.mkdir(parents=True)
    # Code, metadata, saves and caches get private bytes. Borrow only immutable
    # artwork/audio/fonts; imports publish new output through private paths.
    mutable={'.json','.jsonc','.xml','.hx','.hxc','.hscript','.hxs','.lua','.txt','.exe','.ndll','.dll','.dat','.sol'}
    for folder,dirs,files in os.walk(seed):
        rel=Path(folder).relative_to(seed)
        dirs[:]=[d for d in dirs if d not in {'import-cache','tmp','xdg-data','xdg-config','xdg-cache','scratch'}]
        target=runtime/rel;target.mkdir(parents=True,exist_ok=True)
        for name in files:
            source=Path(folder)/name;destination=target/name
            if source.is_symlink():raise ValueError('Private seed contains linked content: '+str(source))
            if source.suffix.lower() in mutable or rel.parts[:2]==('assets','data'):shutil.copyfile(source,destination)
            else:os.link(source,destination)
    (runtime/'assets/imported_mods').mkdir(parents=True,exist_ok=True)
    (runtime/'tmp').mkdir()
    # Fresh registry excludes the seed's previous test chart.
    registry=runtime/'assets/data/freeplaySongJson.jsonc'
    registry.write_text(json.dumps([{'name':'All','songs':[{'name':'Random-Song','character':'bf','week':0}]}]))
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_imported_menu_fixtures.py')],check=True,cwd=ROOT)
    (output/'prepared.json').write_text(json.dumps({'runtime':str(runtime),'fixtures':str(ROOT/'tmp/v34-menu-fixtures')},indent=2))
    print(output,flush=True)

class StartupInfo(ctypes.Structure):
    _fields_=[('cb',w.DWORD),('lpReserved',w.LPWSTR),('lpDesktop',w.LPWSTR),('lpTitle',w.LPWSTR),('dwX',w.DWORD),('dwY',w.DWORD),('dwXSize',w.DWORD),('dwYSize',w.DWORD),('dwXCountChars',w.DWORD),('dwYCountChars',w.DWORD),('dwFillAttribute',w.DWORD),('dwFlags',w.DWORD),('wShowWindow',w.WORD),('cbReserved2',w.WORD),('lpReserved2',ctypes.POINTER(w.BYTE)),('hStdInput',w.HANDLE),('hStdOutput',w.HANDLE),('hStdError',w.HANDLE)]
class ProcessInfo(ctypes.Structure):
    _fields_=[('hProcess',w.HANDLE),('hThread',w.HANDLE),('dwProcessId',w.DWORD),('dwThreadId',w.DWORD)]

def run(output,binary):
    if os.name!='nt':raise ValueError('This runner requires native Windows private desktops')
    import msvcrt
    output=check_root(output);metadata=json.loads((output/'prepared.json').read_text());runtime=check_root(Path(metadata['runtime']));fixtures=check_root(Path(metadata['fixtures']))
    for name in ['Funkin.exe','lime.ndll']:shutil.copyfile(binary.parent/name,runtime/name)
    source_before={str(p.relative_to(fixtures)):digest(p) for p in fixtures.rglob('*') if p.is_file()}
    u=ctypes.WinDLL('user32',use_last_error=True);k=ctypes.WinDLL('kernel32',use_last_error=True)
    u.CreateDesktopW.argtypes=[w.LPCWSTR,w.LPCWSTR,ctypes.c_void_p,w.DWORD,w.DWORD,ctypes.c_void_p];u.CreateDesktopW.restype=w.HANDLE;u.CloseDesktop.argtypes=[w.HANDLE]
    k.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,w.BOOL,w.DWORD,ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(StartupInfo),ctypes.POINTER(ProcessInfo)];k.CreateProcessW.restype=w.BOOL
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.TerminateProcess.argtypes=[w.HANDLE,w.UINT];k.CloseHandle.argtypes=[w.HANDLE]
    desktop_name='CammieMenuAcceptance_'+str(os.getpid());desktop=u.CreateDesktopW(desktop_name,None,None,0,0x10000000,None)
    if not desktop:raise ctypes.WinError(ctypes.get_last_error())
    # CreateDesktop is never activated or switched onto the user's desktop.
    previous=dict(os.environ)
    os.environ['CAMMIE_SMOKE_SAVE_ROOT']='tmp/private-menu-save'
    for key in ['CAMMIE_MENU_SMOKE_PLAN','CAMMIE_LIBRARY_REMOVAL_SMOKE','CAMMIE_LIBRARY_REMOVAL_RESTART_SMOKE','CAMMIE_LIBRARY_LIFECYCLE_SMOKE','CAMMIE_IMPORT_UI_SMOKE','CAMMIE_NV_FAMILY_SMOKE','CAMMIE_OWNER_LIBRARY_SMOKE']:os.environ.pop(key,None)
    def launch(label,flags,timeout=180):
        log=output/(label+'.process.log');stream=log.open('w',encoding='utf-8');input_file=open('NUL','r');si=StartupInfo();si.cb=ctypes.sizeof(si);si.lpDesktop=desktop_name;si.dwFlags=0x100;pi=ProcessInfo()
        for f in [stream,input_file]:os.set_handle_inheritable(msvcrt.get_osfhandle(f.fileno()),True)
        si.hStdInput=msvcrt.get_osfhandle(input_file.fileno());si.hStdOutput=si.hStdError=msvcrt.get_osfhandle(stream.fileno())
        command=[str(runtime/'Funkin.exe'),'--smoke-runtime-root',str(runtime),*flags]
        try:
            if not k.CreateProcessW(None,ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),None,None,True,0x08000000,None,str(runtime),ctypes.byref(si),ctypes.byref(pi)):raise ctypes.WinError(ctypes.get_last_error())
            print(label+' private muted PID '+str(pi.dwProcessId),flush=True);deadline=time.monotonic()+timeout
            while k.WaitForSingleObject(pi.hProcess,2000)!=0:
                if time.monotonic()>deadline:
                    k.TerminateProcess(pi.hProcess,1);k.WaitForSingleObject(pi.hProcess,5000);raise TimeoutError(label)
            code=w.DWORD();k.GetExitCodeProcess(pi.hProcess,ctypes.byref(code));stream.flush()
            print(label+' exit '+str(code.value),flush=True)
            if code.value:raise RuntimeError(log.read_text(errors='replace')[-10000:])
            return log.read_text(errors='replace')
        finally:
            if pi.hThread:k.CloseHandle(pi.hThread)
            if pi.hProcess:k.CloseHandle(pi.hProcess)
            stream.close();input_file.close()
    try:
        for engine in ['Psych Engine','Nightmare Vision']:
            label='import-'+engine.split()[0].lower();marker=runtime/('tmp/'+label+'.jsonl')
            launch(label,['--smoke-import-source',str(fixtures/engine),'--smoke-import-type',engine,'--smoke-import-timeout-ms','150000','--smoke-import-log',str(marker)],200)
        subprocess.run([sys.executable,str(ROOT/'tools/prepare_imported_menu_fixtures.py'),'--runtime-root',str(runtime)],cwd=ROOT,check=True)
        os.environ['CAMMIE_MENU_SMOKE_PLAN']='tmp/menu-plan.json';proofs=[]
        for fps in [60,0]:
            options=runtime/'assets/data/options.json';data=json.loads(options.read_text());data['fpsCap']=fps;data['unlimitedFPS']=fps==0;data['skipModifierMenu']=True;data['autoPause']=False;options.write_text(json.dumps(data));before=digest(options)
            process=launch('menu-'+str(fps),['--smoke-freeplay','--smoke-duration-ms','180000','--smoke-pacing-only','--smoke-log',str(runtime/('tmp/menu-'+str(fps)+'.jsonl'))],200)
            markers=[json.loads(line.split('|',1)[1]) for line in process.splitlines() if line.startswith('MENU_SMOKE|')]
            complete=[m for m in markers if m['event']=='complete']
            if len(complete)!=1:raise RuntimeError('Missing complete marker: '+process[-12000:])
            if digest(options)!=before:raise RuntimeError('Private options changed')
            proofs.append({'fps':fps,**complete[0]})
        if source_before!={str(p.relative_to(fixtures)):digest(p) for p in fixtures.rglob('*') if p.is_file()}:raise RuntimeError('Authored source fixture bytes changed')
        proof={'binarySha256':digest(runtime/'Funkin.exe'),'runtime':str(runtime),'sourceUnchanged':True,'fixtureSourceSha256':source_before,'productionSourceSha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'source').glob('*.hx'))},'runs':proofs}
        (output/'native-proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
    finally:
        os.environ.clear();os.environ.update(previous);u.CloseDesktop(desktop)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'tmp/v34-menu-native');p.add_argument('--seed-runtime',type=Path);p.add_argument('--prepare',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--binary',type=Path,default=ROOT/'export/release/windows/bin/Funkin.exe');a=p.parse_args()
    if a.prepare:
        if not a.seed_runtime:p.error('--prepare requires --seed-runtime')
        prepare(a.seed_runtime,a.output)
    if a.run:run(a.output,a.binary.resolve())
    if not a.prepare and not a.run:p.error('Choose --prepare or --run')
if __name__=='__main__':main()
