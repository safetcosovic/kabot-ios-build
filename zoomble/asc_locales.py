# Adds pt-BR, es-MX, id and tr localizations to the ZOOMBLE App Store listing (app info + current editable version).
# Prints only HTTP status codes (public repo). Screenshots fall back to the primary language.
import os, re, time, json, jwt, urllib.request, urllib.error
APP = '6834303301'
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, 'listing.json')))
LOC = json.load(open(os.path.join(HERE, 'locales.json')))
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
def log(*a): print(*a, flush=True)

# app info localizations (name, subtitle, privacy URL)
s, d = call('GET', f'/v1/apps/{APP}/appInfos')
infos = [x for x in d.get('data', [])] if s == 200 else []
info = next((x for x in infos if x['attributes'].get('state') not in ('READY_FOR_DISTRIBUTION',) and x['attributes'].get('appStoreState') != 'READY_FOR_SALE'), infos[0] if infos else None)
log('appInfo', s, info and info['attributes'].get('state'))
if info:
    iid = info['id']
    s, d = call('GET', f'/v1/appInfos/{iid}/appInfoLocalizations?limit=50')
    have = {x['attributes']['locale']: x['id'] for x in d.get('data', [])} if s == 200 else {}
    log('existing appInfo locales', sorted(have))
    for loc, v in LOC.items():
        attrs = {'name': v['name'], 'subtitle': v['subtitle'], 'privacyPolicyUrl': L['privacy']}
        if loc in have:
            s2, d2 = call('PATCH', f'/v1/appInfoLocalizations/{have[loc]}', {'data': {'type': 'appInfoLocalizations', 'id': have[loc], 'attributes': attrs}})
        else:
            attrs['locale'] = loc
            s2, d2 = call('POST', '/v1/appInfoLocalizations', {'data': {'type': 'appInfoLocalizations', 'attributes': attrs, 'relationships': {'appInfo': {'data': {'type': 'appInfos', 'id': iid}}}}})
        log('appInfoLocalization', loc, s2, d2 if s2 >= 300 else '')

# version localizations
s, d = call('GET', f'/v1/apps/{APP}/appStoreVersions?limit=10')
ver = next((x for x in d.get('data', []) if x['attributes'].get('appStoreState') in ('PREPARE_FOR_SUBMISSION', 'DEVELOPER_REJECTED', 'REJECTED', 'METADATA_REJECTED')), None) if s == 200 else None
log('version', s, ver and (ver['attributes']['versionString'], ver['attributes'].get('appStoreState')))
if ver:
    vid = ver['id']
    s, d = call('GET', f'/v1/appStoreVersions/{vid}/appStoreVersionLocalizations?limit=50')
    have = {x['attributes']['locale']: x['id'] for x in d.get('data', [])} if s == 200 else {}
    log('existing version locales', sorted(have))
    for loc, v in LOC.items():
        attrs = {'description': v['description'], 'keywords': v['keywords'], 'promotionalText': v['promo'], 'supportUrl': L['support'], 'marketingUrl': L['support']}
        if loc in have:
            s2, d2 = call('PATCH', f'/v1/appStoreVersionLocalizations/{have[loc]}', {'data': {'type': 'appStoreVersionLocalizations', 'id': have[loc], 'attributes': attrs}})
        else:
            attrs['locale'] = loc
            s2, d2 = call('POST', '/v1/appStoreVersionLocalizations', {'data': {'type': 'appStoreVersionLocalizations', 'attributes': attrs, 'relationships': {'appStoreVersion': {'data': {'type': 'appStoreVersions', 'id': vid}}}}})
        log('versionLocalization', loc, s2, d2 if s2 >= 300 else '')
