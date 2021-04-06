# -*- coding: utf-8 -*-
import re
import json
from rightmove import consts

NOT_PROPERTY = {
    'plot',
    'land',
    'block of apartments',
    'log cabin'
}

BUILDING_TYPE_MAP_EXTRA = {
    'studio flat': consts.BUILDING_TYPE_STUDIO_FLAT,
    'studio apartment': consts.BUILDING_TYPE_STUDIO_FLAT,
    'flat': consts.BUILDING_TYPE_FLAT,
    'apartment': consts.BUILDING_TYPE_FLAT,
}

BUILDING_TYPE_MAP = dict([
    (t[1].lower(), t[0]) for t in consts.BUILDING_TYPE_CHOICES
])
BUILDING_TYPE_MAP.update(BUILDING_TYPE_MAP_EXTRA)


BUILDING_SITUATION_MAP = {
    "detached": consts.BUILDING_SITUATION_DETACHED,
    "semi-detached": consts.BUILDING_SITUATION_SEMIDETACHED,
    "end of terrace": consts.BUILDING_SITUATION_ENDTERRACE,
    "terraced": consts.BUILDING_SITUATION_MIDTERRACE,
    "link detached": consts.BUILDING_SITUATION_LINKDETACHED,
    "ground floor": consts.BUILDING_SITUATION_GROUNDFLOOR,
}

STATION_TYPE_MAP = {
    "icon-national-train-station": consts.STATION_TYPE_NATIONAL_RAIL,
    "icon-tram-station": consts.STATION_TYPE_TRAM,
    "icon-london-underground": consts.STATION_TYPE_UNDERGROUND,
    "icon-london-overground": consts.STATION_TYPE_OVERGROUND,
}

removed_re = re.compile(r'This property has been removed by the agent', flags=re.I)
situation_re = re.compile("(?P<t>%s)" % "|".join(BUILDING_SITUATION_MAP.keys()), flags=re.I)
type_re = re.compile("(?P<t>%s)" % "|".join(BUILDING_TYPE_MAP.keys()), flags=re.I)
not_property_re = re.compile("(?P<t>%s)" % "|".join(NOT_PROPERTY), flags=re.I)
latlng_re = re.compile(r"latitude=(?P<lat>[-0-9\.]*).*longitude=(?P<lng>[-0-9\.]*)")

rent_bills_incl = re.compile(r"(?<!part )bills inclu[^ ]* +(?!for)", flags=re.I)


def parse_search_results(soup):
    el = soup.find('script', text=re.compile(r'window\.jsonModel = '))
    dat = json.loads(re.sub(r'^[^ ]* = ', '', el.text))
    return dat


def property_array_from_search(soup):
    el = soup.find('script', text=re.compile(r'window\.jsonModel = '))
    dat = json.loads(re.sub(r'^[^ ]* = ', '', el.text))
    return dat['properties']


def parse_search_result_base(attr, property_type):
    """
    Base function to parse essential results.
    :param attr: As generated from property_array_from_search
    :return:
    """
    error = {}

    # WGS84 coordinates
    loc = {
        "lat": attr['location']['latitude'],
        "lon": attr['location']['longitude']
    }

    featured = attr['featuredProperty']

    building_type = None
    building_situation = None

    prop = attr['propertyTypeFullDescription']
    prop = re.sub(' for sale.*$', '', prop)
    prop = re.sub('[1-9]* bedroom *', '', prop)

    is_retirement = False
    if re.search('retirement', prop):
        is_retirement = True

    if re.search('studio', prop, flags=re.I):
        n_bed = 1
    else:
        n_bed = int(attr['bedrooms'])

    sit = re.search(situation_re, prop)
    if sit:
        t = sit.group('t').lower()
        if t in BUILDING_SITUATION_MAP:
            building_situation = BUILDING_SITUATION_MAP[t]
        else:
            error['building_situation'] = t
        prop = re.sub(situation_re, "", prop).strip()

    typ = re.search(type_re, prop)
    if typ:
        t = typ.group('t').lower()
        if t in BUILDING_TYPE_MAP:
            building_type = BUILDING_TYPE_MAP[t]
            if building_type == consts.BUILDING_TYPE_FLAT:
                building_situation = consts.BUILDING_SITUATION_FLAT
        else:
            error['failure_reason'] = 'Unknown building type'
            error['building_type'] = t
            # set as unknown
            building_type = consts.BUILDING_TYPE_UNKNOWN
    elif re.search(not_property_re, prop):
        # The listing is for a type of property we are not tracking (e.g. block of apartments, land)
        error['FAILED'] = True
        error['failure_reason'] = 'Ignored building type'
        error['building_type'] = re.search(not_property_re, prop).group('t')
    else:
        error['FAILED'] = True
        error['failure_reason'] = 'Cannot identify building type'
        error['building_type'] = prop

    this = dict(
        property_type=property_type,
        featured=featured,
        building_type=building_type,
        building_situation=building_situation,
        n_bed=n_bed,
        agent_name=attr['customer']['brandTradingName'],
        agent_attribute=attr['customer']['branchName'],
        address_string=attr['displayAddress'],
        location=loc,
        asking_price=attr['price']['amount'],
        is_retirement=is_retirement,
    )
    if attr.get('displayStatus'):
        this['status'] = attr['displayStatus']

    return this, error


def parse_residential_for_sale_result(attr):
    return parse_search_result_base(attr, consts.PROPERTY_TYPE_FORSALE)


def parse_residential_rent_result(attr):
    this, e = parse_search_result_base(attr, property_type=consts.PROPERTY_TYPE_TORENT)
    this['payment_frequency'] = attr['price']['frequency']
    this['is_house_share'] = (re.search('house share', attr['propertySubType'], flags=re.I) is not None)
    this['inclusive_bills'] = (re.search(rent_bills_incl, attr['summary']) is not None)

    return this, e


def parse_from_soup(soup, property_type):
    """
    :param soup: BeautifulSoup parsed object.
    :param property_type: consts.PROPERTY_TYPE integer. THIs is used to define the parser.
    :return: res, errors
    res: list of tuples, each is (url_string, deferred object)
    errors: dictionary, keyed by URL

    Parse a page of search results from the soup.
    """

    parser_lookup = {
        consts.PROPERTY_TYPE_FORSALE: parse_residential_for_sale_result,
        consts.PROPERTY_TYPE_TORENT: parse_residential_rent_result,
    }
    if property_type not in parser_lookup:
        raise NotImplementedError("Property type not supported.")
    parse_func = parser_lookup[property_type]

    res = []
    errors = {}

    for attr in property_array_from_search(soup):
        url = consts.BASE_URL + attr['propertyUrl']
        try:
            obj, e = parse_func(attr)
            if len(e):
                errors[url] = e
            else:
                res.append(
                    (url, obj)
                )
        except Exception as exc:
            errors[url] = repr(exc)

    return res, errors
