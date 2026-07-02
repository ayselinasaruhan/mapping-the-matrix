import json
import os
import pandas as pd

print("🚀 Unpacking and structuralizing data for Cytoscape web rendering...")

db_file = "citation_network.json"
main_df = pd.read_json(db_file)

# Vectorized explosion (Instant)
main_df = main_df.explode("References").dropna(subset=["References"])
ref_df = pd.json_normalize(main_df["References"])
ref_df.index = main_df.index
ref_df["Source_Paper_PMC"] = main_df["Source_Paper_PMC"].astype(str)
df = ref_df[["Source_Paper_PMC", "Match_Key", "pmid_cited", "article_title", "name", "year", "journal"]]

# Pre-calculate shared hub counts to assign colors instantly
key_to_hubs = df.groupby("Match_Key")["Source_Paper_PMC"].apply(set).to_dict()

elements = []
seen_nodes = set()

print("📦 Creating optimized web JSON mapping...")
for _, row in df.iterrows():
    source = row["Source_Paper_PMC"]
    target = row["Match_Key"]
    
    # Clean up metadata
    title = str(row.get("article_title", "Unknown")).replace('"', "'")
    author = str(row.get("name", "Unknown"))
    year = str(row.get("year", "Unknown")).split('.')[0]
    
    # 1. Add Source Node
    if source not in seen_nodes:
        elements.append({
            "data": {"id": source, "type": "hub", "label": source, "tooltip": f"⭐ CORE HUB: {source}"}
        })
        seen_nodes.add(source)
        
    # 2. Add Reference Node
    if target not in seen_nodes:
        hubs_count = len(key_to_hubs.get(target, set()))
        node_type = "shared" if hubs_count > 1 else "standard"
        elements.append({
            "data": {
                "id": target, 
                "type": node_type, 
                "label": "", 
                "tooltip": f"📄 {title}\n👤 {author} ({year})\n🔗 Connected to {hubs_count} hub(s)"
            }
        })
        seen_nodes.add(target)
        
    # 3. Add Edge Link
    elements.append({"data": {"source": source, "target": target}})

# Write data out directly as a JavaScript variable file
with open("network_data.js", "w", encoding="utf-8") as f:
    f.write(f"const graphElements = {json.dumps(elements)};")

print(f"🎉 Generated network data for {len(seen_nodes)} nodes in seconds flat!")