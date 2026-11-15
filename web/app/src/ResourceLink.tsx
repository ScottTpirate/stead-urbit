import type {ReactNode} from 'react';

export function safeResourceHref(value: string): string | null {
  if (!value || value.length > 2048 || /[\u0000-\u0020\u007f\\]/u.test(value)) return null;
  if (value.startsWith('#') && !value.startsWith('#/')) return value;
  if (value.startsWith('/') && !value.startsWith('//')) return value;
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null;
    return url.href;
  } catch { return null; }
}

// Explicit navigation boundary: no arbitrary DOM properties and no attachment
// fetch during rendering. External navigation requires a deliberate click.
export function ResourceLink({href, children, title}: {href: string; children: ReactNode; title?: string}) {
  const safe = safeResourceHref(href);
  if (!safe) return <span>{children}</span>;
  const external = safe.startsWith('http:') || safe.startsWith('https:');
  return <a href={safe} title={title} target={external ? '_blank' : undefined}
    rel="noopener noreferrer" referrerPolicy="no-referrer">{children}</a>;
}
