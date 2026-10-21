"""Multiplayer client pieces that must agree with the server byte for byte, plus the sandbox and overlay rules."""
from pathlib import Path
import hashlib, hmac, json, os, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def run_haxe(main, extra=None):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
        Path(temp, "Main.hx").write_text(main, encoding="utf-8")
        for name, text in (extra or {}).items():
            Path(temp, name).write_text(text, encoding="utf-8")
        result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", temp, "--run", "Main"],
                                cwd=ROOT, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


def canonical(files):
    entries = sorted(files, key=lambda f: f["path"])
    return json.dumps([{"path": f["path"], "size": f["size"], "sha256": f["sha256"]} for f in entries],
                      separators=(",", ":"), ensure_ascii=False)


class MultiplayerClientTest(unittest.TestCase):
    def test_streaming_sha256_matches_hashlib(self):
        sizes = [0, 1, 55, 56, 63, 64, 65, 119, 120, 1000, 70000]
        blobs = [os.urandom(size) for size in sizes]
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            for index, blob in enumerate(blobs):
                Path(temp, f"{index}.bin").write_bytes(blob)
            out = run_haxe(r'''
class Main { static function main() {
  var dir = "%s";
  for (i in 0...%d) {
    var bytes = sys.io.File.getBytes(dir + "/" + i + ".bin");
    var whole = new multiplayer.MpSha256(); whole.update(bytes, 0, bytes.length);
    var pieces = new multiplayer.MpSha256(); var at = 0; var step = 7;
    while (at < bytes.length) { var n = at + step > bytes.length ? bytes.length - at : step; pieces.update(bytes, at, n); at += n; step = step * 3 + 1; }
    var a = whole.digestHex(); var b = pieces.digestHex();
    if (a != b) throw "split mismatch " + i;
    Sys.println(a);
  }
} }''' % (Path(temp).as_posix(), len(blobs)))
        self.assertEqual(out.split(), [hashlib.sha256(blob).hexdigest() for blob in blobs])

    def test_paths_manifest_and_proof_match_the_server(self):
        files = [{"path": "assets/songs/tést/Inst.ogg", "size": 10, "sha256": "a" * 64},
                 {"path": "assets/data/test/test.json", "size": 3, "sha256": "b" * 64},
                 {"path": "assets/data/test/copy.json", "size": 3, "sha256": "b" * 64}]
        expected_id = hashlib.sha256(canonical(files).encode()).hexdigest()
        secret, ticket, nonce, version = "c" * 64, "d" * 32, "e" * 32, "0.0.47"
        expected_proof = hmac.new(secret.encode(), f"CE-MP-AUTH\n{ticket}\n{nonce}\n{version}".encode(), hashlib.sha256).hexdigest()
        out = run_haxe(r'''
import multiplayer.MpPackage;
class Main { static function check(v:Bool, s:String) if (!v) throw s;
static function main() {
  var made = MpPackage.make([{path:"assets/songs/t\u00e9st/Inst.ogg", size:10, sha256:"%s"},
    {path:"assets/data/test/test.json", size:3, sha256:"%s"}, {path:"assets/data/test/copy.json", size:3, sha256:"%s"}]);
  check(made.total == 13, "unique total " + made.total);
  check(MpPackage.problem(made) == null, "own manifest rejected: " + MpPackage.problem(made));
  var tampered = {files: made.files, total: made.total, id: "0"};
  check(MpPackage.problem(tampered) == "id mismatch", "tamper");
  for (bad in ["assets/../x.ogg", "/assets/a.ogg", "assets\\a.ogg", "assets/con.txt", "assets/a.exe", "assets/a. /b.ogg", "C:/assets/a.ogg", "songs/a.ogg"])
    check(!MpPackage.validPath(bad), "accepted " + bad);
  check(MpPackage.validPath("assets/songs/test/Inst.ogg"), "rejected a song file");
  Sys.println(made.id);
  Sys.println(multiplayer.MpProof.make("%s", "%s", "%s", "%s"));
} }''' % ("a" * 64, "b" * 64, "b" * 64, secret, ticket, nonce, version))
        made_id, proof = out.split()
        self.assertEqual(made_id, expected_id)
        self.assertEqual(proof, expected_proof)

    def test_sandbox_and_overlay_rules(self):
        out = run_haxe(r'''
import multiplayer.ScriptSandbox;
import multiplayer.MpOverlay;
class Main { static function check(v:Bool, s:String) if (!v) throw s;
static function main() {
  check(ScriptSandbox.classAllowed("sys.io.File"), "inactive must allow");
  ScriptSandbox.enable(["C:/Game/mpcache", "C:/Users/me/AppData/Save"]);
  for (name in ["sys.io.File", "sys.io.Process", "Sys", "cpp.Lib", "haxe.Http", "lime.system.System", "openfl.net.URLLoader",
      "openfl.Lib", "multiplayer.MpClient", "FileParser", "ImportWorkflow"])
    check(!ScriptSandbox.classAllowed(name), "allowed " + name);
  for (name in ["flixel.FlxSprite", "PlayState", "flixel.tweens.FlxTween", "StringTools", "Math", "FNFAssets", "haxe.Json"])
    check(ScriptSandbox.classAllowed(name), "denied " + name);
  check(ScriptSandbox.writeAllowed("C:/Game/mpcache/files/aa/x"), "cache write");
  check(ScriptSandbox.writeAllowed("c:\\users\\me\\appdata\\save\\funkin.sol"), "save write, other spelling");
  check(!ScriptSandbox.writeAllowed("C:/Game/assets/data/x.json"), "library write");
  check(!ScriptSandbox.writeAllowed("C:/Game/mpcache/../assets/x.json"), "climbing out");
  check(!ScriptSandbox.writeAllowed("C:/Game/mpcache2/x"), "prefix trick");
  var blocked = false;
  try ScriptSandbox.guardProcess("calc.exe") catch (_:Dynamic) blocked = true;
  check(blocked, "process allowed");
  ScriptSandbox.disable();
  check(ScriptSandbox.writeAllowed("C:/anything"), "disabled must allow");
  check(ScriptSandbox.tidy("a\\b//c/./d/../e/") == "a/b/c/e", "tidy " + ScriptSandbox.tidy("a\\b//c/./d/../e/"));

  check(MpOverlay.read("assets/x.png") == "assets/x.png", "inactive read changed a path");
  MpOverlay.mount("C:/Game", ["assets/songs/Test/Inst.ogg" => "C:/Game/mpcache/files/ab/1", "assets/data/test/test.json" => "C:/Game/mpcache/files/cd/2"]);
  check(MpOverlay.read("assets/songs/test/inst.ogg") == "C:/Game/mpcache/files/ab/1", "case-insensitive read");
  check(MpOverlay.read("C:\\Game\\assets\\data\\test\\test.json") == "C:/Game/mpcache/files/cd/2", "absolute read");
  check(MpOverlay.read("assets/other.png") == "assets/other.png", "unmounted file redirected");
  check(MpOverlay.provides("assets/songs/test") && MpOverlay.isFolder("assets/songs") && !MpOverlay.isFolder("assets/songs/test/Inst.ogg"), "folders");
  var listed = MpOverlay.children("assets/songs", ["bopeebo", "TEST"]);
  check(listed.join(",") == "bopeebo,TEST", "merge keeps the real spelling " + listed.join(","));
  check(MpOverlay.children("assets/data", []).join(",") == "test", "mounted child");
  check(MpOverlay.relativeOf("D:/Elsewhere/assets/x") == null && MpOverlay.relativeOf("../x") == null, "outside root");
  MpOverlay.unmount();
  check(MpOverlay.read("assets/songs/test/inst.ogg") == "assets/songs/test/inst.ogg", "unmount");
  MpOverlay.startRecording("C:/Game");
  MpOverlay.read("assets/images/a.png"); MpOverlay.read("C:/Game/assets/data/b.json"); MpOverlay.read("options.txt");
  check(MpOverlay.stopRecording().join(",") == "assets/data/b.json,assets/images/a.png", "recording");
  Sys.println("ok");
} }''')
        self.assertIn("ok", out)

    def test_play_stream_records_what_the_server_verifies(self):
        out = run_haxe(r'''
import multiplayer.MpPlayStream;
class Main { static function check(v:Bool, s:String) if (!v) throw s;
static function main() {
  var s = new MpPlayStream();
  check(s.addNote(1000, 0, 0) == 0 && s.addNote(1500, 1, 600) == 1 && s.addNote(2000, 2, 0) == 2, "indexes");
  check(s.addNote(2500, 40, 0) == -1 && s.totalNotes() == 3, "lane out of range");
  // Frame at 990: lane 0 goes down and the note is hit in the same frame; no second press.
  s.hit(0, 1003.5); s.judge(0, 0, 4, 3.5);
  s.sample(0, true, 990); s.endFrame();
  s.sample(0, false, 1100); s.endFrame();
  // A hold: head hit late, held until 2050, past the end at 2100 minus the leniency.
  s.hit(1, 1560); s.judge(1, 0, 3, 60);
  s.sample(1, true, 1560); s.endFrame();
  s.sample(1, true, 1800); s.endFrame();
  s.judge(1, 1, 4, 12.0);
  s.sample(1, false, 2050); s.endFrame();
  // A tap that hit nothing, and a miss.
  s.sample(3, true, 1700); s.endFrame();
  s.sample(3, false, 1750); s.endFrame();
  s.judge(2, 0, 0, 12.0);
  // Audio resync stepped back: still sent in time order.
  s.sample(2, true, 2400); s.endFrame();
  s.sample(2, false, 2390); s.endFrame();
  var messages = s.drain();
  check(s.drain().length == 0, "drain empties");
  Sys.println(haxe.Json.stringify(messages));
} }''')
        messages = json.loads(out.strip().splitlines()[-1])
        kinds = [m["t"] for m in messages]
        self.assertEqual(kinds, ["notes", "input", "judge"])
        self.assertEqual([m["seq"] for m in messages], [0, 1, 2])
        notes, inputs, judges = messages[0]["notes"], messages[1]["events"], messages[2]["items"]
        self.assertEqual(notes, [[1000, 0, 0], [1500, 1, 600], [2000, 2, 0]])
        self.assertEqual([e[0] for e in inputs], sorted(e[0] for e in inputs))
        self.assertEqual(sum(1 for e in inputs if e[1] == 0 and e[2]), 1, "the hit's press is not doubled")
        self.assertIn([1700, 3, True], inputs)
        self.assertEqual(judges, [[0, 0, 4, 3.5], [1, 0, 3, 60], [1, 1, 4, None], [2, 0, 0, None]])
        server = ROOT.parents[1] / "Burnout-3-Recomp/server/site"
        if not (server / "cammie_scoring.py").is_file():
            self.skipTest("server checkout not present")
        import importlib.util
        spec = importlib.util.spec_from_file_location("cammie_scoring", server / "cammie_scoring.py")
        scoring = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scoring)
        windows = {"sick": 45, "good": 90, "bad": 135, "shit": 203}
        ordered, reason = scoring.verify(notes, inputs, judges, windows, True)
        self.assertIsNone(reason)
        self.assertEqual(ordered, [4, 3, 0, 4])

    def test_local_endpoint_only_accepts_loopback(self):
        out = run_haxe(r'''
import multiplayer.MpEndpoint;
class Main { static function main() {
  for (value in ["http://127.0.0.1:8099", "http://localhost:8099/", "http://[::1]:80", "https://127.0.0.1:8099",
      "http://example.com:8099", "http://127.0.0.2:1", "http://127.0.0.1:99999", "http://127.0.0.1:8099/x", null]) {
    var e = MpEndpoint.parse(value);
    Sys.println(e == null ? "-" : e.host + " " + e.port + " " + e.secure);
  }
} }''')
        self.assertEqual(out.strip().splitlines(), ["127.0.0.1 8099 false", "localhost 8099 false", "::1 80 false",
                                                    "-", "-", "-", "-", "-", "-"])

    def test_lobby_play_is_wired_into_the_song(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        judge = play[play.index("function standardJudge("):play.index("function standardMiss(")]
        self.assertIn("mpJudged(note, 0, judgement);", judge)
        self.assertIn("mpJudged(owner, 1, hit ? StandardScore.SICK : StandardScore.MISS);", play)
        self.assertIn("mpBuildTimeline();", play[play.index("function standardPrepareChart("):])
        end = play[play.index("function endSong(?force:Bool = false)"):]
        self.assertLess(end.index("MpHooks.current.finishPlay(false)"), end.index("callCodenameEvent('onSongEnd'"),
                        "the server hears the song ended before scripts can hold the end screen")
        exit_ = play[play.index("public static function exitToMenu("):]
        self.assertIn("multiplayer.MpHooks.current.leaveSong(true);", exit_[:400])
        restart = play[play.index("public function restartSong("):]
        self.assertIn("exitToMenu();", restart[:600])
        self.assertIn("if (multiplayer.MpHooks.current != null) Judge.setJudge(Classic);", play)
        self.assertIn("FlxG.random.initialSeed = match.seed;", play)
        self.assertIn("mpFrame();", play[play.index("override public function update(elapsed:Float)"):][:900])
        pause = (ROOT / "source/PauseSubState.hx").read_text(encoding="utf-8")
        self.assertIn("if (multiplayer.MpHooks.current != null) menuItems = ['Resume', 'Exit to menu'];", pause)
        over = (ROOT / "source/GameOverSubstate.hx").read_text(encoding="utf-8")
        self.assertIn("multiplayer.MpHooks.current.finishPlay(true);", over[over.index("public function new(player:Character)"):][:300])
        freeplay = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        select = freeplay[freeplay.index("function openSelection("):]
        self.assertLess(select.index("pick.chosen("), select.index("PlayState.SONG = Song.loadFromJson("))

    def test_native_shadows_are_current(self):
        generated = {}
        for name in ("Type.hx", "sys/FileSystem.hx", "sys/io/File.hx", "sys/io/Process.hx"):
            generated[name] = (ROOT / "source-native" / name).read_text(encoding="utf-8")
        subprocess.run([str(ROOT / ".tools/python/python.exe"), str(ROOT / "tools/make_native_shadows.py")],
                       cwd=ROOT, check=True, capture_output=True)
        for name, text in generated.items():
            self.assertEqual((ROOT / "source-native" / name).read_text(encoding="utf-8"), text, name)
        self.assertIn('<classpath name="source-native" if="cpp" />', (ROOT / "Project.xml").read_text(encoding="utf-8"))
        file_system = generated["sys/FileSystem.hx"]
        for hook in ("MpOverlay.provides(path)", "ScriptSandbox.guardWrite(path)", "MpOverlay.children(path, real)"):
            self.assertIn(hook, file_system)
        self.assertEqual(generated["Type.hx"].count("ScriptSandbox.classAllowed(name)"), 2)


if __name__ == "__main__":
    unittest.main()
