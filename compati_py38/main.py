import re

from lk_utils import fs

pattern_1 = re.compile(r'=.*\b(dict|list|tuple|set)\[')
pattern_2 = re.compile(r'(?::|->).*\b(dict|list|tuple|set)\[')


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
