import logging

from collections import namedtuple, OrderedDict
from decimal import Decimal

using_lxml = False
try:
    import lxml.etree as ET
    using_lxml = True
except ImportError:
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

from collections import defaultdict

# TODO:
# * usebio 1.2
# * Teams
# * Other scoring types
# * Phantom
# * No master points awarded
# * Adjusted scores (event level)
# * Tied places
# * Players without NZB numbers
# * Missing/bad data?

EVENT_TYPES = [
    'INDIVIDUAL',
    'PAIRS',
    'SWISS_PAIRS',
    'TEAMS',
    'SWISS_TEAMS',
]

BOARD_SCORINGS = [
    'MATCH_POINTS',
    'BUTLER_IMPS',
    'CROSS_IMPS',
    'AGGREGATE',
    'IMPS',
    'PAB',
    'BAM',
    'HYBRID',
    'OTHER',
]

DECIMAL_001 = Decimal('0.01')

DIRECTIONS = ['ns', 'ew']

class DuplicatePair(Exception):
    def __init__(self, pair):
        super(DuplicatePair, self).__init__("duplicate pair: {}".format(pair))

class DuplicatePairMapping(Exception):
    def __init__(self, dir, dir_id, pair_id1, pair_id2):
        msg = "duplicate mapping for {} {}: {}/{}".format(dir_id, dir, pair_id1, pair_id2)
        super(DuplicatePairMapping, self).__init__(msg)

class InvalidEventType(Exception):
    def __init__(self, type):
        super(InvalidEventType, self).__init__("invalid/unhandled scoring type '{}'".format(type))

class InvalidDirection(Exception):
    def __init__(self, dir):
        super(InvalidDirection, self).__init__("invalid/unknown direction '{}'".format(dir))

class HandicapMismatch(Exception):
    def __init__(self, handicapped, handicap_value):
        if handicapped:
            msg = "handicap value not given for handicapped event"
        else:
            msg = "handicap value {} given for non-handicapped event".format(handicap_value)
        super(HandicapMismatch, self).__init__(msg)

MasterPoints = namedtuple('MasterPoints', ['type', 'points'])

class Score(object):
    def __init__(self, place, total_score, adjustment, handicap, mps):
        self.place = place
        self.total_score = total_score
        self.adjustment = adjustment
        self.handicap = handicap
        self.percentage = total_score
        self.master_points = mps

    @staticmethod
    def fromxml(score, handicapped):
        final = Decimal(score.get('res'))
        raw = Decimal(score.get('raw_score'))
        raw_handicap = score.get('handicap')
        handicap = Decimal(raw_handicap)
        if handicapped == (raw_handicap == '0'):
            raise HandicapMismatch(handicapped, raw_handicap)

        mps = Score.get_master_points(score)

        # TODO: Adjusted scores are untested!
        #
        # I really need to get hold of some adjusted results.
        #
        # The raw, final, and handicap values are all reported to two decimal
        # places, but the final value we compute does not always match that
        # provided (when we know there was no adjustment). Presumbably this is
        # caused by rounding issues.
        #
        # Since it seems we must manually derive an adjustment value we just treat
        # 0.01 differences as unadjusted and greater differences as being adjusted.
        adjustment = None
        expected_final = (raw + handicap / 2).quantize(DECIMAL_001)
        if (final - expected_final).copy_abs() > DECIMAL_001:
            adjustment = final - raw

        return Score(score.get('place'), final, adjustment, handicap, mps)

    @staticmethod
    def get_master_points(score):
        mps = []
        for type in ['a', 'b', 'c']:
            pts = score.get('%spoints' % type)
            if pts is None or pts == '0':
                continue
            mps.append(MasterPoints(type, int(pts)))
        return mps

    def write_usebio_xml(self, xml):
        element(xml, 'PLACE', self.place)
        element(xml, 'TOTAL_SCORE', self.total_score)
        element(xml, 'PERCENTAGE', self.total_score)
        for mps in self.master_points:
            mp_elem = element(xml, 'MASTER_POINTS')
            element(mp_elem, 'MASTER_POINTS_AWARDED', mps.points)
            element(mp_elem, 'MASTER_POINT_TYPE', mps.type)
        non_empty_element(xml, 'ADJUSTMENT', self.adjustment)
        non_zero_element(xml, 'HANDICAP', self.handicap)

class Player(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id

    @staticmethod
    def fromxml(pair, which):
        name = pair.get('player_name_%d' % which)
        id = pair.get('nzb_no_%d' % which)
        return Player(name, id)

    def get_usebio_xml(self):
        player = ET.Element('PLAYER')
        element(player, 'PLAYER_NAME', self.name)
        non_empty_element(player, 'NATIONAL_ID_NUMBER', self.id)
        return player

class Pair(object):
    def __init__(self, number, dir, players, score, id=None):
        self.id = id
        self.number = number
        self.dir = dir
        self.boards_played = 0
        self.players = players
        self.score = score

    def plays(self, dir):
        assert dir in DIRECTIONS
        return self.dir is None or self.dir == dir

    @staticmethod
    def fromxml(pair, handicapped):
        no = pair.get('no')
        dir = Pair.get_pair_direction(pair.get('dir'))
        players = (Player.fromxml(pair, 1), Player.fromxml(pair, 2))
        score = Score.fromxml(pair, handicapped)
        return Pair(no, dir, players, score)

    @staticmethod
    def get_pair_direction(dir):
        if dir == 'N':
            return 'ns'
        elif dir == 'E':
            return 'ew'
        elif dir == 'H' or not dir:
            return None
        else:
            raise InvalidDirection(dir)

    @staticmethod
    def consistent_seating(pairs):
        return not any(filter(lambda pair: pair.dir is None, pairs))

    def get_usebio_xml(self):
        xml = ET.Element('PAIR')
        element(xml, 'PAIR_NUMBER', self.id)
        non_empty_element(xml, 'DIRECTION', self.dir.upper() if self.dir else None)
        element(xml, 'BOARDS_PLAYED', self.boards_played)

        for player in self.players:
            xml.append(player.get_usebio_xml())

        self.score.write_usebio_xml(xml)

        return xml

class Traveller(object):
    def __init__(self, ns, ew, contract, declarer, lead, tricks, score, ns_mps, ew_mps):
        self.ns = ns
        self.ew = ew
        self.contract = contract or None
        self.declarer = declarer or None
        self.lead = lead or None
        self.tricks = tricks
        self.score = score or None
        self.ns_mps = int(ns_mps)
        self.ew_mps = int(ew_mps)

    @staticmethod
    def fromxml(result, section):
        (ns, ew) = [section.get_pair_id(dir, result.get(dir)) for dir in DIRECTIONS]

        # Scorer records what looks like floor(MPs * 10).
        #
        # Nothing we can do about the floor bit, but divide by 10 to get close
        # to proper MP values.
        mp_ns = float(result.get('mp_ns')) / 10
        mp_ew = float(result.get('mp_ew')) / 10

        # Annoying: need to convert from contract/result to count of tricks won
        contract = result.get('cont')

        return Traveller(ns, ew,
                         contract,
                         result.get('dec'),
                         result.get('lead'),
                         Traveller.get_trick_count(contract, result.get('res')),
                         result.get('score'),
                         mp_ns, mp_ew)

    @staticmethod
    def get_trick_count(contract, result):
        parts = contract.split()

        # Check for passed hands/adjusted/phantom(?)
        if len(parts) != 2:
            return 0

        # Otherwise the first part is the level of the contract
        # Add six to get the target number of tricks
        tricks = int(parts[0]) + 6

        # Check for bid & made
        if result == '=':
            return tricks
        else:
            return tricks + int(result)

    def get_usebio_xml(self):
        xml = ET.Element('TRAVELLER_LINE')
        element(xml, 'NS_PAIR_NUMBER', self.ns)
        element(xml, 'EW_PAIR_NUMBER', self.ew)
        non_empty_element(xml, 'CONTRACT', self.contract)
        non_empty_element(xml, 'PLAYED_BY', self.declarer)
        non_empty_element(xml, 'LEAD', self.lead)
        element(xml, 'TRICKS', self.tricks)
        non_empty_element(xml, 'SCORE', self.score)
        element(xml, 'NS_MATCH_POINTS', self.ns_mps)
        element(xml, 'EW_MATCH_POINTS', self.ew_mps)
        return xml

class Section(object):
    def __init__(self, id, handicapped):
        self.id = id
        self.handicapped = handicapped
        self.id_mappings = {
            'ns': {},
            'ew': {},
        }
        self.pairs = []
        self.boards = defaultdict(list)

    def set_pair_id(self, dir, dir_id, pair_id):
        mapping = self.id_mappings[dir]
        if dir_id in mapping:
            raise DuplicatePairMapping(dir, dir_id, mapping[dir_id], pair_id)
        mapping[dir_id] = pair_id

    def get_pair_id(self, dir, id):
        return self.id_mappings[dir][id]

    @staticmethod
    def fromxml(section):
        return Section(section.get('sectid'), section.get('handicapped'))

class Session(object):
    def __init__(self):
        self.pairs = {}
        self.sections = {}

    @staticmethod
    def fromxml(root):
        session = Session()
        session.read_sections(root)
        session.read_pairs(root)
        session.read_boards(root)
        session.fixup_scores()
        return session

    def read_sections(self, root):
        for section in root.findall('./sections/section'):
            self.sections[section.get('sectid')] = Section.fromxml(section)

    def read_pairs(self, root):
        for section in root.findall("./scores/scsection"):
            sdata = self.sections[section.get('id')]
            for pair in section.findall("pair"):
                pair = Pair.fromxml(pair, sdata.handicapped)
                sdata.pairs.append(pair)
            self.assign_ids(sdata, sdata.pairs)

        self.check_for_duplicates(self.pairs.values())

    @staticmethod
    def check_for_duplicates(pairs):
        unique_ids = set()
        unique_pairs = set()
        for pair in pairs:
            if pair.id in unique_ids:
                raise DuplicatePair(pair.id)
            if pair.players in unique_pairs:
                raise DuplicatePair(pair.players)
            unique_ids.add(pair.id)
            unique_pairs.add(pair.players)

    def assign_ids(self, section, pairs):
        id_func = self.get_id_function(section, pairs)
        for pair in pairs:
            pair.id = id_func(pair)
            self.pairs[pair.id] = pair

            # Record the pair number for one or both of NS and EW.
            #
            # If pairs all sit one direction only their number will only be unique
            # to that direction, but may be duplicated for NS/EW. If they move (dir
            # is None) the number will be unique across NS/EW and hence a mapping
            # will be recorded for both directions.
            for dir in DIRECTIONS:
                if pair.plays(dir):
                    section.set_pair_id(dir, pair.number, pair.id)

    def get_id_function(self, section, pairs):

        # If pairs are always seated in the same direction make a unique ID
        # using the direction and number, otherwise the number should be unique
        # itself.
        if Pair.consistent_seating(pairs):
            assign_id_no_sec = lambda pair: "{} {}".format(pair.number, pair.dir.upper())
        else:
            assign_id_no_sec = lambda pair: str(pair.number)

        # If there is more than one section we need to include the section ID also
        if len(self.sections) > 1:
            assign_id_full = lambda pair: "({}) {}".format(section.id, assign_id_no_sec(pair))
        else:
            assign_id_full = assign_id_no_sec

        return assign_id_full

    def read_boards(self, root):
        for section in root.findall("./board_results/brsection"):
            sec_id = section.get('id')
            sdata = self.sections[sec_id]
            for result in section.findall("result"):
                board = int(result.get('bd'))
                traveller = Traveller.fromxml(result, sdata)
                sdata.boards[board].append(traveller)
                for dir in DIRECTIONS:
                    pair = self.get_pair(sec_id, dir, result.get(dir))
                    pair.boards_played += 1

    def get_pair(self, sec_id, dir, dir_id):
        pair_id = self.sections[sec_id].get_pair_id(dir, dir_id)
        return self.pairs[pair_id]

    def fixup_scores(self):
        for section in self.sections.values():
            for boards in section.boards.values():
                for traveller in boards:
                    if traveller.score == 'Adj':

                        # TODO: Need to figure this out from the MPs awarded
                        #       This is somewhat involved, so for now:
                        traveller.score = 'A5050'

class Event(object):
    def __init__(self,
                 club_name,
                 club_id,
                 scoring_type,
                 board_scoring,
                 event_name,
                 event_date,
                 session):

        if scoring_type not in EVENT_TYPES:
            raise InvalidEventType(scoring_type)

        self.club_name = club_name
        self.club_id = int(club_id)
        self.scoring_type = scoring_type
        self.board_scoring = board_scoring
        self.event_name = event_name
        self.event_date = event_date
        self.session = session

        # If all pairs always sit the same direction report two winners
        if Pair.consistent_seating(session.pairs.values()):
            self.winners = 2
        else:
            self.winners = 1

    @staticmethod
    def fromxml(root):

        # TODO
        if root.get('scoring_type') != 'MP':
            raise InvalidEventType(root.get('scoring_type'))

        session = Session.fromxml(root)
        return Event(root.get('club'),
                     root.get('club_no'),
                     'PAIRS',
                     None,
                     root.get('event_name'),
                     root.get('event_date'),
                     session)

    def get_usebio_xml(self):
        xml = ET.Element('USEBIO')
        xml.set('Version', '1.2')

        club = element(xml, 'CLUB')
        element(club, 'CLUB_NAME', self.club_name)
        element(club, 'CLUB_ID_NUMBER', self.club_id)

        max_boards = max([pair.boards_played for pair in self.session.pairs.values()])

        event = element(xml, 'EVENT')
        event.set('EVENT_TYPE', self.scoring_type)
        element(event, 'PROGRAM_NAME', 'Scorer')
        element(event, 'PROGRAM_VERSION', '140104020')
        element(event, 'EVENT_DESCRIPTION', self.event_name)
        element(event, 'DATE', self.event_date)
        element(event, 'WINNER_TYPE', self.winners)
        non_empty_element(event, 'BOARD_SCORING_METHOD', self.board_scoring)
        element(event, 'BOARDS_PLAYED', max_boards)
        element(event, 'MPS_AWARDED_FLAG', 'Y')

        for (sec_id, sdata) in sorted(self.session.sections.items()):

            # If there is a single section omit the tag
            if len(self.session.sections) == 1:
                section = event
            else:
                section = element(event, 'SECTION')
                section.set('SECTION_ID', sec_id)

            consistent = Pair.consistent_seating(sdata.pairs)

            participants = element(section, 'PARTICIPANTS')
            for pair in sorted(sdata.pairs, key=lambda pair: Event.get_pair_key(pair, consistent)):
                participants.append(pair.get_usebio_xml())

            for board_id in sorted(sdata.boards.keys()):
                board = element(section, 'BOARD')
                element(board, 'BOARD_NUMBER', board_id)
                for traveller in sdata.boards[board_id]:
                    board.append(traveller.get_usebio_xml())

        return xml

    @staticmethod
    def get_pair_key(pair, use_dir):
        return (pair.dir != 'ns' if use_dir else None, int(pair.number))

def convert(file, include_dtd = False):
    if include_dtd and not using_lxml:
        raise ValueError("DTDs are only supported when using lxml")

    dom = ET.parse(file)
    converted = convert_xml(dom)
    tree = ET.ElementTree(converted)
    if include_dtd:
        add_dtd(tree)
    return tree

def convert_xml(dom):
    event = Event.fromxml(dom.getroot())
    return event.get_usebio_xml()

def element(parent, name, value = None):
    assert parent is not None
    assert name
    elem = ET.SubElement(parent, name)
    if value is not None:
        elem.text = str(value)
    return elem

def non_empty_element(parent, name, value):
    if value:
        element(parent, name, value)

def non_zero_element(parent, name, value):
    if value and value != '0':
        element(parent, name, value)

def add_dtd(tree):
    assert using_lxml
    tree.docinfo.public_id = '-//EBU//DTD USEBIO 1.2//EN'
    tree.docinfo.system_url = 'http://www.usebio.org/files/usebio_v1_2.dtd'
