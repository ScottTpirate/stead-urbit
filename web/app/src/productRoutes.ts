// Resource addresses contain identity only. Search text, drafts and view filters
// belong in scoped in-memory navigation state, never in a shared URL.
const ID = /^[a-f0-9]{8}-[a-f0-9]{4}-7[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u;
const REVISION = /^[1-9][0-9]{0,19}$/u;
const validRevision = (value: string) => REVISION.test(value) && BigInt(value) <= 18446744073709551615n;
const OID = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/u;
function validPath(path: string): boolean {
  return path.length > 0 && new TextEncoder().encode(path).length <= 1024
    && !/[\u0000-\u001f\u007f\\]/u.test(path) && path.split('/').every(part => part !== '' && part !== '.' && part !== '..');
}
export type ProjectView = 'overview' | 'work' | 'docs' | 'code';
export type WorkspaceView = 'inbox' | 'my-work' | 'search';
export type ProductRoute =
  | { kind: 'workspace'; view: WorkspaceView }
  | { kind: 'project'; project: string; view: ProjectView }
  | { kind: 'work'; project: string; item?: string }
  | { kind: 'doc'; project: string; collection: string; document: string; revision?: string }
  | { kind: 'collection'; project: string; collection: string }
  | { kind: 'repository'; project: string; repository: string; view: 'files' | 'changes' | 'history' }
  | { kind: 'change'; project: string; change: string; revision?: string }
  | { kind: 'review'; project: string; change: string; revision: string }
  | { kind: 'file'; project: string; repository: string; commit: string; path: string }
  | { kind: 'run'; project: string; run: string };

export function decodeProductRoute(hash: string): ProductRoute | null {
  if (hash.length > 4096 || !hash.startsWith('#') || /[?\s]/u.test(hash)) return null;
  const p = hash.slice(1).split('/');
  const [kind, project, a, b, revision] = p;
  if (p.length === 1 && ['inbox', 'my-work', 'search'].includes(kind ?? '')) {
    return { kind: 'workspace', view: kind as WorkspaceView };
  }
  if (!ID.test(project ?? '')) return null;
  if (kind === 'file' && p.length === 5 && ID.test(a ?? '') && OID.test(b ?? '') && revision) {
    try {
      const path = decodeURIComponent(revision);
      return validPath(path) && encodeURIComponent(path) === revision
        ? {kind:'file',project:project!,repository:a!,commit:b!,path} : null;
    } catch { return null; }
  }
  if (hash.includes('%')) return null;
  if (kind === 'collection' && p.length === 3 && ID.test(a ?? '')) return {kind:'collection',project:project!,collection:a!};
  if (kind === 'project' && p.length === 3 && ['overview', 'work', 'docs', 'code'].includes(a ?? '')) {
    return {kind: 'project', project: project!, view: a as ProjectView};
  }
  // Keep all existing #work/project[/item] links working without rewriting IDs.
  if (kind === 'work' && (p.length === 2 || (p.length === 3 && ID.test(a ?? '')))) {
    return {kind: 'work', project: project!, ...(a ? {item: a} : {})};
  }
  if (kind === 'doc' && [4, 5].includes(p.length) && ID.test(a ?? '') && ID.test(b ?? '')
    && (revision === undefined || validRevision(revision))) {
    return {kind: 'doc', project: project!, collection: a!, document: b!, ...(revision ? {revision} : {})};
  }
  if (kind === 'repository' && p.length === 4 && ID.test(a ?? '') && ['files', 'changes', 'history'].includes(b ?? '')) {
    return {kind: 'repository', project: project!, repository: a!, view: b as 'files' | 'changes' | 'history'};
  }
  if (kind === 'change' && [3, 4].includes(p.length) && ID.test(a ?? '') && (b === undefined || validRevision(b))) {
    return {kind: 'change', project: project!, change: a!, ...(b ? {revision: b} : {})};
  }
  if (kind === 'review' && p.length === 4 && ID.test(a ?? '') && b !== undefined && validRevision(b)) {
    return {kind:'review',project:project!,change:a!,revision:b};
  }
  if (kind === 'run' && p.length === 3 && ID.test(a ?? '')) return {kind: 'run', project: project!, run: a!};
  return null;
}

export function encodeProductRoute(route: ProductRoute): string {
  const parts = route.kind === 'workspace' ? [route.view]
    : route.kind === 'project' ? ['project', route.project, route.view]
    : route.kind === 'work' ? ['work', route.project, ...(route.item ? [route.item] : [])]
    : route.kind === 'doc' ? ['doc', route.project, route.collection, route.document, ...(route.revision ? [route.revision] : [])]
    : route.kind === 'collection' ? ['collection',route.project,route.collection]
    : route.kind === 'repository' ? ['repository', route.project, route.repository, route.view]
    : route.kind === 'change' ? ['change', route.project, route.change, ...(route.revision ? [route.revision] : [])]
    : route.kind === 'review' ? ['review', route.project, route.change, route.revision]
    : route.kind === 'file' ? ['file', route.project, route.repository, route.commit, encodeURIComponent(route.path)]
    : ['run', route.project, route.run];
  const hash = '#' + parts.join('/');
  if (!decodeProductRoute(hash)) throw new Error('Invalid resource address');
  return hash;
}

export type WorkFilters = {title: string; status: string; assignee: string};
export type NavigationView = {filters: WorkFilters; scroll: number; selection?: string};

// Memory only: logout/revocation clears the instance. It cannot persist protected
// drafts in browser history or expose one principal's state to another principal.
export class NavigationMemory {
  private principal = '';
  private entries = new Map<string, NavigationView>();
  bind(principal: string) {
    if (principal !== this.principal) { this.clear(); this.principal = principal; }
  }
  set(route: ProductRoute, view: NavigationView) {
    if (!this.principal) return;
    const key = encodeProductRoute(route);
    if (!this.entries.has(key) && this.entries.size >= 64) this.entries.delete(this.entries.keys().next().value!);
    this.entries.set(key, {...view, filters: {...view.filters}});
  }
  get(route: ProductRoute): NavigationView | undefined {
    const value = this.entries.get(encodeProductRoute(route));
    return value ? {...value, filters: {...value.filters}} : undefined;
  }
  clear() { this.entries.clear(); this.principal = ''; }
}
