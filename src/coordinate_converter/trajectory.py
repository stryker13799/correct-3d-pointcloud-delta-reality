from pathlib import Path

from coordinate_converter.types import Matrix4x4


def parse_trajectory_line(line: str) -> Matrix4x4:
    stripped: str = line.strip()
    if stripped == "":
        raise ValueError("Trajectory line is empty")
    parts: list[str] = stripped.split()
    if len(parts) != 16:
        raise ValueError(
            f"Trajectory line must contain 16 values, got {len(parts)}: {stripped[:80]}"
        )
    values: list[float] = [float(part) for part in parts]
    return (
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        values[6],
        values[7],
        values[8],
        values[9],
        values[10],
        values[11],
        values[12],
        values[13],
        values[14],
        values[15],
    )


def read_trajectory(path: Path) -> tuple[Matrix4x4, ...]:
    if not path.is_file():
        raise FileNotFoundError(f"Trajectory file not found: {path}")
    lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    matrices: list[Matrix4x4] = []
    for line_number, line in enumerate(lines, start=1):
        if line.strip() == "":
            continue
        try:
            matrices.append(parse_trajectory_line(line))
        except ValueError as error:
            raise ValueError(
                f"Invalid trajectory at line {line_number} in {path}: {error}"
            ) from error
    if len(matrices) == 0:
        raise ValueError(f"No trajectory matrices found in {path}")
    return tuple(matrices)


def format_matrix(matrix: Matrix4x4) -> str:
    return (
        f"{matrix[0]:.16e} {matrix[1]:.16e} {matrix[2]:.16e} {matrix[3]:.16e} "
        f"{matrix[4]:.16e} {matrix[5]:.16e} {matrix[6]:.16e} {matrix[7]:.16e} "
        f"{matrix[8]:.16e} {matrix[9]:.16e} {matrix[10]:.16e} {matrix[11]:.16e} "
        f"{matrix[12]:.16e} {matrix[13]:.16e} {matrix[14]:.16e} {matrix[15]:.16e}"
    )


def write_trajectory(path: Path, matrices: tuple[Matrix4x4, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content: str = "\n".join(format_matrix(matrix) for matrix in matrices)
    path.write_text(content + "\n", encoding="utf-8", newline="\n")
