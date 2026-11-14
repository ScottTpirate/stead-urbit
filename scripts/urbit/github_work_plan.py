#!/usr/bin/env python3
"""Prepare private Stead Work drafts from a local GitHub issue export."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import secrets
import sys

import portable_recovery as portable


REPOSITORY = 'ScottTpirate/stead-urbit'
REPOSITORY_PATH = f'(?i:{re.escape(REPOSITORY)})'
SOURCE = re.compile(rf'https://api\.github\.com/repos/{REPOSITORY_PATH}', re.ASCII)
MAX_INPUT = 16 * 1024 * 1024
MAX_ROWS = 2048
MAX_TITLE = 800
MAX_TITLE_CHARACTERS = 200
MAX_DESCRIPTION = 8192
PROJECT_WORK_LIMIT = 128
LOSSES = [
    'Pull requests, comments, attachments and timeline entries are excluded.',
    'Labels, milestones, project board fields, priorities, assignments and relations are not applied.',
    'GitHub identities, permissions, timestamps and authorship are not imported into Stead.',
    'Original body links stay in the text. The tool does not retrieve, rewrite or verify their targets.',
    'These drafts cover the supplied rows. Their digest does not attest to origin or completeness.',
]


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


def issue_number(row, seen):
    portable.require(isinstance(row, dict) and portable.match(SOURCE, row.get('repository_url')), 'issue-repository')
    number = row.get('number')
    portable.require(type(number) is int and 0 < number <= 2**53 - 1, 'issue-number')
    portable.require(number not in seen, 'duplicate-issue-number')
    seen.add(number)
    namespace = 'pull' if 'pull_request' in row else 'issues'
    pattern = re.compile(rf'https://github\.com/{REPOSITORY_PATH}/{namespace}/{number}', re.ASCII)
    portable.require(portable.match(pattern, row.get('html_url')), 'issue-permalink')
    return number


def issue_draft(row, number):
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
    url = f'https://github.com/{REPOSITORY}/issues/{number}'
    description = f'GitHub issue #{number}\n{url}'
    if normalized:
        description += '\n\n' + normalized
    source = {'number': number, 'url': url, 'state': state, 'state_reason': reason}
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


def plan(raw):
    rows = issue_rows(raw)
    result = {'protocol': 'stead.github-work-plan/1', 'repository': REPOSITORY,
              'source_sha256': portable.sha(raw), 'input_rows': len(rows),
              'max_work_per_project': PROJECT_WORK_LIMIT, 'drafts': [], 'needs_review': [],
              'excluded_pull_requests': [], 'losses': LOSSES}
    seen = set()
    ordered = sorted((issue_number(row, seen), row) for row in rows)
    for number, row in ordered:
        if 'pull_request' in row:
            portable.require(isinstance(row['pull_request'], dict), 'pull-request-shape')
            result['excluded_pull_requests'].append(number)
            continue
        bucket, record = issue_draft(row, number)
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
    parser.add_argument('--output', required=True, type=Path, help='New review file in a private directory')
    args = parser.parse_args(argv)
    try:
        result = plan(portable.private_file(args.source, MAX_INPUT))
        raw = portable.encoded(result)
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
