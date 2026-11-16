// This is a display parser for the already-authorized, possibly escaped patch.
// The original string is never reconstructed, repaired or used as authority.
export const PATCH_DISPLAY_BYTES = 196608;
export const PATCH_DISPLAY_LINES = 4096;
export const PATCH_DISPLAY_HUNKS = 256;

export type PatchLine = {
  readonly kind: 'context' | 'added' | 'removed' | 'note';
  readonly text: string;
  readonly oldLine?: number;
  readonly newLine?: number;
};
export type PatchHunk = {readonly header: string; readonly lines: readonly PatchLine[]};
export type ParsedPatch = {readonly kind: 'parsed'; readonly headers: readonly string[]; readonly hunks: readonly PatchHunk[]}
  | {readonly kind: 'fallback'; readonly reason: 'syntax' | 'display-limit'};

const hunkHeader = /^@@ -(0|[1-9][0-9]*)(?:,(0|[1-9][0-9]*))? \+(0|[1-9][0-9]*)(?:,(0|[1-9][0-9]*))? @@(?: .*)?$/u;
const mode = '(?:100644|100755|120000|160000)';
const modeHeader = new RegExp(`^(?:old mode|new mode|new file mode|deleted file mode) ${mode}$`, 'u');
const indexHeader = new RegExp(`^index [0-9a-f]{4,64}\\.\\.[0-9a-f]{4,64}(?: ${mode})?$`, 'u');

export function parseUnifiedPatch(text: string): ParsedPatch {
  const fail = (reason: 'syntax' | 'display-limit' = 'syntax'): ParsedPatch => ({kind: 'fallback', reason});
  if (new TextEncoder().encode(text).length > PATCH_DISPLAY_BYTES) return fail('display-limit');
  if (!text) return {kind: 'parsed', headers: [], hunks: []};
  // Git emits LF-terminated patch records. An incomplete record gets Raw only.
  if (!text.endsWith('\n') || text.includes('\r')) return fail();
  const records = text.slice(0, -1).split('\n');
  if (records.length > PATCH_DISPLAY_LINES) return fail('display-limit');
  if (!/^diff --git .+ .+$/u.test(records[0]!)) return fail();
  const headers: string[] = [records[0]!];
  let at = 1;
  const metadata: string[] = [];
  while (at < records.length && !records[at]!.startsWith('--- ')) {
    const row = records[at]!;
    if (!modeHeader.test(row) && !indexHeader.test(row)) return fail();
    metadata.push(row); headers.push(row); at++;
  }
  // Keep only the complete header orders emitted by the fixed no-renames Git
  // command. Unsupported extended headers remain visible in full through Raw.
  const kinds = metadata.map(row => row.startsWith('index ') ? 'index' : row.slice(0, row.lastIndexOf(' '))).join('|');
  const allowed = ['', 'index', 'old mode|new mode', 'old mode|new mode|index',
    'new file mode|index', 'deleted file mode|index'];
  if (!allowed.includes(kinds)) return fail();
  if (at === records.length) {
    // Header-only creates/deletes may be a truncated nonempty patch. Keep
    // their entire supplied text in Raw rather than infer an empty file.
    return kinds === 'old mode|new mode' ? {kind: 'parsed', headers, hunks: []} : fail();
  }
  if (!records[at]!.startsWith('--- ') || records[at]!.length <= 4
      || !records[at + 1]?.startsWith('+++ ') || records[at + 1]!.length <= 4) return fail();
  headers.push(records[at++]!, records[at++]!);
  const hunks: PatchHunk[] = [];
  let previousOldEnd = 0, previousNewEnd = 0, endOfFileMarked = false;
  while (at < records.length) {
    if (endOfFileMarked) return fail();
    if (hunks.length >= PATCH_DISPLAY_HUNKS) return fail('display-limit');
    const header = records[at++]!, match = hunkHeader.exec(header);
    if (!match) return fail();
    let oldLine = Number(match[1]), newLine = Number(match[3]);
    const oldCount = Number(match[2] ?? '1'), newCount = Number(match[4] ?? '1');
    if (![oldLine, newLine, oldCount, newCount, oldLine + oldCount, newLine + newCount].every(Number.isSafeInteger)
        || (oldCount > 0 && oldLine === 0) || (newCount > 0 && newLine === 0) || (!oldCount && !newCount)) return fail();
    const oldAnchor = oldCount ? oldLine : oldLine + 1, newAnchor = newCount ? newLine : newLine + 1;
    if (!Number.isSafeInteger(oldAnchor) || !Number.isSafeInteger(newAnchor)
        || oldAnchor < previousOldEnd || newAnchor < previousNewEnd
        || oldAnchor - previousOldEnd !== newAnchor - previousNewEnd) return fail();
    previousOldEnd = oldCount ? oldLine + oldCount : oldAnchor;
    previousNewEnd = newCount ? newLine + newCount : newAnchor;
    let oldRemaining = oldCount, newRemaining = newCount, mayMark = false;
    const lines: PatchLine[] = [];
    while (at < records.length && !records[at]!.startsWith('@@ ')) {
      const row = records[at++]!;
      if (row === '\\ No newline at end of file') {
        if (!mayMark) return fail();
        const previous = lines[lines.length - 1]!;
        if ((previous.kind === 'removed' && oldRemaining !== 0) || (previous.kind === 'added' && newRemaining !== 0)
            || (previous.kind === 'context' && (oldRemaining !== 0 || newRemaining !== 0))) return fail();
        endOfFileMarked = true;
        mayMark = false; lines.push({kind: 'note', text: row}); continue;
      }
      if (row.startsWith(' ') && oldRemaining > 0 && newRemaining > 0) {
        lines.push({kind: 'context', text: row.slice(1), oldLine: oldLine++, newLine: newLine++});
        oldRemaining--; newRemaining--;
      } else if (row.startsWith('-') && oldRemaining > 0) {
        lines.push({kind: 'removed', text: row.slice(1), oldLine: oldLine++}); oldRemaining--;
      } else if (row.startsWith('+') && newRemaining > 0) {
        lines.push({kind: 'added', text: row.slice(1), newLine: newLine++}); newRemaining--;
      } else return fail();
      mayMark = true;
    }
    if (oldRemaining || newRemaining) return fail();
    hunks.push({header, lines});
  }
  return hunks.length ? {kind: 'parsed', headers, hunks} : fail();
}
