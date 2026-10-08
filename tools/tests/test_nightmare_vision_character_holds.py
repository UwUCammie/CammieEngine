"""Pin NV manual character-hold leases to owner, field, role, and input lifetime."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def extract_function(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed function: {marker}")


class NightmareVisionCharacterHoldsTest(unittest.TestCase):
    def test_releasing_manual_hold_runs_source_duration_return(self):
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        setter = extract_function(character, 'function set_holding(value:Bool):Bool')
        duration = extract_function(character, 'function nightmareVisionSingDuration():Float')
        self.assertIn('&& sourceDanceNightmare', setter)
        fixture = '''class Conductor { public static var stepCrochet:Float = 1000; }
class Character {
 public var sourceDanceNightmare:Bool = true;
 public var holdTimer:Float = 0;
 public var holdTime:Float = 4;
 public var singDuration:Float = 4;
 public var forceDance:Bool = false;
 var nightmareVisionHolding:Bool = false;
 public var dances:Int = 0;
 public var holding(get,set):Bool;
 function get_holding():Bool return nightmareVisionHolding;
 function dance(force:Bool = false):Void dances++;
 public function new() {}
 ''' + setter + '\n' + duration + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var actor = new Character(); actor.singDuration = 1.5;
  actor.holding = true;
  actor.holdTimer = 1.4;
  actor.holding = false;
  check(actor.dances == 0 && actor.holdTimer == 1.4,
   'release below the authored duration does not force a dance');
  actor.holding = true; actor.holdTimer = 1.5; actor.holding = false;
  check(actor.dances == 1 && actor.holdTimer == 0,
   'releasing after the source duration dances immediately and clears elapsed time');
  actor.sourceDanceNightmare = false; actor.holding = true;
  actor.holdTimer = 8; actor.holding = false;
  check(actor.dances == 1 && actor.holdTimer == 8,
   'native and Psych actors keep their existing hold-release behavior');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_sustain_gate_preserves_hold_state_and_taps(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        helper = (ROOT / 'source/SourceCharacterAnimationLifecycle.hx').read_text(encoding='utf-8')
        method = extract_function(play, 'function prepareNightmareVisionHitSingers(')
        self.assertLess(method.index('actor.holdTimer = 0;'), method.index('retainNightmareVisionHitHold('))
        self.assertLess(method.index('retainNightmareVisionHitHold('), method.index("noteTypeOf(note) == 'Hey!'"))
        self.assertLess(method.index("noteTypeOf(note) == 'Hey!'"),
                        method.index('shouldPlayNightmareVisionNoteAnimation('))

        fixture = '''class FakeAnimation {
 public var calls:Array<String> = [];
 public var heyExists:Bool = false;
 public var holdExists:Bool = false;
 public function new() {}
 public function exists(name:String):Bool return name == 'hey' ? heyExists
  : name == 'singLEFT-hold' && holdExists;
}
class Character {
 public var vSliceSustains:Bool = false;
 public var sourceActor:Bool = true;
 public var holdTimer:Float = 0;
 public var holding:Bool = false;
 public var specialAnim:Bool = false;
 public var animation:FakeAnimation = new FakeAnimation();
 public function new() {}
 public function isNightmareVisionSourceActor():Bool return sourceActor;
 public function playAnim(name:String, force:Bool = false):Void
  animation.calls.push(name + ':' + force);
 public function playAnimForDuration(name:String, duration:Float, forced:Bool):Void
  animation.calls.push('duration:' + name);
}
class Note {
 public var forceGfSing:Bool = false;
 public var owner:Character;
 public var animSuffix:String = '';
 public var noteData:Int = 0;
 public var noAnimation:Bool = false;
 public var isSustainNote:Bool = false;
 public var nightmareVisionSustainEnd:Bool = false;
 public var noteType:String = '';
 public function new() {}
}
class NightmareVisionPlayFieldView {
 public var singers:Array<Dynamic> = [];
 public var playerControls:Bool = true;
 public var autoPlayed:Bool = false;
 public function new() {}
}
class NightmareVisionNoteTypeRuntime {
 public static function noteTypeOf(note:Note):String return note.noteType;
}
class Main {
 public var gf:Character = new Character();
 public var retained:Int = 0;
 public function new() {}
 function nightmareVisionSkinForField(fieldID:Int):Dynamic return null;
 function retainNightmareVisionHitHold(field:NightmareVisionPlayFieldView,
  actor:Character, ownerOverride:Bool):Void { retained++; actor.holding = true; }
 ''' + method + '''
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var host = new Main(); var field = new NightmareVisionPlayFieldView();
  var sustainActor = new Character(); sustainActor.vSliceSustains = true;
  sustainActor.holdTimer = 9; field.singers = [sustainActor];
  var sustain = new Note(); sustain.isSustainNote = true;
  host.prepareNightmareVisionHitSingers(sustain, field, 0, true);
  check(sustainActor.holdTimer == 0 && sustainActor.holding && host.retained == 1
   && sustainActor.animation.calls.length == 0,
   'opted-in NV sustain keeps manual hold updates but does not restart the note animation');

  var tapActor = new Character(); tapActor.vSliceSustains = true; field.singers = [tapActor];
  host.prepareNightmareVisionHitSingers(new Note(), field, 0, false);
  check(tapActor.animation.calls.join(',') == 'singLEFT:true',
   'the V-Slice flag never suppresses a tap animation');

  var legacyActor = new Character(); legacyActor.vSliceSustains = false;
  legacyActor.animation.holdExists = true; field.singers = [legacyActor];
  host.prepareNightmareVisionHitSingers(sustain, field, 0, false);
  check(legacyActor.animation.calls.join(',') == 'singLEFT-hold:false',
   'false or absent metadata keeps the ordinary sustain hold animation');

  var heyActor = new Character(); heyActor.vSliceSustains = true;
  heyActor.animation.heyExists = true; field.singers = [heyActor];
  var hey = new Note(); hey.isSustainNote = true; hey.noteType = 'Hey!';
  host.prepareNightmareVisionHitSingers(hey, field, 0, false);
  check(heyActor.animation.calls.join(',') == 'duration:hey' && heyActor.specialAnim,
   'source Hey handling runs before the regular sustain-animation gate');

  var otherDialect = new Character(); otherDialect.sourceActor = false;
  otherDialect.vSliceSustains = true; field.singers = [otherDialect];
  host.prepareNightmareVisionHitSingers(sustain, field, 0, false);
  check(otherDialect.animation.calls.length == 1,
   'a non-NV actor cannot inherit the NV sustain gate');

  var noAnimationActor = new Character(); noAnimationActor.vSliceSustains = true;
  noAnimationActor.holdTimer = 4; field.singers = [noAnimationActor];
  var suppressed = new Note(); suppressed.noAnimation = true;
  host.prepareNightmareVisionHitSingers(suppressed, field, 0, true);
  check(noAnimationActor.holdTimer == 4 && !noAnimationActor.holding
   && noAnimationActor.animation.calls.length == 0,
   'source noAnimation returns before hold or animation changes');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            (work / 'SourceCharacterAnimationLifecycle.hx').write_text(
                helper, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_field_and_role_claim_lifecycle(self):
        helper = (ROOT / 'source/SourceCharacterHoldLedger.hx').read_text(encoding='utf-8')
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')

        self.assertIn('if (manualHit && field.playerControls && !field.autoPlayed)', play)
        self.assertIn('actor.isNightmareVisionSourceActor()', play)
        self.assertIn('input.inputPressed(key)', play)
        self.assertIn('Math.min(Math.max(SONG.keys, 0), input.pressedActions.length)', play)
        self.assertIn('!anyPressed && !inCutscene', play)
        self.assertIn('field.inControl', play)
        self.assertIn('nightmareVisionFields.indexOf(field)', play)
        self.assertIn('nightmareVisionHoldLedger.clearFieldAll(field)', play)
        self.assertIn('nightmareVisionHoldLedger.clearAll()', play)
        self.assertIn('nightmareVisionHoldRoleGroup(actor) != claim.role', play)
        self.assertIn('!nightmareVisionHoldLedger.hasClaims()', play)
        self.assertIn('!actor.exists', play)
        self.assertIn('return actor.isNightmareVisionSourceActor() ? cast actor : null;', play)
        self.assertNotIn('nightmareVisionRoleGroups.copy()', play)
        self.assertIn('isNightmareVisionSourceActor', character)

        fixture = '''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var ledger = new SourceCharacterHoldLedger();
  check(!ledger.hasClaims(), 'empty ledger exposes the uncapped-update fast path');
  var ownerA = 'owner-a'; var ownerB = 'owner-b';
  var fieldA = {}; var fieldB = {}; var roleA = {}; var roleB = {}; var actor = {};
  check(ledger.retain(ownerA, fieldA, roleA, actor), 'first field claim is new');
  check(!ledger.retain(ownerA, fieldA, roleA, actor), 'same field hit does not duplicate claim');
  check(ledger.retain(ownerA, fieldB, roleA, actor), 'same actor can be held by a second field');
  check(ledger.clearField(ownerA, fieldA).length == 0 && ledger.hasActorClaim(actor),
   'removing one field does not release another field claim');
  check(ledger.retain(ownerB, fieldA, roleB, actor), 'claim identity includes owner and role');
  check(ledger.clearOwner(ownerA).length == 0 && ledger.hasActorClaim(actor),
   'owner release preserves a sibling owner claim');
  var invalidRole = ledger.prune(function(claim) return claim.role == roleB);
  check(invalidRole.length == 0 && ledger.hasActorClaim(actor),
   'role pruning preserves actor state while another role still owns a claim');
  var noClaims = ledger.clearField(ownerB, fieldA);
  check(noClaims.length == 1 && noClaims[0] == actor && !ledger.hasActorClaim(actor),
   'last field/role release returns the actor for clearing');

  var ownerActor = {}; var overrideField = {}; var overrideRole = {};
  ledger.retain(ownerA, overrideField, overrideRole, ownerActor, true);
  var stillOwned = ledger.prune(function(claim) return claim.noteOwnerOverride);
  check(stillOwned.length == 0 && ledger.hasClaim(ownerA, overrideField, ownerActor),
   'a note-owner singer remains valid through field singer-list changes while its source role exists');
  check(ledger.clearAll().length == 1, 'owner teardown returns the final held actor');
  check(!ledger.hasClaims(), 'clear leaves no active leases');
}
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            (work / 'SourceCharacterHoldLedger.hx').write_text(helper, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_standalone_source_actor_is_a_valid_role_token_across_shared_fields(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        role_lookup = extract_function(play, 'function nightmareVisionHoldRoleGroup(')
        member_check = extract_function(play, 'function nightmareVisionGroupContainsActor(')
        fixture = f'''class Character {{
 public var exists:Bool = true;
 public var sourceActor:Bool;
 public function new(sourceActor:Bool) this.sourceActor = sourceActor;
 public function isNightmareVisionSourceActor():Bool return sourceActor;
}}
class NightmareVisionCharacterGroup {{
 public var members:Array<Character> = [];
 public function new() {{}}
}}
class Main {{
 var nightmareVisionRoleGroups:Array<NightmareVisionCharacterGroup> = [];
 var boyfriendGroup:NightmareVisionCharacterGroup;
 var dadGroup:NightmareVisionCharacterGroup;
 var gfGroup:NightmareVisionCharacterGroup;
 public function new() {{}}
 {member_check}
 {role_lookup}
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {{
  var host = new Main();
  var ledger = new SourceCharacterHoldLedger();
  var actor = new Character(true);
  var other = new Character(false);
  check(host.nightmareVisionHoldRoleGroup(actor) == actor,
   'standalone source actor is the stable role token');
  check(host.nightmareVisionHoldRoleGroup(other) == null,
   'non-source actor receives no hold role');
  var fieldA:Dynamic = {{owner:actor,singers:[actor]}};
  var fieldB:Dynamic = {{owner:null,singers:[actor]}};
  var token = host.nightmareVisionHoldRoleGroup(actor);
  check(ledger.retain('owner',fieldA,token,actor), 'field owner can retain standalone actor');
  check(ledger.retain('owner',fieldB,token,actor), 'same actor can be retained by another live singer field');
  var releaseOne = ledger.prune(function(claim) return claim.field != fieldA
   && claim.actor.exists && claim.role == host.nightmareVisionHoldRoleGroup(claim.actor)
   && (claim.field.owner == claim.actor || claim.field.singers.indexOf(claim.actor) >= 0));
  check(releaseOne.length == 0 && ledger.hasActorClaim(actor),
   'one field ending does not clear a shared singer hold');
  var releaseLast = ledger.prune(function(claim) return claim.field != fieldB);
  check(releaseLast.length == 1 && releaseLast[0] == actor && !ledger.hasClaims(),
   'last field release clears the standalone actor hold');

  var grouped = new Character(true);
  var group = new NightmareVisionCharacterGroup(); group.members.push(grouped);
  host.boyfriendGroup = group;
  check(host.nightmareVisionHoldRoleGroup(grouped) == group,
   'registered character still uses the source role group token');
  group.members.resize(0);
  check(host.nightmareVisionHoldRoleGroup(grouped) == grouped,
   'removed role group does not invalidate a still-live source actor token');
  var retiredField:Dynamic = {{owner:grouped,singers:[grouped]}};
  ledger.retain('owner',retiredField,grouped,grouped);
  grouped.exists = false;
  var retired = ledger.prune(function(claim) return claim.actor.exists
   && claim.role == host.nightmareVisionHoldRoleGroup(claim.actor));
  check(retired.length == 1 && retired[0] == grouped,
   'actor existence and role identity prune a retired standalone claim: '
    + retired.length + '/' + ledger.hasActorClaim(grouped));
 }}
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            (work / 'SourceCharacterHoldLedger.hx').write_text(
                (ROOT / 'source/SourceCharacterHoldLedger.hx').read_text(encoding='utf-8'),
                encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
