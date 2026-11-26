import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {MarkdownAttachment} from '../src/MarkdownAttachment';
import {markdownContent} from '../src/Markdown';

test('attachment URLs use explicit governed links without loading images', () => {
  const html = renderToStaticMarkup(<>{markdownContent('![Diagram](https://example.com/diagram.svg)')}</>);
  assert.match(html, /data-attachment-state="link"/u);
  assert.match(html, /href="https:\/\/example.com\/diagram.svg"/u);
  assert.match(html, /target="_blank"/u);
  assert.match(html, /rel="noopener noreferrer"/u);
  assert.match(html, /referrerpolicy="no-referrer"/iu);
  assert.match(html, /Open image/u);
  assert.match(html, /opens in a new tab/u);
  assert.doesNotMatch(html, /<(?:img|iframe|object|embed|script)\b|\s(?:src|srcset|ping)=/u);
});

test('repository relative images require a clone without false open controls', () => {
  for (const target of ['diagram.png', './assets/diagram.svg', '../guide/diagram.png', '/assets/diagram.svg']) {
    const html = renderToStaticMarkup(<MarkdownAttachment target={target} alt="Architecture" origin="repository"/>);
    assert.match(html, /Image: Architecture/u);
    assert.match(html, /data-attachment-state="clone"/u);
    assert.match(html, /Clone the repository to view this image\./u);
    assert.doesNotMatch(html, /<a\b|Open image|\(open\)/u);
  }
  const rendered = renderToStaticMarkup(<>{markdownContent('![Architecture](./assets/diagram.svg)', 'repository')}</>);
  assert.match(rendered, /data-attachment-state="clone"/u);
});

test('unavailable attachment targets never claim to open or navigate', () => {
  for (const origin of ['document', 'repository'] as const) {
    for (const target of ['', '#section', '//tracker.example/a', 'javascript:alert(1)', 'data:image/png;base64,AAAA',
      'file:///etc/passwd', 'mailto:person@example.com', 'https://user:secret@example.com/a', 'https:\\evil.test/a',
      'https://example.com/\nimage', 'a'.repeat(2049)]) {
      const html = renderToStaticMarkup(<MarkdownAttachment target={target} alt="Saved description" origin={origin}/>);
      assert.match(html, /Image: Saved description/u);
      assert.match(html, /data-attachment-state="unavailable"/u);
      assert.match(html, /Image target unavailable\./u);
      assert.doesNotMatch(html, /<a\b|Open image|Clone the repository/u);
    }
  }
});

test('document root links and repository web links retain their distinct origins', () => {
  const document = renderToStaticMarkup(<MarkdownAttachment target="/assets/diagram.svg" alt="Local image" origin="document"/>);
  assert.match(document, /href="\/assets\/diagram.svg"/u);
  assert.doesNotMatch(document, /target="_blank"/u);
  const repository = renderToStaticMarkup(<MarkdownAttachment target="https://example.com/diagram.svg" alt="Web image" origin="repository"/>);
  assert.match(repository, /href="https:\/\/example.com\/diagram.svg"/u);
  const relativeDocument = renderToStaticMarkup(<MarkdownAttachment target="diagram.svg" alt="Missing origin" origin="document"/>);
  assert.match(relativeDocument, /Image target unavailable\./u);
});

test('attachment alt text stays literal and original Markdown stays unchanged', () => {
  const alt = '<img src=x onerror=alert(1)> 雪 🪴 ' + 'long-description-'.repeat(40);
  const html = renderToStaticMarkup(<MarkdownAttachment target="./image.png" alt={alt} origin="repository"/>);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt; 雪 🪴/u);
  assert.ok(html.includes('long-description-'.repeat(40)));
  assert.doesNotMatch(html, /<img\b/u);
  const markdown = '## Kept exactly\n\n![Alt text](../image.svg "Original title")  \n';
  const before = Buffer.from(markdown, 'utf8');
  renderToStaticMarkup(<>{markdownContent(markdown, 'repository')}</>);
  assert.deepEqual(Buffer.from(markdown, 'utf8'), before);
  assert.match(renderToStaticMarkup(<MarkdownAttachment target="" alt="" origin="document"/>), /Image: attachment/u);
});

test('linked images keep both governed destinations without nested anchors', () => {
  const html = renderToStaticMarkup(<>{markdownContent('[![Diagram](https://example.com/image.svg)](https://example.com/guide)', 'repository')}</>);
  assert.equal((html.match(/<a\b/gu) ?? []).length, 2);
  assert.match(html, /Related link/u);
  assert.doesNotMatch(html, /<a\b[^>]*>(?:(?!<\/a>).)*<a\b/su);
  const relative = renderToStaticMarkup(<>{markdownContent('[![Diagram](./image.svg)](https://example.com/guide)', 'repository')}</>);
  assert.match(relative, /Clone the repository/u);
  assert.equal((relative.match(/<a\b/gu) ?? []).length, 1);
  assert.doesNotMatch(relative, /Open image/u);
});
