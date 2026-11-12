"""Tests for model_job.py: billing safety, state machine, Studio branch, tool discovery.

No network, no Tripo calls, no spend: the CLI is always mocked. Set ART_TEST_BLENDER to a Blender
executable to also run the real prepare + 12-view review on a synthetic GLB; otherwise that test is
skipped, not claimed passed.
"""
import importlib.util
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('model_job', HERE / 'model_job.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

MODEL_PAGE = 'https://studio.tripo3d.ai/en/workspace/generate/eb663895-4bac-4256-890a-c3dc9330958b'
GEN_PAGE = 'https://studio.tripo3d.ai/en/workspace/generate'


def tiny_glb(path, half=(1, 1, 1)):
    """A closed box as a self-contained GLB (12 triangles)."""
    x, y, z = half
    vertices = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    indices = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 3, 7, 6, 3, 6, 2, 0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5]
    binary = b''.join(struct.pack('<3f', *v) for v in vertices) + struct.pack('<36H', *indices)
    document = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}],
                'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 96}, {'buffer': 0, 'byteOffset': 96, 'byteLength': 72}],
                'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 8, 'type': 'VEC3', 'min': [-x, -y, -z], 'max': [x, y, z]},
                              {'bufferView': 1, 'componentType': 5123, 'count': 36, 'type': 'SCALAR'}],
                'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1}]}],
                'nodes': [{'mesh': 0}], 'scenes': [{'nodes': [0]}], 'scene': 0}
    body = json.dumps(document).encode(); body += b' ' * (-len(body) % 4)
    Path(path).write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(body) + len(binary)) +
                           struct.pack('<I4s', len(body), b'JSON') + body + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
    return Path(path)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(m, 'STORE', self.root / m.STORE_NAME)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def job(self, provider='api', model='tripo-v3.1'):
        return m.create_job('sample', {'kind': 'text', 'prompt': 'one wooden barrel'}, 1.0, 3000, model, provider)


class Validation(Base):
    def test_asset_id_cannot_escape_storage(self):
        for name in ['../outside', 'a/b', 'C:\\bad', '', '..', 'Barrel']:
            with self.assertRaises(ValueError):
                m.validate_asset_id(name)

    def test_external_glb_dependencies_rejected(self):
        target = self.root / 'asset.glb'
        body = json.dumps({'asset': {'version': '2.0'}, 'buffers': [{'uri': '../secret.bin', 'byteLength': 4}]}).encode()
        body += b' ' * (-len(body) % 4)
        target.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(body)) + struct.pack('<I4s', len(body), b'JSON') + body)
        with self.assertRaises(ValueError):
            m.validate_glb(target)

    def test_size_and_budget_ranges(self):
        for size, tris, axis in [(0, 3000, 'height'), (2000, 3000, 'height'), (1, 50, 'height'), (1, 3000, 'width')]:
            with self.assertRaises(ValueError):
                m.create_job('bad', {'kind': 'text', 'prompt': 'x'}, size, tris, 'tripo-v3.1', 'api', axis)
        job = m.create_job('rock', {'kind': 'text', 'prompt': 'x'}, 40, 200000, 'tripo-v3.1', 'api', 'longest')
        self.assertEqual(m.read(job / 'spec.json')['size_axis'], 'longest')

    def test_job_path_must_be_inside_store(self):
        outside = self.root / 'elsewhere'
        outside.mkdir()
        (outside / 'spec.json').write_text('{}')
        with self.assertRaises(ValueError):
            m.job_path(outside)

    def test_new_job_is_not_approved(self):
        state = m.read(self.job() / 'state.json')
        self.assertEqual(state['status'], 'draft')
        self.assertFalse(state['approved_for_game'])


class Billing(Base):
    def preflight(self):
        return {'valid': True, 'steps': [{'name': 'image-to-model'}], 'candidates': 1, 'generation_credits_estimate': 20}

    def test_budget_failure_never_calls_submit(self):
        job = self.job()
        with patch.object(m, 'invoke', return_value=(0, self.preflight())) as call:
            with self.assertRaises(ValueError):
                m.submit(job, 10)
            self.assertEqual(call.call_count, 1)
            self.assertIn('--dry-run', call.call_args.args[0])
        self.assertEqual(m.read(job / 'state.json')['status'], 'planned')

    def test_multi_step_plan_is_refused(self):
        job = self.job()
        plan = dict(self.preflight(), steps=[{'name': 'generate'}, {'name': 'convert'}])
        with patch.object(m, 'invoke', return_value=(0, plan)):
            with self.assertRaises(ValueError):
                m.plan(job)

    def test_ambiguous_result_cannot_create_second_remote_task(self):
        job = self.job()
        responses = [(0, self.preflight()), (0, {'ok': True}), (7, {'error': 'network interrupted after submission'})]
        with patch.object(m, 'invoke', side_effect=responses) as call:
            with self.assertRaises(ValueError):
                m.submit(job, 20)
            self.assertEqual(m.read(job / 'state.json')['status'], 'needs_reconcile')
            with self.assertRaises(ValueError):
                m.submit(job, 20)
            self.assertEqual(call.call_count, 3)

    def test_watch_timeout_retains_original_task_id(self):
        job = self.job()
        m.update(job, status='submitted', task_id='known-task')
        with patch.object(m, 'invoke', return_value=(6, {'error': 'watch timed out'})) as call:
            state = m.resume(job)
        self.assertEqual(state['task_id'], 'known-task')
        self.assertEqual(call.call_args.args[0][:3], ['task', 'watch', 'known-task'])
        self.assertEqual(state['status'], 'submitted')

    def test_reconcile_cannot_swap_task_id(self):
        job = self.job()
        m.update(job, status='needs_reconcile', task_id='first')
        with self.assertRaises(ValueError):
            m.resume(job, 'second')

    def test_image_change_after_init_is_refused(self):
        image = self.root / 'concept.png'
        image.write_bytes(b'concept-v1')
        job = m.create_job('img', {'kind': 'image', 'file': 'reference.png', 'sha256': m.digest(image)}, 1, 3000, 'tripo-v3.1')
        (job / 'reference.png').write_bytes(b'concept-v2')
        with self.assertRaises(ValueError):
            m.make_args(m.read(job / 'spec.json'), job)

    def test_key_is_redacted_from_cli_output(self):
        class Done:
            returncode = 1
            stdout = json.dumps({'error': 'bad key sk-secret-123'})
            stderr = ''
        with patch.dict(os.environ, {'TRIPO_API_KEY': 'sk-secret-123'}), \
                patch.object(m, 'cli_command', return_value=['node', 'cli.js']), \
                patch.object(m.subprocess, 'run', return_value=Done()):
            code, body = m.invoke(['doctor', '--json'])
        self.assertNotIn('sk-secret-123', json.dumps(body))


class Studio(Base):
    def test_studio_job_never_calls_api(self):
        job = self.job('studio', 'H3.1')
        with patch.object(m, 'invoke') as invoke:
            for op in (lambda: m.plan(job), lambda: m.submit(job, 55), lambda: m.resume(job)):
                with self.assertRaises(ValueError):
                    op()
            invoke.assert_not_called()

    def test_locale_and_plain_urls_accepted_bad_hosts_refused(self):
        for url in (GEN_PAGE, 'https://studio.tripo3d.ai/zh/workspace/generate', 'https://studio.tripo3d.ai/workspace/generate'):
            m.studio_url(url)
        for url in ('http://studio.tripo3d.ai/en/workspace/generate', 'https://evil.example/en/workspace/generate',
                    GEN_PAGE + '?token=abc', 'https://studio.tripo3d.ai/en/pricing'):
            with self.assertRaises(ValueError):
                m.studio_url(url)
        with self.assertRaises(ValueError):
            m.studio_url(GEN_PAGE, asset=True)

    def test_export_restriction_blocks_generation(self):
        job = self.job('studio', 'H3.1')
        m.studio_preflight(job, GEN_PAGE, 55, 200, 'blocked', 'private', False, 'H3.1')
        with self.assertRaises(ValueError):
            m.studio_begin(job, 55)
        self.assertEqual(m.read(job / 'state.json')['status'], 'studio_blocked')

    def test_browser_submission_is_single_use(self):
        job = self.job('studio', 'H3.1')
        m.studio_preflight(job, GEN_PAGE, 55, 200, 'available', 'private', False, 'H3.1')
        m.studio_begin(job, 55)
        with self.assertRaises(ValueError):
            m.studio_begin(job, 55)
        m.studio_record(job, MODEL_PAGE)
        self.assertEqual(m.read(job / 'state.json')['status'], 'studio_submitted')

    def test_cost_over_allowance_blocks(self):
        job = self.job('studio', 'H3.1')
        m.studio_preflight(job, GEN_PAGE, 55, 200, 'available', 'private', False, 'H3.1')
        with self.assertRaises(ValueError):
            m.studio_begin(job, 40)

    def test_browser_download_attaches_without_any_api_call(self):
        job = self.job('studio', 'H3.1')
        source = tiny_glb(self.root / 'browser-download.glb')
        before = m.digest(source)
        m.studio_record(job, MODEL_PAGE, existing=True)
        with patch.object(m, 'invoke') as invoke:
            state = m.studio_attach(job, source)
            invoke.assert_not_called()
        self.assertEqual(state['status'], 'downloaded')
        self.assertEqual(m.digest(job / 'raw' / 'model.glb'), before)
        with self.assertRaises(ValueError):
            m.studio_attach(job, source)

    def test_export_probe_is_explicit_and_cannot_bypass_a_paywall(self):
        job = self.job('studio', 'H3.1')
        state = m.studio_preflight(job, GEN_PAGE, 40, 200, 'unknown', 'private', False, 'H3.1', allow_export_probe=True)
        self.assertEqual(state['studio_preflight']['export_status'], 'unknown')
        self.assertTrue(state['studio_preflight']['export_probe_authorized'])
        job2 = self.job('studio', 'H3.1')
        m.studio_preflight(job2, GEN_PAGE, 40, 200, 'blocked', 'private', False, 'H3.1', allow_export_probe=True)
        with self.assertRaises(ValueError):
            m.studio_begin(job2, 40)

    def test_public_publish_requires_explicit_scope(self):
        job = self.job('studio', 'H3.1')
        m.studio_preflight(job, GEN_PAGE, 55, 200, 'available', 'public', False, 'H3.1')
        with self.assertRaises(ValueError):
            m.studio_begin(job, 55)


class Discovery(Base):
    def test_explicit_env_then_profile_order(self):
        fake = tiny_glb(self.root / 'blender.exe')  # any existing file stands in for the executable
        profile = self.root / 'art' / 'workflow'
        profile.mkdir(parents=True)
        other = tiny_glb(self.root / 'other.exe')
        (profile / 'project-profile.json').write_text(json.dumps({'tools': {'blender': str(other)}}))
        with patch.dict(os.environ, {'BLENDER_EXE': str(fake)}):
            self.assertEqual(m.find_blender(root=self.root), fake)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('BLENDER_EXE', None)
            with patch.object(m.shutil, 'which', return_value=None):
                self.assertEqual(m.find_blender(root=self.root), other)

    def test_missing_explicit_path_is_an_error(self):
        with self.assertRaises(ValueError):
            m.find_blender(self.root / 'nope.exe')

    def test_doctor_reports_without_tools_and_spends_nothing(self):
        with patch.object(m, 'cli_command', side_effect=ValueError('Install the official CLI first')), \
                patch.object(m, 'blender_candidates', return_value=[]), \
                patch.object(m.shutil, 'which', return_value=None), \
                patch.object(m, 'invoke') as invoke:
            os.environ.pop('BLENDER_EXE', None)
            report = m.doctor(self.root)
            invoke.assert_not_called()
        self.assertEqual(report['checks']['tripo_cli']['state'], 'needs setup')
        self.assertEqual(report['checks']['blender']['state'], 'needs setup')
        self.assertFalse(report['ready_for_api_generation'])
        self.assertFalse(report['checks']['gitignore']['covers_store'])

    def test_cli_version_pin_enforced(self):
        bin_dir = self.root / 'npm'
        pkg = bin_dir / 'node_modules' / 'tripo-cli'
        pkg.mkdir(parents=True)
        (pkg / 'package.json').write_text(json.dumps({'version': '0.11.2', 'bin': {'tripo': 'dist/cli.js'}}))
        shim = bin_dir / 'tripo.cmd'
        shim.write_text('')
        with patch.object(m.shutil, 'which', side_effect=lambda n: str(shim) if n.startswith('tripo') else None):
            with self.assertRaises(ValueError):
                m.cli_command()


@unittest.skipUnless(os.environ.get('ART_TEST_BLENDER'), 'set ART_TEST_BLENDER to run the real Blender route')
class BlenderRoute(Base):
    def test_import_local_process_produces_review_set(self):
        source = tiny_glb(self.root / 'rock.glb', half=(3, 1, 0.5))  # longest extent 6 units
        result = subprocess.run([sys.executable, str(HERE / 'model_job.py'), '--root', str(self.root), 'import-local',
                                 '--asset', 'rock', '--height', '2.0', '--size-axis', 'longest', '--file', str(source)],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        job = Path(json.loads(result.stdout)['job'])
        result = subprocess.run([sys.executable, str(HERE / 'model_job.py'), '--root', str(self.root), 'process',
                                 '--job', str(job), '--blender', os.environ['ART_TEST_BLENDER'], '--resolution', '64', '--samples', '1'],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state['status'], 'review_ready')
        report = json.loads((job / 'final' / 'report.json').read_text())
        dims = report['dimensions_m']
        self.assertAlmostEqual(max(dims['x'], dims['y'], dims['z_height']), 2.0, places=3)
        self.assertAlmostEqual(report['ground_z'], 0.0, places=5)
        self.assertEqual(report['triangles'], 12)
        stats = json.loads((job / 'final' / 'review' / 'stats.json').read_text())
        self.assertEqual(len(stats['views']), 14)
        self.assertTrue((job / 'final' / 'review-sheet.png').is_file())
        self.assertEqual(m.digest(job / 'raw' / 'model.glb'), m.digest(source))


if __name__ == '__main__':
    unittest.main()
