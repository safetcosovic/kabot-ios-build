# Uploads the physical-iPhone review recordings as App Review attachments (no personal data printed).
import os, time, json, hashlib, jwt, urllib.request, urllib.error
kid='4UJ35AQA52'; iss='31319e07-4ccb-43a4-9397-f6b6cacdf22a'
key='\n'.join(l.strip() for l in os.environ['ASC_KEY_P8'].replace('\r','').lstrip('﻿').split('\n') if l.strip())
TOK=jwt.encode({'iss':iss,'iat':int(time.time()),'exp':int(time.time())+1100,'aud':'appstoreconnect-v1'},key,algorithm='ES256',headers={'kid':kid,'typ':'JWT'})
def call(method, path, body=None):
    req=urllib.request.Request('https://api.appstoreconnect.apple.com'+path,method=method,headers={'Authorization':'Bearer '+TOK,'Content-Type':'application/json'},data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r: raw=r.read(); return r.status,(json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e: return e.code, e.read()[:400].decode('utf8','replace')
APPS={'com.knotsy.rings':'knotsy-iphone.mp4','com.unarrow.puzzle':'unarrow-iphone.mp4','com.truckzy.cargo':'truckzy-iphone.mp4'}
s,apps=call('GET','/v1/apps?limit=50')
for a in apps['data']:
    f=APPS.get(a['attributes']['bundleId'])
    if not f: continue
    data=open(os.path.join('/tmp/vids',f),'rb').read()
    print('\n=====',a['attributes']['name'],f,len(data))
    s,v=call('GET',f"/v1/apps/{a['id']}/appStoreVersions?limit=1")
    vid=v['data'][0]['id']
    s,d=call('GET',f"/v1/appStoreVersions/{vid}/appStoreReviewDetail")
    rid=d['data']['id']
    s,att=call('GET',f"/v1/appStoreReviewDetails/{rid}/appStoreReviewAttachments")
    if any(t['attributes'].get('fileName')==f for t in att.get('data',[])): print(' already attached'); continue
    for t in att.get('data',[]):
        ds,dd=call('DELETE',f"/v1/appStoreReviewAttachments/{t['id']}"); print(' removed old',t['attributes'].get('fileName'),ds)
    s,r=call('POST','/v1/appStoreReviewAttachments',{'data':{'type':'appStoreReviewAttachments','attributes':{'fileName':f,'fileSize':len(data)},'relationships':{'appStoreReviewDetail':{'data':{'type':'appStoreReviewDetails','id':rid}}}}})
    if s>=300: print(' reserve',s,r); continue
    at=r['data']
    for op in at['attributes']['uploadOperations']:
        chunk=data[op['offset']:op['offset']+op['length']]
        req=urllib.request.Request(op['url'],method=op['method'],data=chunk,headers={h['name']:h['value'] for h in op['requestHeaders']})
        with urllib.request.urlopen(req) as x: pass
    s,c=call('PATCH',f"/v1/appStoreReviewAttachments/{at['id']}",{'data':{'type':'appStoreReviewAttachments','id':at['id'],'attributes':{'uploaded':True,'sourceFileChecksum':hashlib.md5(data).hexdigest()}}})
    print(' commit',s,'' if s<300 else c)
    time.sleep(8)
    s,chk=call('GET',f"/v1/appStoreReviewAttachments/{at['id']}")
    print(' state',(chk['data']['attributes'].get('assetDeliveryState') or {}).get('state') if s==200 else s)
print('DONE')
