import ast
import re
import typing as t
from posixpath import relpath

from lk_utils import fs

pattern_1 = re.compile(r'=.*\b(dict|list|tuple|set)\[')
pattern_2 = re.compile(r'(?::|->).*\b(dict|list|tuple|set)\[')


def check_py38(proj_root: str):
    for fp, fn in fs.findall_files(proj_root, '.py'):
        with open(fp) as f:
            code = f.read()
            future_enabled = 'from __future__ import annotations' in code
            for node, msg in check_subscript(ast.parse(code), future_enabled):
                report(node, msg, filepath=relpath(fp, proj_root), filename=fn)


def scan(dir_: str) -> None:
    dir_ = fs.normpath(dir_)
    
    collect = {}
    ''' {
            <path>: {
                'filename': str,
                'errors': {<int lineno>: str},
                'warnings': {<int lineno>: str line, ...},
            }, ...
        } '''
    
    for fp, fn in fs.findall_files(dir_, suffix='.py'):
        print(':i', fn)
        
        node = {
            'filename': fn,
            'warnings': {},
            'errors'  : {},
        }
        no_warining = False
        
        with open(fp, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f.readlines()):
                line = line.strip()
                
                if not line:
                    continue
                
                if line == 'from __future__ import annotations':
                    no_warining = True
                    continue
                
                if pattern_1.search(line):
                    # line = line.replace('[', '\\[')
                    line = pattern_1.sub(
                        lambda m: m.group(0)[:-1].replace(
                            m.group(1),
                            '[red u]{}[/]'.format(m.group(1))
                        ) + '\\[',
                        line
                    )
                    node['errors'][i] = line
                elif no_warining is False and pattern_2.search(line):
                    line = pattern_2.sub(
                        lambda m: m.group(0)[:-1].replace(
                            m.group(1),
                            '[yellow u]{}[/]'.format(m.group(1))
                        ) + '\\[',
                        line
                    )
                    node['warnings'][i] = line
        
        if node['warnings'] or node['errors']:
            # accept node to collect
            collect[fp] = node
    
    # -------------------------------------------------------------------------
    print(':di0')
    
    if not collect:
        print(':r', '[green]no error found[/]')
        return
    
    for fp, node in collect.items():
        print(':i', '.' * 12 + ' ' + node['filename'])
        print(fp)
        
        if node['errors']:
            print(f'errors ({len(node["errors"])}):')
            for lineno, msg in node['errors'].items():
                print(f'[bright_black]|[/]   '
                      f'[cyan]\\[{lineno:>3}][/]: {msg}', ':r')
        
        if node['warnings']:
            print(f'warnings ({len(node["warnings"])}):')
            for lineno, msg in node['warnings'].items():
                print(f'[bright_black]|[/]   '
                      f'[cyan]\\[{lineno:>3}][/]: {msg}', ':r')


# noinspection PyTypeChecker
def check_subscript(
        tree: ast.AST,
        future_annotations=False
) -> t.Iterator[tuple]:
    # noinspection PyUnresolvedReferences,PyShadowingBuiltins,PyTypeChecker
    def _check(node: ast.Subscript) -> None:
        if isinstance((node1 := node.value), ast.Name):
            if (id := node1.id) in (
                    'dict', 'list', 'set', 'tuple',
            ):
                if node.lineno in weak_warning_linenos:
                    yield node, f'`{id}` is not subscriptable! ' \
                                f'[i](no future annotations)[/]'
                else:
                    yield node, f'`{id}` is not subscriptable!'
        elif isinstance((node2 := node.slice), ast.Subscript):
            yield from _check(node2)
    
    skip_linenos = set()
    weak_warning_linenos = set()
    
    for node in ast.walk(tree):  # note: ast.walk is breadth-first.
        # if hasattr(node, 'lineno'):
        #     print(':i', node.lineno, node)
        
        if getattr(node, 'lineno', None) in skip_linenos:
            if isinstance(node, ast.NamedExpr):
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Subscript):
                        yield from _check(subnode)
            continue
        
        if isinstance(node, ast.Subscript):
            yield from _check(node)
            continue
        
        if isinstance(node, (ast.AnnAssign, ast.FunctionDef)):
            if future_annotations:
                skip_linenos.add(node.lineno)
            else:
                weak_warning_linenos.add(node.lineno)
            continue


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
