"""Verify the Notion page content by reading all blocks via API."""
import sys
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from notion_client import Client

TOKEN = "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"
PAGE_ID = "33e4331b-b8b5-8193-ab7a-df24cad7f9eb"

notion = Client(auth=TOKEN)

def get_all_blocks(page_id):
    """Fetch all blocks from the page, handling pagination."""
    all_blocks = []
    cursor = None
    
    while True:
        if cursor:
            response = notion.blocks.children.list(block_id=page_id, start_cursor=cursor, page_size=100)
        else:
            response = notion.blocks.children.list(block_id=page_id, page_size=100)
        
        all_blocks.extend(response["results"])
        
        if response.get("has_more"):
            cursor = response["next_cursor"]
        else:
            break
    
    return all_blocks

print("Fetching all blocks from the Notion page...\n")
blocks = get_all_blocks(PAGE_ID)

print(f"Total blocks found: {len(blocks)}\n")
print("=" * 70)

# Detailed block-by-block report
headings_found = []
block_type_counts = {}

for i, block in enumerate(blocks, 1):
    btype = block["type"]
    block_type_counts[btype] = block_type_counts.get(btype, 0) + 1
    
    if btype in ("heading_1", "heading_2", "heading_3"):
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        marker = {"heading_1": "H1", "heading_2": "H2", "heading_3": "H3"}[btype]
        headings_found.append(f"[{marker}] {text}")
        print(f"Block {i:3d} | {marker:3s} | {text}")
    elif btype == "callout":
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        print(f"Block {i:3d} | CALL| {text[:80]}...")
    elif btype == "paragraph":
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        if text.strip():
            print(f"Block {i:3d} | PAR | {text[:80]}...")
        else:
            print(f"Block {i:3d} | PAR | (empty paragraph)")
    elif btype == "code":
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        lang = block[btype].get("language", "?")
        print(f"Block {i:3d} | CODE| [{lang}] {text[:60]}...")
    elif btype == "table":
        width = block[btype].get("table_width", "?")
        print(f"Block {i:3d} | TBL | Table (width={width})")
    elif btype == "divider":
        print(f"Block {i:3d} | --- | divider")
    elif btype == "bulleted_list_item":
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        print(f"Block {i:3d} | BUL | {text[:80]}")
    elif btype == "quote":
        text = ""
        for rt in block[btype].get("rich_text", []):
            text += rt.get("plain_text", "")
        print(f"Block {i:3d} | QTE | {text[:80]}")
    else:
        print(f"Block {i:3d} | {btype[:4].upper():4s}| (content)")

print("\n" + "=" * 70)
print("\nBlock type summary:")
for btype, count in sorted(block_type_counts.items()):
    print(f"  {btype:25s}: {count}")

print(f"\nAll headings found ({len(headings_found)}):")
for h in headings_found:
    print(f"  {h}")

# Expected sections check
expected_h1 = [
    "1. Problem Statement",
    "2. System Architecture", 
    "3. Dataset & Feature Engineering",
    "4. The Debugging Journey",
    "5. Final Results",
    "6. Technical Decisions & Trade-offs",
    "7. System Modules",
    "8. Key Learnings",
    "9. What's Next",
    "10. How to Reproduce"
]

print(f"\n--- SECTION VERIFICATION ---")
h1_texts = [h.replace("[H1] ", "") for h in headings_found if h.startswith("[H1]")]
for exp in expected_h1:
    found = any(exp in h for h in h1_texts)
    status = "FOUND" if found else "MISSING"
    print(f"  {status:8s} | {exp}")

print(f"\nLast block (#{len(blocks)}): type={blocks[-1]['type']}")
if blocks[-1]["type"] == "callout":
    text = ""
    for rt in blocks[-1]["callout"].get("rich_text", []):
        text += rt.get("plain_text", "")
    print(f"  Content: {text[:100]}...")
