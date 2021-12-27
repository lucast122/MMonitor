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

    def get_unique_samples(self) -> List[str]:
        q = "SELECT DISTINCT sample_id FROM mmonitor"
        return [t[0] for t in self.query_to_list(q)]

    def create_db(self, db_name):
        con = sqlite3.connect(db_name)
        cursor = con.cursor()
        # delete_command = f"""DROP TABLE IF EXISTS mmonitor"""
        # cursor.execute(delete_command)

        create_command = f"""CREATE TABLE IF NOT EXISTS mmonitor (read_id INTEGER PRIMARY KEY,
            taxonomy TEXT,
            abundance INTEGER,
            sample_id INTEGER,
            project_id INTEGER)"""
        cursor.execute(create_command)
        con.commit()
        con.close()
        self._db_path = db_name

    def update_table_with_kraken_out(self, kraken_out_path: str, tax_rank: str, sample_name: str,
                                     project_name: str):
        con = sqlite3.connect(self._db_path)
        cursor = con.cursor()

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
        for index, row in df.iterrows():
            if row['Count'] > 200:
                check_name_exists_in_sample = f"SELECT EXISTS(SELECT 1 FROM mmonitor WHERE taxonomy='{row['Name']}' AND sample_id='{sample_name}');"
                cursor.execute(check_name_exists_in_sample)
                name_exists = cursor.fetchall()[0][0]
                # if a sample already has a taxon name (e.g. when computation is performed on multiple files for the same sample while sequencing) then add the abundance to the value in the database
                if name_exists == 0:
                    insert_query = f"""INSERT INTO mmonitor
                        (taxonomy, abundance, sample_id, project_id) 
                        VALUES 
                        ('{row['Name']}', {row['Count']}, '{sample_name}', '{project_name}')"""
                    cursor.execute(insert_query)
                # if taxon is new to the data base simply insert it into the table
                elif name_exists == 1:
                    update_query = f"UPDATE mmonitor SET abundance = abundance + {row['Count']} WHERE taxonomy = '{row['Name']}' AND sample_id='{sample_name}'"
                    cursor.execute(update_query)

        con.commit()
        con.close()
