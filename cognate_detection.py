# test multiple thresholds for lexstat

import pandas as pd
from lingpy import Wordlist
from lingpy.compare.lexstat import LexStat
import sys
from pathlib import Path
import time

def test_thresholds(input_file, output_dir, thresholds=None, runs=10000):
    if thresholds is None:
        thresholds = [0.50, 0.55, 0.60]
    
    start = time.time()
    
    print("lexstat analysis")
    print(f"\ninput: {input_file}")
    print(f"output: {output_dir}")
    print(f"thresholds: {', '.join(str(t) for t in thresholds)}")
    print(f"runs: {runs:,}")
    
    # make output dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # load wordlist
    print(f"\nloading wordlist")
    wl = Wordlist(input_file)
    print(f"loaded {len(wl):,} words, {wl.height} concepts, {wl.width} languages")
    
    # create lexstat
    print(f"\ninitializing lexstat")
    lex = LexStat(wl)
    
    # train scorer
    print(f"\ntraining scorer ({runs:,} iterations)")
    print(f"this will take a while")
    scorer_start = time.time()
    lex.get_scorer(runs=runs)
    scorer_time = time.time() - scorer_start
    print(f"scorer training done ({scorer_time/60:.1f} minutes)")
    
    # test each threshold
    results = []
    
    for threshold in thresholds:
        print(f"\n{'='*60}")
        print(f"threshold: {threshold}")
        print(f"{'='*60}")
        
        print(f"clustering")
        cluster_start = time.time()
        lex.cluster(method='lexstat', threshold=threshold, ref='cogid')
        cluster_time = time.time() - cluster_start
        print(f"done ({cluster_time:.1f} seconds)")
        
        # analyze
        cognate_sets = {}
        for idx in lex:
            cog_id = lex[idx, 'cogid']
            if cog_id not in cognate_sets:
                cognate_sets[cog_id] = []
            cognate_sets[cog_id].append(idx)
        
        n_sets = len(cognate_sets)
        n_singletons = sum(1 for s in cognate_sets.values() if len(s) == 1)
        set_sizes = [len(s) for s in cognate_sets.values()]
        avg_size = sum(set_sizes) / len(set_sizes)
        max_size = max(set_sizes)
        
        print(f"\nresults:")
        print(f"  cognate sets: {n_sets:,}")
        print(f"  singletons: {n_singletons:,} ({n_singletons/n_sets*100:.1f}%)")
        print(f"  avg size: {avg_size:.1f}")
        print(f"  max size: {max_size}")
        
        # save
        output_file = f"{output_dir}/lexstat_t{threshold:.2f}"
        lex.output('tsv', filename=output_file)
        print(f"saved to {output_file}.tsv")
        
        # add to summary
        results.append({
            'Threshold': threshold,
            'Cognate_Sets': n_sets,
            'Singletons': n_singletons,
            'Singleton_Pct': f"{n_singletons/n_sets*100:.1f}%",
            'Avg_Size': f"{avg_size:.1f}",
            'Max_Size': max_size
        })
    
    # summary
    total_time = time.time() - start
    
    print("comparison")
    
    summary_df = pd.DataFrame(results)
    print(summary_df.to_string(index=False))

    print("complete")
    print(f"total time: {total_time/60:.1f} minutes")
    
    return summary_df

# main
import argparse

parser = argparse.ArgumentParser(description='test multiple lexstat thresholds')

parser.add_argument('input', help='input tsv file')
parser.add_argument('-o', '--output-dir', default='threshold_tests', help='output directory')
parser.add_argument('-t', '--thresholds', nargs='+', type=float, default=[0.50, 0.55, 0.60], 
                    help='thresholds to test')
parser.add_argument('-r', '--runs', type=int, default=10000, help='scorer iterations')

args = parser.parse_args()

try:
    summary = test_thresholds(
        input_file=args.input,
        output_dir=args.output_dir,
        thresholds=args.thresholds,
        runs=args.runs
    )
    print("done\n")
    sys.exit(0)
except Exception as e:
    print(f"\nerror: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)