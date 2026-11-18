# Characters: miner.glb + viewmodel.glb

Built by the characters agent, 2026-10-13. Both files pass `~/blender-kit/viewer/check.mjs` (exit 0) and
`assets/characters/harness/shoot.mjs` (three.js AnimationMixer, real camera rules, exit 0).

| File | Source script | Tris | Materials | Clips |
|---|---|---|---|---|
| `public/models/viewmodel.glb` (1.1 MB) | `assets/characters/viewmodel.py` | 19,066 total (arms 8,590, pickaxe 1,706, steel pick 1,676, jackhammer 3,782, drill 2,704 + bit 608) | 16 | 11 |
| `public/models/characters/miner.glb` (0.7 MB) | `assets/characters/miner.py` | 14,670 total (skinned miner 13,688, props 982) | 7 on the miner mesh | 9 |

Rebuild (each inside the memory cage):
```
systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 bl assets/characters/viewmodel.py -- public/models/viewmodel.glb assets/characters/previews full
systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 bl assets/characters/miner.py -- public/models/characters/miner.glb assets/characters/previews full
NODE_PATH=node_modules systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 node assets/characters/harness/shoot.mjs assets/characters/previews/three
```
Shared modules: `ck.py` (mesh/IK/clip/export kit), `glove.py` (work glove + finger rig + grip solver),
`vmtools.py` (the four first-person tools). Editable sources: `viewmodel.blend`, `miner.blend`.

## Bone names (three.js sanitises them)
GLTFLoader strips dots from node names: `hand.R` is `handR`, `index.01.R` is `index01R`. Look bones up by
the sanitised name. Empties and props keep theirs (`grip_r`, `lamp`, `vm_pickaxe`, `held_pickaxe`, ...).

**miner (27):** `hips` (root, carries translation), `spine`, `chest`, `neck`, `head`, `shoulder.L/R`,
`upperarm.L/R`, `forearm.L/R`, `hand.L/R`, `fingers.L/R` (all four fingers, proximal), `fingertips.L/R`,
`thumb.L/R`, `thigh.L/R`, `shin.L/R`, `foot.L/R`, `toe.L/R`. Bind pose = A-pose.

**viewmodel (39):** `root`, `shoulder.L/R`, `upperarm.L/R`, `forearm.L/R`, `hand.L/R`, and per hand
`index|middle|ring|pinky|thumb` `.01/.02/.03`.

Every clip keys every bone (117 tracks per viewmodel clip, 81 per miner clip), so crossfades never leave a
bone stuck in the previous clip's pose. Verified: after a 0.25 s crossFadeTo, every bone matches the target
clip within 1 degree (pick_swing to hands_idle, Swing to Walk, Sit to Idle, Drill to Wave).

## viewmodel.glb
**Camera:** authored for a camera at the viewmodel origin looking down −Z, vertical FOV 60, 16:9.
**Recommended setup:** add `gltf.scene` to the viewmodel camera at offset (0, 0, 0), with no rotation and
scale 1. Render it in its own pass after the world (clear depth first) with near 0.01 and FOV 60, so tools
never clip into rock. Procedural sway or bob goes on a parent group, not on the bones.
Hands sit at the lower right. At the pick_swing impact the pick tip projects to NDC (−0.006, −0.099), right on
the crosshair, with the head above it.

**Clips (80 fps keys):**
| Clip | Seconds | Loop | Notes |
|---|---|---|---|
| `pick_idle` | 3.0 | yes | breathing sway, two-handed ready pose (head upper right) |
| `pick_swing` | 0.75 | one-shot | **impact at 0.3375 s = 45 % (frame 27 of 60)**. Wind-up over the right shoulder 0.07–0.25 s, strike 0.255–0.3375 s, recoil to 0.365 s, settle by 0.75 s |
| `pick_equip` | 0.40 | one-shot | rises from below the screen, ends on the `pick_idle` first frame |
| `hammer_idle` | 3.0 | yes | |
| `hammer_use` | 0.5 | yes | 20 Hz blows, 10 Hz shake, 2 Hz shove into the rock |
| `hammer_equip` | 0.45 | one-shot | |
| `drill_idle` | 3.0 | yes | |
| `drill_use` | 0.5 | yes | fine buzz + torque wobble about the bit axis |
| `drill_equip` | 0.45 | one-shot | |
| `hands_idle` | 3.0 | yes | empty gloved hands low left/right |
| `hands_reach` | 0.6 | one-shot | reach forward 0–0.24 s, open, grab at ~0.30 s (use this moment to trigger the interaction), back by 0.6 s |

**Steel pick:** reuses the pick_* clips (same grip points as the pickaxe). To match `TOOLS.*.swingMs`, play
`pick_swing` with `timeScale = 0.75 / (swingMs / 1000)`: 1.0 for the pickaxe (750 ms), 1.154 for the steel
pick (650 ms). The impact then lands at `0.3375 / timeScale` s, i.e. 0.3375 s and 0.2925 s.

**Tool nodes:** these are mesh children of bone `handR`: `vm_pickaxe`, `vm_steelpick`, `vm_jackhammer`,
`vm_diamonddrill`. All four are visible by default; show one at a time.
- Impact/FX empties under each tool: `vm_pickaxe_tip`, `vm_steelpick_tip`, `vm_jackhammer_tip` (chisel point),
  `vm_diamonddrill_tip` (front of the core bit).
- `vm_diamonddrill_bit` (child of `vm_diamonddrill`) is the core bit. Spin it about its local Z while drilling.
- Two-handed tools have both hands baked onto their grips in every clip, so the left hand never slips.

**Arms:** one skinned mesh `vm_arms`:
- Hi-vis sleeves (`fabric_hivis`) with two reflective bands (`custom_reflective`).
- Impact work gloves: `fabric_glove` back, `leather` palm, fingertips and thumb, black `rubber` knuckle armour,
  velcro wrist strap.
- Rugged digital watch on the left wrist (`plastic_black`, `rubber`, `steel`, and `label_watch_face` with an
  embedded backlit LCD reading 06:42).

**Materials:** fabric_hivis, custom_reflective, fabric_glove, leather, rubber, plastic_black, steel,
label_watch_face, wood_dark, steel_dark, plastic_yellow, paint_yellow, aluminium, brass, hose_red, cable.
UVs are in metres (tubes: U around, V along). Grime is AO baked into COLOR_0.

## miner.glb
1.78 m to the top of the head (hard hat top ≈ 1.83 m), front +Z, origin at the feet.

**Clips (30 fps keys):**
| Clip | Seconds | Loop | Notes |
|---|---|---|---|
| `Idle` | 4.0 | yes | breathing, weight shift, glance around |
| `Walk` | 1.1 | yes | planted feet (IK), natural ground speed **0.94 m/s**, so `timeScale = speed / 0.94` |
| `Run` | 0.7 | yes | flight phase, natural speed **2.63 m/s** |
| `Swing` | 1.1 | yes | two-handed overhead pick strike. **Impact at 0.62 s (56 %).** The pick point hits ~0.80 m in front of the origin at ~1.10 m height. Use with `held_pickaxe` |
| `Drill` | 0.6 | yes | braced stance, jackhammer horizontal at ~1.0 m, chisel tip ~1.0 m in front. Use with `held_jackhammer` |
| `Push` | 1.2 | yes | wheelbarrow walk, natural speed 0.75 m/s. Hands grip handles at x = ±0.262 m, 0.27 m in front, 0.865 m high; place the wheelbarrow so its grips are there |
| `Sit` | 4.0 | yes | at a desk, typing. Pelvis sits 0.40 m behind and 0.395 m below standing, so place the origin ~0.40 m in front of the seat centre (seat ≈ 0.46 m). Hands on the keyboard at 0.79 m height, ~0.03 m in front of the origin, feet flat at the origin |
| `Operate` | 3.0 | yes | hands on two vertical lever grips at x = ±0.135 m, 0.40 m in front, ~1.0 m high, alternating throws |
| `Wave` | 2.0 | **no** (one-shot) | starts and ends in the Idle pose |

**Held props:** `held_pickaxe` (344 tris), `held_jackhammer` (400), `held_shovel` (238).
- **Detach them when you clone the miner.** They are root nodes of the same file, so the whole scene would
  draw all three at the feet. Load them on their own with `characters/miner.glb#held_pickaxe` etc., and remove
  or hide the `held_*` roots in each miner clone.
- They are separate root nodes with the grip point at their origin.
- Attach with `grip_r.add(prop)` and an **identity** local transform (position 0, quaternion identity, scale 1),
  verified in three.js.
- Prop frame (three.js): local +Z = working direction (pick point, chisel, blade face). Local +Y runs along the
  handle towards the head for the pickaxe and the shovel blade; for the jackhammer, local +Y runs along the
  right T-grip towards the tool's centre line.
- The Swing and Drill clips put the left hand on the matching second grip (pickaxe butt, jackhammer left
  T-grip).

**Empties:**
- `grip_r`: child of bone `handR`, at the centre of the right fist.
- `lamp`: child of bone `head`, at the headlamp lens. **Its local −Z (three.js) is the beam direction:** forward
  and 10° down (Blender local +Y). This is the same rule as the machines' `light_N` ("spotlight along the empty's
  −Z"). In Blender that means aiming the empty's local **+Y**: CONTRACTS.md says −Y, which looks like a sign
  slip worth checking with the machine agents.

**Materials (7):**
- **skin:** face and forearms, with stubble, brows and a buzz-cut hairline painted into COLOR_0.
- **fabric_shirt:** a light neutral base. Clone it per avatar before tinting, because SkeletonUtils.clone shares
  materials.
- **fabric_hivis:** the vest.
- **custom_reflective:** vest tape and the headlamp lens.
- **fabric_denim:** trousers.
- **leather:** gloves, boots, belt, pouches, knee pads, cap-lamp battery and cord. The darker parts are darkened
  through COLOR_0.
- **helmet_yellow:** the hard hat. The lamp housing and safety glasses (amber/smoke) are darkened through
  COLOR_0.

Props use wood_dark, steel, steel_dark, rubber, paint_yellow and plastic_black.

**Budget deviation:** 7 materials instead of 6. The 7th is `custom_reflective` (silver tape), because the
library's `fabric_hivis` can't align its tape with the vest geometry. To get back to 6, rename that material
to `fabric_hivis` in `vest()` and `hard_hat()` in miner.py (the tape then reads as orange).

## Verification artefacts
- `previews/vm_*.png`: Blender EEVEE from the exact FP camera (pick_swing frames 0–46, equip, steel pick,
  hammer_use, drill, hands).
- `previews/miner_*.png`: rest front/side/back, face, one frame per clip.
- `previews/three/*.png`: three.js harness: FP frames at the impact time, props on `grip_r`.
- `previews/check/*.png`: check.mjs per-clip screenshots (moved out of `public/`).

## Known polish items
- Jackhammer view: the chisel is mostly hidden behind the body in `hammer_*`. The tip (and FX empty) is on the
  crosshair, but a lower or more canted hold would show the chisel.
- Glove grip: the thumb solver lands the thumb tip 25–38 mm from its ideal spot. It reads fine at FP distance,
  but a hand-tuned thumb would be crisper.
- Miner face is simple (behind glasses and under the brim). Natural walk speed is slowish (0.94 m/s);
  timeScale up, or extend the stride, if the game walks faster.
