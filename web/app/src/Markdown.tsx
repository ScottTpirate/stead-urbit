import { Fragment, type ReactNode } from 'react';

// Deliberately small Markdown display vocabulary. Unrecognized syntax stays
// text; there is no HTML parser, image fetch, URL evaluation or raw DOM sink.
function inline(text: string): ReactNode[] {
  return text.split(/(`[^`\n]{1,512}`)/u).map((part, index) =>
    part.startsWith('`') && part.endsWith('`')
      ? <code key={index}>{part.slice(1, -1)}</code>
      : <Fragment key={index}>{part}</Fragment>,
  );
}

export function Markdown({ text }: { readonly text: string }) {
  if (new TextEncoder().encode(text).length > 32768) {
    return <p role="alert">This document exceeds the supported display size.</p>;
  }
  const lines = text.split('\n');
  // The editor stores the canonical front matter; the reader displays the
  // body only when the complete known four-line header is present.
  const header = /^---\nid: [0-9a-f-]{36}\ntype: page\nstate: (draft|published)\n---\n/u;
  const body = header.test(text) ? text.replace(header, '').split('\n') : lines;
  return <article className="markdown" aria-label="Document content">
    {body.map((line, index) => {
      if (line.startsWith('### ')) return <h4 key={index}>{inline(line.slice(4))}</h4>;
      if (line.startsWith('## ')) return <h3 key={index}>{inline(line.slice(3))}</h3>;
      if (line.startsWith('# ')) return <h2 key={index}>{inline(line.slice(2))}</h2>;
      if (line.startsWith('> ')) return <blockquote key={index}>{inline(line.slice(2))}</blockquote>;
      return line ? <p key={index}>{inline(line)}</p> : <br key={index}/>;
    })}
  </article>;
}
