"""Prepare a generated mod and isolated packaged runtime for removal UI smoke checks."""
from pathlib import Path, PurePosixPath
import argparse
import json
import shutil
import uuid
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def prepare(fps):
    private=ROOT/'tmp'/'v34-removal-smoke'/uuid.uuid4().hex[:12]
    private.mkdir(parents=True,exist_ok=False)
    runtime=private/'runtime';runtime.mkdir()
    archive=ROOT/'dist'/'CammieEngine-v0.0.33-windows-x64.zip'
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            parts=PurePosixPath(info.filename).parts
            if not parts or parts[0]!='CammieEngine-windows-x64' or '..' in parts:raise ValueError('Invalid package path')
            if len(parts)==1:continue
            target=runtime.joinpath(*parts[1:])
            if runtime.resolve() not in target.resolve().parents:raise ValueError('Package path escaped runtime')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with package.open(info) as source,target.open('xb') as output:shutil.copyfileobj(source,output)
    options=runtime/'assets/data/options.json'
    config=json.loads(options.read_text(encoding='utf-8-sig'));config.update(fpsCap=60,unlimitedFPS=fps==0,autoPause=False,skipModifierMenu=True)
    options.write_text(json.dumps(config),encoding='utf-8')
    source=private/'generated-source';song='removal-fixture-song'
    data=source/'assets/data'/song;data.mkdir(parents=True)
    (source/'assets/songs'/song).mkdir(parents=True)
    chart={'song':{'song':song,'bpm':100,'speed':1,'needsVoices':False,'player1':'bf','player2':'dad','gfVersion':'gf','stage':'stage','notes':[{'sectionNotes':[[5000,0,0],[6000,4,0]],'mustHitSection':True,'lengthInSteps':16,'bpm':100,'changeBPM':False}]}}
    for suffix in ('','-hard'):(data/(song+suffix+'.json')).write_text(json.dumps(chart),encoding='utf-8')
    (source/'pack.json').write_text(json.dumps({'id':'codex-generated-removal-fixture','name':'Removal Fixture'}),encoding='utf-8')
    (source/'source/psychlua').mkdir(parents=True)
    (source/'source/psychlua/RemovalMarker.hx').write_text('class RemovalMarker {}\n',encoding='utf-8')
    shutil.copyfile(runtime/'assets/songs/bopeebo/Bopeebo_Inst.ogg',source/'assets/songs'/song/'Inst.ogg')
    request={'kind':'generated-library-removal','install':str(runtime).replace('\\','/')+'/','source':str(source).replace('\\','/')}
    (runtime/'tmp').mkdir(exist_ok=True)
    (runtime/'tmp/library-removal-request.json').write_text(json.dumps(request),encoding='utf-8')
    metadata={'private':str(private),'runtime':str(runtime),'source':str(source),'fps':fps,'baseline':str(archive)}
    (private/'prepared.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return metadata
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fps',type=int,choices=(0,60),default=60);args=parser.parse_args();print(json.dumps(prepare(args.fps)))
