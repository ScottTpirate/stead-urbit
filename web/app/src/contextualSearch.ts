import {HomeError, UUID, type HomeClient, type Row, type View} from './api';

type Client = Pick<HomeClient, 'query' | 'currentSessionToken' | 'productMode'>;
export type ContextKind = 'work' | 'document';
export type ContextChoice = {kind: ContextKind; id: string; container: string; title: string};
export type ContextSearchScope = {
  client: Client; project: string; work: string; relation: string; kind: ContextKind;
  term: string; revision: number; writable: boolean; locked: boolean; online: boolean;
};
export type ContextSearchPage = Readonly<{choices: readonly ContextChoice[]; number: number; cursor: string; generation: string; epoch: string}>;
export type ContextSearchState = Readonly<{
  phase: 'idle' | 'loading' | 'ready' | 'failed' | 'expired' | 'revoked' | 'unsupported' | 'offline';
  page?: ContextSearchPage;
}>;
export const CONTEXT_SEARCH_MAX_PAGES = 205;
const bytes = (text: string) => new TextEncoder().encode(text).length;
export const contextChoiceKey = (value: Pick<ContextChoice, 'kind' | 'container' | 'id'>) => `${value.kind}/${value.container}/${value.id}`;

function pageChoices(view: View, scope: ContextSearchScope, seen: Set<string>): ContextChoice[] {
  if (view.kind !== 'search' || view.project_id !== scope.project || view.container_id || view.resource_id
    || !/^[1-9][0-9]{0,19}$/u.test(view.authority_epoch) || BigInt(view.authority_epoch) > 18446744073709551615n
    || !/^[a-f0-9]{64}$/u.test(view.generation) || (view.cursor && !/^[a-f0-9]{64}$/u.test(view.cursor))) throw new HomeError('invalid_response');
  const rows = Object.values(view.rows);
  if (rows.length > 20 || (view.cursor && rows.length !== 20)) throw new HomeError('invalid_response');
  const choices: ContextChoice[] = [];
  for (const row of rows) {
    if (!['work', 'document'].includes(row.kind ?? '') || !UUID.test(row.resource_id ?? '')
      || (row.kind === 'document' ? !UUID.test(row.container_id ?? '') : row.container_id !== '')
      || (row.project_id !== undefined && row.project_id !== scope.project) || typeof row.title !== 'string'
      || bytes(row.title) > 800) throw new HomeError('invalid_response');
    const choice: ContextChoice = {kind: row.kind as ContextKind, id: row.resource_id!, container: row.container_id!, title: title(row)};
    const key = contextChoiceKey(choice);
    if (seen.has(key) || seen.size >= 4096) throw new HomeError('invalid_response');
    seen.add(key);
    if (choice.kind === scope.kind && !(choice.kind === 'work' && choice.id === scope.work)) choices.push(choice);
  }
  return choices;
}
function title(row: Row) {
  const value = row.title?.trim() || '';
  return row.kind === 'document' ? value.split('\n', 1)[0]?.replace(/^#{1,6} +/u, '').trim() || 'Untitled page' : value || 'Untitled work item';
}

/** Only the current page is visible. Every continuation is consumed at most once. */
export class ContextualSearch {
  private scope?: ContextSearchScope;
  private token: object | null = null;
  private carrier?: ReturnType<Client['productMode']>;
  private serial = 0;
  private generation = 0;
  private value: ContextSearchState = {phase: 'idle'};
  private used = new Set<string>();
  private returned = new Set<string>();
  private seen = new Set<string>();
  configure(next: ContextSearchScope): number {
    const token = next.client.currentSessionToken(), carrier = next.client.productMode(), prior = this.scope;
    if (!prior || prior.client !== next.client || this.token !== token || this.carrier !== carrier
      || prior.project !== next.project || prior.work !== next.work || prior.relation !== next.relation || prior.kind !== next.kind
      || prior.term !== next.term || prior.revision !== next.revision || prior.writable !== next.writable || prior.online !== next.online) {
      this.serial++; this.generation++; this.value = {phase: 'idle'}; this.used.clear(); this.returned.clear(); this.seen.clear();
    }
    this.scope = next; this.token = token; this.carrier = carrier;
    return this.generation;
  }
  state(): ContextSearchState {
    if (!this.scope || !this.token || this.token !== this.scope.client.currentSessionToken()) return {phase: 'revoked'};
    if (this.carrier !== this.scope.client.productMode() || this.carrier?.kind !== 'legacy') return {phase: 'unsupported'};
    if (!this.scope.online) return {phase: 'offline'};
    return this.value;
  }
  dispose() { this.serial++; this.scope = undefined; this.value = {phase: 'idle'}; this.used.clear(); this.returned.clear(); this.seen.clear(); }
  async first(): Promise<boolean> { return this.read(true); }
  async next(): Promise<boolean> { return this.read(false); }
  private async read(first: boolean): Promise<boolean> {
    const scope = this.scope;
    if (!scope || !this.token || this.token !== scope.client.currentSessionToken() || this.carrier !== scope.client.productMode()
      || this.carrier?.kind !== 'legacy' || scope.locked || !scope.online || !scope.writable) return false;
    const term = scope.term.trim();
    if (!term || bytes(term) > 128 || !UUID.test(scope.project) || !UUID.test(scope.work)) return false;
    const previous = this.value.phase === 'ready' ? this.value.page : undefined;
    if (!first && (!previous?.cursor || previous.number >= CONTEXT_SEARCH_MAX_PAGES)) return false;
    const cursor = first ? '' : previous!.cursor, number = first ? 1 : previous!.number + 1;
    if (first) { this.used.clear(); this.returned.clear(); this.seen.clear(); }
    const ticket = ++this.serial, token = this.token, carrier = this.carrier;
    const live = () => ticket === this.serial && this.scope?.client === scope.client && this.token === token
      && scope.client.currentSessionToken() === token && this.carrier === carrier && scope.client.productMode() === carrier;
    // The previous page is removed before a cursor is consumed. A failed request
    // offers a fresh first page, never a retry of an ambiguously spent cursor.
    this.value = {phase: 'loading'};
    try {
      if (cursor) { if (this.used.has(cursor)) throw new HomeError('invalid_response'); this.used.add(cursor); }
      const view = await scope.client.query({kind: 'search', project_id: scope.project, container_id: '', resource_id: '', search: term, cursor});
      if (!live()) return false;
      if (!first && previous && (view.authority_epoch !== previous.epoch || view.generation !== previous.generation)) throw new HomeError('stale_cursor');
      if (view.cursor) {
        if (this.returned.has(view.cursor) || this.used.has(view.cursor)) throw new HomeError('invalid_response');
        this.returned.add(view.cursor);
      }
      const choices = pageChoices(view, scope, this.seen);
      this.value = {phase: 'ready', page: {choices, number, cursor: view.cursor, generation: view.generation, epoch: view.authority_epoch}};
    } catch (failure) {
      if (!live()) return false;
      const code = failure instanceof HomeError ? failure.code : '';
      this.value = {phase: ['denied_or_not_found', 'session_required', 'session_changed'].includes(code) ? 'revoked'
        : code === 'stale_cursor' ? 'expired' : ['unsupported_query', 'unsupported_operation', 'unsupported_version'].includes(code) ? 'unsupported' : 'failed'};
    }
    return live();
  }
}
