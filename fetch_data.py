import os
import pandas as pd
import pubmed_parser as pp
import requests

# 1. Load existing data
if os.path.exists("citation_network.csv"):
    df = pd.read_csv("citation_network.csv")
    completed_ids = set(df["Source_Paper_PMC"].unique())
else:
    completed_ids = set()

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

        df_new = pd.DataFrame(references)
        df_new["Source_Paper_PMC"] = pmc_id
        
        # Append to master CSV
        df_new.to_csv("citation_network.csv", mode='a', header=not os.path.exists("citation_network.csv"), index=False)
        print(f"Successfully saved references for {pmc_id}!")
        
    except Exception as e:
        print(f"Error parsing {pmc_id}: {e}")

fhand.close()
print("All papers processed!")