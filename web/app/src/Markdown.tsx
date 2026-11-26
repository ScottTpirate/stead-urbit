import {createElement, Fragment, memo, useDeferredValue, useId, useMemo, useRef, type ReactNode} from 'react';
import MarkdownIt, {type Token} from 'markdown-it';
import {ResourceLink, safeResourceHref} from './ResourceLink';
import {Button} from './primitives';
import {documentOutline, type DocumentHeading} from './documentOutline';
import {MarkdownAttachment} from './MarkdownAttachment';
import './markdown.css';
import './document-outline.css';

// Maintained CommonMark + tables/strikethrough parser, with an explicit React
// vocabulary. No raw HTML, arbitrary attribute forwarding or HTML sink.
const parser = new MarkdownIt({html: false, linkify: false, typographer: false, maxNesting: 20});
const tags = new Set(['p','h1','h2','h3','h4','h5','h6','blockquote','ul','ol','li',
  'em','strong','s','table','thead','tbody','tr','th','td']);
const header = /^---\nid: [0-9a-f-]{36}\ntype: page\nstate: (draft|published)\n---\n/u;
function countTokens(tokens: Token[]): number {
  let count = 0;
  for (const token of tokens) {
    count += 1 + (token.children ? countTokens(token.children) : 0);
    if (count > 2048) return count;
  }
  return count;
}
export type MarkdownOrigin = 'document' | 'repository';
function markdownLink(href: string, children: ReactNode, origin: MarkdownOrigin, key?: number, title?: string) {
  const safe = safeResourceHref(href);
  if (origin === 'repository' && (!safe || !/^https?:/u.test(safe))) {
    return <span key={key} className="markdown-unavailable-link" title="Open repository links in a clone.">{children}
      <span className="stead-visually-hidden"> (repository link unavailable)</span></span>;
  }
  return <ResourceLink key={key} href={href} title={title}>{children}</ResourceLink>;
}
function renderTokens(tokens: Token[], origin: MarkdownOrigin, withinList = false, headingIds?: ReadonlyMap<number, string>): ReactNode[] {
  let index = 0;
  function sequence(inList: boolean): ReactNode[] {
    const output: ReactNode[] = [];
    while (index < tokens.length) {
      const key = index;
      const token = tokens[index++]!;
      if (token.nesting === -1) break;
      if (token.nesting === 1) {
        const childStart = index;
        const children = sequence(inList || token.tag === 'li');
        if (token.type === 'link_open') {
          const href = String(token.attrGet('href') ?? '');
          const title = String(token.attrGet('title') ?? '') || undefined;
          // A linked image has two destinations. Keep the attachment's policy
          // visible and expose the enclosing destination separately; no nested
          // anchors or misleading clickable unavailable-image label.
          output.push(tokens.slice(childStart, index).some(child => child.type === 'image')
            ? <span key={key} className="markdown-linked-attachment">{children} {markdownLink(href, 'Related link', origin, undefined, title)}</span>
            : markdownLink(href, children, origin, key, title));
        } else if (token.hidden || !tags.has(token.tag)) {
          output.push(<Fragment key={key}>{children}</Fragment>);
        } else {
          const props: {key: number; start?: number; scope?: string; id?: string; tabIndex?: number; className?: string} = {key};
          if (token.tag === 'ol') {
            const start = Number(token.attrGet('start') ?? 1);
            if (Number.isSafeInteger(start) && start >= 0 && start <= 999999999) props.start = start;
          }
          if (token.tag === 'th') props.scope = 'col';
          const headingId = token.type === 'heading_open' ? headingIds?.get(key) : undefined;
          if (headingId) {props.id = headingId; props.tabIndex = -1; props.className = 'document-outline-heading';}
          const node = createElement(token.tag, props, children);
          output.push(token.tag === 'table' ? <div key={key} className="markdown-table" tabIndex={0} role="region" aria-label="Document table">{node}</div> : node);
        }
      } else if (token.type === 'inline') {
        let children = token.children ?? [];
        const first = children[0];
        const task = inList && first?.type === 'text' ? /^\[([ xX])\] /u.exec(first.content) : null;
        if (task && first) {
          children = [{...first, content: first.content.slice(task[0].length)} as Token, ...children.slice(1)];
          output.push(<input key={`check-${key}`} type="checkbox" disabled checked={task[1] !== ' '}
            aria-label={task[1] === ' ' ? 'Incomplete task' : 'Completed task'}/>);
        }
        output.push(<Fragment key={key}>{renderTokens(children, origin)}</Fragment>);
      } else if (token.type === 'text') output.push(token.content);
      else if (token.type === 'softbreak') output.push('\n');
      else if (token.type === 'hardbreak') output.push(<br key={key}/>);
      else if (token.type === 'code_inline') output.push(<code key={key}>{token.content}</code>);
      else if (token.type === 'fence' || token.type === 'code_block') {
        output.push(<pre key={key} tabIndex={0}><code>{token.content}</code></pre>);
      } else if (token.type === 'hr') output.push(<hr key={key}/>);
      else if (token.type === 'image') {
        output.push(<MarkdownAttachment key={key} target={String(token.attrGet('src') ?? '')}
          alt={token.content} origin={origin}/>);
      } else output.push(token.content);
    }
    return output;
  }
  return sequence(withinList);
}
type Presentation = {content: ReactNode; headings: readonly (DocumentHeading & {id: string})[]; limited: boolean};
function markdownPresentation(text: string, origin: MarkdownOrigin, headingPrefix?: string): Presentation {
  const fallback = (content: ReactNode): Presentation => ({content, headings: [], limited: false});
  if (new TextEncoder().encode(text).length > 32768) return fallback(<p role="alert">This document exceeds the supported display size.</p>);
  const body = origin === 'repository' ? text : text.replace(header, '');
  let separators = 0;
  for (const character of body) {
    if ((character === '\n' || character === '`') && ++separators > 512) return fallback(<pre className="markdown-plain" tabIndex={0}>{body}</pre>);
  }
  const tokens = parser.parse(body, {});
  if (countTokens(tokens) > 2048) return fallback(<pre className="markdown-plain" tabIndex={0}>{body}</pre>);
  const outline = headingPrefix && origin === 'document' ? documentOutline(tokens) : undefined;
  const headings = outline && outline.headings.length >= 3 ? outline.headings.map((heading, index) => ({...heading, id: `${headingPrefix}-${index}`})) : [];
  const headingIds = new Map(headings.map(heading => [heading.tokenIndex, heading.id]));
  return {content: <>{renderTokens(tokens, origin, false, headingIds)}</>, headings, limited: !!outline?.limited};
}
export function markdownContent(text: string, origin: MarkdownOrigin = 'document'): ReactNode {
  return markdownPresentation(text, origin).content;
}
export const Markdown = memo(function Markdown({text, origin = 'document', showOutline = false}:
  {readonly text: string; readonly origin?: MarkdownOrigin; readonly showOutline?: boolean}) {
  const deferred = useDeferredValue(text);
  const instance = useId().replace(/[^a-zA-Z0-9_-]/gu, ''), article = useRef<HTMLElement>(null);
  const current = useRef({text, origin, showOutline});
  if (current.current.text !== text || current.current.origin !== origin || current.current.showOutline !== showOutline) {
    current.current = {text, origin, showOutline};
  }
  const owner = current.current;
  const preview = useMemo(() => markdownPresentation(deferred, origin, showOutline ? `stead-outline-${instance}` : undefined), [deferred, origin, showOutline, instance]);
  const ready = text === deferred && showOutline && preview.headings.length >= 3;
  function openHeading(id: string) {
    if (!ready || current.current !== owner || !preview.headings.some(heading => heading.id === id)) return;
    const target = article.current?.querySelector<HTMLElement>(`[id="${id}"]`);
    if (!target || !article.current?.contains(target)) return;
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'start', behavior: 'auto'});
  }
  return <>
    {ready && <nav className="document-outline" aria-label="On this page"><details>
      <summary>On this page</summary>
      <ol>{preview.headings.map(heading => <li key={heading.id} data-level={heading.level}>
        <Button variant="quiet" onClick={() => openHeading(heading.id)}>{heading.label}</Button>
      </li>)}</ol>
      {preview.limited && <p>Showing the first 64 headings.</p>}
    </details></nav>}
    <article ref={article} className="markdown" aria-label={origin === 'repository' ? 'Repository file content' : 'Document content'} aria-busy={text !== deferred}>{preview.content}</article>
  </>;
});
