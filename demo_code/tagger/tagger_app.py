import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from typeahead_web import run_api_in_background

from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from PySide6.QtWidgets import QMessageBox

from PySide6.QtCore import QFile


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the QWebEngineView widget to load the html file
        self.browser = QWebEngineView()
        ###html_path = os.path.abspath("tagger_web.html")
        ###self.browser.setUrl(QUrl.fromLocalFile(html_path))
        self.load_html_file()

        # Set up the main window layout
        layout = QVBoxLayout()
        layout.addWidget(self.browser)

        # Set the layout to a central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Set window title and size
        self.setWindowTitle("MAST Data Product Tagger")
        self.resize(1200, 800)

        self.browser.page().profile().downloadRequested.connect(self.handle_download)

    def load_html_file(self):

        if getattr(sys, 'frozen', False):
            # If the application is running in a bundled state
            base_path = sys._MEIPASS
        else:
            # If running in a normal Python environment
            base_path = os.path.dirname(__file__)

        htmlfilepath = os.path.join(base_path, 'tagger_web.html')
        file = QFile(htmlfilepath)
        if not file.open(QFile.ReadOnly | QFile.Text):
            print("Failed to open file")
            return

        html_content = file.readAll().data().decode("utf-8")
        self.browser.setHtml(html_content)

    def handle_download(self, download_item: QWebEngineDownloadRequest):
        # Accept the download
        download_item.accept()

        # Optionally show a message box or handle the download process here
        QMessageBox.information(self, "Download Started", f"Downloading: {download_item.url().toString()}")



def main():
    # Start typeahead and descendant APIs in background
    run_api_in_background()

    # Start the PySide2 app
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
