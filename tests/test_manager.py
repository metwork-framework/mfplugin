from common import with_empty_base, BASE  # common import must be first
from mfplugin.manager import PluginsManager


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
