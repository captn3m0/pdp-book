import os
import markdown
import html5lib
from os import access, R_OK
from PyPDF2 import PdfFileWriter, PdfFileReader
from os.path import isfile
import subprocess
import pdfmerge

class Bookmark:
    def __init__(self, page, title, level=1):
        self.page = page
        self.title = title
        self.level = level

    def __lt__(self, other):
         return self.page < other.page

    def __repr__(self):
        return str([self.page, self.title, self.level])

class Spine:
    def __init__(self):
        self.files = []
        self.currentPage = 1
        self.title = None
        self.bookmarks = []
        self.currentLevel = None
        self.oldBookmarks = []

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
            self.currentLevel = 1
        elif(tag=='h2'):
            b = Bookmark(self.currentPage, element.text, 2)
            self.currentLevel = 2
        elif(tag =='h3'):
            b = Bookmark(self.currentPage, element.text, 3)
            self.currentLevel = 3
        elif(tag =='a'):
            file = element.attrib.get('href')
            b = Bookmark(self.currentPage, element.text, self.currentLevel+1)
            self.currentPage += self._get_pdf_number_of_pages(file)
            self.files.append(file)

        if b:
            self.bookmarks.append(b)

    def _add_bookmark(self, targetFileHandle, title, level, page):
        targetFileHandle.write("BookmarkBegin\n")
        targetFileHandle.write("BookmarkTitle: " + title + "\n")
        targetFileHandle.write("BookmarkLevel: " + str(level) + "\n")
        targetFileHandle.write("BookmarkPageNumber: " + str(page) + "\n")
        targetFileHandle.write("BookmarkZoom: FitHeight\n")

    def _generate_metadata(self, filename, flatten_inner_bookmarks=True):

        with open(filename, 'w') as target:
            if (self.title):
                target.write("InfoBegin\n")
                target.write("InfoKey: Title\n")
                target.write("InfoValue: " + self.title + "\n")

            for b in self.oldBookmarks:
                outer_level = self._get_level_from_page_number(b.page)
                if (flatten_inner_bookmarks):
                    increment = 1
                else:
                    increment = b.level
                level = outer_level + increment
                self.bookmarks.append(Bookmark(b.page+1, b.title, level))

            self.bookmarks.sort()

            for b in self.bookmarks:
                self._add_bookmark(target, b.title, b.level, b.page)

    def _generate_concat_command(self, temp_filename):
        return ["pdftk"] + self.files + ['cat', 'output', temp_filename]

    def _generate_temp_pdf(self, temp_filename):
        # subprocess.run(self._generate_concat_command(temp_filename))
        self._merge(self.files, temp_filename)
        self._parse_old_bookmarks(temp_filename)

    def _get_level_from_page_number(self, page):
        for b in self.bookmarks:
            if (b.page >= page):
                return b.level

    def _iterate_old_bookmarks(self, pdf, bookmarks, level = 1):
        if (isinstance(bookmarks, list)):
            for inner_bookmark in bookmarks:
                self._iterate_old_bookmarks(pdf, inner_bookmark, level+1)
        else:
            pageNumber = pdf.getDestinationPageNumber(bookmarks)
            b = Bookmark(pageNumber, bookmarks.title, level)
            self.oldBookmarks.append(b)

    def _parse_old_bookmarks(self, filename):
        p = PdfFileReader(open(filename, "rb"))
        self._iterate_old_bookmarks(p, p.getOutlines())

    def _update_metadata(self, old_filename, metadata_file, new_filename):
        subprocess.run(['java', '-jar', 'PDFtkBox.jar', old_filename, "update_info", metadata_file, 'output', new_filename])
        # subprocess.run(["pdftk"] + [old_filename, "update_info_utf8", metadata_file, "output", new_filename])

    def _merge(self, paths, output):
        writer = PdfFileWriter()
        for inputFile in paths:
            assert os.path.isfile(inputFile), ERROR_PATH.format(inputFile)
            reader = PdfFileReader(open(inputFile, 'rb'))
            for page in range(1, reader.getNumPages()+1):
                print("Writing "+inputFile+":  " + str(page))
                writer.addPage(reader.getPage(page - 1))
        
        with open(output, 'wb') as stream:
            writer.write(stream)

    def generate(self, filename, delete_temp_files = False):
        METADATA_FILENAME = 'metadata.txt'
        TEMP_PDF_FILENAME = 'temp.pdf'

        self._generate_temp_pdf(TEMP_PDF_FILENAME)
        self._generate_metadata(METADATA_FILENAME)
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

    spine.generate("final.pdf", False)