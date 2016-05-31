import sys

try:
    from . import ScorerConverter
    from PyQt5 import QtWidgets

    def main():
        app = QtWidgets.QApplication(sys.argv)
        sc = ScorerConverter(app)
        sc.show()
        app.exec_()

    if __name__ == "__main__":
        main()
except ImportError:
    def main():
        pass
