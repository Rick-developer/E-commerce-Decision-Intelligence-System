import pandas as pd
import numpy as np

def merge_inputs(ranked_df: pd.DataFrame, item_features_df: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(ranked_df, item_features_df[['itemid', 'margin', 'category_id']], 
                  on='itemid', how='left')
    df['margin'] = df['margin'].fillna(0.0)
    return df

def normalize_margin(df: pd.DataFrame) -> pd.DataFrame:
    min_m = df['margin'].min()
    max_m = df['margin'].max()
    
    if max_m == min_m:
        df['normalized_margin'] = 0.0
    else:
        df['normalized_margin'] = (df['margin'] - min_m) / (max_m - min_m)
    return df

def compute_decision_score(df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """
    STRICTLY MONOTONIC: decision_score = behavioral_score * (1.0 + alpha * normalized_margin)
    
    When margin = 0 → multiplier = 1.0 → score is UNCHANGED from behavioral baseline.
    When margin = max → multiplier = (1 + alpha) → score gets a gentle uplift.
    
    NO item is EVER penalized. Margin can only help, never hurt.
    """
    df['decision_score'] = df['behavioral_score'] * (1.0 + alpha * df['normalized_margin'])
    return df

def apply_override_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Gentle tiebreaker: top 10% margin items get a small +5% nudge."""
    margin_threshold = df['margin'].quantile(0.90)
    df['is_high_margin'] = df['margin'] >= margin_threshold
    
    df['decision_score'] = np.where(
        df['is_high_margin'], 
        df['decision_score'] * 1.05, 
        df['decision_score']
    )
    return df

def generate_explanations(df: pd.DataFrame) -> pd.DataFrame:
    median_score = df['behavioral_score'].median()
    upper_quartile = df['behavioral_score'].quantile(0.75)
    
    conditions = [
        (df['is_high_margin']) & (df['behavioral_score'] >= median_score),
        (df['is_high_margin']) & (df['behavioral_score'] < median_score),
        (~df['is_high_margin']) & (df['behavioral_score'] >= upper_quartile),
        (~df['is_high_margin']) & (df['behavioral_score'] < upper_quartile)
    ]
    
    choices = [
        "High relevance + High margin dollar",
        "Margin-boosted tiebreaker",
        "Pure high behavioral relevance",
        "Standard relevance retained"
    ]
    
    df['explanation'] = np.select(conditions, choices, default="Baseline display item")
    return df

def make_decisions(ranked_df: pd.DataFrame, item_features_df: pd.DataFrame, 
                   alpha: float = 0.15, top_k: int = 20) -> pd.DataFrame:
    """
    The decision layer operates as a SURGICAL margin-aware reordering.
    It takes the SAME candidate pool as the baseline, applies margin boosts,
    re-sorts, and returns the top_k. NO items are ejected by diversity constraints —
    that would create an unfair comparison where the decision layer has fewer 
    relevant items than the baseline.
    """
    df = ranked_df.copy()
        
    df = merge_inputs(df, item_features_df)
    df = normalize_margin(df)
    df = compute_decision_score(df, alpha)
    df = apply_override_rules(df)
    df = generate_explanations(df)
    
    # Pure re-sort by decision_score, then take top_k — NO diversity ejection
    df = df.sort_values(by=['visitorid', 'decision_score'], ascending=[True, False])
    df = df.groupby('visitorid').head(top_k)
    
    return df[['visitorid', 'itemid', 'source', 'decision_score', 'explanation', 'behavioral_score', 'normalized_margin']]
