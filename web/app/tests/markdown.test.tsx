import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {markdownContent} from '../src/Markdown';
import {safeResourceHref} from '../src/ResourceLink';
test('Markdown renders lists emphasis fences tables links and task markers', () => {
  const text='# Guide\n\n**Strong** and *emphasis* with ~~old~~ text.\n\n- [x] Complete\n- [ ] Next\n\n```js\nconst x = "<safe>";\n```\n\n| Goal | State |\n|---|---|\n| Launch | Ready |\n\n[Reference](https://example.com/docs)';
  const html=renderToStaticMarkup(<>{markdownContent(text)}</>);
  for (const expected of ['<h1>Guide</h1>','<strong>Strong</strong>','<em>emphasis</em>','<s>old</s>','<ul>','<table>','<th scope="col">Goal</th>','&lt;safe&gt;','rel="noopener noreferrer"','type="checkbox"']) assert.ok(html.includes(expected),expected);
  assert.equal((html.match(/type="checkbox"/gu) ?? []).length,2);
});
test('HTML and image URLs never create executable or automatically loading elements', () => {
  const html=renderToStaticMarkup(<>{markdownContent('<script>alert(1)</script>\n\n![Private](https://tracker.example/pixel)\n\n[Bad](javascript:alert(1))\n\n<iframe src="https://tracker.example"/>')}</>);
  assert.doesNotMatch(html,/<(script|img|iframe|object|embed)\b/u);
  assert.doesNotMatch(html,/href="javascript:/u);
  assert.match(html,/&lt;script&gt;/u);assert.match(html,/Image: Private/u);
});
test('resource navigation refuses scripts credentials controls protocol-relative and backslash URLs', () => {
  for (const href of ['javascript:alert(1)','data:text/html,hi','file:///etc/passwd','//tracker.example/x','https://user:secret@example.com','https:\\evil.test','https://a.test/\nsecret']) assert.equal(safeResourceHref(href),null,href);
  assert.equal(safeResourceHref('https://example.com/docs'),'https://example.com/docs');
  assert.equal(safeResourceHref('/stead/#work/abc'),'/stead/#work/abc');
});
test('dense and oversized documents stay bounded without truncating accepted source', () => {
  const dense='first\n'+'\n'.repeat(1000)+'last';const html=renderToStaticMarkup(<>{markdownContent(dense)}</>);
  assert.ok(html.includes(dense));assert.match(html,/<pre/u);
  assert.match(renderToStaticMarkup(<>{markdownContent('a'.repeat(32769))}</>),/exceeds the supported display size/u);
});
