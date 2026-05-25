import random
from collections.abc import Callable
from pathlib import Path

from coordinate_converter.types import PlyHeader, PlyVertex, Vec3


def parse_ply_header(lines: list[str]) -> PlyHeader:
    if len(lines) == 0 or lines[0].strip() != "ply":
        raise ValueError("PLY file must start with 'ply'")
    vertex_count: int | None = None
    header_end_index: int | None = None
    for index, line in enumerate(lines):
        stripped: str = line.strip()
        if stripped.startswith("element vertex "):
            count_text: str = stripped.removeprefix("element vertex ").strip()
            vertex_count = int(count_text)
        if stripped == "end_header":
            header_end_index = index
            break
    if vertex_count is None:
        raise ValueError("PLY header missing 'element vertex' declaration")
    if header_end_index is None:
        raise ValueError("PLY header missing 'end_header'")
    header_lines: tuple[str, ...] = tuple(lines[: header_end_index + 1])
    return PlyHeader(lines_before_vertices=header_lines, vertex_count=vertex_count)


def parse_vertex_line(line: str) -> PlyVertex:
    parts: list[str] = line.split()
    if len(parts) < 6:
        raise ValueError(f"PLY vertex line must have at least 6 fields, got {len(parts)}")
    position: Vec3 = (float(parts[0]), float(parts[1]), float(parts[2]))
    color: tuple[int, int, int] = (int(parts[3]), int(parts[4]), int(parts[5]))
    return PlyVertex(position=position, color=color)


def format_vertex_line(vertex: PlyVertex) -> str:
    x: float
    y: float
    z: float
    x, y, z = vertex.position
    red: int
    green: int
    blue: int
    red, green, blue = vertex.color
    return f"{x:.9g} {y:.9g} {z:.9g} {red} {green} {blue}"


def sample_ply_positions(
    path: Path,
    sample_count: int,
    seed: int,
) -> tuple[Vec3, ...]:
    if not path.is_file():
        raise FileNotFoundError(f"PLY file not found: {path}")
    header: PlyHeader | None = None
    vertex_count: int = 0
    header_line_count: int = 0
    with path.open("r", encoding="utf-8") as ply_file:
        header_lines: list[str] = []
        for line in ply_file:
            header_lines.append(line.rstrip("\n"))
            stripped: str = line.strip()
            if stripped.startswith("element vertex "):
                vertex_count = int(stripped.removeprefix("element vertex ").strip())
            if stripped == "end_header":
                header = parse_ply_header(header_lines)
                header_line_count = len(header_lines)
                break
    if header is None:
        raise ValueError(f"PLY header missing in {path}")
    if sample_count >= vertex_count:
        _, vertices = read_ply_vertices(path)
        return tuple(vertex.position for vertex in vertices)
    random_generator: random.Random = random.Random(seed)
    selected_indices: set[int] = set(
        random_generator.sample(range(vertex_count), sample_count)
    )
    max_index: int = max(selected_indices)
    samples: dict[int, Vec3] = {}
    with path.open("r", encoding="utf-8") as ply_file:
        for _ in range(header_line_count):
            next(ply_file)
        for vertex_index in range(vertex_count):
            line: str = next(ply_file).rstrip("\n")
            if vertex_index in selected_indices:
                vertex: PlyVertex = parse_vertex_line(line)
                samples[vertex_index] = vertex.position
            if vertex_index >= max_index and len(samples) == sample_count:
                break
    return tuple(samples[index] for index in sorted(samples))


def read_ply_vertices(path: Path) -> tuple[PlyHeader, tuple[PlyVertex, ...]]:
    if not path.is_file():
        raise FileNotFoundError(f"PLY file not found: {path}")
    lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    header: PlyHeader = parse_ply_header(lines)
    header_line_count: int = len(header.lines_before_vertices)
    vertex_lines: list[str] = lines[header_line_count : header_line_count + header.vertex_count]
    if len(vertex_lines) != header.vertex_count:
        raise ValueError(
            f"PLY file {path} expected {header.vertex_count} vertices, found {len(vertex_lines)}"
        )
    vertices: list[PlyVertex] = []
    for line_number, line in enumerate(vertex_lines, start=header_line_count + 1):
        if line.strip() == "":
            raise ValueError(f"Empty vertex line at line {line_number} in {path}")
        try:
            vertices.append(parse_vertex_line(line))
        except ValueError as error:
            raise ValueError(
                f"Invalid vertex at line {line_number} in {path}: {error}"
            ) from error
    return header, tuple(vertices)


def convert_ply_file(
    source_path: Path,
    destination_path: Path,
    transform_position: Callable[[Vec3], Vec3],
) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(f"PLY file not found: {source_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with source_path.open("r", encoding="utf-8") as source_file:
        header_lines: list[str] = []
        for line in source_file:
            header_lines.append(line.rstrip("\n"))
            if line.strip() == "end_header":
                break
        header: PlyHeader = parse_ply_header(header_lines)
        with destination_path.open("w", encoding="utf-8", newline="\n") as destination_file:
            destination_file.write("\n".join(header.lines_before_vertices))
            destination_file.write("\n")
            for _ in range(header.vertex_count):
                vertex_line: str = next(source_file).rstrip("\n")
                vertex: PlyVertex = parse_vertex_line(vertex_line)
                transformed: PlyVertex = PlyVertex(
                    position=transform_position(vertex.position),
                    color=vertex.color,
                )
                destination_file.write(format_vertex_line(transformed))
                destination_file.write("\n")


def write_ply(path: Path, header: PlyHeader, vertices: tuple[PlyVertex, ...]) -> None:
    if len(vertices) != header.vertex_count:
        raise ValueError(
            f"Vertex count mismatch: header declares {header.vertex_count}, got {len(vertices)}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    header_text: str = "\n".join(header.lines_before_vertices)
    body_lines: list[str] = [format_vertex_line(vertex) for vertex in vertices]
    content: str = header_text + "\n" + "\n".join(body_lines) + "\n"
    path.write_text(content, encoding="utf-8", newline="\n")
