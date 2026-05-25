import itertools

from coordinate_converter.types import Matrix4x4, SignedPermutation3, Vec3


def apply_signed_permutation_to_vec3(
    matrix: SignedPermutation3,
    vector: Vec3,
) -> Vec3:
    x: float
    y: float
    z: float
    x, y, z = vector
    source: tuple[float, float, float] = (x, y, z)
    return (
        matrix[0][0] * source[0] + matrix[0][1] * source[1] + matrix[0][2] * source[2],
        matrix[1][0] * source[0] + matrix[1][1] * source[1] + matrix[1][2] * source[2],
        matrix[2][0] * source[0] + matrix[2][1] * source[1] + matrix[2][2] * source[2],
    )


def inverse_signed_permutation(matrix: SignedPermutation3) -> SignedPermutation3:
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )


def multiply_4x4(left: Matrix4x4, right: Matrix4x4) -> Matrix4x4:
    result: list[float] = []
    for row in range(4):
        for column in range(4):
            value: float = 0.0
            for inner in range(4):
                value += left[row * 4 + inner] * right[inner * 4 + column]
            result.append(value)
    return (
        result[0],
        result[1],
        result[2],
        result[3],
        result[4],
        result[5],
        result[6],
        result[7],
        result[8],
        result[9],
        result[10],
        result[11],
        result[12],
        result[13],
        result[14],
        result[15],
    )


def signed_permutation_to_4x4(matrix: SignedPermutation3) -> Matrix4x4:
    return (
        float(matrix[0][0]),
        float(matrix[0][1]),
        float(matrix[0][2]),
        0.0,
        float(matrix[1][0]),
        float(matrix[1][1]),
        float(matrix[1][2]),
        0.0,
        float(matrix[2][0]),
        float(matrix[2][1]),
        float(matrix[2][2]),
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )


def transform_pose(matrix: SignedPermutation3, pose: Matrix4x4) -> Matrix4x4:
    basis_change: Matrix4x4 = signed_permutation_to_4x4(matrix)
    inverse_basis_change: Matrix4x4 = signed_permutation_to_4x4(
        inverse_signed_permutation(matrix)
    )
    return multiply_4x4(multiply_4x4(basis_change, pose), inverse_basis_change)


def transform_local_point(matrix: SignedPermutation3, point: Vec3) -> Vec3:
    return apply_signed_permutation_to_vec3(matrix, point)


def local_to_world(pose: Matrix4x4, local_point: Vec3) -> Vec3:
    x: float
    y: float
    z: float
    x, y, z = local_point
    world_x: float = (
        pose[0] * x + pose[1] * y + pose[2] * z + pose[3]
    )
    world_y: float = (
        pose[4] * x + pose[5] * y + pose[6] * z + pose[7]
    )
    world_z: float = (
        pose[8] * x + pose[9] * y + pose[10] * z + pose[11]
    )
    return (world_x, world_y, world_z)


def generate_signed_permutation_matrices() -> tuple[SignedPermutation3, ...]:
    axes: tuple[int, int, int] = (0, 1, 2)
    matrices: list[SignedPermutation3] = []
    for permutation in itertools.permutations(axes):
        for signs in itertools.product((-1, 1), repeat=3):
            rows: list[list[int]] = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            for row_index, axis_index in enumerate(permutation):
                rows[row_index][axis_index] = signs[row_index]
            matrices.append(
                (
                    (rows[0][0], rows[0][1], rows[0][2]),
                    (rows[1][0], rows[1][1], rows[1][2]),
                    (rows[2][0], rows[2][1], rows[2][2]),
                )
            )
    return tuple(matrices)


def matrix_label(matrix: SignedPermutation3) -> str:
    axis_names: tuple[str, str, str] = ("x", "y", "z")
    rows: list[str] = []
    for row in matrix:
        parts: list[str] = []
        for axis_index, value in enumerate(row):
            if value == 0:
                continue
            sign: str = "+" if value > 0 else "-"
            parts.append(f"{sign}{axis_names[axis_index]}")
        rows.append("".join(parts) if parts else "0")
    return f"[{'; '.join(rows)}]"
