Nexship – Order & Wallet Management Platform

Nexship is a backend-driven operations platform built with FastAPI that enables users to manage orders, payments, and wallet transactions efficiently.
The system integrates Razorpay payments, role-based dashboards, and a wallet ledger system for secure and scalable operations.

“Great products remove friction from everyday work. Nexship is built to do exactly that.”

Features

JWT Authentication (Signup / Login)

Role-Based Access Control (RBAC)

Cart & Order Management

Complete Order Lifecycle

Created → Pending Payment → Paid → Processing → Completed → Cancelled → Refunded

Wallet System with Transaction History

Razorpay Payment Gateway Integration

Webhook Verification for Secure Payments

Admin Dashboard

Password Reset via Email

Real-time Wallet Balance Updates

Tech Stack

Backend

FastAPI

Python

SQLAlchemy

JWT Authentication

Frontend

HTML

CSS

Vanilla JavaScript

Payments

Razorpay

Email

SMTP (Password Reset)

Deployment

Render

Architecture
Frontend (HTML / JS)
        ↓
FastAPI Backend
        ↓
Database (Users, Orders, Wallet)
        ↓
External Services
   ├ Razorpay (Payments)
   └ SMTP (Email)
Installation

Clone the repository:

git clone https://github.com/ibirender/My-First-Api
cd nexship

Install dependencies:

pip install -r requirements.txt

Run the server:

uvicorn app.main:app --reload

API documentation:

http://localhost:8000/docs


Author
Birender Singh
BTech – Data Science
Backend Developer (FastAPI / Python)
