# Public v2 SDK package — preview 0.1.0

This is the first implementation increment of URB-180 / issue #21. It packages
four pinned public Hoon files in a `desk-dev` directory:

- `lib/stead-codec.hoon`: bounded command codec and receipt validation helpers.
- `lib/stead-delivery.hoon`: finite ACK/fact/kick collection reducer.
- `mar/stead-command-2.hoon`: raw command transport mark.
- `mar/stead-result-2.hoon`: raw result transport mark.

The marks carry cords. Authoritative validation and permissions remain at the
home's final business boundary. An ACK is transport receipt; an accepted business
receipt is a separate result. Parsing or collecting a result grants no authority.
The codec retains command/1 parsing for historical replay; new mutations use
command/2. Command parsing is bounded at 65,536 bytes and result parsing at
262,144 bytes. The authority still validates current identity, grant, epoch,
scope and revision.

The package is a library fragment, not an installable application desk. Its
manifest pins Kelvin 408, runtime 4.6, source identities, all payload digests and
the packager digest. A consumer must supply its own reviewed application,
appropriate `sys.kelvin`, dependencies and installation metadata. This increment
does not compile an independent consumer from the archive, expose an employee
API, negotiate peer versions or implement browser sessions. Those remain #21
and the following Phase 2 work. Phase 1 compiled these library bytes inside its
own native harness; that is not independent SDK-consumer qualification.

From a checkout, build and verify without starting ships:

```sh
mkdir -p .runtime/sdk
python3 scripts/package_sdk.py build --output .runtime/sdk/stead-sdk-v2.tar
python3 scripts/package_sdk.py verify --archive .runtime/sdk/stead-sdk-v2.tar
```

The output must be new; the command refuses replacement of an existing file.
Verification compares every archive byte to the canonical package derived from
the checkout's reviewed `sdk/export-lock.json`. It never extracts or executes
the supplied archive. This verifies integrity relative to that checkout, not a
publisher signature, native conformance or deployment approval. Archives use
fixed ordering, timestamps, ownership and permissions, so identical inputs and
packager bytes produce identical archives across local directories.

The fixed export list excludes the owner-only fixture client, application state,
home implementation, administrative wires and the fixture API specification.
Adding files or changing exported bytes requires a reviewed lock/code change;
the builder never discovers exports by recursively copying the native desk.
The source baseline is `dd0e8c0ce8d1d00f15de6b07e2e26d368c5c3774` for the four
Hoon files and preserved license notices. No production ship or credentials are
included.

The root Apache license and complete third-party notices travel with the package,
including the Urbit MIT notice for the codec's parser lineage. Their historical
entries do not constitute new dependency adoption. Distribution follows the
public developer-file pattern described in the official Urbit distribution
[documentation](https://docs.urbit.org/build-on-urbit/userspace/dist). A complete
release desk, independent client, update/recovery tests and release channels
remain later increments.
