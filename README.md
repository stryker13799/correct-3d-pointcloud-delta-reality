# Coordinate Converter

Converts the Delta Reality assignment point clouds and camera trajectory from the producer coordinate system into the system expected by the Unity viewer.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency installation

## Setup

```bash
uv sync
```

## Input layout

The viewer package provides data under `StreamingAssets`:

- `Points/image1.ply`, `image2.ply`, `image3.ply` — local camera-space ASCII point clouds
- `traj.txt` — three row-major 4×4 camera poses (16 values per line)

Extract the assignment `Windows.zip` (or Linux package) locally. The viewer binaries are not committed to this repository.

## Approach

The assignment states that the data producer and viewer use different coordinate systems, without specifying the exact mapping. The solution searches **signed permutation** basis changes `S` (axis swap and sign flip only):

- Local points: `p_viewer = S * p_source`
- Camera pose: `T_viewer = S * T_source * S⁻¹`

Cross-view nearest-neighbor alignment is **invariant** under this joint transform, so candidate ranking uses a camera-frame heuristic instead: most local points should lie in front of the camera (positive depth after `S`), matching monocular depth reconstruction.

The selected mapping is the standard OpenCV-style camera frame to a Y-up frame:

| Source (CV) | Viewer |
|-------------|--------|
| +X right    | +X right |
| +Y down     | −Y up |
| +Z forward  | +Z forward |

Implemented as `VIEWER_BASIS_CHANGE` in `src/coordinate_converter/convert.py`:

```
[+x; -y; +z]
```

## Commands

### Rank candidates (alignment — informational only)

```bash
uv run coordinate-converter search \
  --input-dir "Windows/ComputerVisionAssignment_Data/StreamingAssets" \
  --sample-count 800 \
  --seed 42 \
  --top 10
```

### Rank candidates (depth heuristic — used to pick `S`)

```bash
uv run coordinate-converter search-heuristic \
  --ply "Windows/ComputerVisionAssignment_Data/StreamingAssets/Points/image1.ply" \
  --sample-count 5000 \
  --seed 42 \
  --depth-threshold 0.1 \
  --top 10
```

### Convert to a separate output directory

```bash
uv run coordinate-converter convert \
  --input-dir "Windows/ComputerVisionAssignment_Data/StreamingAssets" \
  --output-dir output
```

Produces `output/Points/image{1,2,3}.ply` and `output/traj.txt`. Large ASCII PLY files are gitignored under `output/`.

### Apply converted files into the viewer (backs up originals once)

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

Controls (from assignment): hold right mouse to look; `W/A/S/D` move; `Q/E` up/down.

Compare the result to the reference image in the assignment package (`correct_view_sample.png`).

## Assumptions

- Trajectory matrices are camera-to-world transforms applied as `p_world = R * p_local + t` using the first three rows of each 4×4 matrix.
- The basis change is a signed permutation (no scaling or shear).
- PLY format is ASCII with `x y z red green blue` per vertex; colors are unchanged.

## Resources

- [OpenCV camera coordinate system](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) — X right, Y down, Z forward
- [Unity coordinate system](https://docs.unity3d.com/Manual/Coordinates.html) — left-handed, Y up
- Similarity transform for change of basis on poses: `T' = S T S⁻¹`

## Repository notes

- Assignment `.docx` and HR email `.txt` are kept locally but **not** tracked in git.
- `Windows/` viewer binaries and generated `output/` are gitignored; regenerate with the commands above.

## Submission checklist

1. Push this repository and grant access to `vedran@deltareality.com` and `jstajdoh@deltareality.com`.
2. Include converted `image*.ply` and `traj.txt` (via `output/` archive or release asset if too large for git).
3. Document any visual validation notes in your reply.
