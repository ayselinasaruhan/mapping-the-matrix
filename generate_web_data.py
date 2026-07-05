# Generates a structured JSON file for the citation network, optimized for fast loading in the interactive visualization. It processes the raw citation data, normalizes it, and assigns fixed coordinates to each node based on a grid layout.
# This one is much quicker than interactive_network.py, so it is currently the main way to generate the graph.

import json
import os
import pandas as pd
import math

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

key_to_hubs = df.groupby("Match_Key")["Source_Paper_PMC"].apply(set).to_dict()
unique_hubs = list(df["Source_Paper_PMC"].unique())

num_hubs = len(unique_hubs)
grid_size = math.ceil(math.sqrt(num_hubs))
hub_spacing = 4000  

hub_positions = {}
for idx, hub in enumerate(unique_hubs):
    row_idx = idx // grid_size
    col_idx = idx % grid_size
    hub_positions[hub] = {
        "x": col_idx * hub_spacing,
        "y": row_idx * hub_spacing
    }

elements = []
seen_nodes = set()
reference_counts = {}

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
    
    # Hub Node
    if source not in seen_nodes:
        pos = hub_positions.get(source, {"x": 0, "y": 0})
        elements.append({
            "data": {"id": source, "type": "hub", "label": source, "tooltip": f"⭐ CORE HUB: {source}"},
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

with open("network_data.js", "w", encoding="utf-8") as f:
    f.write(f"const graphElements = {json.dumps(elements)};")

print(f"🎉 Done! Successfully mapped {len(seen_nodes)} total components.")