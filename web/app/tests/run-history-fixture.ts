// Explicit synthetic data for host and future rendered component checks only.
import {canonical} from '../src/protocol';
import {RunReadClient, parseRunQuery, type RunDetail, type RunPhase, type RunPreview, type RunQuery, type RunReadTransport} from '../src/runReadProtocol';
import type {RunHistoryProps} from '../src/RunHistory';
export const id = (n: number) => { if (n < 100 || n > 999) throw new Error('Fixture ID bound'); return '019939ba-4000-7000-8000-000000000' + n; };
export const fixtureTime = 1700000000000;
export function preview(n = 400, now = fixtureTime): RunPreview { return {kind:'run',project_id:id(100),work_id:id(101),run_id:id(n),run_revision:'1',phase:'queued',
  issued_at_ms:String(now),deadline_ms:String(now+300000),requester_principal_id:id(102),requester_display_name:'Casey',owner_principal_id:id(102),owner_display_name:'Casey',
  worker_principal_id:id(103),worker_display_name:'Atlas',current_attempt:'0',question_sequence:'0',lease_state:'none',lease_until_ms:'0',result:''}; }
export function detail(n = 400, phase: RunPhase = 'waiting', now = fixtureTime): RunDetail {
  const base = preview(n,now), claimed = phase !== 'queued', terminal = ['submitted','failed','canceled'].includes(phase);
  return {...base,run_revision:claimed?'3':'1',phase,current_attempt:claimed?'1':'0',question_sequence:phase==='waiting'?'1':'0',lease_state:claimed?(terminal?'terminal':'live'):'none',lease_until_ms:claimed?String(now+120000):'0',
    result:phase==='submitted'?canonical({change_id:id(500),result_revision:'2',result_digest:'b'.repeat(64),outcome_id:id(501)}):'',
    execution_contract_revision:'4',execution_contract_digest:'a'.repeat(64),agent_version:canonical({definition_id:id(300),definition_revision:'1',runtime_id:id(301),runtime_revision:'2'}),execution_current:'yes',
    current_attempt_detail:claimed?canonical({attempt:'1',principal_id:id(103),display_name:'Atlas',started_at_ms:String(now+1000),heartbeat_at_ms:String(now+2000),lease_until_ms:String(now+120000),disposition:phase}):'',
    latest_question:phase==='waiting'?canonical({sequence:'1',text:'Which part of the shared guide needs clarification?\nKeep the original wording where possible.',principal_id:id(103),display_name:'Atlas',recorded_at_ms:String(now+3000),
      answer:canonical({text:'Clarify the final step. Keep the exact example.',principal_id:id(102),display_name:'Casey',recorded_at_ms:String(now+4000)})}):''};
}
export function wire(query: RunQuery, rows: readonly (RunPreview | RunDetail)[], overrides: Record<string,unknown> = {}) {
  return canonical({protocol:'stead.run-query-result/1',status:'read',request_id:query.request_id,kind:query.kind,project_id:query.project_id,work_id:query.work_id,run_id:query.run_id,
    authority_epoch:'1',generation:'c'.repeat(64),cursor:'',rows:Object.fromEntries(rows.map((row,index)=>[String(index),row])),...overrides});
}
export function client(overrides: Partial<RunReadTransport> = {}) {
  return new RunReadClient({currentSession:()=> 'session-A',capability:()=> 'stead.run-query/1',query:async raw=>{const request=parseRunQuery(raw);return wire(request,request.kind==='run'?[detail(Number(request.run_id.slice(-3)))]:[preview()]);},...overrides});
}
export function properties(value: RunReadClient | null = client(), overrides: Partial<RunHistoryProps> = {}): RunHistoryProps {
  return {client:value,projectId:id(100),workId:id(101),sessionKey:'ui-session-A',online:true,access:'readable',onSelectRun:()=>{},onOpenChange:()=>{},onAccessChanged:()=>{},...overrides};
}
