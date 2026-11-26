#!/usr/bin/env python3
"""Prepare private Stead Work drafts from a local GitHub issue export."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import secrets
import sys

import portable_recovery as portable


REPOSITORY = 'ScottTpirate/stead-urbit'
LEGACY_FORMAT = 'stead.github-work-plan/1'
FORMAT = 'stead.github-work-plan/2'
REPOSITORY_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}', re.ASCII)
LOGIN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}(?:\[bot\])?', re.ASCII)
UTC_TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z')
MAX_INPUT = 16 * 1024 * 1024
MAX_ROWS = 2048
MAX_TITLE = 800
MAX_TITLE_CHARACTERS = 200
MAX_DESCRIPTION = 8192
PROJECT_WORK_LIMIT = 128
LEGACY_LOSSES = [
    'Pull requests, comments, attachments and timeline entries are excluded.',
    'Labels, milestones, project board fields, priorities, assignments and relations are not applied.',
    'GitHub identities, permissions, timestamps and authorship are not imported into Stead.',
    'Original body links stay in the text. The tool does not retrieve, rewrite or verify their targets.',
    'These drafts cover the supplied rows. Their digest does not attest to origin or completeness.',
]

LOSSES = [
    'Pull requests, comment bodies, attachments and timeline entries are excluded.',
    'Original GitHub authors and dates are copied as source attribution. Stead records the importing member as creator.',
    'Source assignees remain unmapped. Review the destination team before assigning Work.',
    'Labels, milestones, project fields, priorities and relations are excluded.',
    'Body links are preserved verbatim and their targets are unverified.',
    'This preview covers the supplied rows. Its digest establishes the exact input bytes.',
]


def source_account(value):
    if value is None:
        return None
    portable.require(isinstance(value, dict) and portable.match(LOGIN, value.get('login')), 'issue-account')
    return {'login': value['login'], 'id': source_id(value.get('id'))}


def source_id(value):
    portable.require(value is None or (type(value) is int and 0 < value < 2**63), 'issue-source-id')
    return value


def source_time(value):
    if value is None:
        return None
    portable.require(portable.match(UTC_TIMESTAMP, value), 'issue-source-time')
    try:
        datetime.fromisoformat(value[:-1])
    except ValueError:
        raise portable.RecoveryError('issue-source-time') from None
    return value


def provenance(row):
    assigned = row.get('assignees', [])
    if 'assignees' not in row and row.get('assignee') is not None:
        assigned = [row['assignee']]
    portable.require(isinstance(assigned, list) and len(assigned) <= 100 and all(assigned), 'issue-assignees')
    count = row.get('comments')
    portable.require(count is None or (type(count) is int and 0 <= count < 2**63), 'issue-comment-count')
    return {'id': source_id(row.get('id')), 'author': source_account(row.get('user')),
            'created_at': source_time(row.get('created_at')), 'updated_at': source_time(row.get('updated_at')),
            'closed_at': source_time(row.get('closed_at')), 'unmapped_assignees': [source_account(a) for a in assigned],
            'excluded_comment_count': count}


def issue_rows(raw):
    rows = portable.decoded(raw, MAX_INPUT)
    portable.require(isinstance(rows, list) and len(rows) <= MAX_ROWS, 'issue-export-shape')
    if rows and isinstance(rows[0], list):
        flattened = []
        for page in rows:
            portable.require(isinstance(page, list) and len(page) <= 100, 'issue-page-shape')
            portable.require(len(flattened) + len(page) <= MAX_ROWS, 'issue-count-limit')
            flattened.extend(page)
        rows = flattened
    return rows


def issue_number(row, seen, repository_path):
    source = re.compile(rf'https://api\.github\.com/repos/{repository_path}', re.ASCII)
    portable.require(isinstance(row, dict) and portable.match(source, row.get('repository_url')), 'issue-repository')
    number = row.get('number')
    portable.require(type(number) is int and 0 < number <= 2**53 - 1, 'issue-number')
    portable.require(number not in seen, 'duplicate-issue-number')
    seen.add(number)
    namespace = 'pull' if 'pull_request' in row else 'issues'
    pattern = re.compile(rf'https://github\.com/{repository_path}/{namespace}/{number}', re.ASCII)
    portable.require(portable.match(pattern, row.get('html_url')), 'issue-permalink')
    return number


def issue_draft(row, number, repository, version):
    state = row.get('state')
    reason = row.get('state_reason')
    portable.require((state == 'open' and reason in (None, 'reopened'))
                     or (state == 'closed' and reason in (None, 'completed', 'not_planned', 'duplicate')),
                     'issue-state')
    status = 'todo' if state == 'open' else 'done'
    if reason in ('not_planned', 'duplicate'):
        status = 'canceled'
    title = portable.text(row.get('title'), MAX_INPUT)
    portable.require(bool(title.strip()), 'issue-title')
    portable.require('body' in row, 'issue-body')
    body = '' if row['body'] is None else portable.text(row['body'], MAX_INPUT)
    normalized = body.replace('\r\n', '\n').replace('\r', '\n')
    url = f'https://github.com/{repository}/issues/{number}'
    description = f'GitHub issue #{number}\n{url}'
    source = {'number': number, 'url': url, 'state': state, 'state_reason': reason}
    if version == FORMAT:
        source.update(provenance(row))
        if source['author']:
            description += '\nGitHub author: ' + source['author']['login']
        for key, label in (('created_at', 'Created'), ('updated_at', 'Updated'), ('closed_at', 'Closed')):
            if source[key]:
                description += f'\n{label} on GitHub: {source[key]}'
    if normalized:
        description += '\n\n' + normalized
    review = []
    if len(title) > MAX_TITLE_CHARACTERS or len(title.encode('utf-8')) > MAX_TITLE or any(ord(c) < 32 for c in title):
        review.append('Title exceeds the Work title limits or contains control characters.')
    if len(description.encode('utf-8')) > MAX_DESCRIPTION:
        review.append('Description with the source link exceeds the 8,192-byte Work limit.')
    if review:
        return 'needs_review', {'source': source, 'reasons': review}
    notes = []
    if state == 'closed' and reason is None:
        notes.append('Closed without a reason. Review the suggested Done status.')
    if body != normalized:
        notes.append('Carriage returns in the description were normalized to LF.')
    payload = {'title': title, 'description': description, 'type': 'task', 'status': status, 'priority': 'none'}
    return 'drafts', {'source': source, 'notes': notes, 'payload': payload}


def plan(raw, repository=REPOSITORY, version=FORMAT):
    portable.require(version in (FORMAT, LEGACY_FORMAT), 'github-preview-format')
    portable.require(portable.match(REPOSITORY_NAME, repository) and repository.split('/')[1] not in {'.', '..'},
                     'issue-repository')
    portable.require(version != LEGACY_FORMAT or repository == REPOSITORY, 'legacy-repository')
    repository_path = f'(?i:{re.escape(repository)})'
    rows = issue_rows(raw)
    result = {'protocol': version, 'repository': repository,
              'source_sha256': portable.sha(raw), 'input_rows': len(rows),
              'max_work_per_project': PROJECT_WORK_LIMIT, 'drafts': [], 'needs_review': [],
              'excluded_pull_requests': [], 'losses': LEGACY_LOSSES if version == LEGACY_FORMAT else LOSSES}
    seen = set()
    ordered = sorted((issue_number(row, seen, repository_path), row) for row in rows)
    for number, row in ordered:
        if 'pull_request' in row:
            portable.require(isinstance(row['pull_request'], dict), 'pull-request-shape')
            result['excluded_pull_requests'].append(number)
            continue
        bucket, record = issue_draft(row, number, repository, version)
        result[bucket].append(record)
    return result


def publish(raw, output):
    parent = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = '.stead-github-work-' + secrets.token_hex(16)
    opened = None
    try:
        directory = os.fstat(parent)
        portable.require(directory.st_uid == os.getuid() and directory.st_mode & 0o077 == 0,
                         'private-output-directory')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            opened = os.fstat(stream.fileno())
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            portable.require(portable.same_entry(parent, temporary, opened)
                             and portable.same_path(output.parent, directory), 'output-binding')
            os.link(temporary, output.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            portable.require(portable.same_entry(parent, output.name, opened)
                             and portable.same_path(output.parent, directory), 'output-binding')
    finally:
        try:
            if opened is not None and portable.same_entry(parent, temporary, opened):
                os.unlink(temporary, dir_fd=parent)
                os.fsync(parent)
        finally:
            os.close(parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Private local JSON from the GitHub repository issues API')
    parser.add_argument('--repository', default=REPOSITORY, help='Expected GitHub owner/repository')
    parser.add_argument('--output', required=True, type=Path, help='New review file in a private directory')
    args = parser.parse_args(argv)
    try:
        result = plan(portable.private_file(args.source, MAX_INPUT), args.repository)
        raw = portable.encoded(result)
        portable.require(len(raw) <= 2 * MAX_INPUT, 'github-preview-size')
        publish(raw, args.output)
    except portable.RecoveryError as error:
        print(f'GitHub Work planning stopped ({error}).', file=sys.stderr)
        return 1
    except OSError:
        print('GitHub Work planning could not publish a new private review file.', file=sys.stderr)
        return 1
    sys.stdout.buffer.write(portable.encoded({'drafts': len(result['drafts']),
        'needs_review': len(result['needs_review']), 'excluded_pull_requests': len(result['excluded_pull_requests']),
        'source_sha256': result['source_sha256'], 'plan_sha256': portable.sha(raw)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
