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

        # Convert raw API list to a Pandas DataFrame
        df_new = pd.DataFrame(references)
        
        # 1. Add our core tracker column
        df_new["Source_Paper_PMC"] = pmc_id

        # 2. Drop citations that don't have a PMID (e.g., books, external website links)
        # This guarantees every remaining row can be accurately mapped in your network!
        if "pmid_cited" in df_new.columns:
            df_new = df_new.dropna(subset=["pmid_cited"])
            # Prevent Pandas from turning integer IDs into floats (like 34567.0)
            df_new["pmid_cited"] = df_new["pmid_cited"].astype(str).str.split('.').str[0]
        else:
            print(f"⚠️ Warning: No PMIDs found in reference structure for {pmc_id}")
            continue

        # 3. Keep ONLY your chosen 6 columns
        target_columns = ["Source_Paper_PMC", "pmid_cited", "article_title", "name", "year", "journal"]
        # Safe filtering in case the API completely omitted a column like 'year' for a paper
        existing_columns = [col for col in target_columns if col in df_new.columns]
        df_new = df_new[existing_columns]
        
        # Fill any missing metadata blanks so they look clean in your tooltips
        for meta_col in ["article_title", "name", "year", "journal"]:
            if meta_col in df_new.columns:
                df_new[meta_col] = df_new[meta_col].fillna("Unknown")

        # Append to master CSV
        df_new.to_csv("citation_network.csv", mode='a', header=not os.path.exists("citation_network.csv"), index=False)
        print(f"Successfully saved {len(df_new)} clean PMID references for {pmc_id}!")
        
    except Exception as e:
        print(f"Error parsing {pmc_id}: {e}")

fhand.close()
print("All papers processed!")