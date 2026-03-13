# -*- coding: utf-8 -*-
"""
Created on Mon Jan 12 00:29:41 2026

@author: BlankAdventure
"""

import itertools
import time

from models import CerebrasModel, GeminiModel, get_acro, get_acro_safe


def gemini(name, temp, top_p, word):
    llm = GeminiModel(temperature=temp, top_p=top_p, model_name=name)
    print(out)
    return out


def cerebras(name, temp, top_p, word):
    llm = CerebrasModel(
        model_name=name, temperature=temp, top_p=top_p, reasoning_effort="high"
    )
    out = get_acro_safe(llm, word)
    print(out)
    return out


# names = ["gemini-2.5-flash"]
names = ["gpt-oss-120b"]
#temps = [0.4, 0.8, 1.2, 1.6, 2.0]
temps = [0.3, 0.6, 0.9, 1.2, 1.5] #should be max 1.5
top_p = [0.25, 0.50, 0.75, 1.0]
word_list = ["beer", "hash", "drunk", "sister", "tomorrow", "yesterday"]


results = []
iters = 5
combinations = list(itertools.product(names, temps, top_p, word_list))
total = len(combinations)
for i, comb in enumerate(combinations):
    for _ in range(iters):
        out = cerebras(*comb)
        print(f"{i}/{total} - {comb}, {out[0]}")
        results.append( (*comb,out[0]) )
        time.sleep(3)

# 72/120 (failed on 73)
# CATCH:
# UnprocessableEntityError



