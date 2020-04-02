import os
import pytest
# common import must be before mfplugin* imports
from common import with_empty_base, BASE, get_plugin_filepath
from mfplugin.plugin import Plugin
from mfplugin.utils import BadPlugin

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@with_empty_base
def test_build_plugin():
    # this is going to build a plugin
    package_path = get_plugin_filepath(BASE, "plugin1")
    assert package_path.endswith(".plugin")
    os.unlink(package_path)


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
