from pathlib import Path

from coordinate_converter.ply import convert_ply_file as stream_convert_ply_file
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import (
    inverse_signed_permutation,
    multiply_4x4,
    signed_permutation_to_4x4,
    transpose_rotation,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


# World-frame basis change: right-handed COLMAP-style (Y down) -> Unity (Y up).
# PLY vertices are left unchanged; 3DGS.dll already calls PositionFromOpenCVtoUnity
# (negate Y) when loading each splat file.
#
# Trajectory rows are stored in column-major order (R^T flat) while Unity assigns
# the 16 floats to Matrix4x4.m00..m33 in row order. Transpose the 3x3 block
# before applying the world similarity so the effective transform matches the data.
VIEWER_BASIS_CHANGE: SignedPermutation3 = (
    (1, 0, 0),
    (0, -1, 0),
    (0, 0, 1),
)


def convert_pose(
    basis_change: SignedPermutation3,
    pose: Matrix4x4,
) -> Matrix4x4:
    # Column-major traj + row-major Unity fields -> transpose R before world fix.
    row_major_pose: Matrix4x4 = transpose_rotation(pose)
    # Similarity: T_viewer = S * T * S^-1 (keeps det(R) = +1 for Unity quaternions).
    forward: Matrix4x4 = signed_permutation_to_4x4(basis_change)
    inverse: Matrix4x4 = signed_permutation_to_4x4(
        inverse_signed_permutation(basis_change)
    )
    return multiply_4x4(multiply_4x4(forward, row_major_pose), inverse)


def convert_ply_file(
    source_path: Path,
    destination_path: Path,
) -> None:
    # The viewer's PlySplatParsingJob calls PositionFromOpenCVtoUnity (negate Y)
    # when loading vertices. Do not apply a basis change here or Y is flipped twice.
    def transform_position(point: Vec3) -> Vec3:
        return point

    stream_convert_ply_file(source_path, destination_path, transform_position)


def convert_trajectory_file(
    basis_change: SignedPermutation3,
    source_path: Path,
    destination_path: Path,
) -> None:
    poses: tuple[Matrix4x4, ...] = read_trajectory(source_path)
    converted: tuple[Matrix4x4, ...] = tuple(
        convert_pose(basis_change, pose) for pose in poses
    )
    write_trajectory(destination_path, converted)


def convert_dataset(
    basis_change: SignedPermutation3,
    input_dir: Path,
    output_dir: Path,
) -> None:
    points_output: Path = output_dir / "Points"
    points_output.mkdir(parents=True, exist_ok=True)
    points_input: Path = input_dir / "Points"
    for image_name in ("image1", "image2", "image3"):
        convert_ply_file(
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        basis_change,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
