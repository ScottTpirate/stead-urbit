import {createElement, Fragment, memo, useDeferredValue, useMemo, type ReactNode} from 'react';
import MarkdownIt, {type Token} from 'markdown-it';
import {ResourceLink} from './ResourceLink';
import './markdown.css';

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
function renderTokens(tokens: Token[], withinList = false): ReactNode[] {
  let index = 0;
  function sequence(inList: boolean): ReactNode[] {
    const output: ReactNode[] = [];
    while (index < tokens.length) {
      const key = index;
      const token = tokens[index++]!;
      if (token.nesting === -1) break;
      if (token.nesting === 1) {
        const children = sequence(inList || token.tag === 'li');
        if (token.type === 'link_open') {
          output.push(<ResourceLink key={key} href={String(token.attrGet('href') ?? '')}
            title={String(token.attrGet('title') ?? '') || undefined}>{children}</ResourceLink>);
        } else if (token.hidden || !tags.has(token.tag)) {
          output.push(<Fragment key={key}>{children}</Fragment>);
        } else {
          const props: {key: number; start?: number; scope?: string} = {key};
          if (token.tag === 'ol') {
            const start = Number(token.attrGet('start') ?? 1);
            if (Number.isSafeInteger(start) && start >= 0 && start <= 999999999) props.start = start;
          }
          if (token.tag === 'th') props.scope = 'col';
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
        output.push(<Fragment key={key}>{renderTokens(children)}</Fragment>);
      } else if (token.type === 'text') output.push(token.content);
      else if (token.type === 'softbreak') output.push('\n');
      else if (token.type === 'hardbreak') output.push(<br key={key}/>);
      else if (token.type === 'code_inline') output.push(<code key={key}>{token.content}</code>);
      else if (token.type === 'fence' || token.type === 'code_block') {
        output.push(<pre key={key} tabIndex={0}><code>{token.content}</code></pre>);
      } else if (token.type === 'hr') output.push(<hr key={key}/>);
      else if (token.type === 'image') {
        output.push(<span key={key} className="markdown-attachment"><ResourceLink href={String(token.attrGet('src') ?? '')}>
          Image: {token.content || 'attachment'} (open)
        </ResourceLink></span>);
      } else output.push(token.content);
    }
    return output;
  }
  return sequence(withinList);
}
export function markdownContent(text: string): ReactNode {
  if (new TextEncoder().encode(text).length > 32768) return <p role="alert">This document exceeds the supported display size.</p>;
  const body = text.replace(header, '');
  let separators = 0;
  for (const character of body) {
    if ((character === '\n' || character === '`') && ++separators > 512) return <pre className="markdown-plain" tabIndex={0}>{body}</pre>;
  }
  const tokens = parser.parse(body, {});
  if (countTokens(tokens) > 2048) return <pre className="markdown-plain" tabIndex={0}>{body}</pre>;
  return <>{renderTokens(tokens)}</>;
}
export const Markdown = memo(function Markdown({text}: {readonly text: string}) {
  const deferred = useDeferredValue(text);
  const preview = useMemo(() => markdownContent(deferred), [deferred]);
  return <article className="markdown" aria-label="Document content" aria-busy={text !== deferred}>{preview}</article>;
});
