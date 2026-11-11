#!/usr/bin/env python3
"""UF2 helper for Grove Vision AI V1 firmware images: inspect, unpack, pack, verify.

This tool only converts between files. It has no code that looks for a board,
a serial port or a mounted drive, and it never copies anything anywhere but the
output path given on the command line. (The vendor's uf2conv.py, by contrast,
deploys to any mounted bootloader drive unless told not to, and may install
Python packages; it is deliberately not used.)

Format produced (identical to the vendor tool for firmware images):
  512-byte blocks, 256 payload bytes each, flags 0x2000 (family ID present),
  family 0xEF32C892, target address 0x10000000 + offset, zero padding.

Usage:
  uf2_tool.py info   FILE.uf2
  uf2_tool.py unpack FILE.uf2 OUT.bin
  uf2_tool.py pack   IMAGE.bin OUT.uf2
  uf2_tool.py verify FILE.uf2 IMAGE.bin
"""
import argparse
import hashlib
import struct
import sys

MAGIC0 = 0x0A324655
MAGIC1 = 0x9E5D5157
MAGIC_END = 0x0AB16F30
FLAG_FAMILY = 0x2000
FAMILY_GROVE_AI = 0xEF32C892
FIRMWARE_BASE = 0x10000000
FIRMWARE_LIMIT = 0x10200000  # 2 MB Himax flash image
PAYLOAD = 256


def parse(data):
    """Return (blocks, problems). Each block: dict(addr, size, no, total, flags, family, data)."""
    problems = []
    if len(data) % 512 != 0:
        problems.append(f"length {len(data)} is not a multiple of 512")
    blocks = []
    for i in range(len(data) // 512):
        blk = data[i * 512:(i + 1) * 512]
        m0, m1, flags, addr, size, no, total, family = struct.unpack("<8I", blk[:32])
        end = struct.unpack("<I", blk[508:])[0]
        if m0 != MAGIC0 or m1 != MAGIC1 or end != MAGIC_END:
            problems.append(f"block {i}: bad magic")
            continue
        if size > 476:
            problems.append(f"block {i}: payload size {size}")
            continue
        blocks.append({"addr": addr, "size": size, "no": no, "total": total, "flags": flags,
                       "family": family, "data": blk[32:32 + size], "tail": blk[32 + size:508]})
    return blocks, problems


def describe(data):
    blocks, problems = parse(data)
    info = {"bytes": len(data), "blocks": len(blocks), "problems": problems}
    if not blocks:
        return info, b""
    info["families"] = sorted({hex(b["family"]) for b in blocks})
    info["flags"] = sorted({hex(b["flags"]) for b in blocks})
    info["payload_sizes"] = sorted({b["size"] for b in blocks})
    info["first_address"] = hex(blocks[0]["addr"])
    info["end_address"] = hex(blocks[-1]["addr"] + blocks[-1]["size"])
    contiguous = all(blocks[i]["addr"] + blocks[i]["size"] == blocks[i + 1]["addr"] for i in range(len(blocks) - 1))
    numbering = all(b["no"] == i and b["total"] == len(blocks) for i, b in enumerate(blocks))
    padding = all(not any(b["tail"]) for b in blocks)
    info["contiguous"] = contiguous
    info["numbering_consistent"] = numbering
    info["padding_zero"] = padding
    payload = b"".join(b["data"] for b in blocks)
    info["payload_bytes"] = len(payload)
    info["payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return info, payload


def pack(image, base=FIRMWARE_BASE, family=FAMILY_GROVE_AI):
    total = (len(image) + PAYLOAD - 1) // PAYLOAD
    out = bytearray()
    for no in range(total):
        chunk = image[no * PAYLOAD:(no + 1) * PAYLOAD]
        chunk = chunk + b"\x00" * (PAYLOAD - len(chunk))
        head = struct.pack("<8I", MAGIC0, MAGIC1, FLAG_FAMILY, base + no * PAYLOAD, PAYLOAD, no, total, family)
        out += head + chunk + b"\x00" * (512 - 32 - PAYLOAD - 4) + struct.pack("<I", MAGIC_END)
    return bytes(out)


def firmware_checks(info):
    """List of (name, ok, detail) for a V1 firmware UF2."""
    checks = [
        ("no structural problems", not info.get("problems"), info.get("problems")),
        ("single family 0xef32c892", info.get("families") == [hex(FAMILY_GROVE_AI)], info.get("families")),
        ("flags 0x2000 on every block", info.get("flags") == [hex(FLAG_FAMILY)], info.get("flags")),
        ("256-byte payloads", info.get("payload_sizes") == [PAYLOAD], info.get("payload_sizes")),
        ("starts at 0x10000000", info.get("first_address") == hex(FIRMWARE_BASE), info.get("first_address")),
        ("ends inside the 2 MB firmware range",
         int(info.get("end_address", "0x0"), 16) <= FIRMWARE_LIMIT, info.get("end_address")),
        ("addresses contiguous", bool(info.get("contiguous")), ""),
        ("block numbering consistent", bool(info.get("numbering_consistent")), ""),
        ("padding bytes are zero", bool(info.get("padding_zero")), ""),
    ]
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("uf2")
    p = sub.add_parser("unpack"); p.add_argument("uf2"); p.add_argument("out")
    p = sub.add_parser("pack"); p.add_argument("image"); p.add_argument("out")
    p = sub.add_parser("verify"); p.add_argument("uf2"); p.add_argument("image")
    args = ap.parse_args()

    if args.cmd == "pack":
        image = open(args.image, "rb").read()
        if len(image) > FIRMWARE_LIMIT - FIRMWARE_BASE:
            print("image larger than the 2 MB firmware range", file=sys.stderr)
            return 1
        data = pack(image)
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"wrote {args.out}: {len(data)} bytes, {len(data) // 512} blocks")
        return 0

    data = open(args.uf2, "rb").read()
    info, payload = describe(data)
    if args.cmd == "info":
        for k, v in info.items():
            print(f"{k}: {v}")
        ok = True
        for name, passed, detail in firmware_checks(info):
            print(f"{'PASS' if passed else 'FAIL'} {name} {detail if not passed else ''}")
            ok = ok and passed
        return 0 if ok else 1
    if args.cmd == "unpack":
        with open(args.out, "wb") as f:
            f.write(payload)
        print(f"wrote {args.out}: {len(payload)} bytes")
        return 0
    if args.cmd == "verify":
        image = open(args.image, "rb").read()
        padded = image + b"\x00" * ((-len(image)) % PAYLOAD)
        same = payload == padded
        print("payload equals image:", same)
        return 0 if same and all(p for _, p, _ in firmware_checks(info)) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
