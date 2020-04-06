import fastentrypoints  # noqa: F401
import sys
from setuptools import setup
from setuptools import find_packages

required = []
dependency_links = []
EGG_MARK = '#egg='
with open('requirements.txt') as reqs:
    for line in reqs.read().split('\n'):
        if line.startswith('-e git:') or line.startswith('-e git+') or \
                line.startswith('git:') or line.startswith('git+'):
            if EGG_MARK in line:
                package_name = line[line.find(EGG_MARK) + len(EGG_MARK):]
                required.append(package_name)
                dependency_links.append(line)
            else:
                print('Dependency to a git repository should have the format:')
                print('git+ssh://git@github.com/xxxxx/xxxxxx#egg=package_name')
                sys.exit(1)
        else:
            required.append(line)

setup(
    name='mfplugin',
    packages=find_packages(),
    install_requires=required,
    include_package_data=True,
    dependency_links=dependency_links,
    entry_points={
        "console_scripts": [
            "plugin_wrapper = mfplugin.cli_tools.plugin_wrapper:main",
            "plugins.list = mfplugin.cli_tools.plugins_list:main",
            "plugins.info = mfplugin.cli_tools.plugins_info:main",
            "plugins.hash = mfplugin.cli_tools.plugins_hash:main",
            "_plugins.init = mfplugin.cli_tools.plugins_init:main",
            "_plugins.make = mfplugin.cli_tools.plugins_make:main",
            "_plugins.develop = mfplugin.cli_tools.plugins_develop:main",
            "plugins.install = mfplugin.cli_tools.plugins_install:main",
            "plugins.uninstall = mfplugin.cli_tools.plugins_uninstall:main",
            "plugins_validate_name = "
            "mfplugin.cli_tools.plugins_validate_name:main",
        ]
    }
)
