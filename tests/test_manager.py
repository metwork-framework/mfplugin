import os
# common import must be before mfplugin.* imports
from common import with_empty_base, BASE, get_plugin_filepath
from mfplugin.manager import PluginsManager
from mfplugin.compat import get_installed_plugins, get_plugin_info

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
MFMODULE = os.environ.get("MFMODULE", "GENERIC")


@with_empty_base
def test_manager1():
    x = PluginsManager(plugins_base_dir=BASE)
    assert list(x.plugins.items()) == []


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
def test_default_values():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    x.plugins["plugin1"].load_full()
    import json
    print(json.dumps(x.plugins["plugin1"].configuration._doc, indent=4))
    assert x.plugins["plugin1"].configuration.add_plugin_dir_to_python_path


@with_empty_base
def test_install_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    x.plugins["plugin1"].load_full()
    assert int(x.plugins["plugin1"].size) > 0
    assert len(x.plugins["plugin1"].build_date) > 8
    assert len(x.plugins["plugin1"].build_host) > 0
    assert x.plugins["plugin1"].format_version == [1, 0, 0]
    assert len(x.plugins["plugin1"].get_hash()) > 0
    assert x.plugins["plugin1"].get_hash != x.plugins["plugin2"].get_hash()


@with_empty_base
def test_compat():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    tmp = get_installed_plugins(plugins_base_dir=BASE)
    assert len(tmp) == 2
    p1 = [x for x in tmp if x["name"] == "plugin1"][0]
    assert p1["name"] == "plugin1"
    assert p1["version"] == "1.2.3"
    info = get_plugin_info("plugin1", mode="name",
                           plugins_base_dir=BASE)
    assert info["metadatas"]["name"] == "plugin1"
    assert info["metadatas"]["version"] == "1.2.3"
    assert "build_host" in info["metadatas"]
    assert len(info["files"]) > 0


@with_empty_base
def test_develop_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    home = os.path.join(CURRENT_DIR, "data", "plugin1")
    x.develop_plugin(home)
    assert len(x.plugins) == 1
    assert x.plugins["plugin1"].name == "plugin1"
    assert x.plugins["plugin1"].version == "dev_link"
    assert x.plugins["plugin1"].is_dev_linked


@with_empty_base
def test_uninstall_plugin():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    x.uninstall_plugin("plugin1")
    assert len(x.plugins) == 1
    assert list(x.plugins.keys())[0] == "plugin2"


@with_empty_base
def test_get_plugin_env_dict():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    e = x.plugins["plugin1"].get_plugin_env_dict()
    assert e["GENERIC_CURRENT_PLUGIN_NAME"] == "plugin1"
    assert e["GENERIC_CURRENT_PLUGIN_CUSTOM_FOO"] == "bar"


@with_empty_base
def test_cache():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    x.plugins["plugin1"].get_configuration_hash()
    f = x.plugins["plugin1"].get_plugin_env_dict(cache=True)
    assert os.path.isfile("%s/.configuration_cache" %
                          x.plugins["plugin1"].home)
    assert "%s_CURRENT_PLUGIN_CACHE" % MFMODULE not in f
    g = x.plugins["plugin1"].get_plugin_env_dict(cache=True)
    assert "%s_CURRENT_PLUGIN_CACHE" % MFMODULE in g
    del g["%s_CURRENT_PLUGIN_CACHE" % MFMODULE]
    assert len(g) == len(f)


@with_empty_base
def test_plugin_env_context():
    x = PluginsManager(plugins_base_dir=BASE)
    _install_two_plugin(x)
    assert "GENERIC_CURRENT_PLUGIN_CUSTOM_FOO" not in os.environ
    assert "GENERIC_CURRENT_PLUGIN_NAME" not in os.environ
    with x.plugin_env_context("plugin1"):
        assert os.environ["GENERIC_CURRENT_PLUGIN_CUSTOM_FOO"] == "bar"
        assert os.environ["GENERIC_CURRENT_PLUGIN_NAME"] == "plugin1"
    assert "GENERIC_CURRENT_PLUGIN_CUSTOM_FOO" not in os.environ
    assert "GENERIC_CURRENT_PLUGIN_NAME" not in os.environ
