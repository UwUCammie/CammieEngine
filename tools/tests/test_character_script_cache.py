"""Character swaps reuse unchanged parsed scripts without sharing interpreters."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class CharacterScriptCacheTest(unittest.TestCase):
    def test_program_cache_reuses_unchanged_source_and_is_bounded(self):
        source = (ROOT / "source/Character.hx").read_text()
        typedef_start = source.index("typedef CharacterProgramCacheEntry = {")
        typedef_end = source.index("\nclass Character extends", typedef_start)
        typedef = source[typedef_start:typedef_end]
        cache_start = source.index("\tstatic var characterProgramCache:")
        cache_end = source.index("\n\tpublic var animOffsets", cache_start)
        cache = source[cache_start:cache_end]
        fixture = """import hscript.Expr;
using StringTools;
""" + typedef + """
class CharacterScriptCacheTest {
""" + cache + """
\tstatic function main() {
\t\tvar first = cachedCharacterProgram('character:sample.hscript', 'var answer = 1;');
\t\tvar second = cachedCharacterProgram('character:sample.hscript', 'var answer = 1;');
\t\tif (first != second) throw 'unchanged character source was parsed again';

\t\tvar updated = cachedCharacterProgram('character:sample.hscript', 'var answer = 2;');
\t\tif (updated == first) throw 'changed character source reused a stale program';

\t\tfor (index in 0...70)
\t\t\tcachedCharacterProgram('character:' + index, 'var value = ' + index + ';');
\t\tif (characterProgramCacheOrder.length != CHARACTER_PROGRAM_CACHE_MAX
\t\t\t|| characterProgramCache.exists('character:0'))
\t\t\tthrow 'character program cache is not bounded by its LRU limit';
\t}
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "CharacterScriptCacheTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(HSCRIPT),
                 "-main", "CharacterScriptCacheTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
