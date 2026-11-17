"""Three fixed ivory source profiles and closed output parsing; no runtime authority.

This module operates on retained bytes only. The owner proves source custody,
current lease, process completion, stable bounded output and aggregate admission.
A completed %exit is an evaluator refusal, not proof of its compilation stage.
"""
from __future__ import annotations
import hashlib
import json
import re

COMPOSITION_SHA256 = "29f23ddb8849c5b182fca693a993a0634463e12104b47433ba3525adf93dfe31"
COMPOSITION_BYTES = 240159
HELPER_PATH = "pkg/base-dev/lib/test.hoon"
HELPER_SHA256 = "55d5196a3a8dbd5323943c06f138c9b9aa8fd955506c4f4b14e5d56ff05abcc6"
MAX_SOURCE = 1048576
MAX_OUTPUT = 1000000
COMPILER_SOURCE = b"(invalid-unterminated\n"
COMPILER_SHA256 = "93861a0912003ecc017e98791b691937344580ec86980b12c1259e489f3ea89b"
TANG_SHA256 = "6ccdf445296a66cac869b95ff3a7d068421309cf7b541e2cf5adbc79589e0639"
BOOT = ("loom: mapped 512MB\nlite: arvo formula 4ce68411\n"
        "lite: core 641296f\nlite: final state 641296f\neval (run):")
EXIT_STDERR = BOOT + "\n\neval: bail: %exit"
# Exact nonfatal startup diagnostic from the pinned Vere under RLIMIT_CORE=0.
# Retain every original byte/hash; admit only these two complete envelopes.
CORE_LIMIT_WARNING = "boot: core limit: Invalid argument\n"
BOOT_DIAGNOSTICS = (BOOT, CORE_LIMIT_WARNING + BOOT)
EXIT_DIAGNOSTICS = (EXIT_STDERR, CORE_LIMIT_WARNING + EXIT_STDERR)
COMPILER_STDOUT = "/eval\n{1 22}\nsyntax error"
JOB_FIELDS = {"label", "kind", "source", "source_sha256", "timeout_seconds", "arms"}
SUITES = (('catalog',
  'e5ecacbc984ec26e9f3a5c859a76783debc382515681342065c57d9756321cf6',
  ('test-repository-catalog-two-repos-exact-inline-profile',
   'test-repository-catalog-typed-ids-never-infer-alias',
   'test-repository-catalog-retry-is-original-and-current-authorized',
   'test-repository-catalog-resolver-authority-cas-retirement',
   'test-repository-catalog-global-retained-capacity-no-eviction',
   'test-repository-catalog-closed-codec-and-receipt-closure')),
 ('import',
  '83becaaa829e8d77f19e2e3d70f26d51023b9ecd3e820c420625efd84371fb1b',
  ('test-repository-import-inline-exact-refs-reviews-uploads-and-alias',
   'test-repository-import-external-exact-promotion-and-snapshot',
   'test-repository-import-refuses-orphan-corrupt-and-cross-scope-tails',
   'test-repository-import-empty-and-full-pure-roundtrip')),
 ('authority',
  '28efeacc16ca0e1cee091726c95817b1b7972fecba97a0a5c1fc5542cafcdb7a',
  ('test-repository-authority-current-human-roles-and-two-repos',
   'test-repository-authority-nonhuman-and-unresolved-denied',
   'test-repository-authority-browser-possession-and-current-session',
   'test-repository-authority-binding-and-grant-changes-refuse-old-actors',
   'test-repository-authority-credentials-exact-scope-and-expiry',
   'test-repository-authority-retirement-and-lifecycle',
   'test-repository-authority-current-before-original-create-replay',
   'test-repository-authority-missing-and-forged-snapshot-boundaries')),
 ('store',
  '61c1d4c5bb5d3217735f9a808d7cf170cdb38ae209fa8e56333780ced212ccd4',
  ('test-repository-store-two-inline-current-scope',
   'test-repository-store-import-exact-mixed-four-roots',
   'test-repository-store-catalog-key-profile-and-epoch',
   'test-repository-store-object-journal-and-ref-integrity',
   'test-repository-store-review-build-cross-scope',
   'test-repository-store-upload-scope-and-lossless-import',
   'test-repository-store-external-closure-stays-legacy',
   'test-repository-store-current-access-not-old-history')))

MODEL_COMPOSITION_SHA256 = "c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6"
MODEL_COMPOSITION_BYTES = 110358
MODEL_SUITES = (('model-codec', '234f119ef4636c2cc4e9fcc3a1f9ba1d3f556c13b2d1d5cffa951f0492ffae03', ('test-model-codec-golden-reserve-and-derived-native-identity', 'test-model-codec-closed-parent-and-canonical-cas', 'test-model-codec-material-pins-and-exact-charge-reject-drift', 'test-model-codec-observation-absence-empty-and-binary-bytes', 'test-model-codec-parser-and-parent-bounds-do-not-expand', 'test-model-codec-real-linefeeds-and-supplementary-unicode')), ('model-reply', 'd9d3fdd036fcc869159a686bd96a35da6aa07c1c1bbf38b4481ed68b8920d8ed', ('test-model-reply-rebuilds-golden-proposal-from-original-bytes', 'test-model-reply-binary-utf8-duplicate-depth-and-size-refusals', 'test-model-reply-timing-exponents-and-reasoning-are-bounded', 'test-model-reply-refusal-incomplete-and-filter-never-propose-doc', 'test-model-reply-tool-model-and-usage-pins-reject-spoofs', 'test-model-reply-actual-linefeeds-and-supplementary-unicode')), ('model-turn-codec', '17bfc6d95c6fa975487ba893b8a873f08ece870c200c75b8249a3426699e6ed2', ('test-model-turn-codec-four-exact-parent-vectors', 'test-model-turn-codec-closed-canonical-claim-boundary', 'test-model-turn-codec-ids-digests-and-finite-uints', 'test-model-turn-codec-exact-answer-utf8-and-comment-bounds', 'test-model-turn-codec-five-child-identities-are-not-authority', 'test-model-turn-codec-escaped-limits-and-nested-shape-denials')))


DEBUG_COMPOSITION_SHA256 = "81085d13ec4a79a5b75f7e2bcaa4226eb48dd630e9d23e84af4068a3164b44c3"
DEBUG_COMPOSITION_BYTES = 54285
DEBUG_SUITES = (("catalog-debug", "22d1fbebf744e9a035bb5cc4322f77db3e3306e8c378dbf9b702a6efba99299b", SUITES[0][2]),)

def profile(composition_sha256):
    """Return only a source-owned closed profile; no caller-selected counts/paths."""
    _require(type(composition_sha256) is str, "Profile digest type")
    if composition_sha256 == COMPOSITION_SHA256:
        name, size, sources, libraries, arms, suites = ("repository/1", COMPOSITION_BYTES, 55, 50, 26, SUITES)
        paths = tuple("native/core/desk/tests/stead-repository-" + s[0] + ".hoon" for s in suites)
    elif composition_sha256 == MODEL_COMPOSITION_SHA256:
        name, size, sources, libraries, arms, suites = ("native-model-simple/1", MODEL_COMPOSITION_BYTES, 21, 17, 18, MODEL_SUITES)
        paths = tuple("native/core/desk/tests/stead-" + s[0] + ".hoon" for s in suites)
    elif composition_sha256 == DEBUG_COMPOSITION_SHA256:
        name, size, sources, libraries, arms, suites = ("repository-catalog-debug/1", DEBUG_COMPOSITION_BYTES, 55, 50, 6, DEBUG_SUITES)
        paths = ("native/core/desk/tests/stead-repository-catalog.hoon",)
    else:
        raise ValueError("Unknown fixed composition")
    return {"name": name, "composition_sha256": composition_sha256, "composition_bytes": size,
            "source_files": sources, "libraries": libraries, "positive_arms": arms,
            "jobs": len(suites) + 2, "suites": suites, "suite_paths": paths}


def job_profile(jobs):
    """Recheck the complete fixed job sequence; child report fields select nothing."""
    _require(type(jobs) is tuple, "Job sequence type")
    for digest in (COMPOSITION_SHA256, MODEL_COMPOSITION_SHA256, DEBUG_COMPOSITION_SHA256):
        selected = profile(digest)
        labels = ("compiler-control", "failing-tang-control") + tuple(s[0] for s in selected["suites"])
        if len(jobs) == selected["jobs"] and all(type(job) is dict for job in jobs) and tuple(job.get("label") for job in jobs) == labels:
            for job in jobs:
                _checked_job(job)
            return selected
    raise ValueError("Mixed, partial or unknown fixed job sequence")


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pin(data, pin):
    _require(type(data) is bytes and len(data) == pin["bytes"] and
             _sha(data) == pin["sha256"], "Source pin mismatch")


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "Duplicate composition field")
        value[key] = item
    return value


def _inventory(arms):
    return ("^-  (list [@ta @ta])\n:~  " + "\n    ".join(
        f"[(scot %tas %{arm}) (scot %ud (lent {arm}))]" for arm in arms) + "\n==\n").encode()


class _Composer:
    def __init__(self, files):
        self.files = files
        self.parts = []
        self.offsets = []
        self.size = 0
        self.line = 1

    def add(self, data, kind, **source):
        _require(type(data) is bytes and self.size + len(data) <= MAX_SOURCE,
                 "Composed source bound")
        row = {"kind": kind, "generated_start_byte": self.size,
               "generated_end_byte": self.size + len(data),
               "generated_start_line": self.line,
               "generated_newlines": data.count(b"\n"), **source}
        self.parts.append(data)
        self.offsets.append(row)
        self.size += len(data)
        self.line += data.count(b"\n")

    def source(self, path, header=""):
        data = self.files[path]
        declared = re.findall(rb"^/\+  [^\n]*\n", data, re.M)
        wanted = header.encode()
        _require(declared == ([wanted] if wanted else []), "Import header mismatch")
        if wanted:
            start = data.index(wanted)
            spans = ((0, start), (start + len(wanted), len(data)))
        else:
            spans = ((0, len(data)),)
        for start, end in spans:
            if start != end:
                self.add(data[start:end], "original-source", source=path,
                         source_start_byte=start, source_end_byte=end,
                         source_start_line=data[:start].count(b"\n") + 1)

    def finish(self):
        return b"".join(self.parts)


def _closure(names, imports):
    found = set()
    visiting = set()

    def visit(name):
        _require(name in imports and name not in visiting, "Unresolved or cyclic import")
        if name in found:
            return
        _require(len(visiting) < 50, "Import depth bound")
        visiting.add(name)
        for dependency in imports[name]:
            visit(dependency)
        visiting.remove(name)
        found.add(name)

    for name in names:
        visit(name)
    return found


def _job(label, kind, source, arms):
    return {"label": label, "kind": kind, "source": source,
            "source_sha256": _sha(source), "timeout_seconds": 85 if kind == "suite" else 15,
            "arms": tuple(arms)}


def jobs(files, composition_bytes):
    """Compose one of three exact retained profiles; original repository bytes select the original six jobs."""
    _require(type(files) is dict and type(composition_bytes) is bytes, "Input types")
    selected_profile = profile(_sha(composition_bytes))
    _require(len(composition_bytes) == selected_profile["composition_bytes"], "Composition pin mismatch")
    document = json.loads(composition_bytes, object_pairs_hook=_unique)
    sources = document["sources"]
    composition = document["composition"]
    helper = composition["test_helper"]
    _require(set(files) == set(sources) | {HELPER_PATH} and len(files) == selected_profile["source_files"],
             "Exact source inventory required")
    for path, pin in sources.items():
        _pin(files[path], pin)
    _pin(files[HELPER_PATH], helper)
    _require(helper["sha256"] == HELPER_SHA256 and helper["path"] == HELPER_PATH,
             "Test helper pin")
    for data in files.values():
        _require(len(data) <= MAX_SOURCE, "Individual source bound")
        data.decode("utf-8", errors="strict")
    order = composition["library_order"]
    imports = composition["imports"]
    aliases = None
    if selected_profile["composition_sha256"] == MODEL_COMPOSITION_SHA256:
        # The exact reviewed model map uses full paths and retains suite edges.
        # Build only a lossless local name view; never rewrite its pinned bytes.
        _require(all(type(path) is str and re.fullmatch(
            r"native/core/desk/lib/(stead-[a-z0-9-]+)\.hoon", path) for path in order),
            "Model library path form")
        aliases = {path: path.rsplit("/", 1)[1][:-5] for path in order}
        _require(len(aliases) == len(order) and len(set(aliases.values())) == len(order) and
                 set(imports) == set(order) | set(selected_profile["suite_paths"]) and
                 all(set(deps) <= set(order) for deps in imports.values()), "Model graph closure")
        imports = {aliases[path]: [aliases[dep] for dep in composition["imports"][path]]
                   for path in order}
        order = [aliases[path] for path in order]
    _require(len(order) == selected_profile["libraries"] and len(set(order)) == selected_profile["libraries"] and set(order) == set(imports),
             "Exact library order")
    seen = set()
    for name in order:
        _require(set(imports[name]) <= seen, "Import order is not topological")
        seen.add(name)
    tang = (b"=/  test\n" + files[HELPER_PATH] + b"\n=,  test\n"
            b"^-  (list [@ta @ta])\n"
            b":~  [(scot %tas %failure-control) (scot %ud (lent (expect !>(%.n))))]\n==\n")
    _require(_sha(tang) == TANG_SHA256, "Failing control pin")
    result = [_job("compiler-control", "compiler-control", COMPILER_SOURCE, ()),
              _job("failing-tang-control", "failing-tang-control", tang, ())]
    _require(len(composition["suites"]) == len(selected_profile["suites"]), "Exact suite count")
    for (label, expected_sha, arms), path, suite in zip(selected_profile["suites"], selected_profile["suite_paths"], composition["suites"]):
        _require(suite["path"] == path and tuple(suite["arms"]) == arms,
                 "Fixed suite inventory")
        observed = tuple(name.decode() for name in re.findall(
            rb"^\+\+  (test-[a-z0-9-]+)$", files[path], re.M))
        _require(observed == arms, "Test source inventory mismatch")
        declaration = suite["import_header"]
        _require(declaration.startswith("/+  *test, ") and declaration.endswith("\n"),
                 "Test import form")
        direct = declaration[len("/+  *test, "):-1].split(", ")
        declared_order = suite["transitive_library_order"]
        if aliases is not None:
            _require(composition["imports"][path] ==
                     ["native/core/desk/lib/" + name + ".hoon" for name in direct] and
                     all(name in aliases for name in declared_order), "Model suite import edges")
            declared_order = [aliases[name] for name in declared_order]
        needed = _closure(direct, imports)
        selected = [name for name in order if name in needed]
        _require(selected == declared_order and
                 len(selected) == suite["transitive_library_count"], "Suite import closure")
        paths = {f"native/core/desk/lib/{name}.hoon" for name in selected} | {path}
        _require(suite["source_files"] == {name: sources[name] for name in sorted(paths)},
                 "Suite source pins")
        built = _Composer(files)
        if selected_profile["composition_sha256"] == DEBUG_COMPOSITION_SHA256:
            built.add(b"!:\n", "fixed-debug-prefix")
        built.add(b"=/  test\n", "fixed-binding")
        built.source(HELPER_PATH)
        built.add(b"\n", "fixed-separator")
        for name in selected:
            library = f"native/core/desk/lib/{name}.hoon"
            header = composition["exact_import_headers"][library]
            parsed = header[len("/+  "):-1].split(", ") if header else []
            _require(parsed == imports[name], "Library dependency declaration")
            built.add(f"=/  {name}\n".encode(), "fixed-binding")
            built.source(library, header)
            built.add(b"\n", "fixed-separator")
        built.add(b"=,  test\n=>\n", "fixed-test-binding")
        built.source(path, declaration)
        built.add(b"\n", "fixed-separator")
        expression = _inventory(arms)
        _pin(expression, suite["inventory_expression"])
        built.add(expression, "fixed-inventory-expression")
        source = built.finish()
        _pin(source, suite["composed_source"])
        _require(_sha(source) == expected_sha and built.offsets == suite["source_offsets"],
                 "Generated source or mapping mismatch")
        result.append(_job(label, "suite", source, arms))
    return tuple(result)


def _checked_job(job):
    _require(type(job) is dict and set(job) == JOB_FIELDS, "Closed job shape")
    label = job["label"]
    _require(type(label) is str, "Job label type")
    specs = {name: ("suite", sha, arms, 85) for name, sha, arms in SUITES + MODEL_SUITES + DEBUG_SUITES}
    specs.update({"compiler-control": ("compiler-control", COMPILER_SHA256, (), 15),
                  "failing-tang-control": ("failing-tang-control", TANG_SHA256, (), 15)})
    _require(label in specs, "Unknown job")
    kind, sha, arms, timeout = specs[label]
    _require(type(job["source"]) is bytes and 0 < len(job["source"]) <= MAX_SOURCE and
             _sha(job["source"]) == sha and job["source_sha256"] == sha and
             job["kind"] == kind and type(job["arms"]) is tuple and job["arms"] == arms and
             type(job["timeout_seconds"]) is int and job["timeout_seconds"] == timeout,
             "Job identity mismatch")


def _text(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_OUTPUT, "Output byte bound")
    text = raw.decode("utf-8", errors="strict")
    text = re.sub(r"\x1b\[[0-9;]{0,32}m", "", text).replace("\r\n", "\n")
    _require(all((ord(c) >= 32 and not 127 <= ord(c) <= 159) or c in "\t\n" for c in text),
             "Unknown output control character")
    return text.strip(" \t\n")


def _rows(text, names):
    # No free-form diagnostic stripping: exactly one complete printed row list.
    if text.startswith("~[") and text.endswith("]"):
        inner = text[2:-1]
    elif text.startswith("[") and text.endswith("]") and text[1:-1].rstrip(" \t\n").endswith("~"):
        inner = text[1:-1].rstrip(" \t\n")[:-1]
    else:
        raise ValueError("Incomplete row list")
    pattern = re.compile(r"\[[ \t\n]*~\.([a-z0-9-]+)[ \t\n]+~\.(0|[1-9][0-9]{0,2}(?:\.[0-9]{3}){0,2})[ \t\n]*\]")
    matches = list(pattern.finditer(inner))
    _require(len(matches) == len(names) and not pattern.sub("", inner).strip(" \t\n"),
             "Incomplete or extra row content")
    observed = tuple(item.group(1) for item in matches)
    _require(observed == names, "Arm order or identity mismatch")
    rows = []
    for item in matches:
        count = int(item.group(2).replace(".", ""))
        _require(count <= MAX_OUTPUT, "Tang count bound")
        rows.append({"name": item.group(1), "tang_length": count, "passed": count == 0})
    return tuple(rows)


def observe(job, exit_code, stdout, stderr):
    """Parse complete retained output. The caller separately proves completion."""
    _checked_job(job)
    _require(type(exit_code) is int and exit_code == 0, "Evaluator exit is not exact zero")
    out, err = _text(stdout), _text(stderr)
    kind = job["kind"]
    compiler_failure = False
    arms = ()
    if kind == "compiler-control":
        _require(out == COMPILER_STDOUT and err in EXIT_DIAGNOSTICS, "Compiler control mismatch")
        status = "pass"
    elif kind == "failing-tang-control":
        _require(err in BOOT_DIAGNOSTICS, "Failing-tang evaluator refusal")
        rows = _rows(out, ("failure-control",))
        _require(rows[0]["tang_length"] > 0, "Failing tang did not fail")
        status = "pass"
    elif err in EXIT_DIAGNOSTICS:
        # This proves only a completed evaluator %exit. A runtime assertion may
        # also produce it. No arm verdict or stage-specific claim is invented.
        _require(bool(out), "Missing evaluator failure trace")
        compiler_failure = True
        status = "fail"
    else:
        _require(err in BOOT_DIAGNOSTICS, "Unknown evaluator diagnostics")
        arms = _rows(out, job["arms"])
        status = "pass" if all(row["passed"] for row in arms) else "fail"
    return {"label": job["label"], "kind": kind, "status": status, "exit_code": exit_code,
            "arms": arms, "stdout_sha256": _sha(stdout), "stdout_bytes": len(stdout),
            "stderr_sha256": _sha(stderr), "stderr_bytes": len(stderr),
            "compiler_failure": compiler_failure}
