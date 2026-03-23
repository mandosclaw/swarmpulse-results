#!/usr/bin/env python3
# Task: Impossible travel detector | Mission: SaaS Breach Detection via Behavioral Analytics
"""
Detects impossible travel by comparing consecutive login locations.
Uses Haversine formula to calculate travel speed between logins.

Install: pip install (stdlib only)
Usage:   python impossible-travel-detector.py
"""
import math, json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

IP_GEO = {
    "10.0.1.1":("37.7749","-122.4194","San Francisco","US"),
    "203.0.113.5":("51.5074","-0.1278","London","GB"),
    "195.12.45.99":("55.7558","37.6173","Moscow","RU"),
    "1.2.3.4":("35.6762","139.6503","Tokyo","JP"),
}
MAX_LEGIT_KPH = 900
ALERT_KPH = 1500

@dataclass
class LoginEvent:
    user_id: str; ip: str; ts: datetime
    lat: float=0.0; lon: float=0.0; city: str=""; country: str=""

@dataclass
class TravelAlert:
    user_id: str; from_city: str; to_city: str
    dist_km: float; hours: float; speed_kph: float; severity: str

def haversine(lat1,lon1,lat2,lon2):
    R=6371.0; d_lat=math.radians(lat2-lat1); d_lon=math.radians(lon2-lon1)
    a=math.sin(d_lat/2)**2+math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lon/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def enrich(login:LoginEvent) -> LoginEvent:
    if login.ip in IP_GEO:
        lat,lon,city,country=IP_GEO[login.ip]
        login.lat,login.lon,login.city,login.country=float(lat),float(lon),city,country
    return login

def check_travel(a:LoginEvent, b:LoginEvent) -> Optional[TravelAlert]:
    if not(a.lat and b.lat) or (a.city==b.city and a.country==b.country): return None
    dist=haversine(a.lat,a.lon,b.lat,b.lon)
    hrs=abs((b.ts-a.ts).total_seconds())/3600
    if hrs<0.001: return None
    spd=dist/hrs
    if spd<MAX_LEGIT_KPH: return None
    return TravelAlert(user_id=a.user_id,from_city=f"{a.city},{a.country}",to_city=f"{b.city},{b.country}",
        dist_km=round(dist,1),hours=round(hrs,2),speed_kph=round(spd,1),
        severity="CRITICAL" if spd>ALERT_KPH else "HIGH")

class ImpossibleTravelDetector:
    def __init__(self): self._last:dict[str,LoginEvent]={}
    def process(self,uid,ip,ts:datetime) -> Optional[TravelAlert]:
        login=enrich(LoginEvent(user_id=uid,ip=ip,ts=ts))
        alert=check_travel(self._last[uid],login) if uid in self._last else None
        self._last[uid]=login; return alert

if __name__=="__main__":
    d=ImpossibleTravelDetector()
    events=[("alice","10.0.1.1","2026-03-23T09:00:00+00:00"),
            ("alice","195.12.45.99","2026-03-23T09:45:00+00:00"),
            ("bob","10.0.1.1","2026-03-23T08:00:00+00:00"),
            ("bob","203.0.113.5","2026-03-23T18:00:00+00:00"),
            ("alice","1.2.3.4","2026-03-23T10:00:00+00:00")]
    print("=== Impossible Travel Detection ===")
    for uid,ip,ts in events:
        alert=d.process(uid,ip,datetime.fromisoformat(ts))
        if alert:
            print(f"\n🚨 [{alert.severity}] {alert.user_id}: {alert.from_city} → {alert.to_city}")
            print(f"   {alert.dist_km}km in {alert.hours}h = {alert.speed_kph}kph")
        else: print(f"✓ {uid} login from {ip} OK")
