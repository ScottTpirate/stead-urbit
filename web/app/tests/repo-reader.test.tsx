import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {markdownContent} from '../src/Markdown';
import {RepositoryFile, repositoryMarkdown} from '../src/RepoBrowser';
import type {GitBrowseResult} from '../src/api';
const name=(text:string)=>Buffer.from(text,'utf8').toString('hex');
const render=(text:string, filename='README.md')=>renderToStaticMarkup(<RepositoryFile path={[name(filename)]} data={{status:'file',commit:'a'.repeat(40),preview:'text',bytes:Buffer.byteLength(text),text}}/>);
const escaped=(text:string)=>text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
test('Markdown eligibility uses only supported textual names without controls or invalid UTF8',()=>{
 for(const filename of ['README.md','notes.MARKDOWN','équipe.Md'])assert.equal(repositoryMarkdown([name(filename)]),true);
 for(const filename of ['README','file.txt','file.mdx','evil.md\u0000','\u202eread.md'])assert.equal(repositoryMarkdown([name(filename)]),false);
 assert.equal(repositoryMarkdown([]),false);assert.equal(repositoryMarkdown(['ff2e6d64']),false);
});
test('Repository origin preserves actual Doc-like header while default Docs retain their established rendering',()=>{
 const header='---\nid: 00000000-0000-0000-0000-000000000123\ntype: page\nstate: draft\n---\n';
 const body='# Guide\n\nExact content.';
 const legacy=renderToStaticMarkup(<>{markdownContent(header+body)}</>),repository=renderToStaticMarkup(<>{markdownContent(header+body,'repository')}</>);
 assert.equal(legacy,renderToStaticMarkup(<>{markdownContent(body)}</>));assert.doesNotMatch(legacy,/type: page/u);
 assert.match(repository,/type: page/u);assert.match(repository,/00000000-0000-0000-0000-000000000123/u);assert.match(repository,/<h1>Guide<\/h1>/u);
});
test('Repository links cannot navigate app paths or fetch images and external links keep the existing safe boundary',()=>{
 const text='[local](guide.md) [section](#part) [root](/stead/) [web](https://example.com/guide) [bad](javascript:alert(1))\n\n![local image](./x.png) ![external](https://example.com/x.png)\n\n<script>alert(1)</script>';
 const html=renderToStaticMarkup(<>{markdownContent(text,'repository')}</>);
 assert.doesNotMatch(html,/<(script|img|iframe)\b/u);assert.doesNotMatch(html,/href="(?:#|\/|guide|javascript)/u);
 assert.match(html,/href="https:\/\/example.com\/guide"/u);assert.match(html,/rel="noopener noreferrer"/u);assert.match(html,/repository link unavailable/u);assert.match(html,/&lt;script&gt;/u);
 const doc=renderToStaticMarkup(<>{markdownContent('[section](#part) [root](/stead/)')}</>);assert.match(doc,/href="#part"/u);assert.match(doc,/href="\/stead\/"/u);
});
test('Read defaults for Markdown without editing or extra resource requests and preserves exact commit evidence',()=>{
 const html=render('# Guide\n\nReadable **body**.');
 assert.match(html,/role="tab"[^>]*aria-selected="true"[^>]*data-file-mode="read"/u);
 assert.match(html,/<h1>Guide<\/h1>/u);assert.match(html,/<strong>body<\/strong>/u);assert.match(html,/Read-only/u);
 assert.match(html,new RegExp('a'.repeat(40),'u'));assert.doesNotMatch(html,/<(?:input|textarea|form)\b|>Save<|>Edit</u);
});
test('Raw-only textual formats preserve exact Unicode CRLF and whitespace in one file origin',()=>{
 const text='line 1  \r\n<&> "quoted"\r\n雪🪴\t\r\n';const html=render(text,'notes.txt');
 assert.match(html,/aria-label="File contents"/u);assert.ok(html.includes('>'+escaped(text)+'</pre>'));
 assert.doesNotMatch(html,/role="tab"|Repository file content/u);
});
test('Empty binary and oversized files state their actual limits without a fabricated preview',()=>{
 assert.match(render(''),/This file is empty/u);
 for(const preview of ['binary','too-large'] as const){const data:Extract<GitBrowseResult,{status:'file'}>={status:'file',commit:'b'.repeat(40),preview,bytes:40000};
 const html=renderToStaticMarkup(<RepositoryFile data={data} path={[name('README.md')]}/>);
 assert.match(html,preview==='binary'?/Binary file/u:/too large to preview/u);assert.doesNotMatch(html,/role="tab"|Copy contents|Repository file content/u);}
});
test('Dense repository Markdown falls back to exact full source including Doc-like metadata',()=>{
 const text='---\nid: 00000000-0000-0000-0000-000000000123\ntype: page\nstate: draft\n---\n'+'\n'.repeat(520)+'tail';
 const html=renderToStaticMarkup(<>{markdownContent(text,'repository')}</>);assert.ok(html.includes('>'+escaped(text)+'</pre>'));assert.match(html,/markdown-plain/u);
});
