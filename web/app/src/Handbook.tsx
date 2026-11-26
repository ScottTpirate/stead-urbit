import {useEffect, useRef, useSyncExternalStore} from 'react';
import {AppearanceControl} from './Appearance';
import './handbook.css';

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
  return <section className="settings-page">
    <div className="project-heading"><h1 tabIndex={-1} ref={title}>Settings</h1></div>
    <section className="settings-preferences"><h2>Workspace preferences</h2>
      <AppearanceControl/>
      <label className="handbook-setting"><input type="checkbox" checked={visible} onChange={event=>onVisible(event.target.checked)}/>Show Stead Handbook in Projects</label>
      <p className="muted">Handbook visibility is saved for your account in this browser.</p>
      <a href="#handbook">Open Stead Handbook</a>
    </section>
  </section>;
}
