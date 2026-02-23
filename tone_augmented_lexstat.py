# tone-augmented lexstat - encode tone into segments

from lingpy import LexStat
import pandas as pd
import numpy as np
from collections import defaultdict
import re

class ToneAugmentedLexStat:
    # lexstat with tone encoded into segments
    # instead of [p,a,n,i] + [H,L], use [p_H, a_H, n_L, i_L]
    
    def __init__(self, wordlist_file, tone_csv, tone_mapping='syllable', **kwargs):

        print("tone-augmented lexstat")

        print(f"mapping: {tone_mapping}")
        
        # load wordlist
        print(f"\nloading wordlist")
        self.original_wl = LexStat(wordlist_file)
        print(f"loaded {len(self.original_wl):,} words")
        
        # load tones
        print(f"\nloading tones")
        self.tone_data = self._load_tones(tone_csv)
        print(f"loaded {len(self.tone_data):,} patterns")
        
        # create augmented wordlist
        print(f"\ncreating augmented segments")
        self.augmented_file = wordlist_file.replace('.tsv', '_augmented.tsv')
        self._create_augmented(tone_mapping)
        
        # load into lexstat
        print(f"\nloading into lexstat")
        self.lexstat = LexStat(self.augmented_file)
        print(f"ready")
        
        print("initialization complete")

    
    def _load_tones(self, tone_csv):
        # load tone patterns
        df = pd.read_csv(tone_csv)
        tone_map = {}
        lang_cols = [col for col in df.columns if col not in ['ConceptID', 'Concept']]
        
        for _, row in df.iterrows():
            concept = row['Concept']
            for lang in lang_cols:
                pattern = row[lang]
                if pd.notna(pattern) and pattern:
                    tone_map[(concept, lang)] = pattern
        return tone_map
    
    def _create_augmented(self, tone_mapping):
        # create wordlist with tone-augmented segments
        df = pd.read_csv(self.augmented_file.replace('_augmented', ''), 
                         sep='\t', comment='#')
        
        augmented_rows = []
        n_aug = 0
        n_no_tone = 0
        
        for idx, row in df.iterrows():
            concept = row['CONCEPT']
            doculect = row['DOCULECT']
            
            # get tone pattern
            tone_pattern = self.tone_data.get((concept, doculect))
            
            if tone_pattern:
                # parse tones
                tones = [t.strip() for t in tone_pattern.split('.')]
                # get segments
                segments = str(row['TOKENS']).split()
                # map tones to segments
                aug_segments = self._map_tones(segments, tones, tone_mapping)
                row['TOKENS'] = ' '.join(aug_segments)
                n_aug += 1
            else:
                n_no_tone += 1
            
            augmented_rows.append(row)
        
        # write
        aug_df = pd.DataFrame(augmented_rows)
        with open(self.augmented_file, 'w', encoding='utf-8') as f:
            f.write("# Wordlist\n\n# DATA\n")
            aug_df.to_csv(f, sep='\t', index=False)
        
        print(f"augmented: {n_aug:,} words")
        print(f"no tone: {n_no_tone:,} words")
        print(f"saved to: {self.augmented_file}")
    
    def _map_tones(self, segments, tones, mapping):
        # map tone pattern to segments
        
        if mapping == 'word':
            # one tone for whole word
            tone = tones[0] if len(tones) > 0 else 'X'
            return [f"{seg}_{tone}" for seg in segments]
        
        elif mapping == 'syllable':
            # one tone per syllable
            vowels = set('aeiouɛɔɪʊəæɑɨʉɯ')
            aug = []
            tone_idx = 0
            last_tone = tones[0] if len(tones) > 0 else 'X'
            
            for seg in segments:
                # check if vowel
                has_vowel = any(v in seg.lower() for v in vowels)
                
                if has_vowel and tone_idx < len(tones):
                    tone = tones[tone_idx]
                    last_tone = tone
                    aug.append(f"{seg}_{tone}")
                    tone_idx += 1
                else:
                    aug.append(f"{seg}_{last_tone}")
            return aug
        
        elif mapping == 'segment':
            # one tone per segment
            aug = []
            for i, seg in enumerate(segments):
                tone = tones[i] if i < len(tones) else 'X'
                aug.append(f"{seg}_{tone}")
            return aug
        else:
            raise ValueError(f"unknown mapping: {mapping}")
    
    def train(self, runs=10000, **kwargs):
        # train lexstat scorer
        print(f"\ntraining lexstatt")
        print(f"runs: {runs:,}")
        self.lexstat.get_scorer(runs=runs, **kwargs)
        print(f"training complete")
    
    def cluster(self, threshold=0.55, **kwargs):
        # cluster
        print(f"\nclustering with threshold {threshold}")
        self.lexstat.cluster(method='lexstat', threshold=threshold, ref='cogid', **kwargs)
        n_sets = len(set(self.lexstat[idx, 'cogid'] for idx in self.lexstat))
        print(f"created {n_sets:,} cognate sets")
    
    def output(self, filename, **kwargs):
        # save results
        print(f"\nsaving to {filename}")
        base = filename.replace('.tsv', '')
        self.lexstat.output('tsv', filename=base, **kwargs)
        print(f"saved")

# run complete pipeline
def run_pipeline(wordlist_file, tone_csv, output_file,
                 threshold=0.55, runs=10000, tone_mapping='syllable'):
    # create and run
    wl = ToneAugmentedLexStat(wordlist_file, tone_csv, tone_mapping=tone_mapping)
    wl.train(runs=runs)
    wl.cluster(threshold=threshold)
    wl.output(output_file)
    
    # summary
    print("summary")
    
    df = pd.read_csv(output_file, sep='\t', comment='#')
    n_sets = df['COGID'].nunique()
    n_singletons = sum(df['COGID'].value_counts() == 1)
    
    print(f"\ncognate sets: {n_sets:,}")
    print(f"singletons: {n_singletons:,} ({n_singletons/n_sets*100:.1f}%)")

    
    return wl

# main
import argparse

parser = argparse.ArgumentParser(description='tone-augmented lexstat')

parser.add_argument('wordlist', help='input wordlist tsv')
parser.add_argument('tones', help='tone patterns csv')
parser.add_argument('-o', '--output', default='tone_augmented_output.tsv', help='output file')
parser.add_argument('-t', '--threshold', type=float, default=0.55, help='clustering threshold')
parser.add_argument('-r', '--runs', type=int, default=10000, help='training runs')
parser.add_argument('--mapping', choices=['syllable', 'segment', 'word'], 
                    default='syllable', help='tone mapping method')

args = parser.parse_args()

run_pipeline(
    args.wordlist,
    args.tones,
    args.output,
    threshold=args.threshold,
    runs=args.runs,
    tone_mapping=args.mapping
)