import type {Row} from './api';
import {handbookRepositoryResponse} from './handbookRepository';
import whyStead from './handbook/why-stead.md' with {type: 'text'};
import architecture from './handbook/architecture.md' with {type: 'text'};
import dailyWork from './handbook/daily-work.md' with {type: 'text'};
import settings from './handbook/settings.md' with {type: 'text'};
import agents from './handbook/agents.md' with {type: 'text'};
import questions from './handbook/questions.md' with {type: 'text'};

const id = (suffix: string) => '019a0000-0000-7000-8000-0000000000' + suffix;
const project = id('01');
const collection = id('02');
const work = id('03');
const epoch = '1';
const csrf = 'e'.repeat(64);

export const handbookProject: Row = Object.freeze({
  kind: 'project', project_id: project, resource_id: project, project_key: 'GUIDE',
  title: 'Stead Handbook', summary: 'Explore an example task, read the guides and browse the Handbook repository.',
  preset: 'general', role: 'reader', authority_epoch: epoch, resource_revision: '1', policy_revision: '1',
});

export const handbookCollection: Row = Object.freeze({
  kind: 'container', project_id: project, container_id: collection, resource_id: collection,
  resource_revision: '1', container_head: '1', visibility: 'shared', title: 'Handbook guides',
});

const criteria = 'Only the meeting day changes from Monday to Wednesday. The time, meeting point and other wording stay the same. A teammate reviews the proposed edit.';
export const handbookWork: Row = Object.freeze({
  kind: 'work', project_id: project, resource_id: work, container_id: '', resource_revision: '1',
  title: 'Update the visitor guide', type: 'task', status: 'todo', priority: 'medium',
  assignee_principal_id: '', assignee_display_name: '',
  description: 'Move the opening meeting from Monday to Wednesday in the visitor guide. Ask which meeting to update if the guide lists two Monday meetings.\n\nCompletion criteria\n' + criteria,
  completion_criteria: criteria,
});

function document(suffix: string, markdown: string): Row {
  const resource = id(suffix);
  const title = markdown.split('\n', 1)[0]?.replace(/^#\s+/u, '') ?? '';
  return Object.freeze({kind: 'document', project_id: project, resource_id: resource,
    container_id: collection, resource_revision: '1', container_head: '1', title,
    markdown: '---\nid: ' + resource + '\ntype: page\nstate: published\n---\n' + markdown});
}

export const handbookDocs = Object.freeze({
  'why-stead': document('15', whyStead),
  architecture: document('16', architecture),
  'daily-work': document('11', dailyWork),
  settings: document('12', settings),
  agents: document('13', agents),
  questions: document('14', questions),
});
const pages = Object.values(handbookDocs);
const identity: Row = Object.freeze({principal_id: id('20'), binding_id: id('21'), binding_revision: '1',
  identity_ship: '~bus', display_name: 'Handbook reader', session_audit_id: 'f'.repeat(64), can_create: 'no'});
const comment: Row = Object.freeze({kind: 'comment', project_id: project, resource_id: id('30'),
  comment_revision: '1', body: 'I’ll check that the time and meeting point still match the original.',
  identity_ship: '~nec', principal_id: id('22'), accepted_at_ms: '1795708800000'});
const relation: Row = Object.freeze({kind: 'relation', project_id: project, resource_id: id('31'), resource_revision: '1',
  type: 'documents', source_project_id: project, source_kind: 'document', source_container_id: collection,
  source_id: handbookDocs.agents.resource_id!, target_project_id: project, target_kind: 'work',
  target_container_id: '', target_id: work});

function queryRows(query: Record<string, unknown>): Row[] | undefined {
  const {project_id, resource_id, container_id, kind, cursor, search} = query;
  if ([project_id, resource_id, container_id, search].some(field => typeof field !== 'string') || cursor !== '') return;
  if (project_id === '' && container_id === '' && resource_id === '' && search === '') {
    if (kind === 'identity') return [identity];
    if (kind === 'projects') return [handbookProject];
  }
  if (project_id !== project) return;
  if (kind === 'search' && container_id === '' && resource_id === '' && typeof search === 'string') {
    const term = search.trim().toLocaleLowerCase();
    return term ? [handbookWork, ...pages].filter(row => [row.title, row.description, row.markdown]
      .some(field => field?.toLocaleLowerCase().includes(term))) : [];
  }
  if (search !== '') return;
  if (kind === 'document' && container_id === collection) {
    const page = pages.find(row => row.resource_id === resource_id);
    return page ? [page] : undefined;
  }
  if (kind === 'documents' && container_id === collection && resource_id === '') return pages;
  if (container_id !== '') return;
  if (kind === 'work' && (resource_id === '' || resource_id === work)) return [handbookWork];
  if (kind === 'comments' && resource_id === work) return [comment];
  if (kind === 'project' && (resource_id === '' || resource_id === project)) return [handbookProject];
  if (resource_id !== '') return;
  if (kind === 'containers') return [handbookCollection];
  if (kind === 'relations') return [relation];
  if (kind === 'assignees' || kind === 'activity' || kind === 'inbox') return [];
}

const denied = () => Response.json({error: 'denied_or_not_found'}, {status: 403});

/** A separate HomeClient uses this closed source for the packaged reader project. */
export async function handbookFetch(path: string, init: RequestInit): Promise<Response> {
  if (init.signal?.aborted) throw new DOMException('Read aborted', 'AbortError');
  if (init.method !== 'POST' || typeof init.body !== 'string' || init.body.length > 65536) return denied();
  let data: unknown;
  try { data = JSON.parse(init.body); } catch { return denied(); }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return denied();
  const body = data as Record<string, unknown>;
  if (path === '/stead/api/capabilities' && Object.keys(body).length === 1 && body.protocol === 'stead.capabilities/3') {
    return Response.json({protocol: 'stead.capabilities/3', profile: 'configured-team',
      commands: 'stead.command/3', queries: 'stead.query/3', work_contract: 'stead.work-contract/1'});
  }
  if (path === '/stead/auth/resume' && Object.keys(body).length === 1 && body.protocol === 'stead.auth/1') {
    return Response.json({status: 'authenticated', csrf});
  }
  if (new Headers(init.headers).get('X-Stead-CSRF') !== csrf) return denied();
  if (path === '/stead/api/query' && body.protocol === 'stead.query/3' && Object.keys(body).length === 8 && typeof body.request_id === 'string') {
    const rows = queryRows(body);
    if (!rows) return denied();
    return Response.json({protocol: 'stead.query-result/3', status: 'read', request_id: body.request_id,
      kind: body.kind, project_id: body.project_id, container_id: body.container_id, resource_id: body.resource_id,
      search: body.search, cursor: '', generation: 'a'.repeat(64), authority_epoch: epoch,
      rows: Object.fromEntries(rows.map((row, i) => [String(i), row]))});
  }
  if (body.project_id === project && (path === '/stead/api/code' || path === '/stead/api/code/browse')) {
    return handbookRepositoryResponse(path, body) ?? denied();
  }
  return denied();
}
