import { useEffect, useRef, useState } from 'react';
import { watchApproval, type ApprovalNotice } from './approvalWatch';
import { Button, Surface, TextField } from './primitives';
import './urbit-sign-in.css';

type SignInProps = {
  ship: string;
  challenge: { challenge_id?: string; comparison_code?: string; expires_at_ms?: string } | null;
  busy: boolean;
  origin: string;
  notice: string;
  onShipChange: (ship: string) => void;
  onRequest: () => void;
  onCheck: () => void;
  onObserve: (id: string, signal: AbortSignal) => Promise<string>;
  onBack: () => void;
};

export function UrbitSignIn({ ship, challenge, busy, origin, notice, onShipChange, onRequest, onCheck, onObserve, onBack }: SignInProps) {
  const approvalHeading = useRef<HTMLHeadingElement>(null);
  const identityInput = useRef<HTMLInputElement>(null);
  const focusOnReturn = useRef(false);
  const [approval, setApproval] = useState<{id: string; notice: ApprovalNotice} | null>(null);
  const challengeId = challenge?.challenge_id;
  const expiresAt = challenge?.expires_at_ms;
  const observed = approval?.id === challengeId ? approval?.notice : undefined;
  useEffect(() => {
    if (!challengeId) return;
    return watchApproval(expiresAt, signal => onObserve(challengeId, signal),
      next => setApproval({id: challengeId, notice: next}));
  }, [challengeId, expiresAt, onObserve]);


  useEffect(() => {
    if (challenge) approvalHeading.current?.focus();
    else if (focusOnReturn.current) {
      focusOnReturn.current = false;
      identityInput.current?.focus();
    }
  }, [challenge]);

  return <Surface className="urbit-sign-in" aria-labelledby="urbit-sign-in-title">
    <span className="urbit-sign-in-mark" aria-hidden="true">~</span>
    <h1 id="urbit-sign-in-title" tabIndex={-1}>Sign in with Urbit</h1>
    {challenge ? <section className="approval urbit-approval" aria-labelledby="urbit-approval-title">
      <h2 id="urbit-approval-title" ref={approvalHeading} tabIndex={-1}>{observed === 'approved' ? 'Sign-in approved' : observed === 'ended' ? 'Sign-in request ended' : 'Approve on your identity ship'}</h2>
      {observed !== 'approved' && observed !== 'ended' && <p>In a new tab, open your identity ship’s web address with <code>/stead-identity/</code> at the end. Match the code and Home address before approving.</p>}
      <dl className="urbit-approval-summary">
        <div><dt>Comparison code</dt><dd className="comparison">{challenge.comparison_code}</dd></div>
        <div><dt>Home</dt>{' '}<dd>{origin}</dd></div>
        <div><dt>Urbit ID</dt><dd>{`~${ship.trim().replace(/^~/u, '').toLowerCase()}`}</dd></div>
      </dl>
      <p role="status">{observed === 'approved' ? 'Your approval is ready to use on this Home.'
        : observed === 'ended' ? 'This sign-in request has ended. Request a new comparison code.'
        : observed === 'unavailable' ? 'Stead could not check automatically. Choose Check approval to try again.'
        : 'After approving, return to this tab and check approval.'}</p>
      <div className="urbit-sign-in-actions">
        {observed === 'ended'
          ? <Button variant="primary" pending={busy} pendingLabel="Requesting approval" onClick={onRequest}>Request a new code</Button>
          : <Button variant="primary" pending={busy} pendingLabel="Checking approval" onClick={onCheck}>{observed === 'approved' ? 'Open Stead' : 'Check approval'}</Button>}
        <Button variant="quiet" disabled={busy} onClick={() => { focusOnReturn.current = true; onBack(); }}>Use a different ID</Button>
      </div>
    </section> : <>
      <p>Your Urbit approves access to this workspace.</p>
      <form onSubmit={event => { event.preventDefault(); onRequest(); }}>
        <TextField ref={identityInput} label="Urbit ID" description="The tilde (~) is optional."
          placeholder="~sampel-palnet" value={ship} onChange={event => onShipChange(event.target.value)} disabled={busy}
          autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={64}/>
        <Button type="submit" variant="primary" pending={busy} pendingLabel="Requesting approval">Continue</Button>
      </form>
    </>}
    <div className="urbit-sign-in-notice" role="status" aria-live="polite">{notice}</div>
  </Surface>;
}
