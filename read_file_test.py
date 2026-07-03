# -*- coding: utf-8 -*-
with open('generate_ai_prediction.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if i <= 30:
            print(f"{i}: {line}", end='')
        else:
            break