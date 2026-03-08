# 001‑concept.newproject

**Project name:** Office Hero

## Vision

This will be a tool used by Plumbers, Pest Control and HVAC professionals to:

- add new contracts to their back office systems.
- automatically route truck for new contracts or adapting to real-world events like sick-days or emergencies.
- manually adjust truck routes.

## Goals & Success Metrics

- Connection with customer backend systems, starting with the easiest and most common
- follow SOLID and DRY
- religious following of TDD and other quality control techniques
- Automatially route trucks for new contracts

## Initial Requirements

- determine what fields we require from contracts and a common vocabulary we would use to describe them and as an option we will first store the information in our backend system but later we will connect to the customer's current system to integrate seamlessly
- Allow a customer to enter a new contract into our backend system

## Notes / Risks

- We need to be careful to not allow our customers to see each others information or my information for managing the full system.  Customers should only be able to see their own data
- Quality and security need to be addressed before anything else.
