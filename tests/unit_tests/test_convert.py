try:
    import lxml.etree as ET
except ImportError:
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

import unittest

from scorer_to_usebio.convert import *

class TestConvert(unittest.TestCase):
    def test_get_boards_played(self):
        xml = ET.XML("""
            <session>
              <board_results>
                <brsection>
                    <result bd="1" ns="1" ew="1"/>
                    <result bd="2" ns="1" ew="2"/>
                </brsection>
              </board_results>
            </session>""")

        played = get_boards_played(xml)
        self.assertEqual(dict(played), {
            '1 NS': 2,
            '1 EW': 1,
            '2 EW': 1,
        })

    def test_get_ids(self):
        res = ET.XML('<result ns="1" ew="2"/>')
        self.assertEqual(get_ns_id(res), '1 NS')
        self.assertEqual(get_ew_id(res), '2 EW')

    def test_get_pair_key(self):
        n1 = ET.XML('<pair dir="N" no="1"/>')
        e2 = ET.XML('<pair dir="E" no="2"/>')
        foo3 = ET.XML('<pair dir="foo" no="3"/>')
        none4 = ET.XML('<pair no="4"/>')
        self.assertEqual(get_pair_key(n1), (0, 1))
        self.assertEqual(get_pair_key(e2), (1, 2))
        self.assertEqual(get_pair_key(foo3), ('foo', 3))
        self.assertEqual(get_pair_key(none4), (None, 4))

    def test_get_pair_direction(self):
        self.assertEqual(get_pair_direction('N'), 'NS')
        self.assertEqual(get_pair_direction('E'), 'EW')
        self.assertEqual(get_pair_direction('foo'), 'foo')

    def test_convert_player(self):
        pair = ET.XML('<pair player_name_1="p1" player_name_2="p2" nzb_no_1="1" nzb_no_2=""/>')
        p1 = convert_player(pair, 1)
        p2 = convert_player(pair, 2)
        self.assertEqual(len(p1), 2)
        self.assertEqual(p1[0].text, 'p1')
        self.assertEqual(p1[1].text, '1')
        self.assertEqual(len(p2), 1)
        self.assertEqual(p2[0].text, 'p2')

    def test_add_master_points(self):
        xml = ET.XML('<result apoints="1" cpoints="3"/>')
        pair = ET.XML('<pair/>')
        add_master_points(xml, pair)
        self.assertEqual(len(pair), 2)
        self.assertEqual(pair[0][0].text, '1')
        self.assertEqual(pair[0][1].text, 'a')
        self.assertEqual(pair[1][0].text, '3')
        self.assertEqual(pair[1][1].text, 'c')

    def test_convert_result_given_3nt(self):
        res = ET.XML("""<result ns="1"
                                ew="2"
                                cont="3 NT"
                                dec="N"
                                lead="SA"
                                res="="
                                score="400"
                                mp_ns="240"
                                mp_ew="50"/>""")

        traveller = convert_result(res)
        self.assertEqual(len(traveller), 9)
        self.assertEqual(traveller[0].text, '1 NS')
        self.assertEqual(traveller[1].text, '2 EW')
        self.assertEqual(traveller[2].text, '3 NT')
        self.assertEqual(traveller[3].text, 'N')
        self.assertEqual(traveller[4].text, 'SA')
        self.assertEqual(traveller[5].text, '=')
        self.assertEqual(traveller[6].text, '400')
        self.assertEqual(traveller[7].text, '240')
        self.assertEqual(traveller[8].text, '50')

    def test_convert_result_given_passed(self):
        res = ET.XML("""<result ns="1"
                                ew="2"
                                cont="pass"
                                dec=""
                                lead=""
                                res=""
                                score=""
                                mp_ns="240"
                                mp_ew="50"/>""")

        traveller = convert_result(res)
        self.assertEqual(len(traveller), 5)

    def test_element(self):
        xml = ET.XML("<parent/>")
        self.assertEqual(element(xml, 'a').text, None)
        self.assertEqual(element(xml, 'a', 'b').text, 'b')
        self.assertEqual(len(xml), 2)

    def test_non_empty_element(self):
        xml = ET.XML("<parent/>")
        self.assertEqual(len(xml), 0)
        non_empty_element(xml, 'a', None)
        self.assertEqual(len(xml), 0)
        non_empty_element(xml, 'a', '')
        self.assertEqual(len(xml), 0)
        non_empty_element(xml, 'a', '0')
        self.assertEqual(len(xml), 1)
        non_empty_element(xml, 'a', '1')
        self.assertEqual(len(xml), 2)

    def test_non_zero_element(self):
        xml = ET.XML("<parent/>")
        self.assertEqual(len(xml), 0)
        non_zero_element(xml, 'a', None)
        self.assertEqual(len(xml), 0)
        non_zero_element(xml, 'a', '')
        self.assertEqual(len(xml), 0)
        non_zero_element(xml, 'a', '0')
        self.assertEqual(len(xml), 0)
        non_zero_element(xml, 'a', '1')
        self.assertEqual(len(xml), 1)

    @unittest.skipIf(using_lxml, "DTDs supported with lxml")
    def test_dtd_not_supported(self):
        tree = ET.ElementTree(ET.XML("<USEBIO/>"))
        self.assertRaises(ValueError, convert, '', True)

    @unittest.skipIf(not using_lxml, "DTDs only supported with lxml")
    def test_add_dtd(self):
        tree = ET.ElementTree(ET.XML("<USEBIO/>"))
        self.assertEqual(tree.docinfo.public_id, None)
        self.assertEqual(tree.docinfo.system_url, None)
        add_dtd(tree)
        self.assertEqual(tree.docinfo.public_id, '-//EBU//DTD USEBIO 1.1//EN')
        self.assertEqual(tree.docinfo.system_url, 'http://www.usebio.org/files/usebio_v1_1.dtd')
