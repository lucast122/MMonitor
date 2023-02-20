import glob

import pandas as pd

"""
This method takes as input to
@param path_to_prokka_output: Path to the output of prokka that contains the tsv files that will get concatenated
@param output_path: Path to safe the final tsv file to. That tsv file can then used as input for keggcharter and has the columns with EC_number nad taxonomy
"""


def create_keggcharter_input(path_to_prokka_output, output_path):
    keggcharter_sheet = {'taxonomy': ['']}
    df = pd.DataFrame(keggcharter_sheet)
    df_list = []
    df.to_csv(output_path, sep='\t')
    for tsv in glob.glob(f"{path_to_prokka_output}/*.tsv"):
        if not "keggcharter.tsv" in tsv:
            data = pd.read_csv(tsv, sep='\t')
            tax = tsv.split('.tsv')[0]
            tax = tax.split('/')[-1]
            tax = tax.replace('_', ' ')
            tax = tax.replace('.fasta', ' ')
            print(tax)
            data["taxonomy"] = tax
            df_list.append(data)
    df = pd.concat(df_list)
    df.to_csv(output_path, sep='\t')

# create_keggcharter_input("/Users/timolucas/Desktop/kegg_test/",'/Users/timolucas/Desktop/kegg_test/test.tsv')
