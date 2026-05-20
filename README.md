# Stress-tester

A lightweight stress testing tool for backend APIs your app uses.

## iPad app scanning request (important limitation)

You **cannot** scan installed iPad apps from a web page (including GitHub Pages) or from this repo's CLI.
Apple/iOS sandboxing blocks websites and scripts from listing installed apps or attaching to app processes.

### What this tool can target

- API endpoints used by your iPad app (recommended)
- Web backends your app depends on

## GitHub Pages interface (iPad-friendly)

This repo includes `web_ui.html` for iPad Safari.
It lets you:
- Enter an app label + target URL
- Choose method
- Adjust **packets to send** (request count)
- Adjust concurrency/timeout
- Add header/body
- Download JSON results

### Setup steps

1. Push repo to GitHub
2. Enable **Settings → Pages** (branch: default, folder: root)
3. Open published `web_ui.html` URL on iPad Safari
4. Configure target endpoint and packet amount
5. Run test and download report

### CORS note

Browser requests require your API to allow CORS from your Pages domain.
If blocked, use GitHub Actions workflow for server-side stress testing.


## Jamf Trust targeting

This UI now includes a **Jamf Trust preset** in the target profile dropdown.

Because Jamf environments are tenant-specific, you must replace the preset URL with your real Jamf tenant/API endpoint (for example your org's `*.jamfcloud.com` endpoint) before running tests.

Suggested flow:
1. Select **Jamf Trust (preset)**
2. Confirm `App name` auto-fills to `Jamf Trust`
3. Replace URL with your real Jamf endpoint
4. Set packets/concurrency and run

## CLI usage

```bash
python stress_tester.py --url https://your-app.com/health --requests 500 --concurrency 50
```

```bash
python stress_tester.py \
  --url https://api.yourapp.com/login \
  --method POST \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer YOUR_TOKEN" \
  --body '{"email":"test@yourapp.com","password":"secret"}' \
  --requests 300 \
  --concurrency 30
```

Only stress test systems you own or are authorized to test.
