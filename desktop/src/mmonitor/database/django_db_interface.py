import json
from json import loads
from typing import List, Tuple, Any

import pandas as pd
import requests as pyrequests
from requests.auth import HTTPBasicAuth


def _parse_dict(x):
    return pd.Series(loads(x))


def _explode_metadata(df):
    return pd.concat([df, df['data'].apply(_parse_dict)], axis=1).drop(columns='data')


"""
This class gets the path to a db_config file. The db_config is has the host ip 'host', the username 'user' and the password 'password'
 
"""


def convert_date_format(date_str):
    # Check if the date is in the format DD.MM.YYYY
    if len(date_str) == 10 and date_str[2] == '.' and date_str[5] == '.':
        return '-'.join(reversed(date_str.split('.')))
    else:
        # Return the original date if it's not in DD.MM.YYYY format
        return date_str


class DjangoDBInterface:
    def __init__(self, db_config: str):
        try:
            with open(db_config, 'r') as file:
                self._db_config = json.load(file)
        except FileNotFoundError as e:
            print("DB config not found")
            print(e)
        self._connection = None

    def get_user_id(self, username: str, password: str):
        django_url = f"http://{self._db_config['host']}:8020/users/get_user_id/"
        response = pyrequests.post(django_url, data={'username': username, 'password': password})
        if response.status_code == 200:
            return response.json()['user_id']
        else:
            return None


    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.conn)

    def query_to_list(self, query: str) -> List[Tuple[Any]]:
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def add_kaiju_output_to_db(self, sample_name):
        output_dir = os.path.join("kaiju_output", sample_name)

        for output_file in os.listdir(output_dir):
            with open(os.path.join(output_dir, output_file), 'r') as f:
                data = f.readlines()  # Parse the Kaiju output as needed

                # Now, add the parsed data to your DjangoDB.
                # Assuming the structure of the NanoporeRecords, we'll create records and save them
                for record_data in data:
                    record = NanoporeRecords(sample_name=sample_name,
                                             data=record_data)  # Assuming a structure for NanoporeRecords
                    record.save()

    # def get_abundance_meta_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
    #     q = "SELECT nanopore.sample_id, mmonitor.abundance, metadata.* " \
    #         "FROM nanopore " \
    #         "INNER JOIN metadata " \
    #         "WHERE nanopore.sample_id = metadata.sample_id " \
    #         f"AND nanopore.taxonomy = '{taxonomy}' " \
    #         "ORDER BY nanopore.sample_id"
    #     return _explode_metadata(self.query_to_dataframe(q))

    # def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
    #     q = f"SELECT sample_id, abundance FROM nanopore WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
    #     return self.query_to_dataframe(q)

    # def get_all_meta(self) -> pd.DataFrame:
    #     q = "SELECT * FROM metadata ORDER BY sample_id"
    #     return _explode_metadata(self.query_to_dataframe(q))

    # def get_unique_taxonomies(self) -> List[str]:
    #     q = "SELECT DISTINCT taxonomy FROM nanopore"
    #     return [t[0] for t in self.query_to_list(q)]

    # def get_unique_samples(self) -> List[str]:
    #     q = "SELECT DISTINCT sample_id FROM nanopore"
    #     return [t[0] for t in self.query_to_list(q)]

    # def create_db(self):
    #     user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])
    #     if user_id is None:
    #         print("Invalid user credentials")
    #         return
    #
    #
    #     # drop_table_query_metadata = "DROP TABLE metadata;"
    #     # drop_table_query_mmonitor = "DROP TABLE mmonitor;"
    #     # self._cursor.execute(drop_table_query_mmonitor)
    #     # self._cursor.execute(drop_table_query_metadata)
    #     # self._connection.commit()
    #     create_command = f"""
    #     CREATE TABLE IF NOT EXISTS nanopore (
    #         read_id INTEGER PRIMARY KEY,
    #         taxonomy TEXT,
    #         abundance FLOAT,
    #         sample_id TEXT,
    #         user_id INT,
    #         project_id TEXT,
    #         subproject_id TEXT,
    #         sample_date TEXT
    #     );"""  # maker read_id auto increment (1,2,3,4,5...)
    #
    #     # increment_command = """ALTER TABLE nanopore MODIFY COLUMN read_id INT AUTO_INCREMENT;"""
    #
    #     # self._cursor.execute(create_command)
    #     # self._cursor.execute(increment_command)
    #     create_command = """CREATE TABLE IF NOT EXISTS metadata (
    #                 `meta_id` INTEGER PRIMARY KEY,
    #                 `sample_id` TEXT,
    #                 `user_id` INT,
    #                 `data` TEXT
    #             )"""
    #
    #     self._cursor.execute(create_command)
    #     self._connection.commit()

    # def update_table_with_emu_out(self, emu_out_path: str, tax_rank: str, sample_name: str,
    #                               project_name: str, sample_date):
    #     user_id = self.get_user_id()
    #     if user_id is None:
    #         print("Invalid user credentials")
    #         return
    #
    #     df = pd.read_csv(
    #         f"{emu_out_path}/{sample_name}_rel-abundance.tsv",
    #         sep='\t',
    #         header=None,
    #         usecols=[0, 1, 2, 3],
    #         names=['Taxid', 'Abundance', 'Species', 'Genus']
    #     )
    #     df = df.sort_values('Abundance', ascending=False)
    #     df = df.iloc[1:]
    #     df['Sample'] = sample_name
    #     df['Sample_date'] = sample_date
    #     for index, row in df.iterrows():
    #         insert_query = f"""INSERT INTO nanopore
    #         (taxonomy, abundance, sample_id, project_id, user_id)
    #         VALUES ('{row['Species']}', {row['Abundance']}, '{sample_name}', '{project_name}', '{user_id}')"""
    #         self._cursor.execute(insert_query)
    #     self._connection.commit()

    def update_django_with_emu_out(self, emu_out_path: str, tax_rank: str, sample_name: str,
                                   project_name: str, sample_date: str, subproject_name: str):
        user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])

        if user_id is None:
            print("Invalid user credentials")
            return
        print(f"User id clientside: {user_id}")

        df = pd.read_csv(
            f"{emu_out_path}/{sample_name}_rel-abundance.tsv",
            sep='\t',
            header=None,
            # usecols=[0, 1, 2, 3],
            usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 19],
            names=['Taxid', 'Abundance', 'Species', 'Genus', 'Family', 'Order', 'Class', 'Phylum', 'Superkingdom',
                   'Clade', 'Subspecies']
        )
        df = df.fillna("Not Available")

        df = df.sort_values('Abundance', ascending=False)
        df = df.iloc[1:]
        df['Sample'] = sample_name
        # check if sample is in wrong format and convert using function convert_date_format()
        sample_date = convert_date_format(sample_date)

        df['Sample_date'] = sample_date


        for index, row in df.iterrows():
            record_data = {
                "taxonomy": row['Species'],
                "tax_genus": row['Genus'],
                "tax_family": row['Family'],
                "tax_order": row['Order'],
                "tax_class": row['Class'],
                "tax_phylum": row['Phylum'],
                "tax_superkingdom": row['Superkingdom'],
                "tax_clade": row['Clade'],
                "tax_subspecies": row['Subspecies'],

                "abundance": row['Abundance'],

                "sample_id": sample_name,
                "project_id": project_name,
                "user_id": user_id,
                "subproject": subproject_name,
                "date": sample_date


            }
            print(f"Sending record: {record_data}")
            try:
                response = pyrequests.post(
                    f"http://{self._db_config['host']}:8020/users/add_nanopore_record/",
                    json=record_data,
                    auth=HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
                )
                if response.status_code != 200:
                    print(f"Failed to add record: {response.content}")

            except Exception as e:
                print(e)

    def send_nanopore_record_centrifuge(self, kraken_out: dict, sample_name: str, project_id: str, subproject_id: str,
                                        date: str):
        import requests as pyrequests
        from requests.auth import HTTPBasicAuth

        records = []
        for hit in kraken_out:
            record_data = {
                "sample_name": sample_name,
                "project_id": project_id,
                "subproject_id": subproject_id,
                "date": date,
                "tax_id": hit["tax_id"],
                "species": hit["taxonomy"]  # Assuming species for now; might need adjustments based on taxonomic rank
            }
            records.append(record_data)

        for record_data in records:
            print(f"Sending record: {record_data}")
            try:
                auth = HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
                response = pyrequests.post(
                    f"http://{self._db_config['host']}:8020/users/add_nanopore_record/",
                    json=record_data,
                    auth=auth
                )
                if response.status_code != 200:
                    print(f"Failed to add record: {response.content}")
            except Exception as e:
                print(e)

    def send_sequencing_statistics(self, record_data):
        import requests as pyrequests
        from requests.auth import HTTPBasicAuth

        # Fetch the user_id using the provided method
        user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])
        record_data["user_id"] = user_id

        print(f"Sending record: {record_data}")
        try:
            response = pyrequests.post(
                f"http://{self._db_config['host']}:8020/users/add_sequencing_statistics/",
                json=record_data,
                auth=HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
            )
            if response.status_code != 200:
                print(f"Failed to add record: {response.content}")

        except Exception as e:
            print(e)

    # method that converts dates from format DD.MM.YYYY to YYYY-MM-DD only if format is DD.MM.YYYY

    # def update_table_with_kraken_out(self, kraken_out_path: str, tax_rank: str, sample_name: str,
    #                                  project_name: str, sample_date):
    #     user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])
    #     if user_id is None:
    #         print("Invalid user credentials")
    #         return
    #
    #     df = pd.read_csv(
    #         kraken_out_path,
    #         sep='\t',
    #         header=None,
    #         usecols=[1, 3, 5],
    #         names=['Count', 'Rank', 'Name']
    #     )
    #     df = df.sort_values('Count', ascending=False)
    #     df['Sample'] = sample_name
    #     df['Sample_date'] = sample_date
    #     df = df[df['Rank'] == tax_rank]
    #     df = df.drop(columns='Rank')
    #     for index, row in df.iterrows():
    #         if row['Count'] > 100:
    #             check_name_exists_in_sample = f"SELECT EXISTS(SELECT 1 FROM nanopore WHERE taxonomy='{row['Name']}' AND sample_id='{sample_name}');"
    #             self.cursor.execute(check_name_exists_in_sample)
    #             name_exists = self._cursor.fetchall()[0][0]
    #             if name_exists == 0:
    #                 insert_query = f"""INSERT INTO nanopore
    #                     (taxonomy, abundance, sample_id, project_id, sample_date)
    #                     VALUES
    #                     ('{row['Name']}', {row['Count']}, '{sample_name}', '{project_name}','{sample_date}')"""
    #                 self._cursor.execute(insert_query)
    #             elif name_exists == 1:
    #                 update_query = f"UPDATE nanopore SET abundance = abundance + {row['Count']} WHERE taxonomy = '{row['Name']}' AND sample_id='{sample_name}'"
    #                 self._cursor.execute(update_query)
    #     self._connection.commit()

    # def append_metadata_from_csv(self, csv_file: str):
    #     df = pd.read_csv(csv_file)
    #     meta_cols = [col for col in df.columns if col != 'sample_id']
    #     df['data'] = df.apply(lambda x: dumps({col: x[col] for col in meta_cols}), axis=1)
    #     df = df.drop(columns=meta_cols)
    #     engine = create_engine(
    #         'mysql+mysqlconnector://{user}:{password}@{host}:3306/{database}'.format(**self._db_config))
    #     df.to_sql('metadata', engine, if_exists='replace', index=False)

    # def close(self):
    #     self._cursor.close()
    #     self._connection.close()
