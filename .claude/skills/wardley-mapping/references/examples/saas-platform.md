# SaaS Platform — Worked Example

## Strategic Question

A B2B SaaS startup is building a project management tool. Where should it build vs. buy, and what components deserve engineering focus?

## OWM Map

```
title B2B SaaS Project Management Platform
anchor Business Customer [0.95, 0.50]
component Project Management App [0.85, 0.52]
component Workflow Engine [0.65, 0.35]
component User Auth [0.55, 0.75]
component Notifications [0.50, 0.72]
component Data Storage [0.30, 0.80]
component Search [0.40, 0.62]
component Analytics & Reporting [0.60, 0.48]
component AI Suggestions [0.58, 0.18]
component Cloud Infrastructure [0.10, 0.85]
component Email Delivery [0.15, 0.88]

Business Customer->Project Management App
Project Management App->Workflow Engine
Project Management App->User Auth
Project Management App->Notifications
Project Management App->Analytics & Reporting
Project Management App->Search
Project Management App->AI Suggestions
Workflow Engine->Data Storage
Analytics & Reporting->Data Storage
Search->Data Storage
Data Storage->Cloud Infrastructure
Notifications->Email Delivery
Notifications->Cloud Infrastructure

evolve AI Suggestions 0.40
```

## Evolution Rationale

| Component | Stage | Score | Evidence | Strategic Implication |
|---|---|---|---|---|
| Business Customer | Anchor | 0.50 | User anchor | Root of all value chain |
| Project Management App | Product | 0.52 | Many competitors (Asana, Monday, Linear); differentiation on UX/workflow | This is the differentiation zone — build and own |
| Workflow Engine | Custom Built | 0.35 | Custom rule engines are bespoke; few off-the-shelf options match complex B2B workflow needs | Build if workflows are the product's core IP; evaluate no-code engines first |
| User Auth | Commodity | 0.75 | Auth0, Clerk, Supabase Auth all compete on price; MFA/SSO are table stakes | Buy immediately — Auth0 or equivalent. Never build. |
| Notifications | Commodity | 0.72 | Push, email, in-app notifications are a solved problem; multiple vendor options | Buy (e.g., Knock, Novu, or direct provider SDKs) |
| Data Storage | Commodity | 0.80 | Postgres, MySQL, managed cloud databases are utility-grade | Buy managed (RDS, Supabase, PlanetScale) |
| Search | Product | 0.62 | Algolia, Typesense, OpenSearch compete on features; not commodity but not custom | Buy a search-as-a-service; avoid building Lucene wrappers |
| Analytics & Reporting | Product | 0.48 | Mixpanel, Amplitude, custom dashboards all compete; still differentiating | Evaluate buy vs. embed (e.g., Metabase, Cube.js) based on report complexity |
| AI Suggestions | Genesis | 0.18 | LLM-powered task suggestions are novel in PM tools; few established patterns | Explore carefully; this is a pioneer activity. Expect failure and learning. `evolve 0.40` as patterns emerge |
| Cloud Infrastructure | Commodity | 0.85 | AWS/GCP/Azure are utility; serverless abstracts further | Fully outsource; never own hardware |
| Email Delivery | Commodity | 0.88 | SendGrid, Postmark, SES compete on deliverability price | Buy; this is invisible infrastructure |

## Strategic Commentary

1. **Buy everything below Product-stage.** Auth, Notifications, Data Storage, Cloud Infrastructure, and Email Delivery are all commodity or near-commodity. Building any of these is a trap that consumes engineering capacity with zero differentiation value.

2. **AI Suggestions is the only Genesis component — treat it like R&D, not a feature.** It's at 0.18, meaning patterns are undefined and failure is expected. Assign a small pioneer team; don't put it on the critical path. The `evolve 0.40` marker signals it will move to Custom Built as patterns emerge across the industry.

3. **Workflow Engine carries inertia risk.** If the startup builds a custom workflow engine now (reasonable at 0.35), it will resist replacement as the market matures. Design for replaceability — abstraction layer between the app and the engine.

4. **Co-evolution gap to watch:** Analytics & Reporting (Product, 0.48) is served by practices still at an emerging stage in most startups. As the product matures, data modeling discipline (a Practice component) must evolve in parallel or reporting quality will lag.

5. **The differentiation zone is narrow.** Only the Project Management App itself and the Workflow Engine are genuinely worth building. Everything else should route to a vendor decision. Focus engineering on what makes the product's workflow model unique, not on solving solved problems.
