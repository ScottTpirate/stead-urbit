import { Fragment, memo, useDeferredValue, useMemo, type ReactNode } from 'react';

// Deliberately small Markdown display vocabulary. Unrecognized syntax stays
// text; there is no HTML parser, image fetch, URL evaluation or raw DOM sink.
function inline(text: string): ReactNode[] {
  return text.split(/(`[^`\n]{1,512}`)/u).map((part, index) =>
    part.startsWith('`') && part.endsWith('`')
      ? <code key={index}>{part.slice(1, -1)}</code>
      : <Fragment key={index}>{part}</Fragment>,
  );
}

function content(text: string) {
  if (new TextEncoder().encode(text).length > 32768) {
    return <p role="alert">This document exceeds the supported display size.</p>;
  }
  // The editor stores the canonical front matter; the reader displays the
  // body only when the complete known four-line header is present.
  const header = /^---\nid: [0-9a-f-]{36}\ntype: page\nstate: (draft|published)\n---\n/u;
  const body = header.test(text) ? text.replace(header, '') : text;
  // Bound element creation independently of the byte cap. Dense line/code
  // structure uses one inert text node, preserving the entire document body.
  let separators = 0;
  for (const character of body) {
    if ((character === '\n' || character === '`') && ++separators > 512) {
      return <pre className="markdown-plain" tabIndex={0}>{body}</pre>;
    }
  }
  return <>{body.split('\n').map((line, index) => {
      if (line.startsWith('### ')) return <h4 key={index}>{inline(line.slice(4))}</h4>;
      if (line.startsWith('## ')) return <h3 key={index}>{inline(line.slice(3))}</h3>;
      if (line.startsWith('# ')) return <h2 key={index}>{inline(line.slice(2))}</h2>;
      if (line.startsWith('> ')) return <blockquote key={index}>{inline(line.slice(2))}</blockquote>;
      return line ? <p key={index}>{inline(line)}</p> : <br key={index}/>;
    })}</>;
}

export const Markdown = memo(function Markdown({ text }: { readonly text: string }) {
  const deferred = useDeferredValue(text);
  const preview = useMemo(() => content(deferred), [deferred]);
  return <article className="markdown" aria-label="Document content" aria-busy={text !== deferred}>{preview}</article>;
});
