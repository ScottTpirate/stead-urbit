import {useEffect, useId, useRef, useSyncExternalStore} from 'react';
import './handbook-tour.css';

const stops = [
  {view: 'overview', title: 'Overview', text: 'Read the project summary, then use the shortcuts to open Work or Docs.'},
  {view: 'work', title: 'Work', text: 'Open a task to see what needs doing and how to tell when it’s complete.'},
  {view: 'docs', title: 'Docs', text: 'Open a guide to read how this project works.'},
  {view: 'code', title: 'Code', text: 'Browse the repository and open its README.'},
] as const;

type View = typeof stops[number]['view'];
type Outcome = 'completed' | 'dismissed';
type Mode = Outcome | 'invitation' | 'active';

interface Props {
  principal: string;
  view: View;
  onNavigate: (view: View) => void;
}

const updateEvent = 'stead:handbook-tour';
const running = new Set<string>();
const fallback = new Map<string, Outcome>();

function preferenceKey(principal: string) {
  return 'stead.handbook.tour.' + principal;
}

function modeFor(principal: string): Mode {
  if (running.has(principal)) return 'active';
  const key = preferenceKey(principal);
  let stored: string | null = fallback.get(key) ?? null;
  if (!stored) {
    try { stored = window.localStorage.getItem(key); } catch { /* Storage may be disabled. */ }
  }
  return stored === 'completed' || stored === 'dismissed' ? stored : 'invitation';
}

function subscribe(listener: () => void) {
  window.addEventListener(updateEvent, listener);
  window.addEventListener('storage', listener);
  return () => {
    window.removeEventListener(updateEvent, listener);
    window.removeEventListener('storage', listener);
  };
}

function finish(principal: string, outcome: Outcome) {
  running.delete(principal);
  const key = preferenceKey(principal);
  try {
    window.localStorage.setItem(key, outcome);
    fallback.delete(key);
  } catch {
    fallback.set(key, outcome);
  }
  window.dispatchEvent(new Event(updateEvent));
}

/** Render inside the Handbook project. Each stop opens that project's normal tab. */
export function HandbookTour({principal, view, onNavigate}: Props) {
  const mode = useSyncExternalStore(subscribe, () => modeFor(principal));
  const index = stops.findIndex(stop => stop.view === view);
  const stop = stops[index] ?? stops[0];
  const previous = stops[index - 1];
  const next = stops[index + 1];
  const title = useId();
  const focusTarget = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<string | null>(null);

  useEffect(() => {
    if (returnFocus.current === principal) focusTarget.current?.focus();
    returnFocus.current = null;
  }, [mode, principal]);

  function start() {
    returnFocus.current = principal;
    running.add(principal);
    window.dispatchEvent(new Event(updateEvent));
    if (view !== 'overview') onNavigate('overview');
  }

  function close(outcome: Outcome) {
    returnFocus.current = principal;
    finish(principal, outcome);
  }

  if (!principal) return null;

  if (mode === 'completed' || mode === 'dismissed') {
    return <div className="handbook-tour-replay">
      <button ref={focusTarget} type="button" onClick={start}>Replay tour</button>
    </div>;
  }

  return <section className="handbook-tour" aria-labelledby={title}>
    {mode === 'invitation' ? <>
      <p id={title}>Take a short tour of this project?</p>
      <div className="handbook-tour-actions">
        <button type="button" className="handbook-tour-primary" onClick={start}>Show me around</button>
        <button type="button" onClick={() => close('dismissed')}>Skip</button>
      </div>
    </> : <>
      <div aria-live="polite" aria-atomic="true">
        <div className="handbook-tour-step">
          <span>Step {index + 1} of {stops.length}</span>
          <strong id={title}>{stop.title}</strong>
        </div>
        <p>{stop.text}</p>
      </div>
      <div className="handbook-tour-actions">
        <button type="button" disabled={!previous} onClick={() => previous && onNavigate(previous.view)}>Back</button>
        <button type="button" ref={focusTarget} className="handbook-tour-primary"
          onClick={() => next ? onNavigate(next.view) : close('completed')}>
          {next ? 'Next' : 'Done'}
        </button>
        <button type="button" onClick={() => close('dismissed')}>Skip</button>
      </div>
    </>}
  </section>;
}
