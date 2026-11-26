import { useEffect, useState } from 'react';
import { UUID, packRefs, type Fields, type HomeClient } from './api';
import { CopyValue } from './CodeRepository';
import { refHex } from './externalReview';
import { Button } from './primitives';

export type CodeDevelopmentTarget = {
  workId: string;
  title: string;
  ref: string;
  mode: 'browse' | 'review';
};

export function workBranchRef(workId: string) {
  return refHex(`refs/heads/work/${workId}`);
}

type Readback = { scope: string } & (
  { status: 'ready'; snapshot: Fields; writable: boolean } | { status: 'unavailable' });

export function WorkDevelopment({ client, project, work, writable, onOpenCode }: {
  client: HomeClient; project: string; work: { id: string; title: string }; writable: boolean;
  onOpenCode: (target: CodeDevelopmentTarget) => void;
}) {
  const scope = `${project}/${work.id}`;
  const [readback, setReadback] = useState<Readback | null>(null);
  const [attempt, setAttempt] = useState(0);
  const current = readback?.scope === scope ? readback : null;

  useEffect(() => {
    if (!UUID.test(work.id)) return;
    let active = true;
    void client.externalRepository(project).then(({snapshot, access, atCapacity}) => {
      if (!active) return;
      if (access.status === 'external') {
        setReadback({scope, status: 'ready', snapshot, writable: access.writable && !atCapacity});
      } else setReadback({scope, status: 'unavailable'});
    }).catch(() => { if (active) setReadback({ scope, status: 'unavailable' }); });
    return () => { active = false; };
  }, [client, project, work.id, scope, attempt]);

  if (!UUID.test(work.id)) return null;
  const branch = `work/${work.id}`;
  const ref = workBranchRef(work.id);
  const snapshot = current?.status === 'ready' ? current.snapshot : null;
  const refs = snapshot ? packRefs(snapshot) : {};
  const base = snapshot?.head ? refs[snapshot.head] : undefined;
  const commit = refs[ref];
  const canWrite = current?.status === 'ready' && writable && current.writable;
  const canReview = canWrite && snapshot?.generation !== undefined && !!commit && commit !== base;
  function open(mode: CodeDevelopmentTarget['mode']) {
    onOpenCode({ workId: work.id, title: work.title, ref, mode });
  }

  return <section className="work-development" aria-label="Development">
    <h3>Development</h3>
    {!current && <p role="status">Checking the accepted Git snapshot…</p>}
    {current?.status === 'unavailable' && <p role="status">The accepted Git snapshot is unavailable.</p>}
    {current?.status === 'ready' && <div className="work-development-branch">
      {commit || canWrite ? <code>{branch}</code> : null}
      <p role="status">{commit ? 'Branch is in the accepted Git snapshot.' : 'No matching branch in the accepted Git snapshot.'}</p>
      {commit && snapshot?.head === ref && <p>This is the repository’s default branch.</p>}
      {commit && canWrite && snapshot?.head !== ref && commit === base && <p>Push a change to this branch to start a review.</p>}
    </div>}
    <div className="work-development-actions">
      {commit && <Button variant="quiet" onClick={() => open('browse')}>View branch</Button>}
      {canReview && <Button onClick={() => open('review')}>Start change review</Button>}
      {!commit && canWrite && <CopyValue key={branch} value={branch} label="Copy branch name" fallbackLabel="Select the branch name to copy it." />}
      <Button variant="quiet" disabled={!current}
        onClick={() => { setReadback(null); setAttempt(value => value + 1); }}>Check for branch</Button>
    </div>
    {!commit && canWrite && base && <details className="work-development-commands">
      <summary>Branch commands</summary>
      <p>Open Code to clone this repository. In that clone, run <code>git fetch origin</code> first.</p>
      <div className="work-development-actions">
        <CopyValue value={`git switch -c ${branch} ${base}`} label="Copy create command" fallbackLabel="Select the command to copy it." />
        <CopyValue value={`git push -u origin ${branch}`} label="Copy push command" fallbackLabel="Select the command to copy it." />
      </div>
      <p>Push your change, then check for the branch in Stead.</p>
    </details>}
  </section>;
}
