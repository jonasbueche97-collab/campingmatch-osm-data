"""Bounded ODbL extracts and geometrically contained facilities; no private data."""
import json, os, time, hashlib, urllib.request, datetime, pathlib, sys
import osmium
out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
REGIONS={
 'garda':('Gardasee',[45.4,10.45,45.95,10.95],['italy/nord-est','italy/nord-ovest']),
 'argeles':('Argelès-sur-Mer',[42.48,2.95,42.62,3.10],['france/languedoc-roussillon']),
 'costa-brava':('Costa Brava',[41.7,2.8,42.3,3.35],['spain/cataluna'])}
def inside(p,ring):
 x,y=p; result=False
 for i,(a,b) in enumerate(ring):
  c,d=ring[i-1]
  if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a: result=not result
 return result
def in_camp(p,polygons):
 return any(inside(p,outer) and not any(inside(p,h) for h in holes) for outer,holes in polygons)
def facility(t):
 return t.get('amenity') in ['restaurant','drinking_water','toilets','shower'] or t.get('shop') in ['supermarket','convenience'] or t.get('leisure') in ['playground','swimming_pool']
def active(t):
 return t.get('access') not in ['no','private'] and not any(t.get(k)=='yes' for k in ['disused','abandoned','demolished'])
def meta(typ,obj,oid=None):
 return {'type':typ,'id':oid or obj.id,'version':obj.version,'timestamp':obj.timestamp.isoformat(),'tags':dict(obj.tags)}
for rid,(name,bounds,extracts) in REGIONS.items():
 records={};polygons={};pois={};sources=[];south,west,north,east=bounds
 def within(lat,lon):return south<=lat<=north and west<=lon<=east
 class Extract(osmium.SimpleHandler):
  def node(self,n):
   if not n.location.valid():return
   lat,lon=n.location.lat,n.location.lon
   if not within(lat,lon):return
   t=dict(n.tags)
   if t.get('tourism')=='camp_site' and t.get('name'):
    self.keep('node',n,lat,lon)
   elif facility(t) and active(t):
    pois[f'node/{n.id}']={**meta('node',n),'lat':lat,'lon':lon}
   if len(pois)>20000:raise RuntimeError('Facility memory cap exceeded')
  def area(self,a):
   t=dict(a.tags);camp=t.get('tourism')=='camp_site' and t.get('name')
   if not camp and not (facility(t) and active(t)):return
   rings=[]
   for outer in a.outer_rings():
    o=[(n.lon,n.lat) for n in outer if n.location.valid()]
    holes=[[(n.lon,n.lat) for n in ring if n.location.valid()] for ring in a.inner_rings(outer)]
    if len(o)>3:rings.append((o,holes))
   points=[p for ring,_ in rings for p in ring]
   if not points:return
   lat=(min(p[1] for p in points)+max(p[1] for p in points))/2;lon=(min(p[0] for p in points)+max(p[0] for p in points))/2
   if not within(lat,lon):return
   typ='way' if a.from_way() else 'relation';oid=a.orig_id();key=f'{typ}/{oid}'
   if camp:self.keep(typ,a,lat,lon,oid);polygons[key]=rings
   else:pois[key]={**meta(typ,a,oid),'lat':lat,'lon':lon,'_points':points}
  def keep(self,typ,obj,lat,lon,oid=None):
   r=meta(typ,obj,oid);r.update({'lat':lat,'lon':lon} if typ=='node' else {'center':{'lat':lat,'lon':lon}})
   k=f'{typ}/{r["id"]}';old=records.get(k)
   if not old or r['timestamp']>old['timestamp']:records[k]=r
   if len(records)>250:raise RuntimeError('250 camps per region cap exceeded')
 for region in extracts:
  url=f'https://download.geofabrik.de/europe/{region}-latest.osm.pbf';p=out/(region.replace('/','-')+'.osm.pbf');size=0;sha=hashlib.sha256()
  print('DOWNLOAD',rid,url,flush=True)
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CampingMatchPrivate/2.0'}),timeout=45) as r,open(str(p)+'.partial','wb') as f:
   modified=r.headers.get('Last-Modified')
   while True:
    chunk=r.read(1024*1024)
    if not chunk:break
    size+=len(chunk)
    if size>750_000_000 or time.monotonic()-started>1500:raise RuntimeError('Download or 25 minute wall cap exceeded')
    f.write(chunk);sha.update(chunk)
  os.rename(str(p)+'.partial',p)
  print('EXTRACT',rid,size,flush=True)
  Extract().apply_file(str(p),locations=True,idx='sparse_file_array,'+str(out/(rid+'-'+region.split('/')[-1]+'.locations')))
  sources.append({'url':url,'bytes':size,'sha256':sha.hexdigest(),'lastModified':modified})
  p.unlink()
 for pk,poi in pois.items():
  pts=poi.get('_points') or [(poi['lon'],poi['lat'])]
  candidates=[k for k,rings in polygons.items() if k!=pk and all(in_camp(p,rings) for p in pts)]
  if len(candidates)!=1:continue
  camp=records[candidates[0]];camp.setdefault('containedFeatures',[])
  if len(camp['containedFeatures'])<50:
   camp['containedFeatures'].append({**{k:v for k,v in poi.items() if k!='_points'},'relationship':'within_osm_camp_polygon','campVersion':camp['version']})
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 data={'version':0.6,'generator':'CampingMatch Geofabrik extractor 2','regionId':rid,'elements':sorted(records.values(),key=lambda r:(r['type'],r['id']))}
 encoded=json.dumps(data,ensure_ascii=False).encode()
 if len(encoded)>1500000:raise RuntimeError('1.5MB per-region import cap exceeded')
 (out/(rid+'.json')).write_bytes(encoded)
 manifest={'mode':'real-geofabrik-pbf-extraction','regionId':rid,'at':now,'sources':sources,'records':len(records),'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest(),'attribution':'© OpenStreetMap contributors','license':'https://opendatacommons.org/licenses/odbl/1-0/','bounds':bounds,'geometry':'camp polygon bbox center; facilities strictly within exactly one camp polygon, excluding holes. No proof of quality, current operation or public access.','facilities':sum(len(r.get('containedFeatures',[])) for r in records.values()),'liveImportPerformed':False}
 (out/(rid+'-manifest.json')).write_text(json.dumps(manifest,indent=2))
 if rid=='garda':(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 print('SUCCESS',rid,len(records),'facilities',manifest['facilities'],flush=True)
