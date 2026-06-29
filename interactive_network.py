import csv
from pyvis.network import Network
import os
import webbrowser
import networkx as nx
import json
import pandas as pd
import re

print("🌌 Building bulletproof PMID-mapped network universe...")

if not os.path.exists("citation_network.csv"):
    print("❌ Error: citation_network.csv not found! Run fetch_data.py first.")
    exit()

# 1. LOAD CLEAN DATA
df = pd.read_csv("citation_network.csv")

# Clean up basic identifiers
df["Source_Paper_PMC"] = df["Source_Paper_PMC"].astype(str).str.strip()

# Create a robust function to generate matching keys
def generate_match_key(row):
    pmid = str(row.get("pmid_cited", "")).strip().split('.')[0]
    title = str(row.get("article_title", "")).strip()
    
    # Pathway A: Use PMID if it's valid
    if pmid and pmid.lower() not in ["nan", "none", "null", ""]:
        return f"PMID_{pmid}"
    
    # Pathway B: Fallback to normalized title string (lowercase, alphanumeric only)
    if title and title.lower() not in ["nan", "none", "null", ""]:
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
        if clean_title:
            return f"TITLE_{clean_title}"
            
    return None

# Apply the hybrid match key mapping
df["Match_Key"] = df.apply(generate_match_key, axis=1)

# Drop rows that have absolutely zero identifiable markers
df = df.dropna(subset=["Source_Paper_PMC", "Match_Key"])
df = df[~df["Source_Paper_PMC"].str.lower().isin(["nan", "none", "null", ""])]

if df.empty:
    print("❌ Error: No valid rows left after hybrid data matching! Check your CSV entries.")
    exit()

# Map out cross-reference intersections using our hybrid keys
key_to_hubs = df.groupby("Match_Key")["Source_Paper_PMC"].apply(set).to_dict()
unique_hubs = set(df["Source_Paper_PMC"].unique())

# 2. INITIALIZE VISUALIZATION
net = Network(height="100vh", width="100%", bgcolor="#1a1a1a", font_color="white")
net.options.nodes = {"font": {"size": 0, "color": "rgba(0,0,0,0)"}} # Hides raw labels for a clean starry look
net.options.interaction = {"hover": True, "tooltipDelay": 50}

physics_config = {
    "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {"gravitationalConstant": -150, "centralGravity": 0.002, "springLength": 150, "avoidOverlap": 1},
        "stabilization": {"enabled": True, "iterations": 1000}
    }
}
net.set_options(json.dumps(physics_config))

# 3. POPULATE NODES AND EDGES
source_hub_count = 0
for _, row in df.iterrows():
    source = row["Source_Paper_PMC"]
    target_pmid = row["Match_Key"]

    # Fill descriptive blanks for tooltips
    pmid_raw = str(row.get("pmid_cited", "Unknown")).split('.')[0]
    pmid_display = "Not Provided" if pmid_raw.lower() in ["nan", "none", ""] else pmid_raw
    
    title_clean = str(row.get("article_title", "Unknown Title")).replace('"', "'")
    name_clean = str(row.get("name", "Unknown Author"))
    year_clean = str(row.get("year", "Unknown Year")).split('.')[0]
    journal_clean = str(row.get("journal", "Unknown Journal"))
    
    # Construct a beautiful, clear hover tooltip using your saved metadata
    tooltip_text = (
        f"\n📄 Title: {row['article_title']}\n"
        f"\n🆔 PMID: {target_pmid}\n"
        f"\n👤 Author: {row['name']}\n"
        f"\n📅 Year: {row['year']}\n"
        f"\n📖 Journal: {row['journal']}"
    )

    # Add the Source Hub Node (Red Star) & count # of Soure Hubs
    if source not in net.node_ids:
        source_hub_count = source_hub_count + 1
        net.add_node(
            source, 
            label=source,
            title=f"⭐ CORE HUB:\nPMC ID: {source}", 
            color="#E63946", 
            size=45,
            font={"size": 14, "color": "white"}
        )

    # Add or update the Background Reference Node
    sharing_hubs = key_to_hubs.get(target_pmid, set())
    
    if target_pmid in net.node_ids:
        # If it's already a hub node, leave its formatting alone
        if net.get_node(target_pmid).get("color") == "#E63946":
            pass
        # Turn it yellow if it's hit by more than one core paper
        elif len(sharing_hubs) > 1:
            net.get_node(target_pmid)["color"] = "#FFB703"
            net.get_node(target_pmid)["size"] = 28
            net.get_node(target_pmid)["title"] = f"🔗 SHARED CITATION ({len(sharing_hubs)} Hubs):\n" + tooltip_text
    else:
        # Standard blue node for unique single citations, yellow for shared discoveries
        if len(sharing_hubs) > 1:
            net.add_node(target_pmid, title=f"🔗 SHARED CITATION ({len(sharing_hubs)} Hubs):\n" + tooltip_text, color="#FFB703", size=28)
        else:
            net.add_node(target_pmid, title=tooltip_text, color="#4EA8DE", size=15)

    # Establish the link
    net.add_edge(source, target_pmid, color="#555555", width=1)

# 4. CALCULATE GRAPH METRICS
G = nx.from_pandas_edgelist(df, source="Source_Paper_PMC", target="pmid_cited")
degrees = dict(G.degree())
background_degrees = {k: v for k, v in degrees.items() if k not in unique_hubs}

print("\n--- 📈 UPDATED GRAPH METRICS REPORT ---")
print(f"Total Unique Nodes in Map: {G.number_of_nodes()}")
print(f"Total Source Hub Nodes: {source_hub_count}")
print(f"Total Citation Connections: {G.number_of_edges()}")
if background_degrees:
    top_pmid = max(background_degrees, key=background_degrees.get)
    top_title = df[df["pmid_cited"] == top_pmid]["article_title"].values[0]
    print(f"Most Influential Shared Reference: PMID {top_pmid}")
    print(f"↳ Title: '{top_title}' (Cited by {background_degrees[top_pmid]} of your core papers!)")
print("---------------------------------------\n")

# 5. SAVE AND OPEN VISUALIZATION
output_file = "animated_network.html"
net.save_graph(output_file)

# Inject custom auto-freeze physics animations
with open(output_file, "r", encoding="utf-8") as f:
    html = f.read()
js_inject = """
    network.setOptions({ nodes: { chosen: { node: function(v, id, s, h) { if (h) { v.size = v.size * 1.4; v.borderWidth = 2; } } } } });
    network.on("stabilizationIterationsDone", function () { network.setOptions({ physics: false }); });
"""
html = html.replace("drawGraph();", f"drawGraph();\n{js_inject}")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"🚀 Success! Opening clean interactive visualization window...")
webbrowser.open("file://" + os.path.abspath(output_file))