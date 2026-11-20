"""Spread the built nodes on a grid and export build/lineup.glb (three.js visual check only; not a game asset)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import mk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "minekit.blend"))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
skip = set(argv[0].split(",")) if argv else set()
roots = [o for o in bpy.context.scene.objects if o.parent is None and o.name not in skip]
roots.sort(key=lambda o: o.name)
x = y = 0.0
row = 0.0
for o in roots:
    lo, hi = mk.tree_bounds(o)
    w, d = hi.x - lo.x, hi.y - lo.y
    if x + w > 16:
        x, y, row = 0.0, y - row - 1.2, 0.0
    o.location = Vector((x - lo.x, y - hi.y, -lo.z if lo.z < 0 else 0))
    x += w + 1.0
    row = max(row, d)
mk.export_glb(os.path.join(HERE, "build", "lineup.glb"), roots)
print("lineup", len(roots))
