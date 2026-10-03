from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract(source, start_marker, end_marker):
    return source[source.index(start_marker):source.index(end_marker)]


class CategorySearchTest(unittest.TestCase):
    """The freeplay *category* menu has a type-to-search like the chart list.

    Matching must be normalization-based (so "week 2" finds "Week-2"), the
    selection must hop over hidden entries, and the two searches must share the
    same normalization/wrap helpers so they cannot drift apart.
    """

    def test_category_search_matching_and_navigation(self):
        freeplay = (ROOT / 'source/FreeplayState.hx').read_text()
        category = (ROOT / 'source/CategoryState.hx').read_text()

        search_norm = extract(freeplay, '\tpublic static function searchNorm(', '\tfunction songMatches(')
        next_visible = extract(freeplay, '\tpublic static function nextVisibleSelection(', '\n\tfunction changeSelection(')
        # the extracted instance methods are re-declared static in the fixture so
        # a single static main() can drive them
        def as_static(text, name):
            return text.replace('\tfunction ' + name + '(', '\tpublic static function ' + name + '(')

        cat_search_norm = as_static(extract(category, '\tfunction searchNorm(', '\tfunction categoryMatches('), 'searchNorm')
        category_matches = as_static(extract(category, '\tfunction categoryMatches(', '\tfunction anyVisibleCategories('), 'categoryMatches')
        any_visible = as_static(extract(category, '\tfunction anyVisibleCategories(', '\n\tfunction applySearchFilter('), 'anyVisibleCategories')

        fixture = ('class FreeplayState {\n' + search_norm + next_visible + '\n}\n'
                   + 'class Cat {\n'
                   ' static var searchString:String = "";\n'
                   ' static var categories:Array<String> = ["All", "Base Game", "Week-2", "VS Impostor"];\n'
                   + cat_search_norm + category_matches + any_visible +
                   '''
 public static function run(){
  // normalization drops case, spaces, dashes and symbols
  if (FreeplayState.searchNorm("Week-2") != "week2") throw 'norm: ' + FreeplayState.searchNorm("Week-2");
  if (FreeplayState.searchNorm("VS Impostor!") != "vsimpostor") throw 'norm: ' + FreeplayState.searchNorm("VS Impostor!");

  // empty search matches everything
  searchString = "";
  for (i in 0...categories.length) if (!categoryMatches(i)) throw 'empty search must match all';
  if (!anyVisibleCategories()) throw 'empty search must leave something visible';

  // "week 2" (with a space) finds "Week-2" - the point of normalization
  searchString = "week 2";
  if (!categoryMatches(2)) throw 'week 2 should match Week-2';
  if (categoryMatches(1)) throw 'week 2 must not match Base Game';
  // spaces are optional: "week2" matches too
  searchString = "week2";
  if (!categoryMatches(2)) throw 'week2 should match Week-2';

  // a nonsense search hides everything and does not claim otherwise
  searchString = "zzzz";
  for (i in 0...categories.length) if (categoryMatches(i)) throw 'nothing should match zzzz';
  if (anyVisibleCategories()) throw 'no category should be visible';

  // moving skips hidden entries: with "week2" only index 2 is visible, so any
  // change lands back on it and the selection never escapes the filtered list
  searchString = "week2";
  var m = categoryMatches;
  if (FreeplayState.nextVisibleSelection(2, 1, categories.length, m) != 2) throw 'down must stay on the only match';
  if (FreeplayState.nextVisibleSelection(2, -1, categories.length, m) != 2) throw 'up must stay on the only match';
  // change==0 hops forward onto the next matching entry
  if (FreeplayState.nextVisibleSelection(0, 0, categories.length, m) != 2) throw 'change 0 must hop to the match';
  // shift-navigation steps over the filtered-out ones too
  searchString = "";
  if (FreeplayState.nextVisibleSelection(0, 5, categories.length, m) != 1) throw 'shift 5 must wrap 0->1';
  FreeplayState.nextVisibleSelection(0, 0, 0, m); // empty list stays put, no div-by-zero
 }
}
class CategorySearchMain {
 static function main(){
  Cat.run();
 }
}
''')

        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'CategorySearchMain.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'CategorySearchMain', '--interp'],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_category_state_shares_freeplay_search_helpers(self):
        # both searches must use the same normalization + skip helpers rather
        # than keeping private copies that could drift
        category = (ROOT / 'source/CategoryState.hx').read_text()
        freeplay = (ROOT / 'source/FreeplayState.hx').read_text()
        self.assertIn('FreeplayState.searchNorm(', category)
        self.assertIn('FreeplayState.nextVisibleSelection(', category)
        self.assertIn('public static function searchNorm(', freeplay)
        self.assertIn('public static function nextVisibleSelection(', freeplay)

    def test_category_state_has_search_bar_and_filtering(self):
        category = (ROOT / 'source/CategoryState.hx').read_text()
        # the search strip, its handler and the hide/hop wiring must all exist
        self.assertIn('searchBG', category)
        self.assertIn('applySearchFilter()', category)
        self.assertIn('categoryMatches(', category)
        # typing must not move the selection on the same frame
        self.assertIn('typedChar.length == 0', category)
        # backspace is a search key, escape clears/leaves
        self.assertIn('FlxG.keys.justPressed.BACKSPACE', category)
        self.assertIn('!FlxG.keys.justPressed.BACKSPACE', category)
        # shift = 5-at-a-time, matching the chart search
        self.assertIn('FlxG.keys.pressed.SHIFT ? -5 : -1', category)
        self.assertIn('FlxG.keys.pressed.SHIFT ? 5 : 1', category)
        # hidden entries are tucked away rather than left as gaps
        self.assertIn('item.visible = vis', category)

    def test_typing_z_does_not_accept_or_launch(self):
        # Z and SPACE are bound to ACCEPT, and Q/E/W/S/A/D to menu actions, so a
        # keystroke that typed a character must not also accept/open. Without
        # this, typing "z" into the category search launched the highlighted
        # category (and the same bug existed in FreeplayState's chart search).
        for name in ('source/CategoryState.hx', 'source/FreeplayState.hx'):
            text = (ROOT / name).read_text()
            self.assertIn('controls.ACCEPT && typedChar.length == 0', text, name)
            self.assertIn('!FlxG.keys.justPressed.SPACE', text, name)
            # the accept check must come after typedChar is known
            self.assertLess(text.index('var typedChar:String = ""'), text.index('var accepted ='), name)

    def test_clearing_search_unhides_the_list(self):
        # `applySearchFilter` must refresh the rows when clearing a query. The
        # category screen relayouts its full list; Freeplay rematerializes the
        # bounded row window around the still-global song selection.
        for name in ('source/CategoryState.hx', 'source/FreeplayState.hx'):
            text = (ROOT / name).read_text()
            body = text[text.index('function applySearchFilter()'):]
            body = body[:body.index('\n\t}')]
            if name.endswith('FreeplayState.hx'):
                self.assertIn('rebuildVisibleRows()', body, name)
                self.assertIn('function rebuildVisibleRows()', text, name)
            else:
                self.assertIn('applyListLayout()', body, name)
                # the layout work must be shared, not duplicated inline
                self.assertIn('function applyListLayout()', text, name)


if __name__ == '__main__':
    unittest.main()
