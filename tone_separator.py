# tone separator 
# remove pitch tone and extract patterns

import pandas as pd
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Tuple

# tone marks
PITCH_TONE = {
    '\u0301': 'H',  # acute - high
    '\u0300': 'L',  # grave - low
    '\u0304': 'M',  # macron - mid
    '\u0302': 'R',  # circumflex - rising
    '\u030C': 'F',  # caron - falling
    '↓': 'D',       # downstep
    '↑': 'U',       # upstep
}

UNMARKED = 'U'  # unmarked = low tone

# dont remove these
NON_TONE = {
    '\u0303': 'nasal',
    '\u0330': 'creaky',
    '\u0339': 'other',
    '\u031A': 'other',
}

# vowels
VOWELS = set('aeiouəɛɔʊɪũãẽĩõAEIOUƏƐƆŨÃẼĨÕ')

# remove pitch tone only
def remove_tone(text):
    if not text or pd.isna(text):
        return ""
    # normalize
    text = unicodedata.normalize('NFD', text)
    # remove standalone marks
    for mark in ['´', '`', '¯', 'ˆ', 'ˇ', '↓', '↑']:
        text = text.replace(mark, '')
    # filter combining marks
    filtered = []
    for char in text:
        if unicodedata.category(char) == 'Mn':
            if char not in PITCH_TONE:
                filtered.append(char)
        else:
            filtered.append(char)
    result = ''.join(filtered)
    # fix spacing
    result = re.sub(r'([a-zəɛɔʊɪũãẽĩõ])\s+([a-zəɛɔʊɪũãẽĩõ])', r'\1\2', result, flags=re.IGNORECASE)
    result = unicodedata.normalize('NFC', result)
    return result.strip()

# extract tone patterns sequentially
def extract_tones(text, use_simple=False):
    if not text or pd.isna(text):
        return [], "", 0
    text_nfd = unicodedata.normalize('NFD', text)
    
    if use_simple:
        # simple version - just get tones in order
        tone_list = []
        i = 0
        while i < len(text_nfd):
            char = text_nfd[i]
            if char == ' ':
                i += 1
                continue
            if char in VOWELS:
                # look for tone mark
                tone_found = None
                j = i + 1
                while j < len(text_nfd) and unicodedata.category(text_nfd[j]) == 'Mn':
                    if text_nfd[j] in PITCH_TONE:
                        tone_found = PITCH_TONE[text_nfd[j]]
                        break
                    j += 1
                tone_list.append(tone_found if tone_found else UNMARKED)
                i = j
            else:
                i += 1
        tone_pattern = '.'.join(tone_list) if tone_list else ""
        return tone_list, tone_pattern, len(tone_list)
    
    else:
        # version with misalignment correction
        # find vowels and marks
        vowel_data = []
        i = 0
        while i < len(text_nfd):
            char = text_nfd[i]
            if char == ' ':
                i += 1
                continue
            if char in VOWELS:
                vowel_info = {
                    'vowel': char,
                    'position': i,
                    'tone_marks': []
                }
                # get combining marks
                j = i + 1
                while j < len(text_nfd) and unicodedata.category(text_nfd[j]) == 'Mn':
                    if text_nfd[j] in PITCH_TONE:
                        vowel_info['tone_marks'].append({
                            'mark': text_nfd[j],
                            'symbol': PITCH_TONE[text_nfd[j]],
                            'position': j
                        })
                    j += 1
                vowel_data.append(vowel_info)
                i = j
            else:
                i += 1
        
        # handle misaligned tones
        tone_list = []
        for idx, vowel_info in enumerate(vowel_data):
            marks = vowel_info['tone_marks']
            if len(marks) == 0:
                tone_list.append(UNMARKED)
            elif len(marks) == 1:
                tone_list.append(marks[0]['symbol'])
            else:
                # multiple marks - check if previous vowel needs correction
                if idx > 0 and len(vowel_data[idx - 1]['tone_marks']) == 0:
                    if len(tone_list) > 0 and tone_list[-1] == UNMARKED:
                        tone_list[-1] = marks[0]['symbol']
                        tone_list.append(marks[1]['symbol'] if len(marks) > 1 else UNMARKED)
                    else:
                        tone_list.append(marks[-1]['symbol'])
                else:
                    tone_list.append(marks[-1]['symbol'])
        
        tone_pattern = '.'.join(tone_list) if tone_list else ""
        return tone_list, tone_pattern, len(vowel_data)

# process csv
def process_csv(input_csv, output_base, use_simple=False):
    print("tone separator")
    print(f"correction: {'off' if use_simple else 'on'}")

    
    # load
    print(f"loading: {input_csv}")
    df = pd.read_csv(input_csv)
    
    # get columns
    meta_cols = ['ConceptID', 'Concept']
    lang_cols = [col for col in df.columns if col not in meta_cols]
    print(f"found {len(df)} concepts, {len(lang_cols)} languages")
    
    # create segments file

    print("removing tone marks")

    df_segments = df[meta_cols].copy()
    total_processed = 0
    total_changed = 0
    
    for lang in lang_cols:
        if lang in df.columns:
            df_segments[lang] = df[lang].apply(remove_tone)
            # count
            non_empty = sum(1 for x in df[lang] if not pd.isna(x) and str(x).strip() != "")
            changed = sum(1 for i in range(len(df)) 
                         if str(df.iloc[i][lang]) != str(df_segments.iloc[i][lang])
                         and pd.notna(df.iloc[i][lang])
                         and str(df.iloc[i][lang]).strip() != "")
            total_processed += non_empty
            total_changed += changed
    
    print(f"total: {total_changed}/{total_processed} words had tone")
    
    # create tone patterns
    print("extracting tone patterns")

    
    df_tones = df[meta_cols].copy()
    
    for lang in lang_cols:
        if lang in df.columns:
            results = df[lang].apply(lambda x: extract_tones(x, use_simple))
            df_tones[lang] = results.apply(lambda x: x[1])
    
    print("tone patterns extracted")
    
    # save files

    print("saving files")

    
    segments_file = f"{output_base}_segments.csv"
    df_segments.to_csv(segments_file, index=False, encoding='utf-8')
    print(f"saved segments: {segments_file}")
    
    tones_file = f"{output_base}_tones.csv"
    df_tones.to_csv(tones_file, index=False, encoding='utf-8')
    print(f"saved tones: {tones_file}")
    
    original_file = f"{output_base}_original.csv"
    df.to_csv(original_file, index=False, encoding='utf-8')
    print(f"saved original: {original_file}")
    
    # preview
    print("preview")

    preview_rows = min(3, len(df))
    preview_langs = [lang for lang in lang_cols[:4] if lang in df.columns]
    
    for i in range(preview_rows):
        cid = df.iloc[i]['ConceptID']
        concept = df.iloc[i]['Concept']
        print(f"\n{cid}. {concept}")
        for lang in preview_langs:
            orig = df.iloc[i][lang]
            seg = df_segments.iloc[i][lang]
            tone = df_tones.iloc[i][lang]
            if pd.notna(orig) and str(orig).strip() != "":
                print(f"  {lang}: {str(orig):25s} -> {str(seg):20s} [{tone}]")
    
    # basic stats

    print("statistics")
    print(f"total words: {total_processed}")
    print(f"words with tone: {total_changed} ({100*total_changed/total_processed:.1f}%)")
    

    print("complete")
    print(f"segments file: {segments_file}")
    print(f"tones file: {tones_file}")

# main

# get input
if len(sys.argv) > 1:
    input_csv = sys.argv[1]
else:
    input_csv = input("enter csv file path: ").strip()

if not Path(input_csv).exists():
    print(f"error: file not found: {input_csv}")
    sys.exit(1)

# ask about correction
correct = input("use misalignment correction? (y/n) [y]: ").lower().strip()
use_simple = (correct == 'n')

# make output name
input_path = Path(input_csv)
output_base = input_path.stem

print(f"\noutput files:")
print(f"  {output_base}_segments.csv")
print(f"  {output_base}_tones.csv")
print(f"  {output_base}_original.csv")

proceed = input("\nproceed? (y/n) [y]: ").lower().strip()
if proceed and proceed not in ['y', 'yes', '']:
    print("cancelled")
    sys.exit(0)

print()

try:
    process_csv(input_csv, output_base, use_simple=use_simple)
except Exception as e:
    print(f"\nerror: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)