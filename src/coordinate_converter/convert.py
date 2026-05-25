from pathlib import Path

from coordinate_converter.ply import convert_ply_file as stream_convert_ply_file
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import (
    local_to_world,
    multiply_4x4,
    signed_permutation_to_4x4,
    transform_local_point,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


VIEWER_WORLD_BASIS_CHANGE: SignedPermutation3 = (
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
)

VIEWER_LOCAL_BASIS_CHANGE: SignedPermutation3 = (
    (-1, 0, 0),
    (0, -1, 0),
    (0, 0, 1),
)

VIEWER_ROTATION_BASIS_CHANGE: SignedPermutation3 = (
    (-1, 0, 0),
    (0, 0, -1),
    (0, 1, 0),
)


def convert_pose(
    matrix: SignedPermutation3,
    pose: Matrix4x4,
) -> Matrix4x4:
    basis_change: Matrix4x4 = signed_permutation_to_4x4(matrix)
    return multiply_4x4(pose, basis_change)


def convert_ply_file(
    local_matrix: SignedPermutation3,
    rotation_matrix: SignedPermutation3,
    pose: Matrix4x4,
    source_path: Path,
    destination_path: Path,
) -> None:
    adjusted_pose: Matrix4x4 = convert_pose(rotation_matrix, pose)

    def transform_position(point: Vec3) -> Vec3:
        local_point: Vec3 = transform_local_point(local_matrix, point)
        return local_to_world(adjusted_pose, local_point)

    stream_convert_ply_file(source_path, destination_path, transform_position)


def convert_trajectory_file(
    matrix: SignedPermutation3,
    source_path: Path,
    destination_path: Path,
) -> None:
    poses: tuple[Matrix4x4, ...] = read_trajectory(source_path)
    converted: tuple[Matrix4x4, ...] = tuple(
        convert_pose(matrix, pose) for pose in poses
    )
    write_trajectory(destination_path, converted)


def convert_dataset(
    matrix: SignedPermutation3,
    input_dir: Path,
    output_dir: Path,
) -> None:
    poses: tuple[Matrix4x4, ...] = read_trajectory(input_dir / "traj.txt")
    points_output: Path = output_dir / "Points"
    points_output.mkdir(parents=True, exist_ok=True)
    points_input: Path = input_dir / "Points"
    for image_name, pose in zip(("image1", "image2", "image3"), poses, strict=True):
        convert_ply_file(
            VIEWER_LOCAL_BASIS_CHANGE,
            VIEWER_ROTATION_BASIS_CHANGE,
            pose,
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        VIEWER_ROTATION_BASIS_CHANGE,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
