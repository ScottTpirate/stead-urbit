"""Fail-closed current-phase evidence reconciliation; never starts a runtime.

Historical skipped/failed reports are read-only input. Passing a host validator
does not create native evidence. Each claim points to exact artifact bytes and a
typed result within them; source and N/A dispositions stay separately labeled.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

HEX = re.compile(r'[0-9a-f]{64}')
BASE_BINDINGS = ('source_commit', 'native_tree_sha256', 'runtime_lock_sha256',
                 'corpus_sha256', 'contract_freeze_sha256', 'runner_sha256')
NATIVE_BINDINGS = BASE_BINDINGS + ('installed_clay_tree_sha256', 'loaded_closure_sha256', 'observer_sha256')
DISPOSITION = {'native': 'passed', 'source_review': 'reviewed', 'not_applicable': 'not_applicable',
               'host_mocked': 'passed', 'real_host': 'passed', 'real_platform_mocked_sensors': 'passed'}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate evidence JSON key')
        result[key] = value
    return result


def pointer(value, path):
    if path == '':
        return value
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('JSON pointer must be explicit')
    for encoded in path[1:].split('/'):
        token = encoded.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('Noncanonical array pointer')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def artifact_reader(root):
    root = Path(root).resolve(strict=True)

    def read(path):
        if not isinstance(path, str) or Path(path).is_absolute():
            raise ValueError('Evidence artifact must be repository-relative')
        candidate = (root / path).resolve(strict=True)
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError('Evidence artifact escapes repository or is not a file')
        if candidate.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Evidence artifact exceeds bounded input size')
        return candidate.read_bytes()
    return read


def evaluate(manifest, evidence, expected_bindings, *, read_artifact=None):
    """Return failed for missing/stale/mock-as-native/zero-assertion evidence.

    evidence is a list (or {'items': list}) with id/kind/status/bindings/artifact.
    artifact is {path,sha256,pointer}; its pointed result repeats kind/status and
    has explicit assertions [{name,status}], plus nonempty native records for a
    native claim. read_artifact(path)->bytes must read actual retained evidence.
    Source/N-A results also name their independent reviewer and exact scope.
    """
    required = manifest.get('required', [])
    items = evidence.get('items', []) if isinstance(evidence, dict) else evidence
    report = {'protocol': 'stead.qualification-gate/2', 'status': 'failed',
              'test_owner': '/root/qa_review', 'items': [],
              'historical_skips': manifest.get('historical_skips', []),
              'historical_reports_unchanged': True,
              'scope': manifest.get('scope'), 'errors': []}
    if not isinstance(required, list) or not required or not isinstance(items, list):
        report['errors'].append('Nonempty required manifest and explicit evidence list required')
        return report
    names = [item.get('id') for item in required if isinstance(item, dict)]
    supplied_names = [item.get('id') for item in items if isinstance(item, dict)]
    if len(names) != len(required) or len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names):
        report['errors'].append('Duplicate, empty or malformed required identity')
        return report
    if len(supplied_names) != len(items) or len(set(supplied_names)) != len(supplied_names):
        report['errors'].append('Duplicate or malformed supplied evidence identity')
        return report
    extra = set(supplied_names) - set(names)
    if extra:
        report['errors'].append('Unknown evidence identities: ' + ', '.join(sorted(extra)))
    supplied = {item['id']: item for item in items}
    for requirement in required:
        identifier, kind = requirement['id'], requirement.get('kind')
        row = {'id': identifier, 'kind': kind, 'status': 'missing', 'scope': requirement.get('scope')}
        report['items'].append(row)
        item = supplied.get(identifier)
        if item is None:
            row['reason'] = 'Required current-phase evidence was not executed or supplied'
            continue
        try:
            expected_status = DISPOSITION[kind]
            if item.get('kind') != kind or item.get('status') != expected_status:
                raise ValueError('Evidence kind/status cannot qualify this requirement')
            bindings = item.get('bindings', {})
            keys = NATIVE_BINDINGS if kind == 'native' else requirement.get('binding_keys', BASE_BINDINGS)
            if not keys or not isinstance(bindings, dict):
                raise ValueError('Exact evidence source bindings required')
            for key in keys:
                expected = expected_bindings.get(key)
                pattern = r'[0-9a-f]{40}' if key == 'source_commit' else r'[0-9a-f]{64}'
                if not isinstance(expected, str) or not re.fullmatch(pattern, expected) or bindings.get(key) != expected:
                    raise ValueError('Missing/stale expected binding: ' + key)
            artifact = item.get('artifact', {})
            if read_artifact is None or not isinstance(artifact.get('sha256'), str) or not HEX.fullmatch(artifact['sha256']):
                raise ValueError('Actual retained artifact reader and digest required')
            raw = read_artifact(artifact['path'])
            if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
                raise ValueError('Artifact bytes do not match evidence digest')
            proof = pointer(json.loads(raw, object_pairs_hook=unique), artifact['pointer'])
            if not isinstance(proof, dict) or proof.get('kind') != kind or proof.get('status') != expected_status:
                raise ValueError('Artifact result does not support typed disposition')
            assertions = proof.get('assertions')
            if not isinstance(assertions, list) or not assertions:
                raise ValueError('Zero-assertion artifact cannot pass')
            assertion_names = [a.get('name') for a in assertions if isinstance(a, dict)]
            if len(assertion_names) != len(assertions) or len(set(assertion_names)) != len(assertion_names):
                raise ValueError('Malformed/duplicate artifact assertion')
            if any(a.get('status') != expected_status for a in assertions):
                raise ValueError('Failed/skipped/missing assertion preserved as nonpassing')
            wanted = requirement.get('assertions', [])
            if not wanted or not set(wanted).issubset(assertion_names):
                raise ValueError('Required named assertion missing')
            if proof.get('bindings') != bindings:
                raise ValueError('Artifact source bindings differ from index')
            if kind == 'native':
                if proof.get('classification') != 'real-native-fake-ships' or not proof.get('native'):
                    raise ValueError('Actual native commands/signs missing or mocked')
                if proof.get('guard_status') != 'completed':
                    raise ValueError('Guard refused/tripped/incomplete native execution')
            elif kind in ('source_review', 'not_applicable'):
                if proof.get('reviewer') not in ('/root/qa_review', '/root/hoon_review') or not proof.get('scope'):
                    raise ValueError('Bounded independent source disposition required')
                files = proof.get('reviewed_source_files')
                current_files = expected_bindings.get('source_files', {})
                if not isinstance(files, dict) or not files or any(
                        not isinstance(value, str) or not HEX.fullmatch(value) or current_files.get(path) != value
                        for path, value in files.items()):
                    raise ValueError('Reviewed source bytes do not match current exact source files')
                if kind == 'not_applicable' and (identifier != 'no-effect-subsystem' or not proof.get('reason')):
                    raise ValueError('N/A limited to explicitly absent external-effect subsystem')
            row.update(status=expected_status, verified_by=report['protocol'],
                       artifact=artifact, bindings=bindings, assertion_count=len(assertions))
        except (KeyError, ValueError, TypeError, IndexError, OSError) as error:
            row.update(status='failed', reason=f'{type(error).__name__}: {error}')
    report['counts'] = dict(Counter(row['status'] for row in report['items']))
    report['native_required'] = sum(row['kind'] == 'native' for row in report['items'])
    report['native_passed'] = sum(row['kind'] == 'native' and row['status'] == 'passed' for row in report['items'])
    if not report['errors'] and all(row['status'] == DISPOSITION.get(row['kind']) for row in report['items']):
        report['status'] = 'passed'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_bytes(), object_pairs_hook=unique)
    result = evaluate(read(args.manifest), read(args.evidence), read(args.bindings), read_artifact=artifact_reader(args.root))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['status'].upper()} current gate: {result.get('native_passed', 0)}/{result.get('native_required', 0)} native requirements supported")
    raise SystemExit(0 if result['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
