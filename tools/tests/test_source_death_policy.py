"""Pin source death eligibility separately from death-transition effects."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
DONORS = ROOT.parent / "fnf_sources"


def compact(source: str) -> str:
    return "".join(source.split())


class SourceDeathPolicyTest(unittest.TestCase):
    def test_predicates_match_the_pinned_donor_expressions(self):
        psych = (DONORS / "FNF-PsychEngine/source/states/PlayState.hx").read_text(
            encoding="utf-8"
        )
        nightmare = (
            DONORS / "NightmareVision/source/funkin/states/PlayState.hx"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "if(((skipHealthCheck&&instakillOnMiss)||health<=0)"
            "&&!practiceMode&&!isDead&&gameOverTimer==null)",
            compact(psych),
        )
        self.assertIn(
            "if((skipHealthCheck&&instakillOnMiss)||"
            "((healthBounds.max>healthBounds.min&&health<=healthBounds.min)"
            "||(healthBounds.min>healthBounds.max&&health>=healthBounds.min))"
            "&&!practiceMode&&!isDead)",
            compact(nightmare),
        )

    def test_source_policy_truth_tables(self):
        policy = (ROOT / "source/SourceDeathPolicy.hx").read_text(encoding="utf-8")
        fixture = r'''
class SourceDeathPolicyFixture {
  static function check(value:Bool, message:String):Void if (!value) throw message;

  static function main():Void {
    var ordinary = [0.0, 2.0];
    var inverted = [2.0, 0.0];
    var equal = [1.0, 1.0];

    // Psych's health predicate is always health <= 0; it does not use bounds.
    check(SourceDeathPolicy.eligible(false, 0, ordinary, false, false, false, false, false),
      'Psych zero health should be eligible');
    check(SourceDeathPolicy.eligible(false, -0.1, [100.0, 200.0], false, false, false, false, false),
      'Psych ignores NV bounds and accepts negative health');
    check(!SourceDeathPolicy.eligible(false, 0.1, inverted, false, true, false, false, false),
      'Psych does not skip health check unless skipHealthCheck is true');
    check(SourceDeathPolicy.eligible(false, 5, ordinary, true, true, false, false, false),
      'Psych instakill bypasses positive health when requested');
    check(!SourceDeathPolicy.eligible(false, 5, ordinary, true, false, false, false, false),
      'Psych skip flag without instakill is inert');
    check(!SourceDeathPolicy.eligible(false, 0, ordinary, false, false, true, false, false),
      'Psych practice suppresses health death');
    check(!SourceDeathPolicy.eligible(false, 5, ordinary, true, true, true, false, false),
      'Psych practice also suppresses instakill death');
    check(!SourceDeathPolicy.eligible(false, 0, ordinary, false, false, false, true, false),
      'Psych isDead suppresses another death');
    check(!SourceDeathPolicy.eligible(false, 0, ordinary, false, false, false, false, true),
      'Psych active death timer suppresses another death');

    // NV health bounds use the literal donor direction and strict bound ordering.
    check(SourceDeathPolicy.eligible(true, 0, ordinary, false, false, false, false, false),
      'NV normal bounds use the lower boundary');
    check(SourceDeathPolicy.eligible(true, -0.1, ordinary, false, false, false, false, false),
      'NV normal bounds include health below the lower boundary');
    check(!SourceDeathPolicy.eligible(true, 1, ordinary, false, false, false, false, false),
      'NV normal bounds reject interior health');
    check(SourceDeathPolicy.eligible(true, 2, inverted, false, false, false, false, false),
      'NV inverted bounds use the upper-direction boundary');
    check(!SourceDeathPolicy.eligible(true, 1.99, inverted, false, false, false, false, false),
      'NV inverted bounds reject health below their threshold');
    check(!SourceDeathPolicy.eligible(true, 1, equal, false, false, false, false, false),
      'NV equal bounds trigger neither boundary predicate');
    check(!SourceDeathPolicy.eligible(true, 0, ordinary, false, false, true, false, false),
      'NV practice suppresses health-bound death');
    check(!SourceDeathPolicy.eligible(true, 0, ordinary, false, false, false, true, false),
      'NV isDead suppresses health-bound death');
    check(SourceDeathPolicy.eligible(true, 0, ordinary, false, false, false, false, true),
      'NV has no donor timer guard');
    check(!SourceDeathPolicy.eligible(true, 5, ordinary, true, false, false, false, false),
      'NV skip flag without instakill is inert');

    // Preserve the donor's literal `||` precedence: this arm bypasses practice,
    // isDead, and the unused timer parameter.
    check(SourceDeathPolicy.eligible(true, 5, ordinary, true, true, true, true, true),
      'NV instakill skip arm bypasses practice/isDead/timer guards');
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "SourceDeathPolicy.hx").write_text(policy, encoding="utf-8", newline="\n")
            (work / "SourceDeathPolicyFixture.hx").write_text(
                fixture, encoding="utf-8", newline="\n"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SourceDeathPolicyFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
