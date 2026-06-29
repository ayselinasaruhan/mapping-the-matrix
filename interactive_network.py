import csv
from pyvis.network import Network
import os
import webbrowser
import networkx as nx
import json

print("Restoring full network constellations with unclipped titles...")

# ==========================================
# 🛡️ RESILIENT LINE-BY-LINE PARSER (Bypasses Pandas Tracker Crashes)
# ==========================================
raw_rows = []
try:
    with open("citation_network.csv", mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        headers = next(reader, [])  # Grab header row safely
        for row in reader:
            if row:  # Avoid blank lines
                raw_rows.append(row)
    print(f"✅ Successfully read {len(raw_rows)} raw rows using fallback parsing layout!")
except Exception as e:
    print(f"❌ Failed to read CSV file: {e}")
    exit()

# Dynamic data collection arrays
hubs = set()
edges_to_add = []
citation_to_hubs = {}

for idx, row in enumerate(raw_rows, start=2):
    source = None
    target = None
    
    # 1. Scan everything in this row to extract the core PMC paper ID
    for item in row:
        item_clean = item.strip()
        if item_clean.startswith("PMC") and item_clean != "PMC":
            source = item_clean
            hubs.add(source)
            
    # 2. Extract the best fit string for a target reference title
    potential_targets = []
    for item in row:
        item_clean = item.strip()
        if item_clean and not item_clean.startswith("PMC") and item_clean.lower() != "nan":
            potential_targets.append(item_clean)
            
    # Look for an explicit text flag, or fall back to the longest descriptive string found
    for t in potential_targets:
        if t.startswith("Cited Study"):
            target = t
            break
    if not target and potential_targets:
        potential_targets.sort(key=len, reverse=True)
        target = potential_targets[0]
        
    if not target:
        target = f"Unknown Reference (Line {idx})"
        
    # Map out the valid pairs
    if source:
        edges_to_add.append((source, target))
        if target not in citation_to_hubs:
            citation_to_hubs[target] = set()
        citation_to_hubs[target].add(source)

print(f"🎯 Discovered {len(hubs)} Core Hub papers across your dataset!")
print(f"🔗 Loaded {len(edges_to_add)} total citation links.")

# ==========================================
# 🗺️ INITIALIZE NETWORK VISUALIZATION
# ==========================================
net = Network(height="100vh", width="100%", bgcolor="#1a1a1a", font_color="white")
net.options.nodes = {"font": {"size": 0, "color": "rgba(0,0,0,0)"}}
net.options.interaction = {"hover": True, "tooltipDelay": 50, "hideEdgesOnDrag": False}

# Advanced ForceAtlas2 distribution metrics
physics_config = {
    "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
            "gravitationalConstant": -250,   
            "centralGravity": 0.0005,        
            "springLength": 180,             
            "springConstant": 0.04,
            "damping": 0.5,
            "avoidOverlap": 1
        },
        "stabilization": {
            "enabled": True,
            "iterations": 1500,
            "updateInterval": 50
        }
    }
}
net.set_options(json.dumps(physics_config))

# Populate structure smoothly
for source, target_title in edges_to_add:
    # Add Hub Node
    if source not in net.node_ids:
        net.add_node(
            source, 
            label=source,
            title=f"⭐ CORE HUB:\nCore Research Paper ({source})", 
            color="#E63946", 
            size=50,  
            font={"size": 14, "color": "white"} 
        )

    # Add or update background citation nodes
    if target_title in net.node_ids:
        if net.get_node(target_title).get("color") == "#E63946":
            pass
        elif len(citation_to_hubs.get(target_title, set())) > 1:
            net.get_node(target_title)["color"] = "#FFB703" # Shared item intersection
            net.get_node(target_title)["size"] = 30  
            net.get_node(target_title)["title"] = f"🔗 SHARED CITATION:\n{target_title}"
    else:
        if len(citation_to_hubs.get(target_title, set())) > 1:
            net.add_node(target_title, title=f"🔗 SHARED CITATION:\n{target_title}", color="#FFB703", size=30)
        else:
            net.add_node(target_title, title=target_title, color="#4EA8DE", size=18)
        
    net.add_edge(source, target_title, color="#555555", width=1.5)

# ==========================================
# 📊 CALCULATE GRAPH DYNAMICS
# ==========================================
G = nx.Graph()
G.add_edges_from(edges_to_add)

total_nodes = G.number_of_nodes()
total_edges = G.number_of_edges()

degrees = dict(G.degree())
background_degrees = {k: v for k, v in degrees.items() if k not in hubs}
most_cited_paper = max(background_degrees, key=background_degrees.get) if background_degrees else "None"
max_citations = background_degrees[most_cited_paper] if background_degrees else 0

print("\n--- 📈 GRAPH METRICS REPORT ---")
print(f"Total Unique Papers (Nodes): {total_nodes}")
print(f"Total Citation Links (Edges): {total_edges}")
print(f"Most Influential Background Paper: '{most_cited_paper}' (Cited {max_citations} times!)")
print("--------------------------------\n")

# Save out the compiled map
output_file = "animated_network.html"
net.save_graph(output_file)

with open(output_file, "r", encoding="utf-8") as f:
    html_content = f.read()

js_animation_injection = """
    network.setOptions({
        nodes: {
            chosen: {
                node: function(values, id, selected, hovering) {
                    if (hovering) {
                        values.size = values.size * 1.5;
                        values.borderWidth = 3;
                    }
                }
            }
        }
    });
    network.on("stabilizationIterationsDone", function () {
        network.setOptions({ physics: false });
    });
"""
html_content = html_content.replace("drawGraph();", f"drawGraph();\n{js_animation_injection}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"🚀 Full network map generated! Opening '{output_file}'...")
webbrowser.open("file://" + os.path.abspath(output_file))