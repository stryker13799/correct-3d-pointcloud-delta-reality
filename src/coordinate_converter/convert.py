from pathlib import Path

from coordinate_converter.ply import convert_ply_file as stream_convert_ply_file
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import (
    inverse_signed_permutation,
    multiply_4x4,
    signed_permutation_to_4x4,
    transform_local_point,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


# Source frame is right-handed COLMAP-style (X right, Y down, Z forward); the
# viewer is Unity's left-handed Y-up (X right, Y up, Z forward). The basis
# change is a single Y flip: det = -1 (flips handedness), Y-down -> Y-up, and
# the depth axis (Z) is preserved so cameras stay in front of their clouds.
VIEWER_BASIS_CHANGE: SignedPermutation3 = (
    (1, 0, 0),
    (0, -1, 0),
    (0, 0, 1),
)


def convert_pose(
    basis_change: SignedPermutation3,
    pose: Matrix4x4,
) -> Matrix4x4:
    # Similarity transform: T_viewer = S * T_source * S^-1.
    # This keeps det(R) = +1 in the new frame so Unity's Matrix4x4.rotation
    # extracts a valid quaternion.
    forward: Matrix4x4 = signed_permutation_to_4x4(basis_change)
    inverse: Matrix4x4 = signed_permutation_to_4x4(
        inverse_signed_permutation(basis_change)
    )
    return multiply_4x4(multiply_4x4(forward, pose), inverse)


def convert_ply_file(
    basis_change: SignedPermutation3,
    source_path: Path,
    destination_path: Path,
) -> None:
    def transform_position(point: Vec3) -> Vec3:
        return transform_local_point(basis_change, point)

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
            basis_change,
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        basis_change,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
