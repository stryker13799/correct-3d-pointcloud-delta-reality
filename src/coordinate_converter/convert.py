from collections.abc import Iterator
from pathlib import Path

from coordinate_converter.ply import (
    convert_ply_file as stream_convert_ply_file,
    parse_ply_header,
    parse_vertex_line,
)
from coordinate_converter.trajectory import read_trajectory, write_trajectory
from coordinate_converter.transform import (
    apply_signed_permutation_to_vec3,
    inverse_signed_permutation,
    local_to_world,
    multiply_4x4,
    signed_permutation_to_4x4,
)
from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


# The viewer's 3DGS loader converts each local PLY point with PositionFromOpenCVtoUnity
# (x, y, z) -> (x, -y, z). PLY vertices stay untouched, and the trajectory is
# post-multiplied by the inverse of this local-space loader transform.
VIEWER_LOCAL_POINT_CHANGE: SignedPermutation3 = (
    (1, 0, 0),
    (0, -1, 0),
    (0, 0, 1),
)

# Source world Y is already vertical. The viewer world is reached by preserving Y
# and swapping source Z into Unity X / source X into Unity Z.
SOURCE_TO_VIEWER_WORLD_CHANGE: SignedPermutation3 = (
    (0, 0, 1),
    (0, 1, 0),
    (1, 0, 0),
)

VIEWER_FLOOR_PADDING: float = 0.05


def convert_pose(
    world_basis_change: SignedPermutation3,
    local_point_change: SignedPermutation3,
    world_offset: Vec3,
    pose: Matrix4x4,
) -> Matrix4x4:
    # The viewer evaluates: viewer_pose * (local_point_change * p).
    # We want: offset + world_basis_change * (source_pose * p).
    world_change: Matrix4x4 = signed_permutation_to_4x4(world_basis_change)
    inverse_local_change: Matrix4x4 = signed_permutation_to_4x4(
        inverse_signed_permutation(local_point_change)
    )
    converted: Matrix4x4 = multiply_4x4(
        multiply_4x4(world_change, pose),
        inverse_local_change,
    )
    return (
        converted[0],
        converted[1],
        converted[2],
        converted[3] + world_offset[0],
        converted[4],
        converted[5],
        converted[6],
        converted[7] + world_offset[1],
        converted[8],
        converted[9],
        converted[10],
        converted[11] + world_offset[2],
        converted[12],
        converted[13],
        converted[14],
        converted[15],
    )


def _iter_ply_positions(path: Path) -> Iterator[Vec3]:
    if not path.is_file():
        raise FileNotFoundError(f"PLY file not found: {path}")
    with path.open("r", encoding="utf-8") as source_file:
        header_lines: list[str] = []
        for line in source_file:
            header_lines.append(line.rstrip("\n"))
            if line.strip() == "end_header":
                break
        header = parse_ply_header(header_lines)
        for _ in range(header.vertex_count):
            yield parse_vertex_line(next(source_file).rstrip("\n")).position


def calculate_viewer_offset(
    world_basis_change: SignedPermutation3,
    points_input: Path,
    poses: tuple[Matrix4x4, ...],
) -> Vec3:
    min_x: float = float("inf")
    min_y: float = float("inf")
    min_z: float = float("inf")
    max_x: float = float("-inf")
    max_z: float = float("-inf")

    for index, image_name in enumerate(("image1", "image2", "image3")):
        pose: Matrix4x4 = poses[index]
        for point in _iter_ply_positions(points_input / f"{image_name}.ply"):
            source_world: Vec3 = local_to_world(pose, point)
            viewer_world: Vec3 = apply_signed_permutation_to_vec3(
                world_basis_change,
                source_world,
            )
            min_x = min(min_x, viewer_world[0])
            min_y = min(min_y, viewer_world[1])
            min_z = min(min_z, viewer_world[2])
            max_x = max(max_x, viewer_world[0])
            max_z = max(max_z, viewer_world[2])

    if min_x == float("inf"):
        raise ValueError("Cannot calculate viewer offset for empty point clouds")

    center_x: float = (min_x + max_x) / 2.0
    center_z: float = (min_z + max_z) / 2.0
    return (-center_x, -min_y + VIEWER_FLOOR_PADDING, -center_z)


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
    world_basis_change: SignedPermutation3,
    local_point_change: SignedPermutation3,
    world_offset: Vec3,
    source_path: Path,
    destination_path: Path,
) -> None:
    poses: tuple[Matrix4x4, ...] = read_trajectory(source_path)
    converted: tuple[Matrix4x4, ...] = tuple(
        convert_pose(world_basis_change, local_point_change, world_offset, pose)
        for pose in poses
    )
    write_trajectory(destination_path, converted)


def convert_dataset(
    world_basis_change: SignedPermutation3,
    local_point_change: SignedPermutation3,
    input_dir: Path,
    output_dir: Path,
) -> None:
    points_output: Path = output_dir / "Points"
    points_output.mkdir(parents=True, exist_ok=True)
    points_input: Path = input_dir / "Points"
    poses: tuple[Matrix4x4, ...] = read_trajectory(input_dir / "traj.txt")
    world_offset: Vec3 = calculate_viewer_offset(
        world_basis_change,
        points_input,
        poses,
    )
    for image_name in ("image1", "image2", "image3"):
        convert_ply_file(
            points_input / f"{image_name}.ply",
            points_output / f"{image_name}.ply",
        )
    convert_trajectory_file(
        world_basis_change,
        local_point_change,
        world_offset,
        input_dir / "traj.txt",
        output_dir / "traj.txt",
    )
