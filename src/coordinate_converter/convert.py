from pathlib import Path

from coordinate_converter.ply import convert_ply_file as stream_convert_ply_file
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import (
    multiply_4x4,
    signed_permutation_to_4x4,
    transform_local_point,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


VIEWER_LOCAL_BASIS_CHANGE: SignedPermutation3 = (
    (-1, 0, 0),
    (0, -1, 0),
    (0, 0, 1),
)

VIEWER_WORLD_TRANSLATION_OFFSET: Vec3 = (
    -4.60305361,
    4.26299587,
    6.88643729,
)


def convert_pose(
    matrix: SignedPermutation3,
    pose: Matrix4x4,
) -> Matrix4x4:
    basis_change: Matrix4x4 = signed_permutation_to_4x4(matrix)
    converted_pose: Matrix4x4 = multiply_4x4(pose, basis_change)
    return (
        converted_pose[0],
        converted_pose[1],
        converted_pose[2],
        converted_pose[3] + VIEWER_WORLD_TRANSLATION_OFFSET[0],
        converted_pose[4],
        converted_pose[5],
        converted_pose[6],
        converted_pose[7] + VIEWER_WORLD_TRANSLATION_OFFSET[1],
        converted_pose[8],
        converted_pose[9],
        converted_pose[10],
        converted_pose[11] + VIEWER_WORLD_TRANSLATION_OFFSET[2],
        converted_pose[12],
        converted_pose[13],
        converted_pose[14],
        converted_pose[15],
    )


def convert_ply_file(
    local_matrix: SignedPermutation3,
    source_path: Path,
    destination_path: Path,
) -> None:
    def transform_position(point: Vec3) -> Vec3:
        return transform_local_point(local_matrix, point)

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
    points_output: Path = output_dir / "Points"
    points_output.mkdir(parents=True, exist_ok=True)
    points_input: Path = input_dir / "Points"
    for image_name in ("image1", "image2", "image3"):
        convert_ply_file(
            VIEWER_LOCAL_BASIS_CHANGE,
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        VIEWER_LOCAL_BASIS_CHANGE,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
