// Observe a native challenge. Only the person's explicit action consumes an approval.
export type ApprovalNotice = 'approved' | 'ended' | 'unavailable';
export function watchApproval(
  expiresAt: string | undefined,
  status: (signal: AbortSignal) => Promise<string>,
  notify: (notice: ApprovalNotice) => void,
) {
  const until = Number(expiresAt);
  if (!Number.isSafeInteger(until) || until <= 0) return () => {};
  const controller = new AbortController();
  const duration = Math.max(0, Math.min(until - Date.now(), 120_000));
  const deadline = Date.now() + duration;
  let timer: ReturnType<typeof setTimeout>;
  let checking = false;
  let observe = true;

  function stopReading() {
    observe = false;
    clearTimeout(timer);
    controller.abort();
    document.removeEventListener('visibilitychange', wake);
  }
  function ended() {
    stopReading();
    clearTimeout(expiry);
    notify('ended');
  }
  const expiry = setTimeout(ended, duration);
  function schedule() {
    timer = setTimeout(tick, 4_000);
  }
  async function tick() {
    if (!observe || checking) return;
    if (Date.now() >= deadline) { ended(); return; }
    if (document.hidden) return;
    checking = true;
    try {
      const result = await status(controller.signal);
      if (!observe) return;
      if (Date.now() >= deadline || result === 'ended') ended();
      else if (result === 'approved') { stopReading(); notify('approved'); }
      else schedule();
    } catch {
      if (observe) { stopReading(); notify('unavailable'); }
    } finally { checking = false; }
  }
  function wake() {
    if (!document.hidden) { clearTimeout(timer); void tick(); }
  }
  document.addEventListener('visibilitychange', wake);
  schedule();
  return () => { stopReading(); clearTimeout(expiry); };
}
