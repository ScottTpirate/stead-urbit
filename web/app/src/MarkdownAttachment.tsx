import {ResourceLink, safeResourceHref} from './ResourceLink';
import type {MarkdownOrigin} from './Markdown';

type AttachmentTarget = {kind: 'link'; href: string} | {kind: 'clone'} | {kind: 'unavailable'};

function attachmentTarget(target: string, origin: MarkdownOrigin): AttachmentTarget {
  if (!target || target.length > 2048 || /[\u0000-\u0020\u007f\\]/u.test(target)
      || target.startsWith('//') || target.startsWith('#')) return {kind: 'unavailable'};
  const safe = safeResourceHref(target);
  if (safe && (/^https?:/u.test(safe) || origin === 'document' && safe.startsWith('/'))) {
    return {kind: 'link', href: safe};
  }
  if (origin === 'repository' && !/^[a-z][a-z0-9+.-]*:/iu.test(target)) return {kind: 'clone'};
  return {kind: 'unavailable'};
}

// Closed, inert presentation: no image element, resource-loading properties,
// automatic request or arbitrary DOM-property forwarding. Only explicit links
// use the existing navigation boundary. Markdown bytes remain the source.
export function MarkdownAttachment({target, alt, origin}: {
  readonly target: string; readonly alt: string; readonly origin: MarkdownOrigin;
}) {
  const state = attachmentTarget(target, origin);
  const label = `Image: ${alt || 'attachment'}`;
  return <span className="markdown-attachment" data-attachment-state={state.kind}>
    <span className="markdown-attachment-label">{label}</span>
    {state.kind === 'link' ? <ResourceLink href={state.href}>
      Open image<span className="stead-visually-hidden">: {alt || 'attachment'}</span>
      {/^https?:/u.test(state.href) && <span className="stead-visually-hidden"> (opens in a new tab)</span>}
    </ResourceLink> : <span className="markdown-attachment-status">
      {state.kind === 'clone' ? 'Clone the repository to view this image.' : 'Image target unavailable.'}
    </span>}
  </span>;
}
