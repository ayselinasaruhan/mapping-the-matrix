import os
import pandas as pd
import pubmed_parser as pp
import requests
import json

# 1. Load existing data
db_file = "citation_network.json"
existing_data = []
completed_ids = set()

# Only try to read if the file exists and is not empty
if os.path.exists(db_file) and os.path.getsize(db_file) > 0:
    with open(db_file, "r", encoding="utf-8") as f:
        try:
            existing_data = json.load(f)
            for item in existing_data:
                if "Source_Paper_PMC" in item:
                    completed_ids.add(str(item["Source_Paper_PMC"]))
        except json.JSONDecodeError:
            # If the file is corrupted or unreadable, start fresh
            existing_data = []

# 2. Open the text file containing IDs
fhand = open("pmc_list.txt", "r")

for line in fhand:
    pmc_id = line.strip()
    
    if pmc_id in completed_ids:
        print(f"Skipping {pmc_id}, already processed.")
        continue
        
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
            elif title_raw and title_raw.lower() not in ["nan", "none", "null", ""]:
                import re
                clean_title = re.sub(r'[^a-zA-Z0-9]', '', title_raw).lower()
                if clean_title:
                    match_key = f"TITLE_{clean_title}"
            
            # Skip this individual citation if it has no usable title or ID
            if not match_key:
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

        # Package the main paper and its nested reference list together
        paper_entry = {
            "Source_Paper_PMC": pmc_id,
            "Total_References_Count": len(cleaned_references),
            "References": cleaned_references
        }

        # Append to master JSON
        existing_data = [item for item in existing_data if str(item["Source_Paper_PMC"]) != str(pmc_id)]
        
        # Append our freshly grabbed paper data to our main memory list
        existing_data.append(paper_entry)
        
        # Write the entire beautifully organized list back to the disk
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)

        print(f"🎉 Successfully stored {len(cleaned_references)} nested references for {pmc_id}!")
        
    except Exception as e:
        print(f"Error parsing {pmc_id}: {e}")

fhand.close()
print("All papers processed!")