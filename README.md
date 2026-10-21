# dwid Reach Tag Import

Adds a Reach tag to (or removes it from) everyone in a list of IDs, without uploading people one by one in Reach.

There are two scripts:

- **`dwidApi.py`** sends the list to Reach and starts the tagging job.
- **`dwidCheck.py`** checks on a job later, using the Job ID that `dwidApi.py` gave you.

Run both from **cmd**, not PowerShell, in the folder where the scripts are saved.

__All of this was tested and run from VSCode, I have no verification of stability of usage outside this environment.__

---

## Before you start (one-time setup)

You need all of these before the first run:

- [ ] **Python 3** installed.
- [ ] **The `requests` library.** In cmd, run (must be cmd not windows powershell):
  ```
  python -m pip install requests
  ```
- [ ] **A Reach API username and password.** These come from Reach support (support@reach.vote). They are **not** your normal Reach login. You may need special accomodations from Reach to get these.
- [ ] **The Tag ID** of the tag you want to apply. The tag must be one that was created by hand in Reach.
- [ ] **A Google Cloud service account email** that can read the bucket your file is in. It looks like `name@project-id.iam.gserviceaccount.com`. Your Google account needs the **Service Account Token Creator** role on that service account.

---

## Step 1: Prepare the file

The file is a list of IDs, **one ID per line**. A header line like `DWID` at the top is fine, though it will show up as one failed row.

- Plain text or CSV. If it's a CSV, Reach only reads the first column.
- IDs must be bare digits, like `123456789`, **not** `123,456,789`. If the list came from Excel or Google Sheets, format the ID column as **Plain text** before exporting.
- Not zipped, and at most 1,000,000 rows / 100 MB. This script (as of 21Oct2026) does not chunk files of larger sizes. If there is somehow demand, I can implement it (or you can).

Upload the file to your Google Cloud Storage bucket.

## Step 2: Make a signed URL

Reach downloads the file itself, so it needs a link that works **without a Google login**. That's a signed URL.

> ⚠️ **Don't use the "Authenticated URL"** shown on the file's page in the Cloud Console (it starts with `https://storage.cloud.google.com/`). Reach can't sign in, so it gets a Google sign-in page instead of your file, and the job fails with *"invalid file structure, every row must have the same number of columns."*

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and click the **`>_`** icon in the top-right toolbar to open **Cloud Shell**. This is effectively cmd but with predownloaded stuff you need (gcloud command library)
2. In the bucket, click your file and copy its **gsutil URI**. It looks like `gs://my-bucket/my_file.csv`.
3. Paste this into Cloud Shell, swapping in your gsutil URI and service account email:
   ```
   gcloud storage sign-url gs://my-bucket/my_file.csv --impersonate-service-account=SERVICE_ACCOUNT_EMAIL --duration=4h
   ```
  - Replace gs://**my-bucket/my_file.csv** is replaced with whatever .csv you are trying to import
  - Replace --impersonate-service-account=**SERVICE_ACCOUNT_EMAIL** is replaced with your google cloud storage service account email, THIS IS NOT YOUR NORMAL LOGIN EMAIL.
4. Copy the link it prints. It starts with `https://storage.googleapis.com/` and contains `X-Goog-Signature=`. (It will likely be very long and filled with hexadecimal)
5. **Test it:** paste the link into a **private/incognito** browser window. If your list of IDs downloads or shows up, the link is good. If you see a sign-in page or an error, don't use it.

The link stops working after 4 hours. If it expires before you use it, make a new one. You can increase the duration or lower it as needed, but 4 hours is for the buffer in Reach's queue.

## Step 3: Run `dwidApi.py`

```
python dwidApi.py
```

It asks for:

| Prompt | What to enter |
|---|---|
| Tag ID | The Tag ID from Reach |
| Signed URL | The link from Step 2 |
| Person ID Type | The type of ID in your file, typed exactly as one of: `Reach ID`, `State File ID`, `Voterfile VAN ID`, `DWID`, `Voterbase ID`, `DNC Person ID` |
| Action | `add` to apply the tag, `remove` to take it off |
| State | Leave blank unless the campaign covers several states **and** the ID type can repeat across states (like State File ID) |

It then shows everything back to you. **Check it carefully** before typing `y`, because a mistake means waiting in Reach's queue again (which can be minutes or multiple hours). After that it asks for your **Reach API username and password**. 

**The password won't show while you type / copy & paste; that's normal and for security purposes**

When it prints **`Submitted successfully`** and a **Job ID**, copy the Job ID somewhere safe. You need it to check on the job.

It checks the job once after 60 seconds. It will often still say `pending` or `scheduled` then, which just means the job is waiting in line. It can take minutes or hours to reach the front of the queue. Big jobs can take over an hour or longer to run.

Press **Ctrl+C** to cancel at any time *before* confirming. After `Submitted successfully`, the job is already with Reach even if you cancel.

## Step 4: Check on it with `dwidCheck.py` (Optional)

```
python dwidCheck.py
```

Enter the Job ID from Step 3, then your Reach API username and password. You'll get something like:

```
Status: completed
tagged: 4980
failed: 20
total: 5000
```

| Status | Meaning |
|---|---|
| `pending` / `scheduled` | Waiting in Reach's queue; check again later |
| `in_progress` / `retrying` | Running now |
| `completed` | Done. `tagged` + `failed` = `total` |
| `failed` | The whole job failed; the reason is printed underneath |
| `cancelled` | The job was cancelled |

If any rows failed, it prints an **`Error details:`** link to a CSV listing each failed ID and why. The link only works for **30 minutes**; run `dwidCheck.py` again for a fresh one. Open the CSV in **Notepad**, not Excel, so Excel doesn't reformat the IDs.

Common reasons a row fails:

- `PERSON_NOT_FOUND`: the ID doesn't match anyone in your campaign.
- `TAG_ALREADY_APPLIED` / `TAG_ALREADY_REMOVED`: nothing needed doing. These count as successes, not failures.

---

## Troubleshooting

| What you see | What it means |
|---|---|
| `invalid file structure, every row must have the same number of columns`, and `total` is far below the size of your file | Reach got a web page instead of your file. You probably used the Authenticated URL; go back to Step 2. |
| The same message, with a sensible `total` | Some lines in the file have commas in them. Check for IDs written like `1,234,567`, or extra columns on some rows. |
| `Login failed` | Wrong Reach API username or password. Remember these are the API credentials from Reach support. |
| `Submit failed (404)` | The Tag ID doesn't exist, or the tag wasn't created by hand. |
| `Submit failed (403)` | Your API account doesn't have permission to import tags. Ask Reach support. |
| `Submit failed (422)` | Something you typed was rejected. The lines below it say which field. |
| Every row fails with `PERSON_NOT_FOUND` | Wrong Person ID Type for the file, or that ID type isn't turned on for your campaign. |
| The terminal shows `>>>` | You're inside Python, not cmd. Type `exit()` and press Enter. |
| `ModuleNotFoundError: No module named 'requests'` | Run `python -m pip install requests` in cmd. |

---

## Keeping it safe

- **Anyone with the signed URL can download your file until it expires.** Don't post it in chats, emails or docs. Make a new one each time.
- **Never make the bucket or file public.** These are voter IDs.
- **Never type the Reach API password into the scripts themselves.** They ask for it every run on purpose.
