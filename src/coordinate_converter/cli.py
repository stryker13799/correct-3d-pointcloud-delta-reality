import argparse
import shutil
import sys
from pathlib import Path

from coordinate_converter.convert import VIEWER_BASIS_CHANGE, convert_dataset
from coordinate_converter.search import rank_candidates, rank_heuristic_candidates


def _build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Convert assignment data into the viewer coordinate system.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser(
        "search",
        help="Rank signed-permutation basis changes by multi-view alignment score.",
    )
    search_parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing Points/ and traj.txt",
    )
    search_parser.add_argument(
        "--sample-count",
        type=int,
        required=True,
        help="Number of vertices sampled per point cloud for scoring",
    )
    search_parser.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Random seed used for deterministic sampling",
    )
    search_parser.add_argument(
        "--top",
        type=int,
        required=True,
        help="Number of highest-ranked candidates to print",
    )

    heuristic_parser = subparsers.add_parser(
        "search-heuristic",
        help="Rank basis changes by camera-frame depth (in-front fraction).",
    )
    heuristic_parser.add_argument(
        "--ply",
        type=Path,
        required=True,
        help="PLY file used for local-space depth checks",
    )
    heuristic_parser.add_argument(
        "--sample-count",
        type=int,
        required=True,
        help="Number of vertices sampled from the PLY file",
    )
    heuristic_parser.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Random seed used for deterministic sampling",
    )
    heuristic_parser.add_argument(
        "--depth-threshold",
        type=float,
        required=True,
        help="Minimum positive Z depth treated as in front of the camera",
    )
    heuristic_parser.add_argument(
        "--top",
        type=int,
        required=True,
        help="Number of highest-ranked candidates to print",
    )

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert input data using the selected viewer basis change.",
    )
    convert_parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing Points/ and traj.txt",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where converted Points/ and traj.txt are written",
    )

    apply_parser = subparsers.add_parser(
        "apply",
        help="Copy converted outputs into the viewer StreamingAssets folder.",
    )
    apply_parser.add_argument(
        "--converted-dir",
        type=Path,
        required=True,
        help="Directory containing converted Points/ and traj.txt",
    )
    apply_parser.add_argument(
        "--viewer-streaming-assets",
        type=Path,
        required=True,
        help="Viewer StreamingAssets directory to update",
    )
    apply_parser.add_argument(
        "--backup-dir",
        type=Path,
        required=True,
        help="Directory where original viewer files are backed up",
    )

    return parser


def _run_search_heuristic(args: argparse.Namespace) -> int:
    scores = rank_heuristic_candidates(
        args.ply,
        args.sample_count,
        args.seed,
        args.depth_threshold,
    )
    top_count: int = min(args.top, len(scores))
    for rank, score in enumerate(scores[:top_count], start=1):
        print(
            f"{rank:02d} in_front={score.in_front_fraction:.4f} "
            f"median_z={score.median_depth:.6f} det={score.determinant} "
            f"label={score.label}"
        )
    return 0


def _run_search(args: argparse.Namespace) -> int:
    scores = rank_candidates(args.input_dir, args.sample_count, args.seed)
    top_count: int = min(args.top, len(scores))
    for rank, score in enumerate(scores[:top_count], start=1):
        print(
            f"{rank:02d} median_distance={score.median_distance:.6f} label={score.label}"
        )
    return 0


def _run_convert(args: argparse.Namespace) -> int:
    convert_dataset(VIEWER_BASIS_CHANGE, args.input_dir, args.output_dir)
    print(f"Wrote converted data to {args.output_dir}")
    return 0


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _run_apply(args: argparse.Namespace) -> int:
    converted_points: Path = args.converted_dir / "Points"
    viewer_points: Path = args.viewer_streaming_assets / "Points"
    backup_points: Path = args.backup_dir / "Points"
    for image_name in ("image1", "image2", "image3"):
        source_ply: Path = converted_points / f"{image_name}.ply"
        viewer_ply: Path = viewer_points / f"{image_name}.ply"
        backup_ply: Path = backup_points / f"{image_name}.ply"
        if not source_ply.is_file():
            raise FileNotFoundError(f"Converted PLY not found: {source_ply}")
        if viewer_ply.is_file() and not backup_ply.is_file():
            _copy_file(viewer_ply, backup_ply)
        _copy_file(source_ply, viewer_ply)
    converted_traj: Path = args.converted_dir / "traj.txt"
    viewer_traj: Path = args.viewer_streaming_assets / "traj.txt"
    backup_traj: Path = args.backup_dir / "traj.txt"
    if not converted_traj.is_file():
        raise FileNotFoundError(f"Converted trajectory not found: {converted_traj}")
    if viewer_traj.is_file() and not backup_traj.is_file():
        _copy_file(viewer_traj, backup_traj)
    _copy_file(converted_traj, viewer_traj)
    print(f"Applied converted data to {args.viewer_streaming_assets}")
    return 0


def main() -> None:
    parser: argparse.ArgumentParser = _build_parser()
    args: argparse.Namespace = parser.parse_args()
    if args.command == "search":
        exit_code: int = _run_search(args)
    elif args.command == "search-heuristic":
        exit_code = _run_search_heuristic(args)
    elif args.command == "convert":
        exit_code = _run_convert(args)
    elif args.command == "apply":
        exit_code = _run_apply(args)
    else:
        raise ValueError(f"Unknown command: {args.command}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
