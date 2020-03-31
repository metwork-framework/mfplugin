import os
import shutil
import glob
from mfutil import mkdir_p_or_die, BashWrapperOrRaise
from mfplugin.plugin import Plugin
from mfplugin.configuration import Configuration
from mfplugin.command import Command
from mfplugin.utils import get_default_plugins_base_dir, \
    validate_plugin_name, get_rpm_cmd


class PluginsManager(object):

    plugin_class = None
    configuration_class = None
    command_class = None
    plugins_base_dir = None
    _plugins = None
    initialized = None
    __loaded = None

    def __init__(self, plugins_base_dir=None, plugin_class=Plugin,
                 configuration_class=Configuration,
                 command_class=Command):
        self.plugin_class = plugin_class
        self.configuration_class = configuration_class
        self.command_class = command_class
        if plugins_base_dir is not None:
            self.plugins_base_dir = plugins_base_dir
        else:
            self.plugins_base_dir = get_default_plugins_base_dir()
        if os.path.isdir(os.path.join(self.plugins_base_dir, "base")):
            self.initialized = True
        else:
            self.initialized = False
        self.__loaded = False

    def make_plugin_from_directory(self, plugin_home):
        return Plugin.make_from_directory(
            self.plugins_base_dir, plugin_home,
            configuration_class=self.configuration_class,
            command_class=self.command_class)

    def initialize_plugins_base(self):
        shutil.rmtree(self.plugins_base_dir, ignore_errors=True)
        mkdir_p_or_die(self.plugins_base_dir)
        mkdir_p_or_die(os.path.join(self.plugins_base_dir, "base"))
        cmd = get_rpm_cmd(self.plugins_base_dir, "--initdb")
        BashWrapperOrRaise(cmd, Exception, "can't init plugins base: %s" %
                           self.plugins_base_dir)
        self.initialized = True

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        self._plugins = []
        for directory in glob.glob(os.path.join(self.plugins_base_dir, "*")):
            dname = os.path.basename(directory)
            valid, _ = validate_plugin_name(dname)
            if not valid:
                continue
            plugin = self.make_plugin_from_directory(directory)
            self._plugins.append(plugin)

    @property
    def plugins(self):
        self.load()
        return self._plugins
