"""Finite real Geofabrik download + Garda extraction. No scheduler or credentials."""
import json,os,time,hashlib,urllib.request,datetime,pathlib,sys
import osmium
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
started=time.monotonic(); records={}; sources=[]
class Extract(osmium.SimpleHandler):
 def node(self,n):
  if n.tags.get('tourism')=='camp_site' and n.tags.get('name') and n.location.valid(): self.keep('node',n,n.location.lat,n.location.lon)
 def area(self,a):
  if a.tags.get('tourism')!='camp_site' or not a.tags.get('name'):return
  points=[(n.lat,n.lon) for ring in a.outer_rings() for n in ring if n.location.valid()]
  if not points:return
  self.keep('way' if a.from_way() else 'relation',a,(min(p[0] for p in points)+max(p[0] for p in points))/2,(min(p[1] for p in points)+max(p[1] for p in points))/2,a.orig_id())
 def keep(self,typ,obj,lat,lon,oid=None):
  if not (45.4<=lat<=45.95 and 10.45<=lon<=10.95):return
  oid=oid or obj.id;k=f'{typ}/{oid}';r={'type':typ,'id':oid,'version':obj.version,'timestamp':obj.timestamp.isoformat(),'tags':dict(obj.tags)}
  if typ=='node':r.update(lat=lat,lon=lon)
  else:r['center']={'lat':lat,'lon':lon}
  old=records.get(k)
  if not old or r['timestamp']>old['timestamp']:records[k]=r
  if len(records)>250:raise RuntimeError('250 record cap exceeded')
for region in ['nord-est','nord-ovest']:
 url=f'https://download.geofabrik.de/europe/italy/{region}-latest.osm.pbf';p=out/(region+'.osm.pbf');size=0;sha=hashlib.sha256()
 if time.monotonic()-started>1500:raise RuntimeError('25 minute wall cap')
 print('DOWNLOAD',url,flush=True)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CampingMatchPrivate/1.0'}),timeout=45) as r,open(str(p)+'.partial','wb') as f:
  modified=r.headers.get('Last-Modified')
  while True:
   chunk=r.read(1024*1024)
   if not chunk:break
   size+=len(chunk)
   if size>750_000_000 or time.monotonic()-started>1500:raise RuntimeError('Download resource cap exceeded')
   f.write(chunk);sha.update(chunk)
 os.rename(str(p)+'.partial',p)
 print('EXTRACT',region,size,flush=True)
 Extract().apply_file(str(p),locations=True,idx='sparse_file_array,'+str(out/(region+'.locations')))
 sources.append({'url':url,'bytes':size,'sha256':sha.hexdigest(),'lastModified':modified})
 print('CANDIDATES',len(records),flush=True)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
data={'version':0.6,'generator':'CampingMatch Geofabrik extractor','elements':sorted(records.values(),key=lambda r:(r['type'],r['id']))}
encoded=json.dumps(data,ensure_ascii=False).encode()
if len(encoded)>1500000:raise RuntimeError('Import byte cap exceeded')
(out/'garda-overpass-compatible.json').write_bytes(encoded)
(out/'manifest.json').write_text(json.dumps({'mode':'real-geofabrik-pbf-extraction','at':now,'sources':sources,'records':len(records),'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest(),'attribution':'© OpenStreetMap contributors','license':'https://opendatacommons.org/licenses/odbl/1-0/','bounds':[45.4,10.45,45.95,10.95],'geometry':'OSM polygon bounding-box center; no entrance location','liveImportPerformed':False},indent=2))
print('SUCCESS',len(records),str(out/'manifest.json'),flush=True)
