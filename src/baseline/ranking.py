import pandas as pd
import numpy as np

# Configurable weights dictating the behavioral intent score.
# Weights are explicitly stripped of any business/margin assumptions.
BEHAVIORAL_WEIGHTS = {
    'preference_score': 0.4,
    'recency_score': 0.3,
    'popularity_score': 0.2,
    'candidate_score': 0.1
}

def assemble_features(candidates_df: pd.DataFrame, 
                      user_pref_df: pd.DataFrame, 
                      item_features_df: pd.DataFrame, 
                      recency_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assembles all pure behavioral signals onto the candidate pairs.
    Handles null-mapping securely for cold-start scenarios.
    """
    # 1. Start with the structured candidate generation output
    # (Schema: visitorid, itemid, source, candidate_score)
    df = candidates_df.copy()
    
    # 2. Left Join: User Preference (Historical Intent)
    df = pd.merge(df, user_pref_df[['visitorid', 'itemid', 'user_preference_score']], 
                  on=['visitorid', 'itemid'], how='left')
    df['user_preference_score'] = df['user_preference_score'].fillna(0.0)
    
    # 3. Left Join: Global Popularity (Trending Base)
    df = pd.merge(df, item_features_df[['itemid', 'popularity_score']], 
                  on='itemid', how='left')
    df['popularity_score'] = df['popularity_score'].fillna(0.0)
    
    # 4. Left Join: Recency Score (Exponential Time Decay)
    df = pd.merge(df, recency_df[['visitorid', 'itemid', 'recency_score']], 
                  on=['visitorid', 'itemid'], how='left')
    df['recency_score'] = df['recency_score'].fillna(0.0)
    
    return df

def normalize_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    MANDATORY normalizations to strict [0.0, 1.0] bounds.
    Scale consistency is required before applying weighted linear combinations.
    """
    df_norm = df.copy()
    features = ['user_preference_score', 'popularity_score', 'recency_score', 'candidate_score']
    
    for feat in features:
        min_val = df_norm[feat].min()
        max_val = df_norm[feat].max()
        
        if max_val == min_val:
            # Prevent Division-by-Zero: If all items lack variance, the feature provides zero discriminatory power.
            df_norm[feat] = 0.0
        else:
            # Standard Min-Max Math
            df_norm[feat] = (df_norm[feat] - min_val) / (max_val - min_val)
            
    return df_norm

def compute_behavioral_score(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """
    Computes linear combinations over the bounded feature vectors using configurable biases.
    NO business, pricing, or margin logic is permitted in this function.
    """
    df['behavioral_score'] = (
        (df['user_preference_score'] * weights.get('preference_score', 0)) +
        (df['popularity_score'] * weights.get('popularity_score', 0)) +
        (df['recency_score'] * weights.get('recency_score', 0)) +
        (df['candidate_score'] * weights.get('candidate_score', 0))
    )
    return df

def rank_candidates(candidates_df: pd.DataFrame, 
                    user_pref_df: pd.DataFrame, 
                    item_features_df: pd.DataFrame, 
                    recency_df: pd.DataFrame, 
                    weights: dict = None) -> pd.DataFrame:
    """
    Execution orchestrator for the behavioral baseline Ranking Layer.
    Returns structurally identical schema ordered purely by user intent probability.
    """
    if weights is None:
        weights = BEHAVIORAL_WEIGHTS
        
    features_df = assemble_features(candidates_df, user_pref_df, item_features_df, recency_df)
    normalized_df = normalize_features(features_df)
    scored_df = compute_behavioral_score(normalized_df, weights)
    
    # Strictly sort by the highest behavioral relevance
    scored_df = scored_df.sort_values(by=['visitorid', 'behavioral_score'], ascending=[True, False])
    
    # Strip unnecessary calculation columns to guarantee schema modularity
    return scored_df[['visitorid', 'itemid', 'source', 'behavioral_score']]
