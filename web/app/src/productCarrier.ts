// A partial successor capability set must never select the legacy Work writer.
export type ProductCarrierMode = Readonly<{kind: 'legacy' | 'native-human-doc' | 'unsupported'}>;
const successor = ['product_profile', 'work_commands', 'work_queries', 'doc_change_commands', 'doc_change_queries', 'refresh'];
const product = {
  protocol: 'stead.capabilities/3', profile: 'configured-team',
  commands: 'stead.command/3', queries: 'stead.query/3', authentication: 'native-approved-browser/1',
  max_request_bytes: '65536', max_response_bytes: '262144', page_size: '20', runtime: 'isolated-fake',
  product_profile: 'native-human-doc/1', work_commands: 'stead.command/4', work_queries: 'stead.query/4',
  doc_change_commands: 'stead.doc-change/1', doc_change_queries: 'stead.doc-change-query/1', refresh: 'explicit/1',
} as const;
export function productCarrierMode(value: Readonly<Record<string, string>>): ProductCarrierMode {
  if (value.protocol !== product.protocol || value.profile !== product.profile) return Object.freeze({kind: 'unsupported'});
  if (!successor.some(key => Object.hasOwn(value, key))) return Object.freeze({kind: 'legacy'});
  if (Object.keys(value).length !== Object.keys(product).length
    || Object.entries(product).some(([key, expected]) => value[key] !== expected)) return Object.freeze({kind: 'unsupported'});
  return Object.freeze({kind: 'native-human-doc'});
}
