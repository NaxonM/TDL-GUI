import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import json
import zipfile
import urllib.error

# Add src to path to allow importing TdlManager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.tdl_manager import TdlManager

class TestTdlManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        def mock_init(tdl_manager_instance):
            """A mock __init__ for TdlManager to redirect its bin_dir."""
            # Use self from the outer scope to access the temp_dir
            tdl_manager_instance.bin_dir = os.path.join(self.temp_dir, "bin")
            os.makedirs(tdl_manager_instance.bin_dir, exist_ok=True)
            tdl_manager_instance.executable_name = "tdl.exe"
            tdl_manager_instance.local_tdl_path = os.path.join(tdl_manager_instance.bin_dir, tdl_manager_instance.executable_name)

        # We patch the TdlManager's __init__ to control the bin_dir for testing.
        self.patcher = patch('src.tdl_manager.TdlManager.__init__', mock_init)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.manager = TdlManager()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # --- Tests for check_for_tdl ---

    @patch('shutil.which', return_value=None)
    @patch('os.path.exists')
    def test_check_for_tdl_found_local(self, mock_exists, mock_which):
        mock_exists.return_value = True
        path, status = self.manager.check_for_tdl()
        self.assertEqual(status, 'found_local')
        self.assertEqual(path, self.manager.local_tdl_path)
        mock_exists.assert_called_with(self.manager.local_tdl_path)

    @patch('shutil.which')
    @patch('os.path.exists', return_value=False)
    def test_check_for_tdl_found_path(self, mock_exists, mock_which):
        system_path = os.path.join(os.path.sep, 'usr', 'bin', 'tdl.exe')
        mock_which.return_value = system_path
        path, status = self.manager.check_for_tdl()
        self.assertEqual(status, 'found_path')
        self.assertEqual(path, system_path)
        mock_which.assert_called_with(self.manager.executable_name)

    @patch('shutil.which', return_value=None)
    @patch('os.path.exists', return_value=False)
    def test_check_for_tdl_not_found(self, mock_exists, mock_which):
        path, status = self.manager.check_for_tdl()
        self.assertEqual(status, 'not_found')
        self.assertIsNone(path)

    # --- Tests for download_and_install_tdl ---

    @patch('platform.system', return_value='Linux')
    def test_download_non_windows(self, mock_platform_system):
        path, error = self.manager.download_and_install_tdl()
        self.assertIsNone(path)
        self.assertEqual(error, "Automatic installation is only supported on Windows.")

    @patch('src.tdl_manager.tempfile.gettempdir')
    @patch('src.tdl_manager.urllib.request.urlretrieve')
    @patch('src.tdl_manager.urllib.request.urlopen')
    @patch('platform.architecture', return_value=('64bit', ''))
    @patch('platform.system', return_value='Windows')
    def test_download_success_64bit(self, mock_ps, mock_pa, mock_urlopen, mock_urlretrieve, mock_gettempdir):
        """Tests the success path for a 64-bit Windows download."""
        mock_gettempdir.return_value = self.temp_dir
        # Mock API response
        mock_api_response = MagicMock()
        mock_api_response.read.return_value = json.dumps({'tag_name': 'v0.1.0'}).encode()
        mock_api_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_api_response

        # Mock urlretrieve to create a dummy zip file
        def urlretrieve_side_effect(url, filepath, reporthook=None):
            with zipfile.ZipFile(filepath, 'w') as zf:
                zf.writestr('some_dir/tdl.exe', b'dummy_exe_data')
        mock_urlretrieve.side_effect = urlretrieve_side_effect

        progress_callback = MagicMock()
        path, error = self.manager.download_and_install_tdl(progress_callback)

        self.assertIsNone(error)
        self.assertEqual(path, self.manager.local_tdl_path)
        self.assertTrue(os.path.exists(path)) # Check if the file was actually created
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'dummy_exe_data')

        expected_url = 'https://github.com/iyear/tdl/releases/download/v0.1.0/tdl_Windows_64bit.zip'
        expected_zip_path = os.path.join(self.temp_dir, 'tdl_Windows_64bit.zip')
        mock_urlretrieve.assert_called_with(expected_url, expected_zip_path, unittest.mock.ANY)
        self.assertTrue(progress_callback.called)

    @patch('src.tdl_manager.tempfile.gettempdir')
    @patch('src.tdl_manager.urllib.request.urlretrieve')
    @patch('src.tdl_manager.urllib.request.urlopen')
    @patch('platform.architecture', return_value=('32bit', ''))
    @patch('platform.system', return_value='Windows')
    def test_download_success_32bit(self, mock_ps, mock_pa, mock_urlopen, mock_urlretrieve, mock_gettempdir):
        """Tests the success path for a 32-bit Windows download."""
        mock_gettempdir.return_value = self.temp_dir
        mock_api_response = MagicMock()
        mock_api_response.read.return_value = json.dumps({'tag_name': 'v0.1.0'}).encode()
        mock_api_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_api_response

        def urlretrieve_side_effect(url, filepath, reporthook=None):
            with zipfile.ZipFile(filepath, 'w') as zf:
                zf.writestr('tdl.exe', b'dummy_exe_data_32')
        mock_urlretrieve.side_effect = urlretrieve_side_effect

        path, error = self.manager.download_and_install_tdl()

        self.assertIsNone(error)
        self.assertTrue(os.path.exists(path))
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'dummy_exe_data_32')
        expected_url = 'https://github.com/iyear/tdl/releases/download/v0.1.0/tdl_Windows_32bit.zip'
        expected_zip_path = os.path.join(self.temp_dir, 'tdl_Windows_32bit.zip')
        mock_urlretrieve.assert_called_with(expected_url, expected_zip_path, unittest.mock.ANY)

    @patch('platform.system', return_value='Windows')
    @patch('src.tdl_manager.urllib.request.urlopen')
    def test_download_api_failure(self, mock_urlopen, mock_ps):
        mock_api_response = MagicMock()
        mock_api_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_api_response
        path, error = self.manager.download_and_install_tdl()
        self.assertIsNone(path)
        self.assertIn("Failed to get release info", error)

    @patch('platform.system', return_value='Windows')
    @patch('src.tdl_manager.urllib.request.urlopen', side_effect=urllib.error.URLError("Network Error"))
    def test_download_network_failure(self, mock_urlopen, mock_ps):
        path, error = self.manager.download_and_install_tdl()
        self.assertIsNone(path)
        self.assertIn("A network error occurred: Network Error", error)

    @patch('src.tdl_manager.tempfile.gettempdir')
    @patch('src.tdl_manager.urllib.request.urlretrieve')
    @patch('src.tdl_manager.urllib.request.urlopen')
    @patch('platform.system', return_value='Windows')
    def test_download_zip_no_exe(self, mock_ps, mock_urlopen, mock_urlretrieve, mock_gettempdir):
        mock_gettempdir.return_value = self.temp_dir
        mock_api_response = MagicMock()
        mock_api_response.read.return_value = json.dumps({'tag_name': 'v0.1.0'}).encode()
        mock_api_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_api_response

        def urlretrieve_side_effect(url, filepath, reporthook=None):
            with zipfile.ZipFile(filepath, 'w') as zf:
                zf.writestr('readme.txt', b'some data')
        mock_urlretrieve.side_effect = urlretrieve_side_effect

        path, error = self.manager.download_and_install_tdl()
        self.assertIsNone(path)
        self.assertEqual(error, "Could not find tdl.exe in the downloaded archive.")

if __name__ == '__main__':
    unittest.main()
