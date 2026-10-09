package;

/** Disposable source speed/position transactions on the real native state. */
@:access(PlayState)
class RuntimeSmokeLegacyScrollStorage {
	static function check(ok:Bool,message:String):Void if(!ok)throw message;
	public static function verify(state:PlayState,api:NightmareVisionScriptInterp):Void {
		var oldSpeed=PlayState.daScrollSpeed;var oldOffset=state.noteKillOffset;var oldGenerated=state.generatedMusic;
		var oldNotes=state.notes;var oldPending=state.unspawnNotes;
		var points=[state.boyfriendPosition,state.dadPosition,state.gfPosition];
		var coordinates=[for(p in points)[p.x,p.y]];
		var group=state.gfGroup;var groupX=group.x;var groupY=group.y;
		var notes=new flixel.group.FlxGroup.FlxTypedGroup<Note>();var note:Note=null;
		var restore=function(){
			state.notes=oldNotes;state.unspawnNotes=oldPending;state.generatedMusic=oldGenerated;
			PlayState.daScrollSpeed=oldSpeed;state.noteKillOffset=oldOffset;
			for(i in 0...points.length)points[i].set(coordinates[i][0],coordinates[i][1]);
			notes.clear();notes.destroy();if(note!=null)note.destroy();
		};
		try {
			note=new Note(100,0);note.isSustainNote=true;note.nightmareVisionLegacyGeometry=true;
			note.animation.add('__speed_body',[0],1,false);note.animation.play('__speed_body');
			note.scale.y=10;note.baseScaleY=10;notes.add(note);notes.members.push(null);
			state.notes=notes;state.unspawnNotes=[note];state.generatedMusic=true;PlayState.daScrollSpeed=2;
			api.execute(new NightmareVisionScriptParser().parseString('songSpeed=4;','__speed_storage'));
			check(note.scale.y==40&&note.baseScaleY==40&&state.noteKillOffset==87.5,'Native speed queues/kill offset');
			note.noteData=5;
			api.execute(new NightmareVisionScriptParser().parseString('Reflect.setProperty(game,"songSpeed",4);','__speed_storage'));
			check(Math.abs(note.scale.y-15.625)<0.00001,'Same-speed source wider-lane resizing');
			state.generatedMusic=false;
			api.execute(new NightmareVisionScriptParser().parseString('game.songSpeed=8;GF_X=412;game.GF_Y=151;Reflect.setProperty(game,"BF_X",791);PlayState.DAD_Y=108;','__position_storage'));
			check(note.scale.y==15.625&&state.songSpeed==8&&state.noteKillOffset==43.75,'Generation gate and reflected speed');
			check(state.gfPosition.x==412&&state.gfPosition.y==151&&state.boyfriendPosition.x==791&&state.dadPosition.y==108,'Shared source position aliases');
			check(group.x==groupX&&group.y==groupY,'Baseline writes moved an existing group');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_scroll_storage_native_verified',{queueOccurrences:true,sameSpeed:true,generationGate:true,killOffset:true,scriptAndReflection:true,positionAliases:true,groupUnmoved:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}
}
