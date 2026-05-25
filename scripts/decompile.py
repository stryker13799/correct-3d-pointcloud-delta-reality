"""Disassemble IL of PhotoPosesPlacer methods with token resolution."""
from __future__ import annotations
import sys
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase


class DnfileReader(CilMethodBodyReaderBase):
    def __init__(self, pe: dnfile.dnPE, rva: int) -> None:
        self.pe = pe
        self.offset = pe.get_offset_from_rva(rva)

    def read(self, n: int) -> bytes:
        data = self.pe.__data__[self.offset:self.offset + n]
        self.offset += n
        return bytes(data)

    def tell(self) -> int:
        return self.offset

    def seek(self, p: int) -> int:
        self.offset = p
        return self.offset


def resolve_token(pe: dnfile.dnPE, tok: int) -> str:
    table = (tok >> 24) & 0xFF
    rid = tok & 0x00FFFFFF
    tables = pe.net.mdtables
    try:
        if table == 0x0A:  # MemberRef
            row = tables.MemberRef.rows[rid - 1]
            cls = row.Class.row if hasattr(row.Class, "row") else None
            cls_name = ""
            if cls is not None:
                cls_name = f"{getattr(cls.TypeNamespace, 'value', '')}.{getattr(cls.TypeName, 'value', '')}::"
            return cls_name + row.Name.value
        if table == 0x06:  # MethodDef
            row = tables.MethodDef.rows[rid - 1]
            return f"<self>::{row.Name.value}"
        if table == 0x04:  # Field
            row = tables.Field.rows[rid - 1]
            return f"FIELD {row.Name.value}"
        if table == 0x0a:
            pass
        if table == 0x70:  # UserString heap
            us = pe.net.user_strings.get_us(rid)
            if us is not None:
                return f'"{us.value}"'
            return f"us:{rid:x}"
        if table == 0x01:  # TypeRef
            row = tables.TypeRef.rows[rid - 1]
            return f"{row.TypeNamespace.value}.{row.TypeName.value}"
        if table == 0x02:  # TypeDef
            row = tables.TypeDef.rows[rid - 1]
            return f"{row.TypeNamespace.value}.{row.TypeName.value}"
        if table == 0x1B:  # TypeSpec
            return f"typespec:{rid}"
        if table == 0x2B:  # MethodSpec
            row = tables.MethodSpec.rows[rid - 1]
            return f"methodspec:{rid}"
    except Exception as e:
        return f"<err:{e}>"
    return f"tok:{table:02x}:{rid}"


def main(path: str, target_method: str) -> None:
    pe = dnfile.dnPE(path)
    pe.parse_data_directories()
    md = pe.net.mdtables
    for m in md.MethodDef.rows:
        if m.Name.value != target_method:
            continue
        if m.Rva == 0:
            continue
        reader = DnfileReader(pe, m.Rva)
        body = CilMethodBody(reader)
        print(f"=== {target_method} ===")
        for ins in body.instructions:
            op = str(ins.opcode)
            arg = ""
            if ins.operand is not None:
                val = ins.operand
                if hasattr(val, "value"):
                    val = val.value
                try:
                    ival = int(val)
                except Exception:
                    ival = None
                if ival is not None and ival > 0xFFFF:
                    arg = f"0x{ival:08x} -> {resolve_token(pe, ival)}"
                else:
                    arg = repr(val)
            print(f"  IL_{ins.offset:04x}: {op} {arg}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
