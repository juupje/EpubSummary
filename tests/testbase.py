import logging
logging.basicConfig(level=logging.DEBUG)
from unittest import TestCase

class TestBase(TestCase):
    def test_base(self):
        self.test_file = "tests/files/book.epub"

    def get_file(self, filename:str):
        return f"tests/files/{filename}"
