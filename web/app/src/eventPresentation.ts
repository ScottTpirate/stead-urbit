import type {Row} from './api';

const actions = new Map<string, string>([
  ['project.create', 'Created a project'],
  ['work.create', 'Created work'],
  ['work.update', 'Updated work'],
  ['work.assign', 'Changed the work assignee'],
  ['work.comment', 'Commented on work'],
  ['work.delete', 'Deleted work'],
  ['container.create', 'Created a collection'],
  ['document.save', 'Saved a document'],
  ['document.publish', 'Published a document'],
  ['document.delete', 'Deleted a document'],
  ['relation.create', 'Added a relationship'],
  ['relation.delete', 'Removed a relationship'],
]);

export interface EventActor {
  readonly principal_id: string;
  readonly display_name: string;
}

export interface PresentedEvent {
  readonly actor: string;
  readonly action: string;
  readonly summary: string;
  readonly acceptedAt: string;
  readonly details: readonly {readonly label: string; readonly value: string}[];
}

const identifier = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu;
function actorName(actor: EventActor | undefined, principal: string): string | undefined {
  if (!actor || !principal || actor.principal_id !== principal) return;
  const name = actor.display_name.trim();
  if (!name || new TextEncoder().encode(name).length > 200
      || /[\u0000-\u001f\u007f-\u009f]/u.test(name) || identifier.test(name)) return;
  return name;
}

/** Present an already authorized accepted journal row, without resolving identity.
 * Query/3 currently supplies no actor name. A future caller may pass a name only
 * from its authorized native identity projection for the same principal.
 * This helper never treats titles, runtime bindings or IDs as display names.
 */
export function eventPresentation(row: Readonly<Row>, currentPrincipal?: string, resolvedActor?: EventActor): PresentedEvent {
  const principal = row.principal_id ?? '';
  const actor = principal && currentPrincipal && principal === currentPrincipal
    ? 'You' : actorName(resolvedActor, principal) ?? 'Project member';
  const action = actions.get(row.operation ?? '') ?? 'Recorded a project update';
  const detailFields = [
    ['Operation', 'operation'], ['Request ID', 'request_id'], ['Member ID', 'principal_id'],
    ['Resource ID', 'resource_id'], ['Collection ID', 'container_id'], ['Accepted time (milliseconds)', 'accepted_at_ms'],
  ] as const;
  return {
    actor, action, summary: `${actor} ${action[0]!.toLocaleLowerCase()}${action.slice(1)}`,
    acceptedAt: row.accepted_at_ms ?? '',
    details: detailFields.flatMap(([label, key]) => row[key] ? [{label, value: row[key]}] : []),
  };
}
