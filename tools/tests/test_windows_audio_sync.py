"""Bundled Windows audio is copied incrementally without walking imports."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import sync_windows_audio as sync

ROOT = Path(__file__).resolve().parents[2]


class WindowsAudioSyncTest(unittest.TestCase):
    def test_missing_and_changed_audio_copy_but_current_files_are_reused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            repo = Path(folder) / 'repo'
            runtime = Path(folder) / 'runtime'
            source = repo / 'assets/songs/tutorial/Inst.ogg'
            source.parent.mkdir(parents=True)
            runtime.mkdir()
            source.write_bytes(b'bundled audio')
            with patch.object(sync.subprocess, 'check_output', return_value=b'assets/songs/tutorial/Inst.ogg\0') as listed:
                self.assertEqual(sync.sync_audio(runtime, repo), 1)
                self.assertEqual(sync.sync_audio(runtime, repo), 0)
                source.write_bytes(b'updated bundled audio')
                self.assertEqual(sync.sync_audio(runtime, repo), 1)
            self.assertEqual((runtime / 'assets/songs/tutorial/Inst.ogg').read_bytes(), source.read_bytes())
            self.assertEqual(listed.call_args.args[0][-2:], ['assets/songs', 'assets/music'])

    def test_missing_bundled_source_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            root = Path(folder)
            with patch.object(sync.subprocess, 'check_output', return_value=b'assets/songs/missing.ogg\0'):
                with self.assertRaisesRegex(ValueError, 'source is missing'):
                    sync.sync_audio(root, root)
