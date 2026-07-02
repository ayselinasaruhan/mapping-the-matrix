import json
from pyvis.network import Network
import os
import webbrowser
import networkx as nx
import pandas as pd

print("🌌 Building high-performance PMID-mapped network universe...")

if not os.path.exists("citation_network.json"):
    print("❌ Error: citation_network.json not found! Run fetch_data.py first.")
    exit()

# 1. LOAD CLEAN DATA
db_file = "citation_network.json"
main_df = pd.read_json(db_file)
print(f"📋 Loaded DataFrame: {len(main_df)} unique master articles currently on file.")

print("⚡ Unpacking reference records via vectorized explosion...")
# Explode the nested 'References' column instantly without raw Python loops
main_df = main_df.explode("References").dropna(subset=["References"])

# Flatten out the exploded dictionary objects into clean columns
print("🧹 Normalizing metadata structures...")
ref_df = pd.json_normalize(main_df["References"])

# Sync index tracking to match the source papers perfectly
ref_df.index = main_df.index
ref_df["Source_Paper_PMC"] = main_df["Source_Paper_PMC"].astype(str)

# Construct our final working DataFrame cleanly
df = ref_df[["Source_Paper_PMC", "Match_Key", "pmid_cited", "article_title", "name", "year", "journal"]]
print(f"✅ Fast-unpack complete: Processed {len(df)} total data pathways.")

# Map out cross-reference intersections using our hybrid keys
key_to_hubs = df.groupby("Match_Key")["Source_Paper_PMC"].apply(set).to_dict()
unique_hubs = set(df["Source_Paper_PMC"].unique())

# 2. INITIALIZE VISUALIZATION
net = Network(height="100vh", width="100%", bgcolor="#1a1a1a", font_color="white")
net.options.nodes = {"font": {"size": 0, "color": "rgba(0,0,0,0)"}} 
net.options.interaction = {"hover": True, "tooltipDelay": 50}

# 🛠️ PERFORMANCE OVERHAUL CONFIGURATION
# Switched solver to standard barnesHut and capped iterations to prevent endless web loops
physics_config = {
  "physics": {
    "solver": "barnesHut",
    "barnesHut": {
      "gravitationalConstant": -3000,
      "centralGravity": 0.3,
      "springLength": 95,
      "springConstant": 0.04,
      "damping": 0.09,
      "avoidOverlap": 0.2
    },
    "stabilization": {
      "enabled": True,
      "iterations": 150,
      "updateInterval": 25
    }
  },
  "interaction": {
    "hideEdgesOnDrag": True,
    "hideEdgesOnZoom": True,
    "navigationButtons": True
  }
}
net.set_options(json.dumps(physics_config))

# 3. POPULATE NODES AND EDGES
source_hub_count = 0
for _, row in df.iterrows():
    source = row["Source_Paper_PMC"]
    target_pmid = row["Match_Key"]

    title_clean = str(row.get("article_title", "Unknown Title")).replace('"', "'")
    tooltip_text = (
        f"\n📄 Title: {title_clean}\n"
        f"\n🆔 PMID: {target_pmid}\n"
        f"\n👤 Author: {row['name']}\n"
        f"\n📅 Year: {row['year']}\n"
        f"\n📖 Journal: {row['journal']}"
    )

    if source not in net.node_ids:
        source_hub_count += 1
        net.add_node(
            source, 
            label=source,
            title=f"⭐ CORE HUB:\nPMC ID: {source}", 
            color="#E63946", 
            size=45,
            font={"size": 14, "color": "white"}
        )

    sharing_hubs = key_to_hubs.get(target_pmid, set())
    
    if target_pmid in net.node_ids:
        if net.get_node(target_pmid).get("color") == "#E63946":
            pass
        elif len(sharing_hubs) > 1:
            net.get_node(target_pmid)["color"] = "#FFB703"
            net.get_node(target_pmid)["size"] = 28
            net.get_node(target_pmid)["title"] = f"🔗 SHARED CITATION ({len(sharing_hubs)} Hubs):\n" + tooltip_text
    else:
        if len(sharing_hubs) > 1:
            net.add_node(target_pmid, title=f"🔗 SHARED CITATION ({len(sharing_hubs)} Hubs):\n" + tooltip_text, color="#FFB703", size=28)
        else:
            net.add_node(target_pmid, title=tooltip_text, color="#4EA8DE", size=15)

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
    top_titles = df[df["pmid_cited"] == top_pmid]["article_title"].values
    if len(top_titles) > 0:
        print(f"Most Influential Shared Reference: PMID {top_pmid}")
        print(f"↳ Title: '{top_titles[0]}' (Cited by {background_degrees[top_pmid]} of your core papers!)")
print("---------------------------------------\n")

# 5. SAVE AND OPEN VISUALIZATION
output_file = "animated_network.html"
net.save_graph(output_file)

# 🛠️ IMPROVED INJECTION: Immediate freeze post-stabilization
with open(output_file, "r", encoding="utf-8") as f:
    html = f.read()

js_inject = """
    network.setOptions({ nodes: { chosen: { node: function(v, id, s, h) { if (h) { v.size = v.size * 1.4; v.borderWidth = 2; } } } } });
    network.on("stabilizationIterationsDone", function () { 
        network.setOptions({ physics: false }); 
        console.log("⚡ Physics Engine Frozen for Speed!");
    });
"""
html = html.replace("drawGraph();", f"drawGraph();\n{js_inject}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"🚀 Success! Opening optimized interactive visualization...")
webbrowser.open("file://" + os.path.abspath(output_file))