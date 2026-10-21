#Author: Kyle Frohlich
#Date: 20Oct2026
#Purpose: code used to upload files via reach api for POST

import getpass
import time
import requests

BASE = "https://api.reach.vote"

VALID_ID_TYPES = ["Reach ID", "State File ID", "Voterfile VAN ID", "DWID", "Voterbase ID", "DNC Person ID"]


#wrapper for every api call so a failure prints reach's own message instead of a traceback
def call(method, url, what, **kwargs):

    response = requests.request(method, url, timeout=30, **kwargs)
    if not response.ok:

        print(f"\n{what} failed ({response.status_code})")
        #reach puts its explanation in detail on some routes and message on others
        try:
            body = response.json()
            print(body.get("detail") or body.get("message") or response.text)

            if body.get("data"):
                print(body["data"])

        except ValueError:
            print(response.text)

        raise SystemExit(1)

    return response.json()


def main():

    print("Ctrl+c at any time if you make a mistake to cancel the push. \n\n")

    #meant to gather just the tag and nothing else so it'll append to the path
    pre_tag_id = input("Tag ID: ").strip()
    tag_id = BASE + "/api/v2/imports/tags/" + pre_tag_id

    #gets the pre-signed url for the file meant to be uploaded
    file_url = input("Signed URL: ").strip()

    #forces the user to enter a valid id type (likely DWID)
    while True:
        person_id_type = input("Person ID Type: ").strip()
        if person_id_type in VALID_ID_TYPES:
            break
        print("Must be one of: " + ", ".join(VALID_ID_TYPES))

    #forces the user to enter an action
    while True:
        action = input("Action (add or remove): ").strip().lower()
        if action in ("add", "remove"):
            break
        print("Please enter 'add' or 'remove'.")

    #gathers the state, only needed on multi-state campaigns with a non-unique id type
    state = input("State (leave blank if not needed): ").strip().upper()

    #double check for the user
    print("\nPlease confirm everything is 100% correct, otherwise you might waste a lot of time since you get placed in a queue at the Reach endpoint \n")
    print("Tag ID: ", pre_tag_id)
    print("File URL: ", file_url)
    print("Person ID Type: ", person_id_type)
    print("Action: ", action)
    print("State: ", state if state else "(none)")
    confirm = input("\nConfirm y/n: ").strip().lower()

    if confirm != "y":
        print("Aborted POST, nothing was sent")
        return

    #api credentials come from reach support, they are not the normal reach login
    username = input("\nAPI Username: ").strip()
    password = getpass.getpass("API Password: ")

    #login is form encoded, so data= not json=
    token = call(
        "POST", BASE + "/oauth/token", "Login",
        data={"username": username, "password": password},
    )["access_token"]

    auth = {"Authorization": f"Bearer {token}"}

    #state is left out entirely when blank, an empty string would be rejected
    payload = {
        "file_url": file_url,
        "person_id_type": person_id_type,
        "action": action,
    }
    if state:
        payload["state"] = state

    #the actual import request, returns 202 with a job id
    job_id = call("POST", tag_id, "Submit", json=payload, headers=auth)["data"]["id"]

    print(f"\nSubmitted successfully.")
    print(f"Job ID: {job_id}")
    print("\nChecking status in 60 seconds...")
    time.sleep(60)

    #one status check, large imports can sit in a queue for over an hour so this may still be running
    body = call("GET", f"{BASE}/api/v2/imports/tags/{job_id}", "Status check", headers=auth)
    status = body["data"]["status"]
    meta = body["meta"]

    #prints if it failed or not
    print(f"\nStatus: {status}")
    #check what passed or failed
    print(f"tagged: {meta['success_rows']}")
    print(f"failed: {meta['failed_rows']}")
    print(f"total: {meta['total_rows']}")

    if meta["failed_rows"]:
        print(f"\nError details: {body['data']['error_log']}")

    if status == "failed":
        print(body.get("message"))

    if status not in ("completed", "failed", "cancelled"):
        print(f"\nStill processing. Re-run a status check later with Job ID: {job_id}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled. Nothing was sent.")
