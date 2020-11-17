import os
import sys
import tarfile
import filelock
import shutil
import glob
from functools import wraps
from mfutil import mkdir_p_or_die, BashWrapperOrRaise
from mfutil import get_unique_hexa_identifier
import configupdater
from mfplugin.plugin import Plugin
from mfplugin.configuration import Configuration
from mfplugin.app import App
from mfplugin.extra_daemon import ExtraDaemon
from mfplugin.file import PluginFile
from mfplugin.utils import get_default_plugins_base_dir, \
    BadPlugin, plugin_name_to_layerapi2_label, \
    NotInstalledPlugin, AlreadyInstalledPlugin, CantInstallPlugin, \
    CantUninstallPlugin, \
    _touch_conf_monitor_control_file, get_plugin_lock_path, \
    get_extra_daemon_class, get_app_class, get_configuration_class, \
    layerapi2_label_to_plugin_home, PluginEnvContextManager

__pdoc__ = {
    "with_lock": False
}
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
LOGGER = None


def get_logger(*args, **kwargs):
    global LOGGER
    from mflog import get_logger as real_get_logger
    if LOGGER is None:
        LOGGER = real_get_logger("mfplugin.manager")
    return LOGGER


def with_lock(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        lock_path = get_plugin_lock_path()
        # to avoid an INFO message of the filelock library
        # we call get_logger() here to setup the mflog configuration
        get_logger()
        lock = filelock.FileLock(lock_path, timeout=10)
        try:
            with lock.acquire(poll_intervall=1):
                res = f(*args, **kwargs)
            _touch_conf_monitor_control_file()
            return res
        except filelock.Timeout:
            get_logger().warning("can't acquire plugin management lock "
                                 " => another plugins.install/uninstall "
                                 "running ?")
    return wrapper


class PluginsManager(object):

    def __init__(self, plugins_base_dir=None,
                 configuration_class=None,
                 app_class=None,
                 extra_daemon_class=ExtraDaemon):
        self.configuration_class = get_configuration_class(configuration_class,
                                                           Configuration)
        """Configuration class."""
        self.app_class = get_app_class(app_class, App)
        """App class."""
        self.extra_daemon_class = get_extra_daemon_class(extra_daemon_class,
                                                         ExtraDaemon)
        """ExtraDaemon class."""
        self.plugins_base_dir = plugins_base_dir \
            if plugins_base_dir is not None else get_default_plugins_base_dir()
        """Plugin base directory (string)."""
        if not os.path.isdir(self.plugins_base_dir):
            mkdir_p_or_die(self.plugins_base_dir)
        self.__loaded = False

    def make_plugin(self, plugin_home, dont_read_config_overrides=False):
        return Plugin(self.plugins_base_dir, plugin_home,
                      configuration_class=self.configuration_class,
                      app_class=self.app_class,
                      extra_daemon_class=self.extra_daemon_class,
                      dont_read_config_overrides=dont_read_config_overrides)

    def get_plugin(self, name):
        label = plugin_name_to_layerapi2_label(name)
        home = layerapi2_label_to_plugin_home(self.plugins_base_dir, label)
        if home is None:
            raise NotInstalledPlugin("plugin: %s not installed" % name)
        return self.make_plugin(home)

    def plugin_env_context(self, name, **kwargs):
        return self.plugins[name].plugin_env_context(**kwargs)

    def _preuninstall_plugin(self, plugin):
        if shutil.which("_plugins.preuninstall"):
            env_context = {
                "MFMODULE_PLUGINS_BASE_DIR": self.plugins_base_dir
            }
            # FIXME: should be python methods and not shell
            with PluginEnvContextManager(env_context):
                x = BashWrapperOrRaise(
                    "_plugins.preuninstall %s %s %s" %
                    (plugin.name, plugin.version, plugin.release))
                if len(x.stderr) != 0:
                    print(x.stderr, file=sys.stderr)

    def _postinstall_plugin(self, plugin):
        if shutil.which("_plugins.postinstall"):
            env_context = {
                "MFMODULE_PLUGINS_BASE_DIR": self.plugins_base_dir
            }
            # FIXME: should be python methods and not shell
            with PluginEnvContextManager(env_context):
                x = BashWrapperOrRaise(
                    "_plugins.postinstall %s %s %s" %
                    (plugin.name, plugin.version, plugin.release))
                if len(x.stderr) != 0:
                    print(x.stderr, file=sys.stderr)

    def _uninstall_plugin(self, name):
        p = self.get_plugin(name)
        preuninstall_exception = None
        try:
            self._preuninstall_plugin(p)
        except Exception as e:
            preuninstall_exception = e
            # we keep the exception but we want to continue to remove the
            # plugin
        if p.is_dev_linked:
            os.unlink(p.home)
        else:
            shutil.rmtree(p.home, ignore_errors=True)
        self.__loaded = False
        try:
            self.get_plugin(name)
        except NotInstalledPlugin:
            pass
        else:
            raise CantUninstallPlugin("can't uninstall plugin: %s" % name)
        if os.path.exists(p.home):
            raise CantUninstallPlugin("can't uninstall plugin: %s "
                                      "(directory still here)" % name)
        if preuninstall_exception is not None:
            raise CantUninstallPlugin(
                "the plugin is uninstalled but we "
                "found some problems during preuninstall script",
                original_exception=preuninstall_exception)

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
        try:
            # check plugin validity (configuration...)
            p.load_full()
            # execute postinstall
            self._postinstall_plugin(p)
        except Exception:
            try:
                self._uninstall_plugin(p.name)
            except Exception:
                pass
            raise

    def _install_plugin(self, plugin_filepath, new_name=None):
        x = PluginFile(plugin_filepath)
        x.load()
        self.__before_install_develop(new_name if new_name is not None
                                      else x.name)
        if new_name is not None:
            name = new_name
        else:
            name = x.name
        try:
            tf = tarfile.open(plugin_filepath, "r")
            tf.extractall(self.plugins_base_dir)
            os.rename(os.path.join(self.plugins_base_dir, "metwork_plugin"),
                      os.path.join(self.plugins_base_dir, name))
        except Exception as e:
            raise CantInstallPlugin("can't install plugin %s" % x.name,
                                    original_exception=e)
        if new_name:
            lalpath = os.path.join(self.plugins_base_dir, name,
                                   ".layerapi2_label")
            with open(lalpath, "w") as f:
                f.write(plugin_name_to_layerapi2_label(new_name) + "\n")
        self.__loaded = False
        self.__after_install_develop(new_name if new_name is not None
                                     else x.name)

    def _develop_plugin(self, plugin_home):
        p = self.make_plugin(plugin_home)
        self.__before_install_develop(p.name)
        shutil.rmtree(os.path.join(self.plugins_base_dir, p.name), True)
        try:
            os.symlink(p.home, os.path.join(self.plugins_base_dir, p.name))
        except OSError:
            pass
        self.__loaded = False
        self.__after_install_develop(p.name)

    @with_lock
    def install_plugin(self, plugin_filepath, new_name=None):
        """Install a plugin from a .plugin file.

        Args:
            plugin_filepath (string): the plugin file path.
            new_name (string): alternate plugin name if specified.

        Raises:
            BadPluginFile: if the .plugin file is not found or a bad one.
            AlreadyInstalledPlugin: if the plugin is already installed.
            CantInstallPlugin: if the plugin can't be installed.

        """
        self._install_plugin(plugin_filepath, new_name=new_name)

    @with_lock
    def uninstall_plugin(self, name):
        """Uninstall a plugin.

        Args:
            name (string): the plugin name to uninstall.

        Raises:
            NotInstalledPlugin: if the plugin is not installed
            CantUninstallPlugin: if the plugin can't be uninstalled.

        """
        self._uninstall_plugin(name)

    @with_lock
    def develop_plugin(self, plugin_home):
        """Install a plugin in development mode.

        Args:
            plugin_path (string): the plugin path to install.

        Raises:
            AlreadyInstalledPlugin: if the plugin is already installed.
            BadPlugin: if the provided plugin is bad.
            CantInstallPlugin: if the plugin can't be installed.

        """
        self._develop_plugin(plugin_home)

    def repackage_plugin(self, name):
        p = self.get_plugin(name)
        p.load_full()
        if p.is_dev_linked:
            raise Exception("can't repackage a devlinked plugin")
        tmpdir = os.path.join(MFMODULE_RUNTIME_HOME, "tmp",
                              "plugin_%s" % get_unique_hexa_identifier())
        shutil.copytree(p.home, tmpdir, symlinks=True)
        # FIXME: ? clean ?
        newp = self.make_plugin(tmpdir, dont_read_config_overrides=True)
        newp.load_full()
        x = configupdater.ConfigUpdater(delimiters=('=',),
                                        comment_prefixes=('#',))
        x.optionxform = str
        x.read("%s/config.ini" % tmpdir)
        sections = p.configuration._doc.keys()
        for section in sections:
            for option in p.configuration._doc[section].keys():
                if option.startswith('_'):
                    continue
                val = p.configuration._doc[section][option]
                try:
                    newval = newp.configuration._doc[section][option]
                except Exception:
                    # probably a new section
                    try:
                        x.add_section(section)
                    except Exception:
                        pass
                    newval = None
                try:
                    if newval is None:
                        print("NEW [%s]/%s = %s" % (section, option, val),
                              file=sys.stderr)
                    else:
                        if newval == val:
                            continue
                        print("CHANGED [%s]/%s: %s => %s" %
                              (section, option, newval, val),
                              file=sys.stderr)
                    if isinstance(val, bool):
                        x.set(section, option, "1" if val else "0")
                    else:
                        x.set(section, option, val)
                except Exception:
                    pass
        x.update_file()
        new_p = self.make_plugin(tmpdir)
        return new_p.build()

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
                get_logger().warning("found bad plugin in %s => ignoring it "
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
