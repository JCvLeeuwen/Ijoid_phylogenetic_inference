#PDF extractor for linguistic data
#extracts wordlists from comparative PDF

import pdfplumber
import pandas as pd
import re
import sys
import os
import unicodedata

#words to skip
excluded = ['East', 'West', 'to', 'from', 'the', 'and', 'or', 'in', 'of', 'at', 'on', 'with', 'by',
    'for', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
    'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
    'Town', 'River', 'Delta', 'Code', 'Lect', 'Sources', 'Nembe', 'Notes']

#patterns to remove
annotations = [r'\[check\]', r'\?\?+', r'\bcheck\b', r'\bid\.', r'\bsp\.', r'cf\.', 
               r'\bJ\s+\d+', r'\bS\b', r'\bGb\b', r'\bGB\b']

#tone marks unicode
TONE_MARKS = {'\u0301': '́', '\u0300': '̀', '\u0304': '̄', '\u0302': '̂',
              '\u030C': '̌', '\u0303': '̃', '\u0330': '̰', '\u0339': '̹', '\u031A': '̚'}

#fix unicode and tone marks
def fix_unicode(text):
    if not text:
        return ""
    #normalize unicode
    text = unicodedata.normalize('NFC', text)
    #remove spaces before tone marks
    for mark in TONE_MARKS.values():
        text = text.replace(' ' + mark, mark)
        text = text.replace('\u00A0' + mark, mark)
    #fix separated marks
    text = re.sub(r'(\w)\s+([̀-ͯ])', r'\1\2', text)
    return text

def fix_tone_in_word(word):
    if not word:
        return ""
    word = fix_unicode(word)
    #fix spacing in words
    word = re.sub(r'([a-zɔɛəʊɪũãẽĩõ])\s+([̰́̀̄̂̌̃])', r'\1\2', word, flags=re.IGNORECASE)
    word = re.sub(r'\s+', ' ', word)
    return word.strip()

#clean up concept names
def clean_concept(raw):
    if not raw:
        return ""
    concept = fix_unicode(raw)
    #remove numbering
    concept = re.sub(r'^\d+[=\.\s]+', '', concept)
    #remove parentheses
    concept = re.sub(r'\([^)]*\)', '', concept)
    #remove cross-references
    concept = re.sub(r'\bcf\..*', '', concept, flags=re.IGNORECASE)
    concept = re.sub(r'=.*', '', concept)
    #take first part if comma separated
    if ',' in concept:
        concept = concept.split(',')[0]
    #take first part if slash separated
    if '/' in concept:
        concept = concept.split('/')[0]
    concept = concept.strip('\'" \t\n\r')
    concept = ' '.join(concept.split())
    return concept.upper().strip()

#convert orthography
def fix_orthography(word):
    if not word:
        return ""
    word = fix_tone_in_word(word)
    #replace letters
    word = word.replace('c', 'tʃ')
    word = word.replace('j', 'dʒ')
    #fix y
    word = re.sub(r'\by', 'j', word)
    word = re.sub(r'([^aeiouəɛɔʊɪãẽĩõṹ̀̄̂̌̃])y([^aeiouəɛɔʊɪãẽĩõṹ̀̄̂̌̃])', r'\1j\2', word)
    return word

#remove tone marks
def remove_tones(word):
    if not word:
        return ""
    tone_list = ['́', '̀', '̄', '̂', '̌', '̃', '̰', '↓', '↑', '̹', '̚']
    result = word
    for t in tone_list:
        result = result.replace(t, '')
    result = unicodedata.normalize('NFC', result)
    return result

#clean translation text
def clean_translation(raw):
    if not raw or not raw.strip():
        return []
    text = fix_unicode(raw)
    #remove annotations
    for pattern in annotations:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    #remove glosses
    text = re.sub(r'=([^,/]+)', '', text)
    #remove parentheses
    text = re.sub(r'\([^)]*\)', '', text)
    #remove also, contrast, cf
    text = re.sub(r'\balso\s+[^\s,/]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bcontrast\s+[^\s,/]+', '', text, flags=re.IGNORECASE)
    #remove quotes
    text = text.replace("'", '').replace('"', '')
    #remove symbols
    text = re.sub(r'[\*\+](?=\s|$)', '', text)
    text = re.sub(r'\?+', '', text)
    #split on comma or slash
    words = re.split(r'\s*[,/]\s*', text)
    cleaned = []
    for w in words:
        w = w.strip()
        #skip empty
        if not w or w in ['', '-', '*', '+', '?', '??', 'a.', 'b.']:
            continue
        if re.match(r'^[\s\-\*\+\?\.]+$', w):
            continue
        #fix tone
        w = fix_tone_in_word(w)
        #fix orthography
        w = fix_orthography(w)
        w = w.strip()
        if len(w) > 0 and not re.match(r'^[\s\-\*\+\?\.]+$', w):
            cleaned.append(w)
    return cleaned

#check if line starts with language code
def get_lang_and_text(line, lang_codes):
    line = line.strip()
    if not line:
        return None, None
    line = fix_unicode(line)
    parts = line.split(maxsplit=1)
    first = parts[0] if parts else ""
    #check standard codes
    for code in lang_codes:
        if line.startswith(code + ' ') or line == code:
            if line == code:
                trans = ""
            else:
                trans = line[len(code):].strip()
            return code, trans
    #special cases
    special = {'Ịb': 'IB', 'Ịban': 'IB', 'Kala': 'KA', 'Kalab': 'KA', 
               'Nembe': 'NE', 'Defaka': 'DE'}
    for marker, code in special.items():
        if first.startswith(marker):
            trans = line[len(first):].strip()
            return code, trans
    return None, None

def has_lang_code(line, lang_codes):
    words = line.strip().split()
    for w in words:
        if w in lang_codes:
            return True
        if any(m in w for m in ['Ịb', 'Kala', 'Nembe', 'Defaka']):
            return True
    return False

#process one page
def process_page(text, page_num, lang_codes):
    lines = text.strip().split('\n')
    if not lines:
        return []
    first_line = lines[0].strip()
    if not first_line:
        return []
    #skip if first line has language codes
    if has_lang_code(first_line, lang_codes):
        print(f"  skipping page {page_num} - has language codes in first line")
        return []
    #get concept
    concept = clean_concept(first_line)
    if not concept:
        print(f"  no concept on page {page_num}")
        return []
    print(f"  ppage {page_num}: '{concept}'")
    #get translations
    translations = {}
    for i, line in enumerate(lines[1:], 2):
        code, text = get_lang_and_text(line, lang_codes)
        if code:
            words = clean_translation(text)
            if words:
                translations[code] = words
                preview = words[:2]
                extra = f" (+{len(words)-2})" if len(words) > 2 else ""
                print(f"    {code}: {preview}{extra}")
    #make rows
    max_syn = max([len(w) for w in translations.values()] or [0])
    if max_syn == 0:
        print(f"    no etries for '{concept}'")
        return []
    rows = []
    for idx in range(max_syn):
        row = {'Concept': concept}
        for code in sorted(translations.keys()):
            words = translations[code]
            if idx < len(words):
                row[code] = words[idx]
            else:
                row[code] = ""
        rows.append(row)
    print(f"    mmade {len(rows)} rows")
    return rows

#add concept IDs
def add_concept_ids(rows):
    print("\nadding concept IDs...")
    #map concepts to IDs
    concept_map = {}
    id_num = 0
    for row in rows:
        concept = row['Concept']
        if concept not in concept_map:
            id_num += 1
            concept_map[concept] = id_num
    print(f"Found {len(concept_map)} unique concepts")
    #add IDs to rows
    new_rows = []
    for row in rows:
        concept = row['Concept']
        cid = concept_map[concept]
        new_row = {'ConceptID': cid}
        new_row.update(row)
        new_rows.append(new_row)
    #show some examples
    print("examples:")
    shown = set()
    for row in new_rows[:20]:
        cid = row['ConceptID']
        concept = row['Concept']
        if cid not in shown:
            print(f"  {cid} -> {concept}")
            shown.add(cid)
            if len(shown) >= 5:
                break
    return new_rows

#fix ID language column conflict
def fix_id_column(rows):
    if not rows:
        return rows
    #check if ID column exists
    has_id = any('ID' in row and 'ConceptID' in row for row in rows)
    if has_id:
        print("\nWARNING: 'ID' language conflicts with ConceptID")
        print("Renaming ID to ID_LANG")
        new_rows = []
        for row in rows:
            new_row = {}
            for key, val in row.items():
                if key == 'ID' and 'ConceptID' in row:
                    new_row['ID_LANG'] = val
                else:
                    new_row[key] = val
            new_rows.append(new_row)
        return new_rows
    return rows

#get language codes from pages 2-4
def get_lang_codes(pdf_path):
    codes = []
    pdf = pdfplumber.open(pdf_path)
    if len(pdf.pages) < 4:
        print(f"wrong PDF input? PDF only has {len(pdf.pages)} pages")
        return codes
    #pages 2,3,4 
    for page_num in [1, 2, 3]:
        page = pdf.pages[page_num]
        text = page.extract_text()
        if not text:
            continue
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = re.findall(r'\S+', line)
            #get 2-letter codes
            if len(words) >= 1 and len(words[0]) == 2:
                first = words[0]
                if first.isalpha() and first not in excluded:
                    codes.append(first)
    pdf.close()
    codes = sorted(set(codes))
    return codes

#main extraction
def extract_data(pdf_path, output_csv, start_page=6):
    print("getting language codes")

    lang_codes = get_lang_codes(pdf_path)
    if not lang_codes:
        print("ERROR: no language codes found")
        return 0
    print(f"found {len(lang_codes)} codes: {', '.join(lang_codes)}")
    
    print(f"extracting data (from page {start_page})")

    all_rows = []
    pdf = pdfplumber.open(pdf_path)
    total = len(pdf.pages)
    print(f"total pages: {total}")
    
    for page_num, page in enumerate(pdf.pages):
        if page_num < start_page - 1:
            continue
        print(f"\npage {page_num + 1}/{total}")
        text = page.extract_text()
        if not text:
            print("  no text")
            continue
        rows = process_page(text, page_num + 1, lang_codes)
        all_rows.extend(rows)
    
    pdf.close()
    
    if not all_rows:
        print("\nno data extracted...")
        return 0
    
    print(f"\nextracted {len(all_rows)} total rows")
    
    #fix ID column
    all_rows = fix_id_column(all_rows)
    
    #add concept IDs
    all_rows = add_concept_ids(all_rows)
    
    #make dataframe
    print("making CSV")
    df = pd.DataFrame(all_rows)
    
    #fix column order
    cols = df.columns.tolist()
    if 'ConceptID' in cols:
        cols.remove('ConceptID')
    if 'Concept' in cols:
        cols.remove('Concept')
    final_cols = ['ConceptID', 'Concept'] + sorted(cols)
    df = df[final_cols]
    
    #save
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"created csv: {len(df)} rows, {len(df.columns)} columns")
    print(f"unique concepts: {df['ConceptID'].nunique()}")
    print(f"languages: {len(df.columns) - 2}")
    print(f"saved as: {output_csv}")
    
    #preview
    print("first 10 rows:")
    pd.set_option('display.max_columns', 10)
    print(df.head(10).to_string(index=False, max_colwidth=25))
    
    #show tone marks
    print("checking tone marks:")
    sample = df.iloc[0]
    print(f"concept: {sample['Concept']}")
    print("sample forms:")
    for col in df.columns[2:8]:
        val = sample[col]
        if val and len(val) > 0:
            print(f"  {col}: {val}")
    
    return df['ConceptID'].nunique()


if len(sys.argv) > 1:
    pdf_file = sys.argv[1]
else:
    pdf_file = input("\nPDF file path: ").strip()

if not os.path.exists(pdf_file):
    print(f"\nERROR: PDF not found: {pdf_file}")
    sys.exit(1)

#make output filename
base = os.path.splitext(os.path.basename(pdf_file))[0]
output = f"{base}_cleaned.csv"

print(f"\ninput: {pdf_file}")
print(f"output: {output}")

try:
    total = extract_data(pdf_file, output)
    print("DONE!")
    print(f"total concepts: {total}")
    print(f"saved as: {output}")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)