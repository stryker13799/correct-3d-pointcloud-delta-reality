from pathlib import Path
from typing import NamedTuple

from coordinate_converter.ply import sample_ply_positions
from coordinate_converter.trajectory import read_trajectory
from coordinate_converter.transform import (
    apply_signed_permutation_to_vec3,
    generate_signed_permutation_matrices,
    local_to_world,
    matrix_label,
    transform_local_point,
    transform_pose,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


class CandidateScore(NamedTuple):
    matrix: SignedPermutation3
    label: str
    median_distance: float


class HeuristicScore(NamedTuple):
    matrix: SignedPermutation3
    label: str
    determinant: int
    in_front_fraction: float
    median_depth: float


def _world_points_for_view(
    matrix: SignedPermutation3,
    pose: Matrix4x4,
    local_points: tuple[Vec3, ...],
) -> tuple[Vec3, ...]:
    transformed_pose: Matrix4x4 = transform_pose(matrix, pose)
    return tuple(
        local_to_world(
            transformed_pose,
            transform_local_point(matrix, local_point),
        )
        for local_point in local_points
    )


def _median_nearest_neighbor_distance(
    source_points: tuple[Vec3, ...],
    target_points: tuple[Vec3, ...],
) -> float:
    distances: list[float] = []
    for source in source_points:
        best_distance_squared: float = float("inf")
        for target in target_points:
            dx: float = source[0] - target[0]
            dy: float = source[1] - target[1]
            dz: float = source[2] - target[2]
            distance_squared: float = dx * dx + dy * dy + dz * dz
            if distance_squared < best_distance_squared:
                best_distance_squared = distance_squared
        distances.append(best_distance_squared**0.5)
    distances.sort()
    middle: int = len(distances) // 2
    return distances[middle]


def _signed_permutation_determinant(matrix: SignedPermutation3) -> int:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def score_candidate(
    matrix: SignedPermutation3,
    ply_paths: tuple[Path, Path, Path],
    poses: tuple[Matrix4x4, ...],
    sample_count: int,
    seed: int,
) -> float:
    world_clouds: list[tuple[Vec3, ...]] = []
    for ply_index, ply_path in enumerate(ply_paths):
        sampled_local: tuple[Vec3, ...] = sample_ply_positions(
            ply_path,
            sample_count,
            seed + ply_index,
        )
        world_clouds.append(
            _world_points_for_view(matrix, poses[ply_index], sampled_local)
        )

    pair_scores: list[float] = []
    for source_index in range(len(world_clouds)):
        for target_index in range(len(world_clouds)):
            if source_index == target_index:
                continue
            pair_scores.append(
                _median_nearest_neighbor_distance(
                    world_clouds[source_index],
                    world_clouds[target_index],
                )
            )
    pair_scores.sort()
    return sum(pair_scores) / len(pair_scores)


def rank_candidates(
    input_dir: Path,
    sample_count: int,
    seed: int,
) -> tuple[CandidateScore, ...]:
    points_dir: Path = input_dir / "Points"
    ply_paths: tuple[Path, Path, Path] = (
        points_dir / "image1.ply",
        points_dir / "image2.ply",
        points_dir / "image3.ply",
    )
    poses: tuple[Matrix4x4, ...] = read_trajectory(input_dir / "traj.txt")
    if len(poses) != 3:
        raise ValueError(f"Expected 3 trajectory matrices, found {len(poses)}")
    scores: list[CandidateScore] = []
    for matrix in generate_signed_permutation_matrices():
        median_distance: float = score_candidate(
            matrix,
            ply_paths,
            poses,
            sample_count,
            seed,
        )
        scores.append(
            CandidateScore(
                matrix=matrix,
                label=matrix_label(matrix),
                median_distance=median_distance,
            )
        )
    scores.sort(key=lambda item: item.median_distance)
    return tuple(scores)


def rank_heuristic_candidates(
    ply_path: Path,
    sample_count: int,
    seed: int,
    depth_threshold: float,
) -> tuple[HeuristicScore, ...]:
    local_points: tuple[Vec3, ...] = sample_ply_positions(ply_path, sample_count, seed)
    scores: list[HeuristicScore] = []
    for matrix in generate_signed_permutation_matrices():
        transformed_points: list[Vec3] = [
            apply_signed_permutation_to_vec3(matrix, point) for point in local_points
        ]
        depths: list[float] = [point[2] for point in transformed_points]
        depths.sort()
        median_depth: float = depths[len(depths) // 2]
        in_front_count: int = sum(
            1 for depth in depths if depth > depth_threshold
        )
        in_front_fraction: float = in_front_count / len(depths)
        scores.append(
            HeuristicScore(
                matrix=matrix,
                label=matrix_label(matrix),
                determinant=_signed_permutation_determinant(matrix),
                in_front_fraction=in_front_fraction,
                median_depth=median_depth,
            )
        )
    scores.sort(
        key=lambda item: (item.in_front_fraction, -abs(item.median_depth - 1.8)),
        reverse=True,
    )
    return tuple(scores)
