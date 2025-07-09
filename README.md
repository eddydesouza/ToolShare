# ToolShare

**Empowering Local Communities Through Tool Sharing**

ToolShare is a peer-to-peer web application that connects individuals within local neighborhoods who want to **rent out or borrow tools**, from drills and saws to lawnmowers and ladders. This platform fosters a **sustainable sharing economy** by giving users the ability to **list, search, rent, and subscribe to tools** based on proximity using ZIP code-based filters. It’s designed to be simple, intuitive, and hyper-local—perfect for users with limited technical skills but a need for occasional tool access.

---
## 👥 Contributors

| Name            | Role           | Hours/Week | Responsibility             | Skillsets          |
|-----------------|----------------|------------|----------------------------|--------------------|
| Dustin Kelly    | Product Owner  | 25         | Prioritize Product Backlog | Project Management |
| Eddy De Souza   | Developer      | 40         | Backend                    | Python/Flask       |
| Kristen Hafford | Scrum Master   | 25         | Manage Backlog / Team      | Project Management |
| Marcus Greene   | Developer      | 20         | Backend (Database)         | DB/SQL             |
| Mykal Elliott   | QA             | 10         | Testing                    | Selenium           |

---

**ToolShare** — *Making tools accessible, one neighborhood at a time.*




## 🌟 Key Features

- 🔐 **User Registration** — Sign up with name, email, password, and ZIP code.
- 🛠️ **Tool Listings** — Owners can list tools with descriptions, availability, and rental pricing.
- 📍 **Local Search** — Renters browse listings filtered by ZIP code to find nearby options.
- 💳 **Rental Subscription** — Renters can subscribe to weekly/monthly plans and pay using Stripe Test Mode (e.g., card: `4242 4242 4242 4242`).
- 📄 **Profile Management** — Users can view past rentals and manage current subscriptions.
- 🧑‍💼 **Admin Dashboard** — Admins can approve listings, monitor activity, and handle disputes.
- 📱 **Responsive Design** — Works on both desktop and mobile devices.

---

## 🧱 Tech Stack

| Layer           | Technology                 |
|----------------|----------------------------|
| **Backend**     | Python with Flask           |
| **Database**    | MySQL                       |
| **Payments**    | Stripe (Test Mode)          |
| **Frontend**    | HTML/CSS                    |
| **Testing**     | Selenium + unittest         |
| **Hosting**     | Localhost or AWS EC2        |

---

## 📦 Project Structure

```bash
ToolShare/
├── app.py
├── templates/
│   ├── register.html
│   ├── success.html
├── tests/
│   ├── test_toolshare.py
├── requirements.txt
├── README.md
└── sql/
    └── init.sql
