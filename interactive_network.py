import pandas as pd
from pyvis.network import Network
import os
import webbrowser
import networkx as nx
import json

print("Restoring full network constellations with unclipped titles...")

# 1. LOAD DATA
df = pd.read_csv("citation_network.csv")
hubs = df["Source_Paper_PMC"].unique().tolist()

def get_target_title(row):
    for col in ["Cited_Title", "title", "article_title"]:
        if col in row and pd.notnull(row[col]):
            return str(row[col]).strip()
    return f"Unknown Reference (ID: {row.get('pmid', row.get('Reference_Number', 'Unknown'))})"

# ==========================================
# ADVANCED MAPPER: TRUE SHARED CITATION CALCULATION
# ==========================================
citation_to_hubs = {}
for _, row in df.iterrows():
    source = str(row["Source_Paper_PMC"]).strip()
    if not source or source == "nan":
        continue
    target = get_target_title(row)
    
    if target not in citation_to_hubs:
        citation_to_hubs[target] = set()
    citation_to_hubs[target].add(source)

# 2. INITIALIZE NETWORK
net = Network(height="100vh", width="100%", bgcolor="#1a1a1a", font_color="white")

net.options.nodes = {
    "font": {
        "size": 0,          
        "color": "rgba(0,0,0,0)"  
    }
}

net.options.interaction = {
    "hover": True,
    "tooltipDelay": 50,
    "hideEdgesOnDrag": False
}

# ForceAtlas2 solver with slashed central gravity
physics_config = {
    "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
            "gravitationalConstant": -100,
            "centralGravity": 0.005,
            "springLength": 140,      # Slightly longer springs to accommodate larger dots
            "springConstant": 0.06,
            "damping": 0.4,
            "avoidOverlap": 1
        },
        "stabilization": {
            "enabled": True,
            "iterations": 2000,
            "updateInterval": 50
        }
    }
}
net.set_options(json.dumps(physics_config))

# 4. POPULATE STRUCTURE (With scaled-up node sizes!)
for _, row in df.iterrows():
    source = str(row["Source_Paper_PMC"]).strip()
    
    if not source or source == "nan":
        continue
        
    target_title = get_target_title(row)

    # Add Hub Node (Scaled up from 28 to 45)
    if source in hubs:
        if "Source_Paper_Title" in df.columns and pd.notnull(df[df["Source_Paper_PMC"] == source]["Source_Paper_Title"].iloc[0]):
            hub_title = df[df["Source_Paper_PMC"] == source]["Source_Paper_Title"].iloc[0]
        else:
            hub_title = f"Core Research Paper ({source})"
            
        net.add_node(
            source, 
            label=source,
            title=f"⭐ CORE HUB:\n{hub_title}", 
            color="#E63946", 
            size=45,  # 👈 Much bolder central presence
            font={"size": 14, "color": "white"} 
        )

    # Add or update citation nodes
    if target_title in net.node_ids:
        if net.get_node(target_title).get("color") == "#E63946":
            pass
        elif len(citation_to_hubs.get(target_title, set())) > 1:
            net.get_node(target_title)["color"] = "#FFB703"
            net.get_node(target_title)["size"] = 28  # 👈 Scaled up shared nodes
            net.get_node(target_title)["title"] = f"🔗 SHARED CITATION:\n{target_title}"
    else:
        if len(citation_to_hubs.get(target_title, set())) > 1:
            net.add_node(
                target_title, 
                title=f"🔗 SHARED CITATION:\n{target_title}", 
                color="#FFB703", 
                size=28
            )
        else:
            # Standard Blue Node (Scaled up from 10 to 20)
            net.add_node(
                target_title, 
                title=target_title, 
                color="#4EA8DE", 
                size=20  # 👈 Highly visible from zoomed-out view
            )
        
    # Thicker edges (width=2) so lines don't vanish at distance
    net.add_edge(source, target_title, color="#555555", width=2)

# ==========================================
# GRAPH METRICS CALCULATOR
# ==========================================
G = nx.Graph()
for _, row in df.iterrows():
    source = str(row["Source_Paper_PMC"]).strip()
    if not source or source == "nan":
        continue
    target_title = get_target_title(row)
    G.add_edge(source, target_title)

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

# ==========================================
# 5. SAVE AND INJECT TRANSITIONS WITH PHYSICS FREEZE
# ==========================================
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

print(f"\n🚀 Full network restored! Opening '{output_file}'...")
webbrowser.open("file://" + os.path.abspath(output_file))