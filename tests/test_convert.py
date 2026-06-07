import tempfile
import unittest
from pathlib import Path

from coordinate_converter.convert import (
    SOURCE_TO_VIEWER_WORLD_CHANGE,
    VIEWER_LOCAL_POINT_CHANGE,
    calculate_viewer_offset,
    convert_ply_file,
    convert_pose,
)
from coordinate_converter.transform import apply_signed_permutation_to_vec3, local_to_world
from coordinate_converter.types import Matrix4x4, Vec3


class ConvertTests(unittest.TestCase):
    def test_pose_matches_viewer_loader_and_world_basis(self) -> None:
        source_pose: Matrix4x4 = (
            0.0, -1.0, 0.0, 4.0,
            1.0, 0.0, 0.0, -3.0,
            0.0, 0.0, 1.0, -1.0,
            0.0, 0.0, 0.0, 1.0,
        )
        source_point: Vec3 = (1.25, -0.5, 2.0)
        world_offset: Vec3 = (0.5, 2.0, -1.5)

        converted_pose = convert_pose(
            SOURCE_TO_VIEWER_WORLD_CHANGE,
            VIEWER_LOCAL_POINT_CHANGE,
            world_offset,
            source_pose,
        )
        viewer_loaded_point = apply_signed_permutation_to_vec3(
            VIEWER_LOCAL_POINT_CHANGE,
            source_point,
        )

        viewer_world = local_to_world(converted_pose, viewer_loaded_point)
        converted_source_world = apply_signed_permutation_to_vec3(
            SOURCE_TO_VIEWER_WORLD_CHANGE,
            local_to_world(source_pose, source_point),
        )
        expected_world = (
            converted_source_world[0] + world_offset[0],
            converted_source_world[1] + world_offset[1],
            converted_source_world[2] + world_offset[2],
        )

        for actual, expected in zip(viewer_world, expected_world):
            self.assertAlmostEqual(actual, expected)

    def test_ply_positions_are_left_for_viewer_loader(self) -> None:
        source = "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 1",
                "property float x",
                "property float y",
                "property float z",
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "1.0 2.0 3.0 4 5 6",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.ply"
            destination_path = Path(temp_dir) / "out" / "converted.ply"
            source_path.write_text(source, encoding="utf-8", newline="\n")

            convert_ply_file(source_path, destination_path)

            self.assertIn(
                "1 2 3 4 5 6",
                destination_path.read_text(encoding="utf-8"),
            )

    def test_viewer_offset_centers_xz_and_places_floor(self) -> None:
        source = "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 2",
                "property float x",
                "property float y",
                "property float z",
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "1.0 2.0 3.0 4 5 6",
                "3.0 4.0 5.0 7 8 9",
                "",
            ]
        )
        identity_pose: Matrix4x4 = (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            points_dir = Path(temp_dir) / "Points"
            points_dir.mkdir()
            for image_name in ("image1", "image2", "image3"):
                (points_dir / f"{image_name}.ply").write_text(
                    source,
                    encoding="utf-8",
                    newline="\n",
                )

            offset = calculate_viewer_offset(
                SOURCE_TO_VIEWER_WORLD_CHANGE,
                points_dir,
                (identity_pose, identity_pose, identity_pose),
            )

        self.assertEqual(offset, (-4.0, -1.95, -2.0))


if __name__ == "__main__":
    unittest.main()
