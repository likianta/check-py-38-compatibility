from argsense import cli

from .main import scan

cli.cmd()(scan)

if __name__ == '__main__':
    cli.run()
