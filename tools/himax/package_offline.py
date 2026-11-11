#!/usr/bin/env python3
"""Offline packaging of the firmware candidate, with validation. Never deploys.

What it does
  1. Checks only the local mount table for a mounted bootloader drive. It never
     enumerates USB devices. The sandbox, not device absence, enforces isolation.
  2. Copies the vendor image generator (Linux parts only) into a work directory
     and runs it there inside a bubblewrap sandbox: the rest of the filesystem
     is read-only, /dev holds no serial or block devices, /media, /sys and /run
     are empty and there is no network. The vendor `make flash` target and the vendor
     uf2conv.py are not used.
  3. Validates the produced image against the factory image, the SDK inputs and
     the ELF, converts it to UF2 with tools/himax/uf2_tool.py and validates
     that too.

Outputs stay in a new directory under .local-tools/port-himax (never tracked). A JSON report is written to
the path given with --json-out.

Packaging success is not permission to deploy.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uf2_tool  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SDK = os.path.join(REPO, ".local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3")
TOOL_DIR = os.path.join(SDK, "tools/image_gen_cstm")
FACTORY_UF2 = os.path.join(REPO, ".local-tools/firmware/grove-ai-v1/factory/grove_ai_v02-00.uf2")
FACTORY_SHA256 = "8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c"
EI_ZIP = os.path.join(REPO, ".local-tools/firmware/grove-ai-v1/seeed-grove-vision-ai.zip")
ELF_BASENAME = "WEI_FW_gnu_arcem9d_wei_r16.elf"

FLASH_SIZE = 0x200000
CONFIG_AREA = 0x1FE000  # vendor application keeps its settings from here upward
APP_START = 0x22000
# ELF sections the vendor image generator stores. Everything else must be RAM
# that needs no initial content.
STORED_SECTIONS = {".ivt", ".vector", ".text", ".read_only_data", ".data", ".rodata_in_data", ".sdata"}
# Dropped by the vendor flow although not zero; identical treatment in vendor builds.
KNOWN_DROPPED_NONZERO = {".gcc_except_table"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class Report:
    def __init__(self):
        self.checks, self.facts = [], {}

    def add(self, group, name, ok, detail=""):
        self.checks.append({"group": group, "check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)})
        return ok

    @property
    def ok(self):
        return all(c["status"] == "PASS" for c in self.checks)


def board_present():
    # Inspect only the local mount table, never enumerate/contact USB devices.
    hits = []
    try:
        for line in open("/proc/mounts"):
            parts = line.split()
            if len(parts) > 1 and os.path.basename(parts[1]).upper() in ("GROVEAI", "GROVE", "VISIONAI"):
                hits.append(parts[1])
    except OSError:
        pass
    return hits


def copy_tool(dst):
    for root, _dirs, files in os.walk(TOOL_DIR):
        rel = os.path.relpath(root, TOOL_DIR)
        for name in files:
            if name.lower().endswith((".exe", ".dll", ".bat")):
                continue
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            shutil.copy2(os.path.join(root, name), os.path.join(dst, rel, name))
    os.makedirs(os.path.join(dst, "output"), exist_ok=True)  # the generator does not create it
    for exe in ("image_gen_cstm_gnu", "sign_tool"):
        os.chmod(os.path.join(dst, exe), 0o755)


def run_generator(work, img_dir, toolchain_bin):
    tmp = os.path.join(work, "tmp")
    os.makedirs(tmp, exist_ok=True)
    cmd = ["bwrap", "--unshare-net", "--unshare-pid", "--die-with-parent", "--new-session",
           "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--tmpfs", "/media", "--tmpfs", "/sys",
           "--tmpfs", "/run", "--dev", "/dev", "--proc", "/proc",
           "--bind", work, work, "--setenv", "TMPDIR", tmp,
           "--setenv", "PATH", os.path.abspath(toolchain_bin) + ":/usr/bin:/bin", "--chdir", img_dir,
           "./image_gen_cstm_gnu", "ic", "config"]  # same arguments as the vendor makefile
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=600)
    return p.returncode, p.stdout


def elf_sections(toolchain_bin, elf):
    out = subprocess.run([os.path.join(toolchain_bin, "arc-elf32-readelf"), "-S", "-W", elf],
                         check=True, capture_output=True, text=True).stdout
    secs = []
    for line in out.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]{8})\s+([0-9a-f]+)\s+([0-9a-f]+)\s+\S+\s+(\S*)", line)
        if m and "A" in m.group(6) and int(m.group(5), 16) > 0:
            secs.append({"name": m.group(1), "type": m.group(2), "addr": int(m.group(3), 16),
                         "offset": int(m.group(4), 16), "size": int(m.group(5), 16)})
    return secs


def uf2_payload(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
    info, payload = uf2_tool.describe(data)
    return data, info, payload


def package(elf, work, toolchain_bin, rep, label):
    os.makedirs(work, exist_ok=False)  # never delete an earlier candidate
    img_dir = os.path.join(work, "image_gen")
    copy_tool(img_dir)
    shutil.copy2(elf, os.path.join(img_dir, "input", ELF_BASENAME))
    rc, log = run_generator(work, img_dir, toolchain_bin)
    open(os.path.join(work, "image_gen.log"), "w").write(log)
    out_img = os.path.join(img_dir, "output", "output.img")
    if not rep.add("generate", f"{label}: vendor image generator succeeded in the sandbox",
                   rc == 0 and os.path.isfile(out_img), f"exit {rc}"):
        return None, log
    return open(out_img, "rb").read(), log


def verify_application_payload(image, app_parts, secs, elf_bytes):
    """Verify payload AND destinations from the binary SBS descriptors.

    SDK 2.5.3 BLp has a 0x494-byte signing prefix per chunk. The descriptor
    control word encodes its length in the upper half and item count in byte 1;
    each item is (offset, type, destination, size). Type 0xf contains a
    four-byte SDK marker followed by the IVT. The descriptor prelude is four bytes. This verifies packaging, not boot-ROM or
    cryptographic-signature acceptance on hardware.
    """
    expected = {s["name"]: s for s in secs if s["name"] in STORED_SECTIONS}
    if set(expected) != STORED_SECTIONS or not app_parts:
        raise ValueError("missing expected sections or application chunks")
    covered = {name: [] for name in expected}
    for i, part in enumerate(app_parts):
        start, end = part["addr"], part["addr"] + part["size"]
        base = start + 0x494
        if end > len(image) or part["size"] > 0x10000 or base + 16 > end:
            raise ValueError("truncated or oversized application chunk")
        if image[start:start + 8] != bytes.fromhex("424c700220000003"):
            raise ValueError("unexpected BLp header")
        prelude, control, reserved, nxt = struct.unpack_from("<4I", image, base)
        count, header = (control >> 8) & 255, control >> 16
        if not count or header != 16 + 16 * count or reserved != 0 or prelude & 0xFFFF != 0x0101:
            raise ValueError("invalid SBS header")
        want_next = app_parts[i + 1]["addr"] - APP_START if i + 1 < len(app_parts) else 0xFFFFFFFF
        if nxt != want_next or base + header > end:
            raise ValueError("bad application next-header chain")
        source_end = header
        for j in range(count):
            off, kind, addr, size = struct.unpack_from("<4I", image, base + 16 + 16 * j)
            if not size or off < source_end or base + off + size > end:
                raise ValueError("overlapping or truncated SBS payload")
            source_end = off + size
            blob = image[base + off:base + off + size]
            if kind == 0xF:
                sec = expected[".ivt"]
                raw = elf_bytes[sec["offset"]:sec["offset"] + sec["size"]]
                if addr != sec["addr"] - 4 or blob != b"x0x0" + raw:
                    raise ValueError("IVT bytes/destination or SDK marker differ")
                name, relative, length = ".ivt", 0, sec["size"]
            else:
                matches = [(name, sec) for name, sec in expected.items() if name != ".ivt" and
                           sec["addr"] <= addr and addr + size <= sec["addr"] + ((sec["size"] + 3) & ~3)]
                if len(matches) != 1 or kind not in (1, 3):
                    raise ValueError("SBS destination outside expected ELF sections")
                name, sec = matches[0]
                if kind != (1 if name in (".vector", ".text") else 3):
                    raise ValueError("SBS destination type differs from ELF section")
                relative, length = addr - sec["addr"], size
                raw = elf_bytes[sec["offset"]:sec["offset"] + sec["size"]]
                raw += b"\xff" * (-len(raw) % 4)
                if blob != raw[relative:relative + size]:
                    raise ValueError("ELF payload mismatch in " + name)
            covered[name].append((relative, relative + length))
    for name, intervals in covered.items():
        cursor = 0
        for lo, hi in sorted(intervals):
            if lo != cursor: raise ValueError("overlap or gap in " + name)
            cursor = hi
        if cursor != ((expected[name]["size"] + 3) & ~3):
            raise ValueError("incomplete ELF payload in " + name)
    return sum(s["size"] for s in expected.values()) + 4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--elf", required=True)
    ap.add_argument("--work", required=True, help="work directory under .local-tools (recreated)")
    ap.add_argument("--toolchain-bin", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args()

    attached = board_present()
    if attached:
        print(f"refusing to package: Grove device or bootloader drive present ({attached}). Unplug it first.",
              file=sys.stderr)
        return 2
    work = os.path.realpath(args.work)
    if not work.startswith(os.path.join(REPO, ".local-tools", "port-himax") + os.sep) or os.path.lexists(args.work):
        print("--work must be a NEW directory inside .local-tools/port-himax", file=sys.stderr)
        return 2
    if shutil.which("bwrap") is None:
        print("bubblewrap (bwrap) is required for the sandbox", file=sys.stderr)
        return 2

    rep = Report()
    elf_bytes = open(args.elf, "rb").read()
    rep.facts["elf"] = {"sha256": sha256(elf_bytes), "size_bytes": len(elf_bytes)}

    image, log = package(args.elf, os.path.join(work, "run1"), args.toolchain_bin, rep, "run 1")
    if image is None:
        print(log[-2000:])
        return 1
    image2, _ = package(args.elf, os.path.join(work, "run2"), args.toolchain_bin, rep, "run 2")

    # ---- which ELF sections went into the image ------------------------------
    stored = re.findall(r"\['\d+', '([^']+)', '([0-9a-f]+)', '([0-9a-f]+)'", log)
    stored_names = [s[0] for s in stored]
    rep.add("content", "generator stored exactly the expected ELF sections",
            set(stored_names) == STORED_SECTIONS, stored_names)
    secs = elf_sections(args.toolchain_bin, args.elf)
    by_name = {s["name"]: s for s in secs}
    for name, size_hex, addr_hex in stored:
        s = by_name.get(name)
        rep.add("content", f"{name}: size and address in the image match the ELF",
                s is not None and s["size"] == int(size_hex, 16) and s["addr"] == int(addr_hex, 16),
                f"{size_hex} @ {addr_hex}")
    dropped = []
    for s in secs:
        if s["name"] in STORED_SECTIONS:
            continue
        nonzero = False
        if s["type"] != "NOBITS":
            blob = elf_bytes[s["offset"]:s["offset"] + s["size"]]
            nonzero = any(blob)
        dropped.append({"name": s["name"], "size": s["size"], "type": s["type"], "has_nonzero_bytes": nonzero})
        if nonzero and s["name"] not in KNOWN_DROPPED_NONZERO:
            rep.add("content", f"{s['name']} is not stored and must hold no initial data", False,
                    "non-zero bytes would be lost")
    rep.add("content", "sections left out of the image hold no initial data",
            all((not d["has_nonzero_bytes"]) or d["name"] in KNOWN_DROPPED_NONZERO for d in dropped),
            [d["name"] for d in dropped])
    rep.facts["sections_not_stored"] = dropped

    # ---- image layout --------------------------------------------------------
    xml = open(os.path.join(work, "run1", "image_gen", "output", "layout.xml"), encoding="utf-8", errors="replace").read()
    parts = [{"type": int(t, 16), "addr": int(a, 16), "size": int(z, 16)} for t, a, z in
             re.findall(r"<PART_TYPE>(0x[0-9a-f]+)</PART_TYPE>.*?<PART_ADDR>(0x[0-9a-f]+)</PART_ADDR><PART_SIZE>(0x[0-9a-f]+)</PART_SIZE>", xml)]
    rep.facts["partitions"] = [{"type": hex(p["type"]), "addr": hex(p["addr"]), "size": p["size"]} for p in parts]
    app_parts = [p for p in parts if p["type"] == 0x4]
    end = max(p["addr"] + p["size"] for p in parts) if parts else 0
    rep.add("layout", "image no larger than the 2 MB flash", len(image) <= FLASH_SIZE, f"{len(image)} bytes")
    rep.add("layout", "image ends below the vendor configuration area at 0x1FE000",
            len(image) <= CONFIG_AREA and end <= CONFIG_AREA, f"end of last partition {hex(end)}")
    rep.add("layout", "partitions do not overlap",
            all(a["addr"] + a["size"] <= b["addr"] for a, b in zip(sorted(parts, key=lambda p: p["addr"]),
                                                                  sorted(parts, key=lambda p: p["addr"])[1:])), "")
    rep.add("layout", "application starts at 0x22000 in 64 KiB chunks",
            bool(app_parts) and app_parts[0]["addr"] == APP_START and
            all(p["addr"] == APP_START + i * 0x10000 for i, p in enumerate(app_parts)),
            f"{len(app_parts)} chunks")
    for off in (0x20000, 0x21000, 0x22000):
        rep.add("layout", f"'BLp' header at {hex(off)}", image[off:off + 3] == b"BLp", image[off:off + 8].hex())

    # ---- against the factory image and the SDK inputs --------------------------
    fac_data, fac_info, fac = uf2_payload(FACTORY_UF2)
    rep.add("provenance", "local factory UF2 has the published SHA-256", sha256(fac_data) == FACTORY_SHA256, "")
    sdk_bl = os.path.join(TOOL_DIR, "input/BLp/QFN72/HX6537-A09TDIG-1111V")
    bl2 = open(os.path.join(sdk_bl, "sign_formal_PA8530_EM9D_2nd_Bootloader.bin"), "rb").read()
    bl1 = open(os.path.join(sdk_bl, "sign_formal_PA8530_EM9D_Bootloader.bin"), "rb").read()
    rep.add("bootloader", "2nd bootloader region 0x0-0x10000 identical to the factory image",
            image[:0x10000] == fac[:0x10000], sha256(image[:0x10000])[:16])
    rep.add("bootloader", "bootloader region 0x10000-0x20000 identical to the factory image",
            image[0x10000:0x20000] == fac[0x10000:0x20000], sha256(image[0x10000:0x20000])[:16])
    rep.add("bootloader", "both regions start with the SDK binaries for HX6537-A09TDIG-1111V",
            image[:len(bl2)] == bl2 and image[0x10000:0x10000 + len(bl1)] == bl1, "")
    rep.add("bootloader", "loader configuration region 0x21000-0x22000 identical to the factory image",
            image[0x21000:0x22000] == fac[0x21000:0x22000], sha256(image[0x21000:0x22000])[:16])

    # ---- the application inside the image is this ELF ---------------------------
    app = image[APP_START:]
    try:
        coverage = verify_application_payload(image, app_parts, secs, elf_bytes)
        rep.add("content", "every stored ELF byte and destination verified in actual image descriptors", True,
                f"{coverage} bytes (including special IVT marker)")
    except ValueError as e:
        rep.add("content", "every stored ELF byte and destination verified in actual image descriptors", False, str(e))
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    probes_ok, probes = 0, 0
    for s in secs:
        if s["name"] not in STORED_SECTIONS or s["size"] < 64:
            continue
        blob = elf_bytes[s["offset"]:s["offset"] + s["size"]]
        for frac in (0.0, 0.25, 0.5, 0.75):
            start = min(int(len(blob) * frac) & ~3, len(blob) - 48)
            window = blob[start:start + 48]
            if len(set(window)) < 8:
                continue  # skip low-entropy windows that would match anywhere
            probes += 1
            probes_ok += 1 if window in app else 0
    rep.add("content", "sampled windows of every stored ELF section are found in the image",
            probes > 10 and probes_ok == probes, f"{probes_ok}/{probes}")
    rep.add("content", "console strings of the Birdhouse module are present",
            b"BIRDHOUSE RESULT seq=" in app and b"BIRDSELFTEST" in app, "")
    model_sec = by_name.get(".read_only_data")
    rep.add("content", "model identifier 'TFL3' and manifest size are consistent with the stored data section",
            model_sec is not None and manifest["size_bytes"] < model_sec["size"] and b"TFL3" in app, "")

    # ---- determinism -----------------------------------------------------------
    if image2 is not None:
        same = image == image2
        diff = sum(1 for a, b in zip(image, image2) if a != b) if not same else 0
        rep.facts["deterministic"] = same
        rep.add("generate", "two independent packaging runs give the same image", same,
                "identical" if same else f"{diff} differing bytes")

    # ---- UF2 ---------------------------------------------------------------------
    for name, data in (("factory", fac_data),):
        info, payload = uf2_tool.describe(data)
        rep.add("uf2", f"converter reproduces the {name} UF2 byte for byte from its payload",
                uf2_tool.pack(payload) == data, f"{len(data)} bytes")
    if os.path.isfile(EI_ZIP):
        import zipfile
        ei = zipfile.ZipFile(EI_ZIP).read("firmware.uf2")
        info, payload = uf2_tool.describe(ei)
        rep.add("uf2", "converter reproduces the Edge Impulse prebuilt UF2 byte for byte",
                uf2_tool.pack(payload) == ei, f"{len(ei)} bytes")
        rep.facts["edge_impulse_prebuilt_image_bytes"] = len(payload)
    uf2 = uf2_tool.pack(image)
    info, payload = uf2_tool.describe(uf2)
    for name, ok, detail in uf2_tool.firmware_checks(info):
        rep.add("uf2", name, ok, detail if not ok else "")
    rep.add("uf2", "UF2 payload equals the image", payload == image + b"\x00" * ((-len(image)) % 256), "")
    rep.add("uf2", "same family, flags and base address as the factory UF2",
            info["families"] == fac_info["families"] and info["flags"] == fac_info["flags"] and
            info["first_address"] == fac_info["first_address"], f"{info['families']} {info['first_address']}")

    out_dir = os.path.join(work, "out")
    os.makedirs(out_dir, exist_ok=True)
    img_path = os.path.join(out_dir, "birdhouse_candidate_output.img")
    uf2_path = os.path.join(out_dir, "birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2")
    open(img_path, "wb").write(image)
    open(uf2_path, "wb").write(uf2)

    rep.facts["image"] = {"bytes": len(image), "sha256": sha256(image), "application_bytes": len(app),
                          "application_chunks": len(app_parts)}
    rep.facts["uf2"] = {"bytes": len(uf2), "blocks": len(uf2) // 512, "sha256": sha256(uf2),
                        "first_address": info["first_address"], "end_address": info["end_address"]}
    rep.facts["size_comparison_image_bytes"] = {
        "factory_grove_ai_v02_00": len(fac), "candidate": len(image),
        "edge_impulse_prebuilt": rep.facts.get("edge_impulse_prebuilt_image_bytes")}
    rep.facts["generator_version"] = (re.search(r"Image Gen Tool Ver: ([\d .]+)", log) or [None, ""])[1].replace(" ", "")
    rep.facts["sandbox"] = "bubblewrap: read-only root, new private work dir, no devices, no /sys, /run or /media, no network"
    rep.facts["outputs_local_only"] = [os.path.relpath(img_path, REPO), os.path.relpath(uf2_path, REPO)]

    result = {"status": "PASS" if rep.ok else "FAIL", "checks": rep.checks, "facts": rep.facts,
              "note": "Packaging success is not permission to deploy."}
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    fails = [c for c in rep.checks if c["status"] == "FAIL"]
    print(f"[package] {len(rep.checks)} checks, {len(fails)} failed -> {result['status']}")
    for c in fails:
        print(f"  FAIL [{c['group']}] {c['check']}: {c['detail']}")
    print(f"  image {len(image)} bytes sha256 {sha256(image)[:16]}…, UF2 {len(uf2)} bytes, "
          f"addresses {info['first_address']}..{info['end_address']}")
    print("  outputs are local only; nothing was copied to any device")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
