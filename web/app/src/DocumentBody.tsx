import {lazy, Suspense, useEffect, useRef, useState} from 'react';
import {Button} from './primitives';
import {formatLines} from './documentFormatting';
const Markdown = lazy(() => import('./Markdown').then(module => ({default:module.Markdown})));
type Mode = 'read' | 'write' | 'preview' | 'source';
type Props = {text:string; header:string; editable:boolean; locked:boolean; isNew:boolean;
  fullSource:boolean; onFullSource:(full:boolean)=>void; onChange:(text:string)=>void};

export function DocumentBody({text,header,editable,locked,isNew,fullSource,onFullSource,onChange}:Props) {
  const [mode,setMode] = useState<Mode>(isNew && editable ? 'write' : 'read');
  const source = useRef<HTMLTextAreaElement>(null);
  const previousFull = useRef(fullSource);
  useEffect(() => {
    if (fullSource !== previousFull.current) {setMode(fullSource ? 'source' : 'write');previousFull.current=fullSource;}
  },[fullSource]);
  const editing=mode==='write'||mode==='source';
  const body=mode==='source'?text:text.slice(header.length);
  function select(next:Mode) {
    if(locked)return;
    setMode(next);previousFull.current=next==='source';onFullSource(next==='source');
    if(next==='write'||next==='source') requestAnimationFrame(()=>source.current?.focus());
  }
  function format(before:string,after='') {
    if(!editable||locked||!source.current)return;
    const start=source.current.selectionStart,end=source.current.selectionEnd;
    const selection=body.slice(start,end)||'text';
    const next=body.slice(0,start)+before+selection+after+body.slice(end);
    onChange((mode==='source'?'':header)+next);
    requestAnimationFrame(()=>{source.current?.focus();source.current?.setSelectionRange(start+before.length,start+before.length+selection.length);});
  }
  function block(kind:'heading'|'list') {
    if(!editable||locked||!source.current)return;
    const next=formatLines(body,source.current.selectionStart,source.current.selectionEnd,kind);
    onChange((mode==='source'?'':header)+next.text);
    requestAnimationFrame(()=>{source.current?.focus();source.current?.setSelectionRange(next.start,next.end);});
  }
  return <div className="document-body">
    <div className="document-modes" role="group" aria-label="Document view">
      <Button variant={mode==='read'?'primary':'quiet'} disabled={locked} aria-pressed={mode==='read'} onClick={()=>select('read')}>Read</Button>
      {editable&&<Button variant={mode==='write'?'primary':'quiet'} disabled={locked} aria-pressed={mode==='write'} onClick={()=>select('write')}>Edit</Button>}
      <Button variant={mode==='preview'?'primary':'quiet'} disabled={locked} aria-pressed={mode==='preview'} onClick={()=>select('preview')}>Preview</Button>
      <Button variant={mode==='source'?'primary':'quiet'} disabled={locked} aria-pressed={mode==='source'} onClick={()=>select('source')}>Source</Button>
    </div>
    {editing ? <div className="editor-source">
      {editable&&<div className="document-formatting" role="group" aria-label="Formatting">
        <Button variant="quiet" disabled={locked} onClick={()=>format('**','**')}>Bold</Button>
        <Button variant="quiet" disabled={locked} onClick={()=>format('*','*')}>Italic</Button>
        <Button variant="quiet" disabled={locked} onClick={()=>block('heading')}>Heading</Button>
        <Button variant="quiet" disabled={locked} onClick={()=>block('list')}>List</Button>
        <Button variant="quiet" disabled={locked} onClick={()=>format('`','`')}>Code</Button>
        <Button variant="quiet" disabled={locked} onClick={()=>format('[','](url)')}>Link</Button>
      </div>}
      <label className="editor-label" htmlFor="markdown">Markdown source</label>
      <textarea ref={source} id="markdown" value={body} readOnly={!editable||locked} spellCheck
        onChange={event=>onChange((mode==='source'?'':header)+event.target.value)}/>
      <p className="muted">{editable?'Changes stay in this tab until you save.':'Read only. The source is shown exactly as saved.'}</p>
    </div> : <div className="document-reader"><Suspense fallback={<p>Loading document…</p>}><Markdown text={text} showOutline={mode==='read'}/></Suspense></div>}
  </div>;
}
