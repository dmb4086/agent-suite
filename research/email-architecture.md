# Research: Email Server Options

Date: 2026-03-09
Status: Phase 1.1 - Evaluating email architecture

## Option 1: Self-Hosted Postfix + Dovecot

**How it works:**
- Virtual mailboxes (no system users needed)
- MySQL/PostgreSQL backend for user management
- API can create mailboxes by inserting DB rows

**Pros:**
- Full control
- No per-email cost
- Can create mailboxes programmatically via SQL

**Cons:**
- Complex setup (DNS, SPF, DKIM, DMARC)
- Deliverability challenges (IP reputation)
- Maintenance burden

**Programmatic creation:**
```sql
INSERT INTO virtual_users (domain, email, password) 
VALUES ('agentsuite.com', 'agent123@agentsuite.com', hashed_pw);
```
Dovecot/Postfix pick it up automatically.

**Verdict:** Viable but complex. Need to solve DNS/deliverability.

---

## Option 2: AWS SES (Simple Email Service)

**How it works:**
- AWS-managed email sending
- SMTP/IMAP not native (SES is send-only)
- WorkMail adds inbox but requires console setup

**Pros:**
- High deliverability
- AWS handles IP reputation
- API for sending

**Cons:**
- No native inbox/IMAP (without WorkMail)
- WorkMail requires human console access
- More expensive at scale

**Programmatic creation:**
SES: Yes (CreateIdentity API)
WorkMail: No (requires AWS Console)

**Verdict:** Good for sending, not for receiving without WorkMail.

---

## Option 3: Hybrid Approach (Recommended)

**Architecture:**
```
Incoming:
  MX → Mailgun/Postmark (receive) → Webhook → Our API

Outgoing:
  Our API → AWS SES (send)

Storage:
  PostgreSQL (metadata) + S3 (raw emails)

IMAP:
  Custom lightweight server (reads from DB/S3)
```

**Pros:**
- Best deliverability (use established receivers)
- Programmatic everything
- Cost effective
- Scalable

**Cons:**
- More moving parts
- Need to build IMAP layer

**Verdict:** Best for agent-native infrastructure.

---

## Option 4: AgentMail-style (API-First)

**How it works:**
- AgentMail provides API-first email
- Unknown if fully programmatic setup

**Research needed:**
- Does AgentMail require human setup?
- Pricing model?
- Self-hosted option?

**Verdict:** Investigate further. Could save building time.

---

## Decision Matrix

| Criteria | Postfix/Dovecot | AWS SES | Hybrid | AgentMail |
|----------|----------------|---------|--------|-----------|
| Programmatic | ✅ Yes | ⚠️ Partial | ✅ Yes | ❓ Unknown |
| Deliverability | ⚠️ Hard | ✅ Good | ✅ Good | ✅ Good |
| Cost | ✅ Low | ⚠️ Medium | ✅ Medium | ❓ Unknown |
| Complexity | ❌ High | ⚠️ Medium | ⚠️ Medium | ✅ Low |
| Self-hosted | ✅ Yes | ❌ No | ⚠️ Partial | ❌ No |

## Recommendation

**Hybrid approach** for MVP:
1. Mailgun/Postmark for receiving (webhooks)
2. AWS SES for sending
3. PostgreSQL for metadata
4. Custom IMAP (lightweight, reads from DB)

This gives us:
- `POST /inboxes` → creates DB record
- `POST /send` → calls SES API
- `GET /inbox` → queries DB
- Webhooks → receive in real-time

Next: Research Mailgun/Postmark APIs for programmatic setup.
