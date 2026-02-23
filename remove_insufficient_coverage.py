# filter csv file 
# remove languages and concepts with not enough data

import pandas as pd
import argparse
import sys

# count languages that have data
def count_langs(row, lang_cols):
    count = 0
    for lang in lang_cols:
        if lang in row and pd.notna(row[lang]) and str(row[lang]).strip() != '':
            count += 1
    return count

# main filter function
def filter_data(input_file, output_file, remove_langs=None, min_langs=0):
    print(f"reading {input_file}")
    df = pd.read_csv(input_file)
    
    # check if its the right format
    if 'ConceptID' not in df.columns or 'Concept' not in df.columns:
        print("error: need ConceptID and Concept columns")
        sys.exit(1)
    
    # get language columns
    lang_cols = [col for col in df.columns if col not in ['ConceptID', 'Concept']]
    
    print(f"\noriginal data:")
    print(f"  rows: {len(df)}")
    print(f"  concepts: {df['ConceptID'].nunique()}")
    print(f"  languages: {len(lang_cols)}")
    
    # remove languages
    if remove_langs:
        remove_langs = [lang.strip() for lang in remove_langs]
        langs_found = [lang for lang in remove_langs if lang in lang_cols]
        langs_missing = [lang for lang in remove_langs if lang not in lang_cols]
        
        if langs_missing:
            print(f"\nwarning: these not found: {', '.join(langs_missing)}")
        
        if langs_found:
            print(f"\nremoving {len(langs_found)} languages: {', '.join(langs_found)}")
            df = df.drop(columns=langs_found)
            # update list
            lang_cols = [col for col in df.columns if col not in ['ConceptID', 'Concept']]
            print(f"  languages left: {len(lang_cols)}")
    
    # filter by min languages
    if min_langs > 0:
        print(f"\nfiltering concepts with less than {min_langs} languages...")
        
        # check each concept ID
        # need to check all synonym rows
        id_coverage = {}
        for cid in df['ConceptID'].unique():
            rows = df[df['ConceptID'] == cid]
            # get max coverage across synonyms
            max_cov = 0
            for idx, row in rows.iterrows():
                cov = count_langs(row, lang_cols)
                max_cov = max(max_cov, cov)
            id_coverage[cid] = max_cov
        
        # keep concepts that meet threshold
        keep_ids = [cid for cid, cov in id_coverage.items() if cov >= min_langs]
        
        removed = len(id_coverage) - len(keep_ids)
        
        if removed > 0:
            print(f"  removing {removed} concepts")
            print(f"  keeping {len(keep_ids)} concepts")
            df = df[df['ConceptID'].isin(keep_ids)]
        else:
            print(f"  all concepts ok")
    
    # remove empty rows
    empty = df[lang_cols].apply(
        lambda row: all(pd.isna(val) or str(val).strip() == '' for val in row), 
        axis=1
    )
    
    if empty.sum() > 0:
        print(f"\nremoving {empty.sum()} empty rows")
        df = df[~empty]
    
    # reindex IDs
    old_to_new = {}
    new_id = 1
    for old_id in df['ConceptID'].unique():
        old_to_new[old_id] = new_id
        new_id += 1
    df['ConceptID'] = df['ConceptID'].map(old_to_new)
    
    # save
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    # stats
    print(f"\n{'='*60}")
    print("done filtering")
    print(f"{'='*60}")
    print(f"\noutput: {output_file}")
    print(f"\nfinal data:")
    print(f"  rows: {len(df)}")
    print(f"  concepts: {df['ConceptID'].nunique()}")
    print(f"  languages: {len(lang_cols)}")
    print(f"  codes: {', '.join(lang_cols[:10])}" + 
          (f", ... ({len(lang_cols)-10} more)" if len(lang_cols) > 10 else ""))
    
    # synonym info
    syn_counts = df['ConceptID'].value_counts()
    concepts_with_syn = (syn_counts > 1).sum()
    
    if concepts_with_syn > 0:
        print(f"\nsynonyms:")
        print(f"  concepts with synonyms: {concepts_with_syn}")
        print(f"  max synonyms: {syn_counts.max()}")
    
    # coverage info
    print(f"\ncoverage stats:")
    coverages = []
    for idx, row in df.iterrows():
        coverages.append(count_langs(row, lang_cols))
    
    cov_series = pd.Series(coverages)
    print(f"  min languages per row: {cov_series.min()}")
    print(f"  max languages per row: {cov_series.max()}")
    print(f"  mean: {cov_series.mean():.1f}")
    print(f"  median: {cov_series.median():.0f}")
    
    return df


# main
parser = argparse.ArgumentParser(description='filter csv by languages and coverage')

parser.add_argument('input', help='input csv file')
parser.add_argument('output', help='output csv file')
parser.add_argument('--remove-langs', help='languages to remove (comma separated)')
parser.add_argument('--min-langs', type=int, default=0, help='min languages per concept')

args = parser.parse_args()

remove_langs = args.remove_langs.split(',') if args.remove_langs else None
min_langs = args.min_langs

# run filter
filter_data(args.input, args.output, remove_langs, min_langs)