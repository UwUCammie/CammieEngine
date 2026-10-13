#!/usr/bin/env python3
"""Write authored acceptance packages for the real native importer.

Inputs and plans are project-local fixtures, never changes to example donors.
Import each engine directory with prepare_runtime_smoke_fixture.py; then call
this script with --runtime-root to build a plan from the real generated receipts.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
ROOT=Path(__file__).resolve().parents[1]

def short_fixture_ogg(source, target, seconds=8):
    """End a project-owned Vorbis stream on a complete audio page, preserving valid CRC."""
    data=source.read_bytes();offset=0;rate=None;last_end=None
    while offset<len(data):
        if data[offset:offset+4]!=b'OggS': raise ValueError('Invalid source Ogg page')
        count=data[offset+26];laces=data[offset+27:offset+27+count]
        end=offset+27+count+sum(laces)
        body=data[offset+27+count:end]
        if body.startswith(b'\x01vorbis'):rate=struct.unpack_from('<I',body,12)[0]
        granule=struct.unpack_from('<Q',data,offset+6)[0]
        if rate and granule!=0xffffffffffffffff and granule>=seconds*rate and laces[-1]<255:
            page=bytearray(data[offset:end]);page[5]|=4;page[22:26]=bytes(4);crc=0
            for byte in page:
                crc^=byte<<24
                for _ in range(8):crc=((crc<<1)^0x04c11db7 if crc&0x80000000 else crc<<1)&0xffffffff
            struct.pack_into('<I',page,22,crc)
            target.write_bytes(data[:offset]+page)
            return {'sampleRate':rate,'samples':granule,'seconds':granule/rate}
        offset=end
    raise ValueError('No complete audio page for short instrumental fixture')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/v34-menu-fixtures')
    parser.add_argument('--runtime-root',type=Path)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'tmp'): raise ValueError('Fixtures must be below project tmp')
    if args.runtime_root:
        runtime=args.runtime_root.resolve()
        if not runtime.is_relative_to(ROOT/'tmp'): raise ValueError('Use a private runtime below project tmp')
        owners={}
        for receipt in (runtime/'assets/data').glob('*/importProvenance.json'):
            data=json.loads(receipt.read_text(encoding='utf-8'))
            label=data.get('modName','')
            if label.startswith('Menu acceptance '): owners[label]=data['sourceOwner']
        plan=[]
        for engine in ['Psych Engine','Nightmare Vision']:
            prefix='psych:' if engine=='Psych Engine' else 'nv:'
            owner=owners['Menu acceptance '+engine+' full']
            plan += [dict(state='CodenameImportedModsState',action='launch',launchOwner=owner),
                     dict(state=prefix+'TitleState',owner=owner,action='key',key='enter'),
                     dict(state=prefix+'MainMenuState',owner=owner,action='key',key='enter'),
                     dict(state=prefix+'FreeplayState',owner=owner,action='key',key='enter'),
                     dict(state='PlayState',owner=owner,action='key',key='escape'),
                     dict(state='PlayState',substate='PauseSubState',owner=owner,action='key',key='enter'),
                     dict(state='PlayState',substate='',owner=owner,action='game-over'),
                     dict(state='PlayState',substate='GameOverSubstate',owner=owner,action='key',key='enter'),
                     dict(state='PlayState',substate='',retry=True,owner=owner,action='game-over'),
                     dict(state='PlayState',substate='GameOverSubstate',owner=owner,action='key',key='escape'),
                     dict(state=prefix+'FreeplayState',owner=owner,action='key',key='enter'),
                     dict(state='PlayState',substate='',owner=owner,action='complete-song'),
                     dict(state='PlayState',substate='',resultProvider=True,owner=owner,completed=True,action='key',key='enter'),
                     dict(state=prefix+'FreeplayState',owner=owner,action='key',key='f10')]
            for kind,entry in [('main-only',prefix+'MainMenuState'),('no-freeplay',prefix+'TitleState'),('title-only','FreeplayState'),('unsupported','FreeplayState')]:
                owner=owners['Menu acceptance '+engine+' '+kind]
                plan += [dict(state='CodenameImportedModsState',action='launch',launchOwner=owner)]
                if kind=='unsupported' and engine=='Psych Engine':
                    plan += [dict(state='CodenameImportedModsState',diagnostic=True,action='key',key='f')]
                if kind=='unsupported' and engine=='Nightmare Vision':
                    plan += [dict(state=prefix+'TitleState',owner=owner,action='key',key='enter'),
                             dict(state='NightmareVisionFallbackState',owner=owner,action='key',key='enter')]

                if kind in ('main-only','no-freeplay'):
                    if kind=='no-freeplay': plan += [dict(state=entry,owner=owner,action='key',key='enter')]
                    plan += [dict(state=prefix+'MainMenuState',owner=owner,action='key',key='enter')]
                    if kind=='main-only':
                        plan += [dict(state=prefix+'FreeplayState',owner=owner,action='key',key='f10')]
                        continue
                plan += [dict(state='FreeplayState',owner=owner,action='key',key='escape')]
        # Re-enter an earlier engine owner after NV teardown to verify reverse isolation.
        owner=owners['Menu acceptance Psych Engine full']
        plan += [dict(state='CodenameImportedModsState',action='launch',launchOwner=owner),
                 dict(state='psych:TitleState',owner=owner,action='key',key='enter'),
                 dict(state='psych:MainMenuState',owner=owner,action='key',key='enter'),
                 dict(state='psych:FreeplayState',owner=owner,action='key',key='f10')]
        plan.append(dict(state='CodenameImportedModsState',action='check'))
        for step in plan: step.setdefault('substate','')
        target=runtime/'tmp/menu-plan.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(plan,indent=2),encoding='utf-8')
        print(target);return
    audio=ROOT/'assets/music/title.ogg'
    for engine in ['Psych Engine','Nightmare Vision']:
        for kind in ['full','main-only','no-freeplay','title-only','unsupported']:
            package=output/engine/kind
            for folder in ['data/flow-song','songs/flow-song','scripts/states','sounds']:(package/folder).mkdir(parents=True,exist_ok=True)
            label='Menu acceptance '+engine+' '+kind
            (package/'pack.json').write_text(json.dumps({'name':label,'description':'Native menu acceptance fixture'}),encoding='utf-8')
            chart={'song':{'song':'flow-song','bpm':120,'speed':1,'needsVoices':False,'player1':'bf','player2':'dad','gfVersion':'gf','stage':'stage','notes':[{'mustHitSection':True,'sectionNotes':[[10000,0,0]],'lengthInSteps':16,'typeOfSection':0}]}}
            (package/'data/flow-song/flow-song.json').write_text(json.dumps(chart),encoding='utf-8')
            short_fixture_ogg(audio,package/'songs/flow-song/Inst.ogg')
            shutil.copyfile(audio,package/'sounds/menu.ogg')
            states=['TitleState','MainMenuState','FreeplayState']
            if kind=='main-only':states.remove('TitleState')
            if kind=='no-freeplay':states.remove('FreeplayState')
            if kind=='title-only':states=['TitleState']
            for name in states:
                target='MainMenuState' if name=='TitleState' else 'FreeplayState' if name=='MainMenuState' else 'PlayState'
                launch='PlayState.SONG = Song.loadFromJson("flow-song", "flow-song");' if name=='FreeplayState' else ''
                update='if (controls.ACCEPT) {'+launch+' FlxG.switchState(new '+target+'());}'
                if kind=='unsupported' and name=='MainMenuState':update='unsupportedDonorApi();'
                if engine=='Psych Engine':
                    resources='new FlxTimer().start(0.1, function(timer) {}, 0); FlxTween.tween(label, {alpha:0.5}, 30); soundPlaySafe("sounds/menu.ogg", 0);'
                    source='class '+name+' extends MusicBeatState {override function create():Void {super.create(); var label = new FlxText(40,40,1000,"'+label+' '+name+'",24); add(label); '+resources+'} override function update(elapsed:Float):Void {'+update+' super.update(elapsed);}}'
                else:
                    source='import flixel.util.FlxTimer; import flixel.tweens.FlxTween; import flixel.text.FlxText; import funkin.states.MainMenuState; import funkin.states.FreeplayState; import funkin.states.PlayState; import funkin.backend.Song; function onCreate() {var label=new FlxText(40,40,1000,"'+label+' '+name+'",24); add(label); new FlxTimer().start(0.1,function(timer){},0); FlxTween.tween(label,{alpha:0.5},30); FlxG.sound.play(Paths.sound("menu"),0,true);} function onUpdate(elapsed) {'+update+'}'
                (package/'scripts/states'/(name+'.hx')).write_text(source,encoding='utf-8')
            if engine=='Nightmare Vision':
                (package/'meta.json').write_text(json.dumps({'name':label,'stateRedirects':{name:name for name in states}}),encoding='utf-8')
    print(output)
if __name__=='__main__': main()
