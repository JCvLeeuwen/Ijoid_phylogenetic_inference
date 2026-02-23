# split cognate sets using tone patterns

import pandas as pd
import numpy as np
from collections import defaultdict
from lingpy import Wordlist
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import sys

# load tone patterns
def load_tones(tone_csv):
    print(f"loading tone patterns: {tone_csv}")
    df = pd.read_csv(tone_csv)
    tone_dict = {}
    lang_cols = [col for col in df.columns if col not in ['ConceptID', 'Concept']]
    for _, row in df.iterrows():
        concept = row['Concept']
        for lang in lang_cols:
            pattern = row[lang]
            if pd.notna(pattern) and pattern:
                tone_dict[(concept, lang)] = pattern
    print(f"loaded {len(tone_dict):,} patterns")
    return tone_dict

# calculate tone similarity
def tone_similarity(p1, p2):
    if p1 == p2:
        return 1.0
    tones1 = p1.split('.')
    tones2 = p2.split('.')
    min_len = min(len(tones1), len(tones2))
    max_len = max(len(tones1), len(tones2))
    if max_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if tones1[i] == tones2[i])
    return matches / max_len

# cluster tone patterns
def cluster_tones(patterns, threshold=0.6):
    n = len(patterns)
    if n == 1:
        return [0]
    
    # similarity matrix
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            if i == j:
                sim_matrix[i, j] = 1.0
            else:
                sim = tone_similarity(patterns[i], patterns[j])
                sim_matrix[i, j] = sim
                sim_matrix[j, i] = sim
    
    # distance matrix
    dist_matrix = 1 - sim_matrix
    condensed = squareform(dist_matrix)
    
    if np.all(condensed == 0):
        return [0] * n
    
    link_matrix = linkage(condensed, method='average')
    clusters = fcluster(link_matrix, threshold, criterion='distance')
    return clusters

# decide if should split
def should_split(members, tones, clusters, min_size=2):
    from collections import Counter
    n_with_tones = len([p for p in tones if p])
    
    if n_with_tones < 3:
        return 'keep'
    
    cluster_counts = Counter(clusters)
    n_clusters = len(cluster_counts)
    
    if n_clusters == 1:
        return 'keep'
    if n_clusters == n_with_tones:
        return 'keep'
    
    valid = [c for c, count in cluster_counts.items() if count >= min_size]
    if 2 <= len(valid) <= 3:
        return 'split'
    return 'review'

# split cognate sets
def split_sets(lexstat_file, tone_csv, output_file, unstable_ids=None, tone_threshold=0.6):
    print("tone-based splitting")

    # load
    print(f"\nloading lexstat")
    wl = Wordlist(lexstat_file)
    print(f"loaded {len(wl):,} forms")
    
    tone_dict = load_tones(tone_csv)
    
    # organize by cognate sets
    cog_sets = defaultdict(list)
    for idx in wl:
        cogid = wl[idx, 'cogid']
        cog_sets[cogid].append(idx)
    print(f"found {len(cog_sets):,} cognate sets")
    
    # filter to unstable if provided
    if unstable_ids:
        cog_sets = {k: v for k, v in cog_sets.items() if k in unstable_ids}
        print(f"considering {len(cog_sets):,} unstable sets")
    
    # process
    print(f"\nanalyzing")
    print(f"threshold: {tone_threshold}")
    
    decisions = {'keep': 0, 'split': 0, 'review': 0, 'no_tone_data': 0}
    split_details = []
    new_assignments = {}
    next_cogid = max(cog_sets.keys()) + 1
    
    for cogid, members in cog_sets.items():
        # get tone patterns
        member_tones = []
        tones_available = []
        
        for idx in members:
            concept = wl[idx, 'concept']
            doculect = wl[idx, 'doculect']
            pattern = tone_dict.get((concept, doculect))
            member_tones.append(pattern)
            if pattern:
                tones_available.append(pattern)
        
        # skip if not enough tone data
        if len(tones_available) < 3:
            decisions['no_tone_data'] += 1
            for idx in members:
                new_assignments[idx] = cogid
            continue
        
        # cluster
        tone_clusters = cluster_tones(tones_available, threshold=tone_threshold)
        
        # expand to include forms without tones
        full_clusters = []
        cluster_idx = 0
        for pattern in member_tones:
            if pattern:
                full_clusters.append(tone_clusters[cluster_idx])
                cluster_idx += 1
            else:
                full_clusters.append(None)
        
        # decide
        decision = should_split(members, member_tones, tone_clusters)
        decisions[decision] += 1
        
        # apply
        if decision == 'split':
            cluster_to_cogid = {}
            for member, cluster_id in zip(members, full_clusters):
                if cluster_id is None:
                    new_assignments[member] = cogid
                else:
                    if cluster_id not in cluster_to_cogid:
                        if cluster_id == min([c for c in full_clusters if c is not None]):
                            cluster_to_cogid[cluster_id] = cogid
                        else:
                            cluster_to_cogid[cluster_id] = next_cogid
                            next_cogid += 1
                    new_assignments[member] = cluster_to_cogid[cluster_id]
            
            split_details.append({
                'Original_CogID': cogid,
                'Decision': 'SPLIT',
                'N_Members': len(members),
                'N_Clusters': len(set(full_clusters) - {None}),
                'New_CogIDs': list(cluster_to_cogid.values())
            })
        else:
            for idx in members:
                new_assignments[idx] = cogid
    
    # summary
    print(f"\ndecisions:")
    total = sum(decisions.values())
    for dec, count in sorted(decisions.items()):
        pct = count / total * 100 if total > 0 else 0
        print(f"  {dec:15s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\nchanges:")
    old_n = len(cog_sets)
    new_n = len(set(new_assignments.values()))
    print(f"  before: {old_n:,}")
    print(f"  after: {new_n:,}")
    print(f"  change: +{new_n - old_n:,}")
    
    # save
    for idx in wl:
        if idx in new_assignments:
            wl[idx, 'cogid'] = new_assignments[idx]
    wl.output('tsv', filename=output_file.replace('.tsv', ''))
    print(f"\nsaved to: {output_file}")
    
    if split_details:
        details_df = pd.DataFrame(split_details)
        details_file = output_file.replace('.tsv', '_details.csv')
        details_df.to_csv(details_file, index=False)
        print(f"details saved to: {details_file}")

    return decisions

# main
import argparse

parser = argparse.ArgumentParser(description='refine cognate sets using tone')

parser.add_argument('lexstat', help='lexstat output tsv')
parser.add_argument('tones', help='tone patterns csv')
parser.add_argument('-o', '--output', default='lexstat_refined.tsv', help='output file')
parser.add_argument('--unstable-ids', help='file with unstable cognate ids')
parser.add_argument('--tone-threshold', type=float, default=0.6, help='tone threshold')

args = parser.parse_args()

try:
    # load unstable ids
    unstable_ids = None
    if args.unstable_ids:
        with open(args.unstable_ids) as f:
            unstable_ids = [int(line.strip()) for line in f if line.strip()]
        print(f"loaded {len(unstable_ids)} unstable ids")
    
    # run
    stats = split_sets(
        lexstat_file=args.lexstat,
        tone_csv=args.tones,
        output_file=args.output,
        unstable_ids=unstable_ids,
        tone_threshold=args.tone_threshold,
    )
    
    print("done\n")
    sys.exit(0)
except Exception as e:
    print(f"\nerror: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)