import { compactSteadPaths } from './src/brandGeometry.ts';
import { build } from 'esbuild';
import { mkdtemp, readFile, writeFile, rm, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { publishDirectory } from './publish.mjs';
const script = fileURLToPath(import.meta.url);
const root = path.dirname(script);
// Linux flock releases on crashes too; concurrent builds never share staging.
if (process.argv[2] !== '--locked') {
  const child = spawnSync('flock', ['-n', '-E', '75', path.join(root, '.build.lock'), process.execPath, script, '--locked'], {stdio: 'inherit'});
  if (child.error) throw child.error;
  if (child.status === 75) console.error('A Stead browser build is already running.');
  process.exit(child.status ?? 1);
}
const outdir = await mkdtemp(path.join(root, '.build-'));
let published = false;
try {
  // A product entry gives shared UI code a bounded chunk without changing synchronous app imports.
  const result = await build({ absWorkingDir: root, entryPoints: { app: 'src/main.tsx', identity: 'src/identity.ts', product: 'src/productWorkJourney.tsx' },
    bundle: true, minify: true, sourcemap: false, metafile: true, target: ['es2022'],
    format: 'esm', splitting: true, chunkNames: 'chunk-[hash]', outdir, legalComments: 'external',
    define: { 'process.env.NODE_ENV': '"production"' } });
  const favicon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">\n'
    + '<rect width="16" height="16" rx="2.5" fill="#181817"/>\n'
    + '<g fill="#f6f2eb" transform="translate(1 1) scale(.875)">\n'
    + compactSteadPaths.map(path => '<path d="' + path + '"/>').join('\n') + '\n</g></svg>\n';
  await writeFile(path.join(outdir, 'favicon.svg'), favicon);
  const html = '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Stead</title><link rel="icon" type="image/svg+xml" href="/stead/assets/favicon.svg"><link rel="stylesheet" href="/stead/assets/app.css"></head><body><div id="root"></div><script type="module" src="/stead/assets/app.js"></script></body></html>\n';
  await writeFile(path.join(outdir, 'index.html'), html);
  const identityHtml = '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Stead identity approval</title><link rel="stylesheet" href="/stead-identity/assets/identity.css"></head><body><main id="root"></main><script type="module" src="/stead-identity/assets/identity.js"></script></body></html>\n';
  await writeFile(path.join(outdir, 'identity.html'), identityHtml);
  let notices = 'Stead Urbit browser alpha\nApache-2.0; see the source repository and PROVENANCE.md for original source attribution.\n\n';
  notices += await readFile(path.join(root, '../../LICENSE'), 'utf8');
  const licenses = {'react':'LICENSE', 'react-dom':'LICENSE', 'scheduler':'LICENSE',
    'markdown-it':'LICENSE', 'mdurl':'LICENSE', 'entities':'LICENSE', 'uc.micro':'LICENSE.txt',
    'linkify-it':'LICENSE', 'punycode.js':'LICENSE-MIT.txt', 'argparse':'LICENSE'};
  for (const [name, license] of Object.entries(licenses)) {
    notices += `\n\nDependency: ${name}\n` + await readFile(path.join(root, 'node_modules', name, license), 'utf8');
  }
  notices += '\n\nDependency: audited local Lucide icon subset\n'
    + await readFile(path.join(root,'vendor/lucide/LICENSE'),'utf8');
  notices += '\n\nUrbit ship sigil artwork and phoneme indexing (sigil-js, urbit-ob)\n'
    + await readFile(path.join(root, 'vendor/urbit-sigil/LICENSE'), 'utf8');
  await writeFile(path.join(outdir, 'NOTICE.txt'), notices);
  const manifest = { format: 1, classification: 'frontend-build-only', files: {} };
  for (const name of ['index.html', 'identity.html', 'NOTICE.txt', 'favicon.svg', ...Object.keys(result.metafile.outputs).map(file => path.basename(file))]) {
    if (Object.hasOwn(manifest.files, name)) throw new Error('Duplicate output identity');
    const bytes = await readFile(path.join(outdir, name));
    manifest.files[name] = { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
  }
  if (JSON.stringify((await readdir(outdir)).sort()) !== JSON.stringify(Object.keys(manifest.files).sort())) throw new Error('Unexpected output inventory');
  await writeFile(path.join(outdir, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  await writeFile(path.join(outdir, 'metafile.json'), JSON.stringify(result.metafile, null, 2) + '\n');
  await publishDirectory(outdir, path.join(root, 'dist')); published = true;
  console.log(JSON.stringify(manifest, null, 2));
} finally {
  if (!published) await rm(outdir, {recursive: true, force: true});
  // An interrupted replacement's uniquely named previous output is retained.
}
