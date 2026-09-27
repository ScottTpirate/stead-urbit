// Explicit allowlist: neither server text nor arbitrary browser state is copied.
const codes = new Set(['none', 'unexpected_error', 'session_required', 'denied_or_not_found',
  'revision_conflict', 'authority_epoch_conflict', 'stale_cursor', 'capacity_exceeded',
  'outcome_unknown', 'invalid_response', 'unsupported_version', 'projection_unavailable',
  'invalid_csrf', 'resume_required', 'logout_unconfirmed', 'updates_unavailable']);
export function supportDetails(code: string, requestId?: string): string {
  return JSON.stringify({format: 'stead.support/1', app_version: '0.2.0',
    command_protocol: 'stead.command/3', diagnostic: codes.has(code) ? code : 'unexpected_error',
    ...(requestId && /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u.test(requestId)
      ? {request_id: requestId} : {})}, null, 2) + '\n';
}
