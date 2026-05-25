from pathlib import Path

from coordinate_converter.ply import convert_ply_file as stream_convert_ply_file
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import transform_local_point
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


VIEWER_BASIS_CHANGE: SignedPermutation3 = (
    (1, 0, 0),
    (0, 0, 1),
    (0, -1, 0),
)


def convert_pose(
    matrix: SignedPermutation3,
    pose: Matrix4x4,
) -> Matrix4x4:
    return pose


def convert_ply_file(
    matrix: SignedPermutation3,
    source_path: Path,
    destination_path: Path,
) -> None:
    def transform_position(point: Vec3) -> Vec3:
        return transform_local_point(matrix, point)

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
            VIEWER_BASIS_CHANGE,
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        matrix,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
