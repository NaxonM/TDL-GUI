import os
import zipfile
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Since we are not running in the main app, we need to add src to the path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.update_manager import Downloader, UpdateWorker

class TestDownloader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('src.update_manager.urllib.request.urlopen')
    def test_download_success(self, mock_urlopen):
        # Mock the network request
        mock_response = MagicMock()
        mock_response.getheader.return_value = '100'
        mock_response.read.side_effect = [b'test data', b'']
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Create a downloader and run it
        progress_values = []
        downloader = Downloader('http://example.com/test.zip', self.temp_dir, progress_callback=progress_values.append)

        dest_path, err = downloader.run()

        # Assertions
        self.assertIsNone(err)
        self.assertIsNotNone(dest_path)
        self.assertTrue(len(progress_values) > 0)
        self.assertEqual(progress_values[-1], 100)

        # Check if the file was downloaded
        self.assertTrue(os.path.exists(dest_path))
        with open(dest_path, 'rb') as f:
            self.assertEqual(f.read(), b'test data')

    @patch('src.update_manager.urllib.request.urlopen')
    def test_download_failure(self, mock_urlopen):
        # Mock a network error
        mock_urlopen.side_effect = Exception('Network error')

        # Create a downloader and run it
        downloader = Downloader('http://example.com/test.zip', self.temp_dir)
        dest_path, err = downloader.run()

        # Assertions
        self.assertIsNone(dest_path)
        self.assertIsNotNone(err)
        self.assertIn('Download failed: Network error', err)


class TestUpdateWorker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tdl_path = os.path.join(self.temp_dir, 'tdl.exe')
        with open(self.tdl_path, 'w') as f:
            f.write('dummy tdl executable')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_extract_zip(self):
        # Create a dummy zip file
        zip_path = os.path.join(self.temp_dir, 'test.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('tdl.exe', 'new tdl executable')

        # Create an update worker
        worker = UpdateWorker('http://example.com/test.zip', '1.0.0', self.tdl_path, self.temp_dir)

        # Extract the zip
        extracted_path = worker._extract_zip(zip_path)

        # Assertions
        self.assertTrue(os.path.exists(extracted_path))
        with open(extracted_path, 'r') as f:
            self.assertEqual(f.read(), 'new tdl executable')

    def test_create_updater_script(self):
        # Create an update worker
        worker = UpdateWorker('http://example.com/test.zip', '1.0.0', self.tdl_path, self.temp_dir)

        # Create the updater script
        new_exe_path = os.path.join(self.temp_dir, 'new_tdl.exe')
        script_path = worker._create_updater_script(new_exe_path)

        # Assertions
        self.assertTrue(os.path.exists(script_path))
        with open(script_path, 'r') as f:
            content = f.read()
            self.assertIn(f'move /Y "{new_exe_path}" "{self.tdl_path}"', content)
            self.assertIn(f'rmdir /S /Q "{self.temp_dir}"', content)


if __name__ == '__main__':
    unittest.main()
