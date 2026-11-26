import {useEffect, useState} from 'react';

type Appearance = 'system' | 'light' | 'dark';
const preferenceKey = 'stead.appearance';

function preference(value: string | null): Appearance {
  return value === 'light' || value === 'dark' ? value : 'system';
}

function savedAppearance(): Appearance {
  try { return preference(localStorage.getItem(preferenceKey)); }
  catch { return 'system'; }
}

export function AppearanceControl() {
  const [mode, setMode] = useState<Appearance>(savedAppearance);
  useEffect(() => {
    function synchronize(event: StorageEvent) {
      if (event.key === preferenceKey || event.key === null) setMode(savedAppearance());
    }
    window.addEventListener('storage', synchronize);
    return () => window.removeEventListener('storage', synchronize);
  }, []);
  useEffect(() => {
    if (mode === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = mode;
  }, [mode]);

  return <label className="appearance-control">Appearance
    <select value={mode} onChange={event => {
      const next = preference(event.target.value);
      setMode(next);
      try { localStorage.setItem(preferenceKey, next); }
      catch { /* Restricted storage still permits a tab-local preference. */ }
    }}>
      <option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option>
    </select>
  </label>;
}
