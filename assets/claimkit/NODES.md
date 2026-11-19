# Claim kit + nature: node reference

Files: `public/models/claim-kit.glb` (19 roots, 51.2k tris, 2.1 MB; polish pass 2026-10-15, see docs/polish/claims.md) and `public/models/nature.glb` (13 roots,
14.0k tris, 1.4 MB). Both use meshopt compression (EXT_meshopt_compression) and load in three.js with `MeshoptDecoder`.
Both pass `~/blender-kit/viewer/check.mjs` and `node assets/claimkit/inspect.mjs <glb>`, which checks every node
and child listed in CONTRACTS.md.

## Conventions (all nodes)
- Every root is a separate top-level node at the **identity transform**: origin = bottom centre of the footprint,
  **front faces +Z** (three.js), Y up, metres. Place a root with `position = spot`, `rotation.y = yaw`.
- Sizes below are three.js axes: **x width × y height × z depth**. "min/max" is the local bounding box, so +Z is the front.
- **Materials**: library names (`rock`, `wood_timber`, `corrugated`, ...) are meant to be swapped by
  `MaterialLibrary.apply`. Their exported factors are preview values only. `custom_*` and `label_*` materials carry
  embedded textures and must be kept as they are.
- **UV0 in metres** on library materials. Wood: U runs along each member's long axis (the grain). Corrugated sheets:
  the corrugations run along **V** (down the roof slope, vertical on walls). Rock and gravel use a world box projection.
- **COLOR_0** is greyscale grime/AO (1 = clean; a Cycles AO bake times per-plank variation), present on almost every
  mesh. It is absent from emissive bulbs and from the three sign faces. Emissive and glass faces inside a mesh carry 1.0.
- Emissive: the `emit_warm` children (bulbs) are separate nodes. Lit windows are `emit_warm` / `emit_amber` faces inside
  the building meshes (shack, hoist house, mill), so the game can drive their intensity by material.

## claim-kit.glb
| node | size x × y × z (m) | min (x,y,z) | max (x,y,z) | tris | children (local position) |
|---|---|---|---|---|---|
| portal | 17.5 × 13.3 × 9.2 | -8.75, -0.40, -5.00 | 8.71, 12.93, 4.15 | 9758 | portal_frame (0,0,0); bulb_l (-2.39, 2.89, 0.44); bulb_r (2.39, 2.89, 0.44) |
| shack | 5.1 × 5.0 × 5.6 | -2.36, 0.00, -1.90 | 2.73, 4.97, 3.65 | 4278 | shack_bulb (-1.69, 2.35, 1.83) |
| sign_company | 5.4 × 5.1 × 1.9 | -2.70, -0.02, -1.34 | 2.70, 5.07, 0.54 | 2140 | sign_face (0, 3.88, 0.17); plaque_face (0, 2.56, 0.20) |
| sign_forsale | 1.9 × 2.5 × 0.5 | -1.03, 0.00, -0.25 | 0.86, 2.50, 0.29 | 538 | forsale_face (0.06, 1.60, 0.03) |
| headframe_wood | 3.8 × 10.6 × 9.0 | -1.88, -0.06, -6.47 | 1.88, 10.56, 2.53 | 5434 | sheave (0, 9.66, 0.10) |
| headframe_steel | 5.1 × 16.3 × 9.2 | -2.55, -0.10, -5.97 | 2.57, 16.18, 3.20 | 6510 | sheave_0 (-0.62, 14.98, -0.20); sheave_1 (0.62, 14.98, -0.20); hoist_slot (0, 3.25, -5.95) |
| hoist_house | 6.6 × 6.8 × 5.1 | -3.80, 0.00, -2.55 | 2.77, 6.75, 2.55 | 2316 | cable_slot (0, 3.25, 2.25) |
| ore_bin | 3.0 × 6.3 × 5.0 | -1.50, -0.05, -2.23 | 1.50, 6.27, 2.80 | 3820 | - |
| conveyor | 2.7 × 6.7 × 13.7 | -1.36, -0.05, -6.57 | 1.36, 6.67, 7.13 | 2868 | - |
| mill | 8.2 × 18.0 × 11.1 | -4.08, -0.05, -5.22 | 4.07, 17.95, 5.85 | 5078 | stack_top (-2.60, 17.98, -3.85) |
| fuel_tank_small | 2.6 × 2.5 × 1.3 | -1.30, 0.00, -0.65 | 1.30, 2.50, 0.65 | 908 | - |
| ore_cart | 1.1 × 1.3 × 2.4 | -0.56, 0.00, -1.20 | 0.56, 1.27, 1.20 | 1536 | - |
| pile_coal | 3.5 × 1.3 × 2.8 | -1.65, -0.06, -1.33 | 1.80, 1.28, 1.43 | 2286 | - |
| pile_rock | 3.6 × 1.5 × 3.5 | -1.73, -0.07, -1.73 | 1.90, 1.40, 1.77 | 2326 | - |
| fence_2m | 2.1 × 1.4 × 0.2 | -1.08, 0.00, -0.08 | 1.04, 1.37, 0.16 | 308 | - |
| fence_post | 0.2 × 1.4 × 0.2 | -0.08, 0.00, -0.12 | 0.12, 1.37, 0.08 | 128 | - |
| lamp_post | 1.1 × 5.2 × 1.4 | -0.55, 0.00, -0.13 | 0.55, 5.20, 1.32 | 278 | bulb (0, 4.20, 1.06) |
| crates | 2.5 × 1.4 × 1.1 | -1.12, 0.00, -0.56 | 1.40, 1.40, 0.52 | 224 | - |
| keg | 0.6 × 0.9 × 0.6 | -0.29, 0.00, -0.30 | 0.29, 0.86, 0.30 | 444 | - |

### Per-node notes
- **portal**: origin = floor of the adit's front centre. The clear opening is 4.4 × 3.8 m, set in a square timber frame
  whose front face lies at z = 0. The root mesh is the rock face (rock; the tunnel stub is `rock_dark`). Its COLOR_0 fades
  to near-black down the 3 m stub, so the tunnel reads as deep. `portal_frame` holds the timber sets, headboards, the
  EST. 1849 board (`label_est1849`), cribbing wing walls, lanterns, and 0.6 m-gauge rails on sleepers. The rails run
  from z = -2.95 (inside) to z = +4.15 (out front) and end at a timber wheel stop. The rock wraps back to z = -5 at the
  sides and top so it can sink into a terrain wall. The rubble/talus apron reaches about z = +2.4 at |x| > 5.4 m.
  **Terrain must stay out of the tunnel stub**: keep the terrain wall surface at least 4 m behind the origin
  (z ≤ -4) over |x| < 8.5 m and y < 12 m. At minimum keep it clear of the box x ∈ [-3.1, 3.1], y ∈ [0, 5.4],
  z ∈ [-3.1, 0]. Otherwise the wall shows inside the adit; the vignette hit exactly this.
- **sign_company**: the claim's GATE: the path runs under it. Board 4.8 × 1.4 m with its bottom at 3.2 m on two posts,
  tied by knee braces + a tie beam at 2.97 m (no bracing in the opening, nothing below 2.3 m), under a small gable cap.
  `sign_face` is a 4.72 × 1.345 m quad (board front, z = +0.168) and `plaque_face` a 2.21 × 0.45 m quad hung on
  S-hooks (bottom 2.34 m). Both use `sign_face` with **UV exactly 0–1**: u runs left to right and v bottom to top as seen from the front.
  The exporter writes glTF convention (v down), so a CanvasTexture needs `flipY = false`. Each face floats 2–3 cm in
  front of its backing, inside a proud frame, so they don't z-fight at distance.
- **sign_forsale**: post with an arm; the board hangs from eye hooks. `forsale_face` is 1.3 × 0.79 m, `sign_face`, UV 0–1.
- **headframe_wood**: the shaft collar sits at local (0, 0, +1.0), with a dark pit quad and a kibble on the rope. The
  back legs and a small winch extend to z = -6.5, and the rope ends on the winch drum, so this node is self-contained.
  `sheave`: R 0.9 m, origin at the hub, **spins about local X**.
- **headframe_steel**: the shaft and cage sit at local (0, 0, +1.0). The back legs land at z = -5.0 (steep, so the pair
  fits a pad). `sheave_0` and `sheave_1` (R 1.2 m) spin about local X. The back ropes end at the empty **`hoist_slot`**
  (0, 3.25, -5.95). To make them enter the hoist house, give `hoist_house` the **same yaw** and put it at headframe-local
  **(0, 0, -8.2)**. Its `cable_slot` (0, 3.25, +2.25) then meets `hoist_slot`.
- **hoist_house**: a 4.8 × 4.4 m corrugated house (plus plinth and eaves). The cable slot is high in the front gable.
  It has lit side windows, a lit window in the back gable (the end a claim shows to the road), a sliding door, the
  DANGER sign (`label_danger`), a ridge ventilator, an engine stovepipe with a rain cap and a fuel line leaving the -X
  wall at ground level (it reaches x = -3.8).
- **ore_bin**: hopper floor at 2.8 m. The chute discharges toward +Z (front), lip at about (0, 1.95, +2.75): high enough
  to drop into a `conveyor`'s tail hopper (top 1.87 m) when the conveyor's tail sits under it.
- **conveyor**: runs along Z, 24°. The tail (low end, loading hopper, belt at y 1.05) is at the **back, z = -6**. The head
  (high end, belt at y 6.45, motor + gearbox, discharge hood and chute) is at the **front, z = +6**; it has no posts:
  knee struts hang it off a wall plate 1 m past the head pulley (z ≈ +7.1), i.e. off the building it feeds. Supports:
  tail stand, a straight bent at t 0.3, a splayed bent at t 0.6 (t = 0 tail … 1 head).
- **mill**: 7.1 × 9.7 m footprint: three halls stepping down toward the front (crusher house at the back, stamp hall
  with clerestory, front room with a sheet-iron sliding door and the claim OFFICE door + awning), a 17.5 m brick stack
  at the back-left corner (`stack_top` = empty at its mouth, for smoke) with a flue from the crusher house, one leach
  tank + launder at the front-right. A **feed hatch** on the crusher house's +X wall at local (3.43, 4.9–6.1, -3.35 to
  -4.65) faces +X. To feed it, use a `conveyor` with **yaw = mill yaw − 90°**, head 1 m clear of the wall: mill-local
  **(10.5, 0, −4.0)** puts the head pulley at x = 4.5 and its chute in the hatch.
- **fence_post**: the closing post for the open end of a run of `fence_2m` bays.
- **keg**: wooden barrel (bellied staves, three iron hoops, plank lid).
- **fence_2m**: one bay along X, with its post at x = -1 and the rails running to x = +1. Tile at 2 m steps and add one
  extra post at the open end.
- **ore_cart**: a side-tipping V-skip on its own 2.4 m section of 0.6 m-gauge track. Place it at portal-local
  (0, 0, +5.4) and it lines up with the portal rails, just beyond their wheel stop.

## nature.glb
| node | size x × y × z (m) | min (x,y,z) | max (x,y,z) | tris | notes |
|---|---|---|---|---|---|
| pine_a | 10.0 × 17.5 × 9.9 | -4.82, 0.00, -4.89 | 5.16, 17.54, 4.96 | 2268 | mature ponderosa: clear bole, rounded open crown |
| pine_b | 7.6 × 12.5 × 7.2 | -3.85, 0.00, -3.52 | 3.73, 12.48, 3.70 | 1544 | younger ponderosa |
| pine_c | 3.6 × 9.0 × 3.5 | -1.73, 0.00, -1.72 | 1.88, 8.99, 1.75 | 1484 | lodgepole: slim, narrow conical crown |
| pine_dead | 2.8 × 11.6 × 3.9 | -0.75, 0.00, -1.74 | 2.08, 11.62, 2.20 | 352 | grey snag, broken top (`custom_deadwood`) |
| bush_a | 2.9 × 1.5 × 2.7 | -1.35, -0.05, -1.31 | 1.53, 1.44, 1.36 | 92 | manzanita (cards) |
| bush_b | 1.9 × 1.0 × 1.9 | -0.93, -0.05, -0.97 | 0.99, 0.98, 0.93 | 88 | sagebrush (cards) |
| boulder_a | 1.3 × 0.6 × 1.0 | -0.58, -0.05, -0.47 | 0.68, 0.50, 0.49 | 1280 | granite, flat sunk base |
| boulder_b | 2.0 × 1.1 × 1.7 | -0.89, -0.10, -0.90 | 1.15, 1.02, 0.81 | 1280 | |
| boulder_c | 3.9 × 2.1 × 3.0 | -2.01, -0.37, -1.51 | 1.92, 1.71, 1.46 | 2560 | split granite boulder |
| rock_cluster | 4.5 × 0.9 × 4.6 | -2.07, -0.13, -2.42 | 2.39, 0.81, 2.20 | 2500 | 5 boulders + scree |
| log_pile | 2.0 × 1.4 × 3.3 | -1.00, -0.01, -1.70 | 1.00, 1.37, 1.61 | 408 | 10 logs with bark and growth-ring ends |
| stump | 1.9 × 0.7 × 1.8 | -0.96, -0.10, -0.92 | 0.97, 0.61, 0.88 | 154 | |
| grass_tuft | 0.9 × 0.7 × 0.9 | -0.43, -0.02, -0.47 | 0.43, 0.69, 0.47 | 8 | 4 crossed cards (instance heavily) |

- Foliage materials are **alphaMode MASK** and doubleSided: `custom_pine_needles` (cutoff 0.45, 1024² atlas),
  `custom_bush` (0.45), `custom_grass` (0.40). Each card is wound to face outward from the plant, and its normals are
  bent outward and up from the trunk axis for soft crown lighting. Grass normals point straight up so the tuft matches
  terrain lighting. COLOR_0 on trees is a procedural crown AO: inner and lower needles are darker, as is the trunk base.
  `alphaToCoverage` (with MSAA) will help the needles at distance.
- Trunks: `custom_bark` (ponderosa plates, albedo plus normal map), `custom_deadwood`, `custom_log_end`, all embedded JPEGs.
- Rocks are library `rock` with metre UVs (world box projection) and baked AO in COLOR_0.
- Nothing has collision geometry. Suggested colliders: trunk cylinder r ≈ 0.4 (pine_a), 0.3 (pine_b), 0.2 (pine_c);
  boulders by their bounding boxes.

## Rebuild
```
node assets/claimkit/textures.mjs                 # SVG textures (needles, bush, grass, labels); jpg re-encode
bl assets/claimkit/textures_np.py                 # numpy bark / deadwood / log-end (+ normal maps)
bl assets/claimkit/claimkit.py [-- nopreview]     # -> public/models/claim-kit.glb (+ out/claim-kit.blend, previews/)
bl assets/claimkit/nature.py [-- nopreview]       # -> public/models/nature.glb (+ out/nature.blend, previews/)
bl assets/claimkit/claimkit.py -- portal shack    # single nodes -> out/*-partial.glb + previews only
bl assets/claimkit/vignette.py                    # depth-4 claim vignette renders (previews/vignette_*.png)
bl assets/claimkit/lineup.py                      # previews/lineup_claimkit.png, previews/lineup_nature.png
node assets/claimkit/inspect.mjs public/models/claim-kit.glb public/models/nature.glb   # contract check (BOUNDS=1 for the tables)
```
Run Blender and Chromium inside `systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 ...` (CONTRACTS.md).
