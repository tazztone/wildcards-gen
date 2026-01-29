
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wildcards_gen.core.arranger import arrange_list, load_embedding_model, compute_list_embeddings, get_hdbscan_clusters

# Configure logging
logging.basicConfig(level=logging.INFO)

# Foodstuff list extracted from the YAML output
FOODSTUFF_ITEMS = [
    "Chinese anise", "Chinese brown sauce", "Nantua", "Soubise", "Spam", "Tabasco", 
    "aioli", "barley", "basil", "batter", "bay leaf", "bearnaise", "black olive", 
    "borage", "bourguignon", "bread sauce", "brown sauce", "butter", "canned food", 
    "carbonara", "cardamom", "carrot juice", "catsup", "cayenne", "chili sauce", 
    "chives", "chocolate sauce", "chutney", "cider vinegar", "clabber", "clary sage", 
    "clotted cream", "clove", "cocktail sauce", "cocoa", "comfrey", "coriander", 
    "curd", "curry sauce", "demiglace", "dip", "egg", "filling", "frozen food", 
    "garlic", "garlic chive", "gravy", "green mayonnaise", "green olive", "grenadine", 
    "groats", "guacamole", "hard sauce", "heavy cream", "hollandaise", "honey", 
    "horseradish", "horseradish sauce", "hot sauce", "hummus", "hyssop", "juice", 
    "juniper berries", "lemon balm", "light cream", "maple syrup", "marinade", 
    "marjoram", "mayonnaise", "millet", "mint sauce", "miso", "mocha", "mustard sauce", 
    "nasturtium", "nutmeg", "oatmeal", "oolong", "paddy", "paprika", "parsley", 
    "pepper sauce", "pesto", "phyllo", "plum sauce", "popcorn", "poulette", 
    "powdered sugar", "puff paste", "ravigote", "relish", "rosemary", "roughage", 
    "saffron", "sage", "sassafras", "sesame seed", "snail butter", "sorghum", 
    "souchong", "soy sauce", "stick cinnamon", "stuffing", "sugar", "sweet corn", 
    "sweet woodruff", "tea bag", "thyme", "tomato sauce", "turmeric", "vanilla bean", 
    "veloute", "wasabi", "wheat", "whey", "whipping cream", "white sauce", 
    "whole wheat flour", "wild rice", "wine sauce"
]




def debug_run():
    print(f"Testing Arrangement on {len(FOODSTUFF_ITEMS)} items...")
    
    # Test 1: Standard 'eom' (Pass 1) -> Low confidence (Pass 2)
    # Using defaults (min_cluster=3 for pass 1 if we updated it, but let's be explicit)
    print("\n--- Testing Multi-Pass Arrangement (EOM=3 -> Leaf=2) ---")
    
    groups, leftovers, stats = arrange_list(
        FOODSTUFF_ITEMS, 
        model_name="minilm", 
        threshold=0.1, 
        min_cluster_size=3,
        cluster_selection_method='eom',
        return_stats=True
    )
    
    print(f"Total Groups: {len(groups)}")
    if stats:
        print(f"Pass 1 Noise Ratio: {stats.get('pass_1', {}).get('noise_ratio', 0):.2%}")
        if stats.get('pass_2'):
             print(f"Pass 2 Clusters Found: {stats['pass_2']['n_clusters_found']}")
        
    for name, items in groups.items():
        print(f"  {name} ({len(items)}): {items[:3]}...")

    print(f"Leftovers ({len(leftovers)}): {leftovers[:5]}...")
    
    # Test 2: Ultra-Flat Preset config ('leaf' method)
    print("\n--- Testing Ultra-Flat Config (Leaf=3 -> Leaf=2) ---")
    groups, leftovers, stats = arrange_list(
        FOODSTUFF_ITEMS, 
        model_name="minilm", 
        threshold=0.1, 
        min_cluster_size=3,
        cluster_selection_method='leaf',
        return_stats=True
    )
    
    print(f"Total Groups: {len(groups)}")
    for name, items in groups.items():
        print(f"  {name} ({len(items)}): {items[:3]}...")




if __name__ == "__main__":
    debug_run()
