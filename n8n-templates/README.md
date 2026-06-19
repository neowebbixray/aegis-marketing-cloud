# Aegis Marketing Cloud — n8n Workflow Templates

This directory contains starter **n8n workflow templates** for integrating with the **Aegis Marketing Cloud API**. Each template automates a common marketing or CRM workflow and can be imported directly into your n8n instance.

---

## Prerequisites

- [n8n](https://n8n.io/) instance running (default: `http://localhost:5678`)
- Aegis Marketing Cloud backend running (default: `http://localhost:8000`)
- An Aegis API key and workspace ID

---

## Environment Variables

Before importing any template, configure the following environment variables in n8n (Settings → Environment Variables or `.env` file):

| Variable | Description | Default |
|---|---|---|
| `AEGIS_API_URL` | Aegis backend base URL | `http://localhost:8000` |
| `AEGIS_API_KEY` | API bearer token for Aegis auth | *(required)* |
| `AEGIS_WORKSPACE_ID` | Default workspace UUID | *(required)* |
| `SLACK_REPORT_CHANNEL` | Slack channel for campaign reports | `#marketing-reports` |
| `SLACK_WEBHOOK_URL` | Slack webhook for support notifications | *(optional)* |
| `GOOGLE_SHEET_ID` | Google Sheet ID for contact sync | *(optional)* |
| `LEAD_SCORE_THRESHOLD` | Minimum score to update deal stage | `50` |
| `AEGIS_STAGE_HOT` | Pipeline stage UUID for hot leads | *(required for lead scoring)* |
| `AEGIS_STAGE_WARM` | Pipeline stage UUID for warm leads | *(required for lead scoring)* |
| `AEGIS_STAGE_COLD` | Pipeline stage UUID for cold leads | *(required for lead scoring)* |
| `AEGIS_WEEKLY_REPORT_ID` | Report ID for archiving campaign reports | *(optional)* |

---

## Templates Overview

### 1. `contact-sync.json` — Sync Aegis Contacts to Google Sheets / Mailchimp

**Trigger:** Webhook (POST to `/webhook/aegis-contact-sync`)

**Flow:**
1. Receive a webhook payload with a `contact_id`
2. Look up the contact in the Aegis CRM API (`GET /api/v1/crm/contacts/{id}`)
3. Append the contact data to a Google Sheet
4. Create/update the contact in Mailchimp (via Mautic node — swap for native Mailchimp node if preferred)
5. Log a `contact_synced` activity in Aegis

**Use case:** Connect a lead-capture form or Aegis event webhook to automatically sync new contacts to your external spreadsheet and email marketing platform.

### 2. `lead-scoring.json` — Score Leads & Update Deal Stages

**Trigger:** Cron — every Monday at 9:00 AM (`0 9 * * 1`)

**Flow:**
1. Fetch recent email campaigns from Aegis (`GET /api/v1/email/campaigns`)
2. Fetch email delivery records (`GET /api/v1/email/deliveries`)
3. Calculate lead scores via a Code node:
   - **+10** per email opened
   - **+15** per click
   - **+20** bonus for engagement within 7 days
   - Categories: **hot** (≥80), **warm** (≥50), **cold** (<50)
4. Fetch open deals from Aegis (`GET /api/v1/crm/deals`)
5. Update deal stages via (`PATCH /api/v1/crm/deals/{id}/stage`)

**Use case:** Automatically grade leads by email engagement and move deals to the appropriate pipeline stage.

### 3. `campaign-report.json` — Weekly Campaign Report → Slack

**Trigger:** Cron — every Monday at 10:00 AM (`0 10 * * 1`)

**Flow:**
1. Fetch email campaigns from Aegis (`GET /api/v1/email/campaigns?limit=50`)
2. Fetch detailed analytics for each campaign (`GET /api/v1/analytics/campaigns/{id}`)
3. Build a rich markdown summary with per-campaign metrics and overall stats
4. Post the report to Slack (via Slack node) with emoji formatting
5. Archive the report in Aegis analytics (`POST /api/v1/analytics/reports/generate`)

**Use case:** Get a weekly digest of email campaign performance delivered to your team's Slack channel automatically.

### 4. `support-ticket.json` — Create Aegis Contact from Support Email

**Trigger:** IMAP Email — polls the configured mailbox for new messages

**Flow:**
1. Watch a support mailbox via IMAP for new/unseen messages
2. Filter by subject keywords (`urgent`, `high priority`, `support`, `issue`) and priority headers
3. Extract sender name, email, phone number, and message body
4. Create a new contact in Aegis CRM (`POST /api/v1/crm/contacts`)
5. Log a `support_ticket` activity on the contact (`POST /api/v1/crm/activities`)
6. Send a Slack notification to alert the team

**Use case:** Automatically create Aegis CRM contacts from high-priority support ticket emails, ensuring no urgent inquiry goes unlogged.

### 5. `social-scheduler.json` — Publish Aegis Social Content Drafts

**Trigger:** Cron — daily at 8:00 AM, 12:00 PM, and 4:00 PM (`0 8,12,16 * * *`)

**Flow:**
1. Fetch scheduled social posts from Aegis (`GET /api/v1/social/posts?status=scheduled`)
2. Filter posts due for publication within the next 60 minutes
3. If posts are due, publish each one via (`POST /api/v1/social/posts/{id}/publish`)
4. Update the post status to `published` (`PATCH /api/v1/social/posts/{id}`)

**Use case:** Schedule your social media content in Aegis's content calendar and let this workflow auto-publish at the right times.

---

## How to Import

1. Open your n8n instance in a browser.
2. Go to **Workflows** → **Add Workflow** → **Import from File**.
3. Select one of the `.json` files from this directory.
4. After import:
   - Configure **credentials** for HTTP Request nodes (Header Auth) with your `AEGIS_API_KEY`.
   - Set up **Slack**, **Google Sheets**, **IMAP**, and **Mailchimp/Mautic** credentials as needed.
   - Adjust **environment variable** values in n8n Settings → Environment Variables.
   - Toggle the workflow to **Active** to start listening.

---

## Aegis API Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/crm/contacts` | GET, POST | Look up or create contacts |
| `/api/v1/crm/contacts/{id}` | GET | Fetch a single contact |
| `/api/v1/crm/deals` | GET | List deals |
| `/api/v1/crm/deals/{id}/stage` | PATCH | Change deal pipeline stage |
| `/api/v1/crm/activities` | POST | Log CRM activities |
| `/api/v1/email/campaigns` | GET | List email campaigns |
| `/api/v1/email/deliveries` | GET | List email delivery records |
| `/api/v1/analytics/campaigns` | GET | List campaign analytics |
| `/api/v1/analytics/campaigns/{id}` | GET | Get detailed campaign analytics |
| `/api/v1/analytics/reports/generate` | POST | Trigger report generation |
| `/api/v1/social/posts` | GET | List social posts |
| `/api/v1/social/posts/{id}/publish` | POST | Publish a social post |

All endpoints are prefixed with `{{ AEGIS_API_URL }}`. See the Aegis API documentation for full request/response schemas.

---

## Customizing the Templates

- **Swap platforms:** The `contact-sync.json` template uses a Mautic node for Mailchimp. Replace it with the native `n8n-nodes-base.mailchimp` node if needed.
- **Add more scoring rules:** Edit the Code node in `lead-scoring.json` to include web analytics, form submissions, or custom event tracking.
- **Change schedules:** Adjust the `cronExpression` in each `scheduleTrigger` node to match your business cadence.

---

## Troubleshooting

- **No data returned from Aegis API:** Verify `AEGIS_API_URL`, `AEGIS_API_KEY`, and `AEGIS_WORKSPACE_ID` are set correctly.
- **Webhook not firing:** Ensure the workflow is **Active**. Check that your external system can reach the n8n webhook URL (default `http://localhost:5678/webhook/aegis-contact-sync`).
- **IMAP connection failing:** Verify your email credentials use an app-specific password if 2FA is enabled.
- **Slack messages not sending:** Confirm the Slack credential is authorized and `SLACK_REPORT_CHANNEL` is a public channel or the bot has been invited.
