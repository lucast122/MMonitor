from typing import List, Tuple, Any

import sqlite3
import pandas as pd


class MMonitorDBInterface:

    def __init__(self, db_path: str):
        self._db_path = db_path

    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        con = sqlite3.connect(self._db_path)
        df = pd.read_sql_query(query, con)
        con.close()
        return df

    def query_to_list(self, query: str) -> List[Tuple[Any]]:
        con = sqlite3.connect(self._db_path)
        ls = list(con.execute(query))
        con.close()
        return ls

    def get_abundance_meta_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        q = "SELECT mmonitor.sample_id, mmonitor.abundance, metadata.* " \
            "FROM mmonitor " \
            "INNER JOIN metadata " \
            "WHERE mmonitor.sample_id = metadata.sample_id " \
            f"AND mmonitor.taxonomy = '{taxonomy}' " \
            "ORDER BY mmonitor.sample_id"
        return self.query_to_dataframe(q)

    def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        q = f"SELECT sample_id, abundance FROM mmonitor WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
        return self.query_to_dataframe(q)

    def get_all_meta(self) -> pd.DataFrame:
        q = "SELECT * FROM metadata ORDER BY sample_id"
        return self.query_to_dataframe(q)

    def get_unique_taxonomies(self) -> List[str]:
        q = "SELECT DISTINCT taxonomy FROM mmonitor"
        return [t[0] for t in self.query_to_list(q)]
