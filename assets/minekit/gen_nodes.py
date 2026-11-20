"""Write assets/minekit/NODES.md from build/stats.json (run after every full build):  python3 assets/minekit/gen_nodes.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "build", "stats.json")))
glb = os.path.join(HERE, "..", "..", "public", "models", "mine-kit.glb")
size_kb = os.path.getsize(glb) / 1024 if os.path.exists(glb) else 0

KIND = {
    "floor": "floor: origin at the bottom centre",
    "wall": "wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z",
    "hang": "hang: origin at the hang point on top, item hangs down -Y",
    "tunnel": "tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)",
}


def f3(v):
    return " × ".join(f"{x:.2f}" for x in v)


def fv(v):
    return "(" + ", ".join(f"{x:.3f}" for x in v) + ")"


out = []
w = out.append
w("# mine-kit.glb: node reference")
w("")
w(f"`public/models/mine-kit.glb` ({size_kb:.0f} KB, meshopt). Generated from `build/stats.json` by `gen_nodes.py`; "
  "rebuild with `bl assets/minekit/build.py` (inside the memory cage) and re-run this script.")
w("")
w("## Conventions (read first)")
w("")
w("- Metres, three.js axes (Y up). Every node is a **root node with an identity transform**; its front faces **+Z**. "
  "Place with `obj.position.set(...)`, `obj.rotation.y = yaw`.")
w("- **Kinds** (column *kind* below):")
for k, v in KIND.items():
    w(f"  - {v}")
w("- **Reference drift profile** (what the tunnel pieces are built around): walls at x = ±2.2 vertical up to y = 2.5, "
  "elliptical arch to the crown at y = 3.8. `timber_set` posts stand at x ≈ ±1.9 (outer faces ±2.05), cap underside "
  "y = 2.80, cap top 3.10, roof lagging on top up to 3.15: clear opening 3.55 m wide × 2.80 m high. Cap ends are meant "
  "to disappear into the rock (hitches).")
w("- **Rails**: `rail_2m` gauge 0.6 m (rail heads at x = ±0.3125), **rail top y = 0.200**, sleepers every 0.667 m so "
  "2 m pieces tile seamlessly. `ore_cart` origin = wheel/rail contact plane: place it at **y = 0.200** on the rails "
  "(flanges reach 0.022 below). Wheel children spin about local X.")
w("- **Run pieces** `cable_2m`, `vent_duct_2m`, `pipe_2m`: place them every 2 m at the same transform as the drift "
  "centreline (they sit at their position in the profile: cable on the −X rib at 1.95 m, duct in the upper +X corner, "
  "pipes low on the +X rib; looking along +Z, +X is on your LEFT). Rotate yaw π to mirror onto the other side. Sags/hangers/couplings line up at the tile "
  "joints.")
w("- **Duplicate child names**: three.js `GLTFLoader` makes names unique across the file (`bulb`, `bulb_1`, `bulb_2`...). "
  "The glTF keeps the exact contract names and the loader copies them to `userData.name`, so look children up with:")
w("  ```ts")
w("  const find = (root: THREE.Object3D, n: string) => { let r: THREE.Object3D | undefined;")
w("    root.traverse(o => { if (!r && (o.userData.name ?? o.name) === n) r = o; }); return r; };")
w("  ```")
w("  (or have `Assets.model()` do `o.name = o.userData.name ?? o.name` on every descendant of a clone).")
w("- **Materials**: library names (swapped at load by `materials.ts`). Kept as exported: `label_minekit` (one 2048² "
  "decal atlas for every sign/sticker/stencil/gauge face, alpha MASK, single-sided), `custom_expanded_metal`, "
  "`custom_mesh_weld` (alpha-cut, double-sided wire mesh), `custom_chequer_plate` (cage floor).")
w("- **UVs**: metres everywhere a library material is used; on wood the grain/long axis runs along **U**. "
  "**COLOR_0** = baked grime (AO + floor dirt + blotches; 1 = clean) on every mesh except emissive children, screens, "
  "buttons and the needle.")
w("- **Screens / painted faces** (`screen`, `panel_screen`, `board_face`, `face`): one quad, UV 0–1 over the face in the "
  "glTF convention: uv (0,0) = **top-left as seen from the front**. A `CanvasTexture` needs `flipY = false`; a "
  "render-target texture needs its V flipped (`tex.repeat.y = -1; tex.offset.y = 1`).")
w("- **Fuel gauge**: `gauge_needle` sits inside the empty `gauge_mount` (pre-rotated 180° about Y so the needle sweeps "
  "clockwise as seen from the front). Drive only the needle: `needle.rotation.z = THREE.MathUtils.degToRad(-120 + 240 * "
  "fuel)`: −120° = E (8 o'clock, red zone), 0 = ½ (up), +120° = F (4 o'clock). The dial art matches this.")
w("- **Lights**: `bulb`, `cage_light`, `status_light` are separate emissive meshes; put the game's point lights at their "
  "world positions. `shaft_frame` also carries one small emissive bulkhead lamp per 4 m segment.")
w("")
w("## Placement cheat sheet")
w("")
w("| What | How |")
w("|---|---|")
w("| Timbered drift | `timber_set` every **1.5 m** along +Z; each set's lagging spans to the next set toward +Z |")
w("| Steel drift (iron) | `steel_arch` every 1.2–1.5 m; `mesh_panel` / `bolt_plate` on the rock for silver |")
w("| Track | `rail_2m` every 2 m (centred on its own x); `rail_bumper` at the end, same transform as a rail piece |")
w("| Cable / duct / pipes | every 2 m at the drift centreline transform (see Run pieces) |")
w("| Lantern | hang under a cap beam: origin at y = 2.80 (cap underside), every ~4.5 m |")
w("| Shaft | `shaft_frame` every **4 m** vertically, cage centred; use `shaft_frame_landing` (extra) at landings: "
  "its +Z side is open and the upper +Z plate is raised to 2.62 m |")
w("| Cage | `elevator_cage` centred in the shaft; walking surface at **y = 0.18** above its origin; gate on +Z, slide "
  "the `gate` child **+1.12 m along local X** to open (door opening x −1.12..0) |")
w("| Call panel | on the shaft collar/landing wall next to the gate, origin at ~1.35 m height |")
w("| Alcove shoring | origin at the alcove **mouth** floor centre; the alcove and its shoring extend toward **+Z**, the "
  "work face is at z = 9 (shoring_4: 12). Clear envelope kept free for machines: x ±2.8, y ≤ 3.95 (shoring_4: x ±4.0, "
  "y ≤ 5.7) |")
w("")
w("## Nodes")
w("")
w("| node | kind | size W × H × D (m) | tris | children / empties |")
w("|---|---|---|---|---|")
tot = 0
for name, st in S.items():
    tot += st["tris"]
    kids = ", ".join(sorted({c["name"] for c in st["children"]})) or "–"
    flag = " (blockout)" if st.get("blockout") else ""
    w(f"| `{name}`{flag} | {st['kind']} | {f3(st['size'])} | {st['tris']} | {kids} |")
w(f"| **total** | | | **{tot}** | |")
w("")
w("## Details")
w("")
for name, st in S.items():
    w(f"### `{name}`")
    w("")
    w(f"- kind: {KIND[st['kind']]}")
    w(f"- bounds (three.js): min {fv(st['min'])}, max {fv(st['max'])}; size {f3(st['size'])} m; {st['tris']} tris")
    if st.get("notes"):
        w(f"- {st['notes']}")
    for c in st["children"]:
        extra = f", {c['tris']} tris, {', '.join(c['mats'])}" if c["type"] == "mesh" else ""
        w(f"- child `{c['name']}` ({c['type']}) at {fv(c['pos'])}{extra}")
    w(f"- materials: {', '.join(st['materials'])}")
    w("")
open(os.path.join(HERE, "NODES.md"), "w").write("\n".join(out) + "\n")
print(f"NODES.md: {len(S)} nodes, {tot} tris")
