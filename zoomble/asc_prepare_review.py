# Preparation only (NO submission): fills unanswered age-rating questions with "no"
# and attaches the newest VALID build to the editable 1.0.0 version. Prints statuses only.
import os, re, time, json, jwt, urllib.request, urllib.error
APP = '6834303301'; WANT_BUILD = '58902052.0.3'
kid = re.sub('[^A-Z0-9]', '', os.environ.get('ASC_KEY_ID', ''))
if len(kid) != 10: kid = '4UJ35AQA52'
iss = re.sub('[^0-9a-f-]', '', os.environ.get('ASC_ISSUER_ID', '').lower())
if len(iss) != 36: iss = '31319e07-4ccb-43a4-9397-f6b6cacdf22a'
key = '\n'.join(l.strip() for l in os.environ['ASC_KEY_P8'].replace('\r', '').lstrip('﻿').split('\n') if l.strip())
TOK = jwt.encode({'iss': iss, 'iat': int(time.time()), 'exp': int(time.time()) + 1100, 'aud': 'appstoreconnect-v1'}, key, algorithm='ES256', headers={'kid': kid, 'typ': 'JWT'})
def call(method, path, body=None):
    req = urllib.request.Request('https://api.appstoreconnect.apple.com' + path, method=method, headers={'Authorization': 'Bearer ' + TOK, 'Content-Type': 'application/json'}, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read(); return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf8', 'replace')
        try: txt = ' | '.join((x.get('code', '') + ': ' + x.get('detail', '')[:300]) for x in json.loads(txt).get('errors', []))
        except Exception: txt = txt[:400]
        return e.code, txt
print('\n===== ZOOMBLE prepare (no submission)')
SKIP = ('kidsAgeBand', 'koreaAgeRatingOverride', 'ageRatingOverride', 'ageRatingOverrideV2', 'developerAgeRatingInfoUrl', 'gracRatingClassificationNumber')
s, d = call('GET', f'/v1/apps/{APP}/appInfos')
for info in (d.get('data', []) if s == 200 else []):
    if info['attributes'].get('state') == 'READY_FOR_DISTRIBUTION': continue
    s, ar = call('GET', f"/v1/appInfos/{info['id']}/ageRatingDeclaration")
    if s != 200: print(' age rating get', s, ar); continue
    aid = ar['data']['id']
    for k in sorted(k for k, v in ar['data']['attributes'].items() if v is None and k not in SKIP):
        done = False
        for val in (False, 'NONE'):
            s2, d2 = call('PATCH', f'/v1/ageRatingDeclarations/{aid}', {'data': {'type': 'ageRatingDeclarations', 'id': aid, 'attributes': {k: val}}})
            print(' age rating', k, '=', val, '->', s2, '' if s2 < 300 else d2)
            if s2 < 300: done = True; break
        if not done: print(' age rating', k, 'NOT SET')
s, v = call('GET', f'/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5')
ver = [x for x in v.get('data', []) if x['attributes'].get('appStoreState') == 'PREPARE_FOR_SUBMISSION']
s, bl = call('GET', f'/v1/builds?filter[app]={APP}&filter[version]={WANT_BUILD}')
b = [x for x in (bl.get('data', []) if s == 200 else []) if x['attributes'].get('processingState') == 'VALID']
if ver and b:
    s, d = call('PATCH', f"/v1/appStoreVersions/{ver[0]['id']}/relationships/build", {'data': {'type': 'builds', 'id': b[0]['id']}})
    print(' attach build', WANT_BUILD, '->', s, '' if s < 300 else d)
else:
    print(' attach build skipped: version', bool(ver), 'build', bool(b))
print('DONE prepare')
