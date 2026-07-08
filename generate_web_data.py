# Generates a structured JSON file for the citation network, optimized for fast loading in the interactive visualization. It processes the raw citation data, normalizes it, and assigns fixed coordinates to each node based on a grid layout.
# This one is much quicker than interactive_network.py, so it is currently the main way to generate the graph.

import json
import os
import pandas as pd
import math
import time
from google import genai

print("🚀 Structuring data into optimized fast-loading clusters...")

db_file = "citation_network.json"
main_df = pd.read_json(db_file)

# Instant vectorized explosion
main_df = main_df.explode("References").dropna(subset=["References"])
ref_df = pd.json_normalize(main_df["References"])
ref_df.index = main_df.index

# Safe column fallback mapping
ref_df["Source_Paper_PMC"] = main_df["Source_Paper_PMC"].astype(str)
match_col = "Match_Key" if "Match_Key" in ref_df.columns else "pmid_cited"

df = pd.DataFrame()
df["Source_Paper_PMC"] = ref_df["Source_Paper_PMC"]
df["Match_Key"] = ref_df[match_col].astype(str)
df["article_title"] = ref_df.get("article_title", "Unknown Title").fillna("Unknown Title")
df["name"] = ref_df.get("name", "Unknown Author").fillna("Unknown Author")
df["year"] = ref_df.get("year", "Unknown Year").fillna("Unknown Year")

# --- CHRONOLOGICAL TIMELINE LAYOUT + GEMINI AI SUMMARIES ---
unique_hubs = list(df["Source_Paper_PMC"].unique())
key_to_hubs = df.groupby("Match_Key")["Source_Paper_PMC"].apply(set).to_dict()

# Initialize the Gemini client safely
api_key = os.environ.get("GEMINI_API_KEY") or "PASTE_YOUR_ACTUAL_GEMINI_API_KEY_HERE"
client = genai.Client(api_key=api_key)

hub_years = {}
hub_summaries = {}

print("🤖 Querying Gemini API for cluster summaries...")

for idx, hub in enumerate(unique_hubs):
    # Filter using the unified df
    hub_rows = df[df["Source_Paper_PMC"] == hub]
    
    if not hub_rows.empty:
        try:
            year_val = int(float(str(hub_rows.iloc[0]["Year"]).split('.')[0]))
        except:
            year_val = 2020
    else:
        year_val = 2020
    hub_years[hub] = year_val

    # FORCE ONLY THE FIRST 3 HUBS TO CALL AI FOR TESTING
    if idx < 3:
        connected_titles = hub_rows["article_title"].unique()[:15]
        context_text = "\n- ".join(connected_titles)
        
        prompt = f"""
        Review these research titles for PMC ID {hub} ({year_val}):
        {context_text}
        Provide a 3-bullet-point executive summary in clean HTML format (using <ul> and <li> tags). Do not use markdown backticks.
        """
        
        try:
            print(f" -> Analyzing Hub {idx+1}/3 ({hub}) via Gemini...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            hub_summaries[hub] = response.text
            print("⏳ Pacing free tier... resting 4 seconds...")
            time.sleep(4)
        except Exception as e:
            print(f" ⚠️ AI Skip for {hub}: {e}")
            hub_summaries[hub] = "<ul><li>Summary currently unavailable.</li></ul>"
    else:
        # Give remaining hubs quick mock text instantly
        hub_summaries[hub] = "<ul><li>[AI Analysis Pending for this cluster]</li></ul>"

sorted_hubs = sorted(unique_hubs, key=lambda h: hub_years[h])
hub_positions = {}

x_spacing = 3500  # Horizontal distance between eras
y_spacing = 2000  # Vertical spacing variation  

for idx, hub in enumerate(sorted_hubs):
    x_pos = idx * x_spacing
    y_pos = (idx % 3 - 1) * y_spacing 
    hub_positions[hub] = {"x": float(x_pos), "y": float(y_pos)}

# --- INITIALIZE DATA STRUCTURES ONCE ---
hub_spacing = 4000
elements = []
seen_nodes = set()
reference_counts = {}

print("🌟 Building fixed coordinates layout...")
# -------------------------------------------------------------

print("📦 Building fixed coordinates layout...")
for _, row in df.iterrows():
    # Force string conversion immediately to prevent float/NaN skips
    source = str(row["Source_Paper_PMC"]).strip()
    target = str(row["Match_Key"]).strip()

    if not source or not target or source in ["nan", "None", ""] or target in ["nan", "None", ""]:
        continue
    
    if not source or not target or source == "nan" or target == "nan":
        continue
        
    title = str(row["article_title"]).replace('"', "'")
    author = str(row["name"])
    year = str(row["year"]).split('.')[0]
    
    # Hub Node Construction
    if source not in seen_nodes:
        pos = hub_positions.get(source, {"x": 0, "y": 0})
        elements.append({
            "data": {
                "id": source, 
                "type": "hub", 
                "label": source, 
                "tooltip": f"🌟 CORE HUB: {source}",
                "summary": hub_summaries.get(source, "")  # <-- ADD THIS LINE HERE!
            },
            "position": {"x": pos["x"], "y": pos["y"]}
    })
    seen_nodes.add(source)
    reference_counts[source] = 0
        
    # Reference Node
    if target not in seen_nodes:
        hubs_count = len(key_to_hubs.get(target, set()))
        node_type = "shared" if hubs_count > 1 else "standard"
        
        base_pos = hub_positions.get(source, {"x": 0, "y": 0})
        count = reference_counts.get(source, 0)
        
        radius = 500 + (count % 20) * 40  
        angle = count * 0.12  
        
        node_x = base_pos["x"] + radius * math.cos(angle)
        node_y = base_pos["y"] + radius * math.sin(angle)
        
        elements.append({
            "data": {
                "id": target, 
                "type": node_type, 
                "label": "", 
                "tooltip": f"📄 {title}\n👤 {author} ({year})\n🔗 Connected to {hubs_count} hub(s)"
            },
            "position": {"x": node_x, "y": node_y}
        })
        seen_nodes.add(target)
        reference_counts[source] = count + 1
        
    elements.append({"data": {"id": f"e_{source}_{target}", "source": source, "target": target}})

print("\n🔍 --- DATA GENERATION CHECK ---")
print(f"Total graph elements generated: {len(elements)}")
if elements:
    print("\n👀 Sample of the first element structure:")
    import pprint
    pprint.pprint(elements[0])
print("---------------------------------\n")

with open("network_data.js", "w", encoding="utf-8") as f:
    f.write(f"const graphElements = {json.dumps(elements)};")

print(f"🎉 Done! Successfully mapped {len(seen_nodes)} total components.")