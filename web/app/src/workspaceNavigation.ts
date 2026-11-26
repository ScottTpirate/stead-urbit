import {HomeError} from './api';
import {decodeProductRoute, type NavigationView} from './productRoutes';
import type {WorkspaceQueryView} from './WorkspaceView';

// Every listed resource requires an accepted ordinary event. The current Home
// admits at most4096 such events and returns at most20 rows per query page.
export const WORKSPACE_RESTORE_MAX_PAGES = Math.ceil(4096 / 20);
export const WORKSPACE_RESTORE_BUDGET_MS = 20_000;
export type WorkspaceRestore = Readonly<{page: number; selection?: string; scroll: number}>;
export function workspaceRestore(view: WorkspaceQueryView, term: string, memory?: NavigationView): WorkspaceRestore | undefined {
  if (!memory || memory.filters.title !== (view === 'workspace-search' ? term : '')) return;
  const page = memory.workspacePage ?? 1;
  if (!Number.isSafeInteger(page) || page < 1 || page > WORKSPACE_RESTORE_MAX_PAGES) return;
  const selected = memory.selection ? decodeProductRoute(memory.selection) : null;
  const selection = ((selected?.kind === 'work' && selected.item) || selected?.kind === 'doc') ? memory.selection : undefined;
  return {page, selection, scroll: Number.isFinite(memory.scroll) && memory.scroll >= 0 ? memory.scroll : 0};
}
export type RestoreNote = 'page' | 'end' | 'budget' | 'budget-inflight';
export function workspaceRestoreDecision(input: {page: number; cursor: string; target: WorkspaceRestore; routes: readonly string[]}): 'continue' | 'found' | RestoreNote {
  if (input.target.selection && input.routes.includes(input.target.selection)) return 'found';
  if (!input.cursor) return 'end';
  if (input.page >= input.target.page || input.page >= WORKSPACE_RESTORE_MAX_PAGES) return 'page';
  return 'continue';
}

// Only active-walk tokens live here. Nothing is persisted across navigation.
export class WorkspaceCursorSequence {
  private returned = new Set<string>();
  private consumed = new Set<string>();
  use(cursor: string) {
    if (!cursor) return;
    if (this.consumed.has(cursor)) throw new HomeError('invalid_response');
    this.consumed.add(cursor);
  }
  receive(cursor: string) {
    if (!cursor) return;
    if (this.returned.has(cursor) || this.consumed.has(cursor)) throw new HomeError('invalid_response');
    this.returned.add(cursor);
  }
}

// onPage may update parent memory before focus commits. Capture the original
// primitive restoration values once for this exact scope and attempt.
export class WorkspaceRestoreCapture {
  private key = '';
  private attempt = -1;
  private target?: WorkspaceRestore;
  capture(key: string, attempt: number, input?: {page?: number; selection?: string; scroll: number}): WorkspaceRestore | undefined {
    if (key === this.key && attempt === this.attempt) return this.target;
    this.key = key; this.attempt = attempt; this.target = undefined;
    const page = input?.page ?? 1;
    if (input && Number.isSafeInteger(page) && page >= 1 && page <= WORKSPACE_RESTORE_MAX_PAGES) {
      this.target = Object.freeze({page, selection: input.selection,
        scroll: Number.isFinite(input.scroll) && input.scroll >= 0 ? input.scroll : 0});
    }
    return this.target;
  }
}
