"""Print MethodDef bodies (raw IL bytes) for PhotoPosesPlacer methods."""
from __future__ import annotations

import sys
from pathlib import Path

import dnfile
from dnfile.enums import MetadataTables


def main(path: str) -> None:
    pe = dnfile.dnPE(path)
    pe.parse_data_directories()
    tables = pe.net.mdtables
    type_defs = tables.TypeDef.rows
    method_defs = tables.MethodDef.rows
    target_types = {"PhotoPosesPlacer"}
    for i, t in enumerate(type_defs):
        if t.TypeName.value not in target_types:
            continue
        ml = t.MethodList
        start_idx = ml[0].row_index - 1 if isinstance(ml, list) else ml.row_index - 1
        if i + 1 < len(type_defs):
            nxt = type_defs[i + 1].MethodList
            end_idx = nxt[0].row_index - 1 if isinstance(nxt, list) else nxt.row_index - 1
        else:
            end_idx = len(method_defs)
        start = start_idx
        end = end_idx
        print(f"=== {t.TypeNamespace.value}.{t.TypeName.value} ===")
        for m in method_defs[start:end]:
            print(f"  Method: {m.Name.value}  RVA=0x{m.Rva:x}")
            if m.Rva == 0:
                continue
            offset = pe.get_offset_from_rva(m.Rva)
            data = pe.__data__[offset:offset + 4096]
            header_byte = data[0]
            if (header_byte & 0x3) == 0x2:
                code_size = header_byte >> 2
                il = data[1:1 + code_size]
            else:
                # Fat header (12 bytes)
                code_size = int.from_bytes(data[4:8], "little")
                il = data[12:12 + code_size]
            print(f"    code_size={code_size} il={il.hex()}")


if __name__ == "__main__":
    main(sys.argv[1])
