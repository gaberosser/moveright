import requests
from typing import Optional, Dict
from functools import wraps
from datetime import datetime, timedelta
import time
from config import cfg
from core import get_logger

requester_cfg = cfg.get("requester", {})
DEFAULT_REQUEST_FROM = requester_cfg.get("request_from")
DEFAULT_USER_AGENT = requester_cfg.get("user_agent")
DEFAULT_LIMIT_PER_SECOND = requester_cfg.get("limit_per_second")
DEFAULT_LIMIT_PER_HOUR = requester_cfg.get("limit_per_hour")


def increment_time_unit(dt: datetime, unit: str, increment: int=1):
    time_units = ["hour", "minute", "second", "day", "month", "year", "microsecond"]
    time_delta_dict = {
        "hour": timedelta(hours=increment),
        "minute": timedelta(minutes=increment),
        "second": timedelta(seconds=increment),
        "day": timedelta(days=increment),
        "microsecond": timedelta(microseconds=increment)
    }
    if unit == "month":
        kwargs = {k: getattr(dt, k) for k in time_units}
        if kwargs["month"] == 12:
            kwargs["year"] += 1
        kwargs["month"] += 1
        new_dt = datetime(**kwargs)
    elif unit == "year":
        kwargs = {k: getattr(dt, k) for k in time_units}
        kwargs["year"] += 1
        new_dt = datetime(**kwargs)
    else:
        new_dt = dt + time_delta_dict[unit]

    wait_for = (new_dt - datetime.now()).total_seconds()
    return wait_for


class Limiter(object):
    def __init__(self,
                 per_hour: Optional[int] = None,
                 per_minute: Optional[int] = None,
                 per_second: Optional[int] = None,
                 per_day: Optional[int] = None,
                 per_month: Optional[int] = None,
                 per_year: Optional[int] = None):

        self.total_calls = 0
        self.limit_per: Dict[str, Optional[int]] = {
            "hour": per_hour,
            "minute": per_minute,
            "second": per_second,
            "day": per_day,
            "month": per_month,
            "year": per_year,
        }

        self.calls_per: Dict[str, int] = {}
        self.last_check_time: Dict[str, datetime] = {}
        self.logger = get_logger(self.__class__.__name__)

    def check_limits_and_wait(self):
        for k, lim in self.limit_per.items():
            if lim is not None:
                if k in self.last_check_time:
                    if self.calls_per.get(k, 0) >= lim:
                        wait_for = increment_time_unit(self.last_check_time[k], unit=k)
                        if wait_for > 0:
                            self.logger.info("Exceeded per second limit. Sleeping for %.2f seconds...", wait_for)
                            time.sleep(wait_for)
                        # reset the counter
                        self.calls_per[k] = 0
                self.last_check_time[k] = datetime.now()

    def increment_count(self):
        self.total_calls += 1
        for k, lim in self.limit_per.items():
            if lim is not None:
                self.calls_per.setdefault(k, 0)
                self.calls_per[k] += 1


def limited_requests(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        self.check_limits()
        resp = fn(self, *args, **kwargs)
        self.increment_call_counts()
        return resp
    return wrapper


def with_headers(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
        return fn(self, *args, **kwargs)
    return wrapper


class Singleton(type):
    """
    Declare a singleton class by setting `__metaclass__ = Singleton`
    The effect is that `__call__` is called during instantiation, before `__init__`.
    If an instance already exists, we return that, so only one instance ever exists.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # this gets called
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RequesterSingleton(metaclass=Singleton):
    def __init__(self, headers=None, limiter: Optional[Limiter] = None):
        self.limiter = limiter
        # self.limit_per_second = limit_per_second
        #
        # self._total_calls = 0
        # self.calls_this_second = 0
        # self.calls_this_hour = 0
        # self.second_time = datetime.now()
        # self.hour_time = datetime.now()
        self.logger = get_logger(self.__class__.__name__)
        self.headers = requests.utils.default_headers()
        if headers is not None:
            self.headers.update(headers)

    # def increment_call_counts(self):
    #     now = datetime.now()
    #     self._total_calls += 1
    #
    #     if (now - self.second_time).total_seconds() > 1:
    #         self.calls_this_second = 1
    #         self.second_time = now
    #     else:
    #         self.calls_this_second += 1
    #
    #     if (now - self.hour_time).total_seconds() / 3600. > 1:
    #         self.calls_this_hour = 1
    #         self.hour_time = now
    #     else:
    #         self.calls_this_hour += 1
    #
    # def check_limits(self):
    #     """
    #     Test whether we have exceeded any limits and, if so, wait
    #     :return:
    #     """
    #     if self.limit_per_second is not None:
    #         if self.calls_this_second == self.limit_per_second:
    #             # wait until the second is up
    #             wait_til = self.second_time + timedelta(seconds=1)
    #             wait_for = (wait_til - datetime.now()).total_seconds()
    #             self.logger.info("Exceeded per second limit. Sleeping for %.2f seconds...", wait_for)
    #             time.sleep(wait_for)
    #
    #     if self.limit_per_hour is not None:
    #         if self.calls_this_hour == self.limit_per_hour:
    #             # wait until the hour is up
    #             wait_til = self.hour_time + timedelta(hours=1)
    #             wait_for = (wait_til - datetime.now()).total_seconds()
    #             self.logger.info("Exceeded per hour limit. Sleeping for %d minutes...", int(wait_for / 60.))
    #             time.sleep(wait_for)

    def get(self, url, params=None, **kwargs):
        # self.check_limits()
        self.limiter.check_limits_and_wait()
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
        resp = requests.get(url, params=params, **kwargs)
        # self.increment_call_counts()
        self.limiter.increment_count()
        return resp

    def post(self, url, data=None, json=None, **kwargs):
        # self.check_limits()
        self.limiter.check_limits_and_wait()
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
        resp = requests.post(url, data=data, json=json, **kwargs)
        # self.increment_call_counts()
        self.limiter.increment_count()
        return resp


DEFAULT_LIMITER = Limiter(per_hour=DEFAULT_LIMIT_PER_HOUR, per_second=DEFAULT_LIMIT_PER_SECOND)


class MoverightRequester(RequesterSingleton):
    def __init__(self,
                 user_agent: str=DEFAULT_USER_AGENT,
                 request_from: Optional[str]=DEFAULT_REQUEST_FROM,
                 limiter: Optional[Limiter]=DEFAULT_LIMITER):
        self.user_agent = user_agent
        self.request_from = request_from

        headers = {
            'User-Agent': self.user_agent,
        }
        if self.request_from is not None:
            headers['From'] = self.request_from
        super().__init__(headers=headers, limiter=limiter)

