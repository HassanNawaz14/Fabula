# Kaggle Generation

Fabula can generate a case on a free Kaggle GPU instead of the player's CPU. The game pushes a small private notebook, Kaggle runs the same generator that runs locally, and the finished, validated bundle is downloaded into the ready-case library. The player only needs to click **New Game → Generate on Kaggle** and wait about 6–8 minutes.

This route is meant for the case author (the person running Fabula today), not for every end user: the Kaggle account, the API token and the GPU quota all belong to that one account.

## What the user must do once

### 1. Create a Kaggle account and verify it

1. Sign in at <https://www.kaggle.com>.
2. Open **Settings → Phone Verification** and verify a phone number.
   Kaggle only enables **GPUs** and **internet access** for verified accounts, and the generation notebook needs both.
3. Accept the Kaggle competition rules if Kaggle shows that prompt (it appears on the first notebook run for some accounts).

### 2. Create the legacy API key (the `kaggle.json` file)

Kaggle's **Create New Token** button now issues a personal access token, which the classic Python client does not read. The file this game needs lives one section lower:

1. On <https://www.kaggle.com>, open **Settings → API**.
2. Scroll to **Legacy API Credentials**.
3. Click **Create Legacy API Key**. A file named `kaggle.json` downloads.
4. If a download does not appear, check the browser's download list or try another browser; the click always produces the file.

The file is three lines, and only two values matter:

```json
{
  "username": "your-kaggle-username",
  "key": "your-legacy-api-key"
}
```

If you cannot download the file at all, open the Legacy API Credentials section, copy the two values it shows alongside the button (username and key), and create the file by hand with the content above. Do not paste the value from an `access_token` file into `key`: personal tokens and legacy keys are different credentials.

5. Save the file as:
   - Windows: `C:\Users\<you>\.kaggle\kaggle.json`
   - macOS / Linux: `~/.kaggle/kaggle.json`

The parent `.kaggle` folder may already exist (it holds Kaggle's personal `access_token`); leave that file alone and add `kaggle.json` next to it.

Kaggle client 2.x checks `access_token` **before** the legacy key. If that token is stale, or was saved by Notepad as UTF-16 (which produces an `Invalid header value ... Bearer ...` error), login breaks even though `kaggle.json` is correct. Fabula therefore uses `kaggle.json` directly whenever it exists and ignores the personal token entirely.

If you want the personal token to work as well, save `~/.kaggle/access_token` as **UTF-8 without BOM**, one line, with no trailing blank lines.

`kaggle.json` contains the username and an API key. Treat it as a password: do not commit it, paste it into chat, or put it in the repository. The game reads it from that location; it never needs to be copied into the project.

PowerShell shortcut that opens the file for editing once it exists:

```powershell
notepad "$env:USERPROFILE\.kaggle\kaggle.json"
```

Alternative: set `KAGGLE_USERNAME` and `KAGGLE_KEY` environment variables instead of the file. They must contain the legacy username/key, not a personal token.

### 3. Install the Kaggle client

```powershell
python -m pip install -e ".[kaggle]"
```

The game raises a clear message if this step is missing.

### 4. Upload the model as a private dataset

The Kaggle notebook needs the fine-tuned GGUF file:

`models/Qwen2.5-3B-Instruct.Q4_K_M.gguf` (1.80 GiB)

1. On <https://www.kaggle.com>, open **Datasets → New Dataset**.
2. Drag the `.gguf` file (or the `models` folder) into the upload area.
3. Set the title to exactly **`fabula-qwen-3b-gguf`** so the slug matches the default.
4. Set visibility to **Private**.
5. Click **Create**.

The full dataset reference is `<your-username>/fabula-qwen-3b-gguf`, which is what the game uses by default. If the slug differs, set `FABULA_KAGGLE_MODEL_DATASET=<username>/<dataset-slug>`.

The notebook looks for the staged model by file name, taken from `models/model_manifest.json` (`Qwen2.5-3B-Instruct.Q4_K_M.gguf`) and verified against the manifest's SHA-256. If your dataset holds several GGUFs under different names, set `FABULA_KAGGLE_MODEL_FILENAME=<file name>`; a mismatch is reported before generation starts instead of after a long run.

The upload is a one-time cost. Later generations reuse the same dataset.

### 5. Check the connection

From the project folder:

```powershell
python -m fabula kaggle --count 1
```

A first run creates the private notebook `<username>/fabula-case-generator`, waits for it, downloads `case.zip`, validates the bundle and prints `ready: bundles\library\kaggle_<timestamp>`. The notebook is reused and updated on later runs.

## How the game uses it

1. **Start menu → New Game.**
2. Choose **Generate on Kaggle**. The screen shows live progress, the elapsed time and a cancel button.
3. The finished case is installed into `bundles/library/` and the game opens it immediately.
4. Later, the same case appears in **New Game → Play a Ready Case**.

What the notebook does on Kaggle:

1. Bare-clones the Fabula repository (default `main`) with a sparse checkout of `src/` and `models/model_manifest.json`; if sparse checkout is unavailable it falls back to a full clone.
2. Installs a CUDA build of `llama-cpp-python` and enables GPU offload (`FABULA_MODEL_GPU_LAYERS=-1`).
3. Selects the requested GGUF by file name and verifies its manifest SHA-256.
4. Runs the same staged generator as a local run, including the official `stage_validators` hook for cross-document checks; the notebook never patches the cloned source.
5. Packages the validated bundle as `case.zip` and prints `KAGGLE_DONE`.

The notebook is private, runs with GPU and internet enabled, and mounts only the model dataset. Nothing else from the account is exposed. The finished case is validated locally and installed atomically: a broken download or an invalid bundle leaves the existing ready-case library untouched.

## Generating the pre-made library (20–30 cases)

Use the batch command. It runs cases one after another, keeps the finished ones even if one fails, and prints a target path per case:

```powershell
python -m fabula kaggle --count 25
```

Options:

| Option | Values / default |
|---|---|
| `--count` | number of cases, default `1` |
| `--type` | `theft`, `disappearance`, `murder`, `random` (default) |
| `--tone` | `cozy` (default), `neutral`, `dark` |
| `--difficulty` | `easy`, `normal` (default), `hard` |
| `--seed` | first seed; later cases use `seed+1`, `seed+2`, … (default: random per case) |
| `--stop-on-error` | stop the batch on the first failure instead of continuing |

For a varied library, mix the three types and tones, for example three batches:

```powershell
python -m fabula kaggle --count 10 --type theft
python -m fabula kaggle --count 10 --type disappearance --tone neutral
python -m fabula kaggle --count 10 --type murder --tone dark --difficulty hard
```

Budget roughly 6–8 minutes per case plus queue time. Kaggle's free GPU quota is about 30 hours per week; 25–30 cases use a few hours of it. Stop a batch at any time with Ctrl+C — finished cases stay installed.

Cases land in `bundles/library/kaggle_<YYYYMMDD_HHMMSS>` and appear newest-first in the in-game picker.

## Configuration

| Variable | Purpose |
|---|---|
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | Credentials, if not using `~/.kaggle/kaggle.json` |
| `FABULA_KAGGLE_USERNAME` | Kernel owner, if it differs from the credentials username |
| `FABULA_KAGGLE_MODEL_DATASET` | Dataset reference, default `<username>/fabula-qwen-3b-gguf` |
| `FABULA_KAGGLE_MODEL_FILENAME` | File name to pick inside the dataset; default the manifest's staged model |
| `FABULA_KAGGLE_KERNEL_SLUG` | Notebook slug, default `fabula-case-generator` |
| `FABULA_KAGGLE_REPO_URL` | Repository cloned on Kaggle, default the project GitHub URL |
| `FABULA_KAGGLE_REPO_REF` | Branch or tag to clone, default `main` |
| `FABULA_KAGGLE_TIMEOUT` | Seconds before the client gives up waiting, default `2700` |
| `FABULA_KAGGLE_POLL` | Seconds between status checks, default `20`; transient status-API errors are retried with backoff before the run is abandoned |
| `FABULA_LIBRARY_DIR` | Where finished cases are stored, default `bundles/library` |

The notebook reads the repository, so a change to the generator must be pushed before Kaggle can use it. Until a change is merged to `main`, set `FABULA_KAGGLE_REPO_REF` to the branch that contains it.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Kaggle is not connected` | `kaggle.json` is missing or incomplete. Create a **legacy** key from **Settings → API → Legacy API Credentials**. |
| `The Kaggle client is not installed` | Run `python -m pip install -e ".[kaggle]"`. |
| `Kaggle login failed` | The key was revoked, belongs to a personal token instead of the legacy key, or the username is wrong. Recreate the legacy key. |
| `Kaggle login failed` with a valid legacy key | A stale `~/.kaggle/access_token` is aborting login before the legacy key is read. The game retries with the legacy key automatically; if it still fails, rename `access_token` and run again. |
| `Invalid header value b'Bearer ...'` | `~/.kaggle/access_token` is stored as UTF-16 (Notepad's "Unicode") and the SDK injects it into the header. Fabula ignores it while `kaggle.json` exists; to use the personal token too, re-save it as UTF-8 without BOM on one line. |
| `Kaggle refused the request` with 401 | The legacy JSON is malformed. It must contain exactly `username` and `key`, with no extra quotes around the values. |
| `Kaggle refused the request` | The model dataset reference is wrong or not visible to the account. Check the dataset slug and set `FABULA_KAGGLE_MODEL_DATASET`. |
| Notebook fails with `no .gguf model found` | The dataset does not contain the model file. Re-upload the GGUF. |
| Notebook fails with `requested model ... was not found` | The uploaded file name differs from the manifest default. Set `FABULA_KAGGLE_MODEL_FILENAME` to the name the error lists. |
| Notebook fails with `does not match models/model_manifest.json` | The uploaded GGUF is a different build or a corrupted upload. Re-upload the artifact whose hash is in the manifest, or update the manifest for an intentional new build. |
| Notebook fails with `no CUDA build ... could be installed` | Kaggle changed its CUDA images. Re-run; if it persists, the wheel index list in `kaggle_runner.py` needs a newer tag. |
| Status `error` with a quota message | The weekly GPU quota is spent, or the account is not phone-verified. |
| `Kaggle did not finish in time` | The queue was long or the run stalled. Open the notebook URL printed in the message, then raise `FABULA_KAGGLE_TIMEOUT`. |
| Validation fails after a download | The generated case was unusable. Re-run; one failed case does not block the rest of a batch. |
| Cancelling in-game stops progress but the notebook keeps running | The client stops waiting; the remote run may still finish and consume quota. Open the notebook URL to check or stop it. |

## Tests

The Kaggle route is covered offline with a fake API client:

```powershell
python -m pytest -q tests/test_generation_routes.py
```

No Kaggle account is needed for the test suite.
