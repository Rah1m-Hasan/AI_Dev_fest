"""Dataset research is deliberately a manifest, not a scraper of questionable data."""
import json
from pathlib import Path
manifest={"candidates":[{"name":"PaySim","source_url":"https://github.com/EdgarLopezPhD/PaySim","license":"GPL-3.0 for simulator; verify Kaggle distribution terms separately","used":False,"reason":"Relevant synthetic mobile money reference, but the large Kaggle distribution is not redistributed by this repository."}]}
Path("data/metadata").mkdir(parents=True,exist_ok=True);Path("data/metadata/dataset_research.json").write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
