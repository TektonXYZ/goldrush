"""WOFF1 -> TTF/OTF (sfnt) so Blender/sharp/Pango can load the project's @fontsource faces for decals.

    python3 assets/machines_a/woff2ttf.py in.woff out.ttf
"""
import struct
import sys
import zlib


def convert(src, dst):
    data = open(src, "rb").read()
    sig, flavor, length, num_tables = struct.unpack(">4sIIH", data[:14])
    if sig != b"wOFF":
        raise SystemExit(f"{src}: not a WOFF1 file")
    entries = []
    for i in range(num_tables):
        tag, off, comp, orig, csum = struct.unpack(">4sIIII", data[44 + i * 20:64 + i * 20])
        raw = data[off:off + comp]
        entries.append((tag, csum, zlib.decompress(raw) if comp < orig else raw))
    entries.sort(key=lambda e: e[0])
    es = max(k for k in range(16) if 2 ** k <= num_tables)
    sr = 2 ** es * 16
    head = struct.pack(">IHHHH", flavor, num_tables, sr, es, num_tables * 16 - sr)
    offset = 12 + 16 * num_tables
    records, blobs = b"", b""
    for tag, csum, blob in entries:
        records += struct.pack(">4sIII", tag, csum, offset, len(blob))
        pad = (4 - len(blob) % 4) % 4
        blobs += blob + b"\0" * pad
        offset += len(blob) + pad
    open(dst, "wb").write(head + records + blobs)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
