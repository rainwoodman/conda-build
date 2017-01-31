import os
import json
import tarfile

import pytest

from conda_build.conda_interface import download
from conda_build import api
from conda_build.utils import package_has_file, on_win

from .utils import metadata_dir, assert_package_consistency


def test_convert_wheel_raises():
    with pytest.raises(RuntimeError) as exc:
        api.convert("some_wheel.whl")
        assert "Conversion from wheel packages" in str(exc)


def test_convert_exe_raises():
    with pytest.raises(RuntimeError) as exc:
        api.convert("some_wheel.exe")
        assert "cannot convert:" in str(exc)

def assert_package_paths_matches_files(package_path):
    """Ensure that info/paths.json matches info/files"""
    with tarfile.open(package_path) as t:
        files_content = t.extractfile('info/files').read().decode('utf-8')
        files_set = set(line for line in files_content.split('\n') if line)
        paths_content = json.loads(t.extractfile('info/paths.json').read().decode('utf-8'))

    for path_entry in paths_content['paths']:
        assert path_entry['_path'] in files_set
        files_set.remove(path_entry['_path'])

    assert not files_set # Check that we've seen all the entries in files

@pytest.mark.serial
@pytest.mark.parametrize('base_platform', ['linux', 'win', 'osx'])
@pytest.mark.parametrize('package', [('itsdangerous-0.24', 'itsdangerous.py'),
                                     ('py-1.4.32', 'py/__init__.py')])
def test_convert_platform_to_others(testing_workdir, base_platform, package):
    package_name, example_file = package
    f = 'http://repo.continuum.io/pkgs/free/{}-64/{}-py27_0.tar.bz2'.format(base_platform, package_name)
    fn = "{}-py27_0.tar.bz2".format(package_name)
    download(f, fn)
    expected_paths_json = package_has_file(fn, 'info/paths.json')
    api.convert(fn, platforms='all', quiet=False, verbose=False)
    for platform in ['osx-64', 'win-64', 'win-32', 'linux-64', 'linux-32']:
        python_folder = 'lib/python2.7' if not platform.startswith('win') else 'Lib'
        package = os.path.join(platform, fn)
        assert package_has_file(package,
                                '{}/site-packages/{}'.format(python_folder, example_file))

        if expected_paths_json:
            assert package_has_file(package, 'info/paths.json')
            assert_package_paths_matches_files(package)

@pytest.mark.serial
@pytest.mark.skipif(on_win, reason="we create the package to be converted in *nix, so don't run on win.")
def test_convert_from_unix_to_win_creates_entry_points(test_config):
    recipe_dir = os.path.join(metadata_dir, "entry_points")
    fn = api.get_output_file_path(recipe_dir, config=test_config)
    api.build(recipe_dir, config=test_config)
    for platform in ['win-64', 'win-32']:
        api.convert(fn, platforms=[platform], force=True)
        converted_fn = os.path.join(platform, os.path.basename(fn))
        assert package_has_file(converted_fn, "Scripts/test-script-manual-script.py")
        assert package_has_file(converted_fn, "Scripts/test-script-manual.bat")
        assert package_has_file(converted_fn, "Scripts/test-script-setup-script.py")
        assert package_has_file(converted_fn, "Scripts/test-script-setup.bat")
        assert_package_consistency(converted_fn)
