#!/usr/bin/env python3
# Task: Behavioral baseline engine | Mission: SaaS Breach Detection via Behavioral Analytics
"""
Builds per-user behavioral baselines from 30 days of event history.
Features: login time distribution, IP diversity, data access volume, resource patterns.

Install: pip install (stdlib only)
Usage:   python behavioral-baseline.py
"""
import json, statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional
import random

@dataclass
class UserBaseline:
    user_id: str
    login_hours: dict = field(default_factory=lambda: defaultdict(int))
    known_ips: dict = field(default_factory=dict)
    daily_data_volume: list = field(default_factory=list)
    resource_access: dict = field(default_factory=lambda: defaultdict(int))
    known_countries: set = field(default_factory=set)
    auth_failures_7d: int = 0
    last_updated: Optional[datetime] = None

    def update(self, event:dict):
        ts=datetime.fromisoformat(event.get("timestamp",datetime.now(timezone.utc).isoformat()))
        if "login" in event.get("event_type","").lower(): self.login_hours[ts.hour]+=1
        ip=event.get("ip_address","")
        if ip and ip not in self.known_ips: self.known_ips[ip]=ts.isoformat()
        self.known_countries.add(event.get("country","US"))
        res=event.get("resource","")
        if res: self.resource_access[res]+=1
        if event.get("outcome")=="failure" and "auth" in event.get("event_type","").lower():
            self.auth_failures_7d+=1
        self.last_updated=datetime.now(timezone.utc)

    def typical_hours(self) -> tuple:
        if not self.login_hours: return (8,18)
        hours=[h for h,c in self.login_hours.items() for _ in range(c)]
        hours.sort(); n=len(hours)
        return (hours[max(0,n//10)], hours[min(n-1,(n*9)//10)])

    def avg_volume(self) -> float:
        return statistics.mean(self.daily_data_volume) if self.daily_data_volume else 0.0

    def serialize(self) -> dict:
        return {"user_id":self.user_id,"login_hours":dict(self.login_hours),
                "known_ips":self.known_ips,"daily_data_volume":self.daily_data_volume,
                "resource_access":dict(self.resource_access),"known_countries":list(self.known_countries),
                "auth_failures_7d":self.auth_failures_7d,"typical_hours":self.typical_hours(),
                "avg_daily_volume_mb":self.avg_volume(),
                "last_updated":self.last_updated.isoformat() if self.last_updated else None}

class BaselineStore:
    def __init__(self): self._store:dict[str,UserBaseline]={}
    def get_or_create(self,uid:str) -> UserBaseline:
        if uid not in self._store: self._store[uid]=UserBaseline(user_id=uid)
        return self._store[uid]
    def process_event(self, event:dict): self.get_or_create(event.get("actor_id","unknown")).update(event)

if __name__=="__main__":
    store=BaselineStore()
    base=datetime(2026,2,20,tzinfo=timezone.utc)
    for day in range(30):
        for _ in range(random.randint(3,12)):
            h=random.choice([9,10,10,11,12,13,14,15,16,17])
            store.process_event({"actor_id":"usr_alice","event_type":"user.session.start",
                "ip_address":random.choice(["10.0.1.1","10.0.1.2","203.0.113.5"]),
                "country":"US","resource":random.choice(["Salesforce","Jira","S3"]),
                "outcome":"success","timestamp":(base+timedelta(days=day,hours=h)).isoformat()})
    b=store.get_or_create("usr_alice")
    print("=== User Baseline ==="); print(json.dumps(b.serialize(),indent=2))
