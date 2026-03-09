# Agent Suite - Project Definition

## Vision
API-first infrastructure suite (email, calendar, docs) that AI agents can provision programmatically without human OAuth flows or browser sessions.

## Core Problem
Agents can write code, deploy services, orchestrate workflows — but cannot create an email account, provision a calendar, or authenticate with APIs without humans clicking through consent screens.

## Target Users
- AI agents running autonomously
- Developers building agent systems
- Multi-agent coordination platforms

## Differentiation
| Feature | Gmail/Google | AgentMail | Agent Suite (us) |
|---------|--------------|-----------|------------------|
| Auth | OAuth + human consent | API key | API key |
| Provisioning | Human creates account | Unknown - investigating | `POST /inboxes` → instant |
| Calendar | Separate API | Email only | Unified API |
| Docs | Separate API | No | Unified API |
| Self-hosted | No | No | Yes (option) |

## Constraints
- Must work without human browser sessions
- Must be API-key only authentication
- Must be provisioned programmatically
- Must handle cross-service references (email mentions calendar event)

## Tech Stack (Tentative)
- Backend: FastAPI (Python) - TBD by research
- Database: PostgreSQL
- Email: Self-hosted (Postfix/Dovecot) or AWS SES
- Calendar: CalDAV server (Radicale) or custom
- Docs: Yjs + WebSocket
- Auth: Simple API keys

## Success Metrics
- Time to first email: < 5 seconds (vs 2+ hours for Gmail OAuth)
- Time to first calendar: < 5 seconds
- Zero human clicks required for provisioning
