"""Bounded Commons lookup. Reject uncertain identity, missing licence or attribution."""
import json,sys,pathlib,urllib.request,urllib.parse,re,unicodedata,math,time,datetime
def norm(s):
 return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()
def plain(s):return re.sub(r'<[^>]*>','',str(s)).strip()[:500]
def distance(a,b,c,d):
 x,y=math.radians(c-a),math.radians(d-b)
 return 6371000*2*math.asin(min(1,math.sqrt(math.sin(x/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(y/2)**2)))
def select(camp,pages):
 center=camp.get('center',camp);name=norm(camp['tags']['name']);out=[]
 for p in pages:
  info=(p.get('imageinfo') or [{}])[0];m=info.get('extmetadata',{});v=lambda k:plain(m.get(k,{}).get('value',''))
  coordinates=p.get('coordinates',[]);license=v('LicenseShortName');author=v('Artist');description=norm(p.get('title','')+' '+v('ImageDescription'))
  if not name or name not in description or info.get('mime') not in ['image/jpeg','image/png']:continue
  if license not in ['CC BY 3.0','CC BY 4.0','CC BY-SA 3.0','CC BY-SA 4.0','CC0','Public domain'] or not author:continue
  close=[x for x in coordinates if x.get('globe','earth')=='earth' and distance(center['lat'],center['lon'],x['lat'],x['lon'])<=200]
  if not close:continue
  thumb=info.get('thumburl','');original=info.get('url','')
  if any(urllib.parse.urlparse(u).scheme!='https' or urllib.parse.urlparse(u).hostname not in ['upload.wikimedia.org','thumb.wikimedia.org'] for u in [thumb,original]):continue
  license_url=v('LicenseUrl').replace('http://','https://',1)
  if urllib.parse.urlparse(license_url).hostname!='creativecommons.org':continue
  out.append({'campsiteId':f"osm-{camp['type']}-{camp['id']}",'title':p['title'],'filePage':'https://commons.wikimedia.org/wiki/'+urllib.parse.quote(p['title'].replace(' ','_'),safe=':'),'author':author,'license':license,'licenseUrl':license_url,'thumbnail':thumb,'image':thumb,'originalUrl':original,'originalDate':v('DateTimeOriginal') or 'Aufnahmedatum unbekannt','verifiedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'association':{'type':'exact_name_and_coordinates','distanceApproxM':round(distance(center['lat'],center['lon'],close[0]['lat'],close[0]['lon']))},'changes':'Vorschaubild verkleinert; keine inhaltliche Bearbeitung.'})
 return out[:6]
def main(folder):
 folder=pathlib.Path(folder);state={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provider':'Wikimedia Commons','records':{},'checked':0,'errors':[]}
 # Retain accepted results across rotating batches; failed lookups never erase them.
 previous={}
 if (folder/'photos.json').exists():
  previous=json.loads((folder/'photos.json').read_text()).get('records',{})
 state['records']=previous
 camps=[]
 for f in ['garda.json','argeles.json','costa-brava.json']:
  if (folder/f).exists():camps.extend(json.loads((folder/f).read_text())['elements'])
 # At most 40 public lookups per run; rotate so every camp is eventually checked.
 offset=(datetime.date.today().toordinal()*40)%max(1,len(camps));camps=(camps[offset:]+camps[:offset])[:40]
 for c in camps:
  try:
   name=re.sub(r'[^\w -]','',c['tags']['name'])[:100]
   query={'action':'query','format':'json','generator':'search','gsrsearch':'intitle:"'+name+'"','gsrnamespace':6,'gsrlimit':3,'prop':'imageinfo|coordinates','iiprop':'url|extmetadata|mime','iiurlwidth':640,'coprimary':'all'}
   req=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(query),headers={'User-Agent':'CampingMatchOSM/2.0 (https://github.com/jonasbueche97-collab/campingmatch-osm-data)'})
   with urllib.request.urlopen(req,timeout=12) as r:
    raw=r.read(500001)
    if len(raw)>500000:raise ValueError('Response cap')
    data=json.loads(raw)
   if 'error' in data:raise ValueError(str(data['error'])[:200])
   cid=f"osm-{c['type']}-{c['id']}";found=select(c,list(data.get('query',{}).get('pages',{}).values()))
   accepted={p['filePage']:p for p in state['records'].get(cid,[]) if p.get('association',{}).get('type')=='exact_name_and_coordinates'}
   accepted.update({p['filePage']:p for p in found})
   state['records'][cid]=list(accepted.values())[:6];state['checked']+=1
  except Exception as e:state['errors'].append(str(e)[:200])
  time.sleep(1)
 (folder/'photos.json').write_text(json.dumps(state,ensure_ascii=False))
 print('Commons lookups',state['checked'],'accepted photos',sum(map(len,state['records'].values())),'errors',len(state['errors']))
 if state['checked']==0 and camps:raise RuntimeError('No Commons lookup succeeded')
if __name__=='__main__':main(sys.argv[1])
