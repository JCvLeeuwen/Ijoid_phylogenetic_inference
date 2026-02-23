# match concepts with wold borrowing scores

import pandas as pd
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

# clean up concept for matching
def normalize_concept(concept):
    if not concept or pd.isna(concept):
        return ""
    concept = str(concept).lower().strip()
    # remove stuff in parentheses
    concept = re.sub(r'\([^)]*\)', '', concept)
    # remove articles
    concept = re.sub(r'^(the|a|an)\s+', '', concept)
    # remove to
    concept = re.sub(r'^to\s+', '', concept)
    # remove punctuation
    concept = re.sub(r'[.,;:!?\'"()-]', ' ', concept)
    # fix whitespace
    concept = ' '.join(concept.split())
    return concept.strip()

# make different versions of concept
def get_variants(concept):
    variants = set()
    # original
    variants.add(concept.lower().strip())
    # normalized
    norm = normalize_concept(concept)
    variants.add(norm)
    # with the
    variants.add(f"the {norm}")
    # with to
    variants.add(f"to {norm}")
    # singular/plural
    if norm.endswith('s') and len(norm) > 3:
        variants.add(norm[:-1])
        variants.add(f"the {norm[:-1]}")
    elif not norm.endswith('s'):
        variants.add(f"{norm}s")
        variants.add(f"the {norm}s")
    # handle or
    if ' or ' in norm:
        parts = norm.split(' or ')
        for part in parts:
            part = part.strip()
            variants.add(part)
            variants.add(f"the {part}")
    # handle slashes
    if '/' in concept:
        parts = concept.split('/')
        for part in parts:
            part = normalize_concept(part)
            variants.add(part)
            variants.add(f"the {part}")
    return list(variants)

# check how similar two strings are
def similarity(str1, str2):
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

# find match in wold data
def find_match(ijoid_concept, wold_df, threshold=0.8):
    variants = get_variants(ijoid_concept)
    best_match = None
    best_score = 0
    best_method = None
    
    # try exact match first
    for variant in variants:
        matches = wold_df[wold_df['Name'].str.lower().str.strip() == variant]
        if not matches.empty:
            match = matches.iloc[0]
            return {
                'wold_name': match['Name'],
                'wold_id': match['ID'],
                'borrowed_score': match['BorrowedScore'],
                'match_score': 1.0,
                'match_method': 'exact',
                'matched_variant': variant
            }
    
    # try fuzzy matching
    for variant in variants:
        for idx, row in wold_df.iterrows():
            wold_name = str(row['Name']).lower().strip()
            score = similarity(variant, wold_name)
            if score > best_score:
                best_score = score
                best_match = row
                best_method = 'fuzzy'
    
    # return if good enough
    if best_score >= threshold and best_match is not None:
        return {
            'wold_name': best_match['Name'],
            'wold_id': best_match['ID'],
            'borrowed_score': best_match['BorrowedScore'],
            'match_score': best_score,
            'match_method': best_method,
            'matched_variant': 'fuzzy'
        }
    return None

# main matching function
def match_concepts(ijoid_csv, wold_csv, output_csv, threshold=0.8, manual_review=False):
    print("matching concepts with wold scores")
    print(f"ijoid file: {ijoid_csv}")
    print(f"wold file: {wold_csv}")
    print(f"output: {output_csv}")
    print(f"threshold: {threshold}")
    
    # load files
    print("loading data")
    ijoid_df = pd.read_csv(ijoid_csv)
    wold_df = pd.read_csv(wold_csv)
    print(f"loaded {len(ijoid_df)} ijoid entries")
    print(f"loaded {len(wold_df)} wold entries\n")
    
    # get concepts
    if 'Concept' not in ijoid_df.columns:
        print("error: no Concept column in ijoid csv")
        return
    
    concepts = ijoid_df['Concept'].dropna().unique()
    print(f"found {len(concepts)} unique concepts\n")
    
    # match each concept
    print("matching")

    results = []
    matched = 0
    unmatched = 0
    exact = 0
    fuzzy = 0
    
    for concept in concepts:
        # get concept id
        concept_id = None
        if 'ConceptID' in ijoid_df.columns:
            rows = ijoid_df[ijoid_df['Concept'] == concept]
            if not rows.empty:
                concept_id = rows.iloc[0]['ConceptID']
        
        # find match
        match = find_match(concept, wold_df, threshold)
        
        if match:
            matched += 1
            if match['match_method'] == 'exact':
                exact += 1
            else:
                fuzzy += 1
            
            result = {
                'ConceptID': concept_id,
                'Ijoid_Concept': concept,
                'WOLD_Name': match['wold_name'],
                'WOLD_ID': match['wold_id'],
                'BorrowedScore': match['borrowed_score'],
                'MatchScore': match['match_score'],
                'MatchMethod': match['match_method']
            }
            print(f"matched '{concept}' -> '{match['wold_name']}' "
                  f"(score: {match['borrowed_score']:.3f})")
        else:
            unmatched += 1
            result = {
                'ConceptID': concept_id,
                'Ijoid_Concept': concept,
                'WOLD_Name': None,
                'WOLD_ID': None,
                'BorrowedScore': None,
                'MatchScore': None,
                'MatchMethod': 'no_match'
            }
            print(f"no match for '{concept}'")
        results.append(result)
    
    # make dataframe
    results_df = pd.DataFrame(results)
    
    # sort by id if available
    if 'ConceptID' in results_df.columns and results_df['ConceptID'].notna().any():
        results_df = results_df.sort_values('ConceptID')
    
    # save
    results_df.to_csv(output_csv, index=False)
    
    # save separate files if requested
    if manual_review:
        matched_df = results_df[results_df['BorrowedScore'].notna()]
        unmatched_df = results_df[results_df['BorrowedScore'].isna()]
        base_name = Path(output_csv).stem
        base_dir = Path(output_csv).parent
        matched_file = base_dir / f"{base_name}_matched.csv"
        unmatched_file = base_dir / f"{base_name}_unmatched.csv"
        matched_df.to_csv(matched_file, index=False)
        unmatched_df.to_csv(unmatched_file, index=False)
        print(f"\nmatched saved to: {matched_file}")
        print(f"unmatched saved to: {unmatched_file}")
    
    # print summary
  
    print("summary")
    print(f"total concepts: {len(concepts)}")
    print(f"matched: {matched} ({matched/len(concepts)*100:.1f}%)")
    print(f"  exact: {exact}")
    print(f"  fuzzy: {fuzzy}")
    print(f"unmatched: {unmatched} ({unmatched/len(concepts)*100:.1f}%)")
    print(f"\noutput: {output_csv}")



# main
import argparse

parser = argparse.ArgumentParser(description='match ijoid with wold scores')
parser.add_argument('ijoid_csv', help='ijoid wordlist csv')
parser.add_argument('wold_csv', help='wold dataset csv')
parser.add_argument('-o', '--output', default='ijoid_wold_matched.csv', help='output file')
parser.add_argument('-t', '--threshold', type=float, default=0.8, help='matching threshold')
parser.add_argument('--manual-review', action='store_true', help='create separate matched/unmatched files')

args = parser.parse_args()

# check files exist
for path in [args.ijoid_csv, args.wold_csv]:
    if not Path(path).exists():
        print(f"error: file not found: {path}")
        sys.exit(1)

try:
    # do matching
    match_concepts(args.ijoid_csv, args.wold_csv, args.output, 
                   threshold=args.threshold, manual_review=args.manual_review)
    

except Exception as e:
    print(f"\nerror: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)