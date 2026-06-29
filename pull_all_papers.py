import os
import time
import requests
import xml.etree.ElementTree as ET

query = "Artificial Intelligence AND Human Cognition AND open access[Filter]"
batch_size = 2000  
filename = "pmc_list.txt"

# --- SAFEGUARD: Load existing IDs first to avoid duplicates ---
existing_ids = set()
if os.path.exists(filename):
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned:
                existing_ids.add(cleaned)
    print(f"🔄 Found {len(existing_ids)} existing IDs in your file. Safeguard active: skipping duplicates.")

all_new_ids = []
retstart = 0

print("📡 Beginning batched download of all matching PMC IDs...")

while True:
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={query}&retmax={batch_size}&retstart={retstart}&retmode=xml"
    
    try:
        response = requests.get(search_url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            batch_ids = [id_elem.text for id_elem in root.findall(".//IdList/Id") if id_elem.text]
            
            if not batch_ids:
                break
                
            # Process and attach "PMC" prefix while keeping an eye out for duplicates
            for raw_id in batch_ids:
                formatted_id = f"PMC{raw_id}"
                if formatted_id not in existing_ids and formatted_id not in all_new_ids:
                    all_new_ids.append(formatted_id)
            
            print(f" Loaded batch starting at {retstart}... New unique IDs found this run: {len(all_new_ids)}")
            
            if len(batch_ids) < batch_size:
                break
                
            retstart += batch_size
            time.sleep(1.0)
        else:
            time.sleep(3.0)
    except Exception as e:
        time.sleep(5.0)

if not all_new_ids:
    print("\n🤷 No new unique papers found that weren't already in your list!")
else:
    print(f"\n✍️ Appending {len(all_new_ids)} new unique IDs to {filename}...")
    
    # Open in append mode ("a") so we don't destroy your previous list items
    with open(filename, "a", encoding="utf-8") as f:
        for pmc_id in all_new_ids:
            f.write(f"{pmc_id}\n")
        f.flush()            
        os.fsync(f.fileno()) 

    print(f"🎉 Complete! Checked your file and everything is beautifully structured.")