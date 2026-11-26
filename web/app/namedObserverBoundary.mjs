// Narrow observational trial boundary. No request or effect is generated here.
export function permittedCodeRead(value, project) {
  return !!value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === 'action,project_id,protocol,work_id'
    && value.protocol === 'stead.code/1' && value.action === 'work-delegations'
    && value.project_id === project && typeof value.work_id === 'string'
    && /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u.test(value.work_id);
}
export function permittedCommand(command, project, created, started, person) {
  if (!started || !person || !command || command.protocol !== 'stead.command/3'
      || command.project_id !== project || !command.payload) return false;
  const id = command.resource_id;
  if (command.operation === 'work.create') return command.expected_revision === '0';
  if (command.operation === 'work.update') return created.work.has(id);
  if (command.operation === 'container.create') return command.expected_revision === '0' && command.payload.visibility === 'private';
  if (command.operation === 'document.save') return created.container.has(command.payload.container_id)
    && (command.expected_revision === '0' || created.document.has(id));
  return false;
}
export function exactApproval(text, comparison, ship, home) {
  return typeof comparison === 'string' && /^[0-9a-f]{12}$/u.test(comparison)
    && typeof text === 'string' && text.split(/\s+/u).includes(home) && text.split(/\s+/u).includes(ship);
}
