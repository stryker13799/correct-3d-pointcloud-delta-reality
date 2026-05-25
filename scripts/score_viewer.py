"""Score how well three views overlap under a viewer-like pose+point pipeline."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coordinate_converter.convert import convert_pose
from coordinate_converter.trajectory import read_trajectory
from coordinate_converter.transform import (
    apply_signed_permutation_to_vec3,
    local_to_world,
    multiply_4x4,
    signed_permutation_to_4x4,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3

VIEWER_POINT_FIX: SignedPermutation3 = ((1, 0, 0), (0, -1, 0), (0, 0, 1))


def invert_rigid(pose: Matrix4x4) -> Matrix4x4:
    r00, r01, r02, tx = pose[0], pose[1], pose[2], pose[3]
    r10, r11, r12, ty = pose[4], pose[5], pose[6], pose[7]
    r20, r21, r22, tz = pose[8], pose[9], pose[10], pose[11]
    itx = -(r00 * tx + r10 * ty + r20 * tz)
    ity = -(r01 * tx + r11 * ty + r21 * tz)
    itz = -(r02 * tx + r12 * ty + r22 * tz)
    return (
        r00, r10, r20, itx,
        r01, r11, r21, ity,
        r02, r12, r22, itz,
        0.0, 0.0, 0.0, 1.0,
    )


def transpose_rotation(pose: Matrix4x4) -> Matrix4x4:
    return (
        pose[0], pose[4], pose[8], pose[3],
        pose[1], pose[5], pose[9], pose[7],
        pose[2], pose[6], pose[10], pose[11],
        pose[12], pose[13], pose[14], pose[15],
    )


def sample_ply(path: Path, n: int, seed: int) -> tuple[Vec3, ...]:
    rng = random.Random(seed)
    with path.open() as f:
        vcount = 0
        for line in f:
            if line.startswith("element vertex"):
                vcount = int(line.split()[-1])
            if line.strip() == "end_header":
                break
        idx = set(rng.sample(range(vcount), min(n, vcount)))
        pts: list[Vec3] = []
        for i in range(vcount):
            parts = f.readline().split()
            if i in idx:
                pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
    return tuple(pts)


def median_nn(a: tuple[Vec3, ...], b: tuple[Vec3, ...]) -> float:
    dists: list[float] = []
    for p in a:
        best = min(
            (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 for q in b
        )
        dists.append(best**0.5)
    dists.sort()
    return dists[len(dists) // 2]


def score(
    data_dir: Path,
    pose_fn,
    ply_in_file_is_already_viewer_fixed: bool,
) -> float:
    poses = read_trajectory(data_dir / "traj.txt")
    worlds: list[tuple[Vec3, ...]] = []
    for i in (1, 2, 3):
        local = sample_ply(data_dir / "Points" / f"image{i}.ply", 800, 42 + i)
        pose = pose_fn(poses[i - 1])
        if ply_in_file_is_already_viewer_fixed:
            fixed = local
        else:
            fixed = tuple(
                apply_signed_permutation_to_vec3(VIEWER_POINT_FIX, p) for p in local
            )
        worlds.append(tuple(local_to_world(pose, p) for p in fixed))
    pairs: list[float] = []
    for a in range(3):
        for b in range(3):
            if a != b:
                pairs.append(median_nn(worlds[a], worlds[b]))
    pairs.sort()
    return sum(pairs) / len(pairs)


def main(data_dir: Path) -> None:
    s = VIEWER_POINT_FIX
    results: list[tuple[float, str]] = []
    results.append(
        (
            score(
                data_dir,
                lambda p: convert_pose(s, p),
                False,
            ),
            "similarity_traj + viewer_y_on_load",
        )
    )
    results.append(
        (
            score(
                data_dir,
                lambda p: convert_pose(s, invert_rigid(p)),
                False,
            ),
            "similarity(invert(traj)) + viewer_y",
        )
    )
    results.append(
        (
            score(
                data_dir,
                lambda p: convert_pose(s, transpose_rotation(p)),
                False,
            ),
            "similarity(transpose(traj)) + viewer_y",
        )
    )
    results.append(
        (
            score(
                data_dir,
                lambda p: multiply_4x4(signed_permutation_to_4x4(s), p),
                False,
            ),
            "left_S_traj + viewer_y",
        )
    )
    results.append(
        (
            score(data_dir, lambda p: p, False),
            "raw_traj + viewer_y",
        )
    )
    results.append(
        (
            score(
                data_dir,
                lambda p: convert_pose(s, p),
                True,
            ),
            "similarity_traj + ply_already_fixed(no_viewer_y)",
        )
    )
    results.sort(key=lambda item: item[0])
    for dist, label in results:
        print(f"{dist:.6f}  {label}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
