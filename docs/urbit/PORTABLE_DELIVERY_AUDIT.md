# Portable Code delivery audit

An authenticated maintainer can capture one repository's retained delivery
records through the Home. Every page is independently authorized. The fixed
page size is four. A continuation carries the first page's snapshot digest
and its exact next offset. A changed audit projection rejects the continuation.

The audit contains current refs and protection, proposal revisions and
approvals, accepted ref receipts and their ordered changes, recorded merges,
build states with current or final lease information, retained artifact bytes,
release intents, and saved delegation states. Ref names use lowercase hex
because original Git refs can contain non-UTF-8 bytes. The artifact field
retains exact bytes in canonical Base64, bounded to 8 KiB per build.

The snapshot is SHA-256 over the ASCII protocol name
`stead.code-delivery-audit/1`, one zero byte, the canonical header with a final
LF, and every canonical JSON record with its final LF. The header binds the
Home, project, repository, authority epoch, repository revision, and count.
The file verifier checks this transcript, replays ref receipts, verifies
proposal, approval, build, release, and delegation relationships, and hashes
the retained artifact bytes independently.

Run capture with a private current maintainer session and a private output
directory. Supply the verified local CA for synthetic fake-ship fixtures.

```sh
python3 -B scripts/urbit/portable_delivery.py capture \
  --session-file "$session" --ca-file "$ca" --project "$project" --output "$audit"
python3 -B scripts/urbit/portable_delivery.py verify "$audit" --sha256 "$trusted_sha"
```

Retain the printed file SHA-256 separately. Neither digest is a signed
authority assertion. The artifact contains private project data. The export
excludes membership bindings, credentials, keys, uploads, editable Work text,
and source Git objects. Superseded build attempts are outside the saved
delivery profile. Git objects and Work content have separate portable
formats. The audit is for inspection and verification and carries no
permission or executable authority restore.
