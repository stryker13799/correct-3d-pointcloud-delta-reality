from typing import NamedTuple

Matrix4x4 = tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]

Vec3 = tuple[float, float, float]

SignedPermutation3 = tuple[
    tuple[int, int, int],
    tuple[int, int, int],
    tuple[int, int, int],
]


class PlyHeader(NamedTuple):
    lines_before_vertices: tuple[str, ...]
    vertex_count: int


class PlyVertex(NamedTuple):
    position: Vec3
    color: tuple[int, int, int]
