import logging.config
from pathlib import Path

log_file = Path.home() / '.scorer_to_usebio' / 'ScorerConverter.log'

def configure_logging():
    from PyQt5 import QtCore

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,

        'formatters': {
            'brief': {
                'format': '%(message)s',
            },
            'detailed': {
                'format': '%(asctime)s %(module)-17s %(lineno)-4d %(levelname)-8s %(message)s',
            },
        },

        'handlers': {
            'console': {
                'level':'DEBUG',
                'formatter': 'brief',
                'class': 'logging.StreamHandler',
            },

            'file': {
                'level':'DEBUG',
                'formatter': 'detailed',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_file),
                'maxBytes': 1024 * 1024,
                'backupCount': 1,
            },
        },

        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True
        }
    })

    logging.debug('Logging to: %s', log_file)

try:
    import sys
    from . import ScorerConverter
    from PyQt5 import QtWidgets

    def main():
        configure_logging()
        app = QtWidgets.QApplication(sys.argv)
        sc = ScorerConverter(app)
        sc.show()
        app.exec_()
except ImportError:
    def main():
        pass

if __name__ == "__main__":
    main()
