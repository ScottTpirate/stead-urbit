// Public wire helpers: UUIDv7 and the frozen command/3 hash domain.
export function newId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  const now = Date.now();
  if (!Number.isSafeInteger(now) || now < 0 || now >= 2 ** 48) throw new Error('Invalid identity clock');
  let time = BigInt(now);
  for (let index = 5; index >= 0; index--) { bytes[index] = Number(time & 255n); time >>= 8n; }
  bytes[6] = (bytes[6]! & 15) | 112;
  bytes[8] = (bytes[8]! & 63) | 128;
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
export function canonical(value: unknown): string {
  if (typeof value === 'string') {
    for (const character of value) {
      const point = character.codePointAt(0)!;
      if (point === 0 || (point >= 0xd800 && point <= 0xdfff)) throw new Error('Invalid protocol text');
    }
    return JSON.stringify(value);
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid protocol value');
  const object = value as Record<string, unknown>;
  return '{' + Object.keys(object).sort().map(key => JSON.stringify(key) + ':' + canonical(object[key])).join(',') + '}';
}
export async function commandDigest(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode('stead.command/3\0' + canonical(value));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
