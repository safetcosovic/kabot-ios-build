# Prints App Review status for all apps (no personal data).
import os, re, time, json, jwt, urllib.request, urllib.error
kid = re.sub('[^A-Z0-9]', '', os.environ.get('ASC_KEY_ID', ''))
if len(kid) != 10: kid = '4UJ35AQA52'
iss = re.sub('[^0-9a-f-]', '', os.environ.get('ASC_ISSUER_ID', '').lower())
if len(iss) != 36: iss = '31319e07-4ccb-43a4-9397-f6b6cacdf22a'
key = '\n'.join(l.strip() for l in os.environ['ASC_KEY_P8'].replace('\r', '').lstrip('﻿').split('\n') if l.strip())
TOK = jwt.encode({'iss': iss, 'iat': int(time.time()), 'exp': int(time.time()) + 1100, 'aud': 'appstoreconnect-v1'}, key, algorithm='ES256', headers={'kid': kid, 'typ': 'JWT'})
def call(path):
    req = urllib.request.Request('https://api.appstoreconnect.apple.com' + path, headers={'Authorization': 'Bearer ' + TOK})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, e.read()[:300].decode('utf8', 'replace')
s, apps = call('/v1/apps?limit=50')
for a in apps.get('data', []):
    aid = a['id']; print('\n=====', a['attributes']['name'], a['attributes']['bundleId'])
    s, v = call(f'/v1/apps/{aid}/appStoreVersions?limit=5&include=build')
    for x in v.get('data', []):
        at = x['attributes']; print(' version', at['versionString'], at.get('appVersionState') or at.get('appStoreState'), 'created', at.get('createdDate', '')[:16])
    s, r = call(f'/v1/reviewSubmissions?filter[app]={aid}&limit=10&include=items')
    if s != 200: print(' reviewSubmissions', s, r); continue
    inc = {i['id']: i for i in r.get('included', [])}
    for x in r.get('data', []):
        at = x['attributes']
        print(' submission', at.get('state'), 'submitted', (at.get('submittedDate') or '')[:16], 'platform', at.get('platform'))
        for it in x.get('relationships', {}).get('items', {}).get('data', []):
            i = inc.get(it['id'])
            if i: print('   item', i['attributes'].get('state'))
    s, b = call(f'/v1/builds?filter[app]={aid}&sort=-uploadedDate&limit=3')
    for x in b.get('data', []):
        at = x['attributes']; print(' build', at['version'], at['processingState'], at.get('uploadedDate', '')[:16], 'expired' if at.get('expired') else '')
print('DONE')
