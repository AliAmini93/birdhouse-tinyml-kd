#!/usr/bin/env python3
"""Run every offline check for the Birdhouse Himax firmware and record evidence.

Nothing here touches the board: the steps compile, link, run host programs and
inspect files. The script refuses to start if a Grove Vision AI is attached in
bootloader mode with its drive mounted, so that no step can write to it by
accident.

Usage:
  python3 tools/himax/run_offline_checks.py                # all steps
  python3 tools/himax/run_offline_checks.py --only m1,m2   # selected milestones
  python3 tools/himax/run_offline_checks.py --list

Results (logs with local paths removed, summary.json, summary.md) are written to
docs/research/birdhouse_v1_implementation_20261111/results/.

Step status:
  PASS     the step did what a correct build must do
  FAIL     it did not
  BLOCKED  a prerequisite outside this repository is missing
A step marked "negative control" passes only if the checked thing fails in the
expected way (for example: the vendor operator configuration must be rejected).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PY = sys.executable
SDK = os.path.join(REPO, ".local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3")
KERNEL_SRC = os.path.join(SDK, "app/scenario_app/edge_impulse_visionai/ei-model/edge-impulse-sdk/tensorflow/lite/micro/kernels")
TOOLCHAIN_BIN = os.path.join(REPO, ".local-tools/toolchains/arc_gnu_ei_prebuilt_minimal_elf32_le_linux_install/bin")
WORK = os.path.join(REPO, ".local-tools/port-himax")
RESULTS = os.path.join(REPO, "docs/research/birdhouse_v1_implementation_20261111/results")
MANIFEST = os.path.join(REPO, "firmware/himax_arc/birdhouse/model_manifest.json")
TESTS = os.path.join(REPO, "firmware/himax_arc/tests")
STAGE50 = os.path.join(WORK, "birdhouse-executable-step50/obj_socket_24/gnu_arcem9d_wei_r16")
BUILD_INFO = "obj_socket_24/gnu_arcem9d_wei_r16"

STEPS = []


def step(milestone, name, negative_control=False):
    def deco(fn):
        STEPS.append({"milestone": milestone, "name": name, "fn": fn, "negative_control": negative_control})
        return fn
    return deco


class Blocked(Exception):
    pass


def scrub(text):
    """Remove machine-specific paths before anything is written to the repository."""
    home = os.path.expanduser("~")
    text = text.replace(REPO, "<repo>")
    text = text.replace(os.path.dirname(os.path.dirname(PY)), "<python-env>")
    text = text.replace(os.path.dirname(REPO), "<workspace>")
    return text.replace(home, "<home>")


def shorten(text, head=15, tail=80):
    """Keep logs reviewable: long compiler output is cut in the middle."""
    lines = [l if len(l) <= 400 else l[:400] + " …[line truncated]" for l in text.splitlines()]
    if len(lines) > head + tail + 1:
        lines = lines[:head] + [f"… [{len(lines) - head - tail} lines omitted] …"] + lines[-tail:]
    return "\n".join(lines)


def run(cmd, log, cwd=REPO, env=None, timeout=1800):
    """Run a command, append its output to the step log, return (rc, output)."""
    log.append("$ " + " ".join(scrub(str(c)) for c in cmd))
    p = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=timeout, errors="replace")
    out = scrub(p.stdout)
    log.append(shorten(out.rstrip()))
    log.append(f"[exit {p.returncode}]")
    return p.returncode, out


def need(path, what):
    if not os.path.exists(path):
        raise Blocked(f"{what} not found: {scrub(path)}")


def tf_env():
    env = dict(os.environ)
    env["TF_CPP_MIN_LOG_LEVEL"] = "3"
    env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def last_json(out, prefix):
    for line in reversed(out.splitlines()):
        if line.startswith(prefix + " "):
            return json.loads(line[len(prefix) + 1:])
    return None


def verify_ops(label, macros, log, extra=()):
    json_out = os.path.join(RESULTS, f"ops_{label}.json")
    cmd = [PY, "-I", os.path.join(REPO, "tools/himax/verify_tflm_ops.py"), "--label", label,
           "--manifest", MANIFEST, "--kernel-src", KERNEL_SRC, "--macros", macros,
           "--json-out", json_out] + list(extra)
    rc, out = run(cmd, log)
    if os.path.exists(json_out):
        text = scrub(open(json_out, encoding="utf-8").read())
        open(json_out, "w", encoding="utf-8").write(text)
    return rc, out, json_out


def sdk_make(out_dir, log, *args):
    need(SDK, "vendor SDK")
    need(os.path.join(TOOLCHAIN_BIN, "arc-elf32-gcc"), "ARC toolchain")
    return run([os.path.join(REPO, "tools/himax/sdk_make.sh"), out_dir, *args], log)


# ---------------------------------------------------------------- milestone 1

@step("m1", "model manifest is reproducible from the tracked model array")
def m1_manifest(log):
    tmp = os.path.join(WORK, "bh-results", "model_manifest.regen.json")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    rc, _ = run([PY, os.path.join(REPO, "tools/himax/model_manifest.py"), "--model-cc",
                 "firmware/model/student_final_int8_model_data.cc", "--out", tmp], log, env=tf_env())
    if rc != 0:
        return False, {"reason": "manifest tool failed"}
    a = json.load(open(tmp, encoding="utf-8"))
    b = json.load(open(MANIFEST, encoding="utf-8"))
    b.pop("tflite_cross_check", None)
    same = a == b
    return same, {"model_sha256": a["sha256"], "operators": a["operator_histogram"],
                  "peak_live_activation_bytes": a["peak_live_activation_bytes"], "identical_to_tracked": same}


@step("m1", "ARC compiler sees the operator overlay: configuration audit passes")
def m1_config_overlay(log):
    out_dir = os.path.join(WORK, "bh-config-overlay")
    rc, _ = sdk_make(out_dir, log, "bh_tflm_config")
    if rc != 0:
        return False, {"reason": "config dump failed"}
    rc, out, _ = verify_ops("arc_config_overlay", os.path.join(out_dir, "birdhouse/tflm_config.macros"), log)
    return rc == 0, {"verifier_exit": rc, "summary": out.strip().splitlines()[0] if out.strip() else ""}


@step("m1", "vendor operator configuration is rejected by the audit", negative_control=True)
def m1_config_vendor(log):
    out_dir = os.path.join(WORK, "bh-config-vendor")
    rc, _ = sdk_make(out_dir, log, "BH_TFLM_OVERLAY=0", "bh_tflm_config")
    if rc != 0:
        return False, {"reason": "config dump failed"}
    rc, out, json_out = verify_ops("arc_config_vendor", os.path.join(out_dir, "birdhouse/tflm_config.macros"), log)
    fails = [c["check"] for c in json.load(open(json_out))["checks"] if c["status"] == "FAIL"]
    expected = all("FULLY_CONNECTED" in f for f in fails) and len(fails) == 2
    return rc == 1 and expected, {"verifier_exit": rc, "failed_checks": fails}


@step("m1", "stage50 build is rejected: disabled gate and stub kernel detected", negative_control=True)
def m1_stage50(log):
    need(os.path.join(STAGE50, "WEI_FW_gnu_arcem9d_wei_r16.elf"), "historical stage50 build")
    macros = os.path.join(WORK, "bh-config-vendor/birdhouse/tflm_config.macros")
    need(macros, "vendor configuration dump (run the previous step)")
    rc, out, json_out = verify_ops("stage50", macros, log, extra=[
        "--obj-root", STAGE50, "--elf", os.path.join(STAGE50, "WEI_FW_gnu_arcem9d_wei_r16.elf"),
        "--toolchain-bin", TOOLCHAIN_BIN])
    fails = [c for c in json.load(open(json_out))["checks"] if c["status"] == "FAIL"]
    stub = any(c["layer"] == "objects" and "not a stub" in c["check"] for c in fails)
    return rc == 1 and stub, {"verifier_exit": rc, "failed_checks": [c["check"] + " | " + c["detail"] for c in fails]}


# ---------------------------------------------------------------- milestone 2

@step("m2", "reference vectors are reproducible with the TensorFlow Lite interpreter")
def m2_reference_vectors(log):
    tracked = os.path.join(TESTS, "testdata/tflm_reference_vectors.json")
    before = open(tracked, encoding="utf-8").read()
    rc, out = run([PY, os.path.join(REPO, "tools/himax/gen_tflm_reference.py")], log, env=tf_env())
    after = open(tracked, encoding="utf-8").read()
    data = json.loads(after)
    differing = [v["name"] for v in data["vectors"]
                 if v["output_q_reference_kernels"] != v["output_q_default_kernels"]]
    return rc == 0 and before == after, {
        "vectors": len(data["vectors"]), "tensorflow_version": data["tensorflow_version"],
        "identical_to_tracked": before == after,
        "tflite_reference_vs_default_kernel_differences": differing}


@step("m2", "host kernels are built with the same operator gates as the firmware")
def m2_host_config(log):
    rc, _ = run(["make", "-C", TESTS, "config-macros", "CONFIG=overlay"], log)
    if rc != 0:
        return False, {"reason": "host config dump failed"}
    rc, out, _ = verify_ops("host_config_overlay", os.path.join(WORK, "host-tests/overlay/tflm_config.macros"),
                            log, extra=["--host"])
    return rc == 0, {"verifier_exit": rc}


@step("m2", "host inference on vendor TFLite Micro sources: init, arena, 26 vectors, repeat, errors")
def m2_host_inference(log):
    rc, _ = run(["make", "-C", TESTS, "-j8", "tflm", "CONFIG=overlay"], log)
    if rc != 0:
        return False, {"reason": "host build failed"}
    rc, out = run([os.path.join(WORK, "host-tests/overlay/test_tflm_inference")], log)
    summary = last_json(out, "SUMMARY") or {}
    result = last_json(out, "RESULT") or {}
    return rc == 0 and summary.get("status") == "PASS", {"summary": summary, "result": result}


@step("m2", "host inference with the vendor operator configuration is blocked", negative_control=True)
def m2_host_inference_vendor(log):
    rc, _ = run(["make", "-C", TESTS, "-j8", "tflm", "CONFIG=vendor"], log)
    if rc != 0:
        return False, {"reason": "host build failed"}
    rc, out = run([os.path.join(WORK, "host-tests/vendor/test_tflm_inference"), "expect-blocked"], log)
    blocked_at = [l.split("=", 1)[1] for l in out.splitlines() if l.strip().startswith("blocked_at=")]
    return rc == 0, {"blocked_at": blocked_at[0] if blocked_at else None}


# --------------------------------------------------------------------- runner

def board_guard():
    """Refuse to run while a bootloader drive is mounted."""
    hits = []
    try:
        for line in open("/proc/mounts", encoding="utf-8"):
            parts = line.split()
            if len(parts) > 1 and os.path.basename(parts[1]).upper() in ("GROVEAI", "GROVE", "VISIONAI"):
                hits.append(parts[1])
    except OSError:
        pass
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated milestones, e.g. m1,m2")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for s in STEPS:
            print(f"{s['milestone']}  {'[negative control] ' if s['negative_control'] else ''}{s['name']}")
        return 0

    mounted = board_guard()
    if mounted:
        print(f"refusing to run: bootloader drive mounted at {mounted}. Unplug the board first.", file=sys.stderr)
        return 2

    only = set(args.only.split(",")) if args.only else None
    os.makedirs(RESULTS, exist_ok=True)
    os.makedirs(os.path.join(WORK, "bh-results"), exist_ok=True)

    summary_path = os.path.join(RESULTS, "summary.json")
    previous = {}
    if os.path.exists(summary_path):
        for r in json.load(open(summary_path, encoding="utf-8")).get("steps", []):
            previous[(r["milestone"], r["name"])] = r

    records = []
    counters = {}
    for s in STEPS:
        key = (s["milestone"], s["name"])
        counters[s["milestone"]] = counters.get(s["milestone"], 0) + 1
        step_id = f"{s['milestone']}_{counters[s['milestone']]:02d}"
        if only and s["milestone"] not in only:
            if key in previous:
                records.append(previous[key])
            continue
        log = []
        try:
            ok, details = s["fn"](log)
            status = "PASS" if ok else "FAIL"
        except Blocked as e:
            status, details = "BLOCKED", {"reason": str(e)}
        except subprocess.TimeoutExpired:
            status, details = "FAIL", {"reason": "timeout"}
        log_name = f"{step_id}.log.txt"
        with open(os.path.join(RESULTS, log_name), "w", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        records.append({"id": step_id, "milestone": s["milestone"], "name": s["name"],
                        "negative_control": s["negative_control"], "status": status,
                        "details": details, "log": log_name})
        print(f"{status:<8}{step_id}  {s['name']}")

    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head_when_run": head,
        "overall": "PASS" if all(r["status"] == "PASS" for r in records) else
                   ("FAIL" if any(r["status"] == "FAIL" for r in records) else "BLOCKED"),
        "steps": records,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as f:
        f.write("# Offline check results\n\n")
        f.write(f"Generated {summary['generated_utc']} at commit `{head[:12]}` (tree may contain later edits).\n\n")
        f.write(f"Overall: **{summary['overall']}**\n\n")
        f.write("| Step | Status | Check | Kind |\n|---|---|---|---|\n")
        for r in records:
            kind = "negative control" if r["negative_control"] else "positive"
            f.write(f"| `{r['id']}` | {r['status']} | {r['name']} | {kind} |\n")
        f.write("\nReproduce with `python3 tools/himax/run_offline_checks.py` using the project interpreter.\n")
    print(f"overall: {summary['overall']}")
    return 0 if summary["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
