#Author: Kyle Frohlich
#Date: 20Oct2026
#Purpose: check the status of a post request thats finished or in queue

import getpass
from dwidApi import BASE, call

#checks on a tag import that was already submitted, using the job id dwidApi.py printed
job_id = input("Job ID: ").strip()

#api credentials come from reach support, they are not the normal reach login
username = input("API Username: ").strip()
password = getpass.getpass("API Password: ")

token = call(
    "POST", BASE + "/oauth/token", "Login",
    data={"username": username, "password": password},
)["access_token"]

auth = {"Authorization": f"Bearer {token}"}

#the tag import status route, not the responses one
body = call("GET", f"{BASE}/api/v2/imports/tags/{job_id}", "Status check", headers=auth)
status = body["data"]["status"]
meta = body["meta"]

print(f"\nStatus: {status}")
print(f"tagged: {meta['success_rows']}")
print(f"failed: {meta['failed_rows']}")
print(f"total: {meta['total_rows']}")

if meta["failed_rows"]:
    print(f"\nError details: {body['data']['error_log']}")

if status == "failed":
    print(body.get("message"))