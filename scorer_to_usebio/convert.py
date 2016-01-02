import decimal

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
# * Phantom(s)
# * Multiple sections
# * Multiple sessions
# * Other movements (e.g. with single winner/mixed direction)
# * No master points awarded
# * Adjusted scores
# * Handicaps
# * Tied places
# * Players without NZB numbers
# * Missing/bad data?

EVENT_TYPES = [
    'MP_PAIRS',
    'BUTLER_PAIRS',
    'CROSS_IMP',
    'AGGREGATE',
    'SWISS_PAIRS',
    'SWISS_PAIRS_CROSS_IMPS',
    'SWISS_PAIRS_BUTLER_IMPS',
    'SWISS_TEAMS',
    'TEAMS_OF_FOUR',
    'INDIVIDUAL',
]

TYPE_MAPPINGS = {
    'MP': 'MP_PAIRS',
}

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
    root = dom.getroot()
    boards_played = get_boards_played(dom)

    converted = ET.Element('USEBIO')
    converted.set('Version', '1.1')

    club = element(converted, 'CLUB')
    element(club, 'CLUB_NAME', root.get('club'))
    element(club, 'CLUB_ID_NUMBER', root.get('club_no'))

    event = element(converted, 'EVENT')
    event.set('EVENT_TYPE', TYPE_MAPPINGS[root.get('scoring_type')])
    element(event, 'PROGRAM_NAME', 'Scorer')
    element(event, 'PROGRAM_VERSION', '140104020')
    element(event, 'EVENT_DESCRIPTION', root.get('event_name'))
    element(event, 'DATE', root.get('event_date'))
    element(event, 'WINNER_TYPE', '2')
    element(event, 'BOARDS_PLAYED', str(max(boards_played.values())))
    element(event, 'MPS_AWARDED_FLAG', 'Y')

    participants = element(event, 'PARTICIPANTS')
    for participant in get_participants(root, boards_played):
        participants.append(participant)

    for board in convert_boards(root):
        event.append(board)

    return converted

def get_boards_played(root):
    played = defaultdict(int)
    for result in root.findall("./board_results/brsection/result"):
        played[get_ns_id(result)] += 1
        played[get_ew_id(result)] += 1

    return played

def get_ns_id(result):
    return "{} NS".format(result.get('ns'))

def get_ew_id(result):
    return "{} EW".format(result.get('ew'))

# TODO: Teams/individual
# TODO: Cross-check with results to ensure sanity/consistency
def get_participants(root, boards_played):
    yield from get_pairs(root, boards_played)

def get_pairs(root, boards_played):
    for in_pair in sorted(root.findall("./scores/scsection/pair"), key=get_pair_key):
        yield convert_pair(in_pair, boards_played)

def get_pair_key(pair):
    dir = get_pair_direction(pair.get('dir'))
    if dir == 'NS':
        dir = 0
    elif dir == 'EW':
        dir = 1
    return (dir, int(pair.get('no')))

def convert_pair(in_pair, boards_played):
    dir = get_pair_direction(in_pair.get('dir'))
    number = "{} {}".format(in_pair.get('no'), dir)

    out_pair = ET.Element('PAIR')
    element(out_pair, 'PAIR_NUMBER', number)
    element(out_pair, 'DIRECTION', dir)
    element(out_pair, 'BOARDS_PLAYED', str(boards_played[number]))

    out_pair.append(convert_player(in_pair, 1))
    out_pair.append(convert_player(in_pair, 2))

    final = decimal.Decimal(in_pair.get('res'))
    raw = decimal.Decimal(in_pair.get('raw_score'))

    element(out_pair, 'PLACE', in_pair.get('place'))
    element(out_pair, 'TOTAL_SCORE', str(final))
    element(out_pair, 'PERCENTAGE', str(final))

    add_master_points(in_pair, out_pair)

    # TODO: Untested
    # TODO: Presumably won't work with handicaps
    if final != raw:
        element(out_pair, 'ADJUSTMENT', str(final - raw))

    # TODO: Untested
    non_zero_element(out_pair, 'HANDICAP', in_pair.get('handicap'))

    return out_pair

def get_pair_direction(dir):
    if dir == 'N':
        return 'NS'
    elif dir == 'E':
        return 'EW'
    else:
        return dir

def convert_player(pair, which):
    player = ET.Element('PLAYER')
    element(player, 'PLAYER_NAME', pair.get("player_name_{}".format(which)))
    nzb_no = pair.get("nzb_no_{}".format(which))
    non_empty_element(player, 'NATIONAL_ID_NUMBER', nzb_no)
    return player

def add_master_points(in_pair, out_pair):
    for type in ['a', 'b', 'c']:
        pts = in_pair.get('{}points'.format(type))
        if pts is None or pts == '0':
            continue

        mp = element(out_pair, 'MASTER_POINTS')
        element(mp, 'MASTER_POINTS_AWARDED', pts)
        element(mp, 'MASTER_POINT_TYPE', type)

def convert_boards(root):
    boards = defaultdict(list)
    for result in root.findall("./board_results/brsection/result"):
        converted = convert_result(result)
        boards[int(result.get('bd'))].append(converted)

    for (number, results) in sorted(boards.items()):
        board = ET.Element('BOARD')
        element(board, 'BOARD_NUMBER', str(number))
        board.extend(results)
        yield board

def convert_result(result):
    line = ET.Element('TRAVELLER_LINE')
    element(line, 'NS_PAIR_NUMBER', get_ns_id(result))
    element(line, 'EW_PAIR_NUMBER', get_ew_id(result))
    element(line, 'CONTRACT', result.get('cont'))
    non_empty_element(line, 'PLAYED_BY', result.get('dec'))
    non_empty_element(line, 'LEAD', result.get('lead'))
    non_empty_element(line, 'TRICKS', result.get('res'))
    non_empty_element(line, 'SCORE', result.get('score'))
    element(line, 'NS_MATCH_POINTS', result.get('mp_ns'))
    element(line, 'EW_MATCH_POINTS', result.get('mp_ew'))
    return line

def element(parent, name, text = None):
    assert parent is not None
    assert name
    elem = ET.SubElement(parent, name)
    if text is not None:
        elem.text = text
    return elem

def non_empty_element(parent, name, text):
    if text:
        element(parent, name, text)

def non_zero_element(parent, name, text):
    if text and text != '0':
        element(parent, name, text)

def add_dtd(tree):
    assert using_lxml
    tree.docinfo.public_id = '-//EBU//DTD USEBIO 1.1//EN'
    tree.docinfo.system_url = 'http://www.usebio.org/files/usebio_v1_1.dtd'
