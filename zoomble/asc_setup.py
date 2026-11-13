# Fills the ZOOMBLE App Store listing via the App Store Connect API.
# Prints only HTTP status codes and non-personal info (this repo is public).
import os, re, sys, time, json, glob, hashlib, jwt, urllib.request, urllib.error

APP = '6834303301'
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, 'listing.json')))

kid = re.sub('[^A-Z0-9]', '', os.environ.get('ASC_KEY_ID', ''))
if len(kid) != 10: kid = '4UJ35AQA52'
iss = re.sub('[^0-9a-f-]', '', os.environ.get('ASC_ISSUER_ID', '').lower())
if len(iss) != 36: iss = '31319e07-4ccb-43a4-9397-f6b6cacdf22a'
key = '\n'.join(l.strip() for l in os.environ['ASC_KEY_P8'].replace('\r', '').lstrip('﻿').split('\n') if l.strip())

def tok():
    return jwt.encode({'iss': iss, 'iat': int(time.time()), 'exp': int(time.time()) + 1100, 'aud': 'appstoreconnect-v1'}, key, algorithm='ES256', headers={'kid': kid, 'typ': 'JWT'})
TOK = tok()

def call(method, path, body=None):
    url = path if path.startswith('http') else 'https://api.appstoreconnect.apple.com' + path
    req = urllib.request.Request(url, method=method, headers={'Authorization': 'Bearer ' + TOK, 'Content-Type': 'application/json'}, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf8', 'replace')
        try:
            errs = json.loads(txt).get('errors', [])
            txt = ' | '.join((x.get('code', '') + ': ' + x.get('detail', '')[:300]) for x in errs)
        except Exception:
            txt = txt[:400]
        return e.code, txt

def log(*a): print(*a, flush=True)

# ---------- app: content rights
s, d = call('PATCH', f'/v1/apps/{APP}', {'data': {'type': 'apps', 'id': APP, 'attributes': {'contentRightsDeclaration': 'DOES_NOT_USE_THIRD_PARTY_CONTENT'}}})
log('content rights', s, d if s >= 300 else '')

# ---------- app info: categories, name/subtitle/privacy url, age rating
s, d = call('GET', f'/v1/apps/{APP}/appInfos')
info = [x for x in d['data'] if x['attributes'].get('appStoreState') != 'READY_FOR_SALE' and x['attributes'].get('state') != 'READY_FOR_DISTRIBUTION'][0] if s == 200 else None
log('appInfos', s, info and info['attributes'].get('state'))
if info:
    iid = info['id']
    s, d = call('PATCH', f'/v1/appInfos/{iid}', {'data': {'type': 'appInfos', 'id': iid, 'relationships': {
        'primaryCategory': {'data': {'type': 'appCategories', 'id': 'GAMES'}},
        'primarySubcategoryOne': {'data': {'type': 'appCategories', 'id': 'GAMES_RACING'}},
        'primarySubcategoryTwo': {'data': {'type': 'appCategories', 'id': 'GAMES_CASUAL'}},
        'secondaryCategory': {'data': {'type': 'appCategories', 'id': 'ENTERTAINMENT'}}}}})
    log('categories', s, d if s >= 300 else '')
    s, d = call('GET', f'/v1/appInfos/{iid}/appInfoLocalizations')
    for loc in (d['data'] if s == 200 else []):
        if loc['attributes']['locale'].startswith('en'):
            s2, d2 = call('PATCH', f"/v1/appInfoLocalizations/{loc['id']}", {'data': {'type': 'appInfoLocalizations', 'id': loc['id'], 'attributes': {
                'subtitle': L['subtitle'], 'privacyPolicyUrl': L['privacy']}}})
            log('appInfoLocalization', loc['attributes']['locale'], s2, d2 if s2 >= 300 else '')
    s, d = call('GET', f'/v1/appInfos/{iid}/ageRatingDeclaration')
    if s == 200:
        aid = d['data']['id']; cur = d['data']['attributes']
        log('age rating fields', sorted(cur.keys()))
        want = {}
        for k, v in cur.items():
            if isinstance(v, bool) or v is None and k in ('gambling', 'unrestrictedWebAccess', 'lootBox', 'messagingAndChat', 'userGeneratedContent', 'parentalControls', 'ageAssurance', 'healthOrWellnessTopics', 'seventeenPlus', 'advertising'):
                want[k] = False
            elif isinstance(v, str) or v is None:
                if k in ('kidsAgeBand', 'koreaAgeRatingOverride', 'ageRatingOverride', 'ageRatingOverrideV2', 'developerAgeRatingInfoUrl'):
                    continue
                want[k] = 'NONE'
        want['violenceCartoonOrFantasy'] = 'INFREQUENT_OR_MILD'
        if 'advertising' in cur: want['advertising'] = True
        s2, d2 = call('PATCH', f'/v1/ageRatingDeclarations/{aid}', {'data': {'type': 'ageRatingDeclarations', 'id': aid, 'attributes': want}})
        log('age rating', s2, d2 if s2 >= 300 else '')
        if s2 >= 300:
            # retry dropping fields the API complains about
            for bad in re.findall(r"'?/data/attributes/(\w+)", str(d2)) + re.findall(r'attribute \'?(\w+)', str(d2)):
                want.pop(bad, None)
            s3, d3 = call('PATCH', f'/v1/ageRatingDeclarations/{aid}', {'data': {'type': 'ageRatingDeclarations', 'id': aid, 'attributes': want}})
            log('age rating retry', s3, d3 if s3 >= 300 else '')

# ---------- version
s, d = call('GET', f'/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS')
ver = [x for x in d['data'] if x['attributes']['appStoreState'] in ('PREPARE_FOR_SUBMISSION', 'DEVELOPER_REJECTED', 'REJECTED', 'METADATA_REJECTED')][0] if s == 200 and d['data'] else None
log('version', s, ver and (ver['attributes']['versionString'], ver['attributes']['appStoreState']))
vid = ver and ver['id']
if vid:
    s, d = call('GET', f'/v1/apps/{APP}/builds?sort=-uploadedDate&limit=5')
    build = None
    for b in (d['data'] if s == 200 else []):
        log('build', b['attributes']['version'], b['attributes']['processingState'])
        if b['attributes']['processingState'] == 'VALID' and b['attributes']['version'] == L.get('build', b['attributes']['version']):
            build = b; break
    body = {'data': {'type': 'appStoreVersions', 'id': vid, 'attributes': {'versionString': L['version'], 'copyright': L['copyright'], 'releaseType': 'MANUAL'}}}
    if build: body['data']['relationships'] = {'build': {'data': {'type': 'builds', 'id': build['id']}}}
    s, d = call('PATCH', f'/v1/appStoreVersions/{vid}', body)
    log('version patch', s, d if s >= 300 else '', 'build', build and build['attributes']['version'])
    s, d = call('GET', f'/v1/appStoreVersions/{vid}/appStoreVersionLocalizations')
    for loc in (d['data'] if s == 200 else []):
        if not loc['attributes']['locale'].startswith('en'): continue
        lid = loc['id']
        s2, d2 = call('PATCH', f'/v1/appStoreVersionLocalizations/{lid}', {'data': {'type': 'appStoreVersionLocalizations', 'id': lid, 'attributes': {
            'description': L['description'], 'keywords': L['keywords'], 'promotionalText': L['promo'], 'supportUrl': L['support'], 'marketingUrl': L['support']}}})
        log('version localization', loc['attributes']['locale'], s2, d2 if s2 >= 300 else '')
        # screenshots
        s3, d3 = call('GET', f'/v1/appStoreVersionLocalizations/{lid}/appScreenshotSets')
        sets = {x['attributes']['screenshotDisplayType']: x['id'] for x in (d3['data'] if s3 == 200 else [])}
        for dtype, folder in (('APP_IPHONE_67', 'phone'), ('APP_IPAD_PRO_3GEN_129', 'ipad')):
            files = sorted(glob.glob(os.path.join(HERE, 'shots', folder, '*.png')))
            if not files: continue
            sid = sets.get(dtype)
            if not sid:
                s4, d4 = call('POST', '/v1/appScreenshotSets', {'data': {'type': 'appScreenshotSets', 'attributes': {'screenshotDisplayType': dtype}, 'relationships': {'appStoreVersionLocalization': {'data': {'type': 'appStoreVersionLocalizations', 'id': lid}}}}})
                log('create set', dtype, s4, d4 if s4 >= 300 else '')
                if s4 >= 300: continue
                sid = d4['data']['id']
            # remove old screenshots in the set
            s5, d5 = call('GET', f'/v1/appScreenshotSets/{sid}/appScreenshots')
            for old in (d5['data'] if s5 == 200 else []):
                call('DELETE', f"/v1/appScreenshots/{old['id']}")
            for f in files:
                data = open(f, 'rb').read()
                s6, d6 = call('POST', '/v1/appScreenshots', {'data': {'type': 'appScreenshots', 'attributes': {'fileName': os.path.basename(f), 'fileSize': len(data)}, 'relationships': {'appScreenshotSet': {'data': {'type': 'appScreenshotSets', 'id': sid}}}}})
                if s6 >= 300: log('reserve', f, s6, d6); continue
                shot = d6['data']
                for op in shot['attributes']['uploadOperations']:
                    chunk = data[op['offset']:op['offset'] + op['length']]
                    req = urllib.request.Request(op['url'], method=op['method'], data=chunk, headers={h['name']: h['value'] for h in op['requestHeaders']})
                    with urllib.request.urlopen(req) as r: pass
                s7, d7 = call('PATCH', f"/v1/appScreenshots/{shot['id']}", {'data': {'type': 'appScreenshots', 'id': shot['id'], 'attributes': {'uploaded': True, 'sourceFileChecksum': hashlib.md5(data).hexdigest()}}})
                log('screenshot', dtype, os.path.basename(f), s7, d7 if s7 >= 300 else '')

# ---------- price: free
s, d = call('GET', f'/v1/apps/{APP}/appPricePoints?filter[territory]=USA&limit=200')
free = None
for p in (d['data'] if s == 200 else []):
    if float(p['attributes'].get('customerPrice') or 0) == 0.0: free = p['id']; break
log('price points', s, 'free found' if free else 'no free point')
if free:
    body = {'data': {'type': 'appPriceSchedules', 'relationships': {
        'app': {'data': {'type': 'apps', 'id': APP}},
        'baseTerritory': {'data': {'type': 'territories', 'id': 'USA'}},
        'manualPrices': {'data': [{'type': 'appPrices', 'id': '${price1}'}]}}},
        'included': [{'type': 'appPrices', 'id': '${price1}', 'attributes': {'startDate': None}, 'relationships': {'appPricePoint': {'data': {'type': 'appPricePoints', 'id': free}}}}]}
    s, d = call('POST', '/v1/appPriceSchedules', body)
    log('price schedule', s, d if s >= 300 else '')

# ---------- availability: all territories
s, d = call('GET', '/v1/territories?limit=200')
terr = [t['id'] for t in d['data']] if s == 200 else []
log('territories', s, len(terr))
s0, d0 = call('GET', f'/v1/apps/{APP}/appAvailabilityV2')
log('availability get', s0, '' if s0 == 200 else d0)
if s0 != 200 and terr:
    inc = [{'type': 'territoryAvailabilities', 'id': '${t%d}' % i, 'attributes': {'available': True}, 'relationships': {'territory': {'data': {'type': 'territories', 'id': t}}}} for i, t in enumerate(terr)]
    body = {'data': {'type': 'appAvailabilities', 'attributes': {'availableInNewTerritories': True}, 'relationships': {
        'app': {'data': {'type': 'apps', 'id': APP}},
        'territoryAvailabilities': {'data': [{'type': 'territoryAvailabilities', 'id': x['id']} for x in inc]}}}, 'included': inc}
    s, d = call('POST', '/v2/appAvailabilities', body)
    log('availability', s, d if s >= 300 else '')
log('DONE')
