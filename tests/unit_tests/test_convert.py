try:
    import lxml.etree as ET
except ImportError:
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

import unittest

from decimal import Decimal
from scorer_to_usebio.convert import *

class TestScore(unittest.TestCase):
    def test_fromxml_spurious_handicap(self):
        xml = ET.XML('<result res="0" raw_score="0" handicap="1"/>')
        self.assertRaises(HandicapMismatch, Score.fromxml, xml, False)

    def test_fromxml_missing_handicap(self):
        xml = ET.XML('<result res="0" raw_score="0" handicap="0"/>')
        self.assertRaises(HandicapMismatch, Score.fromxml, xml, True)

    def test_fromxml_no_adjustment_round_down(self):
        xml = ET.XML('<result place="1" res="50.00" raw_score="49.99" handicap="0"/>')
        score = Score.fromxml(xml, False)
        self.assertIsNone(score.adjustment)

    def test_fromxml_no_adjustment_round_up(self):
        xml = ET.XML('<result place="1" res="50.00" raw_score="50.01" handicap="0"/>')
        score = Score.fromxml(xml, False)
        self.assertIsNone(score.adjustment)

    def test_fromxml_adjustment(self):
        xml = ET.XML('<result place="1" res="50.02" raw_score="50.00" handicap="0"/>')
        score = Score.fromxml(xml, False)
        self.assertEqual(score.adjustment, Decimal("0.02"))

    def test_get_master_points(self):
        xml = ET.XML('<result apoints="1" cpoints="3"/>')
        mps = Score.get_master_points(xml)
        self.assertEqual(mps, [
            MasterPoints('a', 1),
            MasterPoints('c', 3),
        ])

class TestPair(unittest.TestCase):
    def test_plays(self):
        p1 = Pair(0, 'ns', [], None)
        p2 = Pair(0, 'ew', [], None)
        p3 = Pair(0, None, [], None)
        self.assertTrue(p1.plays('ns'))
        self.assertFalse(p1.plays('ew'))
        self.assertFalse(p2.plays('ns'))
        self.assertTrue(p2.plays('ew'))
        self.assertTrue(p3.plays('ns'))
        self.assertTrue(p3.plays('ew'))

    def test_get_pair_direction(self):
        self.assertEqual(Pair.get_pair_direction('N'), 'ns')
        self.assertEqual(Pair.get_pair_direction('E'), 'ew')
        self.assertIsNone(Pair.get_pair_direction(''))
        self.assertIsNone(Pair.get_pair_direction('H'))
        self.assertRaises(InvalidDirection, Pair.get_pair_direction, 'x')

class TestTraveller(unittest.TestCase):
    def test_get_trick_count(self):
        self.assertEqual(Traveller.get_trick_count("", ""), 0)
        self.assertEqual(Traveller.get_trick_count("PASS", ""), 0)
        self.assertEqual(Traveller.get_trick_count("1 NT", "="), 7)
        self.assertEqual(Traveller.get_trick_count("1 NT", "-7"), 0)
        self.assertEqual(Traveller.get_trick_count("1 NT", "+6"), 13)
        self.assertEqual(Traveller.get_trick_count("7 S", "-1"), 12)
        self.assertEqual(Traveller.get_trick_count("1 S", "+1"), 8)
        self.assertEqual(Traveller.get_trick_count("1 S", "+6"), 13)

class TestSection(unittest.TestCase):
    def test_get_set_pair_id(self):
        section = Section('A', False)
        section.set_pair_id('ns', 1, 1)
        section.set_pair_id('ew', 1, 2)
        self.assertEqual(section.get_pair_id('ns', 1), 1)
        self.assertEqual(section.get_pair_id('ew', 1), 2)
        self.assertRaises(DuplicatePairMapping, section.set_pair_id, 'ns', 1, 1)

def player(count):
    return Player(str(count), count)

def pair(id=None, number=0, dir=None, players=(player(1), player(2))):
    return Pair(number, dir, players, None, id=id)

class TestSession(unittest.TestCase):
    def test_check_for_duplicates_given_dup_players(self):
        pairs = [pair(id='1'), pair(id='2')]
        self.assertRaises(DuplicatePair, Session.check_for_duplicates, pairs)

    def test_check_for_duplicates_given_dup_ids(self):
        p1 = (player(1), player(2))
        p2 = (player(3), player(4))
        pairs = [pair(id='1', players=p1), pair(id='1', players=p2)]
        self.assertRaises(DuplicatePair, Session.check_for_duplicates, pairs)

    def test_assign_ids_multi_section(self):
        session = Session()
        session.sections['A'] = Section('A', False)
        session.sections['B'] = Section('B', False)
        p1 = [pair(number='1'), pair(number='2')]
        p2 = [pair(dir='ns'), pair(dir='ew')]
        session.assign_ids(session.sections['A'], p1)
        session.assign_ids(session.sections['B'], p2)
        self.assertEqual(p1[0].id, '(A) 1')
        self.assertEqual(p1[1].id, '(A) 2')
        self.assertEqual(p2[0].id, '(B) 0 NS')
        self.assertEqual(p2[1].id, '(B) 0 EW')

class TestEvent(unittest.TestCase):
    def test_invalid_scoring_type(self):
        xml = ET.XML('<session type="foo"/>')
        self.assertRaises(InvalidEventType, Event, "", 1, "foo", None, "", "", None)

    def test_unknown_scoring_type(self):
        xml = ET.XML('<session type="foo"/>')
        self.assertRaises(InvalidEventType, Event.fromxml, xml)

    def test_get_pair_key(self):
        self.assertEqual(Event.get_pair_key(pair(number='1', dir='ns'), False), (None, 1))
        self.assertEqual(Event.get_pair_key(pair(number='1', dir='ns'), True), (False, 1))
        self.assertEqual(Event.get_pair_key(pair(number='1', dir='ew'), True), (True, 1))

class TestFunctions(unittest.TestCase):
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
        self.assertEqual(tree.docinfo.public_id, '-//EBU//DTD USEBIO 1.2//EN')
        self.assertEqual(tree.docinfo.system_url, 'http://www.usebio.org/files/usebio_v1_2.dtd')
