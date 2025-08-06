# pyf_budget_routes.py by Eden Pardo
#from flask import Blueprint, request, jsonify
from models import Purchase, BudgetExpense, Budget, Category
from extensions import db

def create_base_savings_category(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            raise ValueError("Budget not found")

        savings_category = Category(
            title="Savings",
            priority=1,
            budget_id=budget.id,
            description="The Pay-Yourself-First Budgeting method requires a Savings category.",
            allocated_amount=0,
            is_savings=True
        )
        db.session.add(savings_category)
        #db.session.flush()  # Save category without committing yet
        db.session.commit()
        return savings_category

    except Exception as e:
        raise e

# Initial budget setup and allocations (when new categories are made)
def pyf_allocation_calculation(budget_id):
    try:
        # Load the budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404

        # Calculate totals
        total_income = sum(income.amount for income in budget.incomes)
        total_expenses = sum(expense.amount for expense in budget.expenses)

        recommendations = []

        # Validate income vs expenses
        if total_expenses > total_income:
            recommendations.append(
                f"Expenses exceed income by ${total_expenses - total_income:.2f}. Consider adjusting your spending."
            )

        # Ensure required Savings category exists
        savings_category = next((c for c in budget.categories if c.is_savings), None)
        if not savings_category:
            recommendations.append("Required 'Savings' category is missing for Pay-Yourself-First budgeting.")

        # Check if Savings category has $0 allocated
        if savings_category and savings_category.allocated_amount <= 0:
            recommendations.append("Your 'Savings' category has $0 allocated. Pay-Yourself-First budgeting prioritizes saving before spending.")

        # Check for other $0 allocations
        for cat in budget.categories:
            if cat.allocated_amount == 0 and not cat.is_savings:
                recommendations.append(
                    f"Category '{cat.title}' has $0 allocated. Consider reviewing its importance."
                )

        # Build category info output
        categories_info = [{
            "title": c.title,
            "description": c.description,
            "allocated_amount": c.allocated_amount,
            "priority": c.priority
        } for c in budget.categories]

        return {
            "status": "analyzed",
            "total_income": total_income,
            "total_expenses": total_expenses,
            "categories": categories_info,
            "recommendations": recommendations
        }, 200

    except Exception as e:
        return {"status": "error", "msg": str(e)}, 500

def  pyf_purchase_calculation(budget_id):
    try:
        recommendations = []

        ## 1. Setup --> Loads all budget data
        # Retrieve budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404
        
        # Retrieve all purchases linked to the budget
        purchases = Purchase.query.filter_by(budget_id=budget_id).order_by(Purchase.date).all()
        if not purchases:
            return {"status": "ok", "msg": "No purchases made yet."}, 200
        
        # Retrieve all categories and expenses
        categories = Category.query.filter_by(budget_id=budget_id).all()
        expenses = BudgetExpense.query.filter_by(budget_id=budget_id).all()
        expense_lookup = {e.id: e for e in expenses}
        income_total = sum(income.amount for income in budget.incomes)

        # Find Savings category (PYF focuses on Savings category)
        savings_category = next((c for c in categories if c.is_savings), None)
        if not savings_category:
            return {"status": "error", "msg": "Savings category not found"}, 400
        
        category_spending = {cat.id: 0 for cat in categories}
        unlinked_purchases = []

        ## 2.1 Track spending
        for purchase in purchases:
            if purchase.budget_expense_id:
                expense = expense_lookup.get(purchase.budget_expense_id)
                if expense and expense.category_id:
                    category_spending[expense.category_id] += purchase.amount
            else:
                unlinked_purchases.append(purchase.title)

        total_spent = sum(p.amount for p in purchases)

        ## 2.2 First Purchase check --> Savings?
        first_purchase = purchases[0] # Ordered by date above
        if first_purchase.budget_expense_id:
            first_expense = expense_lookup.get(first_purchase.budget_expense_id)
            if not (first_expense and first_expense.category_id == savings_category.id):
                recommendations.append("First purchase was not made toward Savings. PYF recommends saving before spending.")
        else:
            recommendations.append("First purchase was not linked to any expense. Consider prioritizing Savings.")

        ## 3. Savings fully paid --> Goal met?
        spent_on_savings = category_spending[savings_category.id]
        if spent_on_savings < savings_category.allocated_amount:
            recommendations.append(
                f"Savings goal not yet reached. ${savings_category.allocated_amount - spent_on_savings:.2f} remaining."
            )
            
        ## 4. Check for overspending

        # Check if user spending exceeds income
        if total_spent > income_total:
            recommendations.append(
                f"Total spending exceeds income by ${total_spent - income_total:.2f}."
            )

        # 6. Per-category overspending
        for category in categories:
            spent = category_spending.get(category.id, 0)
            if spent > category.allocated_amount:
                recommendations.append(
                    f"Overspending in '{category.title}': exceeded by ${spent - category.allocated_amount:.2f}."
                )
        
        ## 5. Category priority violation check --> Are lower categories being spent first?
        priority_spending = {}
        for purchase in purchases:
            if purchase.budget_expense_id:
                exp = expense_lookup.get(purchase.budget_expense_id)
                if exp:
                    cat = next((c for c in categories if c.id == exp.category_id), None)
                    if cat:
                        priority_spending[cat.priority] = priority_spending.get(cat.priority, 0) + purchase.amount

        seen_priorities = sorted(priority_spending.keys())
        for idx, p in enumerate(seen_priorities):
            for higher in range(1, p):
                if higher not in priority_spending:
                    recommendations.append(
                        f"Spending on lower-priority category (priority {p}) before funding priority {higher}."
                    )

        ## 6. Unexpected Purchase check
        for title in unlinked_purchases:
            recommendations.append(f"'{title}' is not linked to a planned expense. Consider updating your budget.")

        # 7. Savings ratio warning
        savings_ratio = savings_category.allocated_amount / income_total
        if savings_ratio < 0.10:
            recommendations.append("Warning: Your savings allocation is less than 10% of income. Consider increasing it.")
        
        # 8. Dynamic recommendations (priority-based)
        for underfunded_cat in categories:
            underfunded_amt = underfunded_cat.allocated_amount - category_spending.get(underfunded_cat.id, 0)
            if underfunded_amt > 50:
                for overspent_cat in categories:
                    if overspent_cat.priority > underfunded_cat.priority:
                        overspent_amt = category_spending.get(overspent_cat.id, 0) - overspent_cat.allocated_amount
                        if overspent_amt > 0:
                            recommendations.append(
                                f"Consider reducing '{overspent_cat.title}' to fully fund higher-priority '{underfunded_cat.title}'."
                            )

        if not recommendations:
            recommendations.append("Nice! No budgeting issues detected.")
        return {
            "status": "analyzed",
            "recommendations": recommendations
        }, 200

    except Exception as e:
        return {"status": "error", "msg": str(e)}, 500