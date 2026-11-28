# Read-only: what is still missing before ZOOMBLE 1.0.0 can be sent to App Review.
# Prints only counts, states and field names (this repo is public). Changes nothing.
import os, re, time, json, jwt, urllib.request, urllib.error
APP = '6834303301'
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
missing = []
def ln(v): return len(v or '')
print('\n===== ZOOMBLE readiness (read-only)')
s, a = call(f'/v1/apps/{APP}')
if s == 200:
    at = a['data']['attributes']
    print(' contentRights', at.get('contentRightsDeclaration'), '| primaryLocale', at.get('primaryLocale'))
    if not at.get('contentRightsDeclaration'): missing.append('content rights')
s, d = call(f'/v1/apps/{APP}/appInfos?include=primaryCategory,ageRatingDeclaration')
for info in (d.get('data', []) if s == 200 else []):
    iat = info['attributes']; print(' appInfo', iat.get('state') or iat.get('appStoreState'), '| ageRating', iat.get('appStoreAgeRating'))
    rel = info.get('relationships', {})
    pc = (rel.get('primaryCategory', {}).get('data') or {}).get('id')
    print('  primaryCategory', pc)
    if not pc: missing.append('primary category')
    s2, ls = call(f"/v1/appInfos/{info['id']}/appInfoLocalizations")
    for l in (ls.get('data', []) if s2 == 200 else []):
        la = l['attributes']
        print('  info loc', la['locale'], 'name', ln(la.get('name')), 'subtitle', ln(la.get('subtitle')), 'privacyUrl', bool(la.get('privacyPolicyUrl')))
    s3, ar = call(f"/v1/appInfos/{info['id']}/ageRatingDeclaration")
    if s3 == 200:
        ara = ar['data']['attributes']
        unset = sorted(k for k, v in ara.items() if v is None and k not in ('kidsAgeBand', 'koreaAgeRatingOverride', 'ageRatingOverride', 'ageRatingOverrideV2', 'developerAgeRatingInfoUrl', 'gracRatingClassificationNumber'))
        print('  age rating set:', {k: v for k, v in ara.items() if v not in (None, 'NONE', False)})
        print('  age rating UNSET fields:', unset)
        if unset: missing.append('age rating questions: ' + ','.join(unset))
    else: print('  ageRating', s3, ar)
s, v = call(f'/v1/apps/{APP}/appStoreVersions?filter[platform]=IOS&limit=5')
ver = [x for x in v.get('data', []) if x['attributes'].get('appStoreState') in ('PREPARE_FOR_SUBMISSION', 'DEVELOPER_REJECTED', 'REJECTED', 'METADATA_REJECTED')]
if not ver: print(' no editable version'); missing.append('editable version')
for x in ver[:1]:
    vid = x['id']; at = x['attributes']
    print(' version', at['versionString'], at.get('appStoreState'), '| copyright', bool(at.get('copyright')), '| releaseType', at.get('releaseType'))
    if not at.get('copyright'): missing.append('copyright')
    s, b = call(f'/v1/appStoreVersions/{vid}/build')
    bd = b.get('data') if s == 200 else None
    if bd:
        ba = bd['attributes']; print('  attached build', ba.get('version'), ba.get('processingState'), '| usesNonExemptEncryption', ba.get('usesNonExemptEncryption'))
        if ba.get('version') != '58902052.0.3': missing.append('attach newest build 58902052.0.3 (attached: %s)' % ba.get('version'))
        if ba.get('usesNonExemptEncryption') is None: missing.append('export compliance (encryption) for build')
    else:
        print('  attached build: NONE'); missing.append('attach build 58902052.0.3')
    s, bl = call(f'/v1/builds?filter[app]={APP}&filter[version]=58902052.0.3')
    for bb in (bl.get('data', []) if s == 200 else []):
        print('  newest build encryption flag', bb['attributes'].get('usesNonExemptEncryption'), '| expired', bb['attributes'].get('expired'))
    s, locs = call(f'/v1/appStoreVersions/{vid}/appStoreVersionLocalizations')
    for l in (locs.get('data', []) if s == 200 else []):
        la = l['attributes']
        print('  loc', la['locale'], 'desc', ln(la.get('description')), 'kw', ln(la.get('keywords')), 'promo', ln(la.get('promotionalText')), 'support', bool(la.get('supportUrl')))
        if not la.get('description') or not la.get('keywords') or not la.get('supportUrl'): missing.append('text for ' + la['locale'])
        s2, ss = call(f"/v1/appStoreVersionLocalizations/{l['id']}/appScreenshotSets?include=appScreenshots")
        sets = ss.get('data', []) if s2 == 200 else []
        for st in sets:
            n = len(st.get('relationships', {}).get('appScreenshots', {}).get('data', []))
            print('   shots', st['attributes']['screenshotDisplayType'], n)
        types = {st['attributes']['screenshotDisplayType'] for st in sets if st.get('relationships', {}).get('appScreenshots', {}).get('data')}
        if la['locale'].startswith('en') and not (types & {'APP_IPHONE_67', 'APP_IPHONE_69', 'APP_IPHONE_65'}): missing.append('iPhone 6.5/6.7/6.9 screenshots (' + la['locale'] + ')')
        if la['locale'].startswith('en') and not (types & {'APP_IPAD_PRO_3GEN_129', 'APP_IPAD_PRO_129', 'APP_IPAD_13'}): missing.append('iPad 13" screenshots (' + la['locale'] + ')')
        s3, ps = call(f"/v1/appStoreVersionLocalizations/{l['id']}/appPreviewSets?include=appPreviews")
        for p in (ps.get('data', []) if s3 == 200 else []):
            print('   previews', p['attributes']['previewType'], len(p.get('relationships', {}).get('appPreviews', {}).get('data', [])))
    s, rd = call(f'/v1/appStoreVersions/{vid}/appStoreReviewDetail')
    if s == 200 and rd.get('data'):
        ra = rd['data']['attributes']
        have = {k: bool(ra.get(k)) for k in ('contactFirstName', 'contactLastName', 'contactPhone', 'contactEmail', 'notes')}
        print('  review detail present fields', have, '| demoRequired', ra.get('demoAccountRequired'))
        if not all(have[k] for k in ('contactFirstName', 'contactLastName', 'contactPhone', 'contactEmail')): missing.append('App Review contact info')
    else:
        print('  review detail', s); missing.append('App Review contact info + notes')
s, av = call(f'/v1/apps/{APP}/appAvailabilityV2')
print(' availability', s)
if s != 200: missing.append('availability/territories')
s, pr = call(f'/v1/apps/{APP}/appPriceSchedule')
print(' price schedule', s)
if s != 200: missing.append('price (free)')
print('\n MISSING:', missing if missing else 'nothing found by API')
print(' NOTE: App Privacy labels (data collection) are not readable via API - check in App Store Connect web.')
print('DONE')
