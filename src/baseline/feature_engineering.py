import pandas as pd
import numpy as np
import hashlib

def simulate_business_features(item_ids: list) -> pd.DataFrame:
    """
    Deterministically simulates price, margin, and category_id for each item 
    using MD5 hashing so that results remain permanently stable across runs.
    """
    features = []
    
    for item in item_ids:
        # Convert item to stable byte string for hashing
        item_str = str(item).encode('utf-8')
        hash_digest = hashlib.md5(item_str).hexdigest()
        
        # Convert hash substrings to integers for pseudo-random bounds
        hash_val_1 = int(hash_digest[:8], 16)
        hash_val_2 = int(hash_digest[8:16], 16)
        hash_val_3 = int(hash_digest[16:24], 16)
        
        # Price: Range 10 to 500
        price = 10 + (hash_val_1 % 491)
        
        # Margin %: Range 10% to 40% (0.10 to 0.40)
        margin_pct = 0.10 + ((hash_val_2 % 31) / 100)
        margin_dollars = round(price * margin_pct, 2)
        
        # Category ID: Simulate 50 distinct categories (0 to 49)
        category_id = hash_val_3 % 50
        
        features.append({
            'itemid': item,
            'price': price,
            'margin': margin_dollars,
            'category_id': category_id
        })
        
    return pd.DataFrame(features)

def calculate_item_popularity(df_interactions: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates purely global normalized popularity for all items based to 
    their sum total of interaction weights.
    Returns: df with ['itemid', 'popularity_score'] scaled between 0.0 and 1.0.
    """
    pop_df = df_interactions.groupby('itemid')['interaction_weight'].sum().reset_index()
    
    min_pop = pop_df['interaction_weight'].min()
    max_pop = pop_df['interaction_weight'].max()
    
    if max_pop == min_pop:
        pop_df['popularity_score'] = 1.0
    else:
        pop_df['popularity_score'] = (pop_df['interaction_weight'] - min_pop) / (max_pop - min_pop)
        
    return pop_df[['itemid', 'popularity_score']]

def calculate_recency(df_interactions: pd.DataFrame, half_life_days: float = 7.0) -> pd.DataFrame:
    """
    Calculates an exponentially decaying recency score for user-item interactions.
    Recent views score closer to 1.0; older behaviors mathematically decay.
    """
    df = df_interactions[['visitorid', 'itemid', 'timestamp']].copy()
    
    # Establish 'now' as the most recent timestamp in the entire dataset log
    max_time = df['timestamp'].max()
    
    # Calculate temporal difference in days
    df['days_ago'] = (max_time - df['timestamp']).dt.total_seconds() / (24 * 60 * 60)
    
    # Exponential decay formula: Score = e^(-lambda * t), where lambda = ln(2) / half_life
    decay_constant = np.log(2) / half_life_days
    df['recency_score'] = np.exp(-decay_constant * df['days_ago'])
    
    # Keep the maximum (most recent) score if a user interacted multiple times
    recency_df = df.groupby(['visitorid', 'itemid'])['recency_score'].max().reset_index()
    
    return recency_df
