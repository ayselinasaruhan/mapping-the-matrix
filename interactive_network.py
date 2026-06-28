import pandas as pd
from pyvis.network import Network
import os
import webbrowser

print("Restoring full network constellations with unclipped titles...")

# 1. LOAD DATA
df = pd.read_csv("citation_network.csv")
hubs = df["Source_Paper_PMC"].unique().tolist()

# 2. INITIALIZE NETWORK
net = Network(height="100vh", width="100%", bgcolor="#1a1a1a", font_color="white")

# 3. FORCE-KILL VISIBLE LABEL TEXT CLUTTER GLOBALLY
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

# 4. POPULATE STRUCTURE (Fully restored loop)
for _, row in df.iterrows():
    source = str(row["Source_Paper_PMC"])
    # Grabs the full, uncut title for the hover tooltip
    target_title = str(row["Cited_Title"]).strip() if pd.notnull(row["Cited_Title"]) else f"Unknown Reference (PMID: {row['Reference_Number']})"

    # Add Hub Node
    if source in hubs:
        hub_title = df[df["Source_Paper_PMC"] == source]["Source_Paper_Title"].iloc[0]
        net.add_node(
            source, 
            label=source,
            title=f"⭐ CORE HUB:\n{hub_title}", 
            color="#E63946", 
            size=28,
            font={"size": 14, "color": "white"} 
        )

    # Add or update citation nodes
    if target_title in net.node_ids:
        if net.get_node(target_title).get("color") != "#E63946":
            net.get_node(target_title)["color"] = "#FFB703"
            net.get_node(target_title)["size"] = 18
            net.get_node(target_title)["title"] = f"🔗 SHARED CITATION:\n{target_title}"
    else:
        # Standard Blue Node (Restored!)
        net.add_node(
            target_title, 
            title=target_title, 
            color="#4EA8DE", 
            size=10
        )
        
    net.add_edge(source, target_title, color="#444444", width=1)

# 5. SAVE AND INJECT TRANSITIONS
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
"""
html_content = html_content.replace("drawGraph();", f"drawGraph();\n{js_animation_injection}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print("\n🚀 Full network restored! Opening 'clean_network.html'...")
webbrowser.open("file://" + os.path.abspath(output_file))