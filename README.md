# Coordinate Converter

Converts the Delta Reality take-home input data into the coordinate system expected by the Unity viewer.

The solution writes replacement versions of:

- `Points/image1.ply`
- `Points/image2.ply`
- `Points/image3.ply`
- `traj.txt`

The final conversion is intentionally small: the PLY files are copied with positions unchanged, because the viewer's `3DGS.dll` already negates local point `y` when loading each PLY. The trajectory matrices are converted with a world-frame Y flip:

```text
viewer_pose = S * source_pose * S^-1
S = diag(1, -1, 1)
```

Since `S` is its own inverse, this compensates for the viewer's local-space point flip and converts the source Y-down world into Unity's Y-up world.

## Reference and Verification

Assignment reference:

![Reference view - three views merged into one coherent room](docs/correct_view_sample.png)

Offline projection of the converted point clouds:

![Converted point-cloud projection](docs/current_result.png)

The projection is not a viewer screenshot; it is a quick deterministic geometry check from the converted pipeline. I also applied the generated files into the Windows viewer and launched it to sanity-check that the room loads as one coherent scene.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency installation

## Setup

### 1. Assignment package

Download and unzip the Windows assignment package:

[Delta Reality assignment - Windows zip](https://storage.divit.hr/share/1p6bzP_p)

After extracting, place the `Windows/` folder at the repository root:

```text
Windows/
  ComputerVisionAssignment.exe
  ComputerVisionAssignment_Data/
    StreamingAssets/
      Points/
        image1.ply
        image1.png
        image1_depth.png
        image1_rays.png
        image2.ply
        image2.png
        image2_depth.png
        image2_rays.png
        image3.ply
        image3.png
        image3_depth.png
        image3_rays.png
      traj.txt
```

The assignment zip, extracted viewer, raw input copies, and generated output are ignored by git.

### 2. Python environment

```bash
uv sync
```

## Commands

Use raw assignment data as input. After the first `apply`, the original viewer files are kept in `backup/`; use that folder for repeat conversions.

### Test

```bash
uv run python -m unittest discover -s tests
```

### Convert

```bash
uv run coordinate-converter convert \
  --input-dir backup \
  --output-dir output
```

This writes:

```text
output/
  Points/
    image1.ply
    image2.ply
    image3.ply
  traj.txt
```

### Apply to the viewer

```bash
uv run coordinate-converter apply \
  --converted-dir output \
  --viewer-streaming-assets "Windows/ComputerVisionAssignment_Data/StreamingAssets" \
  --backup-dir backup
```

### Run the viewer

```bash
Windows/ComputerVisionAssignment.exe
```

Viewer controls:

- Hold right mouse to look around.
- While holding right mouse, use `W/A/S/D` to move.
- Use `Q/E` to move down/up.

## Approach

1. Read the assignment and confirmed the deliverable is only the four replacement files plus source code and workflow documentation.
2. Inspected the Unity viewer IL:
   - `PhotoPosesPlacer.LoadFromTrajFile` reads each `traj.txt` row directly into `Matrix4x4.m00..m33`.
   - It uses `matrix.GetColumn(3)` as the Unity position and `matrix.rotation` as the Unity rotation.
   - `3DGS.dll` `PositionFromOpenCVtoUnity` negates only the local point `y`.
3. Checked the raw data:
   - The three raw PLY files are local camera-space point clouds with positive Z depth.
   - The raw trajectory rows are row-major camera-to-world matrices with translation in column 3.
   - Applying raw poses to raw local points puts the three clouds into the same source-world region.
4. Derived the conversion:
   - Let `S = diag(1, -1, 1)`.
   - The viewer loads each raw PLY point as `S * p`.
   - To display `S * (source_pose * p)`, the viewer pose must be `S * source_pose * S^-1`.
   - No rotation transpose is applied; the viewer already reads the matrix in the same row-major layout used by the file.
5. Added unit tests for the viewer-pipeline invariant and PLY pass-through behavior.

## Assumptions

- `traj.txt` rows are row-major camera-to-world matrices.
- The PLY positions are camera-local coordinates in the source camera frame.
- The viewer's PLY loader always applies the local OpenCV-to-Unity Y flip.
- The source-to-viewer world change is a signed Y-axis flip with no scale, shear, or translation offset.

## Repository Layout

| Path | Role |
|------|------|
| `src/coordinate_converter/` | Converter, CLI, PLY and trajectory parsing |
| `tests/` | Focused conversion invariant tests |
| `scripts/` | Diagnostic helpers used during investigation |
| `docs/*.png` | Assignment reference and final projection sanity check |
| `backup/` | Raw `StreamingAssets` snapshot, gitignored |
| `output/` | Generated replacement files, gitignored |

## Resources

- [Unity rotation and orientation manual](https://docs.unity3d.com/Manual/QuaternionAndEulerRotationsInUnity.html)
- [OpenCV camera coordinates](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- Similarity transform for poses: `T_viewer = S * T_source * S^-1`
