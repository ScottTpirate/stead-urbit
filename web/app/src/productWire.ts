// Bounded string/object JSON for the reserved product protocol. Arrays,
// duplicate keys, non-string scalars, NUL and lone surrogates are never admitted.
import {canonical} from './protocol';
export type ProductJSON = string | {[key: string]: ProductJSON};
export class ProductProtocolError extends Error {
  constructor(readonly code: 'invalid_request' | 'invalid_response' | 'unsupported_profile' = 'invalid_request') { super(code); }
}
export const byteLength = (text: string) => new TextEncoder().encode(text).length;
export function protocolText(value: unknown): asserts value is string {
  if (typeof value !== 'string') throw new ProductProtocolError();
  for (const character of value) {
    const point = character.codePointAt(0)!;
    if (point === 0 || (point >= 0xd800 && point <= 0xdfff)) throw new ProductProtocolError();
  }
}
export function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || ![null, Object.prototype].includes(Object.getPrototypeOf(value))) throw new ProductProtocolError();
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)!;
    if (typeof key !== 'string' || !descriptor.enumerable || !('value' in descriptor)) throw new ProductProtocolError();
  }
  return value as Record<string, unknown>;
}
export function keys(value: Record<string, unknown>, names: readonly string[]) {
  if (Object.keys(value).length !== names.length || names.some(name => !Object.hasOwn(value, name))) throw new ProductProtocolError();
}
export function freeze<T>(value: T): T {
  if (value && typeof value === 'object') { for (const child of Object.values(value)) freeze(child); Object.freeze(value); }
  return value;
}
export function productJSON(value: unknown, limits = {bytes: 65536, depth: 4, keys: 16}): string {
  function check(item: unknown, depth: number): void {
    if (typeof item === 'string') { if (item.length > limits.bytes) throw new ProductProtocolError(); protocolText(item); return; }
    const row = object(item);
    if (depth > limits.depth || Object.keys(row).length > limits.keys) throw new ProductProtocolError();
    for (const [key, child] of Object.entries(row)) { protocolText(key); check(child, depth + 1); }
  }
  check(value, 1);
  const raw = canonical(value);
  if (byteLength(raw) > limits.bytes) throw new ProductProtocolError();
  return raw;
}
export function parseProductJSON(raw: string, limits = {bytes: 65536, depth: 4, keys: 16}): Record<string, unknown> {
  if (typeof raw !== 'string' || raw.length > limits.bytes) throw new ProductProtocolError();
  protocolText(raw);
  if (byteLength(raw) > limits.bytes) throw new ProductProtocolError();
  let offset = 0;
  const space = () => { while (/[\t\n\r ]/u.test(raw[offset] ?? '\u0000')) offset++; };
  function string(): string {
    const start = offset++;
    while (offset < raw.length) {
      const character = raw[offset++];
      if (character === '\\') { offset++; continue; }
      if (character === '"') {
        let value: unknown;
        try { value = JSON.parse(raw.slice(start, offset)); } catch { throw new ProductProtocolError(); }
        protocolText(value); return value;
      }
    }
    throw new ProductProtocolError();
  }
  function value(depth: number): ProductJSON {
    space();
    if (raw[offset] === '"') return string();
    if (raw[offset++] !== '{' || depth > limits.depth) throw new ProductProtocolError();
    const result: {[key: string]: ProductJSON} = Object.create(null);
    space(); if (raw[offset] === '}') { offset++; return result; }
    let count = 0;
    while (offset < raw.length) {
      space(); if (raw[offset] !== '"' || ++count > limits.keys) throw new ProductProtocolError();
      const key = string(); if (Object.hasOwn(result, key)) throw new ProductProtocolError();
      space(); if (raw[offset++] !== ':') throw new ProductProtocolError();
      result[key] = value(depth + 1); space();
      const separator = raw[offset++];
      if (separator === '}') return result;
      if (separator !== ',') throw new ProductProtocolError();
    }
    throw new ProductProtocolError();
  }
  const parsed = object(value(1)); space();
  if (offset !== raw.length) throw new ProductProtocolError();
  return parsed;
}
