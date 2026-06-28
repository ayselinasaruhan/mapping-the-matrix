import pubmed_parser as pp
import urllib.request
import xml.etree.ElementTree as ET
import ssl
import os
import csv

target_pmcid = "PMC8001234" 
pure_numeric_id = target_pmcid.replace("PMC", "")

print(f"=== PROCESSING COHERENT NETWORK FOR: {target_pmcid} ===")

temp_xml = "downloaded_paper.xml"
url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pure_numeric_id}&retmode=xml"

try:
    print(f"\nDownloading official Open-Access XML...")
    
    context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, temp_xml)
    
    # --- STEP 1: PARSE METADATA & FIX MISSING TITLE ---
    pmc_data = pp.parse_pubmed_xml(temp_xml)
    title = pmc_data.get('title')
    
    if not title or title.lower() == 'none':
        try:
            tree = ET.parse(temp_xml)
            root = tree.getroot()
            title_element = root.find(".//article-title")
            if title_element is not None:
                title = "".join(title_element.itertext()).strip()
        except Exception:
            title = "Unknown Title"

    print("\n--- Main Paper Metadata ---")
    print(f"Title: {title}")

    # --- STEP 2: PARSE CITATIONS ---
    citations = pp.parse_pubmed_references(temp_xml)
    citations = citations if citations is not None else []
    
    print(f"\nFound {len(citations)} references. Starting export...")

    # --- STEP 3: EXPORT TO CSV ---
    output_filename = "citation_network.csv"
    
    # Open a new file to write data into
    with open(output_filename, mode="w", newline="", encoding="utf-8") as csv_file:
        # Define the headers (columns) for our spreadsheet
        fieldnames = ["Source_Paper_PMC", "Source_Paper_Title", "Reference_Number", "Cited_Title", "Cited_Journal", "Cited_Year"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        # Write the header row
        writer.writeheader()
        
        # Loop through all 115 citations and write them row by row
        for i, cite in enumerate(citations):
            writer.writerow({
                "Source_Paper_PMC": target_pmcid,
                "Source_Paper_Title": title,
                "Reference_Number": i + 1,
                "Cited_Title": cite.get("article_title"),
                "Cited_Journal": cite.get("journal_title"),
                "Cited_Year": cite.get("year")
            })
            
    print(f"\n🚀 Success! Created file: {output_filename}")
    print("You can now open this file on your computer using Excel or Numbers!")
            
except Exception as e:
    print(f"\nNetwork/Download Error: {e}")

finally:
    if os.path.exists(temp_xml):
        os.remove(temp_xml)