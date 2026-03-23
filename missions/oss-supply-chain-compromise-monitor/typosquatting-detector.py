#!/usr/bin/env python3
# Task: Typosquatting detector | Mission: OSS Supply Chain Compromise Monitor
"""
Detects typosquatting on popular packages using edit-distance, keyboard adjacency,
and homoglyph substitution.

Install: pip install (stdlib only)
Usage:   python typosquatting-detector.py
"""
import re, json
from difflib import SequenceMatcher
from typing import List, Tuple

POPULAR = {"npm": ["react","vue","angular","express","lodash","axios","webpack","babel","eslint",
                   "prettier","typescript","next","jest","mocha","chalk","commander","dotenv"],
           "pypi": ["requests","numpy","pandas","flask","django","scipy","tensorflow","torch",
                    "boto3","pytest","pillow","sqlalchemy","fastapi","pydantic","cryptography"]}
HOMOGLYPHS = {"a":["4","@"],"e":["3"],"i":["1","l"],"l":["1","I"],"o":["0"],"s":["5","$"]}
KEYBOARD = {"q":"wa","w":"qeas","e":"wsdr","r":"edft","t":"rfgy","y":"tghu","u":"yhji",
            "i":"ujko","o":"iklp","p":"ol","a":"qwsz","s":"awedxz","d":"serfcx",
            "f":"drtgvc","g":"ftyhbv","h":"gyujnb","j":"huikmn","k":"jiolm","l":"kop"}

def edit_dist(s1,s2):
    m,n=len(s1),len(s2); dp=list(range(n+1))
    for i in range(1,m+1):
        prev=dp[:]; dp[0]=i
        for j in range(1,n+1):
            dp[j]=min(prev[j]+1,dp[j-1]+1,prev[j-1]+(s1[i-1]!=s2[j-1]))
    return dp[n]

def check_package(name:str, registry:str="npm") -> List[Tuple]:
    results=[]; name_l=name.lower()
    for pop in POPULAR.get(registry,[]):
        d=edit_dist(name_l,pop.lower())
        sim=1.0-d/max(len(name_l),len(pop))
        if d==1: results.append((pop,"edit_distance_1",sim))
        elif d==2 and len(pop)>=6: results.append((pop,"edit_distance_2",sim))
        elif SequenceMatcher(None,name_l,pop.lower()).ratio()>0.85 and name_l!=pop.lower():
            if not any(r[0]==pop for r in results): results.append((pop,"high_similarity",sim))
    return sorted(results,key=lambda x:x[2],reverse=True)

def bulk_scan(packages:List[str], registry:str="npm") -> dict:
    flagged={}
    for pkg in packages:
        hits=check_package(pkg,registry)
        if hits: flagged[pkg]=[{"target":h[0],"type":h[1],"score":round(h[2],3)} for h in hits]
    return flagged

if __name__=="__main__":
    test=["reqeusts","reqests","numpyy","flask2","djang0","reacts","reactt","lodsh","axois","exprss"]
    print("=== Typosquatting Scan ===")
    r=bulk_scan(test,"pypi"); r.update(bulk_scan(test,"npm"))
    print(json.dumps(r,indent=2))
    print(f"\nFlagged {len(r)}/{len(test)} packages as potential typosquats")
