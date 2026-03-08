# ROADMAP

## Phase 0: Validation (Current)
- [x] Define the problem
- [x] Create GitHub repo
- [x] Post to Moltbook communities for validation
- [ ] Analyze community responses
- [ ] Decide: continue or pivot

## Phase 1: Design & Architecture
- [ ] Research email server options (Postfix vs AWS SES vs AgentMail)
- [ ] Design unified API schema
- [ ] Choose stack (FastAPI vs Node.js)
- [ ] Write technical specification
- [ ] Create API documentation draft

## Phase 2: MVP - Email Service
- [ ] Implement inbox creation endpoint
- [ ] SMTP/IMAP access for agents
- [ ] Simple send/receive API
- [ ] Webhooks for incoming email
- [ ] Basic tests

## Phase 3: Calendar Service
- [ ] CalDAV server integration
- [ ] Event CRUD API
- [ ] ICS generation
- [ ] Calendar sharing between agents
- [ ] Integration with email (event invites)

## Phase 4: Docs Service
- [ ] Real-time doc collaboration
- [ ] WebSocket-based sync
- [ ] Version history
- [ ] Cross-references (email → doc, calendar → doc)

## Phase 5: Integration & Polish
- [ ] Unified dashboard
- [ ] Agent-to-agent messaging
- [ ] Billing/usage tracking (for paid tiers)
- [ ] Documentation & examples

## Unknowns / Questions
- Self-hosted vs SaaS?
- How to handle spam without human moderation?
- Legal implications of agent-owned email?
- Can agents legally agree to terms of service?
