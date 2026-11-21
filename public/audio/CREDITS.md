# MOTHERLODE audio credits

Almost every sound in the game is synthesised at runtime by `src/core/audio.ts` (no files). The recordings
below are layered on top of, or swapped in for, a few synthesised sounds where a real recording is clearly
better (footsteps, the pick strike, a door, chair creaks). If any file is missing or can't be decoded, the
synthesised version plays instead.

All files are **CC0 1.0 Universal (public domain dedication)**, http://creativecommons.org/publicdomain/zero/1.0/
Credit is not required; we credit Kenney anyway. Processing for every file: converted to mono 48 kHz,
leading/trailing silence trimmed, peak-normalised to -1 dBFS, 8 ms fade-out, encoded Ogg Vorbis q4.

| File(s) | Source file(s) | Pack | Author | Licence | Used for |
|---|---|---|---|---|---|
| `step_gravel_0..9.ogg` | `Audio/footstep00..09.ogg` | RPG Audio (https://kenney.nl/assets/rpg-audio) | Kenney (www.kenney.nl) | CC0 | `step_gravel` (replaces synth) |
| `step_wood_0..4.ogg` | `Audio/footstep_wood_000..004.ogg` | Impact Sounds 1.0 (https://kenney.nl/assets/impact-sounds) | Kenney | CC0 | `step_wood` (replaces synth) |
| `step_rock_0..4.ogg` | `Audio/footstep_concrete_000..004.ogg` | Impact Sounds 1.0 | Kenney | CC0 | `step_rock` (replaces synth); heel layer under `step_metal` |
| `pick_strike_0..4.ogg` | `Audio/impactMining_000..004.ogg` | Impact Sounds 1.0 | Kenney | CC0 | layer under `pick_hit_rock` / `pick_hit_ore` |
| `door_1.ogg` | `Audio/doorOpen_1.ogg` + 180 ms + `Audio/doorClose_1.ogg` (joined) | RPG Audio | Kenney | CC0 | `door` (replaces synth) |
| `door_2.ogg` | `Audio/doorOpen_2.ogg` + 180 ms + `Audio/doorClose_3.ogg` (joined) | RPG Audio | Kenney | CC0 | `door` (replaces synth) |
| `creak_1..3.ogg` | `Audio/creak1..3.ogg` | RPG Audio | Kenney | CC0 | layer under `sit` / `stand` |

Total size: about 0.3 MB.

Downloaded 2026-10-12 from the kenney.nl asset pages (zip downloads `kenney_impact-sounds.zip`,
`kenney_rpg-audio.zip`); each pack's License.txt states "Creative Commons Zero, CC0".
