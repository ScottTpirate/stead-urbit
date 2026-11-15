export type TextSelection = {text:string;start:number;end:number};

// Textarea offsets are UTF-16 offsets. Expand a block action to its lines,
// preserving all text outside the explicitly selected block.
export function formatLines(text:string,start:number,end:number,kind:'heading'|'list'):TextSelection {
  start=Math.max(0,Math.min(text.length,start));end=Math.max(start,Math.min(text.length,end));
  const first=start===0?0:text.lastIndexOf('\n',start-1)+1;
  const lastSelected=end>start && text[end-1]==='\n'?end-1:end;
  const newline=text.indexOf('\n',lastSelected);
  const last=newline<0?text.length:newline;
  const lines=text.slice(first,last).split('\n');
  const prefix=kind==='heading'?'# ':'- ';
  const existing=kind==='heading'?/^#{1,6} +/u:/^(?:[-+*]|[0-9]+[.)]) +/u;
  let firstDelta=0,totalDelta=0;
  const updated=lines.map((line,index)=>{
    const old=existing.exec(line)?.[0]??'';
    const delta=prefix.length-old.length;
    if(index===0)firstDelta=delta;
    totalDelta+=delta;
    return prefix+line.slice(old.length);
  }).join('\n');
  const next=text.slice(0,first)+updated+text.slice(last);
  const position=Math.max(first+prefix.length,start+firstDelta);
  return {text:next,start:position,end:start===end?position:Math.max(position,end+totalDelta)};
}
