# Shows App Review notes length and attachments per app (no personal data printed).
import os, re, time, json, jwt, urllib.request, urllib.error
kid='4UJ35AQA52'; iss='31319e07-4ccb-43a4-9397-f6b6cacdf22a'
key='\n'.join(l.strip() for l in os.environ['ASC_KEY_P8'].replace('\r','').lstrip('﻿').split('\n') if l.strip())
TOK=jwt.encode({'iss':iss,'iat':int(time.time()),'exp':int(time.time())+1100,'aud':'appstoreconnect-v1'},key,algorithm='ES256',headers={'kid':kid,'typ':'JWT'})
def call(path):
    req=urllib.request.Request('https://api.appstoreconnect.apple.com'+path,headers={'Authorization':'Bearer '+TOK})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, e.read()[:300].decode('utf8','replace')
s,apps=call('/v1/apps?limit=50')
for a in apps['data']:
    print('\n=====',a['attributes']['name'])
    s,v=call(f"/v1/apps/{a['id']}/appStoreVersions?limit=3")
    for x in v['data'][:1]:
        print(' version',x['attributes']['versionString'],x['attributes'].get('appStoreState'))
        s,d=call(f"/v1/appStoreVersions/{x['id']}/appStoreReviewDetail")
        if s!=200: print(' reviewDetail',s); continue
        at=d['data']['attributes']; n=at.get('notes') or ''
        print(' notes chars',len(n),'| mentions recording:', 'record' in n.lower(),'| demoRequired',at.get('demoAccountRequired'))
        print(' notes start:', n[:160].replace('\n',' '))
        s,att=call(f"/v1/appStoreReviewDetails/{d['data']['id']}/appStoreReviewAttachments")
        for t in (att.get('data',[]) if s==200 else []):
            ta=t['attributes']; print(' attachment',ta.get('fileName'),ta.get('fileSize'),(ta.get('assetDeliveryState') or {}).get('state'))
        if s==200 and not att.get('data'): print(' attachments: NONE')
print('DONE')
