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
    parts = date_str.split('.')

    # Check if the date is in the format DD.MM.YYYY or DD.MM.YY
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        day, month, year = parts

        # Convert 2-digit year to 4-digit year assuming it's in the 2000s
        if len(year) == 2:
            year = '20' + year

        return f"{year}-{month}-{day}"
    else:
        # Return the original date if the format is not recognized
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
        django_url = f"http://{self._db_config['host']}:8021/users/get_user_id/"
        response = pyrequests.post(django_url, data={'username': username, 'password': password})
        if response.status_code == 200:
            return response.json()['user_id']
        else:
            return None

    def get_unique_sample_ids(self):
        django_url = f"http://{self._db_config['host']}:8021/users/get_unique_sample_ids/"
        response = pyrequests.post(django_url,
                                   data={'username': self._db_config['user'], 'password': self._db_config['password']})
        if response.status_code == 200:
            return response.json().get('sample_ids', [])
        else:
            return None

    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.conn)

    def query_to_list(self, query: str) -> List[Tuple[Any]]:
        self.cursor.execute(query)
        return self.cursor.fetchall()


    def update_django_with_emu_out(self, emu_out_path: str, tax_rank: str, sample_name: str, project_name: str,
                                   sample_date: str, subproject_name: str, overwrite: bool):
        user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])

        if user_id is None:
            print("Invalid user credentials")
            return

        sample_ids = self.get_unique_sample_ids()
        if sample_name in sample_ids and not overwrite:
            print(
                f"Skipping sample {sample_name} as it is already in the database. Select overwrite to reprocess a sample.")
            return

        df = pd.read_csv(
            f"{emu_out_path}/{sample_name}_rel-abundance-threshold.tsv",
            sep='\t',
            header=None,
            usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13],
            names=['Taxid', 'Abundance', 'Species', 'Genus', 'Family', 'Order', 'Class', 'Phylum', 'Superkingdom',
                   'Clade', 'Subspecies', "count"]
        )
        df.fillna("Not Available", inplace=True)
        df.sort_values('Abundance', ascending=False, inplace=True)
        df = df.iloc[1:]  # Skipping the first row, assuming it's headers or unwanted data
        df['Sample'] = sample_name
        df['Sample'] = sample_name
        sample_date = convert_date_format(sample_date)  # Convert date format if necessary
        df['Sample_date'] = sample_date

        # Prepare a list of records
        records = []
        for index, row in df.iterrows():
            # print(row)
            records.append({
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
                "count": row["count"],
                "sample_id": sample_name,
                "project_id": project_name,
                "user_id": user_id,
                "subproject": subproject_name,
                "date": sample_date
            })

        # Send all records in one request
        try:
            response = pyrequests.post(
                f"http://{self._db_config['host']}:8021/users/overwrite_nanopore_record/",
                json=records,  # Send the list of records
                auth=HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
            )
            if response.status_code != 201:
                print(f"Failed to add records: {response.content}")
            else:
                print(f"Records added successfully.")
        except Exception as e:
            print(e)

    def send_nanopore_record_centrifuge(self, kraken_out_path: str, sample_name: str, project_id: str, subproject_id: str,
                                        date: str, overwrite: bool):

        df = pd.read_csv(
            kraken_out_path,
            sep='\t',
            header=None,
            usecols=[0,1, 3, 5],
            names=["abundance",'Count', 'Rank', 'Name']
        )

        df = df.sort_values('Count', ascending=False)

        df['Sample'] = sample_name
        df['Sample_date'] = date
        df = df[df['Rank'] == "S"]
        df = df.drop(columns='Rank')

        user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])

        if user_id is None:
            print("Invalid user credentials")
            return
        print(f"User id clientside: {user_id}")

        sample_ids = self.get_unique_sample_ids()
        print(f"Found samples: {sample_ids}")
        # do not add sample if overwrite is False and the sample_name is already present in the django DB
        # this makes sure that a sample is only reprocessed if the overwrite bool is set e.g. with the cmd line or in the GUI
        if sample_name in sample_ids and not overwrite:
            print(
                f"Skipping sample {sample_name} as it is already in the database. Select overwrite to reprocess a sample.")
            return

        records = []
        for index, row in df.iterrows():
            record_data = {
                "sample_id": sample_name,
                "project_id": project_id,
                "subproject_id": subproject_id,
                "date": date,
                "taxonomy": row["Name"].strip(),  # Assuming species for now; might need adjustments based on taxonomic rank
                "abundance": row["abundance"]/100, #divide abundance by 100 to get same format used by emu
                "count": row["Count"],
                "project_id": project_id,
                "subproject": subproject_id,
                "tax_genus": "empty",
                "tax_family": "empty",
                "tax_order": "empty",
                "tax_class": "empty",
                "tax_phylum": "empty",
                "tax_superkingdom": "empty",
                "tax_clade": "empty",
                "tax_subspecies": "empty"

            }
            # print(record_data)
            records.append(record_data)

        # print(f"Sending record: {records}")
        try:
            response = pyrequests.post(
                f"http://{self._db_config['host']}:8021/users/overwrite_nanopore_record/",
                json=records,  # Send the list of records
                auth=HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
            )
            if response.status_code != 201:
                print(f"Failed to add records: {response.content}")
            else:
                print(f"Records added successfully.")
        except Exception as e:
            print(e)

    def send_sequencing_statistics(self, record_data):
        import requests as pyrequests
        from requests.auth import HTTPBasicAuth

        # Fetch the user_id using the provided method
        user_id = self.get_user_id(self._db_config['user'], self._db_config['password'])
        record_data["user_id"] = user_id

        # print(f"Sending record: {record_data}")
        try:
            response = pyrequests.post(
                f"http://{self._db_config['host']}:8021/users/add_sequencing_statistics/",
                json=record_data,
                auth=HTTPBasicAuth(self._db_config['user'], self._db_config['password'])
            )
            if response.status_code != 200:
                print(f"Failed to add record: {response.content}")

        except Exception as e:
            print(e)
