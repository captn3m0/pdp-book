import os
import markdown
import html5lib
from os import access, R_OK
from PyPDF2 import PdfFileReader
from os.path import isfile
import subprocess

class Bookmark:
    def __init__(self, page, title, level=1):
        self.page = page
        self.title = title
        self.level = level
class Spine:
    def __init__(self):
        self.files = []
        self.currentPage = 1
        self.title = None
        self.bookmarks = []
    def _get_pdf_number_of_pages(self, filename):
        assert isfile(filename) and access(filename, R_OK), \
                "File {} doesn't exist or isn't readable".format(filename)
        pdf_reader = PdfFileReader(open(filename, "rb"))
        return pdf_reader.numPages
    def iter(self, element):
        tag = element.tag
        b = None
        if(tag=='h1'):
            if (self.title == None):
                self.title = element.text
            b = Bookmark(self.currentPage, element.text, 1)
        elif(tag=='h2'):
            b = Bookmark(self.currentPage, element.text, 2)
        elif(tag =='h3'):
            b = Bookmark(self.currentPage, element.text, 3)
        elif(tag =='a'):
            file = element.attrib.get('href')
            b = Bookmark(self.currentPage, element.text, 2)
            self.currentPage += self._get_pdf_number_of_pages(file)
            self.files.append(file)

        if b:
            self.bookmarks.append(b)

    def _generate_metadata(self, filename):
        with open(filename, 'w') as target:
            if (self.title):
                target.write("InfoBegin\n")
                target.write("InfoKey: Title\n")
                target.write("InfoValue: " + self.title + "\n")
            for b in self.bookmarks:
                target.write("BookmarkBegin\n")
                target.write("BookmarkTitle: " + b.title + "\n")
                target.write("BookmarkLevel: " + str(b.level) + "\n")
                target.write("BookmarkPageNumber: " + str(b.page) + "\n")

    def _generate_concat_command(self, temp_filename):
        return ["pdftk"] + self.files + ['cat', 'output', temp_filename]

    def _generate_temp_pdf(self, temp_filename):
        subprocess.run(self._generate_concat_command(temp_filename))

    def _update_metadata(self, old_filename, metadata_file, new_filename):
        subprocess.run(["pdftk"] + [old_filename, "update_info", metadata_file, "output", new_filename])

    def generate(self, filename, delete_temp_files = False):
        METADATA_FILENAME = 'metadata.txt'
        TEMP_PDF_FILENAME = 'temp.pdf'

        self._generate_metadata(METADATA_FILENAME)
        self._generate_temp_pdf(TEMP_PDF_FILENAME)
        self._update_metadata(TEMP_PDF_FILENAME, METADATA_FILENAME, filename)

        if (delete_temp_files):
            os.remove(METADATA_FILENAME)
            os.remove(TEMP_PDF_FILENAME)


with open("complete.md", "r", encoding="utf-8") as input_file:
    text = input_file.read()
    html = markdown.markdown(text)
    document = html5lib.parseFragment(html, namespaceHTMLElements=False)
    spine = Spine()
    for e in document.iter():
        spine.iter(e)

    spine.generate("final.pdf", True)