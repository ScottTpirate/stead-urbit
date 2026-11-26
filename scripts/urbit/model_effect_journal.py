"""Private no-overwrite model-call journal. Never grants authority or calls a model.

I/O here is filesystem publication only: no network, model, native carrier,
secret resolver or tool invocation. A started marker cannot authorize a call.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
import stat

import model_connections as model

NAMES = frozenset(('request.json', 'started.json', 'response.bin', 'result.json'))
REQUEST_MAX = 128 * 1024
RECORD_MAX = 16384
REASONS = frozenset(('transport-failed', 'timeout', 'canceled', 'authority-lost',
                     'invalid-response', 'publication-uncertain'))
KEY_FIELDS = ('home', 'project_id', 'run_id', 'attempt')


def require(ok):
    if not ok:
        raise ValueError('Model journal refused')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same_metadata(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def directory(fd):
    value = os.fstat(fd)
    require(os.getuid() == os.geteuid() != 0 and stat.S_ISDIR(value.st_mode)
            and value.st_uid == os.geteuid() and stat.S_IMODE(value.st_mode) == 0o700)
    return value.st_dev, value.st_ino


def read(fd, name, maximum):
    require(name in NAMES)
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    try:
        before = os.fstat(item)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                and stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
                and 0 < before.st_size <= maximum)
        chunks, size = [], 0
        while chunk := os.read(item, min(65536, maximum + 1 - size)):
            size += len(chunk); require(size <= maximum); chunks.append(chunk)
        require(same_metadata(before) == same_metadata(os.fstat(item)) and size == before.st_size)
        return b''.join(chunks)
    finally:
        os.close(item)


def publish(fd, name, raw, maximum):
    """Publish a new name; every partial publication remains observable."""
    require(name in NAMES and type(raw) is bytes and 0 < len(raw) <= maximum)
    directory(fd)
    temporary = '.' + name + '.next'
    item = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                   0o600, dir_fd=fd)
    try:
        os.fchmod(item, 0o600)
        offset = 0
        while offset < len(raw):
            count = os.write(item, raw[offset:]); require(count > 0); offset += count
        os.fsync(item)
    finally:
        os.close(item)
    # A rename would silently replace an existing result. link fails instead.
    os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
    os.fsync(fd)
    os.unlink(temporary, dir_fd=fd)
    os.fsync(fd)


def prepared_record(spec, request):
    model.validate_request(spec, request)
    value = asdict(request)
    for key in ('body', 'scope', 'tool_registry'):
        value[key] = value[key].decode('utf-8')
    record = {'protocol': 'stead.model-journal-request/1',
              'connection': spec.raw.decode('utf-8'), 'request': value}
    raw = model.canonical(record)
    require(len(raw) <= REQUEST_MAX)
    return raw


def native_intent(raw, spec, request):
    """Exact structural byte pin, never proof of accepted/current authority."""
    value = model.closed(model.decode(raw, 8192),
        {'effect_id', 'kind', 'provider_id', 'request_digest', 'result', 'charge'})
    require(model.canonical(value) == raw and value['kind'] == 'provider-call'
            and value['effect_id'] == request.effect_id and value['result'] == ''
            and value['provider_id'] == spec.value()['connection_id']
            and value['request_digest'] == request.request_digest)
    require(type(value['charge']) is str)
    fields = {'tool_calls', 'network_calls', 'token_units', 'cost_units', 'input_bytes', 'output_bytes'}
    charge = model.closed(model.decode(value['charge'].encode(), 2048), fields)
    require(model.canonical(charge).decode() == value['charge'])
    numbers = {key: model.uint(item) for key, item in charge.items()}
    require(numbers['network_calls'] == 1 and numbers['token_units'] > 0 and numbers['cost_units'] > 0)
    return model.domain_hash('stead.model-journal-native-intent/1', raw)


class EffectJournal:
    """One exact prepared request rooted at a caller-owned private attempt FD."""

    @classmethod
    def for_run(cls, root_fd, catalog, scope, turn, instructions, messages, tools,
                *, prior_digest=None):
        """Prepare or reopen the pinned request in an admitted supervisor's attempt directory."""
        spec, request = catalog.prepare(scope, turn, instructions, messages, tools,
                                        prior_digest=prior_digest)
        return cls(root_fd, spec, request)

    def __init__(self, root_fd, spec, request):
        self.root = self.fd = None
        self.spec, self.request = spec, request
        self.request_raw = prepared_record(spec, request)
        self.key = {key: model.decode(request.scope, 8192)[key] for key in KEY_FIELDS}
        try:
            self.root = os.dup(root_fd)
            self.root_identity = directory(self.root)
            names = os.listdir(self.root)
            require(len(names) <= 32 and all(type(name) is str and model.UUID.fullmatch(name) for name in names))
            # The dedicated attempt directory may not pool another Run's calls.
            for name in names:
                other = self._open(name)
                try:
                    existing = model.decode(read(other, 'request.json', REQUEST_MAX), REQUEST_MAX)
                    scope = model.decode(existing['request']['scope'].encode(), 8192)
                    require({key: scope[key] for key in KEY_FIELDS} == self.key)
                finally:
                    os.close(other)
            fresh = request.effect_id not in names
            if fresh:
                require(len(names) < 32)
                os.mkdir(request.effect_id, 0o700, dir_fd=self.root)
                os.fsync(self.root)
            self.fd = self._open(request.effect_id)
            self.identity = directory(self.fd)
            if fresh:
                publish(self.fd, 'request.json', self.request_raw, REQUEST_MAX)
            self.observe()
        except BaseException:
            self.close()
            raise

    def _open(self, name):
        require(model.UUID.fullmatch(name) is not None)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.root)
        try:
            directory(fd)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _current(self):
        require(self.fd is not None and directory(self.root) == self.root_identity
                and directory(self.fd) == self.identity)
        live = os.stat(self.request.effect_id, dir_fd=self.root, follow_symlinks=False)
        require((live.st_dev, live.st_ino) == self.identity and stat.S_ISDIR(live.st_mode))
        names = set(os.listdir(self.fd))
        require(names <= NAMES and 'request.json' in names)
        require(read(self.fd, 'request.json', REQUEST_MAX) == self.request_raw)
        return names

    def _started(self):
        raw = read(self.fd, 'started.json', RECORD_MAX)
        value = model.closed(model.decode(raw, RECORD_MAX),
            {'protocol', 'request_sha256', 'native_intent', 'native_intent_digest', 'native_receipt_sha256'})
        require(model.canonical(value) == raw and value['protocol'] == 'stead.model-journal-started/1'
                and value['request_sha256'] == sha(self.request_raw))
        model.digest(value['native_receipt_sha256'])
        require(type(value['native_intent']) is str and value['native_intent_digest']
                == native_intent(value['native_intent'].encode(), self.spec, self.request))
        return raw

    def record_started(self, intent_raw, receipt_digest):
        """True only for a newly durable marker; neither True nor False is a permit."""
        names = self._current()
        model.digest(receipt_digest)
        intent_digest = native_intent(intent_raw, self.spec, self.request)
        record = {'protocol': 'stead.model-journal-started/1', 'request_sha256': sha(self.request_raw),
            'native_intent': intent_raw.decode('utf-8'),
            'native_intent_digest': intent_digest,
            'native_receipt_sha256': receipt_digest}
        raw = model.canonical(record)
        if 'started.json' in names:
            require(self._started() == raw)
            self.observe()
            return False
        require(names == {'request.json'})
        publish(self.fd, 'started.json', raw, RECORD_MAX)
        self.observe()
        return True

    def _result(self, raw=None, reason=None):
        started = self._started()
        result = {'protocol': 'stead.model-journal-result/1', 'request_sha256': sha(self.request_raw),
            'started_sha256': sha(started), 'request_digest': self.request.request_digest,
            'connection_digest': self.spec.sha256, 'response_sha256': None,
            'proposal_digest': None, 'state': 'unknown', 'reason': reason,
            'observed_usage': None, 'authority': 'untrusted-proposal'}
        if raw is not None:
            result['response_sha256'] = sha(raw)
            try:
                proposal = model.normalize_reply(self.spec, self.request, raw)
            except ValueError:
                result['reason'] = 'invalid-response'
            else:
                require(reason is None)
                result.update(state=proposal['state'], reason=None,
                    proposal_digest=model.domain_hash('stead.model-journal-proposal/1', model.canonical(proposal)),
                    observed_usage=proposal['observed_usage'])
        else:
            require(reason in REASONS - {'invalid-response'})
        return model.canonical(result)

    def retain_response(self, raw):
        names = self._current()
        require('started.json' in names)
        maximum = int(self.spec.value()['limits']['output_bytes'])
        require(type(raw) is bytes and 0 < len(raw) <= maximum)
        self._started()
        if 'response.bin' in names:
            # Recovery does not silently finish an interrupted publication.
            require(read(self.fd, 'response.bin', maximum) == raw)
            return self.observe()
        require('result.json' not in names)
        publish(self.fd, 'response.bin', raw, maximum)
        result = self._result(raw)
        publish(self.fd, 'result.json', result, RECORD_MAX)
        return self.observe()

    def record_unknown(self, reason):
        names = self._current()
        require(names == {'request.json', 'started.json'} and reason in REASONS - {'invalid-response'})
        publish(self.fd, 'result.json', self._result(reason=reason), RECORD_MAX)
        return self.observe()

    def observe(self):
        names = self._current()
        result = {'effect_id': self.request.effect_id, 'request_digest': self.request.request_digest,
                  'connection_digest': self.spec.sha256, 'state': 'prepared',
                  'response_sha256': None, 'result_sha256': None,
                  'may_dispatch': False, 'native_settled': False}
        if 'started.json' not in names:
            require(names == {'request.json'})
            return result
        self._started(); result['state'] = 'unknown'
        raw = None
        if 'response.bin' in names:
            raw = read(self.fd, 'response.bin', int(self.spec.value()['limits']['output_bytes']))
            result.update(state='response-retained', response_sha256=sha(raw))
        if 'result.json' in names:
            terminal = read(self.fd, 'result.json', RECORD_MAX)
            value = model.decode(terminal, RECORD_MAX)
            expected = self._result(raw, None if raw is not None else value.get('reason'))
            require(expected == terminal)
            result.update(state='unknown' if value['state'] == 'unknown' else 'completed',
                          result_sha256=sha(terminal), provider_observation=value['state'])
        return result

    def close(self):
        if self.fd is not None:
            os.close(self.fd); self.fd = None
        if self.root is not None:
            os.close(self.root); self.root = None
