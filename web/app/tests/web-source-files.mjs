import assert from 'node:assert/strict';
import {readdir} from 'node:fs/promises';
import path from 'node:path';

// Retain the browser inputs, including the Markdown shipped inside the client.
export async function webSourceFiles(root) {
  const files = [];
  async function collect(directory) {
    const entries = await readdir(path.join(root, directory), {withFileTypes:true});
    assert.ok(entries.length > 0 && entries.length <= 128);
    for (const entry of entries) {
      const name = directory + '/' + entry.name;
      if (name === 'src/handbook' && entry.isDirectory()) {
        await collect(name);
      } else {
        assert.ok(entry.isFile() && !entry.isSymbolicLink(), name);
        if (directory === 'src/handbook') assert.match(entry.name, /^[a-zA-Z0-9-]+\.md$/u);
        files.push(name);
        assert.ok(files.length <= 128);
      }
    }
  }
  await collect('src');
  return files.sort();
}
