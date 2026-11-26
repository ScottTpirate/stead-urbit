import type {Token} from 'markdown-it';

export type DocumentHeading = {tokenIndex: number; level: number; label: string};
export type DocumentOutline = {headings: readonly DocumentHeading[]; limited: boolean};
const MAX_HEADINGS = 64, MAX_LABEL_CHARACTERS = 160;

// Only the already bounded Markdown token stream enters this helper. Labels
// contain plain text; source strings never become DOM IDs or HTML attributes.
function inlineLabel(tokens: readonly Token[]): string {
  let text = '';
  for (const token of tokens) {
    if (token.type === 'softbreak' || token.type === 'hardbreak') text += ' ';
    else if (token.children) text += inlineLabel(token.children);
    else if (token.nesting === 0) text += token.content;
  }
  return text;
}

export function documentOutline(tokens: readonly Token[]): DocumentOutline {
  const headings: DocumentHeading[] = [];
  for (let index = 0; index < tokens.length; index++) {
    const token = tokens[index]!, inline = tokens[index + 1];
    if (token.type !== 'heading_open' || !/^h[1-6]$/u.test(token.tag) || inline?.type !== 'inline') continue;
    const text = inlineLabel(inline.children ?? []).replace(/\s+/gu, ' ').trim();
    if (!text) continue;
    if (headings.length === MAX_HEADINGS) return {headings, limited: true};
    const characters = Array.from(text);
    const label = characters.length > MAX_LABEL_CHARACTERS
      ? characters.slice(0, MAX_LABEL_CHARACTERS).join('') + '…' : text;
    headings.push({tokenIndex: index, level: Number(token.tag.slice(1)), label});
  }
  return {headings, limited: false};
}
