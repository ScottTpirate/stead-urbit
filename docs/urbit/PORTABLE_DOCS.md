# Recover an exported Docs history

`scripts/urbit/portable_docs.py` packages an already exported bare SHA-1
Docs repository. It follows the chosen head through its commit, tree and
Markdown objects and verifies every Git object ID. The archive includes
the project and collection IDs, the head, and the exact object bytes.
Only the selected history goes into the archive.

Use the path and exact head from a previously authorized export. The
project and container labels supplied to this command do not grant access.
Use a private directory and retain the archive's reported SHA-256 separately.

```sh
mkdir -m 700 /path/to/private-recovery
python3 scripts/urbit/portable_docs.py create /path/to/export.git /path/to/private-recovery/docs.json \
  --project PROJECT_UUID --container CONTAINER_UUID --head EXACT_COMMIT
python3 scripts/urbit/portable_docs.py restore /path/to/private-recovery/docs.json /path/to/private-recovery \
  --sha256 RECORDED_DIGEST
```

Restore creates a new bare repository in a unique directory. It rejects
unreachable objects, wrong types, unsupported tree paths, inconsistent hashes,
and oversized input. It checks every recovered object with stock Git and runs
`git fsck --full --strict`. The archive and repository contain document content
and should be stored and transferred using the same controls as the export.

This recovers a Docs collection's Git history and Markdown. Work items,
membership, policy, event history, and the live authority still require the
project restore workflow. The command never boots an Urbit ship. SHA-256
verification checks integrity against a trusted digest. The digest itself
does not attest who authorized the original export.
