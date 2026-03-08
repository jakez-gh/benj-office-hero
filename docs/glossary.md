# Office Hero — Glossary

Industry-standard terms borrowed from PestPac, ServiceTitan, and Jobber where possible.
All AI and human contributors should use these terms consistently across all documents,
code, and communication.

---

## Platform & Tenancy

| Term | Definition |
| ---- | ---------- |
| **Office Hero** | The SaaS platform described in this repository |
| **Operator** | Jake + any internal staff who run and administer the Office Hero platform. Operators can see all Tenant data and platform configuration. Operators are never visible to Tenants. |
| **OperatorStaff** | An Operator team member with full platform access except billing and Operator user management |
| **Tenant** | A service company subscribed to Office Hero (a plumbing, HVAC, or pest control business). Each Tenant's data is strictly isolated from all other Tenants. In the UI this may be labelled "Company." |
| **TenantAdmin** | The owner or office manager at a Tenant. Has full CRUD access within their Tenant's data. |

---

## Field Service

| Term | Definition |
| ---- | ---------- |
| **Technician** | A field worker employed by a Tenant who travels to and performs Jobs. Primary mobile app user. (Universal FSM term) |
| **TechnicianHelper** | A second Technician riding in the same Vehicle; can view their Route but has read-only access to Jobs |
| **Dispatcher** | A Tenant employee who assigns and routes Jobs on behalf of TenantAdmin. May be the same person as TenantAdmin in small companies. |
| **Customer** | The end customer of a Tenant — the homeowner or business receiving the service. Customers never interact with Office Hero directly. (ServiceTitan/Jobber standard) |
| **Location** | A service address associated with a Customer. A single Customer may have multiple Locations (e.g. multiple properties). (ServiceTitan standard) |
| **Job** | A discrete service visit to be performed for a Customer at a Location. The core operational record in Office Hero. (ServiceTitan/Jobber/Housecall Pro standard; PestPac calls this a "Service Order") |
| **Contract** | A recurring service agreement between a Tenant and a Customer that automatically generates Jobs on a defined schedule (e.g. quarterly pest control). (PestPac standard) |
| **Vehicle** | The truck or van used by Technician(s) to travel to Jobs. Routes are assigned to Vehicles. |
| **VehicleCrew** | The set of Technicians assigned to a specific Vehicle for a given day. Includes one driver and zero or more helpers. A Technician may be on different Vehicles on different days. |
| **Route** | The ordered sequence of Jobs (RouteStops) assigned to one Vehicle for a day. (Universal FSM term) |
| **RouteStop** | A single Job within a Route, including its sequence position and estimated arrival time (ETA) |
| **Dispatch** | The act of assigning a Job to a Vehicle's Route, generating a RouteStop. (Universal FSM term) |

---

## Technical

| Term | Definition |
| ---- | ---------- |
| **BackOfficeAdapter** | A protocol (abstract interface) that defines how Office Hero reads and writes data to/from an external back-office system. The default adapter uses Office Hero itself as the system of record. |
| **NativeAdapter** | The default BackOfficeAdapter implementation — Office Hero is the system of record |
| **RBAC** | Role-Based Access Control — every API endpoint declares the minimum role required; middleware enforces this on every request |
| **RLS** | Row-Level Security — a PostgreSQL feature that automatically filters rows based on the current session's tenant context, enforced at the database layer |
| **Repository** | A class that encapsulates all database access for one entity type. Services depend on Repository protocols (ABCs), never on concrete implementations, enabling fast TDD via mocking. |
| **ADR** | Architecture Decision Record — a short document capturing a significant architectural choice, its context, and consequences. Lives in `project-documents/user/architecture/`. |
| **Slice** | A vertical cut through the architecture delivering independent, demonstrable value (UI + logic + data + tests). The unit of work in Erik's methodology. |
| **ORS** | OpenRouteService — the open-source routing engine used to generate route options |
| **MCP** | Model Context Protocol — the protocol used by the Office Hero MCP server to expose API capabilities to AI assistants |
| **FSM** | Field Service Management — the software category Office Hero belongs to |
| **SLO** | Service Level Objective — a target for system reliability (e.g. 99.5% uptime) |

---

## Industry-Specific

| Term | Definition |
| ---- | ---------- |
| **Service Type** | The category of work being performed (e.g. Drain Cleaning, AC Tune-Up, Quarterly Pest Treatment) |
| **custom\_fields** | A JSONB column on the Job record holding industry-specific data (e.g. permit number for plumbing, chemical product used for pest control, equipment model for HVAC) |
| **Scheduling window** | The time range within which a Job is expected to be performed (e.g. "Tuesday 8 AM – 12 PM") |
