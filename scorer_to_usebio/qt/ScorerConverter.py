import logging
import pathlib
import string
import sys
import tempfile

from PyQt5 import QtCore, QtGui, QtWidgets

import scorer_to_usebio

alphanum = string.digits + string.ascii_letters
filename_trans_table = str.maketrans(alphanum + "/ ", alphanum + "-_")

all_filter = 'All files (*)'
scorer_filter = 'Scorer results files (*.xml)'

def sanitise(text):
    return text.translate(filename_trans_table)

def get_default_filename(event):
    return "{}-{}.xml".format(sanitise(event.event_date), sanitise(event.event_name))

class QLogDisplay(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

class PersistentState(object):
    __slots__ = 'output_directory', 'results_directory', 'selected_filter'

    def __init__(self):
        self.clear()

    def clear(self):
        self.output_directory = tempfile.gettempdir()
        self.results_directory = None
        self.selected_filter = all_filter

    def save(self):
        defs = PersistentState()
        settings = PersistentState.create_settings()
        settings.clear()
        for setting in PersistentState.__slots__:
            value = getattr(self, setting)
            if value != getattr(defs, setting):
                settings.setValue(setting, value)
        del settings
        logging.debug("saved persistent state: %s", self)

    def load(self):
        self.clear()
        settings = PersistentState.create_settings()
        for setting in PersistentState.__slots__:
            setattr(self, setting, settings.value(setting, getattr(self, setting)))
        logging.debug("loaded persistent state: %s", self)

    @staticmethod
    def create_settings():
        return QtCore.QSettings("scorer_to_usebio", "ScorerConverter")

class ScorerConverter(QtWidgets.QMainWindow):
    states = {
        'select': 'Please select a scorer results file to convert.',
        'converted_ok': 'Converted: please upload to Pianola and then (optionally) delete.',
        'converted_error': 'An error occurred converting the results: please review the log.',
        'deleted': 'Converted results deleted: exit or select another results file to convert.',
    }

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.results_file = None
        self.persistent = PersistentState()
        self.persistent.load()
        self.initUI()

    def initUI(self):
        selectButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("document-open"), "&Select")
        selectButton.clicked.connect(self.select)

        self.deleteButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-delete"), "&Delete")
        self.deleteButton.setEnabled(False)
        self.deleteButton.clicked.connect(self.delete)

        exitButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("application-exit"), "&Exit")
        exitButton.clicked.connect(self.close)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(selectButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.deleteButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(exitButton)

        logDisplay = QLogDisplay(self)
        logging.getLogger().addHandler(logDisplay)
        logging.getLogger().setLevel(logging.INFO)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(logDisplay.widget)
        mainLayout.addLayout(buttonLayout)

        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(mainLayout)

        logging.info("Saving converted results to '{}'".format(self.persistent.output_directory))

        self.resize(640, 480)
        self.setWindowTitle("Scorer To USEBIO Converter")
        self.setCentralWidget(mainWidget)
        self.setState('select')

    def select(self):
        (filename, filter) = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Select Scorer results file',
            self.persistent.results_directory,
            initialFilter=self.persistent.selected_filter,
            filter=';;'.join([all_filter, scorer_filter]))
        if not filename:
            return

        self.results_file = filename
        self.persistent.selected_filter = filter
        try:
            self.persistent.results_directory = str(pathlib.Path(filename).parent.resolve())
        except FileNotFoundError:
            pass

        self.saveState()

        logging.info("Converting results: '%s'...", filename)
        self.convert(filename)

    def convert(self, filename):
        ok = False
        try:
            (event, xml) = scorer_to_usebio.convert(filename)
            logging.info("Converted results, saving...")
            self.save(event, xml)
            ok = True
        except IOError as err:
            logging.error("IO error: %s", err)
        except SyntaxError as err:
            logging.info("The selected file '%s' does not look like a valid Scorer results file", filename)
            logging.error("Error details: %s", err)
        except scorer_to_usebio.InvalidResultsException as err:
            logging.error("Conversion error: %s", err)
            logging.info("Please raise a support ticket, including the results file you were trying to convert")
        except scorer_to_usebio.InvalidEventType as err:
            logging.error("Could not convert results: %s", err)
            logging.info("Only match point scored events are supported at this time")

        self.setState('converted_ok' if ok else 'converted_error')

    def save(self, event, xml):
        path = pathlib.Path(self.persistent.output_directory) / get_default_filename(event)
        with path.open('wb') as file:
            xml.write(file, encoding='utf-8')
        self.saved = path
        logging.info("Saved converted results to: %s", path)

    def delete(self):
        try:
            self.saved.unlink()
            logging.info("Deleted converted results: %s", self.saved)
            self.setState('deleted')
        except IOError as err:
            logging.error("Error deleting converted results: %s", err)
            self.setState('select')
        self.saved = None
        self.results_file = None

    def exit(self):
        self.saveState()
        self.app.quit()

    def setState(self, state):
        assert state in ScorerConverter.states
        self.state = state
        self.deleteButton.setEnabled(self.state == 'converted_ok')
        self.statusBar().showMessage(ScorerConverter.states[state])
