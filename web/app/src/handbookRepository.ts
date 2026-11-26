import readme from './handbook/README.md' with {type: 'text'};

const project = '019a0000-0000-7000-8000-000000000001';
const linkedWork = '019a0000-0000-7000-8000-000000000003';
// Release fixture: refs/heads/main, with one root tree containing README.md.
const main = '726566732f68656164732f6d61696e';
const filename = '524541444d452e6d64';
const readmeBlob = 'b254a011cac8555be116bc2b3de79e0d722e029c';
const commit = '82c60cf639eba6b19aab1bfb15c03ebacf71ee70';
const snapshot = '63d3ab94c452349ffcca44c7a4f2959ac3b263bd5e866661854c9dd76018b828';

function denied() {
  return Response.json({error: 'denied_or_not_found'}, {status: 403});
}

function fieldsAre(body: Record<string, unknown>, fields: string[]) {
  return Object.keys(body).length === fields.length && fields.every(key => Object.hasOwn(body, key));
}

export function handbookRepositoryResponse(path: string, value: unknown): Response | undefined {
  const codePath = '/stead/api/code';
  const browsePath = '/stead/api/code/browse';
  if (path !== codePath && path !== browsePath) return undefined;
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return denied();
  const body = value as Record<string, unknown>;
  if (body.project_id !== project) return denied();

  if (path === codePath) {
    const protocol = 'stead.code/1';
    const required = ['protocol', 'project_id', 'action'];
    if (body.protocol !== protocol) return denied();
    if (body.action === 'external-list' && (fieldsAre(body, required)
      || (fieldsAre(body, [...required, 'work_id']) && body.work_id === linkedWork))) {
      return Response.json({protocol, status: 'proposals', rows: '[]'});
    }
    if (!fieldsAre(body, required)) return denied();
    if (body.action === 'status') return Response.json({protocol, status: 'external', write: 'no', manage: 'no'});
    if (body.action === 'pack-view') {
      return Response.json({protocol, status: 'external', snapshot, authority_epoch: '1', generation: '1',
        object_count: '3', request_id: '019a0000-0000-7000-8000-000000000009',
        accepted_at_ms: '1795651200000', head: main, refs: JSON.stringify({[main]: commit})});
    }
    return denied();
  }

  const protocol = 'stead.git-browse/1';
  if (!fieldsAre(body, ['protocol', 'project_id', 'snapshot', 'ref', 'path', 'view'])
    || body.protocol !== protocol || body.snapshot !== snapshot || body.ref !== main || !Array.isArray(body.path)) return denied();
  const selection = {protocol, project_id: project, snapshot, ref: main, path: body.path, commit};
  if (body.view === 'tree' && body.path.length === 0) {
    return Response.json({...selection, status: 'tree', truncated: false,
      entries: [{name: filename, kind: 'file', oid: readmeBlob}]});
  }
  if (body.view === 'file' && body.path.length === 1 && body.path[0] === filename) {
    return Response.json({...selection, status: 'file', preview: 'text', bytes: new TextEncoder().encode(readme).length, text: readme});
  }
  return denied();
}
