#!/usr/bin/env python3
"""One generated 3D model per job: concept image -> Tripo -> faithful Blender prep -> review set.

    python model_job.py --root <project> doctor
    python model_job.py --root <project> init --asset barrel --height 1.1 --image concept.png --image-source "Midjourney v8"
    python model_job.py --root <project> plan    --job <job>
    python model_job.py --root <project> submit  --job <job> --max-estimated-credits 40
    python model_job.py --root <project> resume  --job <job> [--task-id ID]
    python model_job.py --root <project> process --job <job> [--blender PATH]
    python model_job.py --root <project> status  --job <job>

Studio (web credits, driven by a browser agent): studio-preflight / studio-begin /
studio-record / studio-attach, then process. A local GLB: import-local, then process.

Jobs live in <project>/.asset-workflow/<asset>/<job>/ (keep it out of version control and
engine import). One job = one generation attempt; a revision is a new job. Raw downloads
are never modified. Nothing here retries, resubmits, or switches credit wallets.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE_NAME = '.asset-workflow'
# Dry-run JSON (valid / steps / candidates / generation_credits_estimate) was verified on this
# version. Re-check that format before changing the pin; a newer CLI is not assumed compatible.
PINNED_CLI = '0.8.1'
STORE = None  # set from --root in main(); tests patch it


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def validate_asset_id(value):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', value or ''):
        raise ValueError('asset ID must use lowercase English letters, digits, _ or -, starting with a letter')
    return value


def initial_state():
    return {'status': 'draft', 'approved_for_game': False, 'updated_at': stamp()}


def require_submittable(state):
    if state['status'] not in ('draft', 'planned'):
        raise ValueError('Generation already attempted or a local asset exists. Resume its task; do not submit again.')


def validate_glb(path):
    path = Path(path)
    with path.open('rb') as f:
        header = f.read(20)
        if len(header) != 20:
            raise ValueError('Incomplete GLB header')
        magic, version, size, chunk_size, kind = struct.unpack('<4sIIII', header)
        if magic != b'glTF' or version != 2 or size != path.stat().st_size or kind != 0x4E4F534A or chunk_size > size - 20:
            raise ValueError('Invalid or truncated GLB')
        content = json.loads(f.read(chunk_size))
    if content.get('asset', {}).get('version') != '2.0':
        raise ValueError('Only GLB / glTF 2.0 is supported')
    for collection in ('buffers', 'images'):
        for item in content.get(collection, []):
            uri = item.get('uri', '')
            if uri and not uri.startswith('data:'):
                raise ValueError('Model must embed its buffers and textures; external URIs are not accepted')
    return content


@contextlib.contextmanager
def locked(job):
    f = (job / 'operation.lock').open('a+b')
    try:
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        raise ValueError('Another operation owns this job; wait for it to finish')
    try:
        yield
    finally:
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def job_path(value):
    job = Path(value).resolve()
    store = Path(STORE).resolve()
    if store not in job.parents or not (job / 'spec.json').is_file():
        raise ValueError(f'Not a job under {store}')
    return job


def update(job, **values):
    state = read(job / 'state.json')
    state.update(values, updated_at=stamp())
    write(job / 'state.json', state)
    return state


# ---------------------------------------------------------------- tool discovery

def profile_tools(root):
    profile = Path(root) / 'art' / 'workflow' / 'project-profile.json'
    try:
        return read(profile).get('tools', {}) if profile.is_file() else {}
    except (OSError, ValueError):
        return {}


def blender_candidates(root=None):
    """Explicit settings first, then PATH, then common install locations. Never installs anything."""
    found = []
    env = os.environ.get('BLENDER_EXE')
    if env:
        found.append(('env BLENDER_EXE', env))
    if root:
        path = profile_tools(root).get('blender')
        if isinstance(path, str) and path:
            found.append(('project profile tools.blender', path))
    which = shutil.which('blender')
    if which:
        found.append(('PATH', which))
    patterns = []
    if os.name == 'nt':
        for base in {os.environ.get('ProgramFiles', r'C:\Program Files'), r'C:\Program Files', r'D:\Program Files'}:
            patterns.append(os.path.join(base, 'Blender Foundation', '*', 'blender.exe'))
        for drive in 'CDEFG':
            for steam in (r'{}:\Program Files (x86)\Steam', r'{}:\SteamLibrary', r'{}:\Steam'):
                patterns.append(os.path.join(steam.format(drive), 'steamapps', 'common', 'Blender', 'blender.exe'))
    elif sys.platform == 'darwin':
        patterns += ['/Applications/Blender.app/Contents/MacOS/Blender',
                     os.path.expanduser('~/Applications/Blender.app/Contents/MacOS/Blender')]
    else:
        patterns += ['/usr/bin/blender', '/snap/bin/blender', os.path.expanduser('~/.steam/steam/steamapps/common/Blender/blender')]
    for pattern in patterns:
        for hit in sorted(glob.glob(pattern), reverse=True):
            found.append(('common location', hit))
    seen, unique = set(), []
    for source, path in found:
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key); unique.append((source, path))
    return unique


def find_blender(explicit=None, root=None):
    if explicit:
        if not Path(explicit).is_file():
            raise ValueError(f'Blender not found at {explicit}')
        return Path(explicit)
    for _, path in blender_candidates(root):
        if Path(path).is_file():
            return Path(path)
    raise ValueError('Blender not found. Pass --blender, set BLENDER_EXE, or record tools.blender in the project profile.')


def blender_version(path):
    try:
        out = subprocess.run([str(path), '--factory-startup', '--version'], capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=90).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    m = re.search(r'Blender\s+(\d+\.\d+(?:\.\d+)?)', out)
    return (m.group(1) if m else None), None


def cli_command():
    # Invoke node directly: no cmd.exe interpretation of user prompts or paths.
    shim = shutil.which('tripo.cmd') or shutil.which('tripo')
    if not shim:
        raise ValueError(f'Install the official CLI first: npm install -g tripo-cli@{PINNED_CLI}')
    package = Path(shim).resolve().parent / 'node_modules' / 'tripo-cli'
    if not (package / 'package.json').is_file():
        package = Path(shim).resolve().parent.parent / 'lib' / 'node_modules' / 'tripo-cli'
    meta = read(package / 'package.json')
    if meta['version'] != PINNED_CLI:
        raise ValueError(f'tripo-cli {meta["version"]} is installed; this workflow is verified on {PINNED_CLI}. '
                         'Install that version, or re-verify the dry-run format before changing the pin.')
    entry = meta['bin']['tripo'] if isinstance(meta['bin'], dict) else meta['bin']
    return [shutil.which('node') or 'node', str(package / entry)]


def invoke(args, timeout=60):
    env = os.environ.copy()
    env.update(TRIPO_NO_UPDATE_CHECK='1', TRIPO_ANALYTICS_ENABLED='0')
    result = subprocess.run(cli_command() + args, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=timeout, env=env)
    try:
        body = json.loads(result.stdout)
    except json.JSONDecodeError:
        body = {'error': (result.stderr or result.stdout)[-1500:]}
    # Never save credentials if the provider accidentally echoes an environment key.
    key = env.get('TRIPO_API_KEY')
    if key:
        body = json.loads(json.dumps(body).replace(key, '[REDACTED]'))
    return result.returncode, body


def doctor(root):
    """Report each capability as executable / needs setup. Prints no secrets, spends nothing."""
    report = {'root': str(Path(root).resolve()), 'python': sys.version.split()[0], 'checks': {}}
    c = report['checks']
    try:
        import PIL  # noqa: F401
        c['pillow'] = {'state': 'executable'}
    except ImportError:
        c['pillow'] = {'state': 'needs setup', 'fix': 'python -m pip install Pillow'}
    node = shutil.which('node')
    c['node'] = {'state': 'executable', 'path': node} if node else {'state': 'needs setup', 'fix': 'install Node.js 20+'}
    try:
        cmd = cli_command()
        c['tripo_cli'] = {'state': 'installed', 'version': PINNED_CLI}
        code, body = invoke(['doctor', '--json'])
        c['tripo_login'] = ({'state': 'executable'} if code == 0 and body.get('ok')
                            else {'state': 'needs setup', 'detail': {k: v for k, v in body.items() if k in ('ok', 'error', 'region')},
                                  'fix': 'tripo login --region <region> --no-open --no-wait --json, then authorize in the browser'})
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        c['tripo_cli'] = {'state': 'needs setup', 'fix': str(exc)}
    c['tripo_api_key_env'] = {'set': bool(os.environ.get('TRIPO_API_KEY'))}
    try:
        blender = find_blender(root=root)
        version, err = blender_version(blender)
        c['blender'] = {'state': 'executable' if version else 'needs setup', 'path': str(blender), 'version': version, **({'error': err} if err else {})}
    except ValueError as exc:
        c['blender'] = {'state': 'needs setup', 'fix': str(exc),
                        'searched': [p for _, p in blender_candidates(root)][:5]}
    ignore = Path(root) / '.gitignore'
    c['gitignore'] = {'covers_store': ignore.is_file() and any(
        line.strip().strip('/') == STORE_NAME for line in ignore.read_text(encoding='utf-8', errors='replace').splitlines())}
    if not c['gitignore']['covers_store']:
        c['gitignore']['fix'] = f'add "{STORE_NAME}/" to .gitignore (raw models are large and not reviewed yet)'
    report['ready_for_api_generation'] = c.get('tripo_login', {}).get('state') == 'executable'
    report['ready_for_local_processing'] = c['blender'].get('state') == 'executable'
    return report


# ---------------------------------------------------------------- jobs

def create_job(asset, source, height, triangles, model, provider='api', size_axis='height'):
    validate_asset_id(asset)
    if provider not in ('api', 'studio', 'local'):
        raise ValueError('Unsupported provider')
    if size_axis not in ('height', 'longest'):
        raise ValueError('size axis must be height or longest')
    if not math.isfinite(height) or not .01 <= height <= 1000:
        raise ValueError('Target size must be 0.01–1000 metres')
    if not 100 <= triangles <= 2_000_000:
        raise ValueError('Triangle budget must be 100–2,000,000')
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    job = Path(STORE) / asset / identifier
    job.mkdir(parents=True)
    spec = {'asset_id': asset, 'job_id': identifier, 'created_at': stamp(), 'source': source,
            'height_m': height, 'size_axis': size_axis, 'triangle_budget': triangles, 'model': model,
            'seed': int(uuid.uuid4().hex[:7], 16), 'scope': 'static-prop', 'cli_version': PINNED_CLI, 'provider': provider}
    write(job / 'spec.json', spec)
    write(job / 'state.json', initial_state())
    return job


def make_args(spec, job):
    source = spec['source']
    if source['kind'] == 'image':
        value = str(job / source['file'])
        if digest(value) != source['sha256']:
            raise ValueError('Reference image changed after the job was created')
    else:
        value = source['prompt']
    return ['make', '--model', spec['model'], '--seed', str(spec['seed']), '--candidates', '1',
            '--param', 'face_limit=' + str(spec['triangle_budget']), '--param', 'texture=true', '--param', 'pbr=true',
            '--out', str(job / 'raw'), '--name', spec['asset_id'] + '-' + spec['job_id'], '--json', '--no-open', '--', value]


def require_provider(job, expected):
    provider = read(job / 'spec.json').get('provider', 'api')
    if provider != expected:
        raise ValueError(f'Job uses {provider} credits, not {expected}. Switching wallets is not automatic.')


def plan(job):
    require_provider(job, 'api')
    require_submittable(read(job / 'state.json'))
    args = make_args(read(job / 'spec.json'), job)
    code, result = invoke(args[:1] + ['--dry-run'] + args[1:])
    if code or not result.get('valid') or len(result.get('steps', [])) != 1 or result.get('candidates') != 1:
        raise ValueError('Preflight failed, or a multi-step/batch billable plan was selected: ' + json.dumps(result, ensure_ascii=False))
    write(job / 'plan.json', result)
    update(job, status='planned')
    return result


def submit(job, max_credits):
    require_provider(job, 'api')
    require_submittable(read(job / 'state.json'))
    result = plan(job)
    estimate = result.get('generation_credits_estimate')
    if not math.isfinite(max_credits) or max_credits <= 0 or not isinstance(estimate, (int, float)) or estimate > max_credits:
        raise ValueError('No reliable estimate or estimate exceeds allowed credits; nothing submitted')
    code, doc = invoke(['doctor', '--json'])
    if code or not doc.get('ok'):
        raise ValueError('Login/environment not ready; run Tripo browser authorization and doctor first')
    update(job, status='submitting', estimated_credits=estimate, max_estimated_credits=max_credits)
    args = make_args(read(job / 'spec.json'), job)
    try:
        code, response = invoke(args[:1] + ['--no-wait'] + args[1:], timeout=90)
        write(job / 'submission.json', response)
        task_id = response.get('task_id')
        if code or not task_id:
            raise ValueError('Submission did not return one task ID')
        return update(job, status='submitted', task_id=task_id)
    except Exception:
        update(job, status='needs_reconcile', message='Submission may exist remotely. Check provider task history and resume by task ID. Never automatically resubmit.')
        raise


def resume(job, task_id=None):
    require_provider(job, 'api')
    state = read(job / 'state.json')
    if task_id:
        if state.get('task_id') and state['task_id'] != task_id:
            raise ValueError('Cannot replace the recorded task ID')
        if state['status'] not in ('needs_reconcile', 'submitting', 'submitted'):
            raise ValueError('Only reconcile a submitted or ambiguous job')
        state = update(job, status='submitted', task_id=task_id)
    if state['status'] in ('downloaded', 'review_ready'):
        return state
    if not state.get('task_id'):
        raise ValueError('Task ID is required to resume; do not repeat generation')
    code, result = invoke(['task', 'watch', state['task_id'], '--download', '--out', str(job / 'raw'),
                           '--timeout', '45', '--no-open', '--json'], timeout=60)
    write(job / 'last-watch.json', result)
    if code:
        return update(job, status='submitted', last_watch_exit=code,
                      message='Watch incomplete or remote failure; inspect last-watch.json. This operation never resubmits.')
    models = list((job / 'raw').rglob('*.glb'))
    if len(models) != 1:
        raise ValueError('Expected exactly one downloaded GLB; inspect raw outputs before processing')
    validate_glb(models[0])
    return update(job, status='downloaded', raw_model=str(models[0].relative_to(job)), raw_sha256=digest(models[0]),
                  credits_consumed=result.get('credits_consumed'), message='Downloaded; local processing next')


def run_blender(blender, script, args, log, timeout):
    with log.open('a', encoding='utf-8') as out:
        return subprocess.run([str(blender), '--background', '--factory-startup', '--disable-autoexec',
                               '--python-exit-code', '2', '--python', str(script), '--', *map(str, args)],
                              stdout=out, stderr=subprocess.STDOUT, timeout=timeout).returncode


def process(job, blender, resolution=512, samples=16):
    """A1 faithful prep (size, ground origin, transforms) + 14-view review set + contact sheet."""
    state = read(job / 'state.json')
    if state['status'] == 'review_ready':
        return state
    if state['status'] != 'downloaded':
        raise ValueError('Download or import a local GLB first')
    model = (job / state['raw_model']).resolve()
    if job not in model.parents or digest(model) != state['raw_sha256']:
        raise ValueError('Raw model changed or escaped its job directory')
    validate_glb(model)
    if (job / 'final').exists():
        raise ValueError('Final output already exists; never overwrite a reviewed asset')
    work = job / ('processing-' + uuid.uuid4().hex[:8])
    work.mkdir()
    log = work / 'blender.log'
    code = run_blender(blender, HERE / 'blender_prepare.py',
                       ['--spec', job / 'spec.json', '--input', model, '--output', work], log, 600)
    if code or not (work / 'report.json').exists():
        raise ValueError('Blender processing failed; raw model preserved. Inspect ' + str(log))
    validate_glb(work / 'model.glb')
    report = read(work / 'report.json')
    if not report.get('geometry_checks_passed'):
        raise ValueError('Geometry checks failed; inspect ' + str(work / 'report.json'))
    code = run_blender(blender, HERE / 'render_asset.py',
                       [work / 'model.glb', '--out', work / 'review', '--resolution', resolution, '--samples', samples], log, 1800)
    if code or not (work / 'review' / 'stats.json').exists():
        raise ValueError('Review render failed; the prepared model is kept. Inspect ' + str(log))
    sheet = make_review_sheet(job, work)
    work.rename(job / 'final')
    return update(job, status='review_ready', final_model='final/model.glb', final_sha256=digest(job / 'final/model.glb'),
                  report='final/report.json', review_sheet=str(Path('final') / sheet.name) if sheet else None,
                  blender_version=report.get('blender_version'), approved_for_game=False,
                  message='Ready for G2 model review (show the review sheet); not approved for game integration')


def make_review_sheet(job, work):
    """Concept first (as anchor), then textured and clay views. Needs Pillow on the host."""
    spec = read(job / 'spec.json')
    views = [work / 'review' / f'{mode}_{name}.png' for mode in ('textured', 'clay')
             for name in ('front34', 'front', 'right', 'back', 'left', 'top', 'bottom')]
    views = [str(v) for v in views if v.is_file()]
    if not views:
        return None
    args = [sys.executable, str(HERE / 'contact_sheet.py'), *views, '--out', str(work / 'review-sheet.png'),
            '--cols', '7', '--title', f"{spec['asset_id']} {spec['job_id']}: textured (row 1) / clay (row 2)"]
    if spec['source']['kind'] == 'image':
        args += ['--anchor', str(job / spec['source']['file'])]
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    return work / 'review-sheet.png' if result.returncode == 0 else None


# ---------------------------------------------------------------- Studio (browser) branch

STUDIO_PAGE = re.compile(r'^/(?:[a-z]{2}(?:-[a-zA-Z]{2,4})?/)?workspace/')
STUDIO_MODEL = re.compile(r'/workspace/[a-z-]+/[a-zA-Z0-9_-]{8,128}/?$')


def studio_url(value, asset=False):
    from urllib.parse import urlparse
    parsed = urlparse(value)
    if parsed.scheme != 'https' or parsed.hostname != 'studio.tripo3d.ai' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an observed Studio page URL without credentials or query tokens')
    if not STUDIO_PAGE.match(parsed.path):
        raise ValueError('Expected a Studio workspace URL')
    if asset and not STUDIO_MODEL.search(parsed.path):
        raise ValueError('Record the specific model page, not the empty generation page')
    return value


def studio_preflight(job, url, credits, balance, export_status, visibility, public_allowed, model_label, allow_export_probe=False):
    require_provider(job, 'studio')
    state = read(job / 'state.json')
    if state['status'] not in ('draft', 'planned', 'studio_planned', 'studio_blocked'):
        raise ValueError('Browser submission already attempted; reconcile the original model instead')
    studio_url(url)
    if not model_label.strip() or not all(math.isfinite(n) and n >= 0 for n in (credits, balance)):
        raise ValueError('Record the visible model label and finite page credit values')
    if export_status not in ('available', 'blocked', 'unknown') or visibility not in ('public', 'private'):
        raise ValueError('Invalid page export or visibility state')
    reasons = []
    if credits > balance:
        reasons.append('Insufficient Studio balance')
    probe = bool(allow_export_probe and export_status == 'unknown')
    if export_status != 'available' and not probe:
        reasons.append('Download/export entitlement is not confirmed available')
    if visibility == 'public' and not public_allowed:
        reasons.append('Public publication needs user authorization')
    observations = {'provider': 'studio', 'page_url': url, 'model_label': model_label, 'credits_shown': credits,
                    'balance_shown': balance, 'export_status': export_status, 'export_probe_authorized': probe,
                    'visibility': visibility, 'public_authorized': public_allowed, 'observed_at': stamp(),
                    'blocked_reasons': reasons, 'source': 'browser visible controls; not API pricing'}
    write(job / 'studio-preflight.json', observations)
    return update(job, status='studio_blocked' if reasons else 'studio_planned', studio_preflight=observations)


def studio_begin(job, max_credits):
    require_provider(job, 'studio')
    state = read(job / 'state.json')
    if state['status'] != 'studio_planned':
        raise ValueError('Studio export, visibility, budget and single-submit checks must pass first')
    observations = state['studio_preflight']
    if (datetime.now(timezone.utc) - datetime.fromisoformat(observations['observed_at'])).total_seconds() > 300:
        raise ValueError('Page checks expired; refresh visible balance, cost and export entitlement')
    if not math.isfinite(max_credits) or max_credits < 0 or observations['credits_shown'] > max_credits:
        raise ValueError('Displayed Studio cost exceeds allowed Studio credits')
    return update(job, status='studio_submitting', max_studio_credits=max_credits,
                  message='Browser agent may click Generate once now. If the result is unknown, inspect assets; never click Generate again for this job.')


def studio_record(job, url, existing=False):
    require_provider(job, 'studio')
    studio_url(url, asset=True)
    state = read(job / 'state.json')
    allowed = ('draft', 'planned', 'studio_planned', 'studio_blocked') if existing else ('studio_submitting', 'studio_submitted')
    if state['status'] not in allowed:
        raise ValueError('Cannot attach this model page to the current job state')
    if state.get('studio_asset_url') and state['studio_asset_url'] != url:
        raise ValueError('Do not replace the recorded Studio model; use a new version')
    return update(job, status='studio_submitted', studio_asset_url=url, existing_studio_asset=existing,
                  message='Observe or download this exact model through Studio; no API fallback')


def studio_attach(job, file):
    require_provider(job, 'studio')
    state = read(job / 'state.json')
    if state['status'] != 'studio_submitted' or not state.get('studio_asset_url'):
        raise ValueError('Record the specific Studio model page before attaching its browser download')
    validate_glb(file)
    raw = job / 'raw' / 'model.glb'
    if raw.exists():
        raise ValueError('Raw model already exists; never replace the original download')
    raw.parent.mkdir(exist_ok=True)
    shutil.copy2(file, raw)
    return update(job, status='downloaded', raw_model='raw/model.glb', raw_sha256=digest(raw),
                  origin='Studio browser download; Studio credits, not API credits', credits_consumed=None,
                  message='Browser GLB attached; run process for the same local Blender workflow')


# ---------------------------------------------------------------- CLI

def main(argv=None):
    global STORE
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='project root (default: current directory)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    for name in ('init', 'import-local'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--asset', required=True)
        cmd.add_argument('--height', type=float, required=True, help='target real size in metres (see --size-axis)')
        cmd.add_argument('--size-axis', choices=['height', 'longest'], default='height',
                         help='height = Z extent (props, buildings); longest = largest extent (rocks, debris, ships)')
        cmd.add_argument('--triangles', type=int, default=5000, help='acceptance target; Tripo face_limit for API jobs')
        cmd.add_argument('--model-version', default='tripo-v3.1')
        if name == 'init':
            cmd.add_argument('--provider', choices=['api', 'studio'], default='api')
            source = cmd.add_mutually_exclusive_group(required=True)
            source.add_argument('--prompt')
            source.add_argument('--image', type=Path)
            cmd.add_argument('--image-source', help='tool that made the concept image, e.g. "Midjourney v8"; recorded as provenance')
        else:
            cmd.add_argument('--file', type=Path, required=True)
    for name in ('plan', 'submit', 'resume', 'process', 'status'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--job', required=True)
        if name == 'submit':
            cmd.add_argument('--max-estimated-credits', type=float, required=True)
        if name == 'resume':
            cmd.add_argument('--task-id')
        if name == 'process':
            cmd.add_argument('--blender', type=Path)
            cmd.add_argument('--resolution', type=int, default=512)
            cmd.add_argument('--samples', type=int, default=16)
    for name in ('studio-preflight', 'studio-begin', 'studio-record', 'studio-attach'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--job', required=True)
        if name == 'studio-preflight':
            cmd.add_argument('--page-url', required=True)
            cmd.add_argument('--credits', type=float, required=True)
            cmd.add_argument('--balance', type=float, required=True)
            cmd.add_argument('--export-status', choices=['available', 'blocked', 'unknown'], required=True)
            cmd.add_argument('--visibility', choices=['public', 'private'], required=True)
            cmd.add_argument('--allow-public', action='store_true')
            cmd.add_argument('--allow-export-probe', action='store_true',
                             help='only for an explicitly authorized single export test when the page cannot show entitlement; never bypasses a known restriction')
            cmd.add_argument('--model-label', required=True)
        elif name == 'studio-begin':
            cmd.add_argument('--max-credits', type=float, required=True)
        elif name == 'studio-record':
            cmd.add_argument('--asset-url', required=True)
            cmd.add_argument('--existing', action='store_true')
        else:
            cmd.add_argument('--file', type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    STORE = root / STORE_NAME
    if args.command == 'doctor':
        print(json.dumps(doctor(root), ensure_ascii=False, indent=2))
        return
    if args.command in ('init', 'import-local'):
        if args.command == 'import-local':
            validate_glb(args.file)
            source = {'kind': 'local-glb', 'path': str(args.file.resolve()), 'sha256': digest(args.file)}
            provider = 'local'
        elif args.image:
            image = args.image.resolve()
            if image.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp') or image.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('Reference must be a PNG/JPEG/WebP up to 20MB')
            source = {'kind': 'image', 'file': 'reference' + image.suffix.lower(), 'sha256': digest(image),
                      'original_path': str(image), 'made_with': args.image_source or 'unrecorded'}
            provider = args.provider
        else:
            if not args.prompt.strip():
                raise ValueError('Prompt cannot be empty')
            source = {'kind': 'text', 'prompt': args.prompt}
            provider = args.provider
        job = create_job(args.asset, source, args.height, args.triangles, args.model_version, provider, args.size_axis)
        if args.command == 'import-local':
            (job / 'raw').mkdir()
            shutil.copy2(args.file, job / 'raw' / 'model.glb')
            update(job, status='downloaded', raw_model='raw/model.glb', raw_sha256=digest(job / 'raw' / 'model.glb'),
                   origin='local-import; no cloud generation')
        elif args.image:
            shutil.copy2(args.image, job / source['file'])
        print(json.dumps({'job': str(job), 'state': read(job / 'state.json')}, ensure_ascii=False))
        return
    job = job_path(args.job)
    with locked(job):
        if args.command == 'studio-preflight':
            result = studio_preflight(job, args.page_url, args.credits, args.balance, args.export_status,
                                      args.visibility, args.allow_public, args.model_label, args.allow_export_probe)
        elif args.command == 'studio-begin':
            result = studio_begin(job, args.max_credits)
        elif args.command == 'studio-record':
            result = studio_record(job, args.asset_url, args.existing)
        elif args.command == 'studio-attach':
            result = studio_attach(job, args.file)
        elif args.command == 'plan':
            result = plan(job)
        elif args.command == 'submit':
            result = submit(job, args.max_estimated_credits)
        elif args.command == 'resume':
            result = resume(job, args.task_id)
        elif args.command == 'process':
            result = process(job, find_blender(args.blender, root), args.resolution, args.samples)
        else:
            result = {'spec': read(job / 'spec.json'), 'state': read(job / 'state.json')}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
