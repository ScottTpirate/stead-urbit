// Audited local Lucide subset. Exact upstream shapes and notices are retained
// in vendor/lucide; see ICONS_NOTICE.md. No URLs, markup or props are forwarded.
export type IconName = 'chevron-down' | 'check' | 'circle' | 'circle-exclamation-point'
  | 'ellipsis' | 'plus' | 'x' | 'search';

export function Icon({name}: {readonly name: IconName}) {
  let shape;
  switch (name) {
    case 'chevron-down': shape = <path d="m6 9 6 6 6-6"/>; break;
    case 'check': shape = <path d="M20 6 9 17l-5-5"/>; break;
    case 'circle': shape = <circle cx="12" cy="12" r="10"/>; break;
    case 'circle-exclamation-point': shape = <><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></>; break;
    case 'ellipsis': shape = <><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></>; break;
    case 'plus': shape = <><path d="M5 12h14"/><path d="M12 5v14"/></>; break;
    case 'x': shape = <><path d="M18 6 6 18"/><path d="m6 6 12 12"/></>; break;
    case 'search': shape = <><path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/></>; break;
    default: return null;
  }
  return <svg className="stead-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" focusable="false">{shape}</svg>;
}
