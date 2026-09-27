"""Review retained clean setup and append URB-170 disposition; never run setup/tests."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent
OUT = BASE / 'portable-bundle'
ATTEMPT = REPO / '.runtime/phase01-20260926/contributor-clean-setup-v2'
CLONE = ATTEMPT / 'checkout'
HEAD = '55475f0565ceb38db9eb5bc057962967398aa5da'
TRIAL = '0d877cff4319de8d437f0da58d4518535f758c36'
ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}


def need(value, why):
    if not value:
        raise ValueError(why)


def git(*arguments, cwd=REPO):
    return subprocess.check_output(['git', *arguments], cwd=cwd, env=ENV)


def remotes(cwd=REPO):
    need(git('remote','get-url','origin',cwd=cwd).decode().strip() == 'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong origin')
    need(git('remote','get-url','--push','origin',cwd=cwd).decode().strip() == 'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong origin push')
    need(git('remote','get-url','--push','upstream',cwd=cwd).decode().strip() == 'DISABLED_UPSTREAM_PUSH', 'Wrong upstream push')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    need(not any(part.is_symlink() for part in (path,*path.parents)) and path.is_file(), 'Nonregular evidence file')
    need(path.stat().st_size <= 4 * 1024 * 1024, 'Small evidence byte bound')
    return path.read_bytes()


def file_hash(path):
    need(not any(part.is_symlink() for part in (path,*path.parents)), 'Redirected download')
    need(stat.S_ISREG(path.stat().st_mode), 'Nonregular download')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    remotes(); remotes(CLONE)
    need(os.sched_getaffinity(0) == {19}, 'Wrong audit affinity')
    cgroup = Path('/proc/self/cgroup').read_text().strip().split('::',1)[1]
    cpu = (Path('/sys/fs/cgroup')/cgroup.lstrip('/')/'cpu.max').read_text().strip()
    need(cpu == '5000 10000', 'Wrong audit CPU quota')
    before = {path.relative_to(OUT).as_posix(): sha(read(path)) for path in OUT.rglob('*') if path.is_file()}
    need(git('rev-parse','HEAD',cwd=CLONE).decode().strip() == HEAD, 'Wrong actual clean checkout')
    need(git('status','--porcelain',cwd=CLONE) == b'', 'Actual clean checkout changed')
    raw = read(ATTEMPT/'result.json'); record = json.loads(raw)
    need(record['source_commit'] == HEAD and record['status'] == 'passed'
         and record['native_ships_started'] is False
         and record['initial']['tracked_clean'] is True
         and record['initial']['runtime_absent'] is True and record['initial']['piers_absent'] is True
         and record['final']['tracked_clean'] is True
         and record['final']['live_piers_exist'] is False and record['final']['control_socket_exists'] is False,
         'Setup did not record a complete clean lifecycle')
    tree = git('rev-parse','HEAD^{tree}',cwd=CLONE).decode().strip()
    need(tree == record['initial']['tree'] == git('rev-parse',HEAD+'^{tree}').decode().strip(), 'Exact checkout tree differs')
    expected = {'clone':None,'checkout':['git','checkout','--detach',HEAD], 'help':['make'],
                'setup':['make','setup'],'doctor':['make','doctor'],'status':['make','status']}
    need([row['name'] for row in record['steps']] == list(expected), 'Step inventory/order differs')
    need(record['steps'][0]['command'][:5] == ['git','clone','--no-local','--no-hardlinks','--no-checkout'], 'Clone reused a working/cache tree')
    for row in record['steps']:
        need(row['exit_code'] == 0 and row['elapsed_seconds'] > 0, 'Failed/missing actual step')
        if expected[row['name']] is not None:
            need(row['command'] == expected[row['name']], 'Step command changed')
        for stream in ('stdout','stderr'):
            item = row[stream]
            need(item['file'] == row['name']+'.'+stream+'.log', 'Unexpected log path')
            value = read(ATTEMPT/item['file'])
            need(len(value) == item['bytes'] and sha(value) == item['sha256'], 'Raw step log differs')
    status = read(ATTEMPT/'status.stdout.log').decode().split('\n',1)[1]
    need(json.loads(status) == {'stage':'stopped','ready':False,'ships':{}}, 'Stopped status was not observed')
    doctor = read(ATTEMPT/'doctor.stdout.log').decode()
    need(record['final']['namespace_negative_result'] in doctor
         and 'PASS private network (loopback only, no internet route), no host home or Docker socket' in doctor,
         'Actual namespace negative output missing')
    need(not (CLONE/'.piers/fakes/live').exists() and not (CLONE/'.piers/fakes/control.sock').exists(), 'Actual setup clone has native fixtures')
    old_helper = read(REPO/'.runtime/phase01-20260926/check_clean_setup.py')
    helper = read(REPO/'.runtime/phase01-20260926/check_clean_setup_v2.py')
    need(helper == old_helper.replace(b"contributor-clean-setup'",b"contributor-clean-setup-v2'").replace(TRIAL.encode(),HEAD.encode()),
         'Setup capture changed beyond source/output identity')
    critical = ('Makefile','specs/urbit/toolchain.lock.json','scripts/urbit/toolchain.py',
                'scripts/urbit/harness.py','scripts/urbit/namespace_check.py')
    source = {}
    for name in critical:
        actual = read(CLONE/name)
        need(actual == git('show',HEAD+':'+name), 'Actual executed setup source differs from committed bytes')
        source[name] = {'sha256':sha(actual),'bytes':len(actual)}
    lock = json.loads(read(CLONE/'specs/urbit/toolchain.lock.json'))
    need([row['key'] for row in record['downloads']] == ['runtime','kernel','boot_artifact','frontend'], 'Downloaded pin inventory differs')
    for row in record['downloads']:
        pin = lock[row['key']]; path = CLONE/'.runtime/downloads'/row['file']
        need(row['file'] == pin['archive'] and row['url'] == pin['url']
             and row['sha256'] == pin['sha256'] == file_hash(path)
             and row['bytes'] == path.stat().st_size, 'Actual downloaded pin bytes differ')
        need('Downloading '+pin['url'] in read(ATTEMPT/'setup.stdout.log').decode(), 'Missing actual download invocation')
    need('PASS pinned downloads, binary, Arvo tree, Git and Node versions' in read(ATTEMPT/'setup.stdout.log').decode(), 'Setup verification incomplete')
    review = json.loads(read(REPO/'docs/urbit/evidence/2026-09-26/socket-path-fix/independent-review.json'))
    need(review['reviewer'] == '/root/core_acceptance_review' and review['findings'] == []
         and review['reviewed_working_files_sha256']['scripts/urbit/harness.py'] == source['scripts/urbit/harness.py']['sha256'],
         'Independent socket change review does not match setup source')
    need(git('status','--porcelain',cwd=CLONE) == b'' and read(ATTEMPT/'result.json') == raw, 'Checkout/record changed during read-only audit')
    copied = []
    def save(name, value):
        remotes()
        target = OUT/name
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        descriptor = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(value); stream.flush(); os.fsync(stream.fileno())
        ref = {'path':name,'bytes':len(value),'sha256':sha(value)}
        copied.append(ref)
        return ref
    for path in sorted(ATTEMPT.iterdir()):
        if path.is_file() and (path.name == 'result.json' or path.suffix == '.log'):
            save('additional/contributor-setup-v2/'+path.name,read(path))
    save('additional/contributor-setup-v2/capture.py',helper)
    for name in critical:
        save('additional/contributor-setup-v2/source/'+name,read(CLONE/name))
    for directory in ('contributor-setup/attempt01','socket-path-fix'):
        for path in sorted((REPO/'docs/urbit/evidence/2026-09-26'/directory).iterdir()):
            need(path.is_file(), 'Unexpected nested legacy/fix evidence')
            save('additional/'+directory+'/'+path.name,read(path))
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    final = {'protocol':'stead.urb170-final-acceptance-review/1','reviewer':'/root/independent_review',
        'recorded_at':stamp,'issue':'https://github.com/ScottTpirate/stead-urbit/issues/20',
        'disposition':'URB-170 acceptance supported; integrator may close the issue with the cited bounded results.',
        'whole_issue_acceptance_supported':True,'qualifies_phase1':False,
        'actual_native_trial_commit':TRIAL,'actual_clean_setup_commit':HEAD,
        'source_identity_rule':'The 0d877 paired native run remains bound to its exact source. The 55475 setup executes setup/doctor/status only; no native evidence is relabeled or carried across the harness change.',
        'prior_records_preserved':{'byte_index_sha256':before['index.json'],
            'paired_result_sha256':before['reports/result.json'],
            'portable_review_sha256':before['POSTPACKAGING_REVIEW.json'],
            'criterion_map_sha256':before['URB170_CRITERIA_REVIEW.json'],
            'upstream_link_addendum_sha256':before['UPSTREAM_LINK_REVIEW.json']},
        'clean_setup':{'capture_sha256':sha(helper),'capture_delta':'Only fixed source commit and create-once output directory changed.',
            'result_sha256':sha(raw),'source_tree':tree,'checkout_tracked_clean_reobserved':True,
            'actual_four_downloads_rehashed':record['downloads'],'executed_source_hashes':source,
            'observed_namespace_negatives':record['final']['namespace_negative_result'],
            'no_live_pier_or_socket_reobserved':True,'logs':copied.copy()},
        'criteria':[
            {'id':'scoped-local-skills','status':'supported','evidence':'URB170_CRITERIA_REVIEW.json:scoped-local-skills'},
            {'id':'upstream-intake-and-repair-proposal','status':'supported-reference-only-unsent-proposal','evidence':'UPSTREAM_LINK_REVIEW.json'},
            {'id':'optional-editor-tool','status':'supported-evaluated-not-adopted','evidence':'URB170_CRITERIA_REVIEW.json:optional-editor-tool'},
            {'id':'frozen-six-task-comparison','status':'supported-completed-5-of-6-tie','evidence':'reports/result.json'},
            {'id':'frontmatter-and-lf','status':'supported-host-and-source','evidence':'URB170_CRITERIA_REVIEW.json:frontmatter-and-lf'},
            {'id':'reference-links','status':'supported-retained-actual-get-observations','evidence':'UPSTREAM_LINK_REVIEW.json'},
            {'id':'sandbox-negative-controls','status':'supported-actual-host-boundary-and-authored-fault-controls-separated','evidence':'URB170_CRITERIA_REVIEW.json:sandbox-negative-controls; additional/contributor-setup-v2/doctor.stdout.log'},
            {'id':'clean-contributor-setup','status':'supported-pinned-download-setup-doctor-stopped','evidence':'additional/contributor-setup-v2/result.json'}],
        'unresolved_issue_criteria':[], 'native_or_host_tests_started_by_this_reviewer':False,
        'reviewer_actions':'Read retained execution/command logs and reviewed source; rehashed actual downloads and copied evidence. No setup, doctor, status, tests, ship or participant execution by this reviewer.',
        'resource_scope':{'affinity':[19],'cpu_max':cpu,'control_group':cgroup},
        'limits':['Clean setup uses preexisting Linux prerequisites and a local source clone; fresh OS provisioning and GitHub authentication were not exercised.',
            'No ships booted in the clean setup; T06 native desk assembly and the paired comparison are separate actual earlier executions.',
            'Both participants score5/6; full T05 mutation inventories remain behavioral failures. No general skill improvement claim.',
            'Full inherited tools remained exposed; one missing-path invocation is disclosed. Twelve earlier plaintexts remain unavailable; three are attributed observations. No complete isolation/equality claim.',
            'Optional language server was rejected before native/editor integration; proposed upstream skill repair is unsent and uncompiled.',
            'Original failed clean setup and earlier pending labels remain preserved. Phase1 current-source qualification stays separate and incomplete.']}
    save('URB170_FINAL_ACCEPTANCE_REVIEW.json',(json.dumps(final,indent=2,sort_keys=True)+'\n').encode())
    text = '''URB-170 acceptance is supported. The integrator may close [issue20](https://github.com/ScottTpirate/stead-urbit/issues/20) with the bounded outcomes below; this does not close Phase1.

The [final criterion review](URB170_FINAL_ACCEPTANCE_REVIEW.json) completes the earlier eight-row map. Four local skills and scoped guidance, the pinned upstream license/instruction review and separate unsent repair proposal, optional editor non-adoption, actual six-task paired evaluation, frontmatter/LF and link checks, and actual sandbox controls have separate evidence. The final missing contributor-setup criterion now has a real clean attempt at `55475f0565ceb38db9eb5bc057962967398aa5da`: setup, doctor and stopped status all exit0. Four pins were downloaded into the new empty cache and independently rehashed; tracked source remains clean, with no live pier or control socket. The doctor actually checked namespace isolation. [Raw setup records](additional/contributor-setup-v2/result.json) and the original failed long-path attempt are preserved.

The [paired native result](reports/result.json) remains bound to `0d877cff4319de8d437f0da58d4518535f758c36`, with a complete **5/6 tie** and full mutation evidence for both failed T05 suites. No native result is relabeled to the later socket-path fix. There is no improvement, complete tool/context isolation, or initial-plaintext equality claim. Twelve earlier message plaintexts remain unavailable; three are attributed integrator observations. No private repairs or repeated private scores occurred.

Reviewer `/root/independent_review` audited retained artifacts and rehashed the actual downloaded files, without launching tests, setup, ships or participants. The fresh setup uses existing Linux prerequisites and a local source clone; it does not establish fresh-OS provisioning or GitHub authentication. Original prequalification, packaging and criterion records retain their earlier pending labels. This later addendum and `FINAL_ACCEPTANCE_INDEX.json` provide the final URB-170 disposition; current-source Phase1 qualification remains separate.
'''
    save('URB170_FINAL_ACCEPTANCE.md',text.encode())
    save('additional/contributor-setup-v2/audit.py',read(Path(__file__).resolve()))
    need(all(sha(read(OUT/name)) == expected for name,expected in before.items()), 'Original portable evidence changed')
    summary = {'protocol':'stead.workflow-v2-final-acceptance-index/1','recorded_at':stamp,
        'original_index_sha256':before['index.json'],'previous_supplement_sha256':before['POSTPACKAGING_ADDENDUM_INDEX.json'],
        'classification':'Later actual setup audit and whole-URB170 criterion disposition; original paired corpus/archive unchanged',
        'files':copied.copy(),'original_portable_files_preserved':len(before),'native_or_test_rerun':False}
    value=(json.dumps(summary,indent=2,sort_keys=True)+'\n').encode()
    index=save('FINAL_ACCEPTANCE_INDEX.json',value)
    print(json.dumps({'final_acceptance_index':index,'files_added':len(copied),
                      'review_sha256':sha(read(OUT/'URB170_FINAL_ACCEPTANCE_REVIEW.json')),
                      'whole_urb170_supported':True,'phase1_qualified':False},indent=2))


if __name__ == '__main__':
    main()
