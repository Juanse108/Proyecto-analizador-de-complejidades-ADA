from typing import List, Tuple, Optional


def is_var(node, name: str = None) -> bool:
    return isinstance(node, dict) and node.get("kind") == "var" and (name is None or node.get("name") == name)


def is_num(node, value=None) -> bool:
    return isinstance(node, dict) and node.get("kind") == "num" and (value is None or node.get("value") == value)


def is_binop(node, op: str) -> bool:
    if not (isinstance(node, dict) and node.get("kind") == "binop"):
        return False

    node_op = node.get("op")

    if node_op == "≤":
        node_op = "<="
    elif node_op == "≥":
        node_op = ">="
    elif node_op == "≠":
        node_op = "!="

    if op == "≤":
        op = "<="
    elif op == "≥":
        op = ">="
    elif op == "≠":
        op = "!="

    return node_op == op


def get_line(node: dict) -> int:
    loc = node.get("loc")
    if loc and isinstance(loc, dict):
        return loc.get("line", 0)
    return 0


def extract_main_body(ast: dict) -> List[dict]:
    if not isinstance(ast, dict):
        return []

    kind = ast.get("kind")

    if kind == "program":
        body = ast.get("body", [])

        if len(body) == 1 and isinstance(body[0], dict) and body[0].get("kind") == "proc":
            return body[0].get("body", [])

        if body and isinstance(body[0], dict) and body[0].get("kind") != "proc":
            return body

        return []

    if kind == "proc":
        return ast.get("body", [])

    return ast.get("body", []) if isinstance(ast.get("body"), list) else []


def normalize_op(op: str) -> str:
    if op == "≤":
        return "<="
    if op == "≥":
        return ">="
    if op == "≠":
        return "!="
    return op


def expr_uses_var(node, varname: str) -> bool:
    if isinstance(node, dict):
        if node.get("kind") == "var" and node.get("name") == varname:
            return True
        for v in node.values():
            if expr_uses_var(v, varname):
                return True
        return False
    elif isinstance(node, list):
        return any(expr_uses_var(elem, varname) for elem in node)
    else:
        return False


def stmt_list_has_assign_to_var(body: List[dict], varname: str) -> bool:
    def _visit(stmts: List[dict]) -> bool:
        for st in stmts:
            kind = st.get("kind")
            if kind == "assign":
                tgt = st.get("target")
                if is_var(tgt, varname):
                    return True
            elif kind == "if":
                if _visit(st.get("then_body", [])):
                    return True
                if _visit(st.get("else_body", [])):
                    return True
            elif kind == "block":
                if _visit(st.get("stmts", [])):
                    return True
            elif kind in ("for", "while", "repeat"):
                if _visit(st.get("body", [])):
                    return True
        return False

    return _visit(body)


def collect_vars_in_expr(node, acc: set) -> None:
    if isinstance(node, dict):
        kind = node.get("kind")
        if kind == "var":
            name = node.get("name")
            if name is not None:
                acc.add(name)
        for v in node.values():
            collect_vars_in_expr(v, acc)
    elif isinstance(node, list):
        for elem in node:
            collect_vars_in_expr(elem, acc)


def expr_has_logical_op(node) -> bool:
    if isinstance(node, dict):
        if node.get("kind") == "binop":
            op = node.get("op")
            if op in ("and", "or"):
                return True
            return expr_has_logical_op(node.get("left")) or expr_has_logical_op(node.get("right"))
        return any(expr_has_logical_op(v) for v in node.values())
    elif isinstance(node, list):
        return any(expr_has_logical_op(elem) for elem in node)
    else:
        return False