import pandas as pd

def load_events(filepath: str) -> pd.DataFrame:
    """
    Loads Retailrocket events dataset, parses timestamps, and filters columns.
    Assumes timestamp is in Unix milliseconds format.
    """
    df = pd.read_csv(filepath)
    
    cols = ['visitorid', 'itemid', 'event', 'timestamp']
    if not all(col in df.columns for col in cols):
        raise ValueError(f"Dataset missing required columns. Expected: {cols}")
        
    df = df[cols].copy()
    
    # Retailrocket commonly stores timestamps as Unix epoch in milliseconds
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
    
    return df.dropna(subset=['timestamp'])

def create_interaction_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maps string events ('view', 'addtocart', 'transaction') to numeric weights.
    """
    weights = {
        'view': 1.0,
        'addtocart': 3.0,
        'transaction': 5.0
    }
    
    # Create the interaction weight. Non-matching events become NaN and are dropped.
    df['interaction_weight'] = df['event'].map(weights)
    return df.dropna(subset=['interaction_weight'])

def aggregate_user_item_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates interaction weights by (visitorid, itemid) to create a 
    single historical preference score per user-item pair.
    """
    agg_df = df.groupby(['visitorid', 'itemid'])['interaction_weight'].sum().reset_index()
    agg_df.rename(columns={'interaction_weight': 'user_preference_score'}, inplace=True)
    return agg_df

def process_pipeline(filepath: str):
    """
    Wrapper function to execute the full data processing pipeline end-to-end.
    Returns the mapped interaction log and the aggregated preference matrix.
    """
    raw_df = load_events(filepath)
    interaction_df = create_interaction_signals(raw_df)
    preference_df = aggregate_user_item_scores(interaction_df)
    
    return interaction_df, preference_df
