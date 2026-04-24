import pandas as pd
import numpy as np

def split_train_test(events_df: pd.DataFrame, test_ratio: float = 0.2) -> tuple:
    """
    Executes a strict chronological dataset split.
    Prevents data leakage. Trains purely on past history and predicts strictly on future 
    unseen purchases to validate genuine pattern recognition.
    """
    df = events_df.sort_values('timestamp')
    purchases = df[df['event'] == 'transaction']
    
    if purchases.empty:
        split_idx = int(len(df) * (1 - test_ratio))
        return df.iloc[:split_idx], df.iloc[split_idx:]
        
    split_idx = int(len(purchases) * (1 - test_ratio))
    split_time = purchases.iloc[split_idx]['timestamp']
    
    train_set = df[df['timestamp'] <= split_time]
    test_purchases = purchases[purchases['timestamp'] > split_time]
    
    return train_set, test_purchases

def get_ground_truth(test_purchases: pd.DataFrame) -> dict:
    """Constructs visitorid -> set of purchased itemids."""
    return test_purchases.groupby('visitorid')['itemid'].apply(set).to_dict()

def calculate_metrics_at_k(recommendations_df: pd.DataFrame, truth_dict: dict, k: int = 10) -> dict:
    """
    Set-based metrics: Hit Rate and Precision @K.
    These check WHETHER the right items are in the list, regardless of position.
    """
    hits = 0
    total_users_evaluated = 0
    precision_sum = 0.0
    
    grouped = recommendations_df.groupby('visitorid')
    
    for visitor, group in grouped:
        if visitor not in truth_dict:
            continue
            
        top_k_items = group.head(k)['itemid'].tolist()
        actual_items = truth_dict[visitor]
        
        if any(item in actual_items for item in top_k_items):
            hits += 1
            
        hits_in_k = sum(1 for item in top_k_items if item in actual_items)
        precision_sum += (hits_in_k / k)
        
        total_users_evaluated += 1
        
    if total_users_evaluated == 0:
        return {'hit_rate_at_k': 0.0, 'precision_at_k': 0.0, 'users_evaluated': 0}
        
    return {
        'hit_rate_at_k': hits / total_users_evaluated,
        'precision_at_k': precision_sum / total_users_evaluated,
        'users_evaluated': total_users_evaluated
    }

def calculate_business_yield(recommendations_df: pd.DataFrame, truth_dict: dict, item_features_df: pd.DataFrame, k: int = 10) -> float:
    """
    Flat yield: sums margin for every recommended item that matches a real purchase.
    Position-agnostic. 
    """
    margin_map = item_features_df.set_index('itemid')['margin'].to_dict()
    total_yield = 0.0
    
    grouped = recommendations_df.groupby('visitorid')
    
    for visitor, group in grouped:
        if visitor not in truth_dict:
            continue
            
        top_k_items = group.head(k)['itemid'].tolist()
        actual_items = truth_dict[visitor]
        
        for item in top_k_items:
            if item in actual_items:
                total_yield += margin_map.get(item, 0.0)
                
    return total_yield

def calculate_position_weighted_yield(recommendations_df: pd.DataFrame, truth_dict: dict, item_features_df: pd.DataFrame, k: int = 10) -> float:
    """
    Position-weighted yield (DCG-style): rewards putting high-margin purchased items 
    at TOP positions where real-world click probability is highest.
    
    Formula: sum( margin_i / log2(position_i + 1) ) for each purchased item hit.
    
    Position 1 gets full weight, position 2 gets /1.58, position 5 gets /2.58, etc.
    This is the TRUE metric that captures the decision layer's reordering benefit.
    """
    margin_map = item_features_df.set_index('itemid')['margin'].to_dict()
    total_weighted_yield = 0.0
    
    grouped = recommendations_df.groupby('visitorid')
    
    for visitor, group in grouped:
        if visitor not in truth_dict:
            continue
            
        top_k_items = group.head(k)['itemid'].tolist()
        actual_items = truth_dict[visitor]
        
        for position, item in enumerate(top_k_items, start=1):
            if item in actual_items:
                total_weighted_yield += margin_map.get(item, 0.0) / np.log2(position + 1)
                
    return total_weighted_yield

def calculate_ndcg_at_k(recommendations_df: pd.DataFrame, truth_dict: dict, k: int = 10) -> float:
    """
    Normalized Discounted Cumulative Gain @K.
    
    Measures ranking quality by comparing the actual recommendation order against
    the ideal (perfect) ordering. A score of 1.0 means every relevant item is 
    placed at the highest possible position; lower scores indicate suboptimal ordering.
    
    Formula:
        DCG  = Σ rel_i / log₂(i + 1)    for i in 1..K
        IDCG = Σ rel_i / log₂(i + 1)    for the ideal (sorted) ordering
        NDCG = DCG / IDCG
    
    Uses binary relevance: rel_i = 1 if item was purchased, 0 otherwise.
    """
    ndcg_scores = []
    grouped = recommendations_df.groupby('visitorid')
    
    for visitor, group in grouped:
        if visitor not in truth_dict:
            continue
            
        top_k_items = group.head(k)['itemid'].tolist()
        actual_items = truth_dict[visitor]
        
        # Binary relevance vector: 1 if purchased, 0 otherwise
        relevance = [1.0 if item in actual_items else 0.0 for item in top_k_items]
        
        # DCG: sum of relevance / log2(position + 1)
        dcg = sum(rel / np.log2(pos + 2) for pos, rel in enumerate(relevance))
        
        # IDCG: ideal ordering — all 1s first, then 0s
        ideal_relevance = sorted(relevance, reverse=True)
        idcg = sum(rel / np.log2(pos + 2) for pos, rel in enumerate(ideal_relevance))
        
        if idcg > 0:
            ndcg_scores.append(dcg / idcg)
        else:
            # No relevant items in ground truth for this user — skip
            ndcg_scores.append(0.0)
    
    return np.mean(ndcg_scores) if ndcg_scores else 0.0

def calculate_mrr(recommendations_df: pd.DataFrame, truth_dict: dict, k: int = 10) -> float:
    """
    Mean Reciprocal Rank @K.
    
    Measures how quickly the system surfaces the FIRST relevant item.
    High MRR = relevant items appear near the top of the list.
    
    Formula:
        RR  = 1 / rank_of_first_relevant_item    (0 if no hit in top-K)
        MRR = mean(RR) across all users
    
    Critical for user experience: users rarely scroll past the first few results.
    """
    reciprocal_ranks = []
    grouped = recommendations_df.groupby('visitorid')
    
    for visitor, group in grouped:
        if visitor not in truth_dict:
            continue
            
        top_k_items = group.head(k)['itemid'].tolist()
        actual_items = truth_dict[visitor]
        
        rr = 0.0
        for position, item in enumerate(top_k_items, start=1):
            if item in actual_items:
                rr = 1.0 / position
                break
        
        reciprocal_ranks.append(rr)
    
    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0

def evaluate_dual_system(ranked_df: pd.DataFrame, decision_df: pd.DataFrame, 
                         test_purchases: pd.DataFrame, item_features_df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """
    Diagnostic Orchestrator.
    Compares baseline behavioral ranking vs business-enhanced decisioning using:
    - Set-based metrics (Hit Rate, Precision, Flat Yield) — same items → same scores
    - Ranking-quality metrics (NDCG, MRR) — captures ordering effectiveness
    - Position-weighted yield (DCG-Margin) — captures reordering benefit
    """
    truth_dict = get_ground_truth(test_purchases)
    
    ml_metrics = calculate_metrics_at_k(ranked_df, truth_dict, k=k)
    ml_yield = calculate_business_yield(ranked_df, truth_dict, item_features_df, k=k)
    ml_pw_yield = calculate_position_weighted_yield(ranked_df, truth_dict, item_features_df, k=k)
    ml_ndcg = calculate_ndcg_at_k(ranked_df, truth_dict, k=k)
    ml_mrr = calculate_mrr(ranked_df, truth_dict, k=k)
    
    bus_metrics = calculate_metrics_at_k(decision_df, truth_dict, k=k)
    bus_yield = calculate_business_yield(decision_df, truth_dict, item_features_df, k=k)
    bus_pw_yield = calculate_position_weighted_yield(decision_df, truth_dict, item_features_df, k=k)
    bus_ndcg = calculate_ndcg_at_k(decision_df, truth_dict, k=k)
    bus_mrr = calculate_mrr(decision_df, truth_dict, k=k)
    
    result = {
        'Evaluation Metric': [
            f'Hit Rate @{k}', 
            f'Precision @{k}', 
            f'NDCG @{k}',
            f'MRR @{k}',
            'Margin Yield ($)',
            'Position-Weighted Yield ($)'
        ],
        'Baseline (Behavioral)': [
            round(ml_metrics['hit_rate_at_k'], 4), 
            round(ml_metrics['precision_at_k'], 4), 
            round(ml_ndcg, 4),
            round(ml_mrr, 4),
            round(ml_yield, 2),
            round(ml_pw_yield, 2)
        ],
        'Decision Engine': [
            round(bus_metrics['hit_rate_at_k'], 4), 
            round(bus_metrics['precision_at_k'], 4), 
            round(bus_ndcg, 4),
            round(bus_mrr, 4),
            round(bus_yield, 2),
            round(bus_pw_yield, 2)
        ]
    }
    
    return pd.DataFrame(result)
