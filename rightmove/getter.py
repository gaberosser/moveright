import requests
from bs4 import BeautifulSoup
from rightmove import parser, consts
from core import get_logger
from time import sleep

logger = get_logger("rightmove_getter")

def _links_from_search(soup, base_url):
    results = soup.find_all('a', attrs={'class': "propertyCard-headerLink"})
    urls = set()
    for el in results:
        par = el.parent.parent.parent
        if 'is-hidden' not in par['class']:
            urls.add(base_url + el['href'])
    return urls


def get_links_one_outcode(outcode_int, find_url, requester=None, per_page=48, index=None):
    """
    :param index: If supplied, this is the pagination parameter. This allows recursive calling.
    """
    outcode = "OUTCODE^%d" % outcode_int
    base_url = "http://www.rightmove.co.uk"
    if requester is None:
        requester = requests
    payload = {
        'locationIdentifier': outcode,
        'numberOfPropertiesPerPage': per_page,
        'viewType': 'LIST',
    }
    if index is not None:
        payload['index'] = index

    resp = requester.get(find_url, params=payload)
    if resp.status_code != 200:
        raise AttributeError("Failed to get links for outcode %s at URL %s. Error: %s" % (
            outcode, find_url, resp.content
        ))

    soup = BeautifulSoup(resp.content, "html.parser")

    if index is None:
        el = soup.find("span", attrs={'class': 'searchHeader-resultCount'})
        nres = int(el.text)
        indexes = range(per_page, nres, per_page)
        # pagination works by supplying an index parameter giving the number of the first link shown (zero indexed)
        # this first result is (obv) the first page. We can then call the function recursively for the remainder
        urls = _links_from_search(soup, base_url)
        for i in indexes:
            try:
                urls.update(get_links_one_outcode(
                    outcode_int,
                    find_url,
                    requester=requester,
                    per_page=per_page,
                    index=i
                ))
            except Exception:
                logger.exception("Failed to get URL results for outcode %s with index %d", outcode, i)
    else:
        urls = _links_from_search(soup, base_url)

    return urls


def outcode_search_payload(outcode_int, index=None, per_page=48, include_sstc=True):
    """
    :param index: If supplied, this is the pagination parameter. This allows recursive calling.
    """
    outcode = "OUTCODE^%d" % outcode_int
    payload = {
        'locationIdentifier': outcode,
        'numberOfPropertiesPerPage': per_page,
        'viewType': 'LIST',
        'includeSSTC': 'true' if include_sstc else 'false',
    }
    if index is not None:
        payload['index'] = index

    return payload


def _run_outcode_search(outcode_int, find_url, requester, payload, retries=3, sec_between_retry=10):
    try_count = 1
    resp = requester.get(find_url, params=payload)
    while try_count <= retries:
        try:
            resp.raise_for_status()
        except Exception:
            logger.error(
                "Failed to get data for outcode %d at URL %s on try %d. Error: %s",
                outcode_int, find_url, try_count, resp.content
            )
            try_count += 1
            sleep(sec_between_retry)
            continue
        else:
            soup = BeautifulSoup(resp.content, "html.parser")
            dat = parser.parse_search_results(soup)
            nres = int(dat['pagination']['last'].strip().replace(',', ''))
            return soup, nres
    raise requests.exceptions.RequestException("Failed to get data for outcode %d" % outcode_int)


def outcode_search_generator(outcode_int, find_url, requester=None, per_page=48):
    """
    :param index: If supplied, this is the pagination parameter. This allows recursive calling.
    """
    if requester is None:
        logger.info("No requester specified, so we will run without request limits.")
        requester = requests
    payload = outcode_search_payload(outcode_int, per_page=per_page)
    try:
        soup, nres = _run_outcode_search(outcode_int, find_url, requester, payload)
        indexes = range(per_page, nres + 1, per_page)  # add one to include final page
        yield soup
    except Exception:
        logger.exception("Failed to get initial results for outcode %d.", outcode_int)
        raise

    for i in indexes:
        payload = outcode_search_payload(outcode_int, per_page=per_page, index=i)
        try:
            soup, nres = _run_outcode_search(outcode_int, find_url, requester, payload)
            yield soup
        except Exception:
            logger.exception("Failed to get page of results for outcode %d with index %d", outcode_int, i)


def search_one_outcode(outcode, property_type, requester=None):
    find_url = consts.FIND_URLS[property_type]
    for i, soup in enumerate(outcode_search_generator(outcode, find_url, requester=requester)):
        try:
            yield parser.parse_from_soup(soup, property_type=property_type)
        except Exception:
            logger.exception("Failed to parse page %d of results for outcode %d.", i, outcode)
            raise
