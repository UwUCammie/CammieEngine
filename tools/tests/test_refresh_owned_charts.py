"""Owner-scoped chart refresh keeps title and audio identity guards."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'refresh_owned_charts', ROOT / 'tools/refresh_owned_charts.py')
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)
OWNER = 'assets/imported_mods/example-owner'
CHART = 'assets/data/example/example-hard.json'


class OwnedChartRefreshTest(unittest.TestCase):
    def test_allows_case_only_storage_title_change_with_same_owner(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            preview, runtime = root / 'preview', root / 'runtime'
            for base, song in ((preview, 'example'), (runtime, 'Example')):
                chart = base / CHART
                chart.parent.mkdir(parents=True)
                chart.write_text(json.dumps({'song': {'song': song, 'notes': []}}))
                (chart.parent / 'compatScripts.json').write_text(
                    json.dumps({'selectedRoot': OWNER}))
            (runtime / 'assets/data/options.json').write_text('{}')
            plan = refresh.make_plan(preview, runtime, OWNER, [CHART])
            self.assertEqual(len(plan['charts']), 1)

            (runtime / CHART).write_text(json.dumps(
                {'song': {'song': 'Unrelated', 'notes': []}}))
            with self.assertRaisesRegex(ValueError, 'audio identity'):
                refresh.make_plan(preview, runtime, OWNER, [CHART])

            (runtime / CHART).write_text(json.dumps(
                {'song': {'song': 'Example', 'notes': []}}))
            (runtime / CHART).parent.joinpath('compatScripts.json').write_text(
                json.dumps({'selectedRoot': 'assets/imported_mods/foreign'}))
            with self.assertRaisesRegex(ValueError, 'owner mismatch'):
                refresh.make_plan(preview, runtime, OWNER, [CHART])


if __name__ == '__main__':
    unittest.main()
