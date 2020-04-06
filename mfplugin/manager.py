import os
import filelock
import shutil
import glob
from functools import wraps
from mflog import get_logger
from mfutil import mkdir_p_or_die, BashWrapperOrRaise, BashWrapper
from mfutil.layerapi2 import LayerApi2Wrapper
from mfplugin.plugin import Plugin
from mfplugin.configuration import Configuration
from mfplugin.app import App
from mfplugin.extra_daemon import ExtraDaemon
from mfplugin.file import PluginFile
from mfplugin.utils import get_default_plugins_base_dir, \
    get_rpm_cmd, BadPlugin, plugin_name_to_layerapi2_label, \
    NotInstalledPlugin, AlreadyInstalledPlugin, CantInstallPlugin, \
    CantUninstallPlugin, PluginsBaseNotInitialized, \
    _touch_conf_monitor_control_file, get_plugin_lock_path

__pdoc__ = {
    "with_base_initialized": False,
    "with_layerapi2_path": False,
    "with_lock": False,
    "PluginEnvContextManager": False
}
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
LOGGER = get_logger("mfplugin.manager")


def with_base_initialized(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.initialized:
            raise PluginsBaseNotInitialized("plugins base not initialized")
        return f(self, *args, **kwargs)
    return wrapper


def with_layerapi2_path(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        old_mlp = os.environ.get('LAYERAPI2_LAYERS_PATH', '')
        os.environ['LAYERAPI2_LAYERS_PATH'] = \
            self.plugins_base_dir + ":" + old_mlp
        res = f(self, *args, **kwargs)
        os.environ['LAYERAPI2_LAYERS_PATH'] = old_mlp
        return res
    return wrapper


def with_lock(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        lock_path = get_plugin_lock_path()
        lock = filelock.FileLock(lock_path, timeout=10)
        try:
            with lock.acquire(poll_intervall=1):
                res = f(*args, **kwargs)
            _touch_conf_monitor_control_file()
            return res
        except filelock.Timeout:
            LOGGER.warning("can't acquire plugin management lock "
                           " => another plugins.install/uninstall "
                           "running ?")
    return wrapper


class PluginsManager(object):

    def __init__(self, plugins_base_dir=None, plugin_class=Plugin,
                 configuration_class=Configuration,
                 app_class=App,
                 extra_daemon_class=ExtraDaemon):
        self.plugin_class = plugin_class
        """Plugin class."""
        self.configuration_class = configuration_class
        """Configuration class."""
        self.app_class = app_class
        """App class."""
        self.extra_daemon_class = extra_daemon_class
        """ExtraDaemon class."""
        self.plugins_base_dir = plugins_base_dir \
            if plugins_base_dir is not None else get_default_plugins_base_dir()
        """Plugin base directory (string)."""
        self.initialized = \
            os.path.isdir(os.path.join(self.plugins_base_dir, "base"))
        """Is the plugin base directory initialized? (boolean)."""
        self.__loaded = False

    @with_lock
    def initialize_plugins_base(self):
        shutil.rmtree(self.plugins_base_dir, ignore_errors=True)
        mkdir_p_or_die(self.plugins_base_dir)
        mkdir_p_or_die(os.path.join(self.plugins_base_dir, "base"))
        cmd = get_rpm_cmd(self.plugins_base_dir, "--initdb")
        BashWrapperOrRaise(cmd, Exception, "can't init plugins base: %s" %
                           self.plugins_base_dir)
        self.initialized = True

    @with_base_initialized
    @with_layerapi2_path
    def make_plugin(self, plugin_home):
        pc = self.plugin_class
        return pc(self.plugins_base_dir, plugin_home,
                  configuration_class=self.configuration_class,
                  app_class=self.app_class,
                  extra_daemon_class=self.extra_daemon_class)

    @with_base_initialized
    @with_layerapi2_path
    def get_plugin(self, name):
        label = plugin_name_to_layerapi2_label(name)
        home = LayerApi2Wrapper.get_layer_home(label)
        if home is None:
            raise NotInstalledPlugin("plugin: %s not installed" % name)
        return self.make_plugin(home)

    @with_base_initialized
    @with_layerapi2_path
    def plugin_env_context(self, name, **kwargs):
        return self.plugins[name].plugin_env_context(**kwargs)

    def _preuninstall_plugin(self, plugin):
        if shutil.which("_plugins.preuninstall"):
            return BashWrapper("_plugins.preuninstall %s %s %s" %
                               (plugin.name, plugin.version, plugin.release))
        else:
            return BashWrapper("true")

    def _postinstall_plugin(self, plugin):
        if shutil.which("_plugins.postinstall"):
            return BashWrapper("_plugins.postinstall %s %s %s" %
                               (plugin.name, plugin.version, plugin.release))
        else:
            return BashWrapper("true")

    def _uninstall_plugin(self, name):
        p = self.get_plugin(name)
        preuninstall_status = self._preuninstall_plugin(p)
        if not preuninstall_status:
            raise CantUninstallPlugin("can't uninstall plugin: %s" % name,
                                      bash_wrapper=preuninstall_status)
        if p.is_dev_linked:
            os.unlink(p.home)
            return
        cmd = get_rpm_cmd(self.plugins_base_dir, '-e --noscripts %s' % name,
                          add_prefix=False)
        BashWrapperOrRaise(cmd, CantUninstallPlugin,
                           "can't uninstall plugin: %s" % name)
        if p.home:
            shutil.rmtree(p.home, ignore_errors=True)
        try:
            self.get_plugin(name)
        except NotInstalledPlugin:
            pass
        else:
            raise CantUninstallPlugin("can't uninstall plugin: %s" % name)
        if os.path.exists(p.home):
            raise CantUninstallPlugin("can't uninstall plugin: %s "
                                      "(directory still here)" % name)

    def __before_install_develop(self, name):
        try:
            self.get_plugin(name)
        except NotInstalledPlugin:
            pass
        else:
            raise AlreadyInstalledPlugin("plugin: %s is already installed" %
                                         name)

    def __after_install_develop(self, name):
        try:
            p = self.get_plugin(name)
        except NotInstalledPlugin:
            raise CantInstallPlugin("can't install plugin %s" % name)
        postinstall_status = self._postinstall_plugin(p)
        if not postinstall_status:
            try:
                self._uninstall_plugin(p)
            except Exception:
                pass

    def _install_plugin(self, plugin_filepath):
        x = PluginFile(plugin_filepath)
        x.load()
        self.__before_install_develop(x.name)
        cmd = get_rpm_cmd(self.plugins_base_dir,
                          '-Uvh --noscripts --force %s' % plugin_filepath,
                          add_prefix=True)
        BashWrapperOrRaise(cmd, CantInstallPlugin,
                           "can't install plugin %s" % x.name)
        self.__after_install_develop(x.name)

    def _develop_plugin(self, plugin_home):
        p = self.make_plugin(plugin_home)
        self.__before_install_develop(p.name)
        shutil.rmtree(os.path.join(self.plugins_base_dir, p.name), True)
        try:
            os.symlink(p.home, os.path.join(self.plugins_base_dir, p.name))
        except OSError:
            pass
        self.__after_install_develop(p.name)

    @with_lock
    @with_base_initialized
    @with_layerapi2_path
    def install_plugin(self, plugin_filepath):
        """Install a plugin from a .plugin file.

        Args:
            plugin_filepath (string): the plugin file path.

        Raises:
            PluginsBaseNotInitialized: if the plugins base is not initialized.
            BadPluginFile: if the .plugin file is not found or a bad one.
            AlreadyInstalledPlugin: if the plugin is already installed.
            CantInstallPlugin: if the plugin can't be installed.

        """
        self.__loaded = False
        self._install_plugin(plugin_filepath)

    @with_lock
    @with_base_initialized
    @with_layerapi2_path
    def uninstall_plugin(self, name):
        """Uninstall a plugin.

        Args:
            name (string): the plugin name to uninstall.

        Raises:
            PluginsBaseNotInitialized: if the plugins base is not initialized.
            NotInstalledPlugin: if the plugin is not installed
            CantUninstallPlugin: if the plugin can't be uninstalled.

        """
        self.__loaded = False
        self._uninstall_plugin(name)

    @with_lock
    @with_base_initialized
    @with_layerapi2_path
    def develop_plugin(self, plugin_home):
        """Install a plugin in development mode.

        Args:
            plugin_path (string): the plugin path to install.

        Raises:
            PluginsBaseNotInitialized: if the plugins base is not initialized.
            AlreadyInstalledPlugin: if the plugin is already installed.
            BadPlugin: if the provided plugin is bad.
            CantInstallPlugin: if the plugin can't be installed.

        """
        self.__loaded = False
        self._develop_plugin(plugin_home)

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
                LOGGER.warning("found bad plugin in %s => ignoring it "
                               "(details: %s)" % (directory, e))
                continue
            self._plugins[plugin.name] = plugin

    def load_full(self):
        self.load()
        [x.load_full() for x in self.plugins.values()]

    @property
    def plugins(self):
        self.load()
        return self._plugins
