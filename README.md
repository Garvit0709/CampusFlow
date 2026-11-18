# CampusFlow v1.0

### Smart Campus Navigation System for UPES Bidholi

CampusFlow is a full-stack web application developed to help students and visitors explore the UPES Bidholi campus, locate buildings, and calculate estimated pedestrian routes.

The project combines interactive mapping, graph algorithms, PostgreSQL, REST APIs, and role-based authentication to provide a campus-specific navigation experience.

**Developed by:** Garvit Maheshwari (GM)

**Live Website:** https://garvit0709.github.io/CampusFlow/

**Backend API:** https://campusflow-backend-eyl4.onrender.com/docs

**GitHub Repository:** https://github.com/Garvit0709/CampusFlow

---

## Features

### Interactive Bidholi Campus Map
- Public campus map without mandatory login.
- 30 mapped campus locations.
- Building search and category filtering.
- Interactive markers and location information.
- OpenStreetMap and satellite map layers.
- Responsive layout and mobile navigation controls.

### Pedestrian Navigation
- Dijkstra-based shortest-path calculation.
- Shortest-distance and stair-free route comparison.
- Pedestrian graph containing 30 buildings and 10 junctions.
- 59 mapped pedestrian connections.
- Estimated route distances and walking directions.
- Read-only junction coordinates retrieved from the backend API.

### Authentication and Administration
- Optional student authentication.
- JWT-based authentication.
- Argon2 password hashing.
- Role-based authorization.
- Protected administrative dashboard and analytics endpoints.
- Public navigation remains accessible without login.

### Additional Research and Development
Earlier development phases included congestion-aware routing, crowd reporting, and a Random Forest-based crowd prediction model trained on synthetic data.

These experimental capabilities are retained in the broader codebase but are not the primary focus of the public Bidholi v1.0 interface.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript, Vite, CSS |
| Mapping | React Leaflet, Leaflet, OpenStreetMap |
| Backend | Python, FastAPI, REST APIs |
| Database | PostgreSQL, Neon |
| Routing | Graph algorithms, Dijkstra's algorithm |
| Authentication | JWT, Argon2, role-based authorization |
| Experimental ML | Scikit-learn, Pandas, NumPy, Random Forest |
| Frontend Hosting | GitHub Pages |
| Backend Hosting | Render |
| Deployment | GitHub Actions |

---

## System Architecture

```text
                   CampusFlow
                       |
                React + Vite
                       |
                Leaflet Campus Map
                       |
                 FastAPI REST API
                       |
          +------------+------------+
          |                         |
    PostgreSQL / Neon        Routing Engine
          |                         |
    Campus Locations         Dijkstra Algorithm
    Pedestrian Graph         Route Comparison
    Authentication Data      Walking Directions
```

The frontend is deployed using GitHub Pages, while the FastAPI backend is hosted on Render and connects to PostgreSQL.

---

## Pedestrian Graph

The Bidholi navigation system currently contains:

| Component | Count |
|---|---:|
| Campus buildings and locations | 30 |
| Pedestrian junctions | 10 |
| Total graph nodes | 40 |
| Pedestrian edges | 59 |
| Ordered building pairs | 870 |
| Route test cases | 1,740 |

The routing engine supports shortest-distance and stair-free route calculations.

Route distances are estimates. The mapped pedestrian geometry has not been fully verified against actual campus walkways.

---

## Testing and Validation

### Routing Tests

The automated routing test suite evaluated 1,740 route cases.

| Metric | Result |
|---|---:|
| Total tests | 1,740 |
| Passed | 1,740 |
| Failed | 0 |
| Pass rate | 100% |

### Database Connectivity

The PostgreSQL connection pool successfully completed 30 test queries.

### Frontend Validation

The following functionality was manually tested:

- Public map access without login.
- Building markers and search.
- Shortest and stair-free routing.
- Walking directions.
- Optional authentication.
- Protected admin access.
- Logout to public map.
- Removal of the demo campus and Junction Editor from the active interface.

### Lighthouse Audit

| Category | Score |
|---|---:|
| Performance | 44 |
| Accessibility | 100 |
| Best Practices | 96 |
| SEO | 91 |

The Lighthouse audit was conducted against a local development build. Performance optimization is deferred to a future release.

---

## Local Development

### Prerequisites

- Python 3.12 recommended for consistency with the deployed backend.
- Node.js 22.
- PostgreSQL database access.
- Git.

### Backend Setup

```powershell
cd backend

py -3.12 -m venv venv

.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python -m uvicorn main:app --reload
```

Configure the database and JWT environment variables before starting the backend.

Use `backend/.env.example` as a configuration reference. Never commit real passwords or secrets.

### Frontend Setup

```powershell
cd frontend

npm install

npm run dev
```

The frontend uses `VITE_API_URL` to identify the FastAPI backend.

For the deployed application:

```text
VITE_API_URL=https://campusflow-backend-eyl4.onrender.com
```

When developing locally, ensure the backend permits the frontend origin through its CORS configuration.

---

## Deployment

**Frontend:** GitHub Pages

https://garvit0709.github.io/CampusFlow/

**Backend:** Render

https://campusflow-backend-eyl4.onrender.com

**Database:** Neon PostgreSQL

GitHub Actions builds the Vite application and publishes the production frontend after changes are merged into the `main` branch.

---

## Known Limitations

- Pedestrian distances are estimated.
- Some route geometries are not ground-verified.
- Stair-free routing excludes mapped staircase connections but does not guarantee full accessibility.
- Building photographs are deferred to a future version.
- Mobile performance optimization remains pending.
- The backend hosting service may experience cold-start delays.

---

## Future Improvements

- Building photograph galleries.
- Improved route geometry accuracy.
- On-campus GPS validation.
- Accessibility verification of pedestrian pathways.
- Frontend performance optimization.
- Expanded campus navigation coverage.

---

## Developer

**Garvit Maheshwari**

Full-Stack Developer | Software Development | Python | React | PostgreSQL

GitHub: https://github.com/Garvit0709

CampusFlow was designed and developed as an individual software development project.

© 2026 Garvit Maheshwari.

---

## Disclaimer

CampusFlow is an independently developed campus navigation project and is not an official UPES navigation service.

Location information and pedestrian routes are provided for educational and demonstration purposes. Users should verify actual walkway conditions and accessibility before relying on route recommendations.