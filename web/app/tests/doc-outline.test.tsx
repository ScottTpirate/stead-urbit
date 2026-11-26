import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import MarkdownIt from 'markdown-it';
import {Markdown, markdownContent} from '../src/Markdown';
import {documentOutline} from '../src/documentOutline';

const parser = new MarkdownIt({html:false,linkify:false,typographer:false,maxNesting:20});
const outline = (text:string)=>documentOutline(parser.parse(text,{}));
const rendered = (text:string)=>renderToStaticMarkup(<Markdown text={text} showOutline/>);
const ids = (html:string)=>[...html.matchAll(/\bid="(stead-outline-[^"]+)"/gu)].map(match=>match[1]);

test('Outline follows rendered ATX and setext headings with plain inline labels and excludes fenced code',()=>{
 const text='# **Overview** and `code`\n\nA guide\n=======\n\n> ## Linked [section](https://example.com)\n\n```markdown\n# Not a heading\n```\n';
 const result=outline(text);
 assert.deepEqual(result.headings.map(({level,label})=>({level,label})),[{level:1,label:'Overview and code'},{level:1,label:'A guide'},{level:2,label:'Linked section'}]);
 assert.equal(result.limited,false);
 const html=rendered(text);
 assert.match(html,/aria-label="On this page"/u);
 assert.equal(ids(html).length,3);
 assert.match(html,/<h1[^>]*><strong>Overview<\/strong> and <code>code<\/code><\/h1>/u);
 assert.match(html,/<pre[^>]*><code># Not a heading\n<\/code><\/pre>/u);
});

test('Short documents keep the established content and default rendering never introduces an outline',()=>{
 for(const text of ['', '# One', '# One\n\n## Two']){
  const html=rendered(text);
  assert.doesNotMatch(html,/document-outline|stead-outline-/u);
 }
 const text='# One\n\n## Two\n\n### Three';
 const html=renderToStaticMarkup(<Markdown text={text}/>);
 assert.doesNotMatch(html,/document-outline|stead-outline-/u);
 assert.match(html,/<h1>One<\/h1>/u);
 assert.equal(renderToStaticMarkup(<>{markdownContent(text)}</>),'<h1>One</h1><h2>Two</h2><h3>Three</h3>');
});

test('Repeated Unicode headings receive distinct instance-local targets without exposing source as IDs',()=>{
 const text='# 同じ 🪴\n\n## 同じ 🪴\n\n### 同じ 🪴';
 const html=renderToStaticMarkup(<><Markdown text={text} showOutline/><Markdown text={text} showOutline/></>);
 const targets=ids(html);
 assert.equal(targets.length,6);assert.equal(new Set(targets).size,6);
 assert.ok(targets.every(id=>/^stead-outline-[A-Za-z0-9_-]+-[0-9]+$/u.test(id)));
 assert.doesNotMatch(html,/href="#|id="[^"]*(?:同じ|🪴)/u);
 assert.equal((html.match(/tabindex="-1"/gu)??[]).length,6);
});

test('Large outlines stop at 64 entries with an explicit limit while retaining every rendered heading',()=>{
 const text=Array.from({length:70},(_,index)=>`## Section ${index+1}`).join('\n\n');
 const result=outline(text),html=rendered(text);
 assert.equal(result.headings.length,64);assert.equal(result.limited,true);
 assert.equal(result.headings[63]!.label,'Section 64');
 assert.equal((html.match(/<button\b/gu)??[]).length,64);
 assert.equal((html.match(/<h2\b/gu)??[]).length,70);
 assert.match(html,/Showing the first 64 headings\./u);
 assert.match(html,/<h2>Section 70<\/h2>/u);
 assert.equal(outline(Array.from({length:64},(_,index)=>`# ${index}`).join('\n')).limited,false);
});

test('Long outline labels have a code-point bound while the full heading text remains available',()=>{
 const title='🪴'.repeat(170),text=`# ${title}\n\n## Two\n\n### Three`;
 const result=outline(text),html=rendered(text);
 assert.equal(result.headings[0]!.label,'🪴'.repeat(160)+'…');
 assert.equal(Array.from(result.headings[0]!.label).length,161);
 assert.ok(html.includes('>'+title+'</h1>'));
 assert.match(html,/Two/u);assert.match(html,/Three/u);
});

test('Outline labels cannot introduce HTML links images or unsafe navigation',()=>{
 const text='# <script>alert(1)</script>\n\n## [Unsafe](javascript:alert(1))\n\n### ![Alt](https://example.com/image.png)';
 const html=rendered(text),nav=html.slice(html.indexOf('<nav'),html.indexOf('</nav>'));
 assert.doesNotMatch(html,/<(?:script|img|iframe)\b|href="javascript:/u);
 assert.match(html,/&lt;script&gt;/u);
 assert.doesNotMatch(nav,/<a\b|href=|src=/u);
 assert.equal((nav.match(/<button\b/gu)??[]).length,3);
 assert.equal(outline(text).headings[2]!.label,'Alt');
});

test('Existing size separator and token display bounds suppress outline rather than imply partial structure',()=>{
 const headings='# One\n\n## Two\n\n### Three\n\n';
 const oversized=rendered(headings+'x'.repeat(32768));
 assert.match(oversized,/exceeds the supported display size/u);assert.doesNotMatch(oversized,/document-outline/u);
 for(const text of [headings+'\n'.repeat(513),headings+'**bold** '.repeat(800)]){
  const html=rendered(text);
  assert.match(html,/markdown-plain/u);assert.doesNotMatch(html,/document-outline|stead-outline-/u);
  assert.ok(html.includes('# One\n\n## Two'));
 }
});

test('Doc metadata and repository origin keep their existing independent render rules',()=>{
 const header='---\nid: 00000000-0000-0000-0000-000000000123\ntype: page\nstate: draft\n---\n';
 const text='# One\n\n## Two\n\n### Three\n\n[Local](guide.md) [Section](#part)';
 const doc=rendered(header+text);
 assert.doesNotMatch(doc,/type: page|00000000-0000-0000-0000-000000000123/u);
 assert.equal(ids(doc).length,3);
 const repository=renderToStaticMarkup(<Markdown text={header+text} origin="repository" showOutline/>);
 assert.match(repository,/type: page/u);assert.doesNotMatch(repository,/document-outline|stead-outline-|href="(?:guide.md|#part)"/u);
 assert.match(repository,/repository link unavailable/u);
 assert.match(renderToStaticMarkup(<>{markdownContent(text)}</>),/href="#part"/u);
});
