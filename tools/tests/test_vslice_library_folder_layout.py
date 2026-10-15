"""V-Slice mods that keep each asset library in its own folder import.

Such a mod has no data folder: song metadata and charts sit beside the audio
(`<library>/songs/<id>/<id>-chart.json`), each character or stage JSON sits in
its own folder beside its sprites, asset paths start at the library name, and
sheets may be DDS. The same build ships its base game in assets/<library>,
which is not part of the mod.
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def dds_dxt5(width, height):
    blocks = ((width + 3) // 4) * ((height + 3) // 4)
    header = bytearray(128)
    header[0:4] = b'DDS '
    header[4:8] = (124).to_bytes(4, 'little')
    header[12:16] = height.to_bytes(4, 'little')
    header[16:20] = width.to_bytes(4, 'little')
    header[76:80] = (32).to_bytes(4, 'little')
    header[80:84] = (4).to_bytes(4, 'little')
    header[84:88] = b'DXT5'
    return bytes(header) + bytes([255, 255, 0, 0, 0, 0, 0, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0, 0]) * blocks


def song_pair(folder, song_id):
    folder.mkdir(parents=True)
    (folder / f'{song_id}-metadata.json').write_text(json.dumps({'version': '2.2.4', 'songName': song_id,
        'playData': {'difficulties': ['normal'], 'characters': {'player': 'bf', 'opponent': 'hero'}}}))
    (folder / f'{song_id}-chart.json').write_text(json.dumps({'version': '2.0.0', 'notes': {'normal': []}}))
    (folder / 'Inst.ogg').write_bytes(b'OggS')


class VSliceLibraryFolderLayoutTest(unittest.TestCase):
    def test_library_folder_is_the_data_root_and_dds_sheets_convert(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            game = Path(folder) / 'game'
            library = game / 'mods/hero/gameplay'
            song_pair(library / 'songs/duel', 'duel')
            (game / 'mods/hero/_polymod_meta.json').write_text('{"title":"Hero","api_version":"0.9.0"}')
            character = library / 'characters/hero'
            character.mkdir(parents=True)
            (character / 'hero.json').write_text(json.dumps({'version': '1.0.0', 'name': 'Hero',
                'assetPath': 'gameplay/characters/hero/hero',
                'animations': [{'name': 'idle', 'prefix': 'idle'}]}))
            (character / 'hero.dds').write_bytes(dds_dxt5(8, 8))
            (character / 'hero.xml').write_text('<TextureAtlas><SubTexture name="idle0000"/></TextureAtlas>')
            (library / 'scripts').mkdir()
            # The build's own base game, in the same per-library shape.
            song_pair(game / 'assets/gameplay/songs/tutorial', 'tutorial')
            main = '''class Main {
  static function main() {
    var game = %s;
    var library = %s;
    var modRoot = null;
    for (root in ImportRootScanner.scan(game)) {
      if (StringTools.replace(root.root, "\\\\", "/").indexOf("/assets/") >= 0 && root.data != "")
        throw "the bundled base game became a mod data root: " + root.root;
      if (StringTools.endsWith(StringTools.replace(root.root, "\\\\", "/"), "mods/hero/gameplay")) modRoot = root;
    }
    if (modRoot == null) throw "the mod library folder was not detected";
    if (modRoot.engine != "V-Slice") throw "wrong engine " + modRoot.engine;
    if (StringTools.replace(modRoot.data, "\\\\", "/") != library) throw "data root not the library folder: " + modRoot.data;
    // A library path spelled with a trailing separator still finds its mod.
    if (!@:privateAccess ImportRootScanner.isPolymodLibraryFolder(library + "/"))
      throw "trailing separator hid the Polymod mod folder";
    if (@:privateAccess ImportRootScanner.isPolymodLibraryFolder(game + "/assets/gameplay/"))
      throw "the bundled base game library counted as a Polymod mod";
    var data = haxe.Json.parse(sys.io.File.getContent(library + "/characters/hero/hero.json"));
    var result = VSliceImporter.convertCharacter(data, library, "hero", false);
    if (Reflect.field(result, "supported") != true) throw "DDS character rejected: " + result.diagnostics;
    var png = null;
    for (asset in result.assets)
      if (StringTools.endsWith(asset.destination, ".png")) png = asset;
    if (png == null || png.requiresConversion != true || !StringTools.endsWith(png.source, "hero.dds"))
      throw "DDS sheet not planned for conversion: " + result.assets;
    var out = %s;
    var decoded = VSliceAstcAdapter.DdsTextureDecoder.decodeFile(png.source, out);
    if (!decoded.success) throw decoded.message;
    if (sys.io.File.getBytes(out).getString(1, 3) != "PNG") throw "converted file is not a PNG";
  }
}''' % (json.dumps(str(game)), json.dumps(str(library)), json.dumps(str(Path(folder) / 'hero.png')))
            (Path(folder) / 'Main.hx').write_text(main, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


    def test_library_note_style_uses_its_own_audio_and_native_base_popups(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            library = Path(folder) / 'gameplay'
            style = library / 'notestyles/hero'
            style.mkdir(parents=True)
            for name in ('hero_notes', 'hero_strums'):
                (style / f'{name}.png').write_bytes(b'png')
                (style / f'{name}.xml').write_text('<TextureAtlas><SubTexture name="noteLeft0000"/></TextureAtlas>')
            (style / 'introGO.ogg').write_bytes(b'OggS')
            data = {'version': '1.1.0', 'name': 'Hero', 'assets': {
                'note': {'assetPath': 'gameplay/notestyles/hero/hero_notes', 'data': {'left': {'prefix': 'noteLeft'}}},
                'noteStrumline': {'assetPath': 'gameplay/notestyles/hero/hero_strums', 'data': {}},
                'countdownGo': {'data': {'audioPath': 'gameplay/notestyles/hero/introGO'}, 'assetPath': None},
                'judgementSick': {'assetPath': 'gameplay/notestyles/funkin/popup/sick'},
                'comboNumber7': {'assetPath': 'gameplay/notestyles/funkin/popup/digit-7'},
                'noteSplash': {'assetPath': 'gameplay/notestyles/funkin/note-splashes', 'data': {'enabled': True}}}}
            main = '''class Main {
  static function main() {
    var result = VSliceImporter.convertNoteStyle(haxe.Json.parse(%s), %s, "hero");
    var audio = false;
    for (asset in result.assets)
      if (StringTools.endsWith(StringTools.replace(asset.source, "\\\\", "/"), "notestyles/hero/introGO.ogg")) audio = true;
    if (!audio) throw "library-relative countdown audio was not found: " + result.assets;
    for (finding in result.diagnostics)
      if (finding.message.indexOf("notestyles/funkin/") >= 0 && finding.code.indexOf("missing") >= 0)
        throw "base-game popup reported missing instead of using the native one: " + finding.message;
  }
}''' % (json.dumps(json.dumps(data)), json.dumps(str(library)))
            (Path(folder) / 'Main.hx').write_text(main, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_definitions_and_note_styles_are_found_in_their_own_folders(self):
        module = (ROOT / 'source/ModuleFunctions.hx').read_text()
        definition = module[module.index('static function findVSliceDefinition('):]
        definition = definition[:definition.index('\n\tstatic function ')]
        # The flat <kind>/<id>.json lookup stays first; the own-folder one follows.
        self.assertLess(definition.index("findImportFile(folder, [stem + '.json'])"),
            definition.index('findNamedDirectory(folder, stem)'))
        self.assertIn("findImportFile(own, [stem + '.json'])", definition)
        style = module[module.index('static function findVSliceNoteStyle('):]
        style = style[:style.index('\n\tstatic function ')]
        self.assertIn('findNamedDirectory(base, StringTools.trim(reference))', style)
        self.assertIn("findImportFile(own, [StringTools.trim(reference) + '.json'])", style)
        # Script asset keys may start at their library folder or a sibling
        # library of the same Polymod mod, and never reach outside that mod.
        library = module[module.index('static function findVSliceLibraryFile('):]
        library = library[:library.index('\n\tstatic function ')]
        self.assertIn("findImportFile(mod, ['_polymod_meta.json'])", library)
        hxc = module[module.index('static function findVSliceHxcAsset('):]
        hxc = hxc[:hxc.index('\n\tstatic function ')]
        self.assertIn('findVSliceLibraryFile(sourceRoot, clean, extensions)', hxc)


if __name__ == '__main__':
    unittest.main()
