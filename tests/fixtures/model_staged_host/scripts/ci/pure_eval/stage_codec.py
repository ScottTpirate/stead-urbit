"""Fixed model-codec phase boundaries on the original ivory evaluator.

There is no live SLOG channel in this evaluator. Each observed boundary is the
complete result of its own source-pinned process. Earlier work is repeated;
these probes isolate cost without claiming a guaranteed performance improvement.
Mugs are diagnostic consistency values, not cryptographic source custody.
"""
from __future__ import annotations
import hashlib
import json
import re

PROFILE_NAME = "native-model-codec-staged/1"
COMPOSITION_SHA256 = 'cbfd2cc91e2153cac9b4cb8c02b15bd1200ebf8fa1d58e2f849ec4ebb8b19561'
COMPOSITION_BYTES = 119574
BASE_COMPOSITION_SHA256 = "c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6"
BASE_COMPOSITION_BYTES = 110358
ORIGINAL_SUITE_SHA256 = "234f119ef4636c2cc4e9fcc3a1f9ba1d3f556c13b2d1d5cffa951f0492ffae03"
ARM = "test-model-codec-golden-reserve-and-derived-native-identity"
LABELS = ("model-codec-stage-core", "model-codec-stage-mint", "model-codec-stage-run")
BOUNDARIES = ("core-ready", "first-arm-minted", "first-arm-ran")
SUITE_PATH = "native/core/desk/tests/stead-model-codec.hoon"
SOURCE_SHA256 = ('f73c6bdbc87a22b6628af19fa93d2076fb0b9fe31c27e8d7c5164682075fa810', '650cbb24fe1ba8d1e101e5f942fd7cfa0da12833e1d0a0e66764ae480c77d7ed', '07ddac5dad80084e536d840c864e990a5e2dd8e48d181146aaea719537c3d2f0')
SUITES = tuple((label, sha, (ARM,) if index == 2 else ())
               for index, (label, sha) in enumerate(zip(LABELS, SOURCE_SHA256)))
MAX_SOURCE = 1048576
MAX_OUTPUT = 1000000
MAX_MUG = 2147483647
STAGE_FIELDS = {"boundary", "core_mug", "formula_mug"}


def require(ok):
    if not ok:
        raise ValueError("Fixed staged evaluator refusal")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def profile():
    return {"name": PROFILE_NAME, "composition_sha256": COMPOSITION_SHA256,
            "composition_bytes": COMPOSITION_BYTES, "source_files": 21,
            "libraries": 17, "positive_arms": 1, "jobs": 5,
            "suites": SUITES, "suite_paths": (SUITE_PATH,) * 3}


def core_source(original, suite, test_raw):
    """Remove the old result inventory and its one test-core application only."""
    require(type(original) is bytes and sha(original) == ORIGINAL_SUITE_SHA256)
    require(type(test_raw) is bytes and type(suite) is dict)
    header = suite["import_header"].encode()
    require(test_raw.count(header) == 1)
    body = test_raw.replace(header, b"", 1)
    inventory = ("^-  (list [@ta @ta])\n:~  " + "\n    ".join(
        f"[(scot %tas %{name}) (scot %ud (lent {name}))]" for name in suite["arms"]) + "\n==\n").encode()
    suffix = b"=,  test\n=>\n" + body + b"\n" + inventory
    require(original.endswith(suffix))
    return original[:-len(suffix)] + b"=,  test\n" + body + b"\n"


def source(core, index):
    require(type(core) is bytes and type(index) is int and 0 <= index <= 2)
    # Capture the original evaluator subject before adding wrapper faces. The
    # dynamic compilation receives exactly this vase, never wrapper locals.
    digits = format(int.from_bytes(core, "little"), "x")
    first = len(digits) % 4 or 4
    literal = digits[:first] + "".join("." + digits[i:i + 4] for i in range(first, len(digits), 4))
    prefix = ("=/  original-vase=vase  !>(.)\n"
              "=/  source=@t\n  ^-  @\n  0x" + literal + "\n"
              "=/  core=vase  (slap original-vase (rain /eval source))\n")
    mint = ("=/  formula=nock\n"
            "  q:(~(mint ut p.core) p:!>(*tang) [%limb %" + ARM + "])\n")
    rows = ["[~.stage-core (scot %ud (mug core))]"]
    if index:
        prefix += mint
        rows.append("[~.stage-mint (scot %ud (mug formula))]")
    if index == 2:
        prefix += "=/  result=tang  ;;(tang .*(q.core formula))\n"
        rows.append("[~." + ARM + " (scot %ud (lent result))]")
    raw = (prefix + "^-  (list [@ta @ta])\n:~  " + "\n    ".join(rows) + "\n==\n").encode()
    require(0 < len(raw) <= MAX_SOURCE)
    return raw


def jobs(files, composition, ordinary_jobs):
    require(type(composition) is bytes and len(composition) == COMPOSITION_BYTES
            and sha(composition) == COMPOSITION_SHA256)
    document = json.loads(composition, object_pairs_hook=unique)
    require(set(document) == {"protocol", "base_composition", "core_source", "stages"}
            and document["protocol"] == "stead.model-codec-staged-composition/1")
    require(type(document["base_composition"]) is str)
    base = document["base_composition"].encode()
    require(len(base) == BASE_COMPOSITION_BYTES and sha(base) == BASE_COMPOSITION_SHA256)
    # The existing composer independently rechecks all21 original source pins,
    # every import edge/offset and all original six arm names. No new importer.
    original = ordinary_jobs(files, base)
    require(type(original) is tuple and len(original) == 5)
    base_doc = json.loads(base, object_pairs_hook=unique)
    core = core_source(original[2]["source"], base_doc["composition"]["suites"][0], files[SUITE_PATH])
    require(document["core_source"] == {"bytes": len(core), "sha256": sha(core)})
    require(type(document["stages"]) is list and len(document["stages"]) == 3)
    result = list(original[:2])
    for index, (label, expected, arms) in enumerate(SUITES):
        raw = source(core, index)
        require(sha(raw) == expected and document["stages"][index] == {
            "label": label, "boundary": BOUNDARIES[index], "bytes": len(raw),
            "sha256": expected, "arms": list(arms)})
        result.append({"label": label, "kind": "suite", "source": raw,
                       "source_sha256": expected, "timeout_seconds": 85, "arms": arms})
    return tuple(result)


def rows(text, names):
    if text.startswith("~[") and text.endswith("]"):
        inner = text[2:-1]
    elif text.startswith("[") and text.endswith("]") and text[1:-1].rstrip(" \t\n").endswith("~"):
        inner = text[1:-1].rstrip(" \t\n")[:-1]
    else:
        raise ValueError("Incomplete staged row list")
    pattern = re.compile(r"\[[ \t\n]*~\.([a-z0-9-]+)[ \t\n]+~\.(0|[1-9][0-9]{0,2}(?:\.[0-9]{3}){0,3})[ \t\n]*\]")
    found = list(pattern.finditer(inner))
    require(tuple(item.group(1) for item in found) == names
            and not pattern.sub("", inner).strip(" \t\n"))
    values = tuple(int(item.group(2).replace(".", "")) for item in found)
    require(all(value <= (MAX_OUTPUT if name == ARM else MAX_MUG)
                for name, value in zip(names, values)))
    return values


def observe(job, exit_code, stdout, stderr, text, boots, exits):
    require(type(exit_code) is int and exit_code == 0)
    index = LABELS.index(job["label"])
    out, err = text(stdout), text(stderr)
    arms, stage, compiler_failure = (), None, False
    if err in exits:
        require(bool(out))
        status, compiler_failure = "fail", True
    else:
        require(err in boots)
        names = ("stage-core",) + (("stage-mint",) if index else ()) + ((ARM,) if index == 2 else ())
        values = rows(out, names)
        stage = {"boundary": BOUNDARIES[index], "core_mug": values[0],
                 "formula_mug": values[1] if index else None}
        if index == 2:
            arms = ({"name": ARM, "tang_length": values[2], "passed": values[2] == 0},)
        status = "pass" if not arms or arms[0]["passed"] else "fail"
    return {"label": job["label"], "kind": job["kind"], "status": status,
            "exit_code": exit_code, "arms": arms, "stdout_sha256": sha(stdout),
            "stdout_bytes": len(stdout), "stderr_sha256": sha(stderr),
            "stderr_bytes": len(stderr), "compiler_failure": compiler_failure, "stage": stage}


def validate_records(records):
    """Owner calls after independently recomputing each complete observation."""
    require(type(records) is list and len(records) <= 5)
    expected = ("compiler-control", "failing-tang-control") + LABELS
    core, formula = None, None
    for index, record in enumerate(records):
        require(type(record) is dict and record.get("label") == expected[index])
        if index < 2:
            continue
        observed = record.get("observation")
        if observed is None:
            require(index == len(records) - 1)
            continue
        require(type(observed) is dict and "stage" in observed)
        stage = observed["stage"]
        if stage is None:
            require(observed.get("status") == "fail" and observed.get("compiler_failure") is True)
            continue
        require(type(stage) is dict and set(stage) == STAGE_FIELDS
                and stage["boundary"] == BOUNDARIES[index - 2]
                and type(stage["core_mug"]) is int and 0 <= stage["core_mug"] <= MAX_MUG)
        if core is None:
            core = stage["core_mug"]
        require(core == stage["core_mug"])
        value = stage["formula_mug"]
        if index == 2:
            require(value is None)
        else:
            require(type(value) is int and 0 <= value <= MAX_MUG)
            if formula is None:
                formula = value
            require(formula == value)
