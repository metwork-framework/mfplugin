import os
import shutil
import glob
from mfutil import mkdir_p_or_die, BashWrapperOrRaise, \
    get_unique_hexa_identifier
from mfplugin.plugin import Plugin
from mfplugin.configuration import Configuration
from mfplugin.command import Command
from mfplugin.file import PluginFile
from mfplugin.utils import get_default_plugins_base_dir, \
    get_rpm_cmd, BadPlugin


def with_base_initialized(f):
    def wrapper(self, *args, **kwargs):
        if not self.initialized:
            # FIXME: better exception class
            raise Exception("plugins base not initialized")
        f(self, *args, **kwargs)
    return wrapper


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

    def initialize_plugins_base(self):
        shutil.rmtree(self.plugins_base_dir, ignore_errors=True)
        mkdir_p_or_die(self.plugins_base_dir)
        mkdir_p_or_die(os.path.join(self.plugins_base_dir, "base"))
        cmd = get_rpm_cmd(self.plugins_base_dir, "--initdb")
        BashWrapperOrRaise(cmd, Exception, "can't init plugins base: %s" %
                           self.plugins_base_dir)
        self.initialized = True

    @with_base_initialized
    def make_plugin(self, plugin_home):
        pc = self.plugin_class
        return pc(plugin_home, plugins_base_dir=self.plugins_base_dir,
                  configuration_class=self.configuration_class,
                  command_class=self.command_class)

    @with_base_initialized
    def install_plugin(self, plugin_filepath, ignore_errors=False,
                       quiet=False):
        x = PluginFile(plugin_filepath)
        x.load()
        # FIXME

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        self._plugins = {}
        for directory in glob.glob(os.path.join(self.plugins_base_dir, "*")):
            dname = os.path.basename(directory)
            if dname == "base":
                # special directory (not a plugin one)
                continue
            try:
                plugin = self.make_plugin(directory)
            except BadPlugin as e:
                # FIXME: log warning
                continue
            self._plugins[plugin.name] = plugin

    @property
    def plugins(self):
        self.load()
        return self._plugins
