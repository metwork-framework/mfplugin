import os
from mfutil import BashWrapper
from mfplugin.utils import get_rpm_cmd, get_default_plugins_base_dir, \
    BadPluginFile


class PluginFile(object):

    plugins_base_dir = None
    plugin_filepath = None
    _name = None
    _version = None
    _release = None
    __loaded = None

    def __init__(self, plugin_filepath, plugins_base_dir=None):
        if plugins_base_dir is not None:
            self.plugins_base_dir = plugins_base_dir
        else:
            self.plugins_base_dir = get_default_plugins_base_dir()
        if not os.path.isfile(plugin_filepath):
            raise BadPluginFile("file: %s not found" % plugin_filepath)
        self.plugin_filepath = plugin_filepath
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
