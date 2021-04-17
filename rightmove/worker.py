from core import requester, get_logger
from rightmove import getter, consts, parser
import pymongo
from config import cfg
import pytz
from datetime import datetime

LOGGER = get_logger("rightmove_worker")
REQUESTER = requester.MoverightRequester()
TIMEZONE = cfg["env"].get("timezone", "utc")
VERSION = cfg["env"]["version"]
MONGO_CLI = None


def mongo_connection():
    global MONGO_CLI
    if MONGO_CLI is None:
        MONGO_CLI = pymongo.MongoClient(**cfg["mongodb"])
    return MONGO_CLI["rightmove"]

def add_retrieval_meta(attr, **kwargs):
    """
    Iterate through the array of attribute dictionaries, adding metadata related to retrieval in-place.
    :param attr_arr:
    :return:
    """
    to_add = {
        "user_agent": REQUESTER.user_agent,
        "request_from": REQUESTER.request_from,
        "timestamp": datetime.now(pytz.timezone(TIMEZONE)),
        "version": VERSION
    }
    to_add.update(kwargs)
    if "__retrieval_meta" in attr:
        LOGGER.warning(
            "attr dict already contains __retrieval_meta: %s",
            str(attr)
        )
    else:
        attr["__retrieval_meta"] = {}
    attr["__retrieval_meta"].update(to_add)


def get_one_outcode(outcode, property_type, **retrieval_meta_kwargs):
    """
    Get the raw attributes for one outcode and store in MongoDB
    :param outcode:
    :param property_type:
    :param retrieval_meta_kwargs: Any kwargs will be passed into the retrieval metadata
    :return: None
    """
    db_name = consts.PROPERTY_TYPE_MAP[property_type]
    coll = mongo_connection()[db_name]
    find_url = consts.FIND_URLS[property_type]
    oids = []
    for i, soup in enumerate(getter.outcode_search_generator(outcode, find_url, requester=REQUESTER)):
        try:
            attr_arr = parser.property_array_from_search(soup)
        except Exception:
            LOGGER.exception("Failed to parse property array from page %d of results of outcode %d.",
                             i + 1, outcode)
            raise
        if len(attr_arr) > 0:
            for attr in attr_arr:
                add_retrieval_meta(attr, outcode=outcode, property_type=property_type, **retrieval_meta_kwargs)
            resp = coll.insert_many(attr_arr)
            oids.extend(resp.inserted_ids)
    return oids

def get_all_outcodes(property_type):
    """
    Iterate over all outcodes and store the results in MongoDB
    :param property_type:
    :return:
    """
    oids = {}
    for outcode, pc in consts.OUTCODE_MAP.items():
        LOGGER.info("Getting %s for outcode %d.",
                    consts.PROPERTY_TYPE_MAP[property_type],
                    outcode)
        try:
            oids[outcode] = get_one_outcode(outcode, property_type, outcode_postcode=pc)
        except Exception:
            LOGGER.exception("Failed to retrieve results for outcode %d.", outcode)