"""Fixed T04 ivory composition and closed output parsing; no runtime authority.

This module operates on retained bytes only. The owner proves source custody,
current lease, process completion, stable bounded output and aggregate admission.
A completed %exit is an evaluator refusal, not proof of its compilation stage.
"""
from __future__ import annotations
import hashlib
import json
import re

COMPOSITION_SHA256 = "3d42cb1788ddbe5bdf6f9643bbbe4d2bfa7245a24431b851ef247c525c9ead72"
COMPOSITION_BYTES = 240147
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
COMPILER_STDOUT = "/eval\n{1 22}\nsyntax error"
JOB_FIELDS = {"label", "kind", "source", "source_sha256", "timeout_seconds", "arms"}
SUITES = (('catalog',
  '4c970d23b0faace637cfc16f65ea519270942dcb77d37bcdc3950ad1e28b7eca',
  ('test-repository-catalog-two-repos-exact-inline-profile',
   'test-repository-catalog-typed-ids-never-infer-alias',
   'test-repository-catalog-retry-is-original-and-current-authorized',
   'test-repository-catalog-resolver-authority-cas-retirement',
   'test-repository-catalog-global-retained-capacity-no-eviction',
   'test-repository-catalog-closed-codec-and-receipt-closure')),
 ('import',
  '904f373104c1a388105864b8d38ed17001666a9b2fbef40eb6eb30bc033372f8',
  ('test-repository-import-inline-exact-refs-reviews-uploads-and-alias',
   'test-repository-import-external-exact-promotion-and-snapshot',
   'test-repository-import-refuses-orphan-corrupt-and-cross-scope-tails',
   'test-repository-import-empty-and-full-pure-roundtrip')),
 ('authority',
  'c13051201e7ee497c29d845b7a4db97fd6a99a8cb07dd97047eef1e3983ba3bc',
  ('test-repository-authority-current-human-roles-and-two-repos',
   'test-repository-authority-nonhuman-and-unresolved-denied',
   'test-repository-authority-browser-possession-and-current-session',
   'test-repository-authority-binding-and-grant-changes-refuse-old-actors',
   'test-repository-authority-credentials-exact-scope-and-expiry',
   'test-repository-authority-retirement-and-lifecycle',
   'test-repository-authority-current-before-original-create-replay',
   'test-repository-authority-missing-and-forged-snapshot-boundaries')),
 ('store',
  'd281c5ebf92d05f94cab6c0c7acbdc50962710ebcce9c5fb141806b0862ce656',
  ('test-repository-store-two-inline-current-scope',
   'test-repository-store-import-exact-mixed-four-roots',
   'test-repository-store-catalog-key-profile-and-epoch',
   'test-repository-store-object-journal-and-ref-integrity',
   'test-repository-store-review-build-cross-scope',
   'test-repository-store-upload-scope-and-lossless-import',
   'test-repository-store-external-closure-stays-legacy',
   'test-repository-store-current-access-not-old-history')))


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
    """Compose exactly the reviewed six jobs, with no caller-selected expression."""
    _require(type(files) is dict and type(composition_bytes) is bytes, "Input types")
    _require(len(composition_bytes) == COMPOSITION_BYTES and
             _sha(composition_bytes) == COMPOSITION_SHA256, "Composition pin mismatch")
    document = json.loads(composition_bytes, object_pairs_hook=_unique)
    sources = document["sources"]
    composition = document["composition"]
    helper = composition["test_helper"]
    _require(set(files) == set(sources) | {HELPER_PATH} and len(files) == 55,
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
    _require(len(order) == 50 and len(set(order)) == 50 and set(order) == set(imports),
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
    _require(len(composition["suites"]) == 4, "Exact suite count")
    for (label, expected_sha, arms), suite in zip(SUITES, composition["suites"]):
        path = f"native/core/desk/tests/stead-repository-{label}.hoon"
        _require(suite["path"] == path and tuple(suite["arms"]) == arms,
                 "Fixed suite inventory")
        observed = tuple(name.decode() for name in re.findall(
            rb"^\+\+  (test-[a-z0-9-]+)$", files[path], re.M))
        _require(observed == arms, "Test source inventory mismatch")
        declaration = suite["import_header"]
        _require(declaration.startswith("/+  *test, ") and declaration.endswith("\n"),
                 "Test import form")
        direct = declaration[len("/+  *test, "):-1].split(", ")
        needed = _closure(direct, imports)
        selected = [name for name in order if name in needed]
        _require(selected == suite["transitive_library_order"] and
                 len(selected) == suite["transitive_library_count"], "Suite import closure")
        paths = {f"native/core/desk/lib/{name}.hoon" for name in selected} | {path}
        _require(suite["source_files"] == {name: sources[name] for name in sorted(paths)},
                 "Suite source pins")
        built = _Composer(files)
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
    specs = {name: ("suite", sha, arms, 85) for name, sha, arms in SUITES}
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
        _require(out == COMPILER_STDOUT and err == EXIT_STDERR, "Compiler control mismatch")
        status = "pass"
    elif kind == "failing-tang-control":
        _require(err == BOOT, "Failing-tang evaluator refusal")
        rows = _rows(out, ("failure-control",))
        _require(rows[0]["tang_length"] > 0, "Failing tang did not fail")
        status = "pass"
    elif err == EXIT_STDERR:
        # This proves only a completed evaluator %exit. A runtime assertion may
        # also produce it. No arm verdict or stage-specific claim is invented.
        _require(bool(out), "Missing evaluator failure trace")
        compiler_failure = True
        status = "fail"
    else:
        _require(err == BOOT, "Unknown evaluator diagnostics")
        arms = _rows(out, job["arms"])
        status = "pass" if all(row["passed"] for row in arms) else "fail"
    return {"label": job["label"], "kind": kind, "status": status, "exit_code": exit_code,
            "arms": arms, "stdout_sha256": _sha(stdout), "stdout_bytes": len(stdout),
            "stderr_sha256": _sha(stderr), "stderr_bytes": len(stderr),
            "compiler_failure": compiler_failure}
