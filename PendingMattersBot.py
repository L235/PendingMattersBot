#!/usr/bin/env python3
"""
KevinClerkBot – Task 2 (machine‑readable update fixed)
====================================================
Tracks Arbitration Committee member activity and outputs both a pretty report
and a ``/data`` page.  This version replaces problematic f‑strings around
MediaWiki braces with ``string.Template`` to avoid *SyntaxError: f‑string: single
'}' is not allowed*.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from string import Template

import mwclient
import mwparserfromhell as mwpfh
import requests

SETTINGS_PATH = "settings.json"
DEFAULT_CFG = {
    "site": "en.wikipedia.org",
    "path": "/w/",
    "user": "BotUser@PasswordName",
    "bot_password": "",
    "ua": "KevinClerkBot‑t2/0.4 (+https://github.com/L235/WordcountClerkBot)",
    "cookie_path": "~/kevinclerkbot/cookies.txt",
    "proceedings_page": "User:KevinClerkBot/Ongoing proceedings",
    "target_page": "User:KevinClerkBot/ArbCom activity",
    "data_page": "User:KevinClerkBot/ArbCom activity/data",
    "run_interval": 600,
}
CFG: Dict[str, object] = DEFAULT_CFG.copy()

# logging
class _Max(logging.Filter):
    def __init__(self, lvl: int):
        super().__init__(); self.lvl = lvl
    def filter(self, rec): return rec.levelno <= self.lvl

a = logging.getLogger(__name__)
a.setLevel(os.getenv("LOG_LEVEL", "INFO"))
_h1 = logging.StreamHandler(sys.stdout); _h1.setLevel(logging.DEBUG); _h1.addFilter(_Max(logging.INFO))
_h2 = logging.StreamHandler(sys.stderr); _h2.setLevel(logging.WARNING)
for h in (_h1, _h2): h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); a.addHandler(h)

###############################################################################
# Regex helpers
###############################################################################
HEADING_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$", re.M)
USER_LINK_RE = re.compile(r"\[\[\s*User(?:: talk)?\s*:\s*([^|\]]+)\|[^\]]*]]", re.I)
TIMESTAMP_RE = re.compile(r"\d{1,2}:\d{2}, \d{1,2} [A-Z][a-z]+ \d{4} \(UTC\)")
USER_TEMPLATE_RE = re.compile(r"\{\{\s*user\|([^}|]+)\s*}}", re.I)
MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"],1)}
SECONDS_PER_DAY = 86_400
GREEN, PALE_GREEN, GREY, YELLOW = "#ccffcc", "#eaffea", "#eeeeee", "#ffffcc"

###############################################################################
# Data classes
###############################################################################
@dataclass
class Arb: name: str; active: bool
@dataclass
class Proceeding: page: str; heading: str; anchor: str; label: str
@dataclass
class CommentStats:
    first_ts: datetime | None = None
    last_ts: datetime  | None = None
    count: int = 0
    def update(self, ts: datetime):
        if self.first_ts is None or ts < self.first_ts: self.first_ts = ts
        if self.last_ts  is None or ts > self.last_ts: self.last_ts = ts
        self.count += 1

###############################################################################
# Utility wrappers
###############################################################################
load_settings = lambda p=SETTINGS_PATH: (CFG.update(DEFAULT_CFG), CFG.update(json.load(open(p))) if os.path.exists(p) else None)

def connect():
    s = requests.Session(); site = mwclient.Site(str(CFG["site"]), path=str(CFG["path"]), clients_useragent=str(CFG["ua"]), pool=s)
    if not site.logged_in: site.login(str(CFG["user"]), str(CFG["bot_password"]))
    return site

fetch = lambda site, title: site.pages[title].text()
slugify = lambda h: re.sub(r"\s+", "_", mwpfh.parse(h).strip_code()).strip("_")

def parse_timestamp(ts_str: str) -> datetime:
    """Parse MediaWiki UTC timestamp format."""
    if not re.match(r"\d", ts_str[0]):
        return datetime.strptime(ts_str, "%H:%M, %d %B %Y (%Z)").replace(tzinfo=timezone.utc)
    
    # Parse format: "HH:MM, DD Month YYYY"
    match = re.match(r"(\d{1,2}):(\d{2}), (\d{1,2}) ([A-Z][a-z]+) (\d{4})", ts_str)
    if not match:
        raise ValueError(f"Invalid timestamp format: {ts_str}")
    
    hour, minute, day, month_name, year = match.groups()
    return datetime(
        int(year),
        MONTHS[month_name],
        int(day),
        int(hour),
        int(minute),
        tzinfo=timezone.utc
    )

parse_ts = parse_timestamp

###############################################################################
# 1. Arbitrators
###############################################################################

def get_arbs(site) -> Dict[str, Arb]:
    arbs: Dict[str, Arb] = {}
    current = None
    for ln in fetch(site, "Wikipedia:Arbitration Committee/Members").splitlines():
        if "Active}}}}" in ln: current = True;  continue
        if "Inactive}}}}" in ln: current = False; continue
        m = USER_TEMPLATE_RE.search(ln)
        if m and current is not None: arbs[m.group(1).strip()] = Arb(m.group(1).strip(), current)
    a.info("%d arbs (%d active)", len(arbs), sum(1 for v in arbs.values() if v.active)); return arbs

###############################################################################
# 2. Proceedings list
###############################################################################

def get_procs(site):
    procs: List[Proceeding] = []
    for wl in mwpfh.parse(fetch(site, CFG["proceedings_page"])).filter_wikilinks():
        tgt = str(wl.title);  lbl = wl.text.strip() if wl.text else tgt.split("#",1)[1]
        if "#" not in tgt: continue
        page, anc = tgt.split("#",1)
        procs.append(Proceeding(page.strip(), anc.replace("_"," "), slugify(anc), lbl))
    a.info("%d proceedings", len(procs)); return procs

###############################################################################
# 3. Section scanning helpers
###############################################################################

def section_text(page_txt: str, anchor: str):
    heads=list(HEADING_RE.finditer(page_txt))
    for i,h in enumerate(heads):
        if slugify(h.group(2))==slugify(anchor):
            return page_txt[h.end(): heads[i+1].start() if i+1<len(heads) else len(page_txt)]
    return ""

def scan(sec_txt:str, arbs:Dict[str,Arb]):
    stats: Dict[str, CommentStats] = {}
    for ln in sec_txt.splitlines():
        tm = TIMESTAMP_RE.search(ln);  um_iter = USER_LINK_RE.finditer(ln) if tm else []
        for um in um_iter:
            user=um.group(1).strip()
            if user in arbs: stats.setdefault(user, CommentStats()).update(parse_ts(tm.group()))
    # second pass window
    missing=set(arbs)-set(stats)
    if missing:
        for um in USER_LINK_RE.finditer(sec_txt):
            user=um.group(1).strip();  window=sec_txt[max(0,um.start()-120): um.end()+120]
            tm=TIMESTAMP_RE.search(window)
            if user in missing and tm: stats.setdefault(user, CommentStats()).update(parse_ts(tm.group()))
    return stats

###############################################################################
# 4. Output helpers
###############################################################################

def status_colour(arb:Arb, st:CommentStats|None, now)->Tuple[str,str,int]:
    if not arb.active: return "inactive", GREY, -1
    if st and st.last_ts:
        days=int((now-st.last_ts).total_seconds()//SECONDS_PER_DAY)
        return f"commented {days} day{'s' if days!=1 else ''} ago", (GREEN if days<=7 else PALE_GREEN), days
    return "not commented", YELLOW, -1


def build_table(proc, arbs, stats):
    now=datetime.now(timezone.utc)
    lines=[f"=== [[{proc.page}#{proc.anchor}|{proc.label}]] ===",
           "{| class=\"wikitable sortable\"",
           "! Arbitrator !! Activity status !! First comment !! Last comment !! # Comments"]
    for name,arb in sorted(arbs.items(), key=lambda kv:kv[0].lower()):
        st=stats.get(name)
        status,col, _=status_colour(arb,st,now)
        first=st.first_ts.strftime("%H:%M, %-d %B %Y (UTC)") if st and st.first_ts else "—"
        last =st.last_ts.strftime("%H:%M, %-d %B %Y (UTC)") if st and st.last_ts  else "—"
        cnt  =st.count if st else 0
        lines.append(f"|- style=\"background:{col}\"\n| [[User:{name}|{name}]] || {status} || {first} || {last} || {cnt}")
    lines.append("|}"); return "\n".join(lines)


def assemble_report(site, arbs):
    out=["<!-- Auto‑generated by KevinClerkBot task 2 – do not edit manually -->"]
    for proc in get_procs(site):
        stxt=section_text(fetch(site,proc.page),proc.heading)
        out.append(build_table(proc, arbs, scan(stxt, arbs)))
    return "\n\n".join(out)

# data page generator using Template to avoid brace escaping hell

def assemble_data(site, arbs):
    now=datetime.now(timezone.utc)
    lines=["{{#switch: {{{proceeding}}}"]
    # per proceeding
    for proc in get_procs(site):
        lines.append(Template(" | $anchor = {{#switch: {{{user}}}").substitute(anchor=proc.anchor.lower()))
        sec=section_text(fetch(site,proc.page),proc.heading)
        stats=scan(sec, arbs)
        # per arbitrator
        user_tpl=Template(
            "     | $user = {{#switch: {{{field|status}}} | status = $status | first = $first | last = $last | count = $count | days = $days }}"
        )
        for name,arb in arbs.items():
            st=stats.get(name)
            status,_c,days=status_colour(arb,st,now)
            first=st.first_ts.strftime("%H:%M, %-d %B %Y (UTC)") if st and st.first_ts else ""
            last =st.last_ts.strftime("%H:%M, %-d %B %Y (UTC)") if st and st.last_ts else ""
            count=str(st.count) if st else "0"
            lines.append(user_tpl.substitute(user=name, status=status, first=first, last=last, count=count, days="" if days<0 else days))
        lines.append("   }}")  # close inner switch
    lines.append("}}"); return "\n".join(lines)

###############################################################################
# Runner
###############################################################################

def run_once(site):
    arbs=get_arbs(site)
    report=assemble_report(site, arbs)
    data  =assemble_data(site, arbs)
    tp=site.pages[str(CFG["target_page"])]
    dp=site.pages[str(CFG["data_page"])]
    if report!=tp.text(): tp.save(report,summary="update activity report (task 2)",minor=False,bot=False)
    if data!=dp.text():  dp.save(data,  summary="update data template (task 2)",minor=True, bot=False)

def main(loop=True):
    load_settings()
    site=connect()
    if not loop: run_once(site); return
    while True:
        try: run_once(site)
        except Exception: a.exception("error in cycle")
        time.sleep(int(CFG["run_interval"]))

if __name__=="__main__":
    main(loop=not any(arg in {"--once","-1"} for arg in sys.argv))
