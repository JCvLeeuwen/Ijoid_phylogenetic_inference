# split data by borrowability score

import pandas as pd
import sys
import os
from pathlib import Path

# normalize concept for matching
def normalize_concept(concept):
    if pd.isna(concept):
        return ""
    concept = str(concept).upper().strip()
    # remove punctuation
    concept = concept.replace('/', ' ')
    concept = concept.replace(',', ' ')
    concept = concept.replace('.', '')
    concept = concept.replace(':', '')
    concept = ' '.join(concept.split())
    return concept

# split data
def split_data(lexstat_file, scores_file, output_dir, threshold=0.8):
    print(f"reading lexstat: {lexstat_file}")
    lexstat_df = pd.read_csv(lexstat_file)
    
    print(f"reading scores: {scores_file}")
    scores_df = pd.read_csv(scores_file)
    
    # make output dir
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # check format
    if 'ConceptID' not in lexstat_df.columns or 'Concept' not in lexstat_df.columns:
        print("error: need ConceptID and Concept columns")
        sys.exit(1)
    
    required = ['ConceptID', 'Ijoid_Concept', 'BorrowedScore']
    missing = [col for col in required if col not in scores_df.columns]
    if missing:
        print(f"error: scores file missing: {', '.join(missing)}")
        sys.exit(1)
    
    print(f"\nlexstat data:")
    print(f"  rows: {len(lexstat_df)}")
    print(f"  concepts: {lexstat_df['ConceptID'].nunique()}")
    
    print(f"\nscores data:")
    print(f"  concepts: {len(scores_df)}")
    
    # map concepts to scores
    concept_to_score = {}
    
    for idx, row in scores_df.iterrows():
        concept = normalize_concept(row['Ijoid_Concept'])
        if pd.notna(row['BorrowedScore']):
            try:
                score = float(row['BorrowedScore'])
                concept_to_score[concept] = score
            except (ValueError, TypeError):
                concept_to_score[concept] = None
        else:
            concept_to_score[concept] = None
    
    print(f"  with score: {sum(1 for s in concept_to_score.values() if s is not None)}")
    print(f"  without score: {sum(1 for s in concept_to_score.values() if s is None)}")
    
    # match lexstat to scores
    id_to_score = {}
    id_to_concept = {}
    
    for cid in lexstat_df['ConceptID'].unique():
        # get concept name
        concept_name = lexstat_df[lexstat_df['ConceptID'] == cid]['Concept'].iloc[0]
        norm = normalize_concept(concept_name)
        id_to_concept[cid] = concept_name
        
        if norm in concept_to_score:
            id_to_score[cid] = concept_to_score[norm]
        else:
            # try partial match
            matched = False
            for score_concept in concept_to_score.keys():
                if norm in score_concept or score_concept in norm:
                    id_to_score[cid] = concept_to_score[score_concept]
                    matched = True
                    break
            if not matched:
                id_to_score[cid] = None
    
    # split into categories
    basic_ids = []
    borrowable_ids = []
    unmatched_ids = []
    
    for cid, score in id_to_score.items():
        if score is None:
            unmatched_ids.append(cid)
        elif score >= threshold:
            basic_ids.append(cid)
        else:
            borrowable_ids.append(cid)
    
    # make dataframes
    basic_df = lexstat_df[lexstat_df['ConceptID'].isin(basic_ids)]
    borrowable_df = lexstat_df[lexstat_df['ConceptID'].isin(borrowable_ids)]
    unmatched_df = lexstat_df[lexstat_df['ConceptID'].isin(unmatched_ids)]
    
    # reindex ids
    def reindex(df):
        if len(df) == 0:
            return df
        old_to_new = {}
        new_id = 1
        for old_id in df['ConceptID'].unique():
            old_to_new[old_id] = new_id
            new_id += 1
        df = df.copy()
        df['ConceptID'] = df['ConceptID'].map(old_to_new)
        return df
    
    basic_df = reindex(basic_df)
    borrowable_df = reindex(borrowable_df)
    unmatched_df = reindex(unmatched_df)
    
    # save files
    basic_file = output_dir / 'basic_vocabulary.csv'
    borrowable_file = output_dir / 'borrowable_vocabulary.csv'
    unmatched_file = output_dir / 'unmatched_vocabulary.csv'
    
    basic_df.to_csv(basic_file, index=False, encoding='utf-8')
    borrowable_df.to_csv(borrowable_file, index=False, encoding='utf-8')
    unmatched_df.to_csv(unmatched_file, index=False, encoding='utf-8')
    
    # print results
    print("splitting complete")
    print(f"\nthreshold: score >= {threshold} = basic")
    print(f"           score < {threshold} = borrowable")
    
    print(f"\n1. basic vocabulary")
    print(f"   file: {basic_file}")
    print(f"   concepts: {basic_df['ConceptID'].nunique()}")
    print(f"   rows: {len(basic_df)}")
    
    print(f"\n2. borrowable vocabulary")
    print(f"   file: {borrowable_file}")
    print(f"   concepts: {borrowable_df['ConceptID'].nunique()}")
    print(f"   rows: {len(borrowable_df)}")
    
    print(f"\n3. unmatched vocabulary")
    print(f"   file: {unmatched_file}")
    print(f"   concepts: {unmatched_df['ConceptID'].nunique()}")
    print(f"   rows: {len(unmatched_df)}")
    
    # summary
    total = lexstat_df['ConceptID'].nunique()
    print("summary")
    print(f"total concepts: {total}")
    print(f"  basic: {len(basic_ids)} ({len(basic_ids)/total*100:.1f}%)")
    print(f"  borrowable: {len(borrowable_ids)} ({len(borrowable_ids)/total*100:.1f}%)")
    print(f"  unmatched: {len(unmatched_ids)} ({len(unmatched_ids)/total*100:.1f}%)")
    
    return basic_df, borrowable_df, unmatched_df

# main
if len(sys.argv) < 4:
    print("usage: python partitioner.py <lexstat.csv> <scores.csv> <output_dir> [threshold]")
    print("\narguments:")
    print("  lexstat.csv - lexstat format csv")
    print("  scores.csv - borrowability scores csv")
    print("  output_dir - output directory")
    print("  threshold - optional threshold (default: 0.8)")
    sys.exit(1)

lexstat_file = sys.argv[1]
scores_file = sys.argv[2]
output_dir = sys.argv[3]
threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8

# check files exist
if not os.path.exists(lexstat_file):
    print(f"error: file not found: {lexstat_file}")
    sys.exit(1)

if not os.path.exists(scores_file):
    print(f"error: file not found: {scores_file}")
    sys.exit(1)

split_data(lexstat_file, scores_file, output_dir, threshold)