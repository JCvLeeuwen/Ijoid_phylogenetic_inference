# review matches and fix them manually

import pandas as pd
import sys
from pathlib import Path

# interactive review
def review_matches(matched_csv, wold_csv, output_csv):

    print("match reviewer")
    print("commands:")
    print("  [enter] - accept match")
    print("  s <text> - search wold and assign")
    print("  n - mark as no match")
    print("  q - quit and save")

    # load data
    matched_df = pd.read_csv(matched_csv)
    wold_df = pd.read_csv(wold_csv)
    
    # get fuzzy matches and unmatched
    needs_review = matched_df[
        (matched_df['MatchMethod'] == 'fuzzy') | 
        (matched_df['MatchMethod'] == 'no_match')
    ].copy()
    
    print(f"total concepts: {len(matched_df)}")
    print(f"need review: {len(needs_review)}\n")
    
    if len(needs_review) == 0:
        print("no concepts need review")
        return
    
    # review each
    reviewed = 0
    changed = 0
    
    for idx, row in needs_review.iterrows():
        print(f"[{reviewed + 1}/{len(needs_review)}]")
        print(f"\nijoid concept: {row['Ijoid_Concept']}")
        
        if row['MatchMethod'] == 'fuzzy':
            print(f"current match: {row['WOLD_Name']}")
            print(f"  id: {row['WOLD_ID']}")
            print(f"  score: {row['BorrowedScore']:.4f}")
            print(f"  confidence: {row['MatchScore']:.2f}")
        else:
            print("current match: none")
        
        # get input
        response = input("\naction ([enter]/s <query>/n/q): ").strip().lower()
        
        if response == 'q':
            print("\nsaving and quitting...")
            break
        elif response == 'n':
            # no match
            matched_df.at[idx, 'MatchMethod'] = 'manual_no_match'
            matched_df.at[idx, 'WOLD_Name'] = None
            matched_df.at[idx, 'WOLD_ID'] = None
            matched_df.at[idx, 'BorrowedScore'] = None
            changed += 1
            print("marked as no match")
        elif response.startswith('s '):
            # search wold
            query = response[2:].strip()
            
            # try as id
            if query.replace('.', '').replace('-', '').isdigit():
                results = wold_df[wold_df['ID'].astype(str) == query]
            else:
                # search by name
                results = wold_df[
                    wold_df['Name'].str.contains(query, case=False, na=False)
                ]
            
            if len(results) == 0:
                print(f"no wold entries found for '{query}'")
            else:
                print(f"\nfound {len(results)} matches:")
                for i, (_, wold_row) in enumerate(results.head(10).iterrows(), 1):
                    print(f"  {i}. {wold_row['ID']} - {wold_row['Name']} "
                          f"(score: {wold_row['BorrowedScore']:.4f})")
                
                # select one
                selection = input("\nselect number (or enter to skip): ").strip()
                
                if selection.isdigit() and 1 <= int(selection) <= len(results):
                    selected = results.iloc[int(selection) - 1]
                    matched_df.at[idx, 'WOLD_Name'] = selected['Name']
                    matched_df.at[idx, 'WOLD_ID'] = selected['ID']
                    matched_df.at[idx, 'BorrowedScore'] = selected['BorrowedScore']
                    matched_df.at[idx, 'MatchScore'] = 1.0
                    matched_df.at[idx, 'MatchMethod'] = 'manual'
                    changed += 1
                    print(f"assigned: {selected['Name']}")
                else:
                    print("skipped")
        elif response == '':
            # accept
            if row['MatchMethod'] == 'fuzzy':
                matched_df.at[idx, 'MatchMethod'] = 'fuzzy_accepted'
            print("accepted")
        else:
            print("invalid command, skipping")
        
        reviewed += 1
    
    # save
    matched_df.to_csv(output_csv, index=False)
    
 
    print("review complete")
    print(f"reviewed: {reviewed}/{len(needs_review)}")
    print(f"changed: {changed}")
    print(f"saved to: {output_csv}")



# main
import argparse

parser = argparse.ArgumentParser(description='review wold matches')
subparsers = parser.add_subparsers(dest='command')

# review
review_parser = subparsers.add_parser('review', help='interactive review')
review_parser.add_argument('matched_csv')
review_parser.add_argument('wold_csv')
review_parser.add_argument('-o', '--output', required=True)


args = parser.parse_args()

if not args.command:
    parser.print_help()
    sys.exit(1)

try:
    if args.command == 'review':
        review_matches(args.matched_csv, args.wold_csv, args.output)
except Exception as e:
    print(f"\nerror: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)