import fastentrypoints  # noqa: F401
from setuptools import setup
from setuptools import find_packages

with open('requirements.txt') as reqs:
    install_requires = [
        line for line in reqs.read().split('\n')
        if (line and not line.startswith('--')) and (";" not in line)
        and not line.startswith('git+https')]

setup(
    name='mfplugin',
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "plugin_wrapper = mfplugin.cli_tools.plugin_wrapper:main",
            "plugins.list = mfplugin.cli_tools.plugins_list:main",
            #"plugins.info = mfutil.cli_tools.plugins_info:main",
            "plugins.hash = mfutil.cli_tools.plugins_hash:main",
            "_plugins.init = mfutil.cli_tools.plugins_init:main",
            "_plugins.make = mfutil.cli_tools.plugins_make:main",
            "_plugins.develop = mfutil.cli_tools.plugins_develop:main",
            "plugins.install = mfutil.cli_tools.plugins_install:main",
            "plugins.uninstall = mfutil.cli_tools.plugins_uninstall:main"
        ]
    }
)
