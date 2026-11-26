import {useEffect, useId, useMemo, useRef, useState} from 'react';
import {Button} from './primitives';
import {parseUnifiedPatch} from './unifiedPatchParser';
import './unified-patch.css';

const labels = {context: 'Unchanged line', added: 'Added line', removed: 'Removed line'} as const;
const markers = {context: ' ', added: '+', removed: '−'} as const;

export function UnifiedPatch({text, sanitized}: {readonly text: string; readonly sanitized: boolean}) {
  const parsed = useMemo(() => parseUnifiedPatch(text), [text]);
  const [mode, setMode] = useState<'diff' | 'raw'>('diff');
  const [selected, setSelected] = useState(0);
  const id = useId(), content = useRef<HTMLDivElement>(null);
  const mounted = useRef(true), identity = useRef({text, sanitized});
  if (identity.current.text !== text || identity.current.sanitized !== sanitized) identity.current = {text, sanitized};
  const owner = identity.current;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const available = parsed.kind === 'parsed';
  const shown = available ? mode : 'raw';
  const hunks = available ? parsed.hunks : [];
  const active = Math.min(selected, Math.max(0, hunks.length - 1));
  function choose(next: 'diff' | 'raw') {
    if (mounted.current && identity.current === owner) setMode(next);
  }
  function go(index: number) {
    if (!mounted.current || identity.current !== owner || shown !== 'diff' || index < 0 || index >= hunks.length) return;
    const target = content.current?.querySelector<HTMLElement>(`[data-patch-hunk="${index}"]`);
    if (!target || !content.current?.contains(target)) return;
    setSelected(index); target.focus({preventScroll: true}); target.scrollIntoView({block: 'nearest', behavior: 'auto'});
  }
  return <div className="unified-patch">
    <div className="unified-patch-toolbar">
      {available && <div role="tablist" aria-label="Patch display" onKeyDown={event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 'diff' : event.key === 'End' ? 'raw' : shown === 'diff' ? 'raw' : 'diff';
        choose(next); event.currentTarget.querySelector<HTMLButtonElement>(`[data-patch-mode="${next}"]`)?.focus();
      }}>
        {(['diff', 'raw'] as const).map(value => <Button key={value} variant="quiet" role="tab" id={`${id}-${value}`}
          aria-controls={`${id}-content`} aria-selected={shown === value} tabIndex={shown === value ? 0 : -1}
          data-patch-mode={value} onClick={() => choose(value)}>{value === 'diff' ? 'Diff' : 'Raw'}</Button>)}
      </div>}
      <span>Read-only</span>
      {shown === 'diff' && hunks.length > 1 && <nav aria-label="Patch hunks">
        <Button variant="quiet" disabled={active === 0} onClick={() => go(active - 1)}>Previous hunk</Button>
        <span>Selected hunk {active + 1} of {hunks.length}</span>
        <Button variant="quiet" disabled={active + 1 >= hunks.length} onClick={() => go(active + 1)}>Next hunk</Button>
      </nav>}
    </div>
    {sanitized && <p className="unified-patch-note">Control and direction characters are shown as visible escapes. Raw preserves this supplied patch, including those escapes.</p>}
    {!available && <p className="unified-patch-note" role="status">{parsed.reason === 'display-limit'
      ? 'This patch exceeds the numbered display limit. The full supplied patch is shown below.'
      : 'This patch cannot be numbered reliably. The full supplied patch is shown below.'}</p>}
    <div ref={content} id={`${id}-content`} role={available ? 'tabpanel' : undefined}
      aria-labelledby={available ? `${id}-${shown}` : undefined}>
      {shown === 'raw' ? <pre className="unified-patch-raw" tabIndex={0} aria-label="Raw supplied patch">{text}</pre>
        : available && <>
          {parsed.headers.length > 0 && <details className="unified-patch-headers"><summary>Patch headers</summary><pre tabIndex={0}>{parsed.headers.join('\n')}</pre></details>}
          {!hunks.length && <p className="unified-patch-note">{text ? 'This patch has no text hunks. See the patch headers for file metadata changes.' : 'No text changes.'}</p>}
          {hunks.map((hunk, index) => <section key={index} className="unified-patch-hunk">
            <h5 tabIndex={-1} data-patch-hunk={index} onFocus={() => setSelected(index)}>Hunk {index + 1}: <code>{hunk.header}</code></h5>
            <div className="unified-patch-lines" role="region" tabIndex={0} aria-label={`Hunk ${index + 1} lines`}>
              <table><thead><tr><th scope="col">Old</th><th scope="col">New</th><th scope="col">Change</th><th scope="col">Content</th></tr></thead>
                <tbody>{hunk.lines.map((line, row) => line.kind === 'note'
                  ? <tr key={row} className="unified-patch-note-row"><td colSpan={4}>{line.text}</td></tr>
                  : <tr key={row} className={`unified-patch-${line.kind}`}><td>{line.oldLine ?? ''}</td><td>{line.newLine ?? ''}</td>
                    <td><span className="stead-visually-hidden">{labels[line.kind]}</span><span aria-hidden="true">{markers[line.kind]}</span></td><td><code>{line.text}</code></td></tr>)}</tbody>
              </table>
            </div>
          </section>)}
        </>}
    </div>
  </div>;
}
