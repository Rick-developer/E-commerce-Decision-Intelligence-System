import os
import sys
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

from data_processing import load_events, create_interaction_signals, aggregate_user_item_scores
from feature_engineering import simulate_business_features, calculate_item_popularity, calculate_recency
from candidate_generation import build_cooccurrence_matrix, generate_candidates
from ranking import rank_candidates
from decision import make_decisions
from evaluation import split_train_test, evaluate_dual_system

def run_pipeline(filepath: str, max_users_to_evaluate: int = 100, top_k: int = 20):
    if not os.path.exists(filepath):
        print(f"Error: Dataset not found at {filepath}")
        return

    print("1. Loading dataset & test environment...")
    events_df = load_events(filepath)
    train_df, test_purchases = split_train_test(events_df)
    
    inter_df = create_interaction_signals(train_df)
    user_pref_df = aggregate_user_item_scores(inter_df)

    unique_items = inter_df['itemid'].unique()
    item_features_df = simulate_business_features(unique_items)
    pop_df = calculate_item_popularity(inter_df)
    
    item_features_df = pd.merge(item_features_df, pop_df, on='itemid', how='left')
    item_features_df['popularity_score'] = item_features_df['popularity_score'].fillna(0.0)
    
    recency_df = calculate_recency(inter_df)
    cooc_matrix = build_cooccurrence_matrix(inter_df)

    print("\n2. Executing pipeline per user...")
    test_users = test_purchases['visitorid'].unique()[:max_users_to_evaluate]
    
    all_ranked_lists = []
    all_decision_lists = []
    
    users_processed = 0
    users_skipped = 0
    total_candidates_generated = 0
    debug_users_printed = 0
    
    for visitor in test_users:
        candidates = generate_candidates(
            visitorid=visitor, 
            user_pref_df=user_pref_df, 
            popular_df=pop_df,
            cooccur_matrix=cooc_matrix, 
            item_features_df=item_features_df,
            n_per_source=50,
            max_cat_limit=25
        )
        
        if candidates is None or candidates.empty:
            users_skipped += 1
            continue
            
        total_candidates_generated += len(candidates)
        
        ranked = rank_candidates(candidates, user_pref_df, item_features_df, recency_df)
        
        # CRITICAL FIX: Pass ONLY the behavioral top-K to the decision layer.
        # This ensures both systems operate on the EXACT same item set.
        # The decision layer can only REORDER these items, not swap in new ones.
        behavioral_top_k = ranked.head(top_k).copy()
        
        decided = make_decisions(
            ranked_df=behavioral_top_k, 
            item_features_df=item_features_df, 
            alpha=0.15, 
            top_k=top_k
        )
        
        # Debug diagnostics for first 2 users
        if debug_users_printed < 2:
            print(f"\n--- DEBUG: User {visitor} ---")
            print("Behavioral Top 5:")
            print(behavioral_top_k[['itemid', 'behavioral_score']].head(5).to_string(index=False))
            print("Decision Top 5:")
            print(decided[['itemid', 'decision_score']].head(5).to_string(index=False))
            
            # Show if any reordering happened
            ranked_order = behavioral_top_k['itemid'].head(10).tolist()
            decided_order = decided['itemid'].head(10).tolist()
            if ranked_order != decided_order:
                print(">>> ORDER CHANGED by decision layer")
            else:
                print(">>> Order unchanged")
            debug_users_printed += 1

        all_ranked_lists.append(behavioral_top_k) 
        all_decision_lists.append(decided)
        
        users_processed += 1

    if users_processed == 0:
        return

    avg_candidates = round(total_candidates_generated / users_processed, 1)
    print(f"\n--- Telemetry ---")
    print(f"Users evaluated: {users_processed} | Skipped: {users_skipped} | Avg candidates: {avg_candidates}")

    final_ranked_df = pd.concat(all_ranked_lists, ignore_index=True)
    final_decision_df = pd.concat(all_decision_lists, ignore_index=True)

    evaluation_report = evaluate_dual_system(
        ranked_df=final_ranked_df, 
        decision_df=final_decision_df, 
        test_purchases=test_purchases, 
        item_features_df=item_features_df, 
        k=top_k
    )
    print("\n=============================================")
    print("      SYSTEM PERFORMANCE vs TRUE EVENTS      ")
    print("=============================================")
    print(evaluation_report.to_string(index=False))

    # Source breakdown
    print("\n--- Source Breakdown (Decision Layer) ---")
    print(final_decision_df['source'].value_counts().to_string())

    # Metric insights
    baseline_yield = float(evaluation_report[evaluation_report['Evaluation Metric'] == 'Margin Yield ($)']['Baseline (Behavioral)'].values[0])
    decision_yield = float(evaluation_report[evaluation_report['Evaluation Metric'] == 'Margin Yield ($)']['Decision Engine'].values[0])
    
    baseline_pw = float(evaluation_report[evaluation_report['Evaluation Metric'] == 'Position-Weighted Yield ($)']['Baseline (Behavioral)'].values[0])
    decision_pw = float(evaluation_report[evaluation_report['Evaluation Metric'] == 'Position-Weighted Yield ($)']['Decision Engine'].values[0])
    
    pw_lift = ((decision_pw - baseline_pw) / baseline_pw) * 100 if baseline_pw > 0 else 0.0

    print(f"\n--- METRIC INSIGHTS ---")
    print(f"Margin Yield:            Baseline ${baseline_yield} | Decision ${decision_yield}")
    print(f"Position-Weighted Yield: Baseline ${baseline_pw} | Decision ${decision_pw}")
    print(f"Position-Weighted Lift:  {pw_lift:+.2f}%")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        TARGET_FILE = sys.argv[1]
    else:
        TARGET_FILE = "data/events.csv"
        
    run_pipeline(TARGET_FILE, max_users_to_evaluate=50, top_k=20)
