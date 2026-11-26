"""Resolve operator-configured agent runtimes to pinned model connections."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import model_connections as model


MAX_BYTES = 64 * 1024
BINDING_FIELDS = ('home', 'project_id', 'definition_id', 'definition_revision',
                  'runtime_id', 'runtime_revision', 'runtime_policy_digest')
REFERENCE_FIELDS = ('connection_id', 'connection_revision')


def binding_key(value):
    model.text(value['home'], 128, nonempty=True, label=True)
    for field in ('project_id', 'definition_id', 'runtime_id'):
        model.uuid(value[field])
    for field in ('definition_revision', 'runtime_revision'):
        model.uint(value[field], positive=True)
    model.digest(value['runtime_policy_digest'])
    return tuple(value[field] for field in BINDING_FIELDS)


class ModelCatalog:
    """One validated operator snapshot. Missing and ambiguous bindings fail closed."""

    def __init__(self, raw):
        data = model.closed(model.decode(raw, MAX_BYTES), {'protocol', 'connections', 'bindings'})
        model.require(data['protocol'] == 'stead.model-catalog/1', 'unsupported_catalog')
        connections, bindings = data['connections'], data['bindings']
        model.require(type(connections) is list and len(connections) <= 32, 'connection_count')
        model.require(type(bindings) is list and len(bindings) <= 64, 'binding_count')
        specs = {}
        for entry in connections:
            spec = model.connection(model.canonical(entry))
            ref = (entry['connection_id'], entry['revision'])
            model.require(ref not in specs, 'duplicate_connection_revision')
            specs[ref] = spec
        self._bindings = {}
        for binding in bindings:
            model.closed(binding, BINDING_FIELDS + REFERENCE_FIELDS)
            key = binding_key(binding)
            ref = (model.uuid(binding['connection_id']), binding['connection_revision'])
            model.uint(ref[1], positive=True)
            model.require(ref in specs, 'missing_connection_revision')
            model.require(key not in self._bindings, 'ambiguous_runtime_binding')
            self._bindings[key] = specs[ref]

    def inventory(self):
        """Return safe operator labels and pins. Endpoints and auth are omitted."""
        for key, spec in sorted(self._bindings.items()):
            value = spec.value()
            yield {**dict(zip(BINDING_FIELDS, key)), 'connection_id': value['connection_id'],
                   'connection_revision': value['revision'], 'connection_digest': spec.sha256,
                   'display_name': value['display_name'], 'model': value['model'],
                   'placement': value['endpoint']['placement']}

    def prepare(self, scope, turn, instructions, messages, tools, *, prior_digest=None):
        """Build the existing journal input for an already pinned Run scope."""
        model.closed(scope, model.SCOPE_FIELDS)
        key = binding_key(scope)
        model.require(key in self._bindings, 'runtime_binding_unavailable')
        spec = self._bindings[key]
        request = model.prepare_chat(spec, scope, turn, instructions, messages, tools,
                                     prior_digest=prior_digest)
        return spec, request


def main(argv=None):
    parser = argparse.ArgumentParser(description="List configured agent runtimes and their model pins.")
    parser.add_argument('catalog', type=Path, help="operator model-catalog JSON file")
    args = parser.parse_args(argv)
    try:
        with args.catalog.open('rb') as source:
            catalog = ModelCatalog(source.read(MAX_BYTES + 1))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Cannot read model catalog: {error}\n")
    json.dump(list(catalog.inventory()), sys.stdout, indent=2, ensure_ascii=True)
    print()


if __name__ == '__main__':
    main()
