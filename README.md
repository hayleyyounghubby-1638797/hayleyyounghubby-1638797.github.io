# The Algorithm — Daily AI Briefing Emailer

A daily AI news briefing delivered to your inbox every weekday at 7am ET. Powered by Claude (with web search) and Resend.

## What it does

Every weekday morning, a GitHub Actions workflow:
1. Calls the Anthropic API with web search enabled to find the latest AI news
2. Generates a personalized briefing in "reality TV meets Wall Street analyst" voice
3. Converts it to a beautiful HTML email
4. Sends it via Resend

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Get a Resend account and API key

1. Go to [resend.com](https://resend.com) and create a free account
2. Add and verify your sending domain (or use Resend's shared domain for testing)
3. Go to **API Keys** → **Create API Key**
4. Copy the key — you'll need it in step 4

> **From email:** Your `FROM_EMAIL` must use a domain you've verified with Resend (e.g. `briefing@yourdomain.com`). For quick testing, Resend lets you send from `onboarding@resend.dev` to your own address on the free plan.

### 3. Get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in
2. Navigate to **API Keys** → **Create Key**
3. Copy the key

> **Web search:** The script uses the `web_search_20250305` tool. Make sure your Anthropic account has access to this tool (available on paid plans).

### 4. Add secrets to GitHub Actions

In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add all four:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `RESEND_API_KEY` | Your Resend API key |
| `TO_EMAIL` | Your email address (where briefings land) |
| `FROM_EMAIL` | Your verified sending address (e.g. `briefing@yourdomain.com`) |

### 5. Enable GitHub Actions

Go to the **Actions** tab in your repo. If prompted, click **Enable GitHub Actions**.

The workflow file is already committed at `.github/workflows/daily-briefing.yml` and will run automatically on schedule once Actions is enabled.

### 6. Trigger a test run manually

1. Go to the **Actions** tab
2. Click **Daily AI Briefing** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch the run complete — check your inbox in ~60 seconds

### 7. Change the send time

Edit `.github/workflows/daily-briefing.yml` and update the cron expression:

```yaml
- cron: '0 12 * * 1-5'  # 7am ET = 12pm UTC, weekdays
```

Cron format: `minute hour day month weekday` (all in UTC).

Common times:
- 6am ET → `0 11 * * 1-5`
- 7am ET → `0 12 * * 1-5`
- 8am ET → `0 13 * * 1-5`
- Include weekends → `0 12 * * *`

> GitHub Actions schedules can run a few minutes late during peak times — this is normal.

---

## Local development

```bash
pip install -r requirements.txt
cp .env .env.local  # fill in your real keys
python briefing.py
```

---

## Project structure

```
briefing.py                          # main script
requirements.txt                     # dependencies
.env                                 # API keys (never commit real keys)
.github/workflows/daily-briefing.yml # GitHub Actions schedule
README.md                            # this file
```
