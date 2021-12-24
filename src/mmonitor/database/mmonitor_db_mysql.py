from typing import List, Tuple, Any

import sqlite3
from mysql.connector import connect
import pandas as pd


class MMonitorDBInterface:

    def __init__(self, db_path: str):
        self._db_path = db_path

    def create_mysql_db(self,user_name: str):
        with connect(user='admin', password='admin', host='localhost', database='mmonitor') as mysql_con:
            cur = mysql_con.cursor()
            cur.execute(f"CREATE DATABASE {user_name}")
            mysql_con.commit()





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
        return [t[0] for t in self.query_t/Users/timolucas/PycharmProjects/MMonitor/src/mmonitor/userside/classifier_out/test_kraken_outo_list(q)]

    def kraken_out_to_query(self, kraken_out_path: str, tax_rank: str, sample_name: str) -> str:
        df = pd.read_csv(
            kraken_out_path,
            sep='\t',
            header=None,
            usecols=[1, 3, 5],
            names=['Count', 'Rank', 'Name']
        )


        df = df.sort_values('Count', ascending=False)

        # format name
        df['Name'] = df['Name'].apply(lambda s: s.strip())

        # add sample name
        df['Sample'] = sample_name


        df = df[df['Rank'] == tax_rank]
        df = df.drop(columns='Rank')
        print(df)


i = MMonitorDBInterface("/resources/mmonitor_centrifuge.db")






