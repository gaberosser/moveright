import sqlite3
import os
import copy
from config import cfg
from core import get_logger
import datetime
import collections
import itertools

LOGGER = get_logger("register")
DEFAULT_KWARGS = cfg["sqlite"]

class AccessLog(object):
    _schema = collections.OrderedDict([
        ("dt", "TIMESTAMP NOT NULL"),
        ("outcode", "INTEGER NOT NULL"),
        ("property_type", "INTEGER NOT NULL"),
        ("result", "TEXT"),
        ("success", "INTEGER NOT NULL CHECK( success IN (0, 1) )"),
        ("num_retries", "INTEGER")
    ])
    _default_for_insert = {
        "dt": datetime.datetime.now
    }

    def __init__(self, **kwargs):
        if len(kwargs) == 0:
            kwargs = copy.copy(DEFAULT_KWARGS)

        kwargs["detect_types"] = sqlite3.PARSE_DECLTYPES
        assert "database" in kwargs, "Required kwarg `database` not supplied"
        db_dir = os.path.dirname(kwargs["database"])
        if not os.path.isdir(db_dir):
            os.makedirs(db_dir)
            LOGGER.info("Created new directory %s for sqlite database.", db_dir)
        self.connection = sqlite3.connect(**kwargs)
        LOGGER.info("Using sqlite DB at %s", kwargs["database"])
        self.table_names = None
        self.update_table_names()

    @property
    def cursor(self):
        return self.connection.cursor()

    def update_table_names(self):
        ret = self.cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        vals = ret.fetchall()
        self.table_names = set(itertools.chain(*vals))

    def _create_if_not_exists_sql(self, table_name):
        sql = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]
        last_ = list(self._schema.keys())[-1]
        for attr_name, attr_det in self._schema.items():
            the_el = " ".join([attr_name, attr_det])
            if attr_name != last_:
                # comma on all but the final line
                the_el += ","
            sql.append(the_el)
        sql.append(")")
        return "".join(sql)

    def create_access_log_table(self, table_name, overwrite=False):
        if overwrite:
            sql = f"""
            DROP TABLE {table_name}
            """
            try:
                self.cursor.execute(sql)
                LOGGER.info("Dropped table %s.", table_name)
            except Exception:
                pass
        sql = self._create_if_not_exists_sql(table_name)
        self.cursor.execute(sql)
        self.update_table_names()
        if table_name not in self.table_names:
            raise KeyError(f"I just tried to create a table called {table_name}, but it isn't in the list of table "
                           f"names after an update. Did creation fail?")

    def log(self, table_name, **insert_kwargs):
        if table_name not in self.table_names:
            self.create_access_log_table(table_name)

        # check that the insert kwargs include only fields in the schema
        unknown_kwargs = set(insert_kwargs).difference(self._schema)
        if len(unknown_kwargs) > 0:
            unknown_str = ",".join(unknown_kwargs)
            raise KeyError(f"{len(unknown_kwargs)} unknown insert_kwargs: {unknown_str}.")

        ins_str = f"INSERT INTO {table_name} VALUES("
        ins_vals = []
        last_ = list(self._schema.keys())[-1]
        for k in self._schema:
            val = insert_kwargs.get(k)
            if val is None and k in self._default_for_insert:
                val = self._default_for_insert[k]()
            ins_vals.append(val)
            ins_str += "?"
            if k != last_:
                ins_str += ", "
        ins_str += ");"

        self.cursor.execute(ins_str, tuple(ins_vals))
        self.connection.commit()


