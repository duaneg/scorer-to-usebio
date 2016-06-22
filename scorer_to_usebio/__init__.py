from .convert import Event, InvalidEventType, InvalidResultsException, Session, convert, using_lxml

try:
    from scorer_to_usebio.qt import main as gui
except ImportError:
    def gui():
        import sys
        from pathlib import Path

        print("You must install PyQt5 in order to use the GUI")
        print("\nTry running the following command:")
        pip = Path(sys.executable).parent / "pip"
        print("{} install PyQt5".format(pip))

__all__ = [Event, InvalidEventType, InvalidResultsException, Session, convert, gui, using_lxml]
