#!/usr/bin/env python3
# Task: Audit log ingestion pipeline | Mission: SaaS Breach Detection via Behavioral Analytics
"""
High-throughput audit log ingestion for SaaS platforms.
Normalizes events from Okta, CloudTrail into unified behavioral schema.

Install: pip install aiohttp
Usage:   python audit-log-ingestion.py
"""
import asyncio, json, time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Optional
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

@dataclass
class BehavioralEvent:
    event_id: str; source: str; event_type: str; actor_id: str; actor_email: str
    ip_address: str; user_agent: str; resource: str; action: str; outcome: str
    timestamp: datetime; raw: dict = field(default_factory=dict)
    risk_indicators: list = field(default_factory=list)

def normalize_okta(raw:dict) -> Optional[BehavioralEvent]:
    try:
        actor=raw.get("actor",{}); client=raw.get("client",{}); outcome=raw.get("outcome",{})
        return BehavioralEvent(
            event_id=raw.get("uuid",""),source="okta",event_type=raw.get("eventType",""),
            actor_id=actor.get("id",""),actor_email=actor.get("login",""),
            ip_address=client.get("ipAddress",""),
            user_agent=client.get("userAgent",{}).get("rawUserAgent",""),
            resource=raw.get("target",[{}])[0].get("displayName","") if raw.get("target") else "",
            action=raw.get("eventType","").split(".")[-1],
            outcome=outcome.get("result","").lower(),
            timestamp=datetime.fromisoformat(raw.get("published","").replace("Z","+00:00")),
            raw=raw)
    except Exception as e: log.warning("Okta normalize error: %s",e); return None

def normalize_cloudtrail(raw:dict) -> Optional[BehavioralEvent]:
    try:
        uid=raw.get("userIdentity",{})
        return BehavioralEvent(
            event_id=raw.get("eventID",""),source="cloudtrail",event_type=raw.get("eventName",""),
            actor_id=uid.get("principalId",""),actor_email=uid.get("arn","").split("/")[-1],
            ip_address=raw.get("sourceIPAddress",""),user_agent=raw.get("userAgent",""),
            resource=raw.get("requestParameters",{}).get("bucketName",raw.get("eventSource","")),
            action=raw.get("eventName","").lower(),
            outcome="failure" if raw.get("errorCode") else "success",
            timestamp=datetime.fromisoformat(raw.get("eventTime","").replace("Z","+00:00")),
            raw=raw)
    except Exception as e: log.warning("CloudTrail error: %s",e); return None

SENSITIVE={"GetSecretValue","DeleteUser","CreateAccessKey","PutBucketPolicy","export","bulk_download"}

def tag_risks(event:BehavioralEvent) -> BehavioralEvent:
    indicators=[]
    h=event.timestamp.hour
    if h>=22 or h<6: indicators.append("after_hours_access")
    if event.outcome=="failure" and "auth" in event.event_type.lower(): indicators.append("auth_failure")
    if event.action in SENSITIVE or event.event_type in SENSITIVE: indicators.append("sensitive_action")
    browsers=["chrome","firefox","safari","edge","mozilla"]
    if event.user_agent and not any(b in event.user_agent.lower() for b in browsers):
        indicators.append("non_browser_agent")
    event.risk_indicators=indicators; return event

class Pipeline:
    def __init__(self, batch_size=500):
        self.batch_size=batch_size; self._buf=[]; self._total=0; self._t0=time.time()
    async def ingest(self, raw:dict, source:str) -> Optional[BehavioralEvent]:
        fn={"okta":normalize_okta,"cloudtrail":normalize_cloudtrail}.get(source)
        if not fn: return None
        ev=fn(raw)
        if not ev: return None
        ev=tag_risks(ev); self._buf.append(ev); self._total+=1
        if len(self._buf)>=self.batch_size: await self.flush()
        return ev
    async def flush(self):
        if not self._buf: return
        log.info("Flushing %d events",len(self._buf)); await asyncio.sleep(0.01); self._buf.clear()
    def stats(self): return {"total":self._total,"eps":round(self._total/(time.time()-self._t0),1)}

async def demo():
    p=Pipeline(batch_size=10)
    for i in range(50):
        raw={"uuid":f"e{i:04d}","eventType":"user.session.start","published":"2026-03-23T23:15:00Z",
             "actor":{"id":f"u{i}","login":f"u{i}@co.com"},
             "client":{"ipAddress":f"1.2.3.{i%255}","userAgent":{"rawUserAgent":"python-requests/2.28"}},
             "outcome":{"result":"SUCCESS" if i%3 else "FAILURE"},"target":[{"displayName":"Salesforce"}]}
        await p.ingest(raw,"okta")
    await p.flush()
    print("Stats:",json.dumps(p.stats(),indent=2))

if __name__=="__main__":
    asyncio.run(demo())
