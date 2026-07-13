import os
import time
import urllib.request
import xml.etree.ElementTree as ET
import sqlite3

# --- 1. DATABASE SETUP ---
# Connects to the database file (creates it if it doesn't exist)
conn = sqlite3.connect("citation_network.db")
cursor = conn.cursor()

# Create Table 1: Maps main source papers to their cited PMIDs
cursor.execute("""
CREATE TABLE IF NOT EXISTS paper_citations (
    source_pmc TEXT,
    cited_pmid TEXT,
    PRIMARY KEY (source_pmc, cited_pmid)
)
""")

# Create Table 2: Stores the unique registry metadata details for every PMID
cursor.execute("""
CREATE TABLE IF NOT EXISTS article_lookup (
    pmid TEXT PRIMARY KEY,
    title TEXT,
    author TEXT,
    year TEXT,
    journal TEXT
)
""")
conn.commit()


# --- 2. INPUT SEED CONFIGURATION ---
input_file = "archive/pmc_list_150.txt"  # Points to your archived seed IDs

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found. Ensure your target ID list is in the archive folder!")
    exit()

with open(input_file, "r") as f:
    pmc_ids = [line.strip() for line in f if line.strip()]

# Check the database to see which PMC IDs we have already processed
cursor.execute("SELECT DISTINCT source_pmc FROM paper_citations")
completed_ids = set([row[0] for row in cursor.fetchall()])


# --- 3. MAIN EXTRACTION ENGINE ---
max_papers = 1000000  # Scaled up for your milestone milestone target
processed_count = 0

for pmc_id in pmc_ids:
    if processed_count >= max_papers:
        break
    if pmc_id in completed_ids:
        continue

    print(f"Processing paper [{processed_count + 1}]: {pmc_id}...")
    
    # Format the live Entrez utility API URL for full XML data retrieval
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc_id}&retmode=xml"
    
    try:
        response = urllib.request.urlopen(url)
        xml_data = response.read()
    except Exception as e:
        print(f"⚠️ Network error downloading {pmc_id}: {e}")
        time.sleep(2)
        continue

    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"⚠️ XML Parsing failure on {pmc_id}: {e}")
        continue

    cleaned_references = []

    # Parse out individual citation elements from the reference list tags
    for ref in root.findall(".//ref-list/ref"):
        ref_data = {"Match_Key": None, "article_title": "N/A", "name": "N/A", "year": "N/A", "journal": "N/A"}
        
        # Extract the target reference ID (PMID)
        pmid_element = ref.find(".//pub-id[@pub-id-type='pmid']")
        if pmid_element is not None and pmid_element.text:
            ref_data["Match_Key"] = "PMID_" + pmid_element.text.strip()
        else:
            continue  # Skip entries missing a valid structural target tracking key

        # Extract title details
        title_element = ref.find(".//article-title")
        if title_element is not None:
            ref_data["article_title"] = "".join(title_element.itertext()).strip()

        # Extract source journal details
        source_element = ref.find(".//source")
        if source_element is not None:
            ref_data["journal"] = source_element.text.strip()

        # Extract publication year details
        year_element = ref.find(".//year")
        if year_element is not None:
            ref_data["year"] = year_element.text.strip()

        # Extract primary author details
        author_element = ref.find(".//name")
        if author_element is not None:
            surname = author_element.find("surname")
            given_names = author_element.find("given-names")
            s_text = surname.text.strip() if (surname is not None and surname.text) else ""
            g_text = given_names.text.strip() if (given_names is not None and given_names.text) else ""
            ref_data["name"] = f"{s_text}, {g_text}".strip(", ")

        # Prevent duplicate reference keys inside the same paper
        if ref_data["Match_Key"] not in [r["Match_Key"] for r in cleaned_references]:
            cleaned_references.append(ref_data)

    # --- 4. SECURE MULTI-ROW SQL INSERTS ---
    # Write structural tracking links to the mapping table
    for ref in cleaned_references:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO paper_citations (source_pmc, cited_pmid) VALUES (?, ?)",
                (pmc_id, ref["Match_Key"])
            )
        except Exception:
            pass

    # Write unique article details entries to the master registry lookup table
    for ref in cleaned_references:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO article_lookup (pmid, title, author, year, journal) VALUES (?, ?, ?, ?, ?)",
                (ref["Match_Key"], ref["article_title"], ref["name"], ref["year"], ref["journal"])
            )
        except Exception:
            pass

    # Safely commit transactions to the hard drive
    conn.commit()
    processed_count += 1
    time.sleep(0.3)  # Standard API rate protection pacing


# --- 5. DATASET STATUS DASHBOARD ---
cursor.execute("SELECT COUNT(DISTINCT source_pmc) FROM paper_citations")
total_main = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM article_lookup")
total_pmids = cursor.fetchone()[0]

print("\n" + "="*40)
print(" Database Population Run Complete!")
print(f"Total Main Source Papers:   {total_main}")
print(f"Total Unique Registry PMIDs: {total_pmids}")
print("="*40)

conn.close()