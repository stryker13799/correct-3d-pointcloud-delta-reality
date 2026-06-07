import tempfile
import unittest
from pathlib import Path

from coordinate_converter.convert import (
    VIEWER_BASIS_CHANGE,
    convert_ply_file,
    convert_pose,
)
from coordinate_converter.transform import apply_signed_permutation_to_vec3, local_to_world
from coordinate_converter.types import Matrix4x4, Vec3


class ConvertTests(unittest.TestCase):
    def test_pose_compensates_for_viewer_local_y_flip(self) -> None:
        source_pose: Matrix4x4 = (
            0.0, -1.0, 0.0, 4.0,
            1.0, 0.0, 0.0, -3.0,
            0.0, 0.0, 1.0, -1.0,
            0.0, 0.0, 0.0, 1.0,
        )
        source_point: Vec3 = (1.25, -0.5, 2.0)

        converted_pose = convert_pose(VIEWER_BASIS_CHANGE, source_pose)
        viewer_loaded_point = apply_signed_permutation_to_vec3(
            VIEWER_BASIS_CHANGE,
            source_point,
        )

        viewer_world = local_to_world(converted_pose, viewer_loaded_point)
        expected_world = apply_signed_permutation_to_vec3(
            VIEWER_BASIS_CHANGE,
            local_to_world(source_pose, source_point),
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


if __name__ == "__main__":
    unittest.main()
