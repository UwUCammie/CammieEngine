"""Psych and Nightmare Vision section focus come from one formula; only the opponent base differs."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(v:Bool,m:String) if(!v)throw m;
 static function near(a:Float,b:Float,m:String) if(Math.abs(a-b)>0.000001)throw m+': '+a+' != '+b;
 static function pair(role:String,base:Float):Array<Float>
  return PsychCharacterPosition.effectiveCameraOffset(role,[10,20],[5,6],0,0,base);
 static function main() {
  var psych=SourceCameraFollowPointMath.PSYCH_OPPONENT_BASE_X;var nv=SourceCameraFollowPointMath.NIGHTMARE_OPPONENT_BASE_X;
  var dad=pair('dad',psych);near(dad[0],165,'Psych dad x');near(dad[1],-74,'Psych dad y');
  dad=pair('dad',nv);near(dad[0],115,'NV dad x');near(dad[1],-74,'NV dad y');
  for(base in [psych,nv]) {
   var bf=pair('boyfriend',base);near(bf[0],-105,'bf x');near(bf[1],-74,'bf y');
   var gf=pair('gf',base);near(gf[0],15,'gf x');near(gf[1],26,'gf y');
  }
  check(PsychCharacterPosition.effectiveCameraOffset('dad',[10,20],[5,6]).join(',')=='165,-74','Psych base stays the default');
  var follow=PsychCharacterPosition.effectiveCameraOffset(' BF ',[10,20],null,3,4);near(follow[0],-107,'follow delta x');near(follow[1],-76,'follow delta y');
  // The hand-written Nightmare Vision helper this formula replaced.
  for(player in [true,false])for(cx in [-200.,0,7.5,110])for(cy in [-20.,0,6])for(sx in [-30.,0,21])for(sy in [-12.,0,22]) {
   var oldX=player?-(100+cx)+sx:100+cx+sx;var oldY=-100+cy+sy;
   var side=player?SourceCameraFollowPointMath.PLAYER:SourceCameraFollowPointMath.OPPONENT;
   near(SourceCameraFollowPointMath.focusOffsetX(side,cx,sx,nv),oldX,'NV x '+player+' '+cx+' '+sx);
   near(SourceCameraFollowPointMath.focusOffsetY(side,cy,sy),oldY,'NV y '+cy+' '+sy);
   near(SourceCameraFollowPointMath.focusOffsetX(SourceCameraFollowPointMath.GIRLFRIEND,cx,sx,nv),cx+sx,'NV gf x');
   near(SourceCameraFollowPointMath.focusOffsetY(SourceCameraFollowPointMath.GIRLFRIEND,cy,sy),cy+sy,'NV gf y');
  }
  trace('ok');
 }
}
'''


class SourceCameraTargetTest(unittest.TestCase):
	def test_psych_and_nightmare_vision_share_the_focus_formula(self):
		files = {
			'Main.hx': MAIN,
			'FNFAssets.hx': 'class FNFAssets {public static function exists(p:String):Bool return false;public static function getText(p:String):String return "";}',
			'CoolUtil.hx': 'class CoolUtil {public static function parseJson(t:String):Dynamic return {};}',
		}
		for name in ['PsychCharacterPosition', 'SourceCharacterId', 'SourceCameraFollowPointMath']:
			files[name + '.hx'] = (ROOT / ('source/' + name + '.hx')).read_text()
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			for name, content in files.items():
				(work / name).write_text(content, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
				cwd=ROOT, text=True, capture_output=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_nightmare_vision_targets_use_the_shared_formula(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		helper = play[play.index('@:keep public function getCharacterCameraPos('):]
		helper = helper[:helper.index('\n\t}\n')]
		self.assertIn('SourceCameraFollowPointMath.NIGHTMARE_OPPONENT_BASE_X', helper)
		section = play[play.index('@:keep public function moveCameraSection('):]
		section = section[:section.index('notifySourceCameraMove(role);')]
		self.assertIn('SourceCameraFollowPointMath.GIRLFRIEND', section)
		self.assertNotIn('gf.cameraPosition[0] + girlfriendCameraOffset[0]', section)

	def test_on_move_camera_is_sent_from_one_place(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		notify = play[play.index('function notifySourceCameraMove('):]
		notify = notify[:notify.index('\n\t}\n')]
		# Both engines notify through the one helper, never from the section code.
		self.assertEqual(play.count("'onMoveCamera'"), 2)
		self.assertIn("callNightmareVision('onMoveCamera', [role]);", notify)
		self.assertIn("callAllHScript('onMoveCamera', [role]);", notify)


if __name__ == '__main__':
	unittest.main()
