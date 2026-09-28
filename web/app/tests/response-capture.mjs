// Evidence capture has a deliberate admission boundary and awaited failures.
export class ResponseCapture {
  #accepting = true;
  #pending = new Set();
  #failures = 0;
  get accepting() { return this.#accepting; }
  get pending() { return this.#pending.size; }
  get failures() { return this.#failures; }
  track(operation) {
    if (!this.#accepting) return false;
    const task = Promise.resolve().then(operation).catch(() => { this.#failures++; })
      .then(() => { this.#pending.delete(task); });
    this.#pending.add(task);
    return true;
  }
  async drain() { await Promise.all([...this.#pending]); }
  async close() {
    this.#accepting = false;
    await this.drain();
    return {complete: true, failures: this.#failures};
  }
}
