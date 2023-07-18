import json
from json import loads, dumps
from typing import List, Tuple, Any

import mysql.connector
import pandas as pd
from sqlalchemy import create_engine


def _parse_dict(x):
    return pd.Series(loads(x))


def _explode_metadata(df):
    return pd.concat([df, df['data'].apply(_parse_dict)], axis=1).drop(columns='data')


class MMonitorDBInterfaceMySQL:
    def __init__(self, db_config: str):
        with open(db_config, 'r') as file:
            self._db_config = json.load(file)
        self._db_path = self._db_config['db_name']
        self._connection = None

    def _connect(self):
        if self._connection is None or not self._connection.is_connected():
            self._connection = mysql.connector.connect(
                host=self._db_config['host'],
                user=self._db_config['user'],
                password=self._db_config['password'],
                database=self._db_config['db_name']
            )

    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.conn)

    def query_to_list(self, query: str) -> List[Tuple[Any]]:
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_abundance_meta_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        q = "SELECT mmonitor.sample_id, mmonitor.abundance, metadata.* " \
            "FROM mmonitor " \
            "INNER JOIN metadata " \
            "WHERE mmonitor.sample_id = metadata.sample_id " \
            f"AND mmonitor.taxonomy = '{taxonomy}' " \
            "ORDER BY mmonitor.sample_id"
        return _explode_metadata(self.query_to_dataframe(q))

    def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        q = f"SELECT sample_id, abundance FROM mmonitor WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
        return self.query_to_dataframe(q)

    def get_all_meta(self) -> pd.DataFrame:
        q = "SELECT * FROM metadata ORDER BY sample_id"
        return _explode_metadata(self.query_to_dataframe(q))

    def get_unique_taxonomies(self) -> List[str]:
        q = "SELECT DISTINCT taxonomy FROM mmonitor"
        return [t[0] for t in self.query_to_list(q)]

    def get_unique_samples(self) -> List[str]:
        q = "SELECT DISTINCT sample_id FROM mmonitor"
        return [t[0] for t in self.query_to_list(q)]

    def create_db(self, db_name):
        create_command = f"""CREATE TABLE IF NOT EXISTS mmonitor (
            read_id INTEGER PRIMARY KEY,
            taxonomy TEXT,
            abundance INTEGER,
            sample_id INTEGER,
            project_id INTEGER,
            sample_date TEXT
        )"""
        self.cursor.execute(create_command)
        create_command = f"""CREATE TABLE IF NOT EXISTS metadata (
            "sample_id"	INTEGER PRIMARY KEY,
            "data" TEXT
        )"""
        self.cursor.execute(create_command)
        self.conn.commit()

    def update_table_with_emu_out(self, emu_out_path: str, tax_rank: str, sample_name: str,
                                  project_name: str, sample_date):
        df = pd.read_csv(
            f"{emu_out_path}/{sample_name}_rel-abundance.tsv",
            sep='\t',
            header=None,
            usecols=[0, 1, 2, 3],
            names=['Taxid', 'Abundance', 'Species', 'Genus']
        )
        df = df.sort_values('Abundance', ascending=False)
        df = df.iloc[1:]
        df['Sample'] = sample_name
        df['Sample_date'] = sample_date
        for index, row in df.iterrows():
            insert_query = f"""INSERT INTO mmonitor
            (taxonomy, abundance, sample_id, project_id) 
            VALUES ('{row['Species']}', {row['Abundance']}, '{sample_name}', '{project_name}')"""
            self.cursor.execute(insert_query)
        self.conn.commit()

    def update_table_with_kraken_out(self, kraken_out_path: str, tax_rank: str, sample_name: str,
                                     project_name: str, sample_date):
        df = pd.read_csv(
            kraken_out_path,
            sep='\t',
            header=None,
            usecols=[1, 3, 5],
            names=['Count', 'Rank', 'Name']
        )
        df = df.sort_values('Count', ascending=False)
        df['Sample'] = sample_name
        df['Sample_date'] = sample_date
        df = df[df['Rank'] == tax_rank]
        df = df.drop(columns='Rank')
        for index, row in df.iterrows():
            if row['Count'] > 100:
                check_name_exists_in_sample = f"SELECT EXISTS(SELECT 1 FROM mmonitor WHERE taxonomy='{row['Name']}' AND sample_id='{sample_name}');"
                self.cursor.execute(check_name_exists_in_sample)
                name_exists = self.cursor.fetchall()[0][0]
                if name_exists == 0:
                    insert_query = f"""INSERT INTO mmonitor
                        (taxonomy, abundance, sample_id, project_id, sample_date) 
                        VALUES 
                        ('{row['Name']}', {row['Count']}, '{sample_name}', '{project_name}','{sample_date}')"""
                    self.cursor.execute(insert_query)
                elif name_exists == 1:
                    update_query = f"UPDATE mmonitor SET abundance = abundance + {row['Count']} WHERE taxonomy = '{row['Name']}' AND sample_id='{sample_name}'"
                    self.cursor.execute(update_query)
        self.conn.commit()

    def append_metadata_from_csv(self, csv_file: str):
        df = pd.read_csv(csv_file)
        meta_cols = [col for col in df.columns if col != 'sample_id']
        df['data'] = df.apply(lambda x: dumps({col: x[col] for col in meta_cols}), axis=1)
        df = df.drop(columns=meta_cols)
        engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}'.format(**db_config))
        df.to_sql('metadata', engine, if_exists='append', index=False)

    def close(self):
        self.cursor.close()
        self.conn.close()
