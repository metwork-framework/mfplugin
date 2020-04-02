import os
# common import must be before mfplugin.* imports
from common import with_empty_base, BASE, get_plugin_filepath
from mfplugin.manager import PluginsManager

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@with_empty_base
def test_manager1():
    x = PluginsManager(plugins_base_dir=BASE)
    assert not x.initialized
    x.initialize_plugins_base()
    assert x.initialized
    y = PluginsManager(plugins_base_dir=BASE)
    assert y.initialized
    assert [x for x in y.plugins.items()] == []


def test_manage_with_empty_base():
    PluginsManager(plugins_base_dir=None)


def _install_two_plugin(x):
    package_filepath = get_plugin_filepath(BASE, "plugin1")
    x.install_plugin(package_filepath)
    os.unlink(package_filepath)
    package_filepath = get_plugin_filepath(BASE, "plugin2")
    x.install_plugin(package_filepath)
    os.unlink(package_filepath)
    assert len(x.plugins) == 2
    assert x.plugins["plugin1"].name == "plugin1"
    assert x.plugins["plugin1"].version == "1.2.3"
    assert x.plugins["plugin1"].release == "1"
    assert x.plugins["plugin1"].is_installed
    assert not x.plugins["plugin1"].is_dev_linked
    assert x.plugins["plugin2"].name == "plugin2"
    assert x.plugins["plugin2"].version == "4.5.6"
    assert x.plugins["plugin2"].release == "1"
    assert x.plugins["plugin2"].is_installed
    assert not x.plugins["plugin2"].is_dev_linked


@with_empty_base
def test_install_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    x.initialize_plugins_base()
    _install_two_plugin(x)
    x.plugins["plugin1"].load_full()


@with_empty_base
def test_develop_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    x.initialize_plugins_base()
    home = os.path.join(CURRENT_DIR, "data", "plugin1")
    x.develop_plugin(home)
    assert len(x.plugins) == 1
    assert x.plugins["plugin1"].name == "plugin1"
    assert x.plugins["plugin1"].version == "devlink"
    assert x.plugins["plugin1"].is_dev_linked


@with_empty_base
def test_uninstall_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    x.initialize_plugins_base()
    _install_two_plugin(x)
    x.uninstall_plugin("plugin1")
    assert len(x.plugins) == 1
    assert list(x.plugins.keys())[0] == "plugin2"
