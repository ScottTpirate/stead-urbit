import {lazy, Suspense, useEffect, useRef, useState, useSyncExternalStore} from 'react';
import {AppearanceControl} from './Appearance';
import type {HandbookPage} from './productRoutes';
import dailyWork from './handbook/daily-work.md' with {type:'text'};
import settings from './handbook/settings.md' with {type:'text'};
import agents from './handbook/agents.md' with {type:'text'};
import questions from './handbook/questions.md' with {type:'text'};
import readme from './handbook/README.md' with {type:'text'};
import './handbook.css';

const Markdown = lazy(() => import('./Markdown').then(module=>({default:module.Markdown})));
const articles = {
  'daily-work': {title: 'Work and Docs', description: 'Find a task, edit a page and confirm your change.', text: dailyWork},
  settings: {title: 'Settings and access', description: 'Appearance, sign-in and what appears in your workspace.', text: settings},
  agents: {title: 'Give an agent a task', description: 'Write a brief, choose an identity and review a result.', text: agents},
  questions: {title: 'Common questions', description: 'Find Code, check a save or bring the Handbook back.', text: questions},
};
const tabs = [['overview','Overview'],['work','Work'],['docs','Docs'],['code','Code']] as const;
const preferenceChanged = 'stead:handbook-visibility';
const temporaryVisibility = new Map<string, boolean>();

function visibilityKey(principal: string) { return 'stead.handbook.hidden.' + principal; }
function storedVisibility(key: string) {
  if (temporaryVisibility.has(key)) return temporaryVisibility.get(key)!;
  try { return localStorage.getItem(key) !== 'yes'; } catch { return true; }
}
function watchPreferences(listener: () => void) {
  window.addEventListener('storage', listener);
  window.addEventListener(preferenceChanged, listener);
  return () => { window.removeEventListener('storage', listener); window.removeEventListener(preferenceChanged, listener); };
}
export function useHandbookVisibility(principal: string) {
  const key = visibilityKey(principal);
  const visible = useSyncExternalStore(watchPreferences, () => storedVisibility(key));
  function setVisible(value: boolean) {
    try {
      if (value) localStorage.removeItem(key); else localStorage.setItem(key, 'yes');
      temporaryVisibility.delete(key);
    } catch { temporaryVisibility.set(key, value); }
    window.dispatchEvent(new Event(preferenceChanged));
  }
  return {visible, setVisible};
}

export function WorkspaceSettings({visible, onVisible}: {visible:boolean; onVisible:(value:boolean)=>void}) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { title.current?.focus(); }, []);
  return <section className="handbook settings-page">
    <div className="project-heading"><h1 tabIndex={-1} ref={title}>Settings</h1></div>
    <section className="handbook-pane"><h2>Workspace preferences</h2>
      <AppearanceControl/>
      <label className="handbook-setting"><input type="checkbox" checked={visible} onChange={event=>onVisible(event.target.checked)}/>Show Stead Handbook in Projects</label>
      <p className="muted">Handbook visibility is saved for your account in this browser.</p>
      <a href="#handbook">Open Stead Handbook</a>
    </section>
  </section>;
}

export function Handbook({page}: {page: HandbookPage}) {
  const title = useRef<HTMLHeadingElement>(null);
  const [raw, setRaw] = useState(false);
  useEffect(() => { title.current?.focus(); setRaw(false); }, [page]);
  const article = page in articles ? articles[page as keyof typeof articles] : null;
  const active = article ? 'docs' : page;
  return <section className="handbook">
    <div className={'project-heading'+(page==='overview' ? ' project-cover' : '')}>
      <div><p className="eyebrow">Projects <span aria-hidden="true">/</span> Guide</p><h1 ref={title} tabIndex={-1}>Stead Handbook</h1></div>
    </div>
    <nav className="tabs handbook-tabs" aria-label="Handbook views">{tabs.map(([key,label])=>
      <a key={key} href={key==='overview'?'#handbook':'#handbook/'+key} aria-current={active===key?'page':undefined}>{label}</a>)}</nav>
    {page==='overview' && <div className="handbook-pane"><h2>Start here</h2><p>Take a task from assignment to a saved result. These examples are safe to explore.</p>
      <div className="handbook-index">
        <a href="#handbook/work"><strong>Explore a Work item</strong><span>See a brief, its completion criteria and the review.</span></a>
        <a href="#handbook/docs"><strong>Browse the guides</strong><span>Work, Docs, settings and working with agents.</span></a>
        <a href="#handbook/code"><strong>Read the Git README</strong><span>Browse files, clone a project and check its commit.</span></a>
      </div></div>}
    {page==='work' && <section className="handbook-pane"><h2>Example Work item</h2>
      <details className="handbook-example"><summary>Update the visitor guide</summary>
        <p>Move the opening meeting from Monday to Wednesday. Keep the time and meeting point.</p>
        <h3>Completion criteria</h3><ul><li>Only the weekday changes.</li><li>A reviewer checks the proposed line.</li><li>The saved guide shows Wednesday when reopened.</li></ul>
        <h3>Review the handoff</h3><p>The worker proposes the edit. The reviewer compares the exact text before accepting it. The owner can then mark the Work done.</p>
        <a href="#handbook/agents">See how to brief an agent</a>
      </details></section>}
    {page==='docs' && <section className="handbook-pane"><h2>Guides</h2><div className="handbook-index">
      {Object.entries(articles).map(([key,doc])=><a key={key} href={'#handbook/'+key}><strong>{doc.title}</strong><span>{doc.description}</span></a>)}
    </div></section>}
    {article && <div className="handbook-pane"><a href="#handbook/docs">All guides</a><Suspense fallback={<p>Loading guide…</p>}><Markdown key={page} text={article.text} showOutline/></Suspense></div>}
    {page==='code' && <section className="handbook-pane"><h2>README.md</h2>
      <div className="handbook-file-modes" role="group" aria-label="README display">
        <button type="button" aria-pressed={!raw} onClick={()=>setRaw(false)}>Read</button>
        <button type="button" aria-pressed={raw} onClick={()=>setRaw(true)}>Raw</button>
      </div>{raw?<pre tabIndex={0} aria-label="README source">{readme}</pre>:<Suspense fallback={<p>Loading README…</p>}><Markdown text={readme} origin="repository"/></Suspense>}</section>}
  </section>;
}
