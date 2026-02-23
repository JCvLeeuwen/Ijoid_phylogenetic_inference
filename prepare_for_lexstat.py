# fix nasalization marks and prepare for lingpy

import pandas as pd
import unicodedata
import re
from pathlib import Path

# realign tildes to correct vowels
def realign_nasalization(form):
    # normalize
    form = unicodedata.normalize('NFD', form)
    # vowels
    vowels = set('aeiouɛɔɪʊAEIOUƐƆƗ')
    
    # find characters and tildes
    chars = []
    i = 0
    while i < len(form):
        if form[i] == '\u0303':
            chars.append(('TILDE', i))
            i += 1
        elif form[i] == ' ':
            chars.append(('SPACE', i))
            i += 1
        elif form[i] == '-':
            chars.append(('HYPHEN', i))
            i += 1
        else:
            j = i + 1
            while j < len(form) and unicodedata.category(form[j]) in ['Mn', 'Mc']:
                j += 1
            char_with_marks = form[i:j]
            base_char = form[i]
            is_vowel = base_char in vowels
            has_tilde = '\u0303' in char_with_marks
            chars.append(('VOWEL' if is_vowel else 'CONS', char_with_marks, has_tilde))
            i = j
    
    # realign tildes
    result = []
    i = 0
    while i < len(chars):
        if len(chars[i]) == 2:
            typ, val = chars[i]
            has_tilde = False
        else:
            typ, val, has_tilde = chars[i]
        
        # look for tildes ahead
        tildes_ahead = 0
        j = i + 1
        while j < len(chars):
            if len(chars[j]) == 2:
                t, v = chars[j]
                ht = False
            else:
                t, v, ht = chars[j]
            if t == 'TILDE':
                tildes_ahead += 1
                j += 1
            elif t == 'SPACE':
                j += 1
            else:
                break
        
        if typ == 'VOWEL':
            # attach tildes to vowel
            if tildes_ahead > 0:
                result.append(val + '\u0303' * tildes_ahead)
                i = j
            else:
                result.append(val)
                i += 1
        elif typ == 'CONS':
            # if consonant has tilde, move to previous vowel
            if has_tilde:
                base_cons = val.replace('\u0303', '')
                # find previous vowel
                for k in range(len(result) - 1, -1, -1):
                    if result[k]:
                        base = unicodedata.normalize('NFD', result[k])[0]
                        if base in vowels:
                            if '\u0303' not in result[k]:
                                result[k] = result[k] + '\u0303'
                            break
                result.append(base_cons)
                if tildes_ahead > 0:
                    i = j
                else:
                    i += 1
            elif tildes_ahead > 0:
                # move tilde to previous vowel
                for k in range(len(result) - 1, -1, -1):
                    if result[k]:
                        base = unicodedata.normalize('NFD', result[k])[0]
                        if base in vowels:
                            if '\u0303' not in result[k]:
                                result[k] = result[k] + '\u0303'
                            break
                result.append(val)
                i = j
            else:
                result.append(val)
                i += 1
        elif typ == 'SPACE':
            if i + 1 < len(chars):
                next_type = chars[i+1][0]
                if next_type != 'TILDE':
                    result.append(' ')
            i += 1
        elif typ == 'HYPHEN':
            result.append('-')
            i += 1
        else:
            i += 1
    
    corrected = ''.join(result)
    corrected = re.sub(r'\s+', ' ', corrected).strip()
    return corrected

# handle double vowels with tildes
def realign_double_vowels(form):
    form = unicodedata.normalize('NFD', form)
    pattern = r'([aeiouɛɔɪʊ])\1\s*(\u0303)\s*(\u0303)?'
    def replace_double(match):
        vowel = match.group(1)
        return vowel + '\u0303' + vowel + '\u0303'
    result = re.sub(pattern, replace_double, form)
    return result

# apply all fixes
def fix_nasalization(form):
    if pd.isna(form) or form == '':
        return form
    form = realign_double_vowels(form)
    form = realign_nasalization(form)
    return form

# tokenize
def tokenize_form(form):
    form = unicodedata.normalize('NFD', form)
    # digraphs
    digraphs = ['gb', 'kp', 'mb', 'nd', 'ŋg', 'ŋm', 'ny', 'dʒ']
    tokens = []
    i = 0
    while i < len(form):
        if form[i] in [' ', '-']:
            i += 1
            continue
        # check digraphs
        if i < len(form) - 1:
            digraph = form[i:i+2]
            if digraph in digraphs:
                if i + 2 < len(form) and form[i+2] == '\u0303':
                    tokens.append(digraph + '\u0303')
                    i += 3
                else:
                    tokens.append(digraph)
                    i += 2
                continue
        # single character
        j = i + 1
        while j < len(form) and unicodedata.category(form[j]) in ['Mn', 'Mc']:
            j += 1
        tokens.append(form[i:j])
        i = j
    return ' '.join(tokens)

# process dataset
def process_dataset(input_csv, output_csv, exclude_langs=None):
    print("loading data...")
    df = pd.read_csv(input_csv)
    
    # get language columns
    lang_cols = [col for col in df.columns if col not in ['ConceptID', 'Concept']]
    
    # exclude languages
    if exclude_langs:
        lang_cols = [col for col in lang_cols if col not in exclude_langs]
        print(f"excluded: {exclude_langs}")
    
    print(f"fixing nasalization for {len(lang_cols)} languages...")
    
    # correct dataset
    corrected_df = df.copy()
    corrections = 0
    
    for col in lang_cols:
        for idx, orig in enumerate(df[col]):
            if pd.notna(orig) and orig != '':
                fixed = fix_nasalization(str(orig))
                corrected_df.at[idx, col] = fixed
                if orig != fixed:
                    corrections += 1
    
    print(f"made {corrections} corrections")
    
    # create lingpy format
    print("creating lingpy format...")
    lingpy_data = []
    word_id = 1
    
    for idx, row in corrected_df.iterrows():
        concept_id = row['ConceptID']
        concept = row['Concept']
        for lang in lang_cols:
            form = row[lang]
            if pd.isna(form) or form == '':
                continue
            tokens = tokenize_form(form)
            lingpy_data.append({
                'ID': word_id,
                'CONCEPT': concept,
                'CONCEPTICON_ID': concept_id,
                'DOCULECT': lang,
                'IPA': form,
                'TOKENS': tokens
            })
            word_id += 1
    
    # save
    lingpy_df = pd.DataFrame(lingpy_data)
    lingpy_df.to_csv(output_csv, index=False, sep='\t')
    
    print(f"saved to: {output_csv}")
    print(f"total entries: {len(lingpy_df)}")
    
    # show sample
    print("\nsample tokenization:")
    for idx, row in lingpy_df.head(5).iterrows():
        print(f"  {row['IPA']:20s} -> {row['TOKENS']}")
    
    return lingpy_df

# test
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="fix nasalization marks and prepare for lingpy")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("output_tsv", help="Path to output TSV file")
    parser.add_argument(
        "--exclude", 
        nargs="*", 
        metavar="LANG",
        help="Language columns to exclude, e.g. --exclude OT WO"
    )

    args = parser.parse_args()
    process_dataset(args.input_csv, args.output_tsv, exclude_langs=args.exclude)
