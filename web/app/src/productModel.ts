// Presentation contract only. Home owns authorization and accepted transitions.
export const workStates = ['backlog', 'todo', 'in_progress', 'in_review', 'done', 'canceled'] as const;
export type WorkState = typeof workStates[number];
export const workStateLabels: Record<WorkState, string> = {
  backlog: 'Backlog', todo: 'To do', in_progress: 'In progress', in_review: 'In review', done: 'Done', canceled: 'Canceled',
};
export const runStates = ['queued', 'running', 'waiting_for_input', 'submitted', 'failed', 'canceled'] as const;
export type RunState = typeof runStates[number];
export const runStateLabels: Record<RunState, string> = {
  queued: 'Queued', running: 'Running', waiting_for_input: 'Waiting for input', submitted: 'Ready for review', failed: 'Failed', canceled: 'Canceled',
};
export const newWorkDefaults = Object.freeze({type: 'task', status: 'todo', priority: 'none', assignee_principal_id: ''});
export function workStateLabel(state: string): string {
  // Retain the meaning of legacy blocked records until their native migration.
  if (state === 'blocked') return 'Blocked';
  return Object.hasOwn(workStateLabels, state) ? workStateLabels[state as WorkState] : 'Unknown state';
}
export function priorityLabel(priority: string): string {
  return ({none: 'No priority', low: 'Low', medium: 'Normal', high: 'High', urgent: 'Urgent'} as Record<string,string>)[priority] ?? 'Unknown priority';
}
export function relationshipLabel(kind: string): string {
  // Version-3 `documents` is Doc→Work. Never interpret it as the new Code link.
  return ({documents: 'Supports', related_to: 'Related', blocks: 'Blocks'} as Record<string,string>)[kind] ?? 'Related';
}
