"""
Functional tests for epmt_convert_csv module.

Tests exercise the CSV conversion logic using real sample data
from the test/data directory without mocking.
"""
import os
import shutil
import tarfile
import tempfile
import unittest

from epmt.epmtlib import get_install_root
install_root = get_install_root()


class TestExtractJobid(unittest.TestCase):
    """Tests for extract_jobid_from_collated_csv."""

    def test_extract_jobid_standard(self):
        from epmt.epmt_convert_csv import extract_jobid_from_collated_csv
        result = extract_jobid_from_collated_csv("pp053-papiex-615503-0.csv")
        self.assertEqual(result, "615503")

    def test_extract_jobid_from_path(self):
        from epmt.epmt_convert_csv import extract_jobid_from_collated_csv
        result = extract_jobid_from_collated_csv("/some/path/pp053-papiex-999999-1.csv")
        self.assertEqual(result, "999999")


class TestConvCsvForDbcopy(unittest.TestCase):
    """Tests for conv_csv_for_dbcopy using real CSV test data."""

    def setUp(self):
        self.test_csv = os.path.join(install_root, "test", "data", "csv", "pp053-papiex-615503-0.csv")
        self.assertTrue(os.path.isfile(self.test_csv), f"Test CSV not found: {self.test_csv}")
        # Create a working copy in a temp dir
        self.tmpdir = tempfile.mkdtemp(prefix="epmt_test_conv_")
        self.work_csv = os.path.join(self.tmpdir, "pp053-papiex-615503-0.csv")
        shutil.copy2(self.test_csv, self.work_csv)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_conv_csv_produces_output(self):
        from epmt.epmt_convert_csv import conv_csv_for_dbcopy
        out_csv = os.path.join(self.tmpdir, "output.tsv")
        header = conv_csv_for_dbcopy(self.work_csv, out_csv, jobid="615503")
        # Should return a header string on success
        self.assertIsInstance(header, str)
        self.assertIn("tags", header)
        self.assertIn("hostname", header)
        # Output file should exist and have content
        self.assertTrue(os.path.isfile(out_csv))
        self.assertGreater(os.path.getsize(out_csv), 0)

    def test_conv_csv_output_is_tab_separated(self):
        from epmt.epmt_convert_csv import conv_csv_for_dbcopy, OUTPUT_CSV_SEP
        out_csv = os.path.join(self.tmpdir, "output.tsv")
        conv_csv_for_dbcopy(self.work_csv, out_csv, jobid="615503")
        with open(out_csv) as f:
            first_line = f.readline()
        # Output should be tab-separated
        self.assertEqual(OUTPUT_CSV_SEP, '\t')
        self.assertIn('\t', first_line)

    def test_conv_csv_in_place(self):
        from epmt.epmt_convert_csv import conv_csv_for_dbcopy
        original_size = os.path.getsize(self.work_csv)
        header = conv_csv_for_dbcopy(self.work_csv, jobid="615503")
        # File should have been modified in place
        self.assertIsInstance(header, str)
        self.assertTrue(os.path.isfile(self.work_csv))
        # The converted file will differ from the original
        new_size = os.path.getsize(self.work_csv)
        self.assertNotEqual(original_size, new_size)


class TestConvertCsvInTar(unittest.TestCase):
    """Tests for convert_csv_in_tar using a real tarball from test data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="epmt_test_tar_")
        # Create a test tarball from the CSV test data
        csv_file = os.path.join(install_root, "test", "data", "csv", "pp053-papiex-615503-0.csv")
        metadata_file = os.path.join(install_root, "test", "data", "corrupted_csv", "job_metadata")
        self.test_tar = os.path.join(self.tmpdir, "test-615503.tgz")
        with tarfile.open(self.test_tar, "w:gz") as tar:
            tar.add(csv_file, arcname="./pp053-papiex-615503-0.csv")
            tar.add(metadata_file, arcname="./job_metadata")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_convert_csv_in_tar_produces_tsv(self):
        from epmt.epmt_convert_csv import convert_csv_in_tar
        out_tar = os.path.join(self.tmpdir, "output.tgz")
        result = convert_csv_in_tar(self.test_tar, out_tar)
        self.assertTrue(result)
        # Output tar should exist
        self.assertTrue(os.path.isfile(out_tar))
        # Output tar should contain a .tsv file and no .csv
        with tarfile.open(out_tar, "r:gz") as tar:
            names = tar.getnames()
        csv_files = [n for n in names if n.endswith('.csv')]
        tsv_files = [n for n in names if n.endswith('.tsv')]
        self.assertEqual(len(csv_files), 0, "Output tar should not contain .csv files")
        self.assertGreater(len(tsv_files), 0, "Output tar should contain .tsv files")

    def test_convert_csv_in_tar_in_place(self):
        from epmt.epmt_convert_csv import convert_csv_in_tar
        result = convert_csv_in_tar(self.test_tar)
        self.assertTrue(result)
        # The original tar should now contain tsv instead of csv
        with tarfile.open(self.test_tar, "r:gz") as tar:
            names = tar.getnames()
        csv_files = [n for n in names if n.endswith('.csv')]
        self.assertEqual(len(csv_files), 0)

    def test_convert_csv_in_tar_invalid_extension(self):
        from epmt.epmt_convert_csv import convert_csv_in_tar
        with self.assertRaises(ValueError):
            convert_csv_in_tar("/tmp/bad_file.zip")


if __name__ == '__main__':
    unittest.main()
