#!/usr/bin/env python3
# Task: Anomaly scoring engine | Mission: SaaS Breach Detection via Behavioral Analytics
"""
Multi-factor anomaly scoring: compares events against user baselines.
Outputs 0-100 risk score with risk level and recommended action.

Install: pip install (stdlib only)
Usage:   python anomaly-scoring-engine.py
"""
import math, json
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class AnomalyScore:
    event_id: str; user_id: str; base_score: float = 0.0
    risk_factors: list = field(default_factory=list)
    final_score: float = 0.0; risk_level: str = "LOW"; recommended_action: str = "log"

def score_event(event:dict, baseline:dict) -> AnomalyScore:
    s=AnomalyScore(event_id=event.get("event_id",""),user_id=event.get("actor_id",""))
    total=0.0
    # Login time
    try:
        h=datetime.fromisoformat(event.get("timestamp","")).hour
        p10,p90=baseline.get("typical_hours",(8,18))
        if h<p10 or h>p90: total+=25.0; s.risk_factors.append(f"unusual_hour:{h} (typical {p10}-{p90})")
    except: pass
    # New IP
    ip=event.get("ip_address",""); known=set(baseline.get("known_ips",{}).keys())
    if ip and ip not in known: total+=20.0; s.risk_factors.append(f"new_ip:{ip}")
    # New country
    country=event.get("country","US"); known_c=set(baseline.get("known_countries",["US"]))
    if country not in known_c: total+=30.0; s.risk_factors.append(f"new_country:{country}")
    # Sensitive action
    sensitive={"GetSecretValue","DeleteUser","CreateAccessKey","export","bulk_download","permission_change"}
    if event.get("action","") in sensitive: total+=25.0; s.risk_factors.append(f"sensitive:{event['action']}")
    # Auth failures
    fails=baseline.get("auth_failures_7d",0)
    if fails>=5: m=1.0+(fails-5)*0.1; total*=m; s.risk_factors.append(f"high_auth_failures:{fails}")
    # Non-browser UA
    ua=event.get("user_agent","").lower()
    if ua and not any(b in ua for b in ["chrome","firefox","safari","edge","mozilla"]):
        total+=10.0; s.risk_factors.append(f"non_browser:{ua[:30]}")
    s.base_score=round(min(total,100.0),1); s.final_score=s.base_score
    if s.final_score>=75: s.risk_level="CRITICAL"; s.recommended_action="block_and_alert"
    elif s.final_score>=50: s.risk_level="HIGH"; s.recommended_action="mfa_challenge"
    elif s.final_score>=25: s.risk_level="MEDIUM"; s.recommended_action="flag_for_review"
    return s

if __name__=="__main__":
    baseline={"typical_hours":(9,17),"known_ips":{"10.0.1.1":"2026-01-01"},"known_countries":["US"],"auth_failures_7d":0}
    events=[
        {"event_id":"e1","actor_id":"alice","action":"export","ip_address":"195.12.45.99","country":"RU","user_agent":"python-requests/2.28","timestamp":"2026-03-23T02:30:00+00:00"},
        {"event_id":"e2","actor_id":"alice","action":"read","ip_address":"10.0.1.1","country":"US","user_agent":"Mozilla/5.0 Chrome/120","timestamp":"2026-03-23T10:15:00+00:00"},
    ]
    print("=== Anomaly Scoring ===")
    for ev in events:
        r=score_event(ev,baseline)
        print(json.dumps({"event_id":r.event_id,"score":r.final_score,"level":r.risk_level,"action":r.recommended_action,"factors":r.risk_factors},indent=2))
