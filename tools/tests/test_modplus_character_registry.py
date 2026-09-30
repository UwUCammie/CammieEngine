"""Loose Modding Plus characters are claimed only from identical supplied media."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ModPlusCharacterRegistryTest(unittest.TestCase):
    def test_complete_byte_matching_files_only_and_existing_registry_wins(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            donor = base / "donor/images/custom_chars"
            target = base / "runtime/images/custom_chars"
            donor.mkdir(parents=True)
            target.mkdir(parents=True)
            (base / "ModPlusCharacterRegistry.hx").write_text(
                (ROOT / "source/ModPlusCharacterRegistry.hx").read_text()
            )
            (base / "CoolUtil.hx").write_text('''class CoolUtil {
 public static function parseJson(value:String):Dynamic return haxe.Json.parse(value);
 public static function stringifyJson(value:Dynamic):String return haxe.Json.stringify(value);
}''')
            (base / "Main.hx").write_text('''class Main {
 static function main() Sys.println(ModPlusCharacterRegistry.repair(Sys.args()[0], Sys.args()[1]));
}''')

            def files(name, *, same=True):
                (donor / name).mkdir()
                (target / name).mkdir()
                payloads = {f"{name}.hscript": b"function start() {}",
                            f"{name}/char.xml": b"<TextureAtlas/>",
                            f"{name}/char.png": b"x" * (65536 + 11)}
                for relative, data in payloads.items():
                    (donor / relative).write_bytes(data)
                    (target / relative).write_bytes(data)
                if not same:
                    # Same size, different content past the first stream chunk.
                    with (target / name / "char.png").open("r+b") as stream:
                        stream.seek(65536 + 3)
                        stream.write(b"y")

            files("matching")
            files("foreign", same=False)
            files("existing", same=False)
            registry = target / "custom_chars.jsonc"
            registry.write_text(json.dumps({"existing": {"like": "existing", "icons": [2, 3]}}))
            env = os.environ.copy()
            env["TMPDIR"] = str(base)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(base), "--run", "Main",
                 str(base / "donor"), str(base / "runtime")],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(result.stdout.rstrip().endswith("1"), result.stdout)
            values = json.loads(registry.read_text())
            self.assertEqual(set(values), {"matching", "existing"})
            self.assertEqual(values["matching"],
                             {"like": "matching", "icons": [0, 1], "colors": ["#FFFFFF"]})
            self.assertEqual(values["existing"], {"like": "existing", "icons": [2, 3]})


if __name__ == "__main__":
    unittest.main()
