try:
    import lxml.etree as ET
except ImportError:
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

import unittest
import scorer_to_usebio
import os

DIR = os.path.dirname(__file__)
EXAMPLES_DIR = os.path.join(DIR, '..', '..', 'examples')
CONVERTED_DIR = os.path.join(DIR, 'converted')

class IntegrationTest(unittest.TestCase):
    def test(self):
        examples = []

        for root, dirs, files in os.walk(EXAMPLES_DIR):
            for file in files:
                path = os.path.join(root, file)
                if os.path.isfile(path) and path.endswith('.xml'):
                    examples.append(path)

        assert len(examples) > 0
        for path in examples:
            converted = scorer_to_usebio.convert(path, False)[1]
            expected = ET.parse(os.path.join(CONVERTED_DIR, os.path.basename(path)))
            converted_text = ET.tostring(converted.getroot())
            expected_text = ET.tostring(expected.getroot())
            fail_msg = "conversion mismatch for example file {}".format(os.path.normpath(path))
            self.assertEqual(converted_text, expected_text, msg=fail_msg)
