"""Unit tests for epmt.epmt_daemon logging preservation."""

import logging
from os.path import join
import sys
import tempfile
import unittest

from daemon import DaemonContext

from epmt.epmt_daemon import _preserve_logger_file_descriptors


class TestDaemonLogging(unittest.TestCase):
    def test_preserve_logger_file_descriptors_keeps_open_handler_streams(self):
        epmt_logger = logging.getLogger('epmt')
        original_handlers = epmt_logger.handlers[:]
        original_level = epmt_logger.level
        original_propagate = epmt_logger.propagate

        for handler in original_handlers:
            epmt_logger.removeHandler(handler)

        with tempfile.TemporaryDirectory() as tempdir:
            file_handler = logging.FileHandler(join(tempdir, 'epmt.log'))
            stream_handler = logging.StreamHandler()
            epmt_logger.addHandler(file_handler)
            epmt_logger.addHandler(stream_handler)

            try:
                context = DaemonContext()
                context.detach_process = False
                context.stdin = sys.stdin
                context.stdout = sys.stdout
                context.stderr = sys.stderr

                _preserve_logger_file_descriptors(context)

                self.assertIsNotNone(context.files_preserve)
                preserved = set(context.files_preserve)
                self.assertIn(file_handler.stream.fileno(), preserved)
                self.assertIn(stream_handler.stream.fileno(), preserved)
            finally:
                for handler in epmt_logger.handlers[:]:
                    epmt_logger.removeHandler(handler)
                    handler.close()
                for handler in original_handlers:
                    epmt_logger.addHandler(handler)
                epmt_logger.setLevel(original_level)
                epmt_logger.propagate = original_propagate


if __name__ == '__main__':
    unittest.main()
