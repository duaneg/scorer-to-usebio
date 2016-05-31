import argparse
import errno
import sys

from .convert import convert, using_lxml

def swallow_errors(callable, *args):
    try:
        return callable(*args)
    except KeyboardInterrupt:
        pass
    except IOError as err:
        if err.errno == errno.EPIPE:
            pass
        else:
            raise

def include_dtd(opts):
    if using_lxml:
        return opts.dtd
    else:
        return False

def process_file(opts, file):
    converted = convert(file, include_dtd(opts))[1]
    params = {
        'encoding': 'utf-8'
    }
    if using_lxml:
        params['pretty_print'] = opts.pretty
        params['xml_declaration'] = opts.dtd
    converted.write(sys.stdout.buffer, **params)
    sys.stdout.flush()

def process_files(opts):
    for file in opts.files:
        process_file(opts, file)

def main():
    parser = argparse.ArgumentParser(description='Convert scorer results file to USEBIO format.')
    if using_lxml:
        parser.add_argument('-p', '--pretty', help='pretty-print the XML', action='store_true')
        parser.add_argument('-d', '--dtd', help='add a DTD to the XML', action='store_true')
    parser.add_argument('files', metavar='file', nargs='+', help='file(s) to convert')

    opts = parser.parse_args()
    swallow_errors(process_files, opts)
    swallow_errors(sys.stdout.close)

if __name__ == "__main__":
    main()
