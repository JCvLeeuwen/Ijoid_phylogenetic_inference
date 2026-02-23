# Ijoid Data Extraction and Automated Cognate Detection Pipeline

## Extract wordlist from PDF
Script: ijoidwordlistextractor.py

This script extracts data from the comparative wordlist PDF. It reads language codes from pages 2-4 and extracts concepts and translations from subsequent pages. 

Usage:
```bash
# provide path to PDF file as argument:
python ijoidwordlistextractor.py path/to/your_wordlist.pdf
```

Output: your_wordlist_cleaned.csv, a wide format CSV with ConceptID, Concept, and language columns

## Filter Languages and Concepts
Script: remove_insufficient_coverage.py

This script filters the dataset by removing specific languages and concepts with insufficient coverage. 

Usage: 
```bash
# Remove specific languages
# Languages are specified using their two letter code
python remove_insufficient_coverage.py input.csv output.csv --remove-langs OT,WO,EG,KL

# Keep only concepts with at least 10 translations
python remove_insufficient_coverage.py input.csv output.csv --min-langs 10

# Combine both filters
python remove_insufficient_coverage.py input.csv output.csv --remove-langs OT,WO --min-langs 15
```

Output: Filtered CSV

## Match concepts to WOLD and Create Separate Datasets Based on Borrowability Scores
Scripts: wold_score_matcher.py, manual_match_review.py, and vocabulary_partition.py
Requires: The parameters.csv found in wold_dataset.cldf.zip available for download under: https://wold.clld.org/download
###  i) Match Concepts
Script: wold_score_matcher.py

This script matches Ijoid concepts to WOLD dataset using fuzzy matching.

Usage:
```bash
python wold_score_matcher.py ijoid_wordlist.csv parameters.csv -o matched_results.csv -t 0.8

# Optional: create separate matched/unmatched files for review
python wold_score_matcher.py ijoid_wordlist.csv parameters.csv -o matched_results.csv --manual-review

```

Output: A wide-format CSV with columns for the concepts of the Ijoid wordlist, the WOLD meaning it was matched with, the corresponding scores, and metrics quantifying the confidence of the matches. 

### ii) Manually Review Matches
Script: manual_match_review.py

This script allows for the (optional) interactive review of fuzzy matches and manual assignment of unmatched concepts.

Usage: 
```bash
# Interactive review
python manual_match_review.py review matched_results.csv parameters.csv -o reviewed_results.csv
```

Output: Reviewed and revised CSV of matched concepts

### iii) Vocabulary Partition
Script: vocabulary_partition.py

This script splits vocabulary into basic (resistant to borrowing) and borrowable based on WOLD scores.

Usage:
```bash
python vocabulary_partition.py filtered_wordlist.csv matched_results.csv output_dir/ 0.8

# Default threshold is 0.8 (scores >= 0.8 = basic vocabulary)
```

Outputs three files:
basic_vocabulary.csv 
borrowable_vocabulary.csv 
unmatched_vocabulary.csv 
## Separate Tone from Segments
Script: tone_separator.py

This script removes pitch tone marks from segments while preserving nasalization, 
extracts tone patterns separately for analysis.

Usage:
```bash
python tone_separator.py input.csv
# When prompted:
# Confirm misalignment correction (y/n)
# Confirm proceed (y)
```

Outputs three files: 
input_segments.csv
input_tones.csv
input_original.csv

## Prepare Data for LexStat Cognate Detection
Script: prepare_for_lexstat.py

This script fixes nasalization artifacts from PDF extraction and converts to LingPy TSV format with proper tokenization.

Usage
```bash
python prepare_for_lexstat.py input.csv output.tsv --exclude OT WO
```

Output: LingPy-compatible TSV
## Cognate detection 
Scripts: cognate_detection.py, identify_unstable_sets.py, tone_splitting.py, and tone_augmented_lexstat.py
### i) Standard LexStat Cognate detection 
Script: cognate_detection.py 

This script tests multiple clustering thresholds and runs full cognate detection.

Usage:
```bash
# Testing multiple thresholds
python cognate_detection.py input.tsv -o results_dir/ -t 0.50 0.55 0.60 -r 10000

# Single threshold
python cognate_detection.py input.tsv -o results_dir/ -t 0.55 -r 100000
```

Output: lexstat_t0.55.tsv
### ii) Tone-Refinement
Script: identify_unstable_sets.py

This script finds cognate sets that may benefit from tone-based refinement.

Usage:
```bash
python identify_unstable_sets.py lexstat_results.tsv -o cognate_analysis.csv --diversity-threshold 0.6 --extract-ids
```

Output: cognate_analysis.csv, unstable_cogids.txt

Script: tone_splitting.py

This script refines unstable cognate sets using tone pattern information. 

Usage:
```bash
# Split using tone patterns
python tone_splitting.py lexstat_results.tsv tone_patterns.csv -o refined.tsv --unstable-ids unstable_cogids.txt --tone-threshold 0.6 
```

Output: refined.tsv containing the cognate sets refined by tone
### iii) Tone-Integration
Script: tone_augmented_lexstat.py

This script encodes tone directly into segment representation. 

Usage:
```bash
python tone_augmented_lexstat.py wordlist.tsv tones.csv -o tone_augmented_output.tsv -t 0.55 -r 10000 
```

Output: tone_augmented_output.tsv containing cognate sets with tone-aware clustering
## Convert to Binary Matrix for BEAST
Script: convert_for_beast.py

This script converts cognate data to binary matrix format for Bayesian phylogenetic analysis. 

Usage:
```bash
python convert_for_beast.py lexstat_results.tsv
```

Output: ijoid_beast_cognates_binary.csv (binary matrix) and ijoid_beast_cognates_binary.nex (NEXUS format for BEAST)
## Visualize Phylogenetic Trees
Script: visualizer.py

This script creates publication-quality visualizations of BEAST MCC trees with posterior probabilities and color-coded labels.

Usage:
```bash
# Edit paths in script, then run:
python visualizer.py
```

Output: PDF and PNG files with colored tips and posterior probabilities 
