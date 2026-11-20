# mine-kit.glb: node reference

`public/models/mine-kit.glb` (4122 KB, meshopt). Generated from `build/stats.json` by `gen_nodes.py`; rebuild with `bl assets/minekit/build.py` (inside the memory cage) and re-run this script.

## Conventions (read first)

- Metres, three.js axes (Y up). Every node is a **root node with an identity transform**; its front faces **+Z**. Place with `obj.position.set(...)`, `obj.rotation.y = yaw`.
- **Kinds** (column *kind* below):
  - floor: origin at the bottom centre
  - wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
  - hang: origin at the hang point on top, item hangs down -Y
  - tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- **Reference drift profile** (what the tunnel pieces are built around): walls at x = ±2.2 vertical up to y = 2.5, elliptical arch to the crown at y = 3.8. `timber_set` posts stand at x ≈ ±1.9 (outer faces ±2.05), cap underside y = 2.80, cap top 3.10, roof lagging on top up to 3.15: clear opening 3.55 m wide × 2.80 m high. Cap ends are meant to disappear into the rock (hitches).
- **Rails**: `rail_2m` gauge 0.6 m (rail heads at x = ±0.3125), **rail top y = 0.200**, sleepers every 0.667 m so 2 m pieces tile seamlessly. `ore_cart` origin = wheel/rail contact plane: place it at **y = 0.200** on the rails (flanges reach 0.022 below). Wheel children spin about local X.
- **Run pieces** `cable_2m`, `vent_duct_2m`, `pipe_2m`: place them every 2 m at the same transform as the drift centreline (they sit at their position in the profile: cable on the −X rib at 1.95 m, duct in the upper +X corner, pipes low on the +X rib; looking along +Z, +X is on your LEFT). Rotate yaw π to mirror onto the other side. Sags/hangers/couplings line up at the tile joints.
- **Duplicate child names**: three.js `GLTFLoader` makes names unique across the file (`bulb`, `bulb_1`, `bulb_2`...). The glTF keeps the exact contract names and the loader copies them to `userData.name`, so look children up with:
  ```ts
  const find = (root: THREE.Object3D, n: string) => { let r: THREE.Object3D | undefined;
    root.traverse(o => { if (!r && (o.userData.name ?? o.name) === n) r = o; }); return r; };
  ```
  (or have `Assets.model()` do `o.name = o.userData.name ?? o.name` on every descendant of a clone).
- **Materials**: library names (swapped at load by `materials.ts`). Kept as exported: `label_minekit` (one 2048² decal atlas for every sign/sticker/stencil/gauge face, alpha MASK, single-sided), `custom_expanded_metal`, `custom_mesh_weld` (alpha-cut, double-sided wire mesh), `custom_chequer_plate` (cage floor).
- **UVs**: metres everywhere a library material is used; on wood the grain/long axis runs along **U**. **COLOR_0** = baked grime (AO + floor dirt + blotches; 1 = clean) on every mesh except emissive children, screens, buttons and the needle.
- **Screens / painted faces** (`screen`, `panel_screen`, `board_face`, `face`): one quad, UV 0–1 over the face in the glTF convention: uv (0,0) = **top-left as seen from the front**. A `CanvasTexture` needs `flipY = false`; a render-target texture needs its V flipped (`tex.repeat.y = -1; tex.offset.y = 1`).
- **Fuel gauge**: `gauge_needle` sits inside the empty `gauge_mount` (pre-rotated 180° about Y so the needle sweeps clockwise as seen from the front). Drive only the needle: `needle.rotation.z = THREE.MathUtils.degToRad(-120 + 240 * fuel)`: −120° = E (8 o'clock, red zone), 0 = ½ (up), +120° = F (4 o'clock). The dial art matches this.
- **Lights**: `bulb`, `cage_light`, `status_light` are separate emissive meshes; put the game's point lights at their world positions. `shaft_frame` also carries one small emissive bulkhead lamp per 4 m segment.

## Placement cheat sheet

| What | How |
|---|---|
| Timbered drift | `timber_set` every **1.5 m** along +Z; each set's lagging spans to the next set toward +Z |
| Steel drift (iron) | `steel_arch` every 1.2–1.5 m; `mesh_panel` / `bolt_plate` on the rock for silver |
| Track | `rail_2m` every 2 m (centred on its own x); `rail_bumper` at the end, same transform as a rail piece |
| Cable / duct / pipes | every 2 m at the drift centreline transform (see Run pieces) |
| Lantern | hang under a cap beam: origin at y = 2.80 (cap underside), every ~4.5 m |
| Shaft | `shaft_frame` every **4 m** vertically, cage centred; use `shaft_frame_landing` (extra) at landings: its +Z side is open and the upper +Z plate is raised to 2.62 m |
| Cage | `elevator_cage` centred in the shaft; walking surface at **y = 0.18** above its origin; gate on +Z, slide the `gate` child **+1.12 m along local X** to open (door opening x −1.12..0) |
| Call panel | on the shaft collar/landing wall next to the gate, origin at ~1.35 m height |
| Alcove shoring | origin at the alcove **mouth** floor centre; the alcove and its shoring extend toward **+Z**, the work face is at z = 9 (shoring_4: 12). Clear envelope kept free for machines: x ±2.8, y ≤ 3.95 (shoring_4: x ±4.0, y ≤ 5.7) |

## Nodes

| node | kind | size W × H × D (m) | tris | children / empties |
|---|---|---|---|---|
| `timber_set` | tunnel | 4.42 × 3.15 × 1.71 | 2304 | – |
| `steel_arch` | tunnel | 4.32 × 3.83 × 0.36 | 3404 | – |
| `bolt_plate` | wall | 0.15 × 0.15 × 0.09 | 424 | – |
| `mesh_panel` | wall | 2.00 × 2.00 × 0.01 | 128 | – |
| `rail_2m` | tunnel | 1.50 × 0.20 × 2.00 | 2444 | ballast |
| `rail_bumper` | tunnel | 1.01 × 0.47 × 0.84 | 1274 | – |
| `ore_cart` | floor | 1.02 × 1.12 × 2.02 | 5148 | wheel_0, wheel_1, wheel_2, wheel_3 |
| `lantern` | hang | 0.18 × 0.68 × 0.18 | 2558 | bulb |
| `bulb_cage` | hang | 0.12 × 0.64 × 0.12 | 1360 | bulb |
| `cable_2m` | tunnel | 0.17 × 0.15 × 2.00 | 1024 | – |
| `vent_duct_2m` | tunnel | 0.80 × 0.85 × 2.00 | 2232 | – |
| `pipe_2m` | tunnel | 0.19 × 0.92 × 2.04 | 1648 | – |
| `generator` | floor | 4.20 × 2.69 × 1.62 | 9270 | exhaust, snd, status_light |
| `fuel_tank` | floor | 2.84 × 1.92 × 1.35 | 4756 | gauge_mount, gauge_needle |
| `desk` | floor | 1.61 × 1.00 × 0.84 | 3004 | – |
| `office_chair` | floor | 0.70 × 1.01 × 0.71 | 3484 | – |
| `monitor` | floor | 0.62 × 0.54 × 0.31 | 1604 | screen |
| `pc_tower` | floor | 0.23 × 0.49 × 0.79 | 1482 | – |
| `keyboard` | floor | 0.32 × 0.03 × 0.45 | 964 | – |
| `desk_lamp` | floor | 0.18 × 0.53 × 0.56 | 1672 | bulb |
| `tool_rack` | wall | 1.46 × 1.56 × 0.29 | 1340 | – |
| `lockers` | floor | 1.20 × 2.07 × 0.55 | 2366 | – |
| `first_aid` | wall | 0.43 × 0.50 × 0.19 | 302 | – |
| `phone_box` | wall | 0.34 × 1.25 × 0.28 | 1430 | – |
| `map_board` | wall | 1.60 × 1.08 × 0.09 | 702 | board_face |
| `ore_bin` | floor | 1.40 × 1.15 × 1.48 | 1766 | fill |
| `elevator_cage` | floor | 2.66 × 3.06 × 2.65 | 8608 | cage_light, gate |
| `shaft_frame` | floor | 3.40 × 4.01 × 3.46 | 5632 | – |
| `call_panel` | wall | 0.38 × 1.18 × 0.18 | 1636 | btn_1, btn_2, btn_3, btn_4, panel_screen |
| `shoring_1` | floor | 7.13 × 4.37 × 7.77 | 5360 | – |
| `shoring_2` | floor | 6.94 × 4.44 × 8.46 | 5740 | – |
| `shoring_3` | floor | 6.95 × 1.97 × 9.12 | 4518 | – |
| `shoring_4` | floor | 10.11 × 6.38 × 11.20 | 7184 | – |
| `rubble_wall` | floor | 4.60 × 3.96 × 2.70 | 3322 | – |
| `explosives_crate` | floor | 0.70 × 0.35 × 0.44 | 984 | – |
| `detonator` | floor | 0.46 × 0.51 × 0.71 | 854 | – |
| `barrel` | floor | 0.61 × 0.88 × 0.61 | 844 | – |
| `crate` | floor | 1.01 × 0.73 × 0.87 | 1070 | – |
| `pallet` | floor | 1.21 × 0.14 × 0.80 | 880 | – |
| `sign_danger` | wall | 0.62 × 0.44 × 0.01 | 126 | – |
| `sign_exit` | wall | 0.58 × 0.34 × 0.06 | 198 | – |
| `sign_level` | wall | 0.90 × 0.50 × 0.03 | 286 | face |
| `fan_unit` | floor | 1.23 × 1.13 × 1.55 | 4232 | blades |
| `light_stand` | floor | 0.97 × 2.40 × 0.88 | 852 | bulb |
| `wheelbarrow` | floor | 0.68 × 0.64 × 1.88 | 818 | – |
| `helmet_rack` | wall | 1.10 × 0.40 × 0.27 | 2610 | – |
| `stretcher` | floor | 0.60 × 0.13 × 2.12 | 666 | – |
| `water_tank` | floor | 0.74 × 1.55 × 0.86 | 1544 | – |
| `shaft_frame_landing` | floor | 3.39 × 4.01 × 3.47 | 4840 | – |
| **total** | | | **120894** | |

## Details

### `timber_set`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (-2.214, 0.000, -0.195), max (2.209, 3.149, 1.512); size 4.42 × 3.15 × 1.71 m; 2304 tris
- materials: steel_dark, wood_planks, wood_timber

### `steel_arch`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (-2.160, 0.000, -0.180), max (2.160, 3.829, 0.180); size 4.32 × 3.83 × 0.36 m; 3404 tris
- materials: steel_dark, wood_timber

### `bolt_plate`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.075, -0.075, -0.000), max (0.075, 0.075, 0.088); size 0.15 × 0.15 × 0.09 m; 424 tris
- origin = rock surface at the bolt; plate faces +Z
- materials: galvanized, steel_dark

### `mesh_panel`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-1.000, -1.000, 0.009), max (1.000, 1.000, 0.019); size 2.00 × 2.00 × 0.01 m; 128 tris
- 2 x 2 m welded mesh sheet (alpha-cut custom_mesh_weld, double-sided), origin = back centre, faces +Z
- materials: custom_mesh_weld

### `rail_2m`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (-0.750, 0.000, -1.000), max (0.750, 0.200, 1.000); size 1.50 × 0.20 × 2.00 m; 2444 tris
- child `ballast` (mesh) at (0.000, 0.000, -0.000), 776 tris, gravel
- materials: gravel, rust, steel, steel_dark, wood_timber

### `rail_bumper`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (-0.507, 0.192, -0.640), max (0.502, 0.660, 0.205); size 1.01 × 0.47 × 0.84 m; 1274 tris
- end-of-track stop clamped to the 0.6 m rails; same frame as rail_2m, buffer faces +Z
- materials: label_minekit, paint_yellow, steel_dark, wood_timber

### `ore_cart`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.510, -0.022, -1.004), max (0.510, 1.100, 1.019); size 1.02 × 1.12 × 2.02 m; 5148 tris
- origin = rail-top contact plane (place at y=0.200 on rail_2m, wheel flanges reach 0.022 below it); wheel_0..3 spin about local X (roll forward = positive rotation.x for +Z travel)
- child `wheel_0` (mesh) at (-0.312, 0.150, 0.360), 356 tris, cast_iron, steel, steel_dark
- child `wheel_1` (mesh) at (0.312, 0.150, 0.360), 356 tris, cast_iron, steel, steel_dark
- child `wheel_2` (mesh) at (-0.312, 0.150, -0.360), 356 tris, cast_iron, steel, steel_dark
- child `wheel_3` (mesh) at (0.312, 0.150, -0.360), 356 tris, cast_iron, steel, steel_dark
- materials: cast_iron, label_minekit, paint_red, rust, steel, steel_dark

### `lantern`

- kind: hang: origin at the hang point on top, item hangs down -Y
- bounds (three.js): min (-0.088, -0.648, -0.088), max (0.088, 0.035, 0.088); size 0.18 × 0.68 × 0.18 m; 2558 tris
- origin = screw-eye hang point (top); hang it under a cap beam
- child `bulb` (mesh) at (0.000, -0.513, -0.000), 192 tris, emit_warm
- materials: brass, cable, emit_warm, galvanized, glass, paint_green, steel_dark

### `bulb_cage`

- kind: hang: origin at the hang point on top, item hangs down -Y
- bounds (three.js): min (-0.060, -0.643, -0.059), max (0.060, 0.000, 0.059); size 0.12 × 0.64 × 0.12 m; 1360 tris
- origin = ceiling/cap attachment point; child bulb = lamp position
- child `bulb` (mesh) at (0.000, -0.497, -0.000), 160 tris, emit_warm
- materials: cable, emit_warm, galvanized, plastic_black, steel

### `cable_2m`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (-2.230, 1.813, -1.000), max (-2.058, 1.967, 1.000); size 0.17 × 0.15 × 2.00 m; 1024 tris
- drift frame: J-hook in the -X rib (x=-2.2) at y=1.95 m (below timber_set's side lagging), power cable + red comms cable sag to the tile joints at z=+-1. Rotate yaw pi for the +X rib.
- materials: cable, galvanized, hose_red, label_minekit, plastic_black, plastic_yellow

### `vent_duct_2m`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (0.906, 1.948, -1.000), max (1.704, 2.800, 1.000); size 0.80 × 0.85 × 2.00 m; 2232 tris
- drift frame: 0.8 m duct centred x=+1.30, y=2.36 (upper +X corner), hung from a messenger wire at y=2.79 (just under the timber caps); hangers at z=+-0.5 so 2 m tiles repeat seamlessly. Rotate yaw pi for the -X side.
- materials: galvanized, hose_yellow, steel_dark

### `pipe_2m`

- kind: tunnel: drift frame (x = 0 centreline, floor y = 0, runs along Z)
- bounds (three.js): min (2.034, 0.403, -1.000), max (2.226, 1.323, 1.045); size 0.19 × 0.92 × 2.04 m; 1648 tris
- drift frame: compressed-air (blue, 114 mm) at x=+2.13 y=1.25 and water (green, 60 mm) at x=+2.15 y=0.86 on a bracket in the +X rib (x=+2.2); coupling at z=+1 (tile joint), air outlet valve at z=-0.5.
- materials: brass, galvanized, paint_blue, paint_green, paint_red, steel, steel_dark

### `generator`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-2.234, 0.000, -0.742), max (1.969, 2.695, 0.881); size 4.20 × 2.69 × 1.62 m; 9270 tris
- Ironside IP-150 genset, long axis X, control panel + doors on the +Z face; empties exhaust (tailpipe tip, smoke up +Y) and snd (engine centre); child status_light (emit_green) on the control panel
- child `exhaust` (empty) at (1.330, 2.690, -0.280)
- child `snd` (empty) at (0.000, 1.000, -0.000)
- child `status_light` (mesh) at (-1.050, 1.550, 0.760), 72 tris, emit_green
- materials: brass, cable, emit_green, label_minekit, paint_black, paint_green, paint_red, paint_yellow, plastic_black, rubber, rust, steel, steel_dark

### `fuel_tank`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-1.275, 0.000, -0.675), max (1.562, 1.916, 0.675); size 2.84 × 1.92 × 1.35 m; 4756 tris
- 2000 L bunded diesel tank; gauge on the +Z face: gauge_needle (inside empty gauge_mount, which is pre-rotated 180 deg about Y) turns about its local Z: rotation.z = -120 deg empty (E, left) .. +120 deg full (F, right), 0 = half
- child `gauge_mount` (empty) at (-0.200, 1.042, 0.666)
- child `gauge_needle` (mesh) at (-0.200, 1.042, 0.666), 68 tris, paint_red, paint_black
- materials: brass, galvanized, glass, label_minekit, paint_black, paint_green, paint_grey, paint_red, rubber, steel, steel_dark

### `desk`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.805, 0.000, -0.405), max (0.805, 1.001, 0.431); size 1.61 × 1.00 × 0.84 m; 3004 tris
- site-office desk, top at y=0.76; keep x in [-0.45, 0.45] of the top free for monitor/keyboard
- materials: aluminium, emit_green, helmet_yellow, label_minekit, paint_black, paint_grey, paint_white, plastic_black, rubber, steel, wood_dark

### `office_chair`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.353, 0.007, -0.402), max (0.353, 1.017, 0.305); size 0.70 × 1.01 × 0.71 m; 3484 tris
- worn vinyl office chair, seat at y=0.48, faces +Z
- materials: canvas, chrome, leather, plastic_black, steel, steel_dark

### `monitor`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.312, -0.003, -0.224), max (0.312, 0.538, 0.090); size 0.62 × 0.54 × 0.31 m; 1604 tris
- rugged 24in monitor; child screen = 0.531 x 0.299 m display, emit_screen, UV 0-1 (glTF convention: uv(0,0) = top-left as seen from the front; CanvasTexture flipY=false)
- child `screen` (mesh) at (0.000, 0.340, 0.035), 2 tris, emit_screen
- materials: cable, emit_green, emit_screen, glass_dark, label_minekit, plastic_black, rubber, steel, steel_dark

### `pc_tower`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.115, 0.000, -0.491), max (0.115, 0.490, 0.302); size 0.23 × 0.49 × 0.79 m; 1482 tris
- rugged industrial PC tower, front panel faces +Z
- materials: cable, emit_green, label_minekit, paint_black, plastic_black, rubber, steel, steel_dark

### `keyboard`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.157, -0.003, -0.375), max (0.157, 0.031, 0.075); size 0.32 × 0.03 × 0.45 m; 964 tris
- rugged compact keyboard, 77 keys with legends (label_minekit), faces +Z
- materials: cable, label_minekit, plastic_black, rubber, steel_dark

### `desk_lamp`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.088, 0.000, -0.138), max (0.088, 0.529, 0.418); size 0.18 × 0.53 × 0.56 m; 1672 tris
- articulated desk lamp; child bulb (emit_warm) inside the shade, shade aims down/+Z
- child `bulb` (mesh) at (0.000, 0.420, 0.309), 96 tris, emit_warm
- materials: emit_warm, paint_black, paint_green, steel

### `tool_rack`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.741, -0.930, -0.002), max (0.723, 0.630, 0.284); size 1.46 × 1.56 × 0.29 m; 1340 tris
- wall rack: pickaxe, shovel, sledgehammer, pry bar on two timber rails; origin = wall surface at the rack centre, mount ~1.35 m
- materials: cast_iron, rust, steel, steel_dark, wood_timber

### `lockers`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.600, 0.000, -0.250), max (0.600, 2.070, 0.298); size 1.20 × 2.07 × 0.55 m; 2366 tris
- bank of four steel lockers (numbered 01-04) on a plinth, doors on +Z
- materials: brass, helmet_white, label_minekit, paint_black, paint_grey, plastic_black, steel, steel_dark, wood_planks

### `first_aid`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.220, -0.250, -0.000), max (0.210, 0.250, 0.190); size 0.43 × 0.50 × 0.19 m; 302 tris
- wall first-aid cabinet, origin = back centre, mount ~1.4 m
- materials: label_minekit, paint_green, steel, steel_dark

### `phone_box`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.170, -0.830, -0.000), max (0.170, 0.420, 0.280); size 0.34 × 1.25 × 0.28 m; 1430 tris
- emergency mine phone in a hooded box with a strobe, origin = back centre, mount ~1.45 m
- materials: cable, emit_red, label_minekit, paint_orange, paint_white, plastic_black, steel, steel_dark

### `map_board`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.800, -0.540, -0.000), max (0.800, 0.540, 0.085); size 1.60 × 1.08 × 0.09 m; 702 tris
- framed mine-plan board, child board_face (sign_face, UV 0-1, 1.5 x 0.98 m), origin = back centre, mount ~1.5 m
- child `board_face` (mesh) at (0.000, 0.000, 0.034), 2 tris, sign_face
- materials: paint_red, plastic_black, sign_face, steel_dark, wood_dark, wood_planks

### `ore_bin`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.700, 0.000, -0.600), max (0.700, 1.145, 0.880); size 1.40 × 1.15 × 1.48 m; 1766 tris
- hand-ore drop bin (rim at 1.12 m) on legs with a front chute; child fill = ore heap, origin on the bin floor (y=0.58): scale fill.scale.y 0 -> 1 for empty -> full (material coal_ore: swap per ore)
- child `fill` (mesh) at (0.000, 0.580, -0.000), 632 tris, coal_ore
- materials: coal_ore, galvanized, label_minekit, paint_yellow, plastic_black, rust, steel, steel_dark

### `elevator_cage`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-1.330, 0.000, -1.280), max (1.330, 3.060, 1.370); size 2.66 × 3.06 × 2.65 m; 8608 tris
- origin = bottom of the underframe; walking surface (chequer plate) at y=0.18; gate on the +Z face (door opening x -1.12..0.0): child gate slides +1.12 m along local X to open; guide shoes at x=+-1.30 (shaft guides at +-1.32); child cage_light (emit_warm) under the roof
- child `cage_light` (mesh) at (0.000, 2.685, -0.350), 96 tris, emit_warm
- child `gate` (mesh) at (-0.560, 0.210, 1.300), 480 tris, paint_yellow, custom_expanded_metal, steel, steel_dark, label_minekit
- materials: brass, canvas, cast_iron, custom_chequer_plate, custom_expanded_metal, emit_warm, label_minekit, paint_red, paint_yellow, rubber, steel, steel_dark, wood_dark

### `shaft_frame`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-1.693, -0.002, -1.739), max (1.710, 4.006, 1.725); size 3.40 × 4.01 × 3.46 m; 5632 tris
- 3.4 x 3.4 x 4 m timber shaft lining, stack every 4 m (sets at y=0 and 2); guides (steel) on the +-X sides with running faces at x=+-1.32; lagged on all four sides
- materials: cable, cast_iron, emit_warm, galvanized, hose_red, steel, steel_dark, wood_dark, wood_planks, wood_timber

### `call_panel`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.190, -0.860, -0.002), max (0.190, 0.320, 0.180); size 0.38 × 1.18 × 0.18 m; 1636 tris
- wall box, origin = back centre at the wall, faces +Z; children btn_1..btn_4 (push along local -Z to press; swap their material to emit_green/emit_red for lit states) and panel_screen (emit_screen, UV 0-1 glTF convention)
- child `btn_1` (mesh) at (0.100, 0.030, 0.134), 128 tris, paint_green
- child `btn_2` (mesh) at (0.100, -0.055, 0.134), 128 tris, paint_green
- child `btn_3` (mesh) at (0.100, -0.140, 0.134), 128 tris, paint_green
- child `btn_4` (mesh) at (0.100, -0.225, 0.134), 128 tris, paint_green
- child `panel_screen` (mesh) at (0.000, 0.120, 0.146), 2 tris, emit_screen
- materials: cable, emit_screen, glass_dark, label_minekit, paint_green, paint_yellow, plastic_black, steel, steel_dark

### `shoring_1`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-3.568, -0.003, 0.241), max (3.565, 4.371, 8.010); size 7.13 × 4.37 × 7.77 m; 5360 tris
- coal face: round timber props + square headers at z = 0.4/3.3/6.2 with roof boards, two log cribs near the mouth, face props at z = 7.9; keeps x +-2.8, y <= 4.0 clear
- materials: steel_dark, wood_planks, wood_timber

### `shoring_2`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-3.470, 0.000, 0.270), max (3.470, 4.438, 8.730); size 6.94 × 4.44 × 8.46 m; 5740 tris
- iron: four horseshoe I-beam arches (z = 0.4/3.2/6.0/8.6) with timber lagging between them on the roof and shoulders, spreader bars at the legs; keeps x +-2.8, y <= 3.95 clear
- materials: steel_dark, wood_planks

### `shoring_3`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-3.474, 2.519, -0.117), max (3.474, 4.486, 9.000); size 6.95 × 1.97 × 9.12 m; 4518 tris
- silver: welded mesh over the upper walls and roof of the nominal alcove (walls x = +-3.5 vertical to 3.3, elliptical arch to 4.5; inset 3 cm), rock bolts with domed plates on a ~1.1 m grid, W-straps across the roof
- materials: custom_mesh_weld, galvanized, steel_dark

### `shoring_4`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-5.050, 0.000, 0.150), max (5.060, 6.382, 11.350); size 10.11 × 6.38 × 11.20 m; 7184 tris
- gold: 10 x 6.5 x 12 m alcove, four heavy H-beam sets (z = 0.5/4.0/7.5/11.0) on concrete footings, knee braces, tie rods, timber roof lagging and steel wall lagging; keeps x +-4.0, y <= 5.7 clear
- materials: concrete, paint_yellow, steel_dark, wood_timber

### `rubble_wall`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-2.300, -0.061, -0.171), max (2.300, 3.900, 2.530); size 4.60 × 3.96 × 2.70 m; 3322 tris
- blasted broken rock filling the 4.4 x 3.8 drift; the pile face looks toward +Z, toe spills to z = +1.8; timber barricade with a DANGER sign at z = +2.3
- materials: gravel, label_minekit, paint_red, paint_white, rock, rock_dark, steel_dark, wood_planks, wood_timber

### `explosives_crate`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.352, 0.000, -0.220), max (0.352, 0.350, 0.220); size 0.70 × 0.35 × 0.44 m; 984 tris
- wooden case of explosives with stencils and the 1.1D diamond, rope handles
- materials: canvas, label_minekit, wood_dark, wood_planks

### `detonator`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.228, 0.000, -0.601), max (0.228, 0.507, 0.105); size 0.46 × 0.51 × 0.71 m; 854 tris
- plunger blasting machine (plunger up), terminals on top, brass plate on +Z
- materials: brass, cable, hose_red, label_minekit, steel, steel_dark, wood_dark, wood_timber

### `barrel`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.305, 0.000, -0.305), max (0.305, 0.884, 0.305); size 0.61 × 0.88 × 0.61 m; 844 tris
- 205 L steel drum (hydraulic oil label)
- materials: label_minekit, paint_blue, steel

### `crate`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.505, 0.000, -0.435), max (0.505, 0.735, 0.435); size 1.01 × 0.73 × 0.87 m; 1070 tris
- wooden shipping crate, stencilled IRONSIDE MINING CO.
- materials: label_minekit, wood_planks

### `pallet`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.605, -0.001, -0.401), max (0.605, 0.145, 0.402); size 1.21 × 0.14 × 0.80 m; 880 tris
- 1.2 x 0.8 m EUR pallet
- materials: wood_planks

### `sign_danger`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.310, -0.220, -0.000), max (0.310, 0.220, 0.010); size 0.62 × 0.44 × 0.01 m; 126 tris
- DANGER UNSUPPORTED GROUND / KEEP OUT plate, origin = back centre
- materials: label_minekit, paint_white, steel

### `sign_exit`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.290, -0.145, -0.000), max (0.290, 0.195, 0.062); size 0.58 × 0.34 × 0.06 m; 198 tris
- photoluminescent/lit EXIT sign in a housing (label glows on its own, also during power cuts), origin = back centre
- materials: label_minekit_glow, plastic_black, steel_dark

### `sign_level`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.450, -0.250, -0.000), max (0.450, 0.250, 0.028); size 0.90 × 0.50 × 0.03 m; 286 tris
- level sign; child face (sign_face, UV 0-1, 0.84 x 0.44 m) for the game to paint 'LEVEL 1 · COAL' etc., origin = back centre
- child `face` (mesh) at (0.000, 0.000, 0.021), 2 tris, sign_face
- materials: paint_black, sign_face, steel_dark

### `fan_unit`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.510, 0.000, -0.905), max (0.715, 1.130, 0.650); size 1.23 × 1.13 × 1.55 m; 4232 tris
- auxiliary axial fan (0.8 m duct size), blows toward +Z; child blades spins about local Z (hub centre)
- child `blades` (mesh) at (0.000, 0.620, 0.120), 876 tris, steel_dark, aluminium
- materials: aluminium, cable, label_minekit, paint_grey, paint_yellow, steel_dark

### `light_stand`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.463, 0.000, -0.604), max (0.505, 2.397, 0.280); size 0.97 × 2.40 × 0.88 m; 852 tris
- tripod work light; child bulb = lamp lens (emit_warm) aimed +Z and 20 deg down
- child `bulb` (mesh) at (0.000, 2.240, 0.083), 2 tris, emit_warm
- materials: aluminium, cable, emit_warm, label_minekit, paint_black, paint_yellow, plastic_black, rubber, steel_dark

### `wheelbarrow`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.340, -0.012, -0.991), max (0.340, 0.630, 0.885); size 0.68 × 0.64 × 1.88 m; 818 tris
- steel wheelbarrow, wheel toward +Z
- materials: paint_green, rubber, rust, steel, steel_dark

### `helmet_rack`

- kind: wall: origin at the centre of the back face (touching the wall), item sticks out toward +Z
- bounds (three.js): min (-0.551, -0.320, -0.001), max (0.553, 0.083, 0.271); size 1.10 × 0.40 × 0.27 m; 2610 tris
- timber rack with pegs, three hard hats and a cap lamp; origin = back centre, mount ~1.6 m
- materials: cable, glass, helmet_white, helmet_yellow, label_minekit, plastic_black, steel_dark, wood_dark, wood_timber

### `stretcher`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.300, 0.013, -1.060), max (0.300, 0.139, 1.060); size 0.60 × 0.13 × 2.12 m; 666 tris
- folding canvas rescue stretcher on its feet, head toward +Z
- materials: aluminium, canvas, label_minekit, leather, rubber, steel

### `water_tank`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-0.368, 0.000, -0.368), max (0.368, 1.550, 0.490); size 0.74 × 1.55 × 0.86 m; 1544 tris
- galvanised drinking-water tank on a stand with a tap and cup dispenser on +Z
- materials: brass, galvanized, label_minekit, paint_white, plastic_black, steel, steel_dark

### `shaft_frame_landing`

- kind: floor: origin at the bottom centre
- bounds (three.js): min (-1.698, -0.004, -1.816), max (1.694, 4.008, 1.654); size 3.39 × 4.01 × 3.47 m; 4840 tris
- EXTRA (not in contract): shaft_frame with the +Z (landing) side open and the upper +Z wall plate raised to 2.62-2.87 m so a cage door fits
- materials: cable, cast_iron, emit_warm, galvanized, hose_red, steel, steel_dark, wood_dark, wood_planks, wood_timber

