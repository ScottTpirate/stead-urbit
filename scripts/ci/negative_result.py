"""Verify the worker's actual rejection observations, with closed case inventory."""
import errno
import hashlib
import re

from worker_result import require


def verify_controls(value, inputs):
    import core_conn
    import native_units
    from conn import framed_length
    from gall_schedule_proof import _cue, _atom, _jam
    files = value['filesystem_controls']
    require(set(files) == {'classification', 'seed_before', 'seed_poisoned', 'seed_after',
        'seed_refusal', 'runtime_expected', 'runtime_after', 'owned_truncated_sha256',
        'cache_mount_read_only', 'cache_write_errno', 'cache_pin_refused'}, 'Filesystem control inventory')
    require(files['classification'] == 'real-disposable-filesystem-controls'
        and files['seed_before'] == files['seed_after'] == value['fresh_seeds']['ships']['zod']
        and files['seed_poisoned'] != files['seed_before']
        and files['seed_refusal'] == 'Seed integrity failure: zod'
        and files['runtime_expected'] == files['runtime_after'] == inputs['runtime_binary_sha256']
        and files['owned_truncated_sha256'] != files['runtime_expected']
        and files['cache_mount_read_only'] is True
        and type(files['cache_write_errno']) is int
        and files['cache_write_errno'] in (errno.EROFS, errno.EACCES) and files['cache_pin_refused'] is True,
        'Filesystem rejection/restoration evidence incomplete')
    for key in ('seed_before', 'seed_poisoned', 'seed_after', 'runtime_expected', 'runtime_after', 'owned_truncated_sha256'):
        require(re.fullmatch(r'[0-9a-f]{64}', files[key]), 'Control digest shape')
    controls = value['negative_controls']
    require(set(controls) == {'classification', 'missing_arm', 'compiler_failure', 'timer_positive',
        'timer_timeout', 'timer_recovered', 'frame_fault_injection'} and controls['classification']
        == 'real-native-controls-and-labeled-frame-fault-injection', 'Native control inventory')

    def complete(observed, expected):
        frame = bytes.fromhex(observed['response_frame_hex'])
        require(len(frame) == 5 + framed_length(frame[:5])
            and hashlib.sha256(frame).hexdigest() == observed['response_frame_sha256']
            and _cue(frame[5:]) == expected, 'Negative control native frame differs')
        return frame

    def unit_request(observed, path):
        resolved = observed['resolved_path']
        require(re.fullmatch(r'/~zod/base/~[0-9a-zA-Z.:-]+' + re.escape(path), resolved)
            and observed['timeout_seconds'] == 60, 'Native control invocation differs')
        parts = resolved.split('/')[1:]
        atoms = ' '.join(core_conn.atom(part.encode()) for part in parts)
        require(observed['request'] == f'[32 %fyrd [%base %test %noun [%path [{atoms} ~]]]]', 'Native control request differs')
        beam = 0
        for part in reversed(parts):
            beam = (_atom(part), beam)
        return (32, (_atom('fyrd'), (_atom('base'), (_atom('test'), (_atom('noun'), (_atom('path'), beam))))))

    missing = controls['missing_arm']
    require(set(missing) == {'path', 'log_hex', 'native_test', 'refusal'}
        and missing['path'] == '/controls/stead-ci-missing'
        and missing['refusal'] == 'Native discovered/executed arm mismatch', 'Missing arm control incomplete')
    observed = missing['native_test']
    unit_request(observed, missing['path'])
    require(observed['resolved_path'].endswith(missing['path']) and observed['timeout_seconds'] == 60
            and observed['stdout'] == '[32 %avow 0 %noun 0]', 'Missing arm invocation differs')
    complete(observed, (32, (_atom('avow'), (0, (_atom('noun'), 0)))))
    raw = bytes.fromhex(missing['log_hex']).decode('utf-8') + '\n' + observed['stdout']
    native_units.verify_output(raw, path=missing['path'], expected=['test-ci-renamed'], succeeds=True)
    try:
        native_units.verify_output(raw, path=missing['path'], expected=['test-ci-required'], succeeds=True)
    except ValueError as error:
        require(str(error) == missing['refusal'], 'Missing arm rejection differs')
    else:
        raise ValueError('Missing arm was accepted')
    compiler = controls['compiler_failure']
    require(compiler['path'] == '/controls/stead-ci-compiler', 'Compiler control path differs')
    log = bytes.fromhex(compiler['log_hex'])
    require(0 < len(log) <= 262144, 'Compiler log bound')
    diagnostic = log.decode('utf-8')
    require('stead-ci-deliberately-undefined' in diagnostic and
        re.search(r'\b(find-fork|build-fail|dojo-lame)\b', diagnostic), 'Compiler diagnostic missing')
    if 'native_test' in compiler:
        require(set(compiler) == {'path', 'log_hex', 'native_test'}, 'Compiler execution schema')
        complete(compiler['native_test'], (32, (_atom('avow'), (0, (_atom('noun'), 1)))))
        unit_request(compiler['native_test'], compiler['path'])
    else:
        require(set(compiler) == {'path', 'log_hex', 'error', 'native_failure'}, 'Compiler failure schema')
        trace = compiler['native_failure']
        expected_request = unit_request(trace, compiler['path'])
        encoded = bytes.fromhex(trace['encoded_frame_hex'])
        require(len(encoded) == 5 + framed_length(encoded[:5]) and _cue(encoded[5:]) == expected_request, 'Compiler native request frame differs')
        require(trace['stage'] == 'parse-terminal', 'Compiler failed outside native build')
        frame = bytes.fromhex(trace['received_frame_hex'])
        require(len(frame) == 5 + framed_length(frame[:5]) and _cue(frame[5:]) == (32, (_atom('avow'), 1)), 'Compiler terminal differs')
    request = '[32 %fyrd [%base %stead-ci-delay %noun [%noun ~]]]'
    timer_noun = (32, (_atom('fyrd'), (_atom('base'), (_atom('stead-ci-delay'), (_atom('noun'), (_atom('noun'), 0))))))
    timer_jam = _jam(timer_noun)
    timer_frame = (b'\0' + len(timer_jam).to_bytes(4, 'little') + timer_jam).hex()
    for key in ('timer_positive', 'timer_recovered'):
        observed = controls[key]
        require(observed['request'] == request and observed['request_frame_hex'] == timer_frame
            and observed['outcome'] == {'raw': '{}', 'json': {}}, 'Timer positive/recovery missing')
        complete(observed, (32, (_atom('avow'), (0, (_atom('noun'), (_atom('stead-core-result'), _atom('7b7d')))))))
    timeout = controls['timer_timeout']
    trace = timeout['native_failure']
    require(timeout['deadline_seconds'] == .05 and 0 < timeout['elapsed_seconds'] < 60
        and trace['stage'] == 'response-header' and trace['received_frame_hex'] == ''
        and trace['request'] == request and trace['error'].startswith('TimeoutError:')
        and trace['encoded_frame_hex'] == timer_frame, 'Actual native timeout missing')
    source = next(row['native_test'] for row in value['native']['commands'] if 'native_test' in row)
    frame = bytes.fromhex(source['response_frame_hex'])
    injected = controls['frame_fault_injection']
    wrong = _jam((32, (_atom('avow'), (0, (_atom('noun'), 1)))))
    expected = {'truncated': frame[:-1], 'corrupt_verdict': b'\0' + len(wrong).to_bytes(4, 'little') + wrong}
    require(injected['original_sha256'] == hashlib.sha256(frame).hexdigest()
        and set(injected['controls']) == set(expected), 'Frame injection inventory differs')
    for name, raw in expected.items():
        require(injected['controls'][name] == {'injected_hex': raw.hex(), 'refusal': 'Native frame/verdict mismatch'}, 'Frame injection observation differs')
