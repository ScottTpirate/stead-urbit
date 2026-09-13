"""Static metadata and mocked GitHub sync tests. No native Hoon or live API calls."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
from check_ecosystem import check, load, SKILLS
from sync_milestones import synchronize


def copy_planning_fixture(source, target):
    """Copy only validator inputs; never touch active piers or downloaded tools."""
    paths = ['specs/urbit/ecosystem.json', 'specs/urbit/backlog.json',
             'AGENTS.md', 'CONTRIBUTING.md', 'SECURITY.md', 'SUPPORT.md',
             'docs/urbit/ECOSYSTEM_PLAN.md', 'docs/urbit/DEVELOPER_GUIDE.md',
             'docs/urbit/STEAD_CARRYOVER.md']
    paths += ['.agents/skills/' + name + '/SKILL.md' for name in SKILLS]
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, destination)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        copy_planning_fixture(ROOT, self.root)

    def test_runtime_and_piers_are_not_fixture_inputs(self):
        import socket
        source = self.root
        (source / '.runtime').mkdir()
        (source / '.runtime/private').write_text('synthetic do-not-copy sentinel')
        (source / '.piers').mkdir()
        with socket.socket(socket.AF_UNIX) as control:
            control.bind(str(source / '.piers/conn.sock'))
            target = Path(self.tmp.name) / 'second-fixture'
            copy_planning_fixture(source, target)
        self.assertFalse((target / '.runtime').exists())
        self.assertFalse((target / '.piers').exists())
        self.assertEqual(check(target), (30, 7, 4))
    def mutate(self, fn):
        path = self.root / 'specs/urbit/ecosystem.json'
        data = json.loads(path.read_text()); fn(data); path.write_text(json.dumps(data))
        with self.assertRaises((ValueError, KeyError, OSError, TypeError)):
            check(self.root)
    def test_valid(self):
        self.assertEqual(check(self.root), (30, 7, 4))
    def test_wrong_repository(self):
        self.mutate(lambda d: d.update(repository='ScottTpirate/stead'))
    def test_duplicate_task(self):
        self.mutate(lambda d: d['tasks'].append(copy.deepcopy(d['tasks'][0])))
    def test_unknown_dependency(self):
        self.mutate(lambda d: d['tasks'][0]['depends_on'].append('URB-999'))
    def test_cycle(self):
        self.mutate(lambda d: d['tasks'][0]['depends_on'].append(d['tasks'][0]['id']))
    def test_canary_cycle(self):
        self.mutate(lambda d: d['canary_admission'].append('URB-280'))
    def test_issue_collision(self):
        self.mutate(lambda d: d['issue_map'].update({'URB-170':2}))
    def test_missing_mapping(self):
        self.mutate(lambda d: d['issue_map'].pop('URB-170'))
    def test_wrong_milestone(self):
        self.mutate(lambda d: d['milestones'][0]['tasks'].append('URB-280'))
    def test_missing_skill(self):
        (self.root/'.agents/skills/stead-hoon/SKILL.md').unlink()
        with self.assertRaises(OSError): check(self.root)
    def test_bad_frontmatter(self):
        path=self.root/'.agents/skills/stead-hoon/SKILL.md'
        path.write_text(path.read_text().replace('name: stead-hoon','name: wrong'))
        with self.assertRaises(ValueError): check(self.root)
    def test_missing_guidance(self):
        (self.root/'SECURITY.md').unlink()
        with self.assertRaises(ValueError): check(self.root)

class FakeAPI:
    def __init__(self):
        meta,_=load(ROOT)
        self.milestones=[]
        self.issues={n:{'title':'['+task+'] test','milestone':None} for task,n in meta['issue_map'].items()}
        self.writes=[]
    def __call__(self,method,path,body=None,paginate=False):
        if paginate: return [copy.deepcopy(self.milestones)]
        if '/issues/' in path:
            n=int(path.rsplit('/',1)[1])
            if method=='GET': return copy.deepcopy(self.issues[n])
            self.writes.append((method,path,body))
            self.issues[n]['milestone']=next(copy.deepcopy(m) for m in self.milestones if m['number']==body['milestone'])
            return copy.deepcopy(self.issues[n])
        self.writes.append((method,path,body))
        m={'title':body['title'],'number':len(self.milestones)+1}
        self.milestones.append(m)
        return copy.deepcopy(m)

class SyncTests(unittest.TestCase):
    def test_create_assign_and_idempotence(self):
        api=FakeAPI()
        self.assertEqual(synchronize(ROOT,api),(7,30))
        writes=len(api.writes)
        self.assertEqual(synchronize(ROOT,api),(0,0))
        self.assertEqual(len(api.writes),writes)
    def test_wrong_issue_aborts_before_write(self):
        api=FakeAPI(); api.issues[2]['title']='Unrelated task'
        with self.assertRaises(ValueError): synchronize(ROOT,api)
        self.assertEqual(api.writes,[])
    def test_conflicting_assignment_aborts_before_write(self):
        api=FakeAPI(); api.issues[2]['milestone']={'title':'Other plan','number':99}
        with self.assertRaises(ValueError): synchronize(ROOT,api)
        self.assertEqual(api.writes,[])
    def test_pr_aborts_before_write(self):
        api=FakeAPI(); api.issues[2]['pull_request']={}
        with self.assertRaises(ValueError): synchronize(ROOT,api)
        self.assertEqual(api.writes,[])

if __name__=='__main__': unittest.main()
