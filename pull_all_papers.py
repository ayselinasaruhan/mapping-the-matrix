# Pulls all papers from PubMed Central (PMC) that match a specific query and saves their IDs to a text file. It avoids duplicates by checking against existing IDs in the file.

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET

filename = "pmc_list_huge.txt"
batch_size = 10000  

# Generate all 2-letter combinations (aa, ab, ac... zz)
alphabet = "abcdefghijklmnopqrstuvwxyz"
combinations = [a + b for a in alphabet for b in alphabet]

print("Starting deep continuous automated PMC harvest (2-letter prefixes)...")

# --- SAFEGUARD: Load existing IDs first ---
existing_ids = set()
if os.path.exists(filename):
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned:
                existing_ids.add(cleaned)
    print(f"🔄 Found {len(existing_ids)} existing IDs in your file. Skipping duplicates.")

all_new_ids = []

try:
    # --- RUN CONTINUOUS ESEARCH PARTITIONS ---
    for combo in combinations:
        # Search query matching open-access papers starting with the 2-letter combo
        query = f"open access[Filter] AND {combo}*[Title]"
        print(f"\n📡 Running Request (Query: Title starting with '{combo.upper()}')...")
        
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={query}&retmax={batch_size}&retmode=xml"
        
        try:
            response = requests.get(search_url, timeout=15)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                batch_ids = [id_elem.text for id_elem in root.findall(".//IdList/Id") if id_elem.text]
                
                if not batch_ids:
                    print(f"No papers returned for prefix: {combo.upper()}")
                    continue
                    
                new_additions_this_batch = 0
                for raw_id in batch_ids:
                    formatted_id = f"PMC{raw_id}"
                    if formatted_id not in existing_ids and formatted_id not in all_new_ids:
                        all_new_ids.append(formatted_id)
                        new_additions_this_batch += 1
                
                print(f"   -> Loaded {len(batch_ids):,} IDs (Added {new_additions_this_batch:,} brand new unique IDs).")
                print(f"   -> Total unique IDs collected this run: {len(all_new_ids):,}")
                
                # Instantly save progress to file
                if all_new_ids:
                    with open(filename, "a", encoding="utf-8") as f:
                        for pmc_id in all_new_ids:
                            f.write(f"{pmc_id}\n")
                            existing_ids.add(pmc_id)
                    all_new_ids.clear()  # Clear memory cache
                
                # Standard delay to avoid API rate limit blocks
                time.sleep(1.5)
            else:
                print(f"⚠️ API returned status code {response.status_code}")
        except Exception as e:
            print(f"⚠️ Network error on partition '{combo.upper()}': {e}")
            time.sleep(3.0)

except KeyboardInterrupt:
    print("\n🛑 Process paused manually by user.")

# --- FINAL STATUS UPDATE ---
print(f"\n🎉 Process complete! Your file '{filename}' currently has {len(existing_ids)} total unique items stored safely.")