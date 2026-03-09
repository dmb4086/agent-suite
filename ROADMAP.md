# ROADMAP

## Phase 0: Validation ✅
- [x] Define the problem
- [x] Create GitHub repo
- [x] Post to Moltbook communities for validation
- [x] Analyze community responses
- [x] Confirm: This is a real need

## Phase 1: Research & Architecture (Current)
- [ ] Research email server options
  - [ ] Postfix/Dovecot self-hosted complexity
  - [ ] AWS SES API capabilities
  - [ ] Mail-in-a-box, Mailcow automation
- [ ] Research calendar options
  - [ ] Radicale CalDAV
  - [ ] Custom calendar API
- [ ] Research docs collaboration
  - [ ] Yjs + WebSocket architecture
  - [ ] CRDT conflict resolution
- [ ] Unified API design
- [ ] Authentication system (API keys)
- [ ] Database schema
- [ ] Deployment strategy

## Phase 2: MVP - Email Service
- [ ] Inbox provisioning endpoint
- [ ] SMTP/IMAP access
- [ ] Send/receive API
- [ ] Webhooks for incoming email
- [ ] Basic tests

## Phase 3: Calendar Service
- [ ] CalDAV integration
- [ ] Event CRUD API
- [ ] ICS generation
- [ ] Calendar sharing

## Phase 4: Docs Service
- [ ] Real-time collaboration
- [ ] WebSocket sync
- [ ] Version history
- [ ] Cross-references

## Phase 5: Integration
- [ ] Unified dashboard
- [ ] Agent-to-agent messaging
- [ ] Documentation
- [ ] Examples

## Current Focus
**Phase 1.1:** Email server research - evaluating Postfix/Dovecot vs AWS SES vs hybrid approach
