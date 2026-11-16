import type {ProductWorkPreview} from '../src/productProtocol';
export const id = (value: number) => `019939ba-4000-7000-8000-${String(value).padStart(12, '0')}`;
export const project = id(100);
export function row(value: number, patch: Partial<ProductWorkPreview> = {}): ProductWorkPreview {
  return {kind: 'work', project_id: project, resource_id: id(value), container_id: '', resource_revision: '1', work_revision: '1',
    execution_contract_protocol: 'stead.work-contract/2', execution_contract_revision: '1', execution_contract_digest: 'a'.repeat(64),
    discussion_sequence: '0', title: `Work ${value}`, type: 'task', status: 'todo', priority: 'none', owner_principal_id: '', worker_principal_id: '',
    owner_display_name: '', worker_display_name: '', snippet: 'Authorized current page preview.', ...patch};
}
