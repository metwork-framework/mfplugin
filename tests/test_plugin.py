from common import with_empty_base, BASE  # common import must be first
import os
import pytest
from mfplugin.plugin import Plugin
from mfplugin.utils import BadPlugin

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@with_empty_base
def test_build_plugin():
    home = os.path.join(CURRENT_DIR, "data", "plugin1")
    x = Plugin(BASE, home)
    assert x.name == "plugin1"
    x.load()
    assert not x.is_installed
    assert not x.is_dev_linked
    package_path = x.build()
    assert os.path.isfile(package_path)
    assert package_path.endswith(".plugin")


@with_empty_base
def test_badplugin1():
    """Test plugin with bad config.ini (missing general section)."""
    home = os.path.join(CURRENT_DIR, "data", "badplugin1")
    x = Plugin(BASE, home)
    with pytest.raises(BadPlugin):
        x.load_full()


@with_empty_base
def test_badplugin2():
    """Test plugin with bad .layerapi2_label."""
    home = os.path.join(CURRENT_DIR, "data", "badplugin2")
    with pytest.raises(BadPlugin):
        Plugin(BASE, home)


@with_empty_base
def test_badplugin3():
    """Test plugin with bad config.ini (bad _version format)."""
    home = os.path.join(CURRENT_DIR, "data", "badplugin3")
    x = Plugin(BASE, home)
    with pytest.raises(BadPlugin):
        x.load_full()


@with_empty_base
def test_badplugin4():
    """Test plugin with bad config.ini (missing _license key)."""
    home = os.path.join(CURRENT_DIR, "data", "badplugin4")
    x = Plugin(BASE, home)
    with pytest.raises(BadPlugin):
        x.load_full()
