import json
from four_pillars import calculate_four_pillars

r = calculate_four_pillars('2026-07-02')
with open('fp_test.json', 'w', encoding='utf-8') as f:
    json.dump(r, f, ensure_ascii=False, indent=2)
print("Done")