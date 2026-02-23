# convert lingpy cognate data to beast format

import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

def create_binary_matrix(input_tsv, output_prefix="ijoid_beast"):
    print("converting to beast format")
    
    # read data
    df = pd.read_csv(input_tsv, sep='\t', comment='#')
    
    # check columns
    required = ['DOCULECT', 'CONCEPT', 'COGID']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    
    # get languages
    languages = sorted(df['DOCULECT'].unique())
    print(f"found {len(languages)} languages")
    print(f"found {len(df)} cognate judgments")
    
    # track which concepts each language has data for
    lang_concepts = defaultdict(set)
    cog_matrix = defaultdict(lambda: defaultdict(int))
    cogclass_to_concept = {}  # maps each cognate class back to its concept
    
    for _, row in df.iterrows():
        lang = row['DOCULECT']
        concept = row['CONCEPT']
        cogid = row['COGID']
        cog_class = f"{concept}_{cogid}"
        cog_matrix[lang][cog_class] = 1
        lang_concepts[lang].add(concept)
        cogclass_to_concept[cog_class] = concept
    
    all_cogs = sorted(set(
        cogclass 
        for lang_cogs in cog_matrix.values() 
        for cogclass in lang_cogs.keys()
    ))
    
    print(f"found {len(all_cogs)} unique cognate classes")
    
    # build dataframe
    # 1 = cognate present, 0 = absent (but language has data for concept), ? = missing
    binary_data = []
    for lang in languages:
        row = {'Language': lang}
        for cogclass in all_cogs:
            concept = cogclass_to_concept[cogclass]
            if cogclass in cog_matrix[lang]:
                row[cogclass] = 1
            elif concept in lang_concepts[lang]:
                row[cogclass] = 0   # different cognate attested for this concept
            else:
                row[cogclass] = '?' # no data for this concept at all
        binary_data.append(row)
    
    binary_df = pd.DataFrame(binary_data)
    binary_df = binary_df.set_index('Language')
    
    # save csv
    csv_file = f"{output_prefix}_cognates_binary.csv"
    binary_df.to_csv(csv_file)
    print(f"saved binary matrix: {csv_file}")
    
    # save nexus
    nexus_file = f"{output_prefix}_cognates_binary.nex"
    create_nexus(binary_df, nexus_file, languages, all_cogs)
    print(f"saved nexus: {nexus_file}")
    
    return binary_df

def create_nexus(binary_df, output_file, languages, cog_classes):
    ntax = len(languages)
    nchar = len(cog_classes)
    
    with open(output_file, 'w') as f:
        f.write("#NEXUS\n\n")
        f.write("BEGIN DATA;\n")
        f.write(f"  DIMENSIONS NTAX={ntax} NCHAR={nchar};\n")
        f.write("  FORMAT DATATYPE=STANDARD SYMBOLS=\"01\" GAP=- MISSING=?;\n")
        f.write("  MATRIX\n")
        
        for lang in languages:
            binary_str = ''.join(str(int(binary_df.loc[lang, cogclass])) 
                                for cogclass in cog_classes)
            clean_lang = lang.replace(' ', '_').replace('-', '_')
            f.write(f"    {clean_lang.ljust(15)} {binary_str}\n")
        
        f.write("  ;\n")
        f.write("END;\n\n")
        f.write("BEGIN ASSUMPTIONS;\n")
        f.write("  OPTIONS DEFTYPE=STANDARD;\n")
        f.write("  CHARSET all = 1-{};\n".format(nchar))
        f.write("END;\n")


# main
import sys

if len(sys.argv) < 2:
    sys.exit(1)

input_file = sys.argv[1]

if not Path(input_file).exists():
    print(f"error: file not found: {input_file}")
    sys.exit(1)

print("converting lingpy to beast")

binary_df = create_binary_matrix(input_file)

print("conversion complete")