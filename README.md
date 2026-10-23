
# CampusFlow

### Intelligent Campus Navigation & Crowd Prediction System

CampusFlow is a full-stack campus navigation platform that combines shortest-path algorithms, crowd reporting, machine learning, and analytics to help users explore a fictional demonstration campus.

## Features

- Interactive campus navigation using React and Leaflet
- Shortest-path routing using Dijkstra's algorithm
- Congestion-aware route recommendations
- Machine learning-based crowd prediction
- Student crowd reporting
- JWT authentication and role-based access control
- Administrator analytics dashboard
- PostgreSQL database integration

## Tech Stack

**Frontend:** React, Vite, JavaScript, Leaflet, Recharts, CSS

**Backend:** Python, FastAPI, REST APIs

**Database:** PostgreSQL

**Machine Learning:** Scikit-learn, Random Forest, Pandas, NumPy

**Security:** JWT, Argon2 password hashing, role-based authorization

## Architecture

React Frontend
    |
    v
FastAPI Backend
    |
    +-- PostgreSQL Database
    |
    +-- Dijkstra Routing Engine
    |
    +-- Random Forest Prediction Model

## Machine Learning

The Random Forest classifier was trained on 7,560 synthetic crowd observations across six fictional campus locations.

Evaluation on a chronologically held-out synthetic test set:

- Random Forest accuracy: 75.40%
- Majority-class baseline accuracy: 42.53%
- Training records: 6,048
- Testing records: 1,512

These metrics describe synthetic-data performance and do not establish real-world prediction accuracy.

## Routing Modes

1. Shortest Distance
2. Smart Routing using recent crowd reports
3. ML-Powered Smart Routing using predicted congestion

## Security

- Student registration and login
- Argon2 password hashing
- JWT-based authentication
- Protected administrator analytics APIs
- Role-based access control

This is a demonstration project. Additional security hardening is required before production deployment.

## Local Setup

### Backend

Create and activate a Python virtual environment inside `backend`, then run:

    python -m pip install -r requirements.txt
    python ml/generate_dataset.py
    python ml/train_model.py
    python -m uvicorn main:app --reload

Configure PostgreSQL and environment variables before starting the backend.

### Frontend

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173

## Project Status

Full-stack demonstration application under active development.

## Disclaimer

Campus locations and crowd training data are fictional or synthetic. Route estimates and crowd predictions are not validated against real campus conditions.
