import {HomeError, type Row, type WorkDelegation} from './api';
import {encodeProductRoute} from './productRoutes';

const positive = (value: string | undefined) => value !== undefined && /^[1-9][0-9]{0,19}$/u.test(value)
  && BigInt(value) <= 18446744073709551615n;

// A grant grants proposal access; copying this brief does not dispatch a run.
// Prefer a contract pin only when the Home supplies the complete supported set.
export function agentBrief(project: string, work: Row, grant: WorkDelegation, origin: string): string {
  if (grant.status !== 'active' || !work.resource_id || !positive(work.resource_revision)) throw new HomeError('invalid_response');
  const base = {
    project_id: project, work_id: work.resource_id, delegation_id: grant.id,
    worker_ship: grant.worker, expires_at_ms: grant.expires, target_ref: grant.ref,
    title: work.title ?? '', description: work.description ?? '',
    work_url: origin + '/stead/' + encodeProductRoute({kind:'work',project,item:work.resource_id}),
  };
  const supplied = ['execution_contract_protocol','execution_contract_revision','execution_contract_digest']
    .some(key => Object.hasOwn(work,key));
  if (!supplied) return JSON.stringify({protocol:'stead.agent-brief/1',...base,work_revision:work.resource_revision},null,2);
  if (work.execution_contract_protocol !== 'stead.work-contract/1'
    || !positive(work.execution_contract_revision)
    || !/^[0-9a-f]{64}$/u.test(work.execution_contract_digest ?? '')) throw new HomeError('invalid_response');
  return JSON.stringify({protocol:'stead.agent-brief/2',...base,
    execution_contract_revision:work.execution_contract_revision,
    execution_contract_digest:work.execution_contract_digest},null,2);
}
