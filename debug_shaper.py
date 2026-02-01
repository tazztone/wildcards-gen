from ruamel.yaml.comments import CommentedMap
from wildcards_gen.core.shaper import ConstraintShaper

def test_shaping():
    root = CommentedMap()
    
    # 1. Large List (Should survive merging, check casing)
    root['large_key'] = [f'item{i}' for i in range(20)]
    
    # 2. Tiny List (Should be merged)
    root['tiny_list'] = ['a', 'b']
    
    shaper = ConstraintShaper(root)
    result = shaper.shape(min_leaf_size=10)
    
    print("Result Keys:", list(result.keys()))
    
    if 'Large_key' in result:
        print("✅ Casing fixed")
    elif 'Large_Key' in result: # title() makes it Large_key if input is large_key? No, 'Large_key'
        print("✅ Casing fixed (alt)")
    elif 'large_key' in result:
        print("❌ Casing failed: Key remains lowercase")
        
    if 'tiny_list' not in result:
        print("✅ Merging worked (tiny_list gone)")

if __name__ == "__main__":
    test_shaping()