"""Psych and NV bars share their fill, clip and alpha maths.

Behaviour against both donor Bar classes is pinned by test_source_bar_contract;
this keeps the two dialect classes on the one shared copy."""
import unittest

from haxe_test_support import ROOT


class SourceBarSharedHelpersTest(unittest.TestCase):
    def read(self, name):
        return (ROOT / 'source' / name).read_text(encoding='utf-8')

    def test_both_bars_use_the_shared_fill_and_clip(self):
        for name, remake in (('PsychSourceBar.hx', 'false'), ('NightmareVisionBar.hx', 'true')):
            text = self.read(name)
            self.assertIn('SourceBarLayout.percentFor(valueFunction, bounds.min, bounds.max)', text, name)
            self.assertIn('SourceBarLayout.regenerateClip(leftBar, bg, ' + remake + ')', text, name)
            self.assertIn('SourceBarLayout.regenerateClip(rightBar, bg, ' + remake + ')', text, name)
            self.assertNotIn('FlxMath.remapToRange', text, name + ' keeps its own fill maths')
            self.assertNotIn('new FlxRect(', text, name + ' keeps its own clip reset')

    def test_fill_percent_does_not_box_on_native(self):
        # update() runs every frame for every bar; a Null<Float> local boxes on hxcpp.
        text = self.read('SourceBarLayout.hx')
        start = text.index('public static function percentFor(')
        body = text[start:text.index('\n\t}', start)]
        self.assertNotIn('Null<Float>', body)

    def test_nv_alpha_multiplier_is_shared(self):
        for name in ('NightmareVisionBar.hx', 'NightmareVisionHealthIcon.hx'):
            text = self.read(name)
            self.assertIn('SourceBarLayout.multipliedAlpha(v, alphaMultipler)', text, name)
            self.assertNotIn('v *= alphaMultipler', text, name)


if __name__ == '__main__':
    unittest.main()
