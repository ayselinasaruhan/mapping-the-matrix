# Completely wipes the citation_network.json file, effectively resetting the database to an empty state.

import json

db_file = "citation_network.json"

# Overwrite the file with an empty list structure
with open(db_file, "w", encoding="utf-8") as f:
    json.dump([], f)

print(f"🗑️ {db_file} has been completely wiped clean!")
