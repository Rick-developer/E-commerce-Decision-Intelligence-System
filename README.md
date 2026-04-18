# 🛒 E-commerce Decision Intelligence System

> A modular, margin-aware recommendation engine that optimizes business yield without sacrificing behavioral relevance — built on real-world e-commerce event data.

---

## 📌 Problem Statement

Traditional recommendation systems rank items purely by **user behavioral intent** (clicks, add-to-carts, purchases). While this maximizes relevance, it leaves significant revenue on the table by ignoring product-level **margin dynamics**.

This project builds a **Decision Intelligence layer** that surgically reorders behaviorally-relevant recommendations to surface higher-margin products at top positions — achieving measurable **Position-Weighted Yield lift** without degrading Hit Rate or Precision.

---

## 🏗️ System Architecture

The system follows a **4-layer modular pipeline**, where each layer has a single responsibility and a clean interface contract:

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  load_events() → create_interaction_signals() → aggregate()      │
│  Retailrocket events.csv → Weighted interaction matrix           │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CANDIDATE GENERATION                            │
│  History (top-N user items) + Co-occurrence (item-item graph)    │
│  + Global Popularity → Deduplicated & diversity-constrained      │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    RANKING LAYER                                 │
│  Behavioral Score = f(preference, recency, popularity, source)   │
│  Min-Max Normalized → Weighted linear combination → Sort         │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   DECISION LAYER                                 │
│  decision_score = behavioral × (1 + α × normalized_margin)       │
│  Strictly monotonic — margin can only boost, never penalize      │
│  Top-10% margin items get +5% tiebreaker nudge                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
E-commerce-Decision-Intelligence-System/
│
├── data/
│   └── events.csv                  # Retailrocket dataset (not tracked by git)
│
├── src/
│   └── baseline/
│       ├── main.py                 # Pipeline orchestrator & entry point
│       ├── data_processing.py      # Event loading, signal mapping, aggregation
│       ├── feature_engineering.py   # Simulated business features, popularity, recency
│       ├── candidate_generation.py  # Multi-source candidate pool construction
│       ├── ranking.py              # Pure behavioral scoring & ranking
│       ├── decision.py             # Margin-aware reordering (Decision Layer)
│       └── evaluation.py           # Dual-system evaluation framework
│
├── .gitignore
└── README.md
```

---

## 🔬 Module Deep Dive

### 1. Data Processing (`data_processing.py`)
- Loads the **Retailrocket** events dataset (Unix ms timestamps)
- Maps raw events to numeric interaction weights:

  | Event         | Weight |
  |---------------|--------|
  | `view`        | 1.0    |
  | `addtocart`   | 3.0    |
  | `transaction`  | 5.0    |

- Aggregates weights per `(user, item)` pair into a single **preference score**

### 2. Feature Engineering (`feature_engineering.py`)
- **Simulated Business Features**: Deterministically generates `price`, `margin`, and `category_id` per item using MD5 hashing (stable across runs)
- **Popularity Score**: Global normalized interaction intensity per item `[0.0, 1.0]`
- **Recency Score**: Exponential decay with configurable half-life (default: 7 days)

### 3. Candidate Generation (`candidate_generation.py`)
Constructs the candidate pool from **three relevance-based sources**:

| Source          | Strategy                                                         |
|-----------------|------------------------------------------------------------------|
| **History**     | User's top-N highest preference items                            |
| **Co-occurrence** | Items frequently co-interacted by similar users (item-item graph) |
| **Global Popular** | Trending items by platform-wide interaction volume              |

Key design decisions:
- **No margin-based candidates** — injecting pure-margin items dilutes the pool with zero-intent products
- **Diversity constraint** — caps items per category (default: 25) to prevent echo-chamber effects
- **Deduplication** — prioritizes history > co-occurrence > global when items overlap

### 4. Ranking Layer (`ranking.py`)
Computes a **pure behavioral intent score** using weighted linear combination:

```
behavioral_score = 0.4 × preference + 0.3 × recency + 0.2 × popularity + 0.1 × candidate_score
```

All features are **Min-Max normalized** to `[0.0, 1.0]` before scoring. No business or margin logic is permitted in this layer.

### 5. Decision Layer (`decision.py`)
The core innovation — a **strictly monotonic margin-aware reordering**:

```
decision_score = behavioral_score × (1.0 + α × normalized_margin)
```

| Margin Level | Multiplier (α=0.15) | Effect                         |
|--------------|---------------------|--------------------------------|
| Minimum (0)  | × 1.00              | Score unchanged from baseline   |
| Maximum (1)  | × 1.15              | Gentle +15% uplift             |
| Top 10%      | × 1.05 bonus        | Additional tiebreaker nudge    |

**Critical constraint**: The decision layer operates on the **exact same candidate pool** as the behavioral baseline. It can only reorder — never inject or eject items.

### 6. Evaluation Framework (`evaluation.py`)
Implements **strict chronological train/test splitting** (no data leakage) and compares both systems using:

| Metric                        | What It Measures                                          |
|-------------------------------|-----------------------------------------------------------|
| **Hit Rate @K**               | % of users with ≥1 correct item in top-K                  |
| **Precision @K**              | Fraction of top-K items that are actual purchases          |
| **Margin Yield ($)**          | Flat sum of margins for correctly predicted items          |
| **Position-Weighted Yield ($)** | DCG-style: `margin / log₂(position + 1)` — rewards top slots |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pandas
- numpy

### Installation

```bash
# Clone the repository
git clone https://github.com/Rick-developer/E-commerce-Decision-Intelligence-System.git
cd E-commerce-Decision-Intelligence-System

# Install dependencies
pip install pandas numpy
```

### Dataset

This project uses the [Retailrocket E-commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset). Download `events.csv` and place it in the `data/` directory:

```
data/
└── events.csv
```

### Running the Pipeline

```bash
cd src/baseline
python main.py
```

Or specify a custom dataset path:

```bash
python main.py path/to/your/events.csv
```

**Configurable parameters** (in `main.py`):

| Parameter                | Default | Description                                |
|--------------------------|---------|--------------------------------------------|
| `max_users_to_evaluate`  | 50      | Number of test users to evaluate           |
| `top_k`                  | 20      | Recommendation list size per user          |
| `alpha` (decision layer) | 0.15    | Margin boost intensity                     |

---

## 📊 Sample Output

```
=============================================
      SYSTEM PERFORMANCE vs TRUE EVENTS
=============================================
         Evaluation Metric  Baseline (Behavioral)  Decision Engine
            Hit Rate @20                 0.XXXX           0.XXXX
           Precision @20                 0.XXXX           0.XXXX
         Margin Yield ($)                XX.XX            XX.XX
Position-Weighted Yield ($)              XX.XX            XX.XX

--- METRIC INSIGHTS ---
Position-Weighted Lift:  +X.XX%
```

> **Expected behavior**: Hit Rate and Precision remain **identical** (same candidate pool). Position-Weighted Yield shows a **positive lift** — proving the decision layer successfully surfaces higher-margin items at top positions.

---

## 🧠 Key Design Principles

1. **Separation of Concerns** — Each pipeline stage has a single responsibility with no cross-layer contamination
2. **Fair Comparison** — Decision layer operates on the identical candidate set as the baseline; no item injection/ejection
3. **Strictly Monotonic Scoring** — Margin can only boost a score, never penalize; items are never worse off
4. **Deterministic Reproducibility** — Business features generated via MD5 hashing; consistent across runs
5. **Chronological Integrity** — Train/test split respects temporal ordering to prevent data leakage

---

## 🛠️ Tech Stack

| Component       | Technology     |
|-----------------|----------------|
| Language        | Python 3.8+    |
| Data Processing | Pandas         |
| Numerical Ops   | NumPy          |
| Feature Hashing | hashlib (MD5)  |
| Dataset         | Retailrocket   |

---

## 📄 License

This project is open source and available for educational and portfolio purposes.

---

## 👤 Author

**Rick-developer**

- GitHub: [@Rick-developer](https://github.com/Rick-developer)
