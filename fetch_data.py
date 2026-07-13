# Gets nested references for a list of PMC IDs and saves them to a JSON file. It avoids duplicates by checking against existing entries in the JSON file.

import os
import pandas as pd
import pubmed_parser as pp
import requests
import json


# 1. Load existing normalized data structures
map_file = "paper_citation_map.json"
lookup_file = "article_lookup.json"

paper_citation_map = {}
article_lookup = {}
completed_ids = set()

# Load Paper Citation Map if it exists
if os.path.exists(map_file) and os.path.getsize(map_file) > 0:
    try:
        with open(map_file, "r", encoding="utf-8") as f:
            paper_citation_map = json.load(f)
            # The keys of this map are the source papers we've already parsed
            completed_ids = set(paper_citation_map.keys())
    except json.JSONDecodeError:
        paper_citation_map = {}

# Load Article Details Lookup Table if it exists
if os.path.exists(lookup_file) and os.path.getsize(lookup_file) > 0:
    try:
        with open(lookup_file, "r", encoding="utf-8") as f:
            article_lookup = json.load(f)
    except json.JSONDecodeError:
        article_lookup = {}

# 2. Open the text file containing IDs
# fhand = open("pmc_list.txt", "r")

# Temporarily limit to the first 150 papers for testing
fhand = open("backup-data/pmc_list_150.txt", "r")
papers_processed = 0
max_papers = 150  # Limit for testing purposes

for line in fhand:
    # Stop if we've reached the limit
    if papers_processed >= max_papers:
        print(f"Reached limit of {max_papers} papers. Stopping.")
        break
    pmc_id = line.strip()
    
    if pmc_id in completed_ids:
        print(f"Skipping {pmc_id}, already processed.")
        continue
    
    papers_processed += 1
        
    print(f"Processing {pmc_id}...")
    
    try:
        # Ask PubMed's official API for this paper's data live over the web
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc_id}&retmode=xml"
        response = requests.get(url)
        
        # Hand the live web content over to the parser
        references = pp.parse_pubmed_references(response.content) 
        
        if not references:
            print(f"No references found for {pmc_id} (might not be open-access).")
            continue

        cleaned_references = []
        
        for ref in references:
            # Clean up raw text inputs from the API parser
            pmid_raw = str(ref.get("pmid_cited", "")).strip().split('.')[0]
            title_raw = str(ref.get("article_title", "")).strip()
            
            # Determine the Hybrid Match Key
            match_key = None
            if pmid_raw and pmid_raw.lower() not in ["nan", "none", "null", ""]:
                match_key = f"PMID_{pmid_raw}"
            else:
                print("This paper has no valid PMID, skipping this reference.")
                continue
                
            # Build the clean structured metadata for this reference
            cleaned_references.append({
                "Match_Key": match_key,
                "pmid_cited": pmid_raw,
                "article_title": title_raw,
                "name": str(ref.get("name", "Unknown Author")),
                "year": str(ref.get("year", "Unknown Year")).split('.')[0],
                "journal": str(ref.get("journal", "Unknown Journal"))
            })

        # Package the main paper connections (File 1 Structure)
        # Gathers just the string match keys for this source paper
        paper_citation_map[pmc_id] = [ref["Match_Key"] for ref in cleaned_references]

        # Package individual reference details (File 2 Structure)
        for ref in cleaned_references:
            key = ref["Match_Key"]
            # Safe checkpoint: only add details if we haven't seen this key before
            if key not in article_lookup:
                article_lookup[key] = {
                    "pmid_cited": ref["pmid_cited"],
                    "article_title": ref["article_title"],
                    "name": ref["name"],
                    "year": ref["year"],
                    "journal": ref["journal"]
                }
            else:
                print(f"Duplicate entry for {key} found, skipping addition to lookup.")

        # Write BOTH beautifully organized files back to disk atomically
        try:
            with open(map_file, "w", encoding="utf-8") as f:
                json.dump(paper_citation_map, f, indent=4)
                
            with open(lookup_file, "w", encoding="utf-8") as f:
                json.dump(article_lookup, f, indent=4)

            print(f" Saved structural map & unique details for {pmc_id}!")
        except Exception as write_err:
            print(f" Disk write issue for {pmc_id}: {write_err}")

    except Exception as e:
        print(f"Error parsing {pmc_id}: {e}")

fhand.close()

print("All papers processed!")
print(f"Total Main Papers stored:   {len(paper_citation_map)}")
print(f"Total Unique PMIDs stored:  {len(article_lookup)}")