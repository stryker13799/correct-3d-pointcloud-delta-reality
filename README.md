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

The assignment states that the data producer and viewer use different coordinate systems, without specifying the exact mapping. The viewer is a Unity application; decompiling `Assembly-CSharp.dll` (`GaussianSplatting.PhotoPosesPlacer.LoadFromTrajFile`) confirms:

- Each trajectory line is parsed as 16 floats and assigned directly to `Matrix4x4.m00..m33` (row-major).
- The splat loader's `transform.position` is set from `matrix.GetColumn(3)` and `transform.rotation` from `matrix.rotation`.
- Each `image{N}.ply` is rendered as that loader's child, so `world = transform · local`.

So the viewer expects **Unity left-handed, Y-up** world and a proper rotation (det = +1) in each pose.

Inspection of the raw source data (`scripts/diagnose.py`) shows the trajectory and point clouds are already internally consistent in source world:

- Raw camera translations: `(3.97, −3.21, −1.45)`, `(4.52, −3.15, −1.40)`, `(4.71, −3.12, −1.40)` — three cameras spread along **X**, near-constant Y and Z.
- Raw camera forward direction (col2 of R) is ≈ `(−0.10, 0.07, −0.99)` for every pose: cameras face along source **−Z**.
- Sampling each `imageN.ply` and applying its pose places all three world clouds in the same region (~`(4.3, −2.7, −3.7)`), directly in front of the cameras.

So the source is right-handed **COLMAP-style**: +X right, +Y **down**, +Z forward. Unity is left-handed Y-up with +Z still forward. The conversion is a single **Y flip** applied as a similarity:

- Local points: `p_viewer = S · p_source`
- Camera pose: `T_viewer = S · T_source · S⁻¹`

with

```
S = [[1, 0, 0],
     [0,-1, 0],
     [0, 0, 1]]
```

`S` is involutive (`S⁻¹ = S`) and has `det = −1`, which flips handedness (RH → LH) while turning Y-down into Y-up. The similarity preserves `det(R) = +1` on the rotation part, so Unity's `Matrix4x4.rotation` extracts a valid quaternion. Z is left untouched, which preserves the depth axis so the cameras stay in front of their clouds.

Implemented as `VIEWER_BASIS_CHANGE` in `src/coordinate_converter/convert.py`.

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

- Trajectory matrices are camera-to-world transforms stored row-major; the viewer reads them as Unity `Matrix4x4` fields `m00..m33`.
- The basis change is a signed permutation (no scaling or shear).
- PLY format is ASCII with `x y z red green blue` per vertex; colors are unchanged.

## Resources

- [Unity coordinate system](https://docs.unity3d.com/Manual/Coordinates.html) — left-handed, Y up, Z forward
- Similarity transform for change of basis on poses: `T' = S T S⁻¹`
- Viewer logic confirmed by disassembling `Assembly-CSharp.dll` (see `scripts/decompile.py`)

## Repository notes

- Assignment `.docx` and HR email `.txt` are kept locally but **not** tracked in git.
- `Windows/` viewer binaries and generated `output/` are gitignored; regenerate with the commands above.

## Submission checklist

1. Push this repository and grant access to `vedran@deltareality.com` and `jstajdoh@deltareality.com`.
2. Include converted `image*.ply` and `traj.txt` (via `output/` archive or release asset if too large for git).
3. Document any visual validation notes in your reply.
