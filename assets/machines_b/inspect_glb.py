"""Structural report of a GLB (no dependencies): node tree, materials, images, COLOR_0 per mesh, clips.
    python3 assets/machines_b/inspect_glb.py public/models/machines/raiseborer.glb
"""
import json
import struct
import sys


def load(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + n])


def main(path):
    js = load(path)
    nodes = js["nodes"]
    meshes = js.get("meshes", [])
    mats = js.get("materials", [])
    kids = set(c for nd in nodes for c in nd.get("children", []))
    roots = [i for i in range(len(nodes)) if i not in kids]

    def walk(i, d=0):
        nd = nodes[i]
        info = ""
        if "mesh" in nd:
            m = meshes[nd["mesh"]]
            col = any("COLOR_0" in p["attributes"] for p in m["primitives"])
            info = f"  mesh[{len(m['primitives'])} prim{' +COLOR_0' if col else ''}]"
        print("  " * d + f"- {nd.get('name')}{info}")
        for c in nd.get("children", []):
            walk(c, d + 1)
    for r in roots:
        walk(r)
    print("materials:", ", ".join(m.get("name", "?") for m in mats))
    print("images:", ", ".join(f"{im.get('name')}({im.get('mimeType')})" for im in js.get("images", [])))
    for an in js.get("animations", []):
        print("clip", an["name"], "channels", len(an["channels"]))
    print("extensions:", js.get("extensionsUsed"))


if __name__ == "__main__":
    main(sys.argv[1])
