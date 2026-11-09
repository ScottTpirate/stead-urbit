#!/usr/bin/env python3
"""Bounded pure Hoon Git foundation tests and stock-Git vectors; no ship boot.

The existing host execution guardian owns thermal admission, one CPU, 50% CPU,
the shared native lock, timeout and cleanup. Native input is read-only and has
no network, home, live pier, authority socket, or writable source mount.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import execution_policy

ROOT = Path(__file__).resolve().parent.parent.parent
LIBRARY = 'native/core/desk/lib/stead-code-git-pkt.hoon'
TESTS = 'native/core/desk/tests/stead-code-git-pkt.hoon'
OBJECT_LIBRARY = 'native/core/desk/lib/stead-code-git-objects.hoon'
OBJECT_TESTS = 'native/core/desk/tests/stead-code-git-objects.hoon'
PACK_LIBRARY = 'native/core/desk/lib/stead-code-git-pack.hoon'
PACK_TESTS = 'native/core/desk/tests/stead-code-git-pack.hoon'
BASE_GIT = 'native/core/desk/lib/stead-git.hoon'
RECEIVE_LIBRARY = 'native/core/desk/lib/stead-code-receive.hoon'
RECEIVE_TESTS = 'native/core/desk/tests/stead-code-receive.hoon'
WIRE_LIBRARY = 'native/core/desk/lib/stead-code-receive-wire.hoon'
WIRE_TESTS = 'native/core/desk/tests/stead-code-receive-wire.hoon'
ENTRY_LIBRARY = 'native/core/desk/lib/stead-code-git-entry.hoon'
ENTRY_TESTS = 'native/core/desk/tests/stead-code-git-entry.hoon'
DELTA_LIBRARY = 'native/core/desk/lib/stead-code-git-delta.hoon'
DELTA_TESTS = 'native/core/desk/tests/stead-code-git-delta.hoon'
REVIEW_LIBRARY = 'native/core/desk/lib/stead-code-review.hoon'
REVIEW_TESTS = 'native/core/desk/tests/stead-code-review.hoon'
RESOLVE_LIBRARY = 'native/core/desk/lib/stead-code-git-resolve.hoon'
GRAPH_LIBRARY = 'native/core/desk/lib/stead-code-git-graph.hoon'
GRAPH_TESTS = 'native/core/desk/tests/stead-code-git-graph.hoon'
PACK_ORACLE = 'scripts/urbit/git_pack_oracle.py'
INFLATE_LIBRARY = 'native/core/desk/lib/stead-code-git-inflate.hoon'
INFLATE_TESTS = 'native/core/desk/tests/stead-code-git-inflate.hoon'
ARMS = (
    'test-encode-data', 'test-encode-binary', 'test-encode-empty-data',
    'test-encode-controls', 'test-encode-control-payload-rejected',
    'test-encode-at-bound', 'test-encode-over-bound-rejected',
    'test-encode-width-rejected', 'test-decode-controls-and-empty',
    'test-decode-binary-zero', 'test-decode-all-zero-payload',
    'test-decode-offset-and-tail', 'test-decode-truncated-header',
    'test-decode-truncated-payload', 'test-decode-required-relative-to-offset',
    'test-decode-nonhex-rejected', 'test-decode-reserved-rejected',
    'test-decode-over-bound-rejected', 'test-decode-at-bound',
    'test-decode-upper-hex', 'test-decode-offset-rejected',
    'test-decode-buffer-bound-rejected', 'test-decode-buffer-width-rejected',
)
EXTRA_CHECKS = (
    'failing-tang-control-detected', 'compiler-failure-control-detected',
    'native-encoded-ls-refs-accepted-by-stock-git',
    'stock-advertisement-decoded-natively', 'stock-refs-decoded-natively',
)
OBJECT_ARMS = (
    'test-object-empty-blob', 'test-object-trailing-zero', 'test-object-tag-exact-bytes',
    'test-object-kind-rejected', 'test-object-width-rejected', 'test-object-bound-rejected',
    'test-oid-zero', 'test-oid-leading-zero', 'test-oid-full-width', 'test-oid-uppercase-rejected',
    'test-oid-short-rejected', 'test-oid-nul-rejected', 'test-ref-valid', 'test-ref-head-rejected',
    'test-ref-leading-dot-rejected', 'test-ref-lock-component-rejected', 'test-ref-nul-rejected',
    'test-ref-bound-rejected',
)
PACK_ARMS = (
    'test-pack-empty-sha-one', 'test-pack-version-three', 'test-pack-unsupported-version',
    'test-pack-declared-count-bound', 'test-pack-signature', 'test-pack-checksum',
    'test-pack-empty-payload', 'test-pack-missing-entries', 'test-pack-truncated',
    'test-pack-envelope-does-not-validate-entry', 'test-pack-byte-bound', 'test-pack-explicit-width',
)
RECEIVE_ARMS = (
    'test-ref-advance', 'test-ref-competing-writes', 'test-ref-revoked', 'test-ref-epoch',
    'test-ref-protected-delete', 'test-ref-batch-rejects-stale-member', 'test-ref-non-fast-forward',
    'test-ref-namespace', 'test-ref-duplicate', 'test-ref-bad-name', 'test-ref-unsupported',
    'test-ref-tag-replacement', 'test-ref-bad-target', 'test-ref-missing-target', 'test-ref-tag-and-branch-create',
)
WIRE_ARMS = (
    'test-receive-wire-create',
    'test-receive-wire-empty-capabilities',
    'test-receive-wire-command-order',
    'test-receive-wire-final-lf',
    'test-receive-wire-pack-is-opaque',
    'test-receive-wire-large-tail-bypasses-pkt-buffer-limit',
    'test-receive-wire-pack-bound',
    'test-receive-wire-buffer-bound',
    'test-receive-wire-buffer-width',
    'test-receive-wire-empty',
    'test-receive-wire-truncated-header',
    'test-receive-wire-truncated-payload',
    'test-receive-wire-missing-flush',
    'test-receive-wire-invalid-header',
    'test-receive-wire-delimiter',
    'test-receive-wire-response-end',
    'test-receive-wire-first-nul-required',
    'test-receive-wire-later-nul-forbidden',
    'test-receive-wire-duplicate-ref',
    'test-receive-wire-invalid-ref',
    'test-receive-wire-unsupported-ref',
    'test-receive-wire-uppercase-oid',
    'test-receive-wire-command-spacing',
    'test-receive-wire-unknown-capability',
    'test-receive-wire-unsupported-sha256',
    'test-receive-wire-push-options-unsupported',
    'test-receive-wire-unadvertised-capability',
    'test-receive-wire-duplicate-capability',
    'test-receive-wire-duplicate-agent-key',
    'test-receive-wire-capability-whitespace',
    'test-receive-wire-capability-nul',
    'test-receive-wire-command-count-at-bound',
    'test-receive-wire-command-count-over-bound',
    'test-receive-wire-delete-advertisement',
    'test-receive-wire-advertisement-profile',
    'test-receive-wire-advertisement-bound',
    'test-receive-wire-header-bound',
    'test-receive-wire-capability-block-bound',
    'test-receive-wire-agent-at-token-bound',
    'test-receive-wire-agent-over-token-bound',
    'test-receive-wire-ref-at-bound',
    'test-receive-wire-ref-over-bound',
    'test-receive-wire-command-payload-bound',
    'test-receive-wire-shallow-unsupported',
    'test-receive-wire-signed-push-unsupported',
)
ENTRY_ARMS = (
    'test-entry-ordinary-commit',
    'test-entry-ordinary-tree',
    'test-entry-ordinary-blob',
    'test-entry-ordinary-tag',
    'test-entry-multi-byte-size',
    'test-entry-size-at-bound',
    'test-entry-size-over-bound',
    'test-entry-size-zero-extension',
    'test-entry-size-extension-bound',
    'test-entry-truncated-size',
    'test-entry-invalid-type',
    'test-entry-reserved-type',
    'test-entry-missing-zlib',
    'test-entry-offset-before-header',
    'test-entry-offset-at-trailer',
    'test-entry-offset-beyond-buffer',
    'test-entry-ofs-base',
    'test-entry-ofs-multi-byte',
    'test-entry-ofs-zero',
    'test-entry-ofs-before-pack',
    'test-entry-ofs-truncated',
    'test-entry-ofs-extension-bound',
    'test-entry-ofs-value-bound',
    'test-entry-ofs-missing-zlib',
    'test-entry-ref-big-endian',
    'test-entry-ref-zero-preserved',
    'test-entry-ref-truncated',
    'test-entry-ref-missing-zlib',
    'test-entry-pack-byte-bound',
    'test-entry-explicit-width',
    'test-entry-short-envelope',
    'test-entry-empty-envelope',
)
DELTA_ARMS = (
    'test-delta-copy-and-literal',
    'test-delta-literal-zeroes',
    'test-delta-empty-result',
    'test-delta-copy-offset',
    'test-delta-copy-and-binary',
    'test-delta-base-size',
    'test-delta-truncated-size',
    'test-delta-size-encoding',
    'test-delta-base-size-bound',
    'test-delta-target-size-bound',
    'test-delta-truncated-target',
    'test-delta-missing-result',
    'test-delta-literal-result-bound',
    'test-delta-truncated-literal',
    'test-delta-reserved-instruction',
    'test-delta-copy-base-bound',
    'test-delta-copy-result-bound',
    'test-delta-truncated-copy',
    'test-delta-missing-copy-field',
    'test-delta-copy-fourth-offset-byte',
    'test-delta-copy-default-size',
    'test-delta-copy-sparse-offset',
    'test-delta-copy-sparse-size',
    'test-delta-copy-high-size',
    'test-delta-instruction-at-bound',
    'test-delta-instruction-over-bound',
    'test-delta-remaining-budget',
    'test-delta-budget-input-bound',
    'test-delta-base-byte-bound',
    'test-delta-patch-byte-bound',
    'test-delta-base-width',
    'test-delta-patch-width',
)
REVIEW_ARMS = (
    'test-review-records-exact-change',
    'test-review-self-denied',
    'test-review-outsider-denied',
    'test-review-approval-epoch',
    'test-review-candidate-ref',
    'test-review-revoked-reviewer',
    'test-review-merge-permission',
    'test-review-epoch-changed',
    'test-review-ref-changed',
    'test-review-proposal-revised',
    'test-review-head-changed',
    'test-review-scope-changed',
    'test-review-self-merge',
    'test-review-forged-self-review',
    'test-review-requires-work-item',
)
GRAPH_ARMS = (
    'test-graph-tree-exact-name',
    'test-graph-tree-malformed-name',
    'test-graph-tree-unsupported-symlink',
    'test-graph-tree-duplicate',
    'test-graph-tree-order',
    'test-graph-commit-tree',
    'test-graph-tag-target',
    'test-graph-closure',
    'test-graph-closure-missing-object',
    'test-graph-closure-wrong-type',
    'test-graph-read-exact-commit',
    'test-graph-read-unreachable-object',
    'test-graph-read-traversal',
    'test-graph-empty-closure',
    'test-graph-duplicate-roots',
    'test-graph-visit-bound',
    'test-graph-byte-bound',
    'test-graph-queue-state',
    'test-graph-queue-bound',
    'test-graph-queue-at-bound',
    'test-graph-oid-mismatch',
    'test-graph-read-unreachable-revision',
    'test-graph-read-unreachable-tree',
    'test-graph-read-forbidden-loader',
    'test-graph-read-corrupt-loader',
    'test-graph-read-directory',
    'test-graph-path-depth-bound',
    'test-graph-root-bound',
    'test-graph-executable-file',
)
CODE_CHECKS = (
    'native-blob-roundtrip', 'native-tree-roundtrip', 'native-commit-roundtrip', 'native-tag-roundtrip',
    'native-object-graph-stock-fsck', 'native-ref-syntax-matches-stock-git',
    'stock-pack-envelope-checked-natively', 'corrupt-stock-pack-rejected-natively',
    'stock-pack-independent-index-check',
)
PACK_INTEROP_CHECKS = ('stock-ref-pack-native-headers', 'stock-ref-pack-native-deltas', 'stock-ref-pack-reconstructed-natively',
                       'stock-ofs-pack-native-headers', 'stock-ofs-pack-native-deltas', 'stock-ofs-pack-reconstructed-natively')
INFLATE_ARMS = (
    'test-inflate-empty',
    'test-inflate-stored-empty',
    'test-inflate-stored-binary',
    'test-inflate-fixed-binary',
    'test-inflate-dynamic-tree',
    'test-inflate-offset-and-tail',
    'test-inflate-concatenated-streams',
    'test-inflate-stock-multiple-blocks',
    'test-inflate-overlapping-match',
    'test-inflate-small-declared-window',
    'test-inflate-cross-block-distance',
    'test-inflate-blocks-at-bound',
    'test-inflate-blocks-over-bound',
    'test-inflate-truncated-header',
    'test-inflate-truncated-footer',
    'test-inflate-truncated-deflate',
    'test-inflate-invalid-method',
    'test-inflate-invalid-window',
    'test-inflate-header-check',
    'test-inflate-dictionary',
    'test-inflate-checksum',
    'test-inflate-reserved-block',
    'test-inflate-stored-complement',
    'test-inflate-stored-truncated',
    'test-inflate-output-bound',
    'test-inflate-stored-output-bound',
    'test-inflate-offset-bound',
    'test-inflate-reserved-length',
    'test-inflate-reserved-distance',
    'test-inflate-distance-before-output',
    'test-inflate-oversubscribed-tree',
    'test-inflate-incomplete-tree',
    'test-inflate-empty-code-tree',
    'test-inflate-repeat-without-previous',
    'test-inflate-repeat-bound',
    'test-inflate-missing-end-code',
    'test-inflate-literal-count',
    'test-inflate-input-bound',
    'test-inflate-input-width',
    'test-inflate-output-limit',
    'test-inflate-bit-work-bound',
    'test-inflate-byte-work-bound',
    'test-inflate-symbol-work-bound',
    'test-inflate-empty-distance-tree',
    'test-inflate-single-symbol-tree',
    'test-inflate-tree-length-bound',
    'test-inflate-tree-width-bound',
)
INFLATE_CHECKS = INFLATE_ARMS + (
    'inflater-failing-tang-control-detected', 'inflater-compiler-failure-control-detected',
)
RESOLVE_CONTROLS = (
    'native-resolve-empty-pack', 'native-resolve-correct-checksum-wrong-count',
    'native-resolve-correct-pack-checksum-bad-zlib-adler', 'native-resolve-wrong-inflated-width',
    'native-resolve-offset-not-entry-boundary', 'native-resolve-thin-without-visible-base',
    'native-resolve-thin-with-wrong-base-bytes', 'native-resolve-thin-with-verified-base',
)
EXPECTED_CHECKS = ARMS + EXTRA_CHECKS + OBJECT_ARMS + PACK_ARMS + RECEIVE_ARMS + WIRE_ARMS + ('receive-wire-failing-tang-control-detected',) + ENTRY_ARMS + DELTA_ARMS + REVIEW_ARMS + GRAPH_ARMS + CODE_CHECKS + PACK_INTEROP_CHECKS + RESOLVE_CONTROLS
ANSI = re.compile(r'\x1b\[[0-9;]*m')
MAX_OUTPUT = 1_048_576


def digest(data):
    return hashlib.sha256(data).hexdigest()


def literal(value):
    text = format(value, 'x')
    first = len(text) % 4 or 4
    return '0x' + '.'.join([text[:first], *[text[i:i + 4] for i in range(first, len(text), 4)]])


def decimal(value):
    return format(value, ',').replace(',', '.')


def octets(data):
    return f'[{decimal(len(data))} {literal(int.from_bytes(data, "little"))}]'


def parse_rows(output, width):
    """Accept a complete printed list of fixed-width @ta cells, no diagnostics."""
    if not isinstance(output, str) or len(output) > MAX_OUTPUT or width not in (2, 4):
        raise ValueError('Native row output outside bounds')
    cell = r'~\.([a-z0-9.-]+)'
    pattern = re.compile(r'\[\s*' + r'\s+'.join([cell] * width) + r'\s*\]')
    # Vere prints a list either as ~[rows] or [rows ~]. Require that exact
    # outer structure; stray brackets or a second noun cannot count as tests.
    outer = output.strip()
    if outer.startswith('~[') and outer.endswith(']'):
        inner = outer[2:-1]
    elif outer.startswith('[') and outer.endswith(']') and outer[1:-1].rstrip().endswith('~'):
        inner = outer[1:-1].rstrip()[:-1]
    else:
        raise ValueError('Native output is not a complete bounded row list')
    rows = pattern.findall(inner)
    if not rows or len(rows) > 128 or pattern.sub('', inner).strip():
        raise ValueError('Native output is not a complete bounded row list')
    return rows


def native_bytes(width, value):
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]{3})*', width) or not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]{4})*', value):
        raise ValueError('Native byte row is not a canonical bounded number')
    length, atom = int(width.replace('.', '')), int(value[2:].replace('.', ''), 16)
    if length > 65_520 or atom.bit_length() > 8 * length:
        raise ValueError('Native bytes exceed explicit width')
    return atom.to_bytes(length, 'little')


def reference_packets(data):
    """Independent host oracle for complete stock-produced pkt-line buffers."""
    if len(data) > 1_048_576:
        raise ValueError('Fixture buffer exceeds bound')
    result, offset = [], 0
    while offset < len(data):
        if len(result) >= 128 or len(data) - offset < 4:
            raise ValueError('Truncated or excessive fixture packets')
        header = data[offset:offset + 4]
        if not re.fullmatch(rb'[0-9a-fA-F]{4}', header):
            raise ValueError('Nonhex fixture header')
        size = int(header, 16)
        if size in (0, 1, 2):
            kind, body, end = ('flush', 'delim', 'response-end')[size], b'', offset + 4
        elif 4 <= size <= 65_520 and offset + size <= len(data):
            kind, body, end = 'data', data[offset + 4:offset + size], offset + size
        else:
            raise ValueError('Invalid or incomplete fixture length')
        result.append((kind, body, end))
        offset = end
    return result


def validate_report(report, expected=EXPECTED_CHECKS):
    if not isinstance(report, dict) or report.get('status') != 'passed' or not isinstance(report.get('checks'), list):
        raise ValueError('Native report has no passing result')
    rows = report['checks']
    if (len(rows) != len(expected)
            or tuple(row.get('name') for row in rows) != expected
            or any(row.get('passed') is not True for row in rows)):
        raise ValueError('Native expected-check inventory is incomplete')
    return report


def inside():
    execution_policy.require_lease(Path('/execution'), read_only=True)
    library = Path('/input/library.hoon').read_text()
    tests = Path('/input/tests.hoon').read_text()
    helper = Path('/input/test-helper.hoon').read_text()
    header, body = tests.split('\n', 1)
    if header != '/+  *test, stead-code-git-pkt' or tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', tests, re.M)) != ARMS:
        raise ValueError('Missing or unexpected native test arm/header')
    prefix = '=>\n' + library + '\n'
    test_prefix = '=/  test\n' + helper + '\n=/  stead-code-git-pkt\n' + library + '\n=,  test\n=>\n' + body + '\n'
    report = {'status': 'failed', 'scope': 'pure Hoon Git framing, SHA-1 objects, ref syntax and pack reconstruction; no acceptance service',
              'qualifies_phase': False, 'checks': [], 'records': []}
    def record(name, passed, **values):
        report['checks'].append({'name': name, 'passed': bool(passed), **values})
        if not passed:
            raise AssertionError(name)
    def native(source, label):
        execution_policy.require_lease(Path('/execution'), read_only=True)
        if len(source.encode()) > MAX_OUTPUT:
            raise ValueError('Evaluator source exceeds bound')
        result = subprocess.run(['/runtime/vere', 'eval', '--loom', '29'], input=source.encode(), capture_output=True, timeout=45)
        if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
            raise ValueError('Evaluator output exceeds bound')
        stdout, stderr = (ANSI.sub('', value.decode()).strip() for value in (result.stdout, result.stderr))
        report['records'].append({'kind': 'pure-native', 'label': label, 'source_sha256': digest(source.encode()),
                                  'exit_code': result.returncode, 'stdout': stdout, 'stderr': stderr})
        execution_policy.require_lease(Path('/execution'), read_only=True)
        return stdout, result.returncode == 0 and 'eval: bail:' not in stderr
    def git(*args, data=None, protocol=False, status=False):
        env = {'HOME': '/tmp/empty-home', 'PATH': '/usr/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}
        if protocol:
            env['GIT_PROTOCOL'] = 'version=2'
        argv = ['/runtime/git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *args]
        result = subprocess.run(argv, input=data, capture_output=True, timeout=15, env=env)
        if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
            raise ValueError('Stock Git output exceeds bound')
        report['records'].append({'kind': 'stock-git', 'argv': argv, 'input_sha256': digest(data) if data is not None else None,
                                  'stdout_hex': result.stdout.hex(), 'stderr': result.stderr.decode(), 'exit_code': result.returncode})
        if result.returncode and not status:
            raise ValueError('Stock Git fixture failed')
        return result.returncode if status else result.stdout
    try:
        # One compilation runs every explicit test arm and a deliberate failing
        # tang. Exact names/counts are checked independently on both sides.
        arms = ARMS + ('failure-control',)
        expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(
            f'[(scot %tas %{name}) (scot %ud (lent {name}))]' for name in arms) + '\n==\n'
        output, valid = native(test_prefix + expression, 'native-unit-inventory-and-failing-control')
        rows = parse_rows(output, 2) if valid else []
        if tuple(row[0] for row in rows) != arms:
            raise ValueError('Native test result names or compiler result differ')
        for name, tang_lines in rows[:-1]:
            record(name, tang_lines == '0')
        record('failing-tang-control-detected', bool(re.fullmatch(r'[1-9][0-9]*', rows[-1][1])), tang_lines=rows[-1][1])
        output, valid = native('(invalid-unterminated\n', 'deliberately-invalid-compiler-control')
        record('compiler-failure-control-detected', not valid and 'syntax error' in output)
        git('init', '--bare', '--template=', '--initial-branch=main', '/work/fixture.git')
        tree = git('--git-dir=/work/fixture.git', 'hash-object', '-w', '-t', 'tree', '--stdin', data=b'').strip()
        commit_body = (b'tree ' + tree + b'\nauthor Fixture <fixture@stead.invalid> 0 +0000\n'
                       b'committer Fixture <fixture@stead.invalid> 0 +0000\n\nPacket fixture\n')
        commit = git('--git-dir=/work/fixture.git', 'hash-object', '-w', '-t', 'commit', '--stdin', data=commit_body).strip()
        git('--git-dir=/work/fixture.git', 'update-ref', 'refs/heads/main', commit.decode())
        # Native output is supplied directly as the protocol-v2 ls-refs request.
        frames = [('data', b'command=ls-refs\n'), ('delim', b''), ('data', b'symrefs\n'), ('flush', b'')]
        expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(
            f'=/  frame  (encode %{kind} {octets(data)})\n    ?>  ?=(^ frame)\n    [(scot %ud length.u.frame) (scot %ux data.u.frame)]'
            for kind, data in frames) + '\n==\n'
        output, valid = native(prefix + expression, 'native-ls-refs-request')
        if not valid:
            raise ValueError('Native encoder failed')
        encoded = parse_rows(output, 2)
        if len(encoded) != len(frames):
            raise ValueError('Native encoder omitted a frame')
        request = b''.join(native_bytes(width, value) for width, value in encoded)
        if [(kind, body) for kind, body, _ in reference_packets(request)] != frames:
            raise ValueError('Native request differs from intended exact bytes')
        advertisement = git('upload-pack', '--stateless-rpc', '--advertise-refs', '/work/fixture.git', protocol=True)
        response = git('upload-pack', '--stateless-rpc', '/work/fixture.git', data=request, protocol=True)
        expected_ref = commit + b' refs/heads/main\n'
        record('native-encoded-ls-refs-accepted-by-stock-git', expected_ref in [row[1] for row in reference_packets(response)],
               request_sha256=digest(request), commit_oid=commit.decode())
        for name, raw in [('stock-advertisement-decoded-natively', advertisement), ('stock-refs-decoded-natively', response)]:
            expression = f'=/  buffer=octets  {octets(raw)}\n=/  offset=@ud  0\n=/  rows=(list [@ta @ta @ta @ta])  ~\n|-\n^-  (list [@ta @ta @ta @ta])\n?:  =(offset length.buffer)  (flop rows)\n?>  (lth (lent rows) 128)\n=/  value  (decode buffer offset)\n?>  ?=(%ready -.value)\n$(offset next.value, rows [[(scot %tas kind.value) (scot %ud length.body.value) (scot %ux data.body.value) (scot %ud next.value)] rows])\n'
            output, valid = native(prefix + expression, name)
            decoded = [(kind, native_bytes(width, value), int(next_offset.replace('.', ''))) for kind, width, value, next_offset in parse_rows(output, 4)] if valid else []
            record(name, decoded == reference_packets(raw), packet_count=len(decoded), input_sha256=digest(raw))
        base_git = Path('/input/base-git.hoon').read_text()
        object_library = Path('/input/object-library.hoon').read_text()
        object_tests = Path('/input/object-tests.hoon').read_text()
        pack_library = Path('/input/pack-library.hoon').read_text()
        pack_tests = Path('/input/pack-tests.hoon').read_text()
        # Comments may precede the import; remove exactly that one known import.
        if object_library.count('/+  stead-git\n') != 1:
            raise ValueError('Unexpected object-library imports')
        object_body = object_library.replace('/+  stead-git\n', '')
        object_prefix = '=/  stead-git\n' + base_git + '\n=>\n' + object_body + '\n'
        compiled, valid = native(object_prefix + '42\n', 'object-helper-compilation-control')
        if not valid or compiled != '42':
            raise ValueError('Object helper did not compile independently')
        receive_library = Path('/input/receive-library.hoon').read_text()
        receive_tests = Path('/input/receive-tests.hoon').read_text()
        if receive_library.count('/+  stead-code-git-objects\n') != 1:
            raise ValueError('Unexpected receive-library imports')
        receive_body = receive_library.replace('/+  stead-code-git-objects\n', '')
        receive_dependency = '=/  stead-git\n' + base_git + '\n=/  stead-code-git-objects\n' + object_body + '\n'
        compiled, valid = native(receive_dependency + '=>\n' + receive_body + '\n42\n', 'receive-helper-compilation-control')
        if not valid or compiled != '42':
            raise ValueError('Receive helper did not compile independently')
        wire_library = Path('/input/wire-library.hoon').read_text()
        wire_tests = Path('/input/wire-tests.hoon').read_text()
        wire_import = '/+  stead-code-git-pkt, stead-code-git-objects, stead-code-receive\n'
        if wire_library.count(wire_import) != 1:
            raise ValueError('Unexpected receive-wire imports')
        wire_body = wire_library.replace(wire_import, '')
        wire_dependency = receive_dependency + '=/  stead-code-git-pkt\n' + library + '\n=/  stead-code-receive\n' + receive_body + '\n'
        entry_library = Path('/input/entry-library.hoon').read_text()
        delta_library = Path('/input/delta-library.hoon').read_text()
        review_library = Path('/input/review-library.hoon').read_text()
        review_import = '/+  stead-code-git-objects, stead-code-receive\n'
        if review_library.count(review_import) != 1:
            raise ValueError('Unexpected code-review imports')
        review_body = review_library.replace(review_import, '')
        review_dependency = receive_dependency + '=/  stead-code-receive\n' + receive_body + '\n'
        resolve_library = Path('/input/resolve-library.hoon').read_text()
        resolve_import = '/+  stead-code-git-pack, stead-code-git-entry, stead-code-git-delta, stead-code-git-objects\n'
        if resolve_library.count(resolve_import) != 1:
            raise ValueError('Unexpected pack resolver imports')
        resolve_body = resolve_library.replace(resolve_import, '')
        resolve_dependency = (receive_dependency + '=/  stead-code-git-pack\n' + pack_library
                              + '\n=/  stead-code-git-entry\n' + entry_library
                              + '\n=/  stead-code-git-delta\n' + delta_library + '\n')
        graph_library = Path('/input/graph-library.hoon').read_text()
        graph_import = '/+  stead-code-git-objects\n'
        if graph_library.count(graph_import) != 1:
            raise ValueError('Unexpected graph helper imports')
        graph_body = graph_library.replace(graph_import, '')
        for module, source, tests_source, names, dependency in (
                ('stead-code-git-objects', object_body, object_tests, OBJECT_ARMS, '=/  stead-git\n' + base_git + '\n'),
                ('stead-code-git-pack', pack_library, pack_tests, PACK_ARMS, ''),
                ('stead-code-receive', receive_body, receive_tests, RECEIVE_ARMS, receive_dependency),
                ('stead-code-receive-wire', wire_body, wire_tests, WIRE_ARMS, wire_dependency),
                ('stead-code-git-entry', entry_library, Path('/input/entry-tests.hoon').read_text(), ENTRY_ARMS, ''),
                ('stead-code-git-delta', delta_library, Path('/input/delta-tests.hoon').read_text(), DELTA_ARMS, ''),
                ('stead-code-review', review_body, Path('/input/review-tests.hoon').read_text(), REVIEW_ARMS, review_dependency),
                ('stead-code-git-graph', graph_body, Path('/input/graph-tests.hoon').read_text(), GRAPH_ARMS, receive_dependency)):

            test_header, test_body = tests_source.split('\n', 1)
            expected_header = '/+  *test, ' + ('stead-code-git-pkt, ' if module == 'stead-code-receive-wire' else '') + module
            if module == 'stead-code-git-graph':
                expected_header += ', stead-code-git-objects, stead-git'
            if test_header != expected_header or tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', tests_source, re.M)) != names:
                raise ValueError('Unexpected native module test inventory')
            test_source = '=/  test\n' + helper + '\n' + dependency + '=/  ' + module + '\n' + source + '\n=,  test\n=>\n' + test_body + '\n'
            evaluated_names = names + (('failure-control',) if module == 'stead-code-receive-wire' else ())
            expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(f'[(scot %tas %{name}) (scot %ud (lent {name}))]' for name in evaluated_names) + '\n==\n'
            output, valid = native(test_source + expression, module + '-unit-inventory')
            results = parse_rows(output, 2) if valid else []
            if tuple(row[0] for row in results) != evaluated_names:
                raise ValueError('Native module result names or compiler result differ')
            failure = results.pop() if module == 'stead-code-receive-wire' else None
            module_report = {'module': module, 'scope': 'pure native unit arms only; no installed service or accepted write', 'checks': [{'name': name, 'tang_lines': tang_lines, 'passed': tang_lines == '0'} for name, tang_lines in results]}
            Path('/output/' + module + '.json').write_text(json.dumps(module_report, indent=2) + '\n')
            for name, tang_lines in results:
                record(name, tang_lines == '0')
            if failure is not None:
                record('receive-wire-failing-tang-control-detected', bool(re.fullmatch(r'[1-9][0-9]*', failure[1])), tang_lines=failure[1])
        def object_case(kind, body):
            expression = f'=/  value  (hash-object %{kind} {octets(body)})\n?>  ?=(^ value)\n^-  (list [@ta @ta @ta @ta])\n~[[(scot %tas kind.u.value) (scot %ud length.body.u.value) (scot %ux data.body.u.value) (scot %ux oid.u.value)]]\n'
            output, valid = native(object_prefix + expression, 'native-' + kind + '-object')
            rows = parse_rows(output, 4) if valid else []
            if len(rows) != 1:
                raise ValueError('Native object result is missing')
            actual_kind, width, data, oid = rows[0]
            actual_body = native_bytes(width, data)
            actual_oid = f'{int(oid[2:].replace(".", ""), 16):040x}'
            stock_oid = git('--git-dir=/work/fixture.git', 'hash-object', '-t', kind, '--stdin', data=body).strip().decode()
            if actual_kind != kind or actual_body != body or actual_oid != stock_oid:
                raise ValueError('Native object bytes/OID differ from stock Git')
            written = git('--git-dir=/work/fixture.git', 'hash-object', '-w', '-t', kind, '--stdin', data=actual_body).strip().decode()
            recovered = git('--git-dir=/work/fixture.git', 'cat-file', kind, written)
            record('native-' + kind + '-roundtrip', written == actual_oid and recovered == body,
                   oid=actual_oid, body_sha256=digest(body), bytes=len(body))
            return actual_oid
        blob_oid = object_case('blob', b'Exact binary bytes: \xff\x00\n')
        tree_oid = object_case('tree', b'100644 example.txt\0' + bytes.fromhex(blob_oid))
        code_commit = object_case('commit', (f'tree {tree_oid}\nauthor Jo\u00eb Example <jo@example.invalid> 1700000000 -0500\n'
                                  'committer Fixture <fixture@stead.invalid> 1700000010 +0000\n\nPreserve authors and original bytes.\n').encode())
        tag_oid = object_case('tag', (f'object {code_commit}\ntype commit\ntag v1\ntagger Fixture <fixture@stead.invalid> 1700000020 +0000\n\nExact annotated tag.\n').encode())
        git('--git-dir=/work/fixture.git', 'update-ref', 'refs/heads/code', code_commit)
        git('--git-dir=/work/fixture.git', 'update-ref', 'refs/tags/v1', tag_oid)
        git('--git-dir=/work/fixture.git', 'fsck', '--full', '--strict')
        record('native-object-graph-stock-fsck', True, commit_oid=code_commit, tag_oid=tag_oid)
        refs = ['refs/heads/main', 'refs/tags/v1', 'refs/notes/topic', 'refs/heads/feature/\u6771\u4eac',
                'refs/heads/@', 'refs/heads/a.LOCK', 'refs/heads/a./b', 'refs/heads/-leading',
                'refs/heads/.local', 'refs/a.lock/child', 'refs/a.lock', 'refs/heads/a..b',
                'refs/heads/a@{b', 'refs//heads', 'refs/heads/a\\b', 'refs/heads/a b',
                'refs/heads/a~b', 'refs/heads/a^b', 'refs/heads/a:b', 'refs/heads/a?b',
                'refs/heads/a*b', 'refs/heads/a[b', 'refs/heads/main/', 'refs/heads/main.',
                'refs/', 'refs/a\x7fb', 'refs/a\x01b', 'refs/heads/' + 'x' * 1013]
        expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(f'[~.r{index} (scot %tas ?:((valid-ref {octets(ref.encode())}) %yes %no))]' for index, ref in enumerate(refs)) + '\n==\n'
        output, valid = native(object_prefix + expression, 'native-full-ref-validation')
        rows = parse_rows(output, 2) if valid else []
        if [row[0] for row in rows] != [f'r{index}' for index in range(len(refs))] or any(row[1] not in ('yes', 'no') for row in rows):
            raise ValueError('Native ref result inventory differs')
        comparisons = [(row[1] == 'yes') == (git('check-ref-format', ref, status=True) == 0) for row, ref in zip(rows, refs)]
        record('native-ref-syntax-matches-stock-git', all(comparisons), cases=len(refs))
        raw_pack = git('--git-dir=/work/fixture.git', 'pack-objects', '--stdout', '--all')
        pack_prefix = '=>\n' + pack_library + '\n'
        expression = f'=/  value  (inspect {octets(raw_pack)})\n?>  ?=(%envelope -.value)\n^-  (list [@ta @ta @ta @ta])\n~[[(scot %ud version.value) (scot %ud declared.value) (scot %ud entries-length.value) (scot %ux checksum.value)]]\n'
        output, valid = native(pack_prefix + expression, 'native-stock-pack-envelope')
        rows = parse_rows(output, 4) if valid else []
        expected = (int.from_bytes(raw_pack[4:8], 'big'), int.from_bytes(raw_pack[8:12], 'big'), len(raw_pack) - 32, int.from_bytes(raw_pack[-20:], 'big'))
        actual = tuple(int(value.replace('.', ''), 16 if index == 3 else 10) for index, value in enumerate(rows[0])) if len(rows) == 1 else None
        record('stock-pack-envelope-checked-natively', actual == expected and hashlib.sha1(raw_pack[:-20]).digest() == raw_pack[-20:],
               bytes=len(raw_pack), declared_objects=expected[1], sha256=digest(raw_pack))
        corrupt = raw_pack[:-1] + bytes([raw_pack[-1] ^ 1])
        output, valid = native(pack_prefix + f'=([%invalid %checksum] (inspect {octets(corrupt)}))\n', 'native-corrupt-pack-trailer')
        record('corrupt-stock-pack-rejected-natively', valid and output == '%.y')
        git('init', '--bare', '--template=', '--initial-branch=main', '/work/pack-check.git')
        git('--git-dir=/work/pack-check.git', 'index-pack', '--strict', '--stdin', data=raw_pack)
        record('stock-pack-independent-index-check', git('--git-dir=/work/pack-check.git', 'index-pack', '--strict', '--stdin', data=corrupt, status=True) != 0)
        # Real stock-generated REF and OFS deltas, independently expanded by
        # the host oracle. Native helpers receive the exact entry/delta bytes;
        # inflation remains host-only and is not claimed as native coverage.
        import git_pack_oracle as oracle
        base_body = b''.join(f'line {n:03d} with a similar field and payload\n'.encode() for n in range(28))
        expected_objects = {}
        for index in range(6):
            body = base_body[:400] + str(index).encode() + base_body[401:]
            oid = git('--git-dir=/work/fixture.git', 'hash-object', '-w', '--stdin', data=body).strip().decode()
            expected_objects[oid] = ('blob', body)
        object_list = ('\n'.join(expected_objects) + '\n').encode()
        entry_prefix = '=>\n' + entry_library + '\n'
        delta_prefix = receive_dependency + '=>\n' + delta_library + '\n'
        inflate_source = Path('/input/inflate-library.hoon').read_text()
        resolve_prefix = (resolve_dependency + '=/  stead-code-git-resolve\n' + resolve_body
                          + '\n=/  stead-code-git-inflate\n' + inflate_source
                          + '\n=,  stead-code-git-resolve\n')
        expected_inventory = '(malt ~[' + ' '.join(
            f'[{literal(int(oid, 16))} %blob {octets(body)} {literal(int(oid, 16))}]'
            for oid, (_, body) in sorted(expected_objects.items())
        ) + '])'
        def check_pack(name, pack, *, complete='|', reject=None, read='~', **facts):
            rejected = '|' if reject is None else f'=(reason.work %{reject})'
            expression = (
                '=/  view=base-reader\n  |=  oid=@ux\n  ^-  (unit object)\n'
                + '\n'.join('  ' + line for line in read.splitlines()) + '\n'
                + f'=/  work=job  (begin {octets(pack)})\n'
                '=/  turns=@ud  0\n'
                '|-  ^-  ?\n'
                f'?:  ?=(%complete -.work)  {complete}\n'
                f'?:  ?=(%rejected -.work)  {rejected}\n'
                '?:  =(100 turns)  |\n'
                '$(work (step work inflate:stead-code-git-inflate view), turns +(turns))\n'
            )
            output, valid = native(resolve_prefix + expression, name)
            record(name, valid and output == '%.y', pack_sha256=digest(pack), **facts)

        for form, options, delta_kind in [('ref', (), 7), ('ofs', ('--delta-base-offset',), 6)]:
            packed = git('--git-dir=/work/fixture.git', 'pack-objects', '--stdout', '--threads=1', '--window=10', '--depth=10', *options, data=object_list)
            if oracle.unpack(packed) != expected_objects:
                raise ValueError('Independent stock delta pack expansion differs')
            reader = oracle.Reader(packed[:-20])
            reader.pos = 12
            entries = []
            for _ in range(int.from_bytes(packed[8:12], 'big')):
                offset = reader.pos
                first = reader.byte()
                kind = (first >> 4) & 7
                length = reader.size(first & 15, 4, first & 128)
                base = offset - reader.distance() if kind == 6 else bytes(reader.take(20)) if kind == 7 else None
                zlib_offset = reader.pos
                expanded = reader.inflate(length)
                entries.append({'offset': offset, 'kind': kind, 'length': length, 'base': base,
                                'zlib_offset': zlib_offset, 'data': expanded})
            if reader.pos != len(packed) - 20 or not any(e['kind'] == delta_kind for e in entries):
                raise ValueError('Stock fixture lacks complete requested delta entries')
            expression = f'=/  pack=octets  {octets(packed)}\n^-  (list [@ta @ta @ta @ta])\n:~  ' + '\n    '.join(
                f'=/  value  (decode pack {decimal(entry["offset"])})\n    ?>  ?=(%& -.value)\n    =/  source  source.p.value\n    =/  base-value=@\n      ?@  source  0\n      ?-  -.source\n        %offset  at.source\n        %oid  value.source\n      ==\n    [(scot %ud kind.p.value) (scot %ud inflated.p.value) (scot %ud zlib-offset.p.value) (scot %ux base-value)]'
                for entry in entries) + '\n==\n'
            output, valid = native(entry_prefix + expression, 'stock-' + form + '-pack-entry-headers')
            rows = parse_rows(output, 4) if valid else []
            actual_headers = [(int(k.replace('.', '')), int(n.replace('.', '')), int(z.replace('.', '')), int(b[2:].replace('.', ''), 16)) for k, n, z, b in rows]
            expected_headers = [(e['kind'], e['length'], e['zlib_offset'], int.from_bytes(e['base'], 'big') if isinstance(e['base'], bytes) else e['base'] or 0) for e in entries]
            record('stock-' + form + '-pack-native-headers', actual_headers == expected_headers,
                   entries=len(entries), delta_entries=sum(e['kind'] == delta_kind for e in entries), pack_sha256=digest(packed))
            resolved = {}
            pending = list(entries)
            native_deltas = []
            for _ in range(33):
                for entry in list(pending):
                    if entry['kind'] in (1, 2, 3, 4):
                        body = entry['data']
                    else:
                        base = resolved.get(entry['base']) if isinstance(entry['base'], int) else expected_objects.get(entry['base'].hex(), (None, None))[1]
                        if base is None:
                            continue
                        body = oracle.delta(base, entry['data'], oracle.MAX_EXPANDED)
                        oid = hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()
                        if expected_objects.get(oid) != ('blob', body):
                            raise ValueError('Delta fixture reconstruction lost original object bytes')
                        expression = f'=/  value  (apply {octets(base)} {octets(entry["data"])} 33.554.432)\n?>  ?=(%& -.value)\n=/  object  (hash-object:stead-code-git-objects %blob p.value)\n?>  ?=(^ object)\n^-  (list [@ta @ta @ta @ta])\n~[[~.delta (scot %ud length.p.value) (scot %ux oid.u.object) (scot %tas ?:(=({octets(body)} p.value) %yes %no))]]\n'
                        output, valid = native(delta_prefix + expression, f'stock-{form}-delta-at-{entry["offset"]}')
                        rows = parse_rows(output, 4) if valid else []
                        match = len(rows) == 1 and rows[0][0] == 'delta' and int(rows[0][1].replace('.', '')) == len(body) and f'{int(rows[0][2][2:].replace(".", ""), 16):040x}' == oid and rows[0][3] == 'yes'
                        if not match:
                            raise ValueError('Native delta differs from exact stock object bytes/OID')
                        native_deltas.append({'offset': entry['offset'], 'oid': oid, 'bytes': len(body), 'patch_sha256': digest(entry['data'])})
                    resolved[entry['offset']] = body
                    pending.remove(entry)
                if not pending:
                    break
            git('--git-dir=/work/pack-check.git', 'index-pack', '--strict', '--stdin', data=packed)
            record('stock-' + form + '-pack-native-deltas', not pending and len(native_deltas) == sum(e['kind'] in (6, 7) for e in entries) and bool(native_deltas),
                   cases=native_deltas, pack_sha256=digest(packed))
            check_pack('stock-' + form + '-pack-reconstructed-natively', packed,
                       complete=f'=(items.work {expected_inventory})',
                       object_ids=sorted(expected_objects), entries=len(entries))

        import zlib
        def framed(count, entries):
            payload = b'PACK' + (2).to_bytes(4, 'big') + count.to_bytes(4, 'big') + entries
            return payload + hashlib.sha1(payload).digest()

        base = b'abc'
        base_oid = int.from_bytes(hashlib.sha1(b'blob 3\0' + base).digest(), 'big')
        changed = b'abd'
        changed_oid = int.from_bytes(hashlib.sha1(b'blob 3\0' + changed).digest(), 'big')
        stream = zlib.compress(base)
        ordinary = b'\x33' + stream
        patch = bytes([3, 3, 0x90, 2, 1]) + b'd'
        delta = zlib.compress(patch)
        ref_entry = bytes([0x76]) + base_oid.to_bytes(20, 'big') + delta
        thin = framed(1, ref_entry)
        check_pack('native-resolve-empty-pack', framed(0, b''), complete='=(~ items.work)')
        check_pack('native-resolve-correct-checksum-wrong-count', framed(1, ordinary * 2),
                   reject='extra-entry-bytes')
        bad_adler = stream[:-1] + bytes([stream[-1] ^ 1])
        check_pack('native-resolve-correct-pack-checksum-bad-zlib-adler', framed(1, b'\x33' + bad_adler),
                   reject='adler')
        check_pack('native-resolve-wrong-inflated-width', framed(1, b'\x34' + stream),
                   reject='inflated-boundary')
        offset_inside = bytes([0x66, len(ordinary) - 1]) + delta
        check_pack('native-resolve-offset-not-entry-boundary', framed(2, ordinary + offset_inside),
                   reject='base-boundary')
        check_pack('native-resolve-thin-without-visible-base', thin, reject='unresolved-base')
        read_base = f'?.  =(oid {literal(base_oid)})  ~\n'
        check_pack('native-resolve-thin-with-wrong-base-bytes', thin, reject='invalid-base',
                   read=read_base + f'[~ %blob {octets(b"bad")} {literal(base_oid)}]')
        oid = literal(changed_oid)
        check_pack('native-resolve-thin-with-verified-base', thin,
                   read=read_base + f'[~ %blob {octets(base)} {literal(base_oid)}]',
                   complete=f'=(items.work (malt ~[[{oid} %blob {octets(changed)} {oid}]]))')
        report['status'] = 'passed'
    finally:
        Path('/output/report.json').write_text(json.dumps(report, indent=2) + '\n')
    validate_report(report)


def inside_inflate():
    """Fixed standalone inflater corpus; no other source or service is read."""
    execution_policy.require_lease(Path('/execution'), read_only=True)
    library = Path('/input/inflate-library.hoon').read_text()
    tests = Path('/input/inflate-tests.hoon').read_text()
    helper = Path('/input/test-helper.hoon').read_text()
    header, body = tests.split('\n', 1)
    if header != '/+  *test, stead-code-git-inflate' or tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', tests, re.M)) != INFLATE_ARMS:
        raise ValueError('Inflater test inventory/header differs')
    prefix = '=/  test\n' + helper + '\n=/  stead-code-git-inflate\n' + library + '\n=,  test\n=>\n' + body + '\n'
    report = {'status': 'failed', 'qualifies_phase': False, 'scope': 'pure bounded zlib inflater only; no resolver or service',
              'checks': [], 'records': []}
    def native(source, label):
        execution_policy.require_lease(Path('/execution'), read_only=True)
        if len(source.encode()) > MAX_OUTPUT:
            raise ValueError('Inflater evaluator source exceeds bound')
        try:
            result = subprocess.run(['/runtime/vere', 'eval', '--loom', '29'], input=source.encode(), capture_output=True, timeout=45)
        except subprocess.TimeoutExpired as error:
            report['records'].append({'kind': 'pure-native', 'label': label, 'source_sha256': digest(source.encode()),
                                      'timeout_seconds': 45, 'stdout': (error.stdout or b'')[:MAX_OUTPUT].decode(errors='replace'),
                                      'stderr': (error.stderr or b'')[:MAX_OUTPUT].decode(errors='replace')})
            raise
        if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
            raise ValueError('Inflater evaluator output exceeds bound')
        stdout, stderr = (ANSI.sub('', value.decode()).strip() for value in (result.stdout, result.stderr))
        report['records'].append({'kind': 'pure-native', 'label': label, 'source_sha256': digest(source.encode()),
                                  'exit_code': result.returncode, 'stdout': stdout, 'stderr': stderr})
        execution_policy.require_lease(Path('/execution'), read_only=True)
        return stdout, result.returncode == 0 and 'eval: bail:' not in stderr
    try:
        names = INFLATE_ARMS + ('failure-control',)
        expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(f'[(scot %tas %{name}) (scot %ud (lent {name}))]' for name in names) + '\n==\n'
        output, valid = native(prefix + expression, 'stead-code-git-inflate-unit-inventory')
        rows = parse_rows(output, 2) if valid else []
        if tuple(name for name, _ in rows) != names:
            raise ValueError('Inflater native result inventory or compilation differs')
        for name, count in rows[:-1]:
            report['checks'].append({'name': name, 'passed': count == '0', 'tang_lines': count})
        report['checks'].append({'name': 'inflater-failing-tang-control-detected',
                                 'passed': bool(re.fullmatch(r'[1-9][0-9]*', rows[-1][1])), 'tang_lines': rows[-1][1]})
        output, valid = native('(invalid-unterminated\n', 'deliberately-invalid-compiler-control')
        report['checks'].append({'name': 'inflater-compiler-failure-control-detected', 'passed': not valid and 'syntax error' in output})
        if all(check['passed'] for check in report['checks']):
            report['status'] = 'passed'
        validate_report(report, INFLATE_CHECKS)
    finally:
        Path('/output/report.json').write_text(json.dumps(report, indent=2) + '\n')


def main(mode="full"):
    if mode not in ("full", "inflate"):
        raise ValueError("Unknown fixed vector mode")
    import toolchain
    allowed = {'https://github.com/ScottTpirate/stead-urbit.git', 'git@github.com:ScottTpirate/stead-urbit.git'}
    for flags in ([], ['--push']):
        if subprocess.check_output(['git', 'remote', 'get-url', *flags, 'origin'], cwd=ROOT, text=True).strip() not in allowed:
            raise ValueError('Origin is not the authorized derivative')
    lock = toolchain.verify()
    git_binary = Path(shutil.which('git')).resolve(strict=True)
    base = ROOT / '.runtime/code-git-vectors'
    if any(path.is_symlink() for path in (base, *base.parents)):
        raise ValueError('Redirected fixture path')
    if subprocess.run(['git', 'check-ignore', '-q', str(base / 'probe')], cwd=ROOT).returncode:
        raise ValueError('Fixture path must be ignored')
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    for name in ('input', 'output', 'work', 'code'):
        (run / name).mkdir(mode=0o700)
    foundation_names = (LIBRARY, TESTS, OBJECT_LIBRARY, OBJECT_TESTS, PACK_LIBRARY, PACK_TESTS, BASE_GIT, RECEIVE_LIBRARY, RECEIVE_TESTS, WIRE_LIBRARY, WIRE_TESTS, ENTRY_LIBRARY, ENTRY_TESTS, DELTA_LIBRARY, DELTA_TESTS, REVIEW_LIBRARY, REVIEW_TESTS, RESOLVE_LIBRARY, GRAPH_LIBRARY, GRAPH_TESTS, INFLATE_LIBRARY, PACK_ORACLE)
    names = (INFLATE_LIBRARY, INFLATE_TESTS) if mode == "inflate" else foundation_names
    sources = {name: ROOT / name for name in names}
    sources.update({ 'scripts/urbit/code_git_vectors.py': Path(__file__),
               'scripts/urbit/execution_policy.py': Path(execution_policy.__file__)})
    hashes = {name: digest(path.read_bytes()) for name, path in sources.items()}
    helper = toolchain.CACHE / lock['kernel']['directory'] / 'pkg/base-dev/lib/test.hoon'
    copies = [(ROOT / LIBRARY, 'input/library.hoon'), (ROOT / TESTS, 'input/tests.hoon'),
              (ROOT / OBJECT_LIBRARY, 'input/object-library.hoon'), (ROOT / OBJECT_TESTS, 'input/object-tests.hoon'),
              (ROOT / PACK_LIBRARY, 'input/pack-library.hoon'), (ROOT / PACK_TESTS, 'input/pack-tests.hoon'),
              (ROOT / BASE_GIT, 'input/base-git.hoon'),
              (ROOT / RECEIVE_LIBRARY, 'input/receive-library.hoon'), (ROOT / RECEIVE_TESTS, 'input/receive-tests.hoon'),
              (ROOT / WIRE_LIBRARY, 'input/wire-library.hoon'), (ROOT / WIRE_TESTS, 'input/wire-tests.hoon'),
              (ROOT / ENTRY_LIBRARY, 'input/entry-library.hoon'), (ROOT / ENTRY_TESTS, 'input/entry-tests.hoon'),
              (ROOT / DELTA_LIBRARY, 'input/delta-library.hoon'), (ROOT / DELTA_TESTS, 'input/delta-tests.hoon'),
              (ROOT / REVIEW_LIBRARY, 'input/review-library.hoon'), (ROOT / REVIEW_TESTS, 'input/review-tests.hoon'),
              (ROOT / RESOLVE_LIBRARY, 'input/resolve-library.hoon'),
              (ROOT / GRAPH_LIBRARY, 'input/graph-library.hoon'), (ROOT / GRAPH_TESTS, 'input/graph-tests.hoon'),
              (ROOT / INFLATE_LIBRARY, 'input/inflate-library.hoon'),
              (ROOT / PACK_ORACLE, 'code/git_pack_oracle.py'),
              (helper, 'input/test-helper.hoon'), (Path(__file__), 'code/code_git_vectors.py'),
              (Path(execution_policy.__file__), 'code/execution_policy.py')]
    if mode == 'inflate':
        copies = [(ROOT / INFLATE_LIBRARY, 'input/inflate-library.hoon'),
                  (ROOT / INFLATE_TESTS, 'input/inflate-tests.hoon'),
                  (helper, 'input/test-helper.hoon'), (Path(__file__), 'code/code_git_vectors.py'),
                  (Path(execution_policy.__file__), 'code/execution_policy.py')]
    for source, target in copies:
        with (run / target).open('xb') as output:
            output.write(source.read_bytes())
    evidence = {'mode': mode, 'scope': 'pure Git protocol helpers only; no ship boot or Stead Git service', 'sources_sha256': hashes,
                'toolchain_sha256': digest(toolchain.LOCK_PATH.read_bytes()), 'helper_sha256': digest(helper.read_bytes()),
                'git_sha256': digest(git_binary.read_bytes()), 'git_version': lock['host_tools']['git'],
                'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    execution_policy.write_json(run / '.stead-disposable.json', {'format': 1, 'purpose': 'bounded pure native Git packet vectors'})
    execution_policy.write_json(run / 'inputs.json', evidence)
    print('Evidence: ' + str(run), flush=True)
    def command(control, run_id):
        return ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--clearenv',
                '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
                '--symlink', 'usr/bin', '/bin', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                '--dir', '/tmp/empty-home', '--setenv', 'HOME', '/tmp/empty-home', '--setenv', 'LANG', 'C.UTF-8',
                '--setenv', 'PATH', '/usr/bin', '--setenv', 'STEAD_EXECUTION_ID', run_id,
                '--ro-bind', str(run / 'code'), '/code', '--ro-bind', str(run / 'input'), '/input',
                '--ro-bind', str(control), '/execution', '--bind', str(run / 'output'), '/output',
                '--bind', str(run / 'work'), '/work', '--ro-bind', str(git_binary), '/runtime/git',
                '--ro-bind', str(toolchain.CACHE / lock['runtime']['binary']), '/runtime/vere',
                '--chdir', '/work', '/usr/bin/python3', '/code/code_git_vectors.py', '_inside_inflate' if mode == 'inflate' else '_inside']
    with (run / 'console.log').open('xb') as console:
        guarded = execution_policy.run_guarded(command, root=ROOT, label='code-git-inflate' if mode == 'inflate' else 'code-git-pkt', timeout=180, console=console)
    evidence['guard_report'] = guarded['run_directory'] + '/report.json'
    evidence['sources_after_sha256'] = {name: digest(path.read_bytes()) for name, path in sources.items()}
    execution_policy.write_json(run / 'inputs.json', evidence)
    if guarded['status'] != 'completed' or hashes != evidence['sources_after_sha256']:
        raise ValueError('Native guard/source check failed: ' + str(guarded.get('reason')))
    report = execution_policy.read_json(run / 'output/report.json', maximum=MAX_OUTPUT)
    validate_report(report, INFLATE_CHECKS if mode == 'inflate' else EXPECTED_CHECKS)
    print(f'PASS {len(report["checks"])} checks; pure native Git helpers only; no ship boot', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['_inside']:
        inside()
    elif sys.argv[1:] == ['_inside_inflate']:
        inside_inflate()
    elif sys.argv[1:] == ['inflate']:
        main('inflate')
    elif sys.argv[1:]:
        raise SystemExit('No caller-selected input paths or commands are accepted')
    else:
        main()
