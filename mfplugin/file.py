import os
from mfutil import BashWrapper
from mfplugin.utils import get_rpm_cmd, get_default_plugins_base_dir, \
    BadPluginFile


class PluginFile(object):

    def __init__(self, plugin_filepath):
        self.plugins_base_dir = get_default_plugins_base_dir()
        """Plugins base directory (string)."""
        if not os.path.isfile(plugin_filepath):
            raise BadPluginFile("file: %s not found" % plugin_filepath)
        self.plugin_filepath = plugin_filepath
        """Plugin file path (string)."""
        self.__loaded = False

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        frmt = "%{name}~~~%{version}~~~%{release}\\n"
        cmd = get_rpm_cmd(self.plugins_base_dir, '-qp',
                          '--qf "%s" "%s"' % (frmt, self.plugin_filepath))
        x = BashWrapper(cmd)
        if not x:
            raise BadPluginFile(x)
        if x:
            tmp = x.stdout.split('~~~')
            if len(tmp) < 2:
                raise BadPluginFile("incorrect output for cmd: %s" % cmd)
            self._name = tmp[0]
            self._version = tmp[1]
            self._release = tmp[2]
        cmd = get_rpm_cmd(self.plugins_base_dir, '-qi',
                          "-p " + self.plugin_filepath)
        x = BashWrapper(cmd)
        if not x:
            raise BadPluginFile(x)
        self._raw_metadata_output = x.stdout
        for line in x.stdout.split('\n'):
            tmp = line.strip().split(':', 1)
            if len(tmp) <= 1:
                continue
            name = tmp[0].strip().lower()
            value = tmp[1].strip()
            if name == "build host":
                self._build_host = value
            if name == "build date":
                self._build_date = value
            if name == "size":
                self._size = value
        cmd = get_rpm_cmd(self.plugins_base_dir, '-ql',
                          "-p " + self.plugin_filepath)
        x = BashWrapper(cmd)
        if not x:
            raise Exception(x)
        self._raw_files_output = x.stdout
        self._files = [x.strip() for x in x.stdout.split('\n')]
        found = False
        for f in self._files:
            if "/.plugin_format_version" in f:
                found = True
                break
        if not found:
            raise BadPluginFile("This plugin file is too old => you have to "
                                "rebuild it with a more recent MetWork "
                                "version")

    @property
    def name(self):
        self.load()
        return self._name

    @property
    def version(self):
        self.load()
        return self._version

    @property
    def release(self):
        self.load()
        return self._release

    @property
    def size(self):
        self.load()
        return self._size

    @property
    def build_host(self):
        self.load()
        return self._build_host

    @property
    def build_date(self):
        self.load()
        return self._build_date

    @property
    def raw_metadata_output(self):
        self.load()
        return self._raw_metadata_output

    @property
    def raw_files_output(self):
        self.load()
        return self._raw_files_output

    @property
    def files(self):
        self.load()
        return self._files

    @property
    def home(self):
        return None
