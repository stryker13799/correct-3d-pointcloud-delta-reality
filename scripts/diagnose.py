"""Diagnose whether the source trajectory matches the source point clouds.

Loads a random subset of vertices from each image{N}.ply, transforms them with
the corresponding pose from traj.txt (raw, no basis change), and prints
bounding boxes / centroids for each resulting world-space cloud. If the three
clouds share roughly the same world region, the data is internally consistent
and only a basis change is needed.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path


def parse_pose(line: str) -> tuple[float, ...]:
    return tuple(float(v) for v in line.split())


def transform(pose: tuple[float, ...], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        pose[0] * x + pose[1] * y + pose[2] * z + pose[3],
        pose[4] * x + pose[5] * y + pose[6] * z + pose[7],
        pose[8] * x + pose[9] * y + pose[10] * z + pose[11],
    )


def sample_ply(path: Path, n: int, seed: int) -> list[tuple[float, float, float]]:
    rng = random.Random(seed)
    with path.open() as f:
        header_lines: list[str] = []
        vcount = 0
        for line in f:
            header_lines.append(line)
            if line.startswith("element vertex"):
                vcount = int(line.split()[-1])
            if line.strip() == "end_header":
                break
        idx_set = set(rng.sample(range(vcount), min(n, vcount)))
        out: list[tuple[float, float, float]] = []
        for i in range(vcount):
            line = f.readline()
            if i in idx_set:
                parts = line.split()
                out.append((float(parts[0]), float(parts[1]), float(parts[2])))
    return out


def summarize(name: str, pts: list[tuple[float, float, float]]) -> None:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    n = len(pts)
    print(
        f"{name}: n={n}  "
        f"x[{min(xs):+.2f},{max(xs):+.2f}] (mean {sum(xs)/n:+.2f})  "
        f"y[{min(ys):+.2f},{max(ys):+.2f}] (mean {sum(ys)/n:+.2f})  "
        f"z[{min(zs):+.2f},{max(zs):+.2f}] (mean {sum(zs)/n:+.2f})"
    )


def main(streaming: Path) -> None:
    poses = [parse_pose(line) for line in (streaming / "traj.txt").read_text().splitlines() if line.strip()]
    all_world: list[tuple[float, float, float]] = []
    for i in (1, 2, 3):
        local = sample_ply(streaming / "Points" / f"image{i}.ply", 3000, 42 + i)
        world = [transform(poses[i - 1], p) for p in local]
        summarize(f"image{i} local ", local)
        summarize(f"image{i} world ", world)
        all_world.extend(world)
        print()
    summarize("combined world", all_world)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
