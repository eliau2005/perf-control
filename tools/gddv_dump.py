#!/usr/bin/env python3
"""Decode an Intel DTT GDDV data vault (INT3400 `data_vault` sysfs blob).

Mirrors the layout thermald's thd_gddv.cpp expects (ESIFDV v2 header,
LZMA-alone compressed payload, nested KEYS repository, 0xA0D8 key items,
TLV table elements) so we can see what ASUS actually ships and where
thermald's parser breaks.

usage: gddv_dump.py data_vault [--raw]
"""
import lzma
import struct
import sys
import uuid

SIG_HEADER = 0x1FE5
SIG_KEY = 0xA0D8
COMPRESSED = 0x40000000
TYPES = {3: "u32", 4: "u64", 7: "bin", 8: "str"}


def header(b, off):
    sig, hsize, ver, flags = struct.unpack_from("<HHII", b, off)
    if sig != SIG_HEADER:
        raise ValueError(f"bad header signature 0x{sig:04x} at {off}")
    seg = b[off + 0x0c:off + 0x2c].split(b"\0")[0].decode(errors="replace")
    comment = b[off + 0x2c:off + 0x6c].split(b"\0")[0].decode(errors="replace")
    psize, pclass = struct.unpack_from("<I4s", b, off + 0x8c)
    return dict(hsize=hsize, ver=ver >> 24, flags=flags, seg=seg, comment=comment,
                payload_size=psize, pclass=pclass.decode(errors="replace"))


def elements(v):
    """Walk a binary table as thermald does: [u32 type][u64 value | u64 len + bytes]."""
    out, off = [], 0
    while off + 4 <= len(v):
        t = struct.unpack_from("<I", v, off)[0]
        off += 4
        if t == 4:
            out.append(struct.unpack_from("<Q", v, off)[0])
            off += 8
        elif t == 8:
            n = struct.unpack_from("<Q", v, off)[0]
            off += 8
            out.append(v[off:off + n].split(b"\0")[0].decode(errors="replace"))
            off += n
        elif t == 7:
            n = struct.unpack_from("<Q", v, off)[0]
            off += 8
            raw = v[off:off + n]
            out.append(str(uuid.UUID(bytes_le=raw)) if n == 16 else raw.hex())
            off += n
        else:
            out.append(f"<type {t} at {off - 4}: thermald would fail here>")
            break
    return out


def dump_keys(b, start, end, indent="  "):
    off = start
    while off < end:
        sig = struct.unpack_from("<H", b, off)[0]
        if sig == SIG_HEADER:
            h = header(b, off)
            print(f"{indent}[nested DV seg={h['seg']!r} comment={h['comment']!r} "
                  f"class={h['pclass']} payload={h['payload_size']}]")
            dump_keys(b, off + h["hsize"], off + h["hsize"] + h["payload_size"], indent + "  ")
            off += h["hsize"] + h["payload_size"]
            continue
        if sig != SIG_KEY:
            print(f"{indent}!! unknown signature 0x{sig:04x} at {off}")
            return
        off += 2
        kflags, klen = struct.unpack_from("<II", b, off)
        off += 8
        key = b[off:off + klen].split(b"\0")[0].decode(errors="replace")
        off += klen
        vtype, vlen = struct.unpack_from("<II", b, off)
        off += 8
        val = b[off:off + vlen]
        off += vlen
        tname = TYPES.get(vtype, str(vtype))
        if vtype == 3:
            shown = struct.unpack_from("<I", val)[0]
        elif vtype == 4:
            shown = struct.unpack_from("<Q", val)[0]
        elif vtype == 8:
            shown = val.split(b"\0")[0].decode(errors="replace")
        elif vtype == 7:
            shown = elements(val)
        else:
            shown = val.hex()
        print(f"{indent}{key} ({tname}, {vlen}B) = {shown}")


def main():
    b = open(sys.argv[1], "rb").read()
    h = header(b, 0)
    print(f"GDDV: {h}")
    body = b[h["hsize"]:h["hsize"] + h["payload_size"]]
    if h["flags"] & COMPRESSED:
        props = body[0]
        dict_size, usize = struct.unpack_from("<IQ", body, 1)
        body = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(body)
        print(f"LZMA-alone payload: props=0x{props:02x} dict={dict_size} "
              f"declared={usize} got={len(body)}")
    if "--raw" in sys.argv:
        sys.stdout.buffer.write(body)
        return
    dump_keys(body, 0, len(body))


if __name__ == "__main__":
    main()
