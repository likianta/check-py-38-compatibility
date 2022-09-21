import ast
import typing as t
from posixpath import isfile
from posixpath import relpath

from lk_utils import fs


class T:
    CheckedInfo = t.Iterator[t.Tuple[ast.AST, str]]


def check_py38(path: str) -> None:
    if isfile(path):
        _check_file(path)
    else:
        _check_dir(path)
    print('done')


def _check_dir(dir_: str) -> None:
    for fp, fn in fs.findall_files(dir_, '.py'):
        print(':di0', fn)
        with open(fp) as f:
            code = f.read()
            future_enabled = 'from __future__ import annotations' in code
            for node, msg in check_typing_annotations(ast.parse(code), future_enabled):
                report(node, msg, filepath=relpath(fp, dir_), filename=fn)


def _check_file(file: str) -> None:
    with open(file) as f:
        code = f.read()
        future_enabled = 'from __future__ import annotations' in code
        for node, msg in check_typing_annotations(ast.parse(code), future_enabled):
            report(node, msg, filepath=file, filename=fs.get_filename(file))


# -----------------------------------------------------------------------------

# noinspection PyTypeChecker
def check_typing_annotations(
        tree: ast.AST,
        future_annotations=False
) -> t.Iterator[tuple]:
    # noinspection PyUnresolvedReferences,PyShadowingBuiltins,PyTypeChecker
    def _check_subscriptable(node: ast.Subscript) -> T.CheckedInfo:
        if isinstance((node1 := node.value), ast.Name):
            if (id := node1.id) in ('dict', 'list', 'set', 'tuple'):
                if node.lineno in weak_warning_linenos:
                    yield node, (
                        f'[red dim][b]`{id}`[/] is not '
                        f'subscriptable! [i](missing future '
                        f'annotations)[/][/]'
                    )
                else:
                    yield node, (
                        f'[red][b]`{id}`[/] is not subscriptable![/]'
                    )
        elif isinstance((node2 := node.slice), ast.Subscript):
            yield from _check_subscriptable(node2)
    
    # noinspection PyUnresolvedReferences
    def _check_union_operator(node: ast.BinOp) -> T.CheckedInfo:
        def _get_plain_literal(node) -> str:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Constant):
                return str(node.value)
            else:
                raise ValueError(node)
        if isinstance(node.op, ast.BitOr):
            left = _get_plain_literal(node.left)
            right = _get_plain_literal(node.right)
            if left in ('dict', 'list', 'set', 'tuple') or \
                    right in ('dict', 'list', 'set', 'tuple'):
                if node.lineno in weak_warning_linenos:
                    yield node, (
                        '[red dim]union operator: `{} | {}` '
                        '[i](missing future annotations)[/][/]'.format(
                            left, right
                        )
                    )
                else:
                    yield node, (
                        'union operator: `{} | {}`'.format(left, right)
                    )
    
    # -------------------------------------------------------------------------
    
    skipped_linenos = set()
    weak_warning_linenos = set()
    
    for node in ast.walk(tree):  # note: ast.walk is breadth-first.
        # if hasattr(node, 'lineno'):
        #     print(':i', node.lineno, node)
        
        if getattr(node, 'lineno', None) in skipped_linenos:
            if isinstance(node, ast.NamedExpr):
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Subscript):
                        yield from _check_subscriptable(subnode)
            continue
        
        if isinstance(node, ast.Subscript):
            yield from _check_subscriptable(node)
            continue
        
        if isinstance(node, ast.BinOp):
            yield from _check_union_operator(node)
            continue
        
        if isinstance(node, (ast.AnnAssign, ast.FunctionDef)):
            if future_annotations:
                for lineno in range(node.lineno, node.end_lineno + 1):
                    skipped_linenos.add(lineno)
            else:
                for lineno in range(node.lineno, node.end_lineno + 1):
                    weak_warning_linenos.add(lineno)
            continue


# -----------------------------------------------------------------------------

def report(node: ast.AST, msg: str = '', **kwargs):
    print(':ir', '''
        [cyan]path:[/] [magenta]{filepath}[/]
        [cyan]name:[/] [yellow]{filename}[/]
        [cyan]line:[/] [b green]{row}[/][dim]:[/][dim green]{col}[/]
        [cyan]info:[/] [red]{msg}[/]
    '''.format(
        filepath=kwargs['filepath'],
        filename=kwargs['filename'],
        row=node.lineno,
        col=node.col_offset,
        msg=msg,
    ))
