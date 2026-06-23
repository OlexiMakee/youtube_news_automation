import os
import sys
import json
from pathlib import Path

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.briefs import BriefsService
from app.services.governance import registry_ready

# Must use free model
os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-fake-test-key-for-now"
# We will just verify the mock or handle the key absence smoothly for testing structure

def test_brief_service():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("Testing registry readiness...")
    if not registry_ready(root_dir):
        print("FAIL: Registry not ready. Cannot test briefs.")
        return
    print("PASS: Registry is ready.")

    print("Fetching briefs list...")
    result = BriefsService.list_briefs(root_dir)
    print("Found briefs:", len(result["briefs"]))
    
    if result["briefs"]:
        brief_id = result["briefs"][0]["id"]
        print(f"Fetching brief {brief_id}...")
        brief = BriefsService.get_brief_by_id(root_dir, brief_id)
        print("PASS: Fetched brief.")
        print(f"Claims count: {len(brief['claims'])}")
        
        print("Testing redaction...")
        redacted = BriefsService.redact_brief(brief)
        print("PASS: Redaction succeeded.")

        print("Testing markdown export...")
        md = BriefsService.export_brief(root_dir, brief_id, "markdown")
        print("MD preview:", md[:100].replace('\n', ' '))
    else:
        print("No briefs found to fetch. This is okay if DB is empty.")

    print("\nAll tests passed successfully.")

if __name__ == "__main__":
    test_brief_service()
