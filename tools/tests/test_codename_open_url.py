"""Validate the shared owner-script URL opener without launching a browser."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameOpenURLTest(unittest.TestCase):
    def test_validates_http_links_and_dispatches_only_through_injected_opener(self):
        bindings = (ROOT / "source/CodenameModBindings.hx").read_text()
        self.assertIn("openURL:function(url:String):Bool", bindings)
        self.assertIn("CodenameOpenURLCompat.open(url,", bindings)
        self.assertIn("FlxG.openURL(safeUrl)", bindings)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import CodenameOpenURLCompat;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  Sys.putEnv('FNF_COMPAT_TEST_NO_BROWSER', '');
  var opened:Array<String> = [];
  var opener = function(url:String):Void opened.push(url);
  var donorLinks = [
   'https://youtube.com/@A2music',
   'https://youtube.com/@DaPootisBird',
   'https://twitter.com/Tayied1',
   'https://www.roblox.com/communities/17127111/Jule-Games-x-Euphoric-Bros#!/about',
   'https://steampowered.com'
  ];
  for (url in donorLinks)
   check(CodenameOpenURLCompat.open(url, opener), 'rejected donor HTTP(S) URL: ' + url);
  check(opened.length == donorLinks.length, 'valid links were not dispatched exactly once');
  for (i in 0...donorLinks.length)
   check(opened[i] == donorLinks[i], 'URL changed during dispatch: ' + opened[i]);

  var normalized = CodenameOpenURLCompat.normalize('HTTPS://example.com/path?q=1#section');
  check(normalized == 'https://example.com/path?q=1#section',
   'scheme should be canonicalized while preserving path/query/fragment: ' + normalized);
  check(CodenameOpenURLCompat.normalize('http://localhost:8080/path')
   == 'http://localhost:8080/path', 'HTTP localhost with a valid port should be allowed');
  check(CodenameOpenURLCompat.normalize('https://[2001:db8::1]:443/')
   == 'https://[2001:db8::1]:443/', 'bracketed IPv6 authority should be allowed');

  var rejected = [
   null, '', ' https://example.com', 'https://example.com ',
   'javascript:alert(1)', 'data:text/html,hello', 'file:///etc/passwd',
   '//example.com/path', 'https://', 'https:///path',
   'https://user@example.com/', 'https://user:password@example.com/',
   'https://example.com\\@evil.test/', 'https://example.com/a\nb',
   'https://example..com/', 'https://.example.com/',
   'https://example.com:0/', 'https://example.com:70000/',
   'https://example.com:not-a-port/'
  ];
  var countBefore = opened.length;
  for (url in rejected)
   check(!CodenameOpenURLCompat.open(url, opener), 'unsafe URL was accepted: ' + url);
  check(opened.length == countBefore, 'rejected URL reached the injected opener');

  check(!CodenameOpenURLCompat.open('https://example.com/', null),
   'missing platform opener should be reported as unavailable');
  check(!CodenameOpenURLCompat.open('https://example.com/', function(_url:String):Void
   throw 'test dispatch error'), 'opener errors should not escape the compatibility adapter');

  Sys.putEnv('FNF_COMPAT_TEST_NO_BROWSER', '1');
  var beforeSuppressed = opened.length;
  check(CodenameOpenURLCompat.open('https://example.com/credits', opener),
   'private browser suppression rejected a valid URL');
  check(opened.length == beforeSuppressed, 'private menu check activated the opener');
  check(!CodenameOpenURLCompat.open('file:///etc/passwd', opener),
   'private browser suppression bypassed URL validation');
  Sys.putEnv('FNF_COMPAT_TEST_NO_BROWSER', '');
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
