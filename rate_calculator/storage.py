
import json
import os

MAPPINGS_FILE = "/Users/fengyuanshi/Desktop/rate calculation/saved_mappings.json"

def save_mappings(labor_map, depr_map, groups=None, expenses=None, projections=None, contracts=None):
    data = {
        "labor": labor_map,
        "depreciation": depr_map,
        "groups": groups if groups else {},
        "expenses": expenses if expenses else {},
        "projections": projections if projections else [],
        "contracts": contracts if contracts else {}
    }
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(data, f)

def load_mappings():
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, 'r') as f:
            data = json.load(f)
            if "groups" not in data: data["groups"] = {}
            if "expenses" not in data: data["expenses"] = {}
            if "projections" not in data: data["projections"] = []
            if "contracts" not in data: data["contracts"] = {}
            return data
    return {"labor": {}, "depreciation": {}, "groups": {}, "expenses": {}, "projections": [], "contracts": {}}
