#!/usr/bin/env python3
"""Attach an uploaded build to its App Store version and submit it for App Review.

Uses the App Store Connect API with the same key as the build. Environment:
  ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_PATH   API key
  BUNDLE_ID                                 e.g. com.stingerzbaseball.gsdtf
  APP_VERSION                               e.g. 1.0
  BUILD_NUMBER                              e.g. 4
  WHATS_NEW                                 release notes (used for updates, not the first version)
"""
import json, os, sys, time, urllib.request, urllib.error
import jwt  # PyJWT

API = "https://api.appstoreconnect.apple.com/v1"
KEY_ID, ISSUER = os.environ["ASC_KEY_ID"], os.environ["ASC_ISSUER_ID"]
KEY = open(os.path.expanduser(os.environ["ASC_KEY_PATH"])).read()
BUNDLE, VERSION, BUILD = os.environ["BUNDLE_ID"], os.environ["APP_VERSION"], os.environ["BUILD_NUMBER"]
WHATS_NEW = os.environ.get("WHATS_NEW") or "Bug fixes and improvements."

EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED",
            "INVALID_BINARY", "DEVELOPER_ACTION_NEEDED"}


def die(msg):
    print(f"::error::{msg}")
    sys.exit(1)


def token():
    now = int(time.time())
    return jwt.encode({"iss": ISSUER, "iat": now, "exp": now + 1100, "aud": "appstoreconnect-v1"},
                      KEY, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})


def call(method, path, body=None, ok_missing=False):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode(errors="replace")
        if ok_missing and e.code == 404:
            return None
        try:
            errs = json.loads(text).get("errors", [])
            detail = "; ".join(f"{x.get('title')}: {x.get('detail')}" for x in errs) or text
        except ValueError:
            detail = text
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}")


# 1. Find the app
apps = call("GET", f"/apps?filter[bundleId]={BUNDLE}&limit=1")["data"]
if not apps:
    die(f"No app in App Store Connect with bundle ID {BUNDLE}.")
app_id = apps[0]["id"]
print(f"App: {apps[0]['attributes']['name']} ({app_id})")

# 2. Wait for the build to finish processing
build_id = None
for i in range(90):  # up to ~45 minutes
    res = call("GET", f"/builds?filter[app]={app_id}&filter[version]={BUILD}"
                      f"&filter[preReleaseVersion.version]={VERSION}&limit=1")["data"]
    if res:
        state = res[0]["attributes"].get("processingState")
        print(f"Build {VERSION} ({BUILD}): {state}")
        if state == "VALID":
            build_id = res[0]["id"]
            break
        if state in ("FAILED", "INVALID"):
            die(f"Apple marked build {BUILD} as {state}. Check App Store Connect → TestFlight for details.")
    else:
        print(f"Waiting for build {BUILD} to appear in App Store Connect…")
    time.sleep(30)
if not build_id:
    die("Timed out waiting for Apple to process the build. Run the workflow again later, or submit it by hand.")

# Export compliance (the app declares ITSAppUsesNonExemptEncryption=false, but set it just in case)
try:
    call("PATCH", f"/builds/{build_id}", {"data": {"type": "builds", "id": build_id,
                                                   "attributes": {"usesNonExemptEncryption": False}}})
except RuntimeError as e:
    print(f"(export compliance already set: {e})")

# 3. Find or create the App Store version
versions = call("GET", f"/apps/{app_id}/appStoreVersions?filter[platform]=IOS&limit=50")["data"]
released = any(v["attributes"]["appStoreState"] in ("READY_FOR_SALE", "REPLACED_WITH_NEW_VERSION")
               for v in versions)
match = next((v for v in versions if v["attributes"]["versionString"] == VERSION), None)
if match:
    state = match["attributes"]["appStoreState"]
    print(f"Version {VERSION}: {state}")
    if state in ("WAITING_FOR_REVIEW", "IN_REVIEW"):
        die(f"Version {VERSION} is already {state.replace('_', ' ').lower()}. "
            "Wait for Apple's decision, or remove it from review in App Store Connect first.")
    if state not in EDITABLE:
        die(f"Version {VERSION} is {state} and can't take a new build. "
            "Run the workflow again with a higher version number, like 1.1.")
    version_id = match["id"]
else:
    open_v = next((v for v in versions if v["attributes"]["appStoreState"] in EDITABLE), None)
    if open_v:
        die(f"Version {open_v['attributes']['versionString']} is still open in App Store Connect. "
            f"Use that version number, or delete it before creating {VERSION}.")
    print(f"Creating version {VERSION}")
    version_id = call("POST", "/appStoreVersions", {"data": {
        "type": "appStoreVersions",
        "attributes": {"platform": "IOS", "versionString": VERSION, "releaseType": "AFTER_APPROVAL"},
        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})["data"]["id"]

# 4. Attach the build
call("PATCH", f"/appStoreVersions/{version_id}/relationships/build",
     {"data": {"type": "builds", "id": build_id}})
print(f"Attached build {BUILD} to version {VERSION}")

# 5. "What's New" text (only allowed on updates, not the first release)
if released:
    locs = call("GET", f"/appStoreVersions/{version_id}/appStoreVersionLocalizations")["data"]
    for loc in locs:
        call("PATCH", f"/appStoreVersionLocalizations/{loc['id']}", {"data": {
            "type": "appStoreVersionLocalizations", "id": loc["id"], "attributes": {"whatsNew": WHATS_NEW}}})
    print(f"Set What's New for {len(locs)} language(s)")

# 6. Submit for review (reuse an open, unsubmitted submission if there is one)
subs = call("GET", f"/reviewSubmissions?filter[app]={app_id}&filter[platform]=IOS"
                   f"&filter[state]=READY_FOR_REVIEW&limit=5")["data"]
if subs:
    sub_id = subs[0]["id"]
else:
    sub_id = call("POST", "/reviewSubmissions", {"data": {
        "type": "reviewSubmissions", "attributes": {"platform": "IOS"},
        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})["data"]["id"]

items = call("GET", f"/reviewSubmissions/{sub_id}/items")["data"]
if not items:
    try:
        call("POST", "/reviewSubmissionItems", {"data": {
            "type": "reviewSubmissionItems",
            "relationships": {
                "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": sub_id}},
                "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}}}})
    except RuntimeError as e:
        die("Apple wouldn't add the version to review. Usually something on the version page is missing "
            f"(screenshots, description, privacy answers, age rating, review contact info). Details: {e}")

try:
    call("PATCH", f"/reviewSubmissions/{sub_id}", {"data": {
        "type": "reviewSubmissions", "id": sub_id, "attributes": {"submitted": True}}})
except RuntimeError as e:
    die(f"Submitting for review failed. Fix what Apple lists below in App Store Connect, then run again. Details: {e}")

print(f"Submitted GS DTF {VERSION} (build {BUILD}) for App Review.")
