# find unstable cognate sets

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from lingpy import Wordlist
import sys

# calculate edit distance
def edit_distance(s1, s2):
    if s1 == s2:
        return 0.0
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 1.0
    # dp table
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n] / max(m, n)

# analyze cognate sets
def analyze_sets(lexstat_file, output_file=None, size_threshold=8, diversity_threshold=0.6):
    print("analyzing cognate sets")
    
    print(f"\nloading: {lexstat_file}")
    wl = Wordlist(lexstat_file)
    
    # organize by cognate sets
    cog_sets = defaultdict(list)
    for idx in wl:
        cogid = wl[idx, 'cogid']
        cog_sets[cogid].append(idx)
    
    print(f"found {len(cog_sets):,} cognate sets")
    
    # analyze
    print(f"\nanalyzing")
    results = []
    unstable = 0
    
    for cogid, members in cog_sets.items():
        # get forms
        forms = [wl[idx, 'ipa'] for idx in members]
        concepts = [wl[idx, 'concept'] for idx in members]
        doculects = [wl[idx, 'doculect'] for idx in members]
        
        # stats
        size = len(members)
        n_langs = len(set(doculects))
        n_concepts = len(set(concepts))
        
        # diversity
        if size > 1:
            dists = []
            for i in range(len(forms)):
                for j in range(i+1, len(forms)):
                    dist = edit_distance(forms[i], forms[j])
                    dists.append(dist)
            avg_div = np.mean(dists)
            max_div = np.max(dists)
        else:
            avg_div = 0.0
            max_div = 0.0
        
        # check if unstable
        is_large = size > size_threshold
        is_diverse = avg_div > diversity_threshold
        is_multi = n_concepts > 1
        is_unstable = is_large or is_diverse or is_multi
        
        if is_unstable:
            unstable += 1
        
        # flags
        flags = []
        if is_large:
            flags.append(f"large({size})")
        if is_diverse:
            flags.append(f"diverse({avg_div:.2f})")
        if is_multi:
            flags.append(f"multi-concept({n_concepts})")
        
        results.append({
            'CognateID': cogid,
            'Size': size,
            'Languages': n_langs,
            'Concepts': n_concepts,
            'Avg_Diversity': round(avg_div, 3),
            'Max_Diversity': round(max_div, 3),
            'Is_Unstable': is_unstable,
            'Flags': '; '.join(flags) if flags else ''
        })
    
    # make dataframe
    df = pd.DataFrame(results)
    df = df.sort_values('Avg_Diversity', ascending=False)
    
    # summary
    print(f"\nsummary:")
    print(f"  total sets: {len(cog_sets):,}")
    print(f"  unstable: {unstable:,} ({unstable/len(cog_sets)*100:.1f}%)")
    print(f"  large (>{size_threshold}): {sum(df['Size'] > size_threshold):,}")
    print(f"  diverse (>{diversity_threshold}): {sum(df['Avg_Diversity'] > diversity_threshold):,}")
    print(f"  multi-concept: {sum(df['Concepts'] > 1):,}")
    
    # save
    if output_file:
        df.to_csv(output_file, index=False)
        print(f"\nsaved to: {output_file}")
    
    return df

# extract unstable ids
def extract_ids(analysis_df, output_file='unstable_cogids.txt'):
    unstable_ids = analysis_df[analysis_df['Is_Unstable']]['CognateID'].tolist()
    with open(output_file, 'w') as f:
        for cogid in unstable_ids:
            f.write(f"{cogid}\n")
    print(f"saved unstable ids to: {output_file}")
    return unstable_ids

# main
import argparse

parser = argparse.ArgumentParser(description='identify unstable cognate sets')

parser.add_argument('input', help='lexstat output tsv')
parser.add_argument('-o', '--output', default='cognate_set_analysis.csv', help='output csv')
parser.add_argument('--size-threshold', type=int, default=8, help='size threshold')
parser.add_argument('--diversity-threshold', type=float, default=0.6, help='diversity threshold')
parser.add_argument('--extract-ids', action='store_true', help='save unstable ids')

args = parser.parse_args()

try:
    df = analyze_sets(
        lexstat_file=args.input,
        output_file=args.output,
        size_threshold=args.size_threshold,
        diversity_threshold=args.diversity_threshold
    )
    
    if args.extract_ids:
        extract_ids(df)
    
    print("done\n")
    sys.exit(0)
except Exception as e:
    print(f"\nerror: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)