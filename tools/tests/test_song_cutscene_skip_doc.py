"""The song cutscene list documents the key that really skips it."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SongCutsceneSkipDocTest(unittest.TestCase):
	def test_comment_names_the_skip_key(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		field = play.index('var songCutscenes:')
		above = play[play.rindex('}', 0, field):field]
		self.assertIn('CutsceneSkipKey', above)
		self.assertNotIn('Enter', above)
		self.assertNotIn('Advance an explicitly skipped event video', play)


if __name__ == '__main__':
	unittest.main()
