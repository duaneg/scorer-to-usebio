try:
    import scorer_to_usebio.qt
    from PyQt5 import QtCore, QtTest, QtWidgets
    from scorer_to_usebio.qt import ScorerConverter

    app = QtWidgets.QApplication([])
except ImportError:
    app = None

import string
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

original_get_default_filename = scorer_to_usebio.qt.get_default_filename

def get_random_text():
    return ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(6))

def get_tmp_filename(*args, **kwargs):
    return get_random_text() + original_get_default_filename(*args, **kwargs)

class NonPersistentState(scorer_to_usebio.qt.PersistentState):
    def __init__(self):
        super().__init__()
    def load(self): pass
    def save(self): pass

# TODO: Should be using @patch instead, but can't get it to work
scorer_to_usebio.qt.PersistentState = NonPersistentState

@unittest.skipIf(app is None, "PyQt5 not installed")
class TestScorerConverter(unittest.TestCase):
    def setUp(self):
        self.sc = ScorerConverter(app)

    def test_initial_state(self):
        self.assertIsNone(self.sc.results_file)
        self.assertFalse(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['select'])

    @patch('scorer_to_usebio.qt.get_default_filename', new=get_tmp_filename)
    def test_select_valid(self):
        filename = 'examples/pairs.xml'

        def getOpenFileName(*args, **kwargs):
            return (filename, "")
        QtWidgets.QFileDialog.getOpenFileName = getOpenFileName

        QtTest.QTest.mouseClick(self.sc.selectButton, QtCore.Qt.LeftButton)
        self.assertEqual(self.sc.results_file, filename)
        self.assertTrue(self.sc.saved.name.endswith("16-11-2015-Monday_Afternoon_November_Pairs.xml"))
        self.assertTrue(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['converted_ok'])
        self.assertTrue(self.sc.saved.exists())
        self.sc.saved.unlink()

    @patch('scorer_to_usebio.qt.get_default_filename', new=get_tmp_filename)
    def test_select_nonexistent(self):
        filename = 'blah/nonexistent.xml'

        def getOpenFileName(*args, **kwargs):
            return (filename, "")
        QtWidgets.QFileDialog.getOpenFileName = getOpenFileName

        QtTest.QTest.mouseClick(self.sc.selectButton, QtCore.Qt.LeftButton)
        self.assertEqual(self.sc.results_file, filename)
        self.assertIsNone(self.sc.saved)
        self.assertFalse(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['converted_error'])

    @patch('scorer_to_usebio.qt.get_default_filename', new=get_tmp_filename)
    def test_select_invalid(self):
        filename = 'README.md'

        def getOpenFileName(*args, **kwargs):
            return (filename, "")
        QtWidgets.QFileDialog.getOpenFileName = getOpenFileName

        QtTest.QTest.mouseClick(self.sc.selectButton, QtCore.Qt.LeftButton)
        self.assertEqual(self.sc.results_file, filename)
        self.assertIsNone(self.sc.saved)
        self.assertFalse(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['converted_error'])

    def test_delete(self):
        file = tempfile.NamedTemporaryFile(delete=False)
        file.close()
        path = Path(file.name)
        self.sc.saved = path
        self.assertTrue(path.exists())
        self.sc.deleteButton.setEnabled(True)
        QtTest.QTest.mouseClick(self.sc.deleteButton, QtCore.Qt.LeftButton)
        self.assertFalse(path.exists())
        self.assertIsNone(self.sc.saved)
        self.assertIsNone(self.sc.results_file)
        self.assertFalse(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['deleted'])

    def test_delete_nonexistent(self):
        file = tempfile.NamedTemporaryFile()
        path = Path(file.name)
        file.close()
        self.assertFalse(path.exists())
        self.sc.saved = path
        self.sc.deleteButton.setEnabled(True)
        QtTest.QTest.mouseClick(self.sc.deleteButton, QtCore.Qt.LeftButton)
        self.assertFalse(path.exists())
        self.assertIsNone(self.sc.saved)
        self.assertIsNone(self.sc.results_file)
        self.assertFalse(self.sc.deleteButton.isEnabled())
        self.assertEqual(self.sc.statusBar().currentMessage(), ScorerConverter.status_text['select'])

    @patch('scorer_to_usebio.qt.get_default_filename', new=get_tmp_filename)
    def test_set_output(self):
        dirname = '.'

        def getExistingDirectory(*args, **kwargs):
            return dirname
        QtWidgets.QFileDialog.getExistingDirectory = getExistingDirectory

        QtTest.QTest.mouseClick(self.sc.outputButton, QtCore.Qt.LeftButton)

        self.assertEqual(self.sc.persistent.output_directory, dirname)
