"""Real host systemd/process-lifetime controls; no native/Firefox pass implied."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'web/app'))
import browser_process


CHILD = '''import os,sys,time
from pathlib import Path
pid=os.fork()
if pid == 0:
    os.setsid()
    Path(sys.argv[1]).write_text(str(os.getpid()))
    time.sleep(300)
else:
    while not Path(sys.argv[1]).exists(): time.sleep(.01)
    if sys.argv[2] == 'hang': time.sleep(300)
'''


def not_running(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split(') ')[1].startswith('Z ')
    except FileNotFoundError:
        return True


class BrowserProcessControls(unittest.TestCase):
    def test_normal_exit_removes_detached_descendant(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime', prefix='browser-owner-normal-') as path:
            output = Path(path)
            pidfile = output / 'detached.pid'
            result = browser_process.run(['/usr/bin/python3', '-c', CHILD, str(pidfile), 'exit'],
                root=ROOT, output=output, healthy=lambda: None, timeout=10)
            self.assertEqual(result['status'], 'pass')
            self.assertTrue(result['cleanup']['empty'])
            self.assertTrue(not_running(int(pidfile.read_text())))

    def test_timeout_removes_detached_descendant(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime', prefix='browser-owner-timeout-') as path:
            output = Path(path)
            pidfile = output / 'detached.pid'
            with self.assertRaises(TimeoutError):
                browser_process.run(['/usr/bin/python3', '-c', CHILD, str(pidfile), 'hang'],
                    root=ROOT, output=output, healthy=lambda: None, timeout=1)
            self.assertTrue(json.loads((output / 'browser-process.json').read_text())['cleanup']['empty'])
            self.assertTrue(not_running(int(pidfile.read_text())))

    def test_controller_sigkill_closes_pipe_and_stops_service(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime', prefix='browser-owner-death-') as path:
            output = Path(path)
            pidfile = output / 'detached.pid'
            launcher = ('import sys; from pathlib import Path; '
                'sys.path.insert(0, sys.argv[1] + "/web/app"); import browser_process; '
                'browser_process.run(["/usr/bin/python3","-c",sys.argv[4],sys.argv[3],"hang"],'
                'root=Path(sys.argv[1]),output=Path(sys.argv[2]),healthy=lambda:None,timeout=20)')
            process = subprocess.Popen(['/usr/bin/python3', '-B', '-c', launcher, str(ROOT), str(output), str(pidfile), CHILD])
            try:
                deadline = time.monotonic() + 10
                while not pidfile.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail('Controller failed before descendant spawn')
                    time.sleep(.05)
                proof = next(output.glob('stead-browser-*.service.json'))
                value = json.loads(proof.read_text())
                unit = proof.name.removesuffix('.json')
                process.kill()
                process.wait(timeout=3)
                deadline = time.monotonic() + 8
                while not browser_process.group_empty(value['cgroup']):
                    if time.monotonic() > deadline:
                        self.fail('Controller death left browser descendants')
                    time.sleep(.1)
                self.assertTrue(not_running(int(pidfile.read_text())))
                self.assertIn(browser_process.properties(unit)['ActiveState'], ('inactive', 'failed'))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)

    def test_debug_and_keylog_environment_do_not_transfer(self):
        saved = dict(os.environ)
        try:
            os.environ.update(DEBUG='pw:protocol,pw:channel', DEBUG_FILE='/tmp/forbidden', PWDEBUG='1',
                              SSLKEYLOGFILE='/tmp/forbidden', NODE_OPTIONS='--inspect', MOZ_DISABLE_CONTENT_SANDBOX='1')
            environment = browser_process.clean_environment(ROOT)
            self.assertEqual(set(environment), {'PATH', 'HOME', 'LANG', 'XDG_RUNTIME_DIR', 'PLAYWRIGHT_BROWSERS_PATH'})
        finally:
            os.environ.clear()
            os.environ.update(saved)


if __name__ == '__main__':
    unittest.main(verbosity=2)
