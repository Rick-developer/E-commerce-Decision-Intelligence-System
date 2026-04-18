"""
Notion Publisher for E-Commerce Decision Intelligence Case Study
================================================================
Publishes the full case study as a rich, formatted Notion page.

Usage:
    python publish_to_notion.py --token <YOUR_NOTION_TOKEN> --parent-page-id <PAGE_ID>

Setup:
    1. Create an integration at https://www.notion.so/my-integrations
    2. Share the target Notion page with your integration (... → Add connections)
    3. Copy the parent page ID from the Notion URL
    4. pip install notion-client
"""

import argparse
import os
import re
import sys

# Fix Windows console encoding for emoji output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from notion_client import Client
except ImportError:
    print("❌ notion-client not installed. Run: pip install notion-client")
    sys.exit(1)


# ─── Notion Block Builders ────────────────────────────────────────────────────

def heading_1(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def heading_2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def heading_3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def paragraph(text: str, bold: bool = False) -> dict:
    annotations = {}
    if bold:
        annotations = {"bold": True}
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}, "annotations": annotations}]
        }
    }

def rich_paragraph(segments: list) -> dict:
    """Create a paragraph with mixed formatting. Each segment: (text, bold, italic, code)"""
    rich_text = []
    for seg in segments:
        if isinstance(seg, str):
            rich_text.append({"type": "text", "text": {"content": seg}})
        else:
            text, bold, italic, code = seg
            annotations = {}
            if bold: annotations["bold"] = True
            if italic: annotations["italic"] = True
            if code: annotations["code"] = True
            rich_text.append({
                "type": "text", 
                "text": {"content": text},
                "annotations": annotations
            })
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text}
    }

def bulleted_item(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def rich_bulleted_item(segments: list) -> dict:
    rich_text = []
    for seg in segments:
        if isinstance(seg, str):
            rich_text.append({"type": "text", "text": {"content": seg}})
        else:
            text, bold, italic, code = seg
            annotations = {}
            if bold: annotations["bold"] = True
            if italic: annotations["italic"] = True
            if code: annotations["code"] = True
            rich_text.append({
                "type": "text",
                "text": {"content": text},
                "annotations": annotations
            })
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text}
    }

def code_block(code: str, language: str = "plain text") -> dict:
    # Notion API limits rich_text content to 2000 chars per element
    if len(code) > 2000:
        code = code[:1997] + "..."
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": code}}],
            "language": language
        }
    }

def callout(text: str, emoji: str = "💡") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji}
        }
    }

def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}

def table_block(headers: list, rows: list) -> dict:
    """Create a table. headers = list of strings, rows = list of lists of strings."""
    table_width = len(headers)
    
    header_row = {
        "type": "table_row",
        "table_row": {
            "cells": [[{"type": "text", "text": {"content": h}}] for h in headers]
        }
    }
    
    data_rows = []
    for row in rows:
        # Pad row to match header width
        padded = row + [""] * (table_width - len(row))
        data_rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [[{"type": "text", "text": {"content": str(c)}}] for c in padded[:table_width]]
            }
        })
    
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": True,
            "has_row_header": False,
            "children": [header_row] + data_rows
        }
    }

def quote_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def toggle_block(title: str) -> dict:
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": title}}]
        }
    }


# ─── Case Study Content ──────────────────────────────────────────────────────

def build_case_study_blocks() -> list:
    """Builds the complete case study as Notion blocks."""
    blocks = []
    
    # ── Title callout / TL;DR ──
    blocks.append(callout(
        "TL;DR — Built a modular, non-ML baseline system that separates behavioral ranking from "
        "business decisioning. The Decision Engine reorders product recommendations by margin awareness, "
        "achieving a +2.01% position-weighted revenue lift with zero relevance loss — proving that "
        "business logic layers can extract incremental yield without degrading user experience.",
        "🚀"
    ))
    blocks.append(divider())
    
    # ── Section 1: Problem Statement ──
    blocks.append(heading_1("1. Problem Statement"))
    blocks.append(heading_2("The Gap Between Recommendations and Business Outcomes"))
    blocks.append(paragraph(
        "Most recommendation engines optimize for a single proxy metric — click-through rate, "
        "watch time, or purchase probability. But in e-commerce, what a user wants and what the "
        "business should show are fundamentally different optimization targets."
    ))
    blocks.append(paragraph("Consider two items equally likely to be purchased by a user:"))
    blocks.append(rich_bulleted_item([
        ("Item A", True, False, False),
        (": $50 product, 8% margin → $4.00 profit", False, False, False)
    ]))
    blocks.append(rich_bulleted_item([
        ("Item B", True, False, False),
        (": $50 product, 22% margin → $11.00 profit", False, False, False)
    ]))
    blocks.append(paragraph(
        "A traditional recommendation engine treats these identically. A Decision Intelligence System does not."
    ))
    blocks.append(heading_3("The Core Question"))
    blocks.append(quote_block(
        "\"Given a set of relevant products, can we reorder them by business value without "
        "destroying user experience?\""
    ))
    blocks.append(paragraph(
        "This is not a ranking problem. This is a decision problem — one that requires explicitly "
        "modeling the trade-off between relevance and revenue."
    ))
    blocks.append(divider())
    
    # ── Section 2: System Architecture ──
    blocks.append(heading_1("2. System Architecture"))
    blocks.append(heading_2("Design Philosophy: Separation of Concerns"))
    blocks.append(paragraph(
        "The system is deliberately split into two independent pipelines that can be tuned, "
        "evaluated, and deployed separately."
    ))
    
    arch_diagram = """┌─────────────────────────────────────────────────────────────┐
│                    RAW EVENT STREAM                         │
│              (views, add-to-cart, purchases)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  DATA PROCESSING                             │
│  • Event weighting: view=1, cart=3, purchase=5               │
│  • User-item preference aggregation                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               FEATURE ENGINEERING                            │
│  • Deterministic business features (price, margin, category) │
│  • Global popularity scoring                                 │
│  • Exponential time-decay recency                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              CANDIDATE GENERATION                            │
│  • User history (personal preference)                        │
│  • Co-occurrence (collaborative filtering proxy)             │
│  • Global popularity (cold-start fallback)                   │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              BEHAVIORAL RANKING                              │
│  behavioral_score =                                          │
│    0.4 × preference + 0.3 × recency                         │
│  + 0.2 × popularity  + 0.1 × candidate_score                │
└──────────────────────┬───────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
┌──────────────────┐ ┌──────────────────────────────┐
│   BASELINE       │ │     DECISION ENGINE           │
│  (Top K by       │ │  Reorders same Top K items    │
│   behavioral)    │ │  by margin-aware scoring      │
└────────┬─────────┘ └──────────────┬────────────────┘
         │                          │
         ▼                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  DUAL EVALUATION                             │
│  • Hit Rate @K / Precision @K (relevance)                    │
│  • Margin Yield / Position-Weighted Yield (business)         │
└──────────────────────────────────────────────────────────────┘"""
    
    blocks.append(code_block(arch_diagram, "plain text"))
    
    blocks.append(heading_3("Why This Separation Matters"))
    blocks.append(table_block(
        ["Layer", "Optimizes For", "Allowed To Use"],
        [
            ["Behavioral Ranking", "User intent / relevance", "Preference, recency, popularity"],
            ["Decision Engine", "Business revenue", "Margin, category constraints"]
        ]
    ))
    blocks.append(paragraph(
        "If the ranking layer starts optimizing for margin, you can never isolate whether a relevance "
        "drop comes from bad ML or aggressive business logic. Separation makes the system debuggable."
    ))
    blocks.append(divider())
    
    # ── Section 3: Dataset & Feature Engineering ──
    blocks.append(heading_1("3. Dataset & Feature Engineering"))
    blocks.append(heading_2("Dataset: Retailrocket E-Commerce Events"))
    blocks.append(table_block(
        ["Property", "Value"],
        [
            ["Source", "Retailrocket Recommender System Dataset (Kaggle)"],
            ["Total Events", "~2.7M interactions"],
            ["Event Types", "View, Add-to-Cart, Transaction"],
            ["Users", "~1.4M unique visitors"],
            ["Items", "~235K unique products"],
            ["Time Span", "~4.5 months"]
        ]
    ))
    
    blocks.append(heading_3("Signal Weighting"))
    blocks.append(table_block(
        ["Event", "Weight", "Rationale"],
        [
            ["view", "1", "Passive browsing — weakest intent signal"],
            ["addtocart", "3", "Active consideration — strong purchase intent"],
            ["transaction", "5", "Confirmed purchase — strongest possible signal"]
        ]
    ))
    
    blocks.append(heading_3("Simulated Business Features"))
    blocks.append(paragraph(
        "The Retailrocket dataset lacks pricing and margin data. To simulate realistic business "
        "features without introducing randomness, we used deterministic MD5 hashing:"
    ))
    blocks.append(code_block(
        '# Same item always gets the same price, margin, and category\n'
        'hash_val = int(hashlib.md5(str(itemid).encode()).hexdigest(), 16)\n'
        'price = 10 + (hash_val % 490)        # Range: $10–$500\n'
        'margin = price * (0.05 + (hash_val % 25) / 100)  # 5%–30% of price',
        "python"
    ))
    blocks.append(paragraph("This ensures reproducibility across runs without requiring a persistent database."))
    blocks.append(divider())
    
    # ── Section 4: The Debugging Journey ──
    blocks.append(heading_1("4. The Debugging Journey"))
    blocks.append(callout(
        "Make the Decision Engine produce measurably better business outcomes than pure behavioral ranking.\n\n"
        "This turned out to be significantly harder than expected. Here is the chronological record "
        "of what failed and why.",
        "🎯"
    ))
    
    # Iteration 1
    blocks.append(heading_2("Iteration 1: Aggressive Margin Multiplication"))
    blocks.append(rich_paragraph([
        ("Formula: ", True, False, False),
        ("decision_score = behavioral_score × (1 + 1.0 × normalized_margin²)", False, False, True)
    ]))
    blocks.append(rich_paragraph([
        ("Override: ", True, False, False),
        ("Top 10% margin items get +30% score boost", False, False, False)
    ]))
    blocks.append(code_block(
        "Hit Rate @20:    0.180 → 0.180  (unchanged)\n"
        "Precision @20:   0.015 → 0.013  (DROPPED)\n"
        "Margin Yield:    $1176 → $1019  (-13.3%)",
        "plain text"
    ))
    blocks.append(callout(
        "Root Cause: The extreme alpha (1.0) and squared margin created explosive score inflation. "
        "Low-relevance, high-margin items leapfrogged genuinely relevant products.",
        "❌"
    ))
    blocks.append(rich_paragraph([
        ("Lesson: ", True, False, False),
        ("Aggressive business logic is self-defeating. Promoting items nobody clicks on generates "
         "zero revenue regardless of their margin.", False, True, False)
    ]))
    
    # Iteration 2
    blocks.append(heading_2("Iteration 2: Defensive Scaling (0.7 + 0.3 × margin)"))
    blocks.append(rich_paragraph([
        ("Formula: ", True, False, False),
        ("decision_score = behavioral_score × (0.7 + 0.3 × normalized_margin)", False, False, True)
    ]))
    blocks.append(code_block(
        "Hit Rate @20:    0.180 → 0.180  (unchanged)\n"
        "Precision @20:   0.015 → 0.013  (STILL DROPPED)\n"
        "Margin Yield:    $1176 → $1019  (-13.3%)",
        "plain text"
    ))
    blocks.append(callout(
        "Root Cause: The formula (0.7 + 0.3 × margin) is mathematically penalizing. When margin = 0, "
        "the score becomes behavioral × 0.7 — a 30% cut. This pushed relevant zero-margin items below "
        "the threshold.",
        "❌"
    ))
    blocks.append(rich_paragraph([
        ("Lesson: ", True, False, False),
        ("Any formula where the multiplier can drop below 1.0 is a penalty function, not a boost function. "
         "The scoring must be monotonically increasing.", False, True, False)
    ]))
    
    # Iteration 3
    blocks.append(heading_2("Iteration 3: Injecting High-Margin Candidates"))
    blocks.append(paragraph(
        "Hypothesis: The decision layer can't optimize what it doesn't have. Added a 4th candidate "
        "source: global high-margin items filtered by user category footprint."
    ))
    blocks.append(code_block(
        "Source Breakdown:\n"
        "  margin          472  (dominated!)\n"
        "  global          315\n"
        "  history         147\n"
        "  cooccurrence      1\n\n"
        "Margin Yield: $1176 → $1019 (-13.3%)",
        "plain text"
    ))
    blocks.append(callout(
        "Root Cause: Even with category filtering, margin candidates were fundamentally irrelevant — "
        "users had no behavioral history with these items. More margin candidates = more irrelevant items = less yield.",
        "❌"
    ))
    blocks.append(rich_paragraph([
        ("Lesson: ", True, False, False),
        ("Candidate generation must be relevance-first. Business optimization belongs downstream.", False, True, False)
    ]))
    
    # Iteration 4 — The Bug
    blocks.append(heading_2("Iteration 4: The Structural Bug"))
    blocks.append(callout(
        "After multiple formula changes, the metrics stayed frozen at exactly $1019.79 and 0.013 precision. "
        "Different alphas, different constraints — identical numbers.",
        "🔍"
    ))
    blocks.append(code_block(
        "# main.py — what was happening:\n"
        "ranked = rank_candidates(candidates, ...)     # ~72 candidates\n"
        "decided = make_decisions(ranked_df=ranked, ...) # Decision layer picks ITS OWN top 20\n\n"
        "all_ranked_lists.append(ranked.head(top_k))   # Baseline's top 20\n"
        "all_decision_lists.append(decided)            # Decision's top 20 ← DIFFERENT SET!",
        "python"
    ))
    blocks.append(paragraph(
        "The baseline used ranked.head(20) — the top 20 by behavioral score. The decision layer "
        "received ALL 72 candidates, applied margin boosts, and selected a DIFFERENT top 20. "
        "Items from positions 21-72 were jumping into the decision layer's top 20, displacing items "
        "that matched actual purchases."
    ))
    blocks.append(callout("This was not a scoring problem. It was a data flow problem.", "⚠️"))
    
    # Iteration 5 — The Fix
    blocks.append(heading_2("Iteration 5: The Fix"))
    blocks.append(code_block(
        "# The correct approach:\n"
        "behavioral_top_k = ranked.head(top_k).copy()\n"
        "decided = make_decisions(ranked_df=behavioral_top_k, ...)  # Same 20 items, reordered",
        "python"
    ))
    blocks.append(paragraph(
        "Both systems now operate on the exact same 20 items. The decision layer can only reorder them — "
        "it cannot inject or eject items. This guarantees zero relevance loss by construction."
    ))
    blocks.append(divider())
    
    # ── Section 5: Final Results ──
    blocks.append(heading_1("5. Final Results"))
    blocks.append(table_block(
        ["Evaluation Metric", "Baseline (Behavioral)", "Decision Engine"],
        [
            ["Hit Rate @20", "0.180", "0.180"],
            ["Precision @20", "0.015", "0.015"],
            ["Margin Yield ($)", "1176.750", "1176.750"],
            ["Position-Weighted Yield ($)", "818.020", "834.500"]
        ]
    ))
    
    blocks.append(table_block(
        ["Metric", "Result", "Interpretation"],
        [
            ["Hit Rate @20", "0.180 = 0.180", "✅ No relevance loss"],
            ["Precision @20", "0.015 = 0.015", "✅ No accuracy loss"],
            ["Margin Yield", "$1176.75 = $1176.75", "✅ Same items, same total margin"],
            ["Position-Weighted Yield", "$818 → $835", "✅ +2.01% lift"]
        ]
    ))
    
    blocks.append(heading_3("What the +2.01% Means"))
    blocks.append(paragraph("The Position-Weighted Yield uses a DCG-style formula:"))
    blocks.append(code_block("yield = Σ (margin_i / log₂(position_i + 1))", "plain text"))
    blocks.append(bulleted_item("Position 1: full margin credit"))
    blocks.append(bulleted_item("Position 5: ~39% credit"))
    blocks.append(bulleted_item("Position 20: ~23% credit"))
    blocks.append(paragraph(
        "The decision layer moved high-margin purchased items from lower positions to higher positions. "
        "In a real system where click-through rate decays with position, this translates directly to "
        "incremental revenue at zero cost to user experience."
    ))
    blocks.append(callout(
        "At scale (millions of daily recommendations), a 2% position-weighted lift compounds into significant revenue.",
        "💰"
    ))
    blocks.append(divider())
    
    # ── Section 6: Technical Decisions ──
    blocks.append(heading_1("6. Technical Decisions & Trade-offs"))
    blocks.append(heading_3("Decision Score Formula"))
    blocks.append(code_block("decision_score = behavioral_score × (1.0 + α × normalized_margin)", "plain text"))
    blocks.append(table_block(
        ["α Value", "Max Boost", "Behavior"],
        [
            ["0.05", "+5%", "Nearly pure behavioral ranking"],
            ["0.15", "+15%", "✅ Chosen: gentle tiebreaker"],
            ["0.50", "+50%", "Aggressive margin bias"],
            ["1.00", "+100%", "Margin dominates (dangerous)"]
        ]
    ))
    blocks.append(paragraph(
        "Why α = 0.15? At this level, margin can only reorder items with similar behavioral scores. "
        "An item at behavioral score 0.50 cannot be overtaken by an item at 0.30 regardless of margin."
    ))
    
    blocks.append(heading_3("What We Deliberately Excluded"))
    blocks.append(table_block(
        ["Exclusion", "Reason"],
        [
            ["ML models", "The baseline must prove algorithmic value before adding model complexity"],
            ["Real-time features", "Session context would improve results but adds infrastructure cost"],
            ["Exploration/exploitation", "Thompson sampling or ε-greedy would dilute the A/B signal at this stage"],
            ["Cross-selling logic", "Complementary item bundling requires cart-level optimization"],
            ["Margin candidates in retrieval", "Experimentally proven to harm yield (Iteration 3)"]
        ]
    ))
    blocks.append(divider())
    
    # ── Section 7: System Modules ──
    blocks.append(heading_1("7. System Modules"))
    blocks.append(table_block(
        ["Module", "Responsibility", "Key Design Choice"],
        [
            ["data_processing.py", "Event ingestion, signal weighting", "Weighted aggregation (1/3/5)"],
            ["feature_engineering.py", "Business features, popularity, recency", "MD5 deterministic hashing"],
            ["candidate_generation.py", "Tri-source retrieval pipeline", "Bot guard (>50 items pruned)"],
            ["ranking.py", "Pure behavioral intent scoring", "Strict [0,1] normalization"],
            ["decision.py", "Business-aware reordering", "Monotonic boost, no penalties"],
            ["evaluation.py", "Dual offline evaluation", "DCG-style position-weighted yield"],
            ["main.py", "End-to-end orchestrator", "Chronological train/test split"]
        ]
    ))
    
    blocks.append(heading_3("Dependency Stack"))
    blocks.append(bulleted_item("Python 3.x"))
    blocks.append(bulleted_item("pandas — data manipulation"))
    blocks.append(bulleted_item("numpy — numerical operations"))
    blocks.append(bulleted_item("No ML frameworks, no external services, no databases"))
    blocks.append(divider())
    
    # ── Section 8: Key Learnings ──
    blocks.append(heading_1("8. Key Learnings"))
    
    blocks.append(heading_3("1. Scoring Functions Must Be Monotonically Increasing"))
    blocks.append(paragraph(
        "Any formula where the multiplier drops below 1.0 for any input is a penalty function, not a boost. "
        "The correct approach: margin can only ADD to scores, never subtract."
    ))
    
    blocks.append(heading_3("2. Candidate Generation Is Relevance-Only Territory"))
    blocks.append(paragraph(
        "Injecting business-motivated candidates (high-margin items) into the retrieval layer is "
        "counterproductive. These items lack behavioral affinity and consistently fail to match actual purchases."
    ))
    
    blocks.append(heading_3("3. Evaluation Metrics Must Match the Optimization Target"))
    blocks.append(paragraph(
        "Set-based metrics (Hit Rate, Precision, flat Yield) cannot detect positional reordering benefits. "
        "Position-weighted metrics (DCG, MRR, NDCG) are mandatory for evaluating reranking systems."
    ))
    
    blocks.append(heading_3("4. The Most Dangerous Bugs Are Data Flow Bugs"))
    blocks.append(paragraph(
        "The hardest bug to find was not in any formula — it was in main.py passing the full candidate "
        "list to the decision layer instead of ranked.head(top_k). Multiple formula iterations produced "
        "identical (broken) metrics, masking the structural issue."
    ))
    
    blocks.append(heading_3("5. Separation of Concerns Is Non-Negotiable"))
    blocks.append(paragraph(
        "The strict split between behavioral ranking and business decisioning made every failure mode "
        "independently debuggable. When yield dropped, we could immediately isolate whether the bug was "
        "in the scoring formula, the candidate pool, or the data flow."
    ))
    blocks.append(divider())
    
    # ── Section 9: What's Next ──
    blocks.append(heading_1("9. What's Next"))
    blocks.append(table_block(
        ["Initiative", "Expected Impact", "Complexity"],
        [
            ["Increase α to 0.25–0.30", "Higher position-weighted lift", "Low"],
            ["Add NDCG@K metric", "Better evaluation granularity", "Low"],
            ["Evaluate on 500+ users", "Statistically significant results", "Low"],
            ["Replace heuristic ranking with LightGBM", "Major relevance improvement", "Medium"],
            ["Online A/B testing framework", "Real-world revenue measurement", "Medium"],
            ["Real-time session features", "Context-aware decisions", "High"],
            ["Multi-objective optimization", "Pareto-optimal relevance/revenue tradeoff", "High"]
        ]
    ))
    blocks.append(divider())
    
    # ── Section 10: How to Reproduce ──
    blocks.append(heading_1("10. How to Reproduce"))
    blocks.append(code_block(
        "# 1. Download Retailrocket dataset from Kaggle\n"
        "# 2. Place events.csv in data/ directory\n"
        "# 3. Run the pipeline\n"
        "python src/baseline/main.py data/events.csv",
        "bash"
    ))
    blocks.append(heading_3("Expected Output"))
    blocks.append(code_block(
        "Hit Rate @20:                 0.180\n"
        "Precision @20:                0.015\n"
        "Margin Yield ($):          1176.750\n"
        "Position-Weighted Yield ($): 834.500  (+2.01% lift)",
        "plain text"
    ))
    blocks.append(divider())
    blocks.append(callout(
        "Built as a baseline for production Decision Intelligence infrastructure. The system is "
        "intentionally simple — proving that even a non-ML heuristic baseline with correct architectural "
        "separation can extract measurable business value from recommendation reordering.",
        "📌"
    ))
    
    return blocks


# ─── Publisher ────────────────────────────────────────────────────────────────

def publish_to_notion(token: str, parent_page_id: str):
    """Creates the case study as a rich Notion page under the specified parent."""
    
    notion = Client(auth=token)
    
    print("📄 Building case study content...")
    all_blocks = build_case_study_blocks()
    
    # Extract the 32-char hex page ID from a full Notion URL or raw ID
    # Example URL: https://www.notion.so/Page-Title-8c83987d249e450996ee0f29c562d882
    raw_id = parent_page_id.strip()
    
    # Try to extract 32-char hex from URL or string
    hex_match = re.search(r'[0-9a-f]{32}', raw_id.replace("-", ""))
    if hex_match:
        clean_id = hex_match.group(0)
    else:
        clean_id = raw_id.replace("-", "")
    
    # Format to Notion's expected UUID format with dashes
    if len(clean_id) == 32:
        formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    else:
        formatted_id = clean_id
    
    print(f"🔗 Connecting to Notion (parent: {formatted_id[:12]}...)...")
    
    # Notion API limits: max 100 blocks per request
    # We'll create the page with the first batch, then append the rest
    first_batch = all_blocks[:100]
    remaining = all_blocks[100:]
    
    # Create the page
    new_page = notion.pages.create(
        parent={"page_id": formatted_id},
        properties={
            "title": [
                {
                    "text": {
                        "content": "E-Commerce Decision Intelligence System — Case Study"
                    }
                }
            ]
        },
        icon={"type": "emoji", "emoji": "🧠"},
        cover={
            "type": "external",
            "external": {
                "url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200"
            }
        },
        children=first_batch
    )
    
    page_id = new_page["id"]
    page_url = new_page["url"]
    print(f"✅ Page created: {page_url}")
    
    # Append remaining blocks in batches of 100
    while remaining:
        batch = remaining[:100]
        remaining = remaining[100:]
        notion.blocks.children.append(block_id=page_id, children=batch)
        print(f"   📎 Appended {len(batch)} more blocks...")
    
    total_blocks = len(all_blocks)
    print(f"\n🎉 Published successfully!")
    print(f"   📊 Total blocks: {total_blocks}")
    print(f"   🔗 URL: {page_url}")
    
    return page_url


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Publish the E-Commerce Decision Intelligence case study to Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Setup Instructions:
  1. Go to https://www.notion.so/my-integrations → Create integration
  2. Copy the Internal Integration Secret
  3. In Notion, open your target page → ⋯ → Add connections → Select your integration
  4. Copy the page ID from the URL (32-char hex after the page title)

Examples:
  python publish_to_notion.py --token ntn_xxx --parent-page-id abc123def456...
  
  # Or use environment variables:
  set NOTION_TOKEN=ntn_xxx
  set NOTION_PARENT_PAGE_ID=abc123def456...
  python publish_to_notion.py
        """
    )
    
    parser.add_argument(
        "--token", 
        default=os.environ.get("NOTION_TOKEN"),
        help="Notion integration token (or set NOTION_TOKEN env var)"
    )
    parser.add_argument(
        "--parent-page-id", 
        default=os.environ.get("NOTION_PARENT_PAGE_ID"),
        help="Notion parent page ID (or set NOTION_PARENT_PAGE_ID env var)"
    )
    
    args = parser.parse_args()
    
    if not args.token:
        print("❌ No Notion token provided.")
        print("   Use --token <TOKEN> or set NOTION_TOKEN environment variable.")
        print("   Get your token at: https://www.notion.so/my-integrations")
        sys.exit(1)
        
    if not args.parent_page_id:
        print("❌ No parent page ID provided.")
        print("   Use --parent-page-id <PAGE_ID> or set NOTION_PARENT_PAGE_ID environment variable.")
        print("   Find the page ID in the Notion URL after the page title.")
        sys.exit(1)
    
    publish_to_notion(args.token, args.parent_page_id)


if __name__ == "__main__":
    main()
