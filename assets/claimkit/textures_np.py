"""Bark / deadwood / log-end textures with numpy (Blender's Python has numpy; the system Python doesn't).

    bl assets/claimkit/textures_np.py        -> assets/claimkit/tex/{bark,bark_n,deadwood,deadwood_n,log_end}.png
    node assets/claimkit/textures.mjs        -> re-encodes those to .jpg (smaller GLBs) + makes the SVG textures

All tile seamlessly (periodic noise + periodic Voronoi). Bark/deadwood cover 1 m (u, around the trunk) x 2 m
(v, up the trunk) at 512 x 1024 px. Normal maps are OpenGL/glTF convention (+Y = up the texture).
"""
import os
import struct
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tex")
os.makedirs(OUT, exist_ok=True)


def write_png(path, arr):
    """arr: H x W x 3|4 float 0..1 (row 0 = top of the image)."""
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    h, w, c = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, {3: 2, 4: 6}[c], 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    print("tex", os.path.basename(path), f"{len(png) / 1024:.0f} KB")


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def tile_noise(h, w, cy, cx, rng):
    g = rng.random((cy, cx))
    y = np.arange(h) / h * cy
    x = np.arange(w) / w * cx
    yi, xi = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = y - yi, x - xi
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y0, y1, x0, x1 = yi % cy, (yi + 1) % cy, xi % cx, (xi + 1) % cx
    a, b = g[np.ix_(y0, x0)], g[np.ix_(y0, x1)]
    c, d = g[np.ix_(y1, x0)], g[np.ix_(y1, x1)]
    fx, fy = fx[None, :], fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, cy, cx, rng, octaves=5, gain=0.5):
    t, amp, norm = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        t += amp * tile_noise(h, w, cy * 2 ** o, cx * 2 ** o, rng)
        norm += amp
        amp *= gain
    return t / norm


def voronoi(h, w, ny, nx, rng, jitter=0.85, aspect=1.0, wu=None, wv=None):
    """Periodic jittered-grid Voronoi: F1, F2 (distances in texture-WIDTH units; v distances scaled by
    `aspect` = height/width in world units) and the cell id. 3x3 neighbour search = 9 vector passes."""
    J = 0.5 + (rng.random((ny, nx, 2)) - 0.5) * jitter
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    u, v = (u + 0.5) / w, (v + 0.5) / h
    if wu is not None:
        u, v = u + wu, v + wv
    cx, cy = np.floor(u * nx).astype(int), np.floor(v * ny).astype(int)
    F1 = np.full((h, w), 9.0)
    F2 = np.full((h, w), 9.0)
    ID = np.zeros((h, w), int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ix, iy = cx + dx, cy + dy
            jx, jy = J[iy % ny, ix % nx, 0], J[iy % ny, ix % nx, 1]
            du = u - (ix + jx) / nx
            dv = (v - (iy + jy) / ny) * aspect
            d = np.sqrt(du * du + dv * dv)
            idx = (iy % ny) * nx + (ix % nx)
            m = d < F1
            F2 = np.where(m, F1, np.minimum(F2, d))
            ID = np.where(m, idx, ID)
            F1 = np.where(m, d, F1)
    return F1, F2, ID


def normal_map(height, strength):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength  # rows go DOWN = -v
    n = np.stack([-gx, gy, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def bark():
    """Ponderosa pine: cinnamon/orange puzzle-piece plates of thin scales split by deep black fissures."""
    rng = np.random.default_rng(31)
    H, W = 1024, 512
    wu = (fbm(H, W, 8, 4, rng) - 0.5) * 0.06
    wv = (fbm(H, W, 8, 4, rng) - 0.5) * 0.05
    F1, F2, ID = voronoi(H, W, 4, 4, rng, 0.9, aspect=2.0, wu=wu, wv=wv)
    e = F2 - F1
    plate = smooth(0.006, 0.032, e)  # 0 in the fissure, 1 on the plate face
    fw_u = (fbm(H, W, 24, 12, rng, 3) - 0.5) * 0.035
    fw_v = (fbm(H, W, 24, 12, rng, 3) - 0.5) * 0.02
    f1, f2, fid = voronoi(H, W, 44, 15, rng, 0.95, aspect=2.0, wu=wu * 0.6 + fw_u, wv=wv * 0.6 + fw_v)
    edge_var = fbm(H, W, 16, 8, rng, 3)
    flake_edge = smooth(0.001, 0.004 + 0.006 * edge_var, f2 - f1)
    pal = np.array([[0.63, 0.37, 0.23], [0.72, 0.44, 0.27], [0.55, 0.32, 0.21], [0.60, 0.45, 0.33],
                    [0.68, 0.50, 0.37], [0.50, 0.34, 0.25]])
    cell_tone = rng.random(4 * 4)
    flake_tone = rng.random(44 * 15)
    base = pal[(ID * 7 + 3) % len(pal)] * (0.86 + 0.26 * cell_tone[ID])[..., None]
    fresh = pal[(fid * 5) % len(pal)]
    grey = np.array([0.52, 0.47, 0.43])
    weather = smooth(0.55, 0.9, flake_tone[fid])[..., None]
    alb = base * 0.55 + fresh * 0.45
    alb = alb * (1 - weather * 0.6) + grey * weather * 0.6
    alb *= (0.74 + 0.26 * flake_edge)[..., None]
    alb = alb * 0.85 + alb.mean(-1, keepdims=True) * 0.15
    n = fbm(H, W, 32, 16, rng, 4)
    alb *= (0.85 + 0.3 * n)[..., None]
    edge_dark = smooth(0.0, 0.07, e)
    alb *= (0.68 + 0.32 * edge_dark)[..., None]
    fis = np.array([0.11, 0.08, 0.062]) * (0.8 + 0.4 * n)[..., None]
    alb = alb * plate[..., None] + fis * (1 - plate[..., None])
    write_png(os.path.join(OUT, "bark.png"), alb)
    height = 0.15 + 0.85 * smooth(0.0, 0.07, e) - 0.12 * (1 - flake_edge) * plate + 0.06 * n
    write_png(os.path.join(OUT, "bark_n.png"), normal_map(height, 7.0))


def deadwood():
    """Silver-grey weathered snag wood: long vertical grain, shallow checks, a few deep cracks."""
    rng = np.random.default_rng(17)
    H, W = 1024, 512
    streak = fbm(H, W, 3, 40, rng, 5, 0.55)
    fine = fbm(H, W, 6, 120, rng, 3)
    warp = fbm(H, W, 4, 6, rng)
    crack = np.zeros((H, W))
    for k in range(5):
        c = fbm(H, W, 2, 3, rng, 3)
        x = np.abs(((np.arange(W)[None, :] / W + (c - 0.5) * 0.25 + rng.random()) % 1.0) - 0.5)
        crack = np.maximum(crack, 1 - smooth(0.0, 0.006 + 0.004 * rng.random(), x))
    g = 0.5 + 0.35 * (streak - 0.5) * 2 + 0.12 * (fine - 0.5)
    tint = np.stack([g * 1.03, g * 1.0, g * 0.95], -1)
    brown = np.array([0.42, 0.33, 0.25])
    stain = smooth(0.6, 0.8, warp)[..., None]
    alb = tint * (1 - stain * 0.5) + brown * stain * 0.5
    alb *= (1 - 0.8 * crack)[..., None]
    write_png(os.path.join(OUT, "deadwood.png"), alb * 0.95)
    height = 0.6 * streak + 0.25 * fine - 0.7 * crack
    write_png(os.path.join(OUT, "deadwood_n.png"), normal_map(height, 5.0))


def log_end():
    """Cut log end: growth rings, a heart check, darker heartwood, a thin bark rim (UV 0-1 over the disc)."""
    rng = np.random.default_rng(5)
    S = 256
    y, x = (np.mgrid[0:S, 0:S] + 0.5) / S - 0.5
    cx, cy = 0.03, -0.02
    ang = np.arctan2(y - cy, x - cx)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / 0.5
    wob = fbm(S, S, 6, 6, rng, 3)
    rr = r * (1 + 0.05 * (wob - 0.5))
    rings = 0.5 + 0.5 * np.cos(rr * 2 * np.pi * 22 + 0.6 * np.sin(ang * 3))
    late = smooth(0.75, 0.95, rings)
    wood = np.array([0.80, 0.64, 0.45])
    heart = np.array([0.66, 0.46, 0.30])
    col = wood * (1 - smooth(0.3, 0.6, 1 - r))[..., None] + heart * smooth(0.3, 0.6, 1 - r)[..., None]
    col = col * (1 - 0.22 * late)[..., None]
    check = np.exp(-(((ang - 0.9 + 0.08 * (wob - 0.5)) * r * 20) ** 2)) * smooth(0.05, 0.2, r) * (1 - smooth(0.55, 0.85, r))
    col *= (1 - 0.75 * check)[..., None]
    barkc = np.array([0.24, 0.16, 0.11]) * (0.8 + 0.4 * wob)[..., None]
    rim = smooth(0.9, 0.94, rr)[..., None]
    col = col * (1 - rim) + barkc * rim
    grey = np.array([0.55, 0.52, 0.48])
    col = col * 0.8 + grey * 0.2  # weathered a little
    write_png(os.path.join(OUT, "log_end.png"), col * (0.92 + 0.12 * fbm(S, S, 16, 16, rng, 3))[..., None])


bark()
deadwood()
log_end()
