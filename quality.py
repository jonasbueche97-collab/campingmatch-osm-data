"""Daily official open classification subset. No inferred campsite ratings."""
import csv,io,json,datetime,urllib.request,pathlib
def read(url,cap):
 req=urllib.request.Request(url,headers={'User-Agent':'CampingMatchOpenData/1.0 (https://github.com/jonasbueche97-collab/campingmatch-osm-data)'})
 with urllib.request.urlopen(req,timeout=45) as r:
  raw=r.read(cap+1)
  if len(raw)>cap:raise ValueError('Download limit')
  return raw
metadata=json.loads(read('https://www.data.gouv.fr/api/1/datasets/hebergements-touristiques-classes-en-france/',100000))
if metadata.get('license')!='fr-lo' or metadata.get('organization',{}).get('id')!='534fff57a3a7292c64a77ce4':raise ValueError('Publisher or licence changed')
url='https://data.classement.atout-france.fr/static/exportHebergementsClasses/hebergements_classes.csv'
raw=read(url,5000000)
rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
selected=[r for r in rows if r.get('TYPOLOGIE ÉTABLISSEMENT')=='CAMPING' and r.get('CODE POSTAL')=='66700' and r.get('COMMUNE')=='ARGELÈS-SUR-MER']
if not selected:raise ValueError('No supported regional classifications; previous snapshot retained')
out={'provider':'Atout France','sourceUrl':url,'license':'fr-lo','licenseUrl':'https://www.etalab.gouv.fr/licence-ouverte-open-licence/','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':selected,'attribution':'Atout France · Hébergements touristiques classés en France'}
pathlib.Path('data/quality.json').write_text(json.dumps(out,ensure_ascii=False))
print('Official classifications:',len(selected))
