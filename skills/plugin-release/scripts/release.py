#!/usr/bin/env python3
"""Portable, non-publishing release operations. See ../references/runbook.md."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def run(argv, root):
    subprocess.run(argv, cwd=root, check=True)


def execute(root, output, packager, dry_run=False):
    root, output, packager = (Path(p).expanduser().resolve() for p in (root, output, packager))
    manifest = root / 'plugin.json'
    if not manifest.is_file():
        manifest = root / '.claude-plugin/plugin.json'
    identity = json.loads(manifest.read_text())
    name, version = identity['name'], identity['version']
    if any('/' in v or '\\' in v or v in ('.', '..') for v in (name, version)):
        raise ValueError('Invalid archive identity')
    config = root / 'config/release.json'
    extension = None
    if config.exists():
        extension = json.loads(config.read_text())
        if not isinstance(extension, dict):
            raise ValueError('Release extension must be an object')
    if extension is not None:
        if extension.get('schema_version') != 1:
            raise ValueError('Unsupported release extension version')
        for key in ('preflight', 'package'):
            if not isinstance(extension.get(key), list) or not extension[key] or not all(isinstance(x, str) for x in extension[key]):
                raise ValueError('Release extension requires argv arrays: ' + key)
    # Always build in an isolated destination; stdout never doubles as a path API.
    with tempfile.TemporaryDirectory(prefix='plugin-release-') as temp:
        stage = Path(temp)
        values = {'packager': str(packager), 'output': str(stage)}
        def command(key):
            return [arg.format(**values) for arg in extension[key]]
        if extension is not None:
            run(command('preflight'), root)
            run(command('package'), root)
        else:
            # Generic fallback snapshots tracked files, excluding local/ignored artifacts.
            # git archive preserves symlinks and executable bits, including manifests.
            snapshot = stage / 'source'
            snapshot.mkdir()
            tarball = stage / 'source.tar'
            run(['git', 'archive', '--format=tar', '--output', str(tarball), 'HEAD'], root)
            run(['tar', '-xf', str(tarball), '-C', str(snapshot)], root)
            run(['bash', str(packager), str(snapshot)], root)
            built = snapshot / f'{name}-v{version}.plugin'
            shutil.move(str(built), stage / built.name)
        built = stage / f'{name}-v{version}.plugin'
        if len(list(stage.glob('*.plugin'))) != 1:
            raise ValueError('Package contract must produce exactly one archive')
        if not built.is_file():
            raise ValueError('Package contract did not produce expected archive: ' + str(built))
        with zipfile.ZipFile(built) as archive:
            if archive.testzip() is not None:
                raise ValueError('Corrupt release archive')
            entries = archive.namelist()
            if any(n.startswith('/') or '..' in Path(n).parts for n in entries):
                raise ValueError('Unsafe archive paths')
            manifest_data = json.loads(archive.read('plugin.json' if 'plugin.json' in entries else '.claude-plugin/plugin.json'))
            if manifest_data['name'] != name or manifest_data['version'] != version:
                raise ValueError('Archive manifest differs from release identity')
        if dry_run:
            return {'name': name, 'version': version, 'archive': None, 'planned_archive': str(output / built.name), 'files': len(entries), 'dry_run': True}
        output.mkdir(parents=True, exist_ok=True)
        destination = output / built.name
        shutil.copy2(built, destination)
        return {'name': name, 'version': version, 'archive': str(destination), 'files': len(entries), 'dry_run': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--packager', type=Path, default=Path(__file__).with_name('package.sh'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--result', type=Path, required=True, help='Explicit JSON receipt for downstream upload')
    args = parser.parse_args()
    try:
        # Never leave a prior success receipt available after a failed invocation.
        args.result.unlink(missing_ok=True)
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=args.repo, text=True).strip():
            raise ValueError('Release requires a clean tree')
        result = execute(args.repo, args.output, args.packager, args.dry_run)
        args.result.write_text(json.dumps(result, indent=2) + '\n')
    except (OSError, ValueError, subprocess.CalledProcessError, KeyError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
