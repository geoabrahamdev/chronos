"""CHRONOS local-only open world with bounded HHMI Janelia MaleCNS v1.0 circuits.

The simulator deliberately keeps two truths separate: selected edge weights and
cell identities are from MaleCNS; the rate, sensor and body physics are explicit
toy-model assumptions, not a full biophysical reconstruction.
"""
from __future__ import annotations

import json, math, random, threading, time
from collections import Counter
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
try:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather
    import pyarrow.ipc as ipc
except ImportError:  # The checked-in portable cache needs only the Python stdlib.
    pa = pc = feather = ipc = None

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "malecns"
TYPES = DATA / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
CONNECTIONS = DATA / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
PATHWAY = DATA / "verified-odor-motor-path.json"
VALIDATION = DATA / "verified-path-validation.json"
SYN_PARTNERS = DATA / "syn-partners-male-cns-v1.0-minconf-0.5.feather"
SYN_POINTS = DATA / "syn-points-male-cns-v1.0-minconf-0.5.feather"
TBAR_TRANSMITTERS = DATA / "tbar-neurotransmitters-male-cns-v1.0.feather"
PORTABLE_CIRCUITS = DATA / "portable-circuits.json"
SYNAPSE_FILES = {
    "partners": (SYN_PARTNERS, 6777179098),
    "points": (SYN_POINTS, 13061489098),
    "tbar_transmitters": (TBAR_TRANSMITTERS, 2651680218),
}

@lru_cache(maxsize=1)
def verified_pathway():
    return json.loads(PATHWAY.read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def pathway_cell_coords():
    """Per-cell centroid in native 8-nm voxels, computed from actual synapse samples
    (HHMI Janelia MaleCNS v1.0 export). Each cell's centroid is the mean of all its pre- and
    post-synaptic site coordinates recorded across all 11 edges. Also returns a normalized
    version in [-1,1] preserving aspect ratio, for 3D rendering."""
    path = verified_pathway()
    points = {}
    for edge in path["edges"]:
        for s in edge.get("synapse_coordinate_sample", []):
            if "pre" in s:  points.setdefault(edge["pre"],  []).append(tuple(s["pre"]))
            if "post" in s: points.setdefault(edge["post"], []).append(tuple(s["post"]))
    centroids_voxel = {b: (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts), sum(p[2] for p in pts)/len(pts))
                       for b, pts in points.items() if pts}
    if not centroids_voxel:
        return {}
    xs = [c[0] for c in centroids_voxel.values()]
    ys = [c[1] for c in centroids_voxel.values()]
    zs = [c[2] for c in centroids_voxel.values()]
    cx_bb, cy_bb, cz_bb = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2
    max_span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    scale = (max_span / 2) if max_span > 0 else 1
    out = {}
    for b, c in centroids_voxel.items():
        out[b] = {
            # MaleCNS v1.0 synapse points are 8-nm voxel indices. Both forms are returned so callers do not need to guess.
            "voxel_8nm": [round(c[0]), round(c[1]), round(c[2])],
            "nm":        [round(c[0]*8), round(c[1]*8), round(c[2]*8)],
            "norm":      [round((c[0]-cx_bb)/scale, 4), round((c[1]-cy_bb)/scale, 4), round((c[2]-cz_bb)/scale, 4)],
            "sample_count": len(points[b]),
        }
    return out

@lru_cache(maxsize=1)
def pathway_validation():
    return json.loads(VALIDATION.read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def synapse_data_status():
    files = {}
    for name, (path, expected_bytes) in SYNAPSE_FILES.items():
        actual_bytes = path.stat().st_size if path.exists() else 0
        files[name] = {
            "filename": path.name,
            "ready": actual_bytes == expected_bytes,
            "bytes": actual_bytes,
            "expected_bytes": expected_bytes,
        }
    evidence = verified_pathway().get("synapse_evidence", {})
    return {
        "all_tables_ready": all(item["ready"] for item in files.values()),
        "table_count": sum(1 for item in files.values() if item["ready"]),
        "expected_table_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files.values()),
        "selected_partner_rows": evidence.get("selected_partner_rows", 0),
        "evidence_status": evidence.get("status", "not extracted"),
        "runtime_mode": "preprocessed pathway subset; raw tables are not loaded by the browser",
        "files": files,
    }

@lru_cache(maxsize=1)
def types():
    table = feather.read_table(TYPES, columns=["bodyId", "type"])
    return {row["bodyId"]: row["type"] or "untyped" for row in table.to_pylist()}

def members(circuit, table):
    if circuit == "odor":
        return {i for i,t in table.items() if t.startswith(("ORN_DM1", "ORN_VA2")) or t in {"DM1_lPN", "VA2_adPN"}}
    return {i for i,t in table.items() if t.startswith(("EPG", "PEN", "PEG", "PFL"))}

@lru_cache(maxsize=1)
def circuits():
    """Load the attributed portable subset, or rebuild it from official raw tables."""
    if PORTABLE_CIRCUITS.exists():
        return json.loads(PORTABLE_CIRCUITS.read_text(encoding="utf-8"))
    if feather is None or ipc is None:
        raise RuntimeError(
            "portable-circuits.json is missing; install requirements-data.txt "
            "and download the official MaleCNS tables to rebuild it"
        )
    table = types(); odor_members, compass_members = members("odor", table), members("compass", table)
    odor, compass = Counter(), Counter()
    reader = ipc.open_file(pa.memory_map(str(CONNECTIONS), "r"))
    odor_values, compass_values = pa.array(list(odor_members), type=pa.int64()), pa.array(list(compass_members), type=pa.int64())
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        for selected, target in ((odor_values, odor), (compass_values, compass)):
            mask = pc.and_(pc.is_in(batch.column("body_pre"), value_set=selected), pc.is_in(batch.column("body_post"), value_set=selected))
            picked = batch.filter(mask).to_pydict()
            for pre, post, weight in zip(picked["body_pre"], picked["body_post"], picked["weight"]):
                target[(pre, post)] += weight
    def pack(name, chosen, edges):
        ranked = edges.most_common()
        if name == "odor":
            ranked = ([edge for edge in ranked if table[edge[0][0]].startswith("ORN_DM1")][:10] +
                      [edge for edge in ranked if table[edge[0][0]].startswith("ORN_VA2")][:10])
        else: ranked = ranked[:42]
        rows = [{"pre":a,"post":b,"pre_type":table[a],"post_type":table[b],"neuropil":"not included","neurotransmitter":"not included","synapses":w} for (a,b),w in ranked]
        return {"dataset":"HHMI Janelia MaleCNS v1.0","circuit":name,"member_count":len(chosen),"edge_count":len(rows),"edges":rows,
                "note":"Cell identities and weights are from MaleCNS v1.0. The flat connection export has no per-edge neuropil or neurotransmitter field; CHRONOS rate dynamics and body control remain model assumptions."}
    return {"odor":pack("odor", odor_members, odor), "compass":pack("compass", compass_members, compass)}

def circuit(circuit_name):
    if circuit_name == "pathway": return verified_pathway()
    if circuit_name not in {"odor", "compass"}: raise ValueError("unknown circuit")
    return circuits()[circuit_name]

def clamp(x,a=0,b=1): return max(a,min(b,x))
def angle_delta(a,b): return math.atan2(math.sin(a-b),math.cos(a-b))

INTERACTION_PROFILES={
    "food":{"mode":"feeding","duration":3.5,"need":"hunger","gain":.62,"cooldown":8.0,"complete":"fed"},
    "water":{"mode":"drinking","duration":2.5,"need":"thirst","gain":.85,"cooldown":12.0,"complete":"drank water"},
    "rest":{"mode":"resting","duration":10.0,"need":"fatigue","gain":.60,"cooldown":12.0,"complete":"rested"},
}

class OpenWorld:
    def __init__(self):
        self.lock=threading.RLock(); self.last=time.monotonic(); self.reset()
    def reset(self):
        self.fly={"x":5.00,"y":4.50,"z":.20,"heading":-1.55,"speed":0.0,"trail":[]}
        self.needs={"hunger":.72,"thirst":.45,"fatigue":.23,"fear":.08}
        self.compass=True; self.running=True; self.tick=0; self.event="Woke in the meadow. Antennae sampling."
        self.custom_index=0; self.cooldowns={}; self.interaction=None; self.waypoint={"x":8.20,"y":1.50}; self.waypoint_until=0.0; self.depart_until=0.0; self.trail_history=[]; self.pivots=[]
        self.traffic_until=time.monotonic()+30.0; self.traffic_next=0.0
        self.flight={"mode":"cruise","target_z":.20,"target_id":None,"contact_z":None}
        self.pathway_rates={node["body"]:0.0 for node in verified_pathway()["nodes"]}
        self.world={"span":6,"wind":[.22,.05,.018],"home":[3.00,3.15,0],"biomes":[
            {"label":"FOREST EDGE","x":0,"y":0,"w":1.8,"h":1.8,"color":"#285239"},
            {"label":"ORCHARD","x":1.8,"y":0,"w":1.7,"h":1.8,"color":"#607d3d"},
            {"label":"RIDGE","x":3.5,"y":0,"w":2.5,"h":2.0,"color":"#51683b"},
            {"label":"CENTRAL CLEARING","x":1.4,"y":1.8,"w":2.6,"h":1.4,"color":"#557f43"},
            {"label":"POND","x":0,"y":1.8,"w":1.4,"h":1.5,"color":"#315d4c"},
            {"label":"WETLAND","x":4.0,"y":2.0,"w":2.0,"h":1.7,"color":"#526f4c"},
            {"label":"SHELTER GROVE","x":1.1,"y":3.3,"w":1.8,"h":1.1,"color":"#45693d"},
            {"label":"ROAD VERGE","x":3.0,"y":3.6,"w":3.0,"h":.9,"color":"#77814a"},
            {"label":"FLOWER FIELD","x":0,"y":4.4,"w":3.0,"h":1.6,"color":"#618648"},
            {"label":"GARDEN","x":3.0,"y":4.5,"w":3.0,"h":1.5,"color":"#4c743e"}],
            "trees":[{"x":1.10,"y":.74,"h":.46},{"x":.44,"y":1.22,"h":.34},{"x":2.62,"y":.62,"h":.38},{"x":3.82,"y":.92,"h":.31},{"x":5.15,"y":.76,"h":.42},{"x":4.52,"y":2.62,"h":.36},{"x":5.42,"y":3.18,"h":.29},{"x":1.86,"y":3.70,"h":.38},{"x":.56,"y":5.18,"h":.31},{"x":2.48,"y":5.36,"h":.41},{"x":4.00,"y":5.12,"h":.35},{"x":5.44,"y":5.32,"h":.36}],
            "roads":[{"id":"meadow-road","label":"MEADOW ROAD","x1":.12,"y1":4.20,"x2":5.88,"y2":4.20}],
            "cars":[{"id":"car-passing","road":"meadow-road","t":.18,"speed":.22,"direction":1,"color":"#e2a64c"}],
            "sources":[
            {"id":"nectar","label":"orchard nectar / DM1","kind":"food","x":2.68,"y":.62,"z":.04,"odor":"DM1","color":"#ffbd58"},
            {"id":"canopy-nectar","label":"canopy nectar / DM1","kind":"food","x":1.10,"y":.74,"z":.48,"odor":"DM1","color":"#ffbd58"},
            {"id":"yeast","label":"wetland yeast / VA2","kind":"food","x":5.20,"y":2.82,"z":.03,"odor":"VA2","color":"#ae8df4"},
            {"id":"water","label":"pond water","kind":"water","x":.62,"y":2.52,"z":0,"color":"#66c9ff"},
            {"id":"nest","label":"shelter grove","kind":"rest","x":1.86,"y":3.78,"z":0,"color":"#b6d887"},
            {"id":"threat","label":"ridge threat","kind":"threat","x":4.68,"y":.86,"z":.36,"color":"#ff6b61"}]}
        # Scale the authored 6x6 scene into a 10x10 free-roaming world while
        # preserving its relative ecology; altitude is deliberately unchanged.
        scale=10/6
        for biome in self.world["biomes"]:
            biome["x"]*=scale; biome["y"]*=scale; biome["w"]*=scale; biome["h"]*=scale
        for tree in self.world["trees"]: tree["x"]*=scale; tree["y"]*=scale
        for road in self.world["roads"]:
            road["x1"]*=scale; road["y1"]*=scale; road["x2"]*=scale; road["y2"]*=scale
        for source in self.world["sources"]: source["x"]*=scale; source["y"]*=scale
        self.world["home"]=[value*scale if index<2 else value for index,value in enumerate(self.world["home"])]
        self.world["span"]=10
    def add_stimulus(self, kind, x, y, z=0.0):
        templates={
            "dm1":("food","nectar / DM1","DM1","#ffbd58"),
            "va2":("food","yeast / VA2","VA2","#ae8df4"),
            "water":("water","water",None,"#66c9ff"),
            "shelter":("rest","shelter",None,"#b6d887"),
            "threat":("threat","threat",None,"#ff6b61"),
        }
        if kind not in templates: return False
        role,label,odor,color=templates[kind]; self.custom_index+=1
        source={"id":f"user-{kind}-{self.custom_index}","label":f"user {label}","kind":role,
                "x":clamp(x,.08,9.92),"y":clamp(y,.08,9.92),"z":clamp(z,0,.72),"color":color,"user_created":True}
        if odor: source["odor"]=odor
        self.world["sources"].append(source)
        self.event=f"new {label} stimulus at z={source['z']:.2f}: reassessing"
        return True
    def move_fly(self, x, y, z):
        f=self.fly; f["x"]=clamp(x,.04,9.96); f["y"]=clamp(y,.04,9.96); f["z"]=clamp(z,.035,.72)
        f["trail"]=[]; self.depart_until=0.0; self.interaction=None
        self.event=f"fly repositioned by user to {f['x']:.2f}, {f['y']:.2f}, z={f['z']:.2f}"
    def update_traffic(self, dt, now):
        # Traffic is occasional rather than a perpetual obstacle field: one larger
        # car passes for a short interval, then the road is empty and fully free.
        if self.world["cars"] and now>=self.traffic_until:
            self.world["cars"]=[]; self.traffic_next=now+random.uniform(14.0,24.0)
        elif not self.world["cars"] and now>=self.traffic_next:
            palette=["#e2a64c","#506a7c","#b85b4d"]
            road=random.choice(self.world["roads"])
            self.world["cars"]=[{"id":f"car-{self.tick}","road":road["id"],"t":random.random(),"speed":random.uniform(.16,.26),"direction":random.choice([-1,1]),"color":random.choice(palette)}]
            self.traffic_until=now+random.uniform(5.0,8.0)
        roads={road["id"]:road for road in self.world["roads"]}
        for car in self.world["cars"]:
            road=roads[car["road"]]; car["t"]=(car["t"]+car["speed"]*car["direction"]*dt)%1.0
            car["x"]=road["x1"]+(road["x2"]-road["x1"])*car["t"]
            car["y"]=road["y1"]+(road["y2"]-road["y1"])*car["t"]
            car["z"]=.025
    def remove_stimulus(self, source_id):
        before=len(self.world["sources"])
        self.world["sources"]=[s for s in self.world["sources"] if not (s.get("user_created") and s["id"]==source_id)]
        if len(self.world["sources"])<before:
            if self.interaction and self.interaction["source_id"]==source_id: self.interaction=None
            self.cooldowns.pop(source_id,None); self.event="user stimulus removed from meadow"; return True
        self.event="only user-added stimuli can be removed"; return False
    def clear_stimuli(self):
        removed=[s["id"] for s in self.world["sources"] if s.get("user_created")]
        self.world["sources"]=[s for s in self.world["sources"] if not s.get("user_created")]
        for source_id in removed: self.cooldowns.pop(source_id,None)
        if self.interaction and self.interaction["source_id"] in removed: self.interaction=None
        self.event=f"removed {len(removed)} user stimulus{'s' if len(removed)!=1 else ''}"
    def explore(self, now, f):
        if now>=self.waypoint_until or math.hypot(f["x"]-self.waypoint["x"],f["y"]-self.waypoint["y"])<.12:
            phase=self.tick*.61
            self.waypoint={"x":clamp(5.0+3.75*math.sin(phase),.10,9.90),"y":clamp(5.0+3.45*math.sin(phase*1.7),.10,9.90)}
            self.waypoint_until=now+2.4
        return self.waypoint
    def odor(self, source, x, y, z):
        # A 3D plume stretches downwind and weakens above/below its source layer.
        wx,wy,wz=self.world["wind"]; dx,dy=x-source["x"],y-source["y"]
        forward=dx*wx+dy*wy; lateral=abs(dx*wy-dy*wx)/max(.001,math.hypot(wx,wy))
        height=abs((z-source.get("z",0))-forward*wz/max(.001,math.hypot(wx,wy)))
        return math.exp(-lateral*lateral/.11-height*height/.05)*math.exp(-abs(forward)*1.35)*(1.0 if forward>=-.04 else .18)
    def advance_pathway(self, dm1_drive):
        """Small non-spiking rate model over one verified, weighted MaleCNS chain.

        We deliberately use unsigned gains: transmitter predictions alone do not
        establish receptor-specific excitatory/inhibitory sign at each synapse.
        A branch may override edge weights to run a null-model comparison.
        """
        path=verified_pathway(); nodes=path["nodes"]; edges=path["edges"]
        override=getattr(self,"_weight_override",None)
        weights=override if override is not None else [edge["synapses"] for edge in edges]
        max_weight=max(weights) if weights else 1
        old=self.pathway_rates; new={}
        first=nodes[0]["body"]
        new[first]=clamp(old[first]*.62+dm1_drive*.70)
        for i,edge in enumerate(edges):
            pre,post=edge["pre"],edge["post"]
            gain=.18+.82*(weights[i]/max_weight)
            new[post]=clamp(old[post]*.70+new[pre]*gain*.58)
        self.pathway_rates=new
        return new[edges[-1]["post"]]
    def step(self, now=None, dt=None):
        if now is None: now=time.monotonic()
        if dt is None: dt=min(.08,max(.0,now-self.last))
        self.last=now
        if not self.running: return self.snapshot()
        self.tick+=1
        f,n=self.fly,self.needs
        n["hunger"]=clamp(n["hunger"]+dt*.006);n["thirst"]=clamp(n["thirst"]+dt*.004);n["fatigue"]=clamp(n["fatigue"]+dt*.002)
        self.update_traffic(dt,now)
        sources=self.world["sources"]
        foods=[s for s in sources if s["kind"]=="food"]
        dm1=max((self.odor(s,f["x"],f["y"],f["z"]) for s in foods if s.get("odor")=="DM1"),default=0.0)
        va2=max((self.odor(s,f["x"],f["y"],f["z"]) for s in foods if s.get("odor")=="VA2"),default=0.0)
        motor_drive=self.advance_pathway(clamp(dm1*(.7+.3*n["hunger"])))
        threats=[s for s in sources if s["kind"]=="threat"]
        hazards=[{**s,"hazard":"threat"} for s in threats]+[{**car,"kind":"car","hazard":"traffic"} for car in self.world["cars"]]
        nearest_hazard=min(hazards,key=lambda s:math.sqrt((f["x"]-s["x"])**2+(f["y"]-s["y"])**2+(f["z"]-s.get("z",0))**2),default=None)
        hazard_d=math.sqrt((f["x"]-nearest_hazard["x"])**2+(f["y"]-nearest_hazard["y"])**2+(f["z"]-nearest_hazard.get("z",0))**2) if nearest_hazard else 9
        # Threats and moving road traffic are sensed well before ground contact.
        hazard_gain=.82 if nearest_hazard and nearest_hazard["hazard"]=="traffic" else .68
        n["fear"]=clamp(hazard_gain*math.exp(-hazard_d*3.4))
        interaction_source=next((source for source in sources if self.interaction and source["id"]==self.interaction["source_id"]),None)
        if self.interaction and not interaction_source: self.interaction=None
        if self.interaction:
            profile=INTERACTION_PROFILES[self.interaction["kind"]]
            progress=clamp((now-self.interaction["started_at"])/profile["duration"])
            n[profile["need"]]=clamp(self.interaction["start_need"]-profile["gain"]*progress)
            if progress>=1:
                self.cooldowns[interaction_source["id"]]=now+profile["cooldown"]
                dx,dy=f["x"]-interaction_source["x"],f["y"]-interaction_source["y"]
                length=math.hypot(dx,dy)
                if length<.001: dx,dy=math.cos(f["heading"]),math.sin(f["heading"]); length=1.0
                self.waypoint={"x":clamp(interaction_source["x"]+dx/length*.45,.05,9.95),"y":clamp(interaction_source["y"]+dy/length*.45,.05,9.95)}
                self.depart_until=now+1.8; self.event=f"{profile['complete']} after {profile['duration']:.1f}s; departing area"
                self.interaction=None; interaction_source=None
        # Compare physiological drives on one scale. Sensory evidence and proximity
        # break ties, but a nearly satisfied need cannot beat severe hunger merely
        # because its resource is nearby. Thresholds model short-term satiety.
        is_available=lambda s:self.cooldowns.get(s["id"],0)<=now
        distance_to=lambda s:math.hypot(f["x"]-s["x"],f["y"]-s["y"])
        food_scores=[(n["hunger"]+.16*self.odor(s,f["x"],f["y"],f["z"])+.05/(.60+distance_to(s)),s,f"follow {s.get('odor','food')} plume") for s in foods if is_available(s) and n["hunger"]>=.16]
        waters=[s for s in sources if s["kind"]=="water"]; rests=[s for s in sources if s["kind"]=="rest"]
        candidates=food_scores+[(n["thirst"]+.05/(.60+distance_to(s)),s,"seek water") for s in waters if is_available(s) and n["thirst"]>=.20]
        candidates += [(n["fatigue"]+.05/(.60+distance_to(s)),s,"return to shelter") for s in rests if is_available(s) and n["fatigue"]>=.28]
        target_source=None
        if nearest_hazard and hazard_d<(.55 if nearest_hazard["hazard"]=="traffic" else .62):
            if self.interaction:
                self.event=f"{self.interaction['mode']} interrupted by {nearest_hazard['hazard']}"
                self.interaction=None; interaction_source=None
            away_x,away_y=f["x"]-nearest_hazard["x"],f["y"]-nearest_hazard["y"]
            away_length=math.hypot(away_x,away_y)
            if away_length<.03:
                away_x,away_y=math.cos(f["heading"]),math.sin(f["heading"]); away_length=1.0
            target=({"x":clamp(f["x"]+away_x/away_length*.95,.05,9.95),"y":clamp(f["y"]+away_y/away_length*.95,.05,9.95)},f"climb and evade {nearest_hazard['hazard']}")
            target_source=nearest_hazard
        elif interaction_source:
            progress=clamp((now-self.interaction["started_at"])/self.interaction["duration"])
            target=(interaction_source,f"{self.interaction['mode']} {round(progress*100)}%")
            target_source=interaction_source
        elif now<self.depart_until: target=(self.waypoint,"leave resource area")
        elif candidates:
            _,source,label=max(candidates,key=lambda item:item[0]); target=(source,label); target_source=source
        else: target=(self.explore(now,f),"explore meadow")
        desired=math.atan2(target[0]["y"]-f["y"],target[0]["x"]-f["x"])
        target_distance=math.hypot(target[0]["x"]-f["x"],target[0]["y"]-f["y"])
        cast=math.sin(now*4.2)*.48*clamp(target_distance/.45,.03,1)
        noise=(random.random()-.5)*(1.8 if not self.compass else .10)
        f["heading"]+=angle_delta(desired+cast+noise,f["heading"])*dt*(.7 if not self.compass else 2.1)
        # Continuous flight has three explicit vertical modes. Resource contact is
        # ground-proximate, not merely an X/Y crossing; departure regains cruise height.
        if target_source and target_source["kind"] in {"threat","car"}:
            target_z=.55; flight_mode="climb / evade"; contact_z=None
        elif self.interaction and interaction_source:
            contact_z=clamp(interaction_source.get("z",0)+.045,.035,.16)
            target_z=contact_z; flight_mode=self.interaction["mode"]
        elif target_source and target_source["kind"] in {"food","water","rest"}:
            contact_z=clamp(target_source.get("z",0)+.045,.035,.16)
            target_z=clamp(contact_z+min(.30,target_distance*.26),.035,.36)
            flight_mode="landing" if target_distance<.34 else "low approach"
        elif now<self.depart_until:
            target_z=.28; flight_mode="departing"
            contact_z=None
        else:
            target_z=.20+.045*math.sin(now*1.8+f["x"]*3); flight_mode="cruise"
            contact_z=None
        self.flight={"mode":flight_mode,"target_z":round(target_z,3),"target_id":target_source["id"] if target_source else None,"contact_z":round(contact_z,3) if contact_z is not None else None}
        if self.interaction and interaction_source:
            f["x"]=interaction_source["x"]; f["y"]=interaction_source["y"]; f["z"]=target_z; f["speed"]=0.0
        else:
            f["z"]=clamp(f["z"]+(target_z-f["z"])*dt*3.2,.035,.72)
            f["speed"]=.46*(.78+n["hunger"]*.22+n["fear"]*.45)*(.62+.72*motor_drive)
            f["x"]=clamp(f["x"]+math.cos(f["heading"])*f["speed"]*dt,.04,9.96); f["y"]=clamp(f["y"]+math.sin(f["heading"])*f["speed"]*dt,.04,9.96)
        f["trail"].append([round(f["x"],4),round(f["y"],4),round(f["z"],4)]); f["trail"]=f["trail"][-140:]
        self.trail_history.append({"tick":self.tick,"wall":round(now,3),"x":round(f["x"],4),"y":round(f["y"],4),"z":round(f["z"],4),"heading":round(f["heading"],4),"speed":round(f["speed"],4),"compass":self.compass,"mode":self.flight["mode"],"interaction":self.interaction["source_id"] if self.interaction else None})
        self.trail_history=self.trail_history[-500:]
        for obj in ([target_source] if target_source and not self.interaction else []):
            contact_z=clamp(obj.get("z",0)+.045,.035,.16)
            horizontal_distance=math.hypot(f["x"]-obj["x"],f["y"]-obj["y"])
            vertical_gap=abs(f["z"]-contact_z)
            profile=INTERACTION_PROFILES.get(obj["kind"])
            if profile and is_available(obj) and horizontal_distance<.13 and vertical_gap<.025:
                self.interaction={"active":True,"source_id":obj["id"],"kind":obj["kind"],"mode":profile["mode"],"started_at":now,"duration":profile["duration"],"start_need":n[profile["need"]]}
                f["x"]=obj["x"]; f["y"]=obj["y"]; f["z"]=contact_z; f["speed"]=0.0
                self.flight={"mode":profile["mode"],"target_z":round(contact_z,3),"target_id":obj["id"],"contact_z":round(contact_z,3)}
                target=(obj,profile["mode"]); self.event=f"{profile['mode']} at {obj['label']}: 0%"
        if not self.compass: self.event="compass lesion: heading estimate unstable"
        elif self.interaction:
            progress=clamp((now-self.interaction["started_at"])/self.interaction["duration"])
            self.event=f"{self.interaction['mode']} at {target_source['label']}: {round(progress*100)}%"
        elif self.tick%50==0: self.event=target[1]
        return self.snapshot(dm1,va2,target[1])
    def snapshot_state(self):
        """Deterministic state capture for counterfactual branching. Not for UI."""
        import copy
        return {
            "fly":copy.deepcopy(self.fly),"needs":dict(self.needs),
            "compass":self.compass,"running":self.running,"tick":self.tick,
            "custom_index":self.custom_index,"cooldowns":dict(self.cooldowns),"event":self.event,
            "interaction":copy.deepcopy(self.interaction),
            "waypoint":dict(self.waypoint),"waypoint_until":self.waypoint_until,
            "depart_until":self.depart_until,
            "traffic_until":self.traffic_until,"traffic_next":self.traffic_next,
            "flight":dict(self.flight),"pathway_rates":dict(self.pathway_rates),
            "world":copy.deepcopy(self.world),"last":self.last,
            "trail_history":copy.deepcopy(self.trail_history),
            "pivots":copy.deepcopy(self.pivots),
        }
    def restore_state(self, snap):
        import copy
        self.fly=copy.deepcopy(snap["fly"]); self.needs=dict(snap["needs"])
        self.compass=snap["compass"]; self.running=snap["running"]; self.tick=snap["tick"]
        self.custom_index=snap["custom_index"]; self.cooldowns=dict(snap["cooldowns"]); self.event=snap.get("event","")
        self.interaction=copy.deepcopy(snap["interaction"]) if snap["interaction"] else None
        self.waypoint=dict(snap["waypoint"]); self.waypoint_until=snap["waypoint_until"]
        self.depart_until=snap["depart_until"]
        self.traffic_until=snap["traffic_until"]; self.traffic_next=snap["traffic_next"]
        self.flight=dict(snap["flight"]); self.pathway_rates=dict(snap["pathway_rates"])
        self.world=copy.deepcopy(snap["world"]); self.last=snap["last"]
        self.trail_history=copy.deepcopy(snap["trail_history"])
        self.pivots=copy.deepcopy(snap["pivots"])
    def branches(self, seeds, steps):
        """Four honestly-named counterfactual futures from the current tick.
        branch 0 = baseline           (same state, seeded stochastic choices)
        branch 1 = sated              (hunger/thirst/fatigue reduced)
        branch 2 = exhausted          (fatigue elevated)
        branch 3 = scrambled_pathway  (same weights, randomly reassigned to edges)
        Each runs in a sandbox clone; the live world is never mutated.
        """
        snap=self.snapshot_state()
        def _scramble_pathway(b):
            # Null comparison: preserve the observed weight distribution but randomly
            # reassign weights to edges. World goals, compass, and hazard policy stay intact.
            weights=[e["synapses"] for e in verified_pathway()["edges"]]
            random.shuffle(weights)
            b._weight_override = weights
        scenarios=[
            ("baseline",     lambda b: None),
            ("sated",        lambda b: b.needs.update(hunger=0.08,thirst=0.08,fatigue=0.08)),
            ("exhausted",    lambda b: b.needs.update(hunger=0.2,thirst=0.2,fatigue=0.95)),
            ("scrambled_pathway", _scramble_pathway),
        ]
        results=[]
        for i, seed in enumerate(seeds[:len(scenarios)]):
            name, perturb = scenarios[i]
            branch=OpenWorld.__new__(OpenWorld); branch.lock=threading.RLock()
            branch.restore_state(snap)
            saved=random.getstate(); random.seed(int(seed)*1000+i)
            try:
                perturb(branch)
                trajectory=[]; now=branch.last
                for _ in range(steps):
                    now+=0.12
                    branch.step(now=now,dt=0.12)
                    f=branch.fly
                    trajectory.append({"tick":branch.tick,"x":round(f["x"],4),"y":round(f["y"],4),"z":round(f["z"],4),"heading":round(f["heading"],4),"compass":branch.compass,"mode":branch.flight["mode"]})
            finally:
                random.setstate(saved)
            results.append({"seed":int(seed),"scenario":name,"trajectory":trajectory,"final_needs":{k:round(v,3) for k,v in branch.needs.items()}})
        return {"from_tick":snap["tick"],"steps":steps,"world_span":self.world["span"],"branches":results}
    def snapshot(self, dm1=None, va2=None, goal="sample"):
        f=self.fly
        if dm1 is None:
            foods=[s for s in self.world["sources"] if s["kind"]=="food"]
            dm1=max((self.odor(s,f["x"],f["y"],f["z"]) for s in foods if s.get("odor")=="DM1"),default=0.0)
            va2=max((self.odor(s,f["x"],f["y"],f["z"]) for s in foods if s.get("odor")=="VA2"),default=0.0)
        od,cp=circuit("odor"),circuit("compass")
        path=verified_pathway(); motor_drive=self.pathway_rates[path["nodes"][-1]["body"]]
        active=[]
        for e in od["edges"]: active.append({**e,"activity":round((dm1 if "DM1" in e["pre_type"] else va2)*e["synapses"],2),"module":"olfactory"})
        for e in cp["edges"][:16]: active.append({**e,"activity":round((.82 if self.compass else .05)*e["synapses"],2),"module":"compass"})
        for edge in path["edges"]:
            tbar_nt=edge.get("tbar_dominant_prediction")
            transmitter=(f"{tbar_nt} / per-synapse prediction" if tbar_nt and tbar_nt!="unavailable" else "per-neuron prediction")
            active.append({**edge,"neuropil":edge["roi_status"],"neurotransmitter":transmitter,"activity":round(self.pathway_rates[edge["post"]]*edge["synapses"],2),"module":"verified_pathway"})
        home=self.world["home"]; vector=[round(home[0]-f["x"],3),round(home[1]-f["y"],3),round(home[2]-f["z"],3)]
        coords=pathway_cell_coords(); pathway={**path,"motor_drive":round(motor_drive,3),"validation":pathway_validation(),"nodes":[{**node,"rate":round(self.pathway_rates[node["body"]],3),"coord":coords.get(node["body"])} for node in path["nodes"]],"edges":[{**edge,"activity":round(self.pathway_rates[edge["post"]]*edge["synapses"],2)} for edge in path["edges"]]}
        synapse_data=synapse_data_status()
        if self.interaction:
            progress=clamp((time.monotonic()-self.interaction["started_at"])/self.interaction["duration"])
            interaction={**self.interaction,"progress":round(progress,3),"remaining":round(max(0,self.interaction["duration"]*(1-progress)),2)}
        else: interaction={"active":False,"mode":None,"source_id":None,"duration":0,"progress":0,"remaining":0}
        return {"fly":f,"needs":self.needs,"world":self.world,"flight":self.flight,"interaction":interaction,"compass_enabled":self.compass,"running":self.running,"event":self.event,"goal":goal,"behavior":interaction["mode"] if interaction["active"] else "flying",
                "senses":{"dm1":round(dm1,3),"va2":round(va2,3),"optic_flow":round(f["speed"]*10,3),"altitude":round(f["z"],3),"airflow":self.world["wind"],"home_vector":vector},"active_edges":active,
                "pathway":pathway,"data":{"dataset":od["dataset"],"odor_members":od["member_count"],"compass_members":cp["member_count"],"gpu_vram_mb":0,"synapse_tables_ready":synapse_data["all_tables_ready"],"synapse_table_count":synapse_data["table_count"],"selected_partner_rows":synapse_data["selected_partner_rows"],"synapse_runtime_mode":synapse_data["runtime_mode"]},"model_note":od["note"]}
    def _pivot(self, kind, detail=None):
        self.pivots.append({"tick":self.tick,"wall":round(time.monotonic(),3),"kind":kind,"detail":detail or {}})
        self.pivots=self.pivots[-100:]
    def act(self, action, params=None):
        with self.lock:
            if action=="pause": self.running=not self.running
            elif action=="lesion":
                self.compass=not self.compass; self._pivot("lesion",{"compass":self.compass})
            elif action=="reset": self.reset()
            elif action in self.needs: self.needs[action]=clamp(self.needs[action]+.24); self.event=f"{action} drive increased"
            elif action=="stimulus":
                params=params or {}
                try:
                    kind=params.get("kind",[""])[0]; x=float(params.get("x",[""])[0]); y=float(params.get("y",[""])[0]); z=float(params.get("z",["0"])[0])
                    if self.add_stimulus(kind,x,y,z): self._pivot("stimulus",{"kind":kind,"x":round(x,3),"y":round(y,3),"z":round(z,3)})
                    else: self.event="unsupported stimulus"
                except (ValueError, TypeError): self.event="invalid stimulus drop"
            elif action=="move_fly":
                params=params or {}
                try:
                    mx=float(params.get("x",[""])[0]); my=float(params.get("y",[""])[0]); mz=float(params.get("z",[""])[0])
                    self.move_fly(mx,my,mz); self._pivot("move_fly",{"x":round(mx,3),"y":round(my,3),"z":round(mz,3)})
                except (ValueError, TypeError): self.event="invalid fly reposition"
            elif action=="remove":
                if self.remove_stimulus((params or {}).get("id",[""])[0]): self._pivot("remove",{})
            elif action=="clear_stimuli": self.clear_stimuli(); self._pivot("clear",{})
            return self.step()

WORLD=OpenWorld()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/"dist"),**kw)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/api/world":
            query=parse_qs(parsed.query)
            with WORLD.lock: return self.reply(WORLD.act(query.get("action",[""])[0],query) if "action" in query else WORLD.step())
        if parsed.path=="/api/worldline":
            with WORLD.lock: return self.reply({"history":WORLD.trail_history,"pivots":WORLD.pivots,"tick":WORLD.tick,"world_span":WORLD.world["span"]})
        if parsed.path=="/api/branches":
            q=parse_qs(parsed.query)
            try:
                seeds=[int(s) for s in q.get("seeds",["1,2,3,4"])[0].split(",") if s.strip()]
                steps=min(400,max(1,int(q.get("steps",["120"])[0])))
            except (ValueError,TypeError): return self.reply({"error":"invalid params"},HTTPStatus.BAD_REQUEST)
            with WORLD.lock: return self.reply(WORLD.branches(seeds,steps))
        if parsed.path=="/api/connectome":
            try:return self.reply(circuit(parse_qs(parsed.query).get("circuit",["odor"])[0]))
            except ValueError as e:return self.reply({"error":str(e)},HTTPStatus.BAD_REQUEST)
        if parsed.path=="/api/health":
            synapse_data=synapse_data_status()
            portable_ready=PORTABLE_CIRCUITS.exists() and PATHWAY.exists() and VALIDATION.exists()
            return self.reply({"status":"ok" if portable_ready else "degraded","data_ready":portable_ready,"raw_tables_ready":synapse_data["all_tables_ready"],"gpu_vram_used_mb":0,"synapse_data":synapse_data})
        return super().do_GET()
    def reply(self,payload,status=HTTPStatus.OK):
        body=json.dumps(payload).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=="__main__":
    print("CHRONOS open world at http://127.0.0.1:4173");ThreadingHTTPServer(("127.0.0.1",4173),Handler).serve_forever()
