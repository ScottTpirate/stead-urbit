import json
from pathlib import Path
import sys
sys.path[:0] = ['/src/scripts/sdk_native','/src/scripts/urbit']
from native import Native
import multi_home_signin_trial, native_tls

class Peer(Native):
    def _arguments(self):
        args = super()._arguments()
        return args[:1] + ['--https-port', str(native_tls.PORTS[self.ship])] + args[1:]

ships = []
try:
    imports = Path('/state/source')
    for name in json.loads(Path('/src/focus-files.json').read_text()):
        src = Path('/src/native/core/desk') / name
        target = imports / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(src.read_bytes())
    for ship, port in [('zod',31337),('nec',31338)]:
        peer = Peer(ship, port, lambda: None)
        ships.append(peer)
        print('Booting and verifying source on',ship,flush=True)
        peer.start()
        peer.install(imports)
    multi_home_signin_trial.run(*ships)
finally:
    for peer in reversed(ships):
        peer.stop()
