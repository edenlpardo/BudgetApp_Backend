# BudgetApp_Backend  
Budgeting App Backend  

This is the backend of a full-featured budgeting web application designed to help users track income, expenses, and financial habits using structured budgeting methodologies. It supports personalized budgets based on Pay-Yourself-First and 50/30/20 frameworks, delivering real-time feedback and financial recommendations.  

Technologies and Tools:  
Language & Framework: Python, Flask (RESTful API)
Database: PostgreSQL (via Flask-SQLAlchemy)
Authentication: Bcrypt for password hashing and secure login
Deployment: Render
Testing: Postman (for API validation)
Version Control: Git, GitHub (as seen in original repo)

Features:  
User registration and login with hashed password security  
Budget creation based on two financial frameworks:  
--Pay-Yourself-First (PYF)  
--50/30/20 Rule  
Real-time budget allocation, validation, and overspending detection  
Personalized financial recommendations  
Support for:  
--Recurring and one-time incomes/expenses  
--Normalization of financial entries across time periods  
--Purchase tracking (not exposed in frontend)  
Modular codebase with Flask Blueprints for:  
--User management  
--Budget logic  
--Category and purchase tracking  

API Testing:  
All API endpoints were tested using Postman to verify:  
--Input validation  
--JSON response structures  
--Database state changes  
--Auth-protected route access  

Deployment:  
The backend was deployed on Render, providing a stable and scalable environment to serve API endpoints for frontend integration.
