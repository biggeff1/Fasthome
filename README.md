# Fasthome

Fasthome is a real-estate agency platform focused on verified users, verified properties, matching, managed visits, dual contracts, common inspection reports, offline payment recording, landlord payouts, and end-to-end rental tracking.

## Core product rules

- One user account can search, rent, and publish properties.
- Account creation and identity certification are separate steps.
- Certification supports passport, voter card, or driving licence plus facial verification.
- The verified face capture becomes the profile photo.
- Publishing requires a connected, certified account.
- Property creation is dynamic and saved as drafts.
- Exact property address, GPS coordinates, Google Maps link, and rent amount are private.
- Matching uses only: furnished status, province, city/territory, administrative subdivision, neighborhood, minimum living rooms, minimum bedrooms, maximum budget, and maximum occupants.
- Matching displays available/validated properties from 60% to 100% compatibility.
- A visit request requires Fasthome approval and landlord approval without exposing the requester's identity to the landlord at that stage.
- After the agent marks the visit as completed, the requester can accept or decline the property.
- A concluded rental creates two contracts: Fasthome↔tenant and Fasthome↔landlord.
- The property inspection report (PV) is one shared record for both sides.
- Payments are never made online through Fasthome. Agents/admins record offline payments received from tenants and separately record payouts to landlords.
- An active rental removes the property from public availability until the rental is closed and the property is released by Fasthome.

## Stack

- Django
- PostgreSQL-ready configuration
- Server-rendered templates with a responsive mobile-first UI

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
