import os
import shutil
# unset_env import must be before mfplugin.* imports
import unset_env  # noqa: F401
from mfplugin.plugin import Plugin

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
BASE = os.path.join(CURRENT_DIR, "tmp", "plugins_base_dir")


def with_empty_base(func):
    def wrapper(*args, **kwargs):
        shutil.rmtree(BASE, True)
        func(*args, **kwargs)
        shutil.rmtree(BASE, True)
    return wrapper


def get_plugin_filepath(base, test_plugin):
    home = os.path.join(CURRENT_DIR, "data", test_plugin)
    x = Plugin(BASE, home)
    assert x.name == test_plugin
    x.load()
    assert not x.is_installed
    assert not x.is_dev_linked
    package_path = x.build()
    assert os.path.isfile(package_path)
    assert package_path.endswith(".plugin")
    return package_path
