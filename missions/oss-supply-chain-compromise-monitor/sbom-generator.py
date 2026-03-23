#!/usr/bin/env python3
# Task: SBOM generator | Mission: OSS Supply Chain Compromise Monitor
"""
Generates CycloneDX SBOM for Python projects with vulnerability cross-references.

Install: pip install (stdlib only)
Usage:   python sbom-generator.py  # generates sbom.json
"""
import json, subprocess, urllib.request, urllib.error, uuid
from datetime import datetime, timezone
from typing import Optional

def get_pkgs():
    return json.loads(subprocess.run(["pip","list","--format=json"],capture_output=True,text=True).stdout)

def get_meta(name,version):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json",timeout=5) as r:
            info=json.load(r).get("info",{})
            return {"license":info.get("license","UNKNOWN"),"home_page":info.get("home_page",""),"summary":info.get("summary","")}
    except: return {"license":"UNKNOWN","home_page":"","summary":""}

def get_vulns(name,version):
    payload=json.dumps({"version":version,"package":{"name":name,"ecosystem":"PyPI"}}).encode()
    try:
        req=urllib.request.Request("https://api.osv.dev/v1/query",data=payload,
            headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=5) as r:
            return [{"id":v["id"],"summary":v.get("summary","")} for v in json.load(r).get("vulns",[])]
    except: return []

def get_hash(name,version):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json",timeout=5) as r:
            for f in json.load(r).get("urls",[]):
                if d:=f.get("digests",{}).get("sha256"): return d
    except: return None

def gen_sbom(output="sbom.json",check_vulns=True):
    pkgs=get_pkgs(); components=[]
    for i,pkg in enumerate(pkgs):
        n,v=pkg["name"],pkg["version"]
        print(f"[{i+1}/{len(pkgs)}] {n}=={v}")
        meta=get_meta(n,v); h=get_hash(n,v); vulns=get_vulns(n,v) if check_vulns else []
        c={"type":"library","bom-ref":f"pkg:pypi/{n.lower()}@{v}","name":n,"version":v,
           "purl":f"pkg:pypi/{n.lower()}@{v}","description":meta["summary"],
           "licenses":[{"license":{"name":meta["license"]}}] if meta["license"]!="UNKNOWN" else [],
           "externalReferences":[]}
        if meta["home_page"]: c["externalReferences"].append({"type":"website","url":meta["home_page"]})
        if h: c["hashes"]=[{"alg":"SHA-256","content":h}]
        if vulns: c["vulnerabilities"]=vulns
        components.append(c)
    sbom={"bomFormat":"CycloneDX","specVersion":"1.5","serialNumber":f"urn:uuid:{uuid.uuid4()}",
          "version":1,"metadata":{"timestamp":datetime.now(timezone.utc).isoformat(),
          "tools":[{"name":"swarmpulse-sbom-generator","version":"1.0.0"}]},"components":components}
    with open(output,"w") as f: json.dump(sbom,f,indent=2)
    vc=sum(len(c.get("vulnerabilities",[])) for c in components)
    print(f"\nSBOM → {output} | {len(components)} components | {vc} vulns found")
    return sbom

if __name__=="__main__":
    gen_sbom("sbom.json",check_vulns=True)
