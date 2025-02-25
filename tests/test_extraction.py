from testbase import TestBase
from epubsummary.main import unpack_epub

class TestExtraction(TestBase):
    def test_extract(self):
        self.test_file = self.get_file("book.epub")
        unpack_epub(self.test_file)
