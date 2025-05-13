import ast
import sys
from pathlib import Path
from typing import Union

# ─────────────────────────────────────────────
#  Helpers for type parsing
# ─────────────────────────────────────────────

# simple Python → TS primitive map
_PRIM_MAP = {
    'str': 'string',
    'int': 'number',
    'float': 'number',
    'bool': 'boolean',
    'dict': 'Record<string, any>',
    'Any': 'any',
}

def parse_annotation(node: ast.AST) -> str:
    """
    Given an AST annotation node, return its base name, e.g. `GreetInput`,
    or fallback to `Any`.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id
    return 'Any'

def py_to_ts(anno: str) -> str:
    """Map a parsed annotation name to its TS equivalent."""
    return _PRIM_MAP.get(anno, anno)

# ─────────────────────────────────────────────
#  Main conversion routine
# ─────────────────────────────────────────────

def _convert(
    src_path: Union[str, Path],
    out_index: Union[str, Path],
    out_dts:   Union[str, Path]
):
    src = Path(src_path).read_text()
    tree = ast.parse(src)

    # 1) Collect Pydantic models (BaseModel subclasses)
    models: dict[str, dict[str,str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {
            getattr(b, 'id', getattr(b, 'attr', None))
            for b in node.bases
        }
        if 'BaseModel' not in base_names:
            continue

        # It's a Pydantic model
        fields: dict[str,str] = {}
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields[stmt.target.id] = parse_annotation(stmt.annotation)
        models[node.name] = fields

    # 2) Collect exposed methods on ANY class
    funcs: list[tuple[str,str,str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        for m in node.body:
            if not isinstance(m, ast.FunctionDef):
                continue

            # Detect any form of `@expose`:
            is_exposed = False
            for dec in m.decorator_list:
                # bare @expose
                if isinstance(dec, ast.Name) and dec.id == 'expose':
                    is_exposed = True
                # @webview.expose or similar
                elif isinstance(dec, ast.Attribute) and dec.attr == 'expose':
                    is_exposed = True
                # @expose(...)  decorator-call
                elif isinstance(dec, ast.Call):
                    fn = dec.func
                    if isinstance(fn, ast.Name) and fn.id == 'expose':
                        is_exposed = True
                    elif isinstance(fn, ast.Attribute) and fn.attr == 'expose':
                        is_exposed = True

            if not is_exposed:
                continue

            # Determine which arg is your payload:
            args = m.args.args  # list of ast.arg
            # If first arg is not 'self', it's a staticmethod: use args[0]
            if args and args[0].arg != 'self':
                payload_arg = args[0]
            # Otherwise assume instance method: use args[1] if present
            elif len(args) >= 2:
                payload_arg = args[1]
            else:
                payload_arg = None

            # Parse input type
            if payload_arg and payload_arg.annotation:
                in_typ = parse_annotation(payload_arg.annotation)
            else:
                in_typ = 'Any'

            # Parse return type
            if m.returns:
                out_typ = parse_annotation(m.returns)
            else:
                out_typ = 'Any'

            funcs.append((m.name, in_typ, out_typ))

    # 3) Generate interface/index.ts
    index_lines: list[str] = []
    # -- TS interfaces for your models
    for model_name, fields in models.items():
        index_lines.append(f"export interface {model_name} {{")
        for fname, ftype in fields.items():
            index_lines.append(f"  {fname}: {py_to_ts(ftype)};")
        index_lines.append("}\n")

    # -- wrapper functions
    for fn_name, in_t, out_t in funcs:
        ts_in  = py_to_ts(in_t)
        ts_out = py_to_ts(out_t)
        index_lines.append(f"export function {fn_name}(data: {ts_in}): Promise<{ts_out}> {{")
        index_lines.append(f"  return window.pywebview.api.{fn_name}(data);")
        index_lines.append("}\n")

    Path(out_index).write_text("\n".join(index_lines))

    # 4) Generate interface/interface.d.ts
    dts_lines: list[str] = []
    if models:
        model_list = ", ".join(models.keys())
        dts_lines.append(f"import {{ {model_list} }} from './index';\n")

    dts_lines.append("declare global {")
    dts_lines.append("  interface Window {")
    dts_lines.append("    pywebview: {")
    dts_lines.append("      api: {")
    for fn_name, in_t, out_t in funcs:
        ts_in  = py_to_ts(in_t)
        ts_out = py_to_ts(out_t)
        dts_lines.append(f"        {fn_name}(data: {ts_in}): Promise<{ts_out}>;")
    dts_lines.append("      }")
    dts_lines.append("    }")
    dts_lines.append("  }")
    dts_lines.append("}\n")

    Path(out_dts).write_text("\n".join(dts_lines))


def convert():
    in_file = Path("app/interface.py")
    out_index = Path("interface/index.ts")
    out_dts = Path("interface/interface.d.ts")
    out_index.parent.mkdir(parents=True, exist_ok=True)
    out_dts.parent.mkdir(parents=True, exist_ok=True)
    _convert(in_file, out_index, out_dts)
    
def convert_live():
    import watchdog.events
    import watchdog.observers
    
    in_file = Path("app/interface.py")
    
    class EventHandler(watchdog.events.FileSystemEventHandler):
        def __init__(self, callback):
            self.callback = callback
            
        def on_modified(self, event):
            if event.src_path == in_file:
                print("Interface file changed, converting...")
                convert()
    
    observer = watchdog.observers.Observer()
    event_handler = EventHandler(convert)
    observer.schedule(event_handler, path=in_file.parent, recursive=False)
    observer.start()

    convert()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python convert.py app/interface.py interface/index.ts interface/interface.d.ts")
        sys.exit(1)
    _convert(sys.argv[1], sys.argv[2], sys.argv[3])
