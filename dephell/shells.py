# built-in
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import List, Tuple

# external
import attr
import pexpect
from shellingham import ShellDetectionFailure, detect_shell

# app
from .utils import cached_property, is_windows


@attr.s()
class Shells:
    bin_path = attr.ib()
    shells = dict()

    @cached_property
    def _shell_info(self) -> Tuple[str, Path]:
        # detect by shellingham
        try:
            name, path = detect_shell()
        except (ShellDetectionFailure, RuntimeError):
            pass
        else:
            return name, Path(path)

        # detect by env
        for env in ('SHELL', 'COMSPEC'):
            path = os.environ.get(env)
            if path:
                path = Path(path).resolve()
                return path.stem, path

        # try to find any known shell
        for name in sorted(self.shells):
            path = shutil.which(name)
            if path is not None:
                return name, Path(path)

        raise OSError('cannot detect shell')

    @property
    def shell_name(self) -> str:
        return self._shell_info[0]

    @property
    def shell_path(self) -> Path:
        return self._shell_info[-1]

    @property
    def current(self) -> 'BaseShell':
        shell_class = self.shells.get(self.shell_name)
        return shell_class(
            bin_path=self.bin_path,
            shell_path=self.shell_path,
        )

    def run(self) -> int:
        return self.current.run()


@attr.s()
class BaseShell:
    bin_path = attr.ib()
    shell_path = attr.ib()

    name = NotImplemented
    activate = NotImplemented
    interactive = NotImplemented

    @property
    def executable(self) -> str:
        if self.shell_path is not None:
            return str(self.shell_path)
        return self.name

    @property
    def entrypoint(self) -> str:
        return str(self.bin_path / self.activate)

    @property
    def dimensions(self):
        columns, lines = shutil.get_terminal_size()
        return lines, columns

    @property
    def command(self):
        return 'source "{}"'.format(str(self.entrypoint))

    @property
    def args(self):
        return ['-i']

    # https://github.com/ofek/hatch/blob/master/hatch/shells.py
    def run(self) -> int:
        if not self.interactive:
            result = subprocess.run(self.command, shell=is_windows())
            return result.returncode

        terminal = pexpect.spawn(
            self.executable,
            args=self.args,
            dimensions=self.dimensions,
        )

        def sigwinch_passthrough(sig, data):
            terminal.setwinsize(*self.dimensions)

        signal.signal(signal.SIGWINCH, sigwinch_passthrough)
        terminal.sendline(self.command)
        terminal.interact(escape_character=None)
        terminal.close()
        return terminal.exitstatus


def _register_shell(cls: BaseShell) -> BaseShell:
    if cls.name in Shells.shells:
        raise NameError('already registered: ' + cls.name)
    Shells.shells[cls.name] = cls
    return cls


@_register_shell
class CmdShell(BaseShell):
    name = 'cmd'
    activate = 'activate.bat'
    interactive = False

    @property
    def command(self):
        return [self.executable, '/k', self.entrypoint]


@_register_shell
class PowerShell(BaseShell):
    name = 'powershell'
    activate = 'activate.ps1'
    interactive = False

    @property
    def command(self):
        return [self.executable, '-executionpolicy', 'bypass', '-NoExit', '-NoLogo', '-File', self.activate]


@_register_shell
class BashShell(BaseShell):
    name = 'bash'
    activate = 'activate'
    interactive = True


@_register_shell
class FishShell(BaseShell):
    name = 'fish'
    activate = 'activate.fish'
    interactive = True


@_register_shell
class ZshShell(BaseShell):
    name = 'zsh'
    activate = 'activate'
    interactive = True


@_register_shell
class XonShell(BaseShell):
    name = 'xonsh'
    activate = 'activate'
    interactive = not is_windows()

    @property
    def command(self):
        path = str(self.bin_path.parent)
        if self.interactive:
            return '$PATH.insert(0, "{}")'.format(path)
        return [self.executable, '-i', '-D', 'VIRTUAL_ENV="{}"'.format(path)]

    @property
    def args(self) -> List[str]:
        return ['-i', '-D', 'VIRTUAL_ENV=' + str(self.bin_path.parent)]


@_register_shell
class TcShell(BaseShell):
    name = 'tcsh'
    activate = 'activate.csh'
    interactive = True


@_register_shell
class CShell(BaseShell):
    name = 'csh'
    activate = 'activate.csh'
    interactive = True
