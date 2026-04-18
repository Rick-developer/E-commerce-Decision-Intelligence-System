import pandas as pd

def get_user_history(user_pref_df: pd.DataFrame, visitorid: int, n: int = 50) -> pd.DataFrame:
    user_data = user_pref_df[user_pref_df['visitorid'] == visitorid]
    top_items = user_data.nlargest(n, 'user_preference_score')[['itemid', 'user_preference_score']].copy()
    top_items.rename(columns={'user_preference_score': 'candidate_score'}, inplace=True)
    top_items['source'] = 'history'
    return top_items

def get_global_popular(popular_df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    top_items = popular_df.nlargest(n, 'popularity_score')[['itemid', 'popularity_score']].copy()
    top_items.rename(columns={'popularity_score': 'candidate_score'}, inplace=True)
    top_items['source'] = 'global'
    return top_items

def build_cooccurrence_matrix(interaction_df: pd.DataFrame) -> pd.DataFrame:
    user_items = interaction_df[['visitorid', 'itemid']].drop_duplicates()
    
    user_counts = user_items.groupby('visitorid').size()
    valid_users = user_counts[user_counts <= 50].index
    user_items = user_items[user_items['visitorid'].isin(valid_users)]
    
    co_occur = pd.merge(user_items, user_items, on='visitorid')
    co_occur = co_occur[co_occur['itemid_x'] != co_occur['itemid_y']]
    
    matrix = co_occur.groupby(['itemid_x', 'itemid_y']).size().reset_index(name='strength')
    matrix.rename(columns={'itemid_x': 'item_id', 'itemid_y': 'related_item_id'}, inplace=True)
    return matrix

def get_cooccurrence_candidates(user_pref_df: pd.DataFrame, cooccur_matrix: pd.DataFrame, visitorid: int, n: int = 50) -> pd.DataFrame:
    # Expanded Seed Base to 30 for broader co-occurrence network footprint
    user_items = user_pref_df[user_pref_df['visitorid'] == visitorid].nlargest(30, 'user_preference_score')
    
    if user_items.empty:
        return pd.DataFrame(columns=['itemid', 'candidate_score', 'source'])
        
    seed_item_ids = user_items['itemid'].unique()
    related = cooccur_matrix[cooccur_matrix['item_id'].isin(seed_item_ids)]
    
    agg_related = related.groupby('related_item_id')['strength'].sum().reset_index()
    agg_related.rename(columns={'related_item_id': 'itemid', 'strength': 'candidate_score'}, inplace=True)
    
    all_purchased_items = user_pref_df[user_pref_df['visitorid'] == visitorid]['itemid'].unique()
    agg_related = agg_related[~agg_related['itemid'].isin(all_purchased_items)]
    
    top_cands = agg_related.nlargest(n, 'candidate_score')[['itemid', 'candidate_score']].copy()
    top_cands['source'] = 'cooccurrence'
    return top_cands

def apply_diversity_constraint(candidates_df: pd.DataFrame, item_features_df: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    priority_map = {'history': 1, 'cooccurrence': 2, 'global': 3}
    candidates_df['priority'] = candidates_df['source'].map(priority_map)
    
    merged = pd.merge(candidates_df, item_features_df[['itemid', 'category_id']], on='itemid', how='left')
    
    merged = merged.sort_values(
        by=['visitorid', 'priority', 'candidate_score'], 
        ascending=[True, True, False]
    )
    
    merged['category_tally'] = merged.groupby(['visitorid', 'category_id']).cumcount()
    filtered = merged[merged['category_tally'] < limit]
    
    return filtered[['visitorid', 'itemid', 'source', 'candidate_score']]

def generate_candidates(visitorid: int, user_pref_df: pd.DataFrame, popular_df: pd.DataFrame, 
                        cooccur_matrix: pd.DataFrame, item_features_df: pd.DataFrame, 
                        n_per_source: int = 50, max_cat_limit: int = 25) -> pd.DataFrame:
    """
    Candidate generation uses ONLY relevance-based sources: history, co-occurrence, popularity.
    Margin optimization happens downstream in the decision layer, which reorders these 
    candidates by margin. Injecting pure-margin candidates here dilutes the pool with 
    items the user has zero intent for, destroying both precision and yield.
    """
    hist_cands = get_user_history(user_pref_df, visitorid, n=n_per_source)
    cooc_cands = get_cooccurrence_candidates(user_pref_df, cooccur_matrix, visitorid, n=n_per_source)
    global_cands = get_global_popular(popular_df, n=n_per_source)
    
    combined = pd.concat([hist_cands, cooc_cands, global_cands], ignore_index=True)
    combined['visitorid'] = visitorid
    
    priority_map = {'history': 1, 'cooccurrence': 2, 'global': 3}
    combined['temp_priority'] = combined['source'].map(priority_map)
    combined = combined.sort_values(by=['temp_priority', 'candidate_score'], ascending=[True, False])
    
    combined = combined.drop_duplicates(subset=['itemid'], keep='first')
    combined = combined.drop(columns=['temp_priority'])
    
    final_candidates = apply_diversity_constraint(combined, item_features_df, limit=max_cat_limit)
    return final_candidates
