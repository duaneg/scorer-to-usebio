try:
    from .ScorerConverter import ScorerConverter
    __all__ = [ScorerConverter]
except ImportError:
    import pathlib
    import sys
    print("You must install PyQt5 in order to use the GUI")
    print("Try running the following command:")
    pip = pathlib.Path(sys.executable).parent / "pip"
    print("{} install PyQt5".format(pip))
