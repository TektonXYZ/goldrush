# town.glb nodes

`public/models/town.glb` (7.1 MB, 140k tris in total): 21 root nodes, all at the file origin with identity transforms. Built by
`assets/town/build.py` (Blender 5.2 + meshopt). Load a node with `Assets.model("town.glb#<name>")`.

**Coordinates are three.js, in the node's local frame.** +X is right, +Y is up, +Z is the **front** (the
street side; object yaw rotates +Z the way `shared/` describes). The origin is the ground centre of the
footprint. W = X extent, D = Z extent, H = Y extent, all in metres, including eaves and steps. Look up
children *inside* the cloned node (`node.getObjectByName("door")`): names like `door`, `board`,
`board_face` and `wheels_0` repeat across nodes.

Materials use the library names in `docs/CONTRACTS.md`. Signs are `label_*` (embedded textures, no
COLOR_0). Fake lit interiors behind the windows and open doors use `custom_interior`, an emissive
atlas (strength 1.4) that the library keeps as exported. The monument statue is `custom_bronze`, and
the telegraph insulators are `custom_insulator`. Every library-material mesh has metric UVs plus
COLOR_0 grime: a Cycles AO bake times per-board weathering, darker near the ground.

**Plank textures** (`wood_planks`, `wood_painted_*`): the photos' boards run along texture V, so `tk.py` maps the
grain to V and fits every board or trim piece up to 42 cm wide across exactly one board of the photo (joint
positions measured from the albedo, `tk.PLANK_SETS`). Painted clapboards and board-and-batten use the band of
the photo where the paint is whole (`arch.CLEAN_V`). Walking surfaces use `wood_timber` (`arch.DECK`).
The rubble foundations of the four wooden buildings and the depot go 12 cm below ground (bbox min y = -0.12).

## Main Street buildings (shared layout)
For all four shops, the facade wall is at **z = +4.0**. The covered porch / boardwalk deck runs from
z = 4.0 to 6.4, with its top at **y = 0.5** (assay office: 0.55). Two full-width steps go down to the
street at **z = +7.0**, so porch fronts line up when the buildings share a street line. The body runs
back from z = 4.0 to the back wall. A `door` empty marks the main door threshold.
`TOWN.doors.landOffice` (5.5 m in front of the origin) lands on the porch, 1.1 m in front of the doors.

| node | W x D x H | body (walls) | main door | children | tris |
|---|---|---|---|---|---|
| `land_office` | 11.0 x 15.3 x 10.8 | x +-5, z -7.0..4.0 | double doors standing OPEN over a lit office, x -0.85..0.85, sill y 0.5, transom glass lettered LAND OFFICE | `door` (0, 0.5, 4.37); `door_light` (0, 2.6, 2.8): put a warm PointLight here for light spill; `claims_board` (-3.15, 2.2, 6.27): the CLAIMS FOR SALE board, freestanding on the porch facing +Z | 17.0k |
| `assay_office` | 9.3 x 13.1 x 9.8 | brick, x +-4.5, z -6.0..4.0 | iron double doors, open, x -0.8..0.8; GOLD BOUGHT blade sign hangs at x -2.6, y 4.0, z 4.8 | `door` (0, 0.55, 4.4) | 9.3k |
| `general_store` | 14.0 x 17.6 x 10.8 | x +-6.5, z -9.0..4.0 | double glazed doors x -0.9..0.9 | `door` (0, 0.5, 4.42) | 18.0k |
| `saloon` | 13.0 x 15.9 x 11.0 | x +-6, z -8.0..4.0 | batwing doors in an open doorway, x -0.85..0.85, lit bar behind | `door` (0, 0.5, 4.42) | 19.3k |

Each building also has a `<name>_signs` child mesh that holds its label quads. Back doors: land office
x -1.9, saloon x -2.5, general store x -0.1 (double); each has a small stoop at the back wall.

## depot (railway station + platform)
- W x D x H **50.4 x 10.4 x 7.15**. The station building is x +-8, z -0.6..4.6 (street side +Z). The
  platform deck (top **y = 0.65**) runs x +-22, with ramps down to the ground at x = +-22..25.2.
- **Platform edge: z = -3.5**, running along X. **Rail centreline: z = -5.15** (empty `track` at
  (0, 0, -5.15)). Lay `track_10m` there with the same yaw as the depot, and place rolling stock at
  y = 0.47 on that line. That leaves an 8 cm gap from a car side to the platform edge.
- Children: `spawn` (4.0, 0.65, -2.4) is on the platform by the waiting-room door. `door_platform`
  (4.0, 0.65, -1.3) is the waiting-room door on the track side. `door_street` (3.6, 0.65, 5.2) is the
  street-side door; its porch spans x 2.2..5.0 with steps to z 6.6. The street-side wing steps are at
  x +-11.5, z 0.2..1.1. Also `depot_signs`.
- MOTHERLODE GULCH name boards: on both gable ends, on the street wall, and hanging under the
  track-side eave facing the track. A canopy covers the east platform (x 8.6..21.6). The luggage cart
  and freight sit at the west end.
- 17.9k tris.
- **Placement note:** `shared/town.ts` gives the depot yaw pi/2 with `railZ = 4` (a track along world
  X). For a track running along world X, use yaw 0 or pi so the platform edge runs along X.

## Rail
**RAIL_TOP = 0.47 m.** Rolling stock origins sit on the railhead plane (wheel contact, centred on the
vehicle). Its front faces **+Z** and its length runs along Z, so rotate it +-pi/2 to run on a track
laid along X. All `wheels_N` children are axle sets: the origin is at the axle centre and they spin
about local **X**. Positive `rotation.x` rolls the vehicle forward (toward its +Z front). Per frame:
`wheel.rotation.x += distance / r`.

| node | W x D x H | notes | tris |
|---|---|---|---|
| `track_10m` | 10.0 x 4.3 x 0.47 | Rails along **X**, x -5..5 (butt segments every 10 m). Gauge 1.435, rail centres z +-0.75, railhead y 0.47. 16 sleepers, tie plates, spikes, a mid-length fish-plated joint, and a ballast prism (top 3.0 m wide at y 0.22, toe 4.3 m). Child `railhead` (0, 0.47, 0). | 1.2k |
| `buffer_stop` | 3.0 x 4.3 x 2.5 | Origin = the rail end: rails run x 0..2.8 along +X, and the striped timber beam at x ~0.35, y 1.36 faces -X toward incoming trains. Put it at the far end of the last `track_10m` with the same yaw. Red lamp. | 0.8k |
| `locomotive` | 3.1 x 16.9 x 4.5 | 4-4-0 plus tender. Pilot tip at z +8.33, tender rear coupler at z -8.53. `wheels_0..7` at z 6.6, 5.4 (leading truck, r 0.394); 3.3, 0.9 (drivers, **r 0.7875**); -2.0, -3.5, -5.85, -7.35 (tender, r 0.394). Empty `smoke` (0, 4.46, 6.25) at the stack top. Rod children: `siderod_l/r`, `mainrod_l/r`, `crosshead_l/r`. **Clip `Run`** (1.0 s loop) = one driver revolution = 4.948 m travelled: it spins every wheel (small wheels 2x) and drives the rods and crossheads. Play it with `timeScale = speed / 4.948` (m/s) and don't spin the wheels yourself, or the rods won't follow. Headlamp face is `emit_warm`; tender lamp `emit_red`. | 19.5k |
| `coach` | 3.1 x 16.8 x 4.6 | Clerestory coach. End platforms at z +-7.4 (floor y 1.22, steps both sides), body z +-7.0. `wheels_0..3` at z 6.0, 4.5, -4.5, -6.0, r 0.42. 11 lit windows a side. | 7.4k |
| `boxcar` | 3.3 x 11.8 x 4.5 | Sliding doors (half open) mid-length on both sides. `wheels_0..3` at z 4.35, 2.85, -2.85, -4.35, r 0.42. | 6.2k |

Train order (front to back) with ~0.3 m coupler gaps: locomotive, coach, boxcar. Car centre spacing:
locomotive to coach 17.1 m, coach to boxcar 14.6 m.

## gas_station
- W x D x H **20 x 13 x 8.9**: a concrete pad x +-10, z -6..7.
- The canopy (12 x 8, underside y 5.0, `emit_white` light panels) is centred at (0, 5, 0.5), on 4 steel
  columns at x +-4.5, z 0.5 +- 2.6. Its fascia reads MOTHERLODE FUEL front and back.
- Pumps on two islands at x -2.2 and +2.2 (z 0.5): UNLEADED / DIESEL, `emit_green` displays, hoses,
  nozzles. Empties `pump_0` (-3.2, 0.12, 0.5) and `pump_1` (3.2, 0.12, 0.5) mark where to stand.
- The kiosk is x -9..-3.5, z -5.6..-2.2; its door (-4.7, 0.12, -2.2) faces +Z. Drum racks at x -9.4;
  ice chest.
- **Price pylon** at x 7.6, z 5.6 (the front-right corner), facing +Z. Child **`board_face`**: material
  `sign_face`, **UV 0-1, 3.2 m wide x 2.4 m tall (4:3 landscape)**, bottom edge y 5.45, top 7.85,
  face plane z = 5.685. It sits in a backlit `emit_white` frame under a red GAS header (y 7.9..8.9).
  Empty `board` (7.6, 6.65, 5.7) is the board centre.
- 6.8k tris.

## monument
- W x D x H **8.6 x 8.6 x 7.6**: octagonal granite steps (r 4.3; top step y 0.52), a granite plinth
  3.5 x 2.5 x 2.35, and a bronze 49er (pick on his shoulder, gold pan in hand, ~2.4 m tall, feet at
  y 4.6) facing +Z.
- Child **`board_face`**: `sign_face`, **UV 0-1, 3.0 x 2.0 m landscape**, in a brass frame on the
  plinth's **+Z face** (face plane z = 1.271, bottom y 1.26, top y 3.26). Empty `board`
  (0, 2.26, 1.28) is the board centre. Read it from about (0, 1.7, 4.5).
- Children: `monument_statue` (custom_bronze), `monument_signs` (the dedication plaque on the back
  face). Two lamp posts flank the front.
- 4.0k tris.

## Props
| node | W x D x H | notes | tris |
|---|---|---|---|
| `water_tower` | 5.9 x 8.3 x 11.9 | Railroad tank (r 2.6, floor at y 6.4) on a 4-leg timber trestle centred on the origin. Spout swings out toward +Z (to z 5.3), so line it up with a track. | 2.1k |
| `windmill` | 5.8 x 6.8 x 11.7 | Lattice tower centred on the origin, stock tank at (2.4, 0, 1.6). Child **`rotor`** at (0, 9.85, 0.68) faces +Z and **spins about its local Z**. | 2.6k |
| `telegraph_pole` | 4.0 x 0.8 x 8.7 | Two crossarms along X (z -0.13). Insulator tops at y 8.485 (x +-1.08, +-0.648, +-0.216) and y 7.685 (x +-0.78, +-0.26). Wire stubs run +-0.9 m along X: string wires between poles along X. Pole transformer. | 1.8k |
| `wagon` | 1.8 x 6.0 x 2.3 | Ore-loaded freight wagon, tongue toward +Z (to z 3.9). Rear wheels r 0.66, front r 0.52 (part of the mesh, not separate). | 2.8k |
| `bench` | 1.9 x 0.5 x 0.9 | Sitter faces +Z; seat top y 0.47. | 0.4k |
| `street_lamp` | 0.6 x 0.4 x 4.25 | Cast iron. Child **`bulb`** (`emit_warm`) at (0, 3.55, 0) is the lamp centre. | 0.8k |
| `boardwalk_4m` | 4.0 x 3.0 x 0.5 | Along X, x +-2, deck top **y 0.5** from z -1.5 (back = building line) to z 0.9, two steps to z +1.5 (street). With the shops' yaw, place segments at shop-local z = 5.5 to continue a porch line. | 0.4k |
| `barrels` | 1.3 x 2.0 x 0.9 | 3 standing, 1 lying. | 1.4k |
| `hitching_post` | 2.7 x 0.2 x 1.2 | Hewn rail along X (top y 1.02, posts to 1.2), two iron tie rings. | 0.4k |
