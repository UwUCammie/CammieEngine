"""The shared Freeplay look: one palette for Freeplay, options, import and main menus."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source'


def read(name):
    return (SOURCE / name).read_text(encoding='utf-8')


class MenuStyleTest(unittest.TestCase):
    def run_haxe(self, body):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(body, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(SOURCE), '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_palette_is_the_freeplay_palette(self):
        # These are the values Freeplay has always drawn with; changing one changes every screen.
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  check(MenuStyle.SHADE == 0xE6101622 && MenuStyle.BAR == 0xFF101622, 'dim or footer');
  check(MenuStyle.CARD == 0xFF182235 && MenuStyle.CARD_SELECTED == 0xFF354963, 'card colours');
  check(MenuStyle.PINK == 0xFFFF66B7 && MenuStyle.TEAL == 0xFF80E3D0 && MenuStyle.GOLD == 0xFFFFD166, 'accents');
  check(MenuStyle.CREAM == 0xFFFFF4DC && MenuStyle.TEXT == 0xFFCFD8E5 && MenuStyle.MUTED == 0xFF9DB2CC
   && MenuStyle.DISABLED == 0xFF8B97A8, 'text colours');
  check(MenuStyle.PANEL == 0xFF141C2C && MenuStyle.PANEL_ROW == 0xFF2B3C57 && MenuStyle.PANEL_RULE == 0xFF3A4A66
   && MenuStyle.RULE == 0xFF3A4A63 && MenuStyle.DIM == 0xFF05080F, 'popup colours');
  check(MenuStyle.FONT == 'assets/fonts/vcr.ttf', 'font');
  check(MenuStyle.BAR_HEIGHT == 68 && MenuStyle.ROW_HEIGHT == FreeplayBrowserLayout.ROW_HEIGHT
   && MenuStyle.SELECTED_HEIGHT == FreeplayBrowserLayout.SELECTED_HEIGHT && MenuStyle.LIST_TOP == FreeplayBrowserLayout.TOP,
   'geometry drifted from Freeplay');
  check(MenuStyle.CARD_ALPHA == 0.78 && MenuStyle.DETAIL_ALPHA == 0.82, 'card opacity');
 }
}''')

    def test_state_rules_match_freeplay_rows(self):
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  check(MenuStyle.cardColor(0) == MenuStyle.CARD && MenuStyle.cardColor(1) == MenuStyle.CARD_SELECTED, 'card colour ends');
  var half = MenuStyle.cardColor(0.5);
  check(((half >> 16) & 255) > 0x18 && ((half >> 16) & 255) < 0x35, 'card colour does not blend');
  check(MenuStyle.cardColor(-4) == MenuStyle.CARD && MenuStyle.cardColor(9) == MenuStyle.CARD_SELECTED
   && MenuStyle.cardColor(Math.NaN) == MenuStyle.CARD, 'stray focus left the palette');
  check(MenuStyle.cardAlpha(0) == 0.78 && Math.abs(MenuStyle.cardAlpha(1) - 1) < 1e-9, 'card opacity ends');
  check(MenuStyle.titleColor(false, false) == MenuStyle.TEXT && MenuStyle.titleColor(true, false) == MenuStyle.CREAM
   && MenuStyle.titleColor(true, true) == MenuStyle.DISABLED && MenuStyle.titleColor(false, true) == MenuStyle.DISABLED, 'title colours');
  check(MenuStyle.titleScale(0) == 1 && Math.abs(MenuStyle.titleScale(1) - 28 / 22) < 1e-9, 'selected title is not 28 over 22');
  check(MenuStyle.switchLabel(true) == 'ON' && MenuStyle.switchLabel(false) == 'OFF'
   && MenuStyle.switchColor(true) == MenuStyle.TEAL && MenuStyle.switchColor(false) == MenuStyle.MUTED
   && MenuStyle.chipColor(true) != MenuStyle.chipColor(false), 'switch look');
  check(MenuStyle.fillWidth(400, 0.5) == 200 && MenuStyle.fillWidth(400, 7) == 400 && MenuStyle.fillWidth(400, -1) == 0
   && MenuStyle.fillWidth(400, Math.NaN) == 0, 'progress fill is not bounded');
 }
}''')

    def test_row_positions_are_freeplays(self):
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  for (height in [540, 720, 1080]) for (selected in [0, 3]) for (position in [0, 1, 2, 5, 9]) {
   check(MenuStyle.rowTop(position, selected, height) == FreeplayBrowserLayout.centeredRowY(position, selected, height),
    'row ' + position + ' differs from the Freeplay list at ' + height);
  }
  // The selected card is centred; the card below it drops by its extra height.
  var selected = MenuStyle.rowTop(2, 2, 720);
  check(Math.abs(selected + MenuStyle.SELECTED_HEIGHT / 2 - 360) < 1e-9, 'selection not centred');
  check(MenuStyle.rowTop(3, 2, 720) - selected == MenuStyle.SELECTED_HEIGHT, 'row under the selection did not drop');
  check(MenuStyle.rowTop(1, 2, 720) - MenuStyle.rowTop(0, 2, 720) == MenuStyle.ROW_HEIGHT, 'idle rows are not compact');
  check(MenuStyle.rowFits(selected, MenuStyle.SELECTED_HEIGHT, 720), 'selected card does not fit');
  check(!MenuStyle.rowFits(MenuStyle.rowTop(40, 0, 720), MenuStyle.ROW_HEIGHT, 720), 'a far row is drawn');
  check(!MenuStyle.rowFits(MenuStyle.rowTop(-40, 0, 720), MenuStyle.ROW_HEIGHT, 720), 'a row above the header is drawn');
 }
}''')

    def test_stacks_scroll_and_fit_their_region(self):
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  // A stack drops the cards under the open one by its extra height.
  check(MenuStyle.stackTop(0, 0, 100, 44, 92, 4) == 100 && MenuStyle.stackTop(1, 0, 100, 44, 92, 4) == 100 + 44 + 4 + 48, 'open card did not push the next one down');
  check(MenuStyle.stackTop(2, 3, 100, 44, 92, 4) == 100 + 2 * 48, 'cards above the open one moved');
  check(MenuStyle.stackHeight(0, 44, 92, 4) == 0 && MenuStyle.stackHeight(1, 44, 92, 4) == 92 && MenuStyle.stackHeight(3, 44, 92, 4) == 2 * 48 + 92, 'stack height');
  // A short stack never scrolls; a long one keeps the open card centred and stops at its ends.
  check(MenuStyle.stackScroll(2, 4, 44, 92, 4, 540) == 0, 'a short stack scrolled');
  var region = 540.0;
  for (selected in 0...20) {
   var scroll = MenuStyle.stackScroll(selected, 20, 44, 92, 4, region);
   var top = MenuStyle.stackTop(selected, selected, 100, 44, 92, 4) - scroll;
   check(MenuStyle.fitsRegion(top, 92, 100, 100 + region), 'row ' + selected + ' of 20 is out of view');
   check(scroll >= 0 && scroll <= MenuStyle.stackHeight(20, 44, 92, 4) - region + 1e-9, 'scroll left the stack');
  }
  check(MenuStyle.fitsRegion(100, 44, 100, 640) && !MenuStyle.fitsRegion(60, 44, 100, 640) && !MenuStyle.fitsRegion(620, 44, 100, 640), 'region test');
 }
}''')

    def test_main_menu_keeps_every_native_row_reachable(self):
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  check(MainMenuLayout.capacity(720) >= 6, 'story, freeplay, donate, options, import and costumes must all fit');
  for (count in 1...MainMenuLayout.capacity(720) + 1) for (selected in 0...count) {
   var last = -1000.0;
   for (index in 0...count) {
    check(MainMenuLayout.shown(index, selected, count, 720), 'row ' + index + ' hidden with ' + count + ' rows');
    var top = MainMenuLayout.rowTop(index, selected, count, 720);
    check(top > last, 'rows are out of order');
    last = top;
   }
  }
  // A longer menu scrolls to keep the chosen row in view, and the stack is centred when short.
  for (selected in 0...12) check(MainMenuLayout.shown(selected, selected, 12, 720), 'the chosen row of twelve is hidden');
  check(MainMenuLayout.stackStart(4, 720) > MainMenuLayout.REGION_TOP, 'a short stack is not centred');
  check(MainMenuLayout.stackStart(6, 720) >= MainMenuLayout.REGION_TOP, 'a full stack rose above its region');
  // The context panel is level with the highlighted card and stays on screen for every entry.
  for (count in [4, 5, 6]) for (selected in 0...count) {
   var selectedTop = MainMenuLayout.rowTop(selected, selected, count, 720);
   for (height in [120, 200, 340]) {
    var panel = MainMenuLayout.stageTop(selectedTop, height, 720);
    check(panel >= MainMenuLayout.REGION_TOP - 20 && panel + height <= 640, 'the context panel leaves its region');
    check(height > 200 || Math.abs(panel - selectedTop) < 1e-9 || panel + height >= 639, 'the panel is not level with its card');
   }
  }
  check(MainMenuFacts.middleEllipsis('short/path', 40) == 'short/path', 'a short path was cut');
  var long = 'C:/Users/uwucammie/Documents/coding/FNF/fnf_example_mods/psych/Ugh Moment';
  for (limit in [30, 40, 54, 70]) {
   var cut = MainMenuFacts.middleEllipsis(long, limit);
   check(cut.length <= limit && cut.indexOf('...') > 0 && cut.substr(cut.length - 'Ugh Moment'.length) == 'Ugh Moment' && cut.indexOf('C:/') == 0, 'path ellipsis ' + limit + ': ' + cut);
  }
  var tiny = MainMenuFacts.middleEllipsis(long, 12);
  check(tiny.length <= 12 && tiny.substr(tiny.length - 3) == 'ent', 'a tiny budget lost the folder name: ' + tiny);
 }
}''')

    def test_main_menu_facts_are_short_and_sized_to_their_rows(self):
        self.run_haxe(r'''class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function main() {
  check(MainMenuFacts.plural(1, 'week', 'weeks') == '1 week' && MainMenuFacts.plural(12, 'week', 'weeks') == '12 weeks', 'plural');
  check(MainMenuFacts.pathTail('C:\\mods\\Ugh Moment\\') == 'Ugh Moment' && MainMenuFacts.pathTail('/a/b/c') == 'c'
   && MainMenuFacts.pathTail('') == '' && MainMenuFacts.pathTail('/x/' + [for (i in 0...60) 'y'].join(''), 10).length == 10, 'path tail');
  var story = MainMenuFacts.story(8);
  check(story.big == '8 weeks' && story.rows.length == 0, 'story facts');
  check(MainMenuFacts.freeplay(381, 0, 0).rows.length == 1 && MainMenuFacts.freeplay(381, 3, 2).rows.length == 2, 'freeplay rows');
  var options = MainMenuFacts.options({downscroll: true, midscroll: false, useCustomInput: true, fpsCap: 120, offset: 20}, 'save0');
  check(options.rows.length <= MainMenuLayout.FACT_ROWS, 'too many option rows');
  var shown = [for (row in options.rows) row.label + '=' + row.value].join('|');
  check(shown.indexOf('Scroll direction=Down') >= 0 && shown.indexOf('Middlescroll=Off') >= 0 && shown.indexOf('120 FPS') >= 0
   && shown.indexOf('20 ms') >= 0 && shown.indexOf('save0') >= 0, 'option rows ' + shown);
  var busy = MainMenuFacts.importer(4, true, 'Checking saved imports', 'Auto', '');
  check(busy.big == 'Refreshing' && busy.sub == 'Checking saved imports', 'import status');
  var idle = MainMenuFacts.importer(1, false, '', 'Psych', 'C:/mods/Ugh Moment');
  check(idle.big == '1 mod ready' && idle.rows[1].value == 'Ugh Moment', 'import facts');
  // While the saved imports are still being checked the count is unknown: say so, never '0 mods ready'.
  var unknown = MainMenuFacts.importer(0, false, '', 'Auto', '', true);
  check(unknown.big == 'Checking...' && unknown.big.indexOf('0') < 0 && unknown.sub != 'Add songs and mods from other engines.', 'import count shown before it is known: ' + unknown.big);
  check(MainMenuFacts.importer(0, false, '', 'Auto', '', false).big == '0 mods ready', 'the settled count is still shown');
  check(MainMenuFacts.importer(3, true, 'Refreshing import: Ugh', 'Auto', '', true).big == 'Refreshing', 'a running refresh keeps its own heading');
  var unknownFreeplay = MainMenuFacts.freeplay(381, 0, 0, true);
  check(unknownFreeplay.rows[0].value == 'Checking...' && unknownFreeplay.sub.indexOf('Every song in the base game') < 0, 'freeplay ready count shown before it is known');
  check(MainMenuFacts.freeplay(381, 0, 0, false).rows[0].value == '0', 'the settled freeplay count is still shown');
  for (fact in [story, options, idle, MainMenuFacts.plain('X', 'Y', 'Z', MenuStyle.TEAL)])
   check(MainMenuFacts.panelHeight(fact) >= 100 && MainMenuFacts.panelHeight(fact) < 400, 'panel height');
  check(MainMenuFacts.panelHeight(options) > MainMenuFacts.panelHeight(story), 'a panel does not grow with its rows');
 }
}''')

    def test_footer_hints_fit_beside_the_screen_title(self):
        self.run_haxe(r'''import MenuStyle.MenuHint;
class Main {
 static function check(ok:Bool, m:String):Void if (!ok) throw m;
 static function fits(name:String, hints:Array<MenuHint>) {
  check(hints.length > 0, name + ' has no hints');
  for (hint in hints) check(hint.key != '' && hint.action != '', name + ' has an empty hint');
  var room = MenuStyle.hintsRoom(1280);
  check(MenuStyle.hintsWidth(hints) <= room, name + ' hints run under the title: ' + MenuStyle.hintsWidth(hints) + ' of ' + room);
 }
 static function main() {
  fits('freeplay', FreeplayPulse.hints());
  fits('importer', MenuHints.importer());
  fits('main menu', MenuHints.mainMenu());
  for (inOptions in [false, true]) for (inSection in [false, true]) for (open in [false, true]) for (confirm in [false, true])
   for (edit in [false, true]) for (saves in [false, true])
    fits('options', MenuHints.options(inOptions, inSection, open, confirm, edit, saves));
  // What each step offers.
  check(MenuHints.options(true, false, false, false, true, true).map(function(h) return h.key).indexOf('LEFT/RIGHT') >= 0, 'saves are unreachable');
  check(MenuHints.options(true, false, false, false, true, false).map(function(h) return h.key).indexOf('LEFT/RIGHT') < 0, 'saves offered without the save menu');
  check(MenuHints.options(false, false, false, true, true, true)[0].action == 'Erase', 'erase is not confirmed');
  check(MenuHints.options(true, true, false, false, true, true).map(function(h) return h.action).indexOf('Sections') >= 0, 'no way back from a section');
 }
}''')


class FreeplayUsesTheSharedStyleTest(unittest.TestCase):
    def test_freeplay_takes_its_look_from_the_helper(self):
        state = read('FreeplayState.hx')
        row = read('FreeplayBrowserRow.hx')
        sections = read('FreeplayDetailSections.hx')
        library = read('LibraryMenuSubState.hx')
        for source in (state, row, sections, library):
            self.assertIn('MenuStyle.', source)
        # The palette literals now live in MenuStyle alone.
        for literal in ('0xFF182235', '0xFF354963', '0xFF101622', '0xFFFF66B7', '0xFF80E3D0', '0xFFFFD166',
                        '0xFFFFF4DC', '0xFFCFD8E5', '0xFF9DB2CC', '0xFF8B97A8', '0xFF141C2C', '0xFF2B3C57', '0xE6101622'):
            for name, source in (('FreeplayState', state), ('FreeplayBrowserRow', row),
                                 ('FreeplayDetailSections', sections), ('LibraryMenuSubState', library)):
                self.assertNotIn(literal, source, name + ' still hard-codes ' + literal)
        self.assertIn('MenuWidgets.backdrop()', state)
        self.assertIn('MenuWidgets.shade()', state)
        self.assertIn("new MenuFooter('FREEPLAY', FreeplayPulse.hints(), false)", state)
        self.assertIn('MenuStyle.cardAlpha(motion.focus)', row)
        self.assertIn('MenuStyle.titleColor(selected, disabled)', row)
        self.assertIn('MenuWidgets.panel(state, x, y, width, height)', library)

    def test_helper_has_no_display_objects_and_widgets_read_it(self):
        style = read('MenuStyle.hx')
        self.assertNotIn('import flixel', style)
        for name in ('MenuWidgets.hx', 'MenuCard.hx', 'MenuFooter.hx', 'MenuButton.hx'):
            source = read(name)
            self.assertIn('MenuStyle.', source, name)
            self.assertIsNone(re.search(r'0xFF[0-9A-Fa-f]{6}', source.replace('0xFF000000', '')), name + ' has its own palette')

    def test_footer_reproduces_freeplays_hint_row(self):
        footer = read('MenuFooter.hx')
        for expected in ('FlxG.height - 31', 'MenuStyle.GOLD', 'MenuStyle.MUTED', 'MenuStyle.RULE',
                         'FlxG.width - 244, FlxG.height - 13, 226, 5', 'MenuStyle.HEADING_SIZE', 'angle = -2',
                         'key.width + 5', 'action.width + 10', 'hintX += 12'):
            self.assertIn(expected, footer)


class ScreensUseTheSharedStyleTest(unittest.TestCase):
    def test_options_screen_is_built_from_cards_and_keeps_its_behaviour(self):
        options = read('SaveDataState.hx')
        for expected in ('MenuWidgets.backdrop()', 'new MenuCard(', 'new MenuFooter(', 'MenuWidgets.sizedPanel(',
                         'MenuHints.options(', 'new SaveFile(i, SAVE_WIDTH)', 'layoutStack(optionCards,'):
            self.assertIn(expected, options)
        self.assertNotIn('Alphabet', options)
        self.assertNotIn('0xFF7194fc', options)
        # Navigation, sounds, saving and the slide between saves and options are unchanged.
        for expected in ('controls.UP_MENU', 'controls.DOWN_MENU', 'controls.RIGHT_MENU || controls.LEFT_MENU',
                         "playMenuSound('scroll')", "playMenuSound('confirm')", "playMenuSound('cancel')",
                         'saveOptions();', 'OptionsCategories.move(categoryOptions, optionsSelected, change)',
                         'FlxTween.num(FlxG.camera.scroll.x, x, 0.1', 'ImportMenuNavigationPolicy.optionsActionAllowed'):
            self.assertIn(expected, options)
        for target in ('new ControlsState()', 'new CalibrationState()', 'new CreditsState()', 'new ModuleState()',
                       'new SelectSortState()', 'new CategoryState()'):
            self.assertIn(target, options)

    def test_save_slots_keep_their_state_machine(self):
        slot = read('SaveFile.hx')
        self.assertIn('class SaveFile extends MenuCard', slot)
        for expected in ('public var beingSelected:Bool', 'public var askingToConfirm:Bool', 'public var selectingLoad:Bool = true',
                         'public function askToConfirm(', 'public function beSelected(', 'public function changeSelection()',
                         'curFrame = turnOn ? 1 : 0'):
            self.assertIn(expected, slot)
        self.assertIn('Erase this save for good?', slot)

    def test_importer_uses_cards_and_buttons_and_keeps_its_workflow(self):
        screen = read('ImportSettingsState.hx')
        for expected in ('MenuWidgets.background(this)', 'new MenuButton(', 'MenuWidgets.sizedPanel(', 'MenuHints.importer()',
                         'progressPresentation.setMenuLane(', 'new MenuCard(stepNames[index]', 'function refreshPanels()'):
            self.assertIn(expected, screen)
        self.assertNotIn('FlxUIButton', screen)
        self.assertNotIn('FlxColor.WHITE, CENTER, OUTLINE', screen)
        for expected in ('ImportWorkflow.beginSongScan(', 'ImportWorkflow.beginSongImport(', 'detachImportAndLeave()',
                         'new ImportPackageNameSubState(', 'scanButton.active = !busy && sourceValid',
                         'new MainMenuState()'):
            self.assertIn(expected, screen)
        prompt = read('ImportPackageNameSubState.hx')
        self.assertIn('MenuWidgets.panel(this, x, y, width, height)', prompt)
        self.assertIn('new MenuButton(', prompt)
        self.assertNotIn('FlxUIButton', prompt)

    def test_progress_cards_use_the_shared_look(self):
        bar = read('ImportRefreshProgressBar.hx')
        update = read('UpdateProgressBar.hx')
        for source in (bar, update):
            self.assertIn('MenuStyle.PANEL', source)
            self.assertIn('MenuStyle.TEAL', source)
            self.assertIn('MenuStyle.PINK', source)
        self.assertIn('MenuStyle.AMBER', bar)

    def test_main_menu_is_a_card_list_and_keeps_its_routes(self):
        menu = read('MainMenuState.hx')
        for expected in ('new MenuCard(rowLabel(optionShit[i])', 'MainMenuLayout.rowTop(', 'new MenuFooter(', 'MenuHints.mainMenu()',
                         'MainMenuFacts.', 'function refreshFacts()', 'snapshot.inspectionPending',
                         'MenuWidgets.backdrop()', 'FlxFlicker.flicker(magenta, 1.1, 0.15, false)', 'spr.flicker(1, 0.06',
                         "FlxTween.tween(spr, {opacity: 0}, 0.4", 'mainActionAllowed(importWorkBusy'):
            self.assertIn(expected, menu)
        for route in ('new StoryMenuState()', 'FreeplayState.openHostLibrary()', 'new FreeplayState()', 'new SaveDataState()',
                      'new ImportSettingsState()', 'new TitleState()', 'new CodenameImportedModsState()'):
            self.assertIn(route, menu)
        self.assertIn("'story mode', 'freeplay'#if sys, 'online'#end, 'donate', 'options'#if sys, 'import'#end", menu)
        for hxc in ('hxcMountMenuOverlay', 'hxcClearMenuOverlay', 'hxcAddCostumeMenuItem', 'updateHxcMenuOverlay'):
            self.assertIn(hxc, menu)
        self.assertNotIn('FNF_main_menu_assets', menu)

    def test_native_probe_captures_every_restyled_screen(self):
        probe = read('RuntimeMenuStyleProbe.hx')
        for name in ('freeplay', 'options-sections', 'options-rows', 'options-saves', 'main-menu', 'import', 'import-name'):
            self.assertIn("'" + name, probe)
        self.assertIn('RuntimeMenuStyleProbe.enabled()', read('RuntimeSmokeHarness.hx'))
        self.assertIn('--verify-menu-style', probe)


if __name__ == '__main__':
    unittest.main()
