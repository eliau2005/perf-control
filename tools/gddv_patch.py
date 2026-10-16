#!/usr/bin/env python3
"""Add a package-temperature passive row to the PSVTs of an Intel DTT data vault.

ASUS's X1402ZA policy only throttles PL1 against the skin sensor SEN1 (which
reads a constant 63 °C on Linux); CPU temperature is left to the hardware TCC
trip (TjMax − TccOffset = 92/95 °C), so sustained loads sit on thermal
throttling. This tool appends, to every named PSVT (and IETM.D0's default),
a row  TCPU → TCPU @ TRIP °C  so thermald steps PL1 down *before* the TCC trip.

usage: gddv_patch.py IN.bin OUT.bin [--trip 89] [--step-mw 500] [--period-s 2]

Output keeps the vault's container format (ESIFDV v2, LZMA-alone payload) and
updates payload sizes and the SHA-256 payload hash. thermald (≥ 2.5.12, with
<DataVaultFromFileSystem>1 in /etc/thermald/thermald-features.xml) loads it
from /lib/firmware/intel/dtt/dtt_data_vault_<crc32s>.bin instead of the
firmware's; the file must be a root-owned regular file ≤ 4096 bytes.
"""
import argparse
import hashlib
import lzma
import struct
import sys

SIG_HEADER, SIG_KEY, COMPRESSED = 0x1FE5, 0xA0D8, 0x40000000
TCPU = "\\_SB_.PC00.TCPU"


def u64(v):
    return struct.pack("<IQ", 4, v)


def s(v):
    b = v.encode() + b"\0"
    return struct.pack("<IQ", 8, len(b)) + b


def psvt_row(trip_c, step_mw, period_s):
    # source, target, priority, sample period (0.1 s), trip (0.1 K), domain,
    # control knob 0x10000 = PL1, limit, step (mW), limit coeff, unlimit coeff, 0
    return (s(TCPU) + s(TCPU) + u64(10) + u64(period_s * 10) + u64(int(trip_c * 10 + 2732))
            + u64(9) + u64(0x10000) + s("MAX") + u64(step_mw) + u64(10) + u64(20) + u64(0))


def header(b, off=0):
    sig, hsize, ver, flags = struct.unpack_from("<HHII", b, off)
    assert sig == SIG_HEADER, f"bad signature at {off}"
    psize = struct.unpack_from("<I", b, off + 0x8c)[0]
    return hsize, ver, flags, psize


def patch_keys(body, start, end, row, log):
    """Rewrite the KEYS stream in body[start:end]; return new bytes."""
    out, off = bytearray(), start
    while off < end:
        sig = struct.unpack_from("<H", body, off)[0]
        if sig == SIG_HEADER:
            hsize, _ver, _flags, psize = header(body, off)
            inner = patch_keys(body, off + hsize, off + hsize + psize, row, log)
            hdr = bytearray(body[off:off + hsize])
            struct.pack_into("<I", hdr, 0x8c, len(inner))
            out += hdr + inner
            off += hsize + psize
            continue
        assert sig == SIG_KEY, f"unknown signature 0x{sig:04x} at {off}"
        kflags, klen = struct.unpack_from("<II", body, off + 2)
        key = body[off + 10:off + 10 + klen]
        vtype, vlen = struct.unpack_from("<II", body, off + 10 + klen)
        vstart = off + 18 + klen
        val = body[vstart:vstart + vlen]
        name = key.split(b"\0")[0].decode()
        if vtype == 7 and (name.startswith("/shared/tables/psvt/") or name == "/participants/IETM.D0/psvt"):
            val = val + row
            log.append(name)
        out += struct.pack("<HII", SIG_KEY, kflags, klen) + key + struct.pack("<II", vtype, len(val)) + val
        off = vstart + vlen
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--trip", type=float, default=89.0, help="°C on the package (default 89)")
    ap.add_argument("--step-mw", type=int, default=500)
    ap.add_argument("--period-s", type=int, default=2)
    a = ap.parse_args()

    b = open(a.src, "rb").read()
    hsize, _ver, flags, psize = header(b)
    assert flags & COMPRESSED, "only compressed vaults handled"
    body = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(b[hsize:hsize + psize])
    log = []
    new_body = patch_keys(body, 0, len(body), psvt_row(a.trip, a.step_mw, a.period_s), log)
    # thermald's lzma decoder insists on the stock LZMA-alone properties 5d 00 00 00 01
    comp = lzma.compress(new_body, format=lzma.FORMAT_ALONE,
                         filters=[{"id": lzma.FILTER_LZMA1, "dict_size": 1 << 24, "lc": 3, "lp": 0, "pb": 2}])
    hdr = bytearray(b[:hsize])
    hdr[0x6c:0x8c] = hashlib.sha256(comp).digest()
    struct.pack_into("<I", hdr, 0x8c, len(comp))
    out = bytes(hdr) + comp
    open(a.dst, "wb").write(out)
    print(f"patched {len(log)} PSVTs: {', '.join(n.split('/')[-1] for n in log)}")
    print(f"row: TCPU->TCPU {a.trip} °C, step {a.step_mw} mW, period {a.period_s} s; "
          f"size {len(b)} -> {len(out)} bytes (limit 4096)")
    if len(out) > 4096:
        print("ERROR: exceeds thermald's 4 KiB file limit", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
