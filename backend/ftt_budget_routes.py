#ftt_budget_routes.py by Eden Pardo
#from flask import Blueprint, request, jsonify
from models import Category, Purchase, Budget, BudgetExpense, BudgetIncome
from extensions import db
from base_budget_routes import*

def create_base_categories_ftt(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        total_income = sum(income.amount for income in budget.incomes)
        allocations = {
            "Needs": 0.50 * total_income,
            "Savings": 0.20 * total_income,
            "Wants": 0.30 * total_income,
        }

        needs_category = Category(
            title="Needs",
            priority=1,
            budget_id=budget.id,
            description="The 50/30/20 Budgeting method requires a Needs category.",
            allocated_amount=allocations["Needs"]
        )
        savings_category = Category(
            title="Savings",
            priority=2,
            budget_id=budget.id,
            description="The 50/30/20 Budgeting method requires a Savings category.",
            allocated_amount=allocations["Savings"]
        )
        wants_category = Category(
            title="Wants",
            priority=3,
            budget_id=budget.id,
            description="The 50/30/20 Budgeting method requires a Wants category.",
            allocated_amount=allocations["Wants"]
        )

        db.session.add(needs_category)
        db.session.add(savings_category)
        db.session.add(wants_category)
        db.session.commit()

        return {
            "msg": "Base categories created successfully.",
            "categories": [needs_category.to_json(), savings_category.to_json(), wants_category.to_json()]
        }, 201


    except Exception as e:
        db.session.rollback()
        raise e

# Initial budget setup and allocations
def ftt_allocation_calculation(budget_id):
    try:
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404

        total_income = sum(income.amount for income in budget.incomes)
        total_expenses = sum(expense.amount for expense in budget.expenses)

        recommendations = []

        if total_expenses > total_income:
            recommendations.append(
                f"Expenses exceed income by ${total_expenses - total_income:.2f}. Consider adjusting your spending."
            )

        # Retrieve current allocations for comparison
        category_lookup = {c.title.lower(): c for c in budget.categories}

        expected_ratios = {
            "needs": 0.50,
            "wants": 0.30,
            "savings": 0.20
        }

        # Check zero allocations
        for cat in budget.categories:
            if cat.allocated_amount == 0:
                recommendations.append(
                    f"Category '{cat.title}' has $0 allocated. Consider assigning funds to reflect its importance."
                )

        # Check deviation from expected ratios
        for name, expected_ratio in expected_ratios.items():
            cat = category_lookup.get(name)
            if cat:
                actual = cat.allocated_amount
                lower = total_income * (expected_ratio - 0.95)
                upper = total_income * (expected_ratio + 1.05)
                if not (lower <= actual <= upper):
                    recommendations.append(
                        f"'{cat.title}' allocation is outside the recommended 50/30/20 range. You assigned ${actual:.2f}, but target is ~{int(expected_ratio * 100)}% of income."
                    )
            else:
                recommendations.append(f"Missing required category: '{name.title()}'")

        # Build category info
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
        db.session.rollback()
        return {"status": "error", "msg": str(e)}, 500

def  ftt_purchase_calculation(budget_id):
    try:
        recommendations = []

        ## 1. Load relevant data
        budget = Budget.query.get(budget_id)
        if not budget:
            return {"status": "error", "msg": "Budget not found"}, 404

        purchases = Purchase.query.filter_by(budget_id=budget_id).order_by(Purchase.date).all()
        if not purchases:
            return {"status": "ok", "msg": "No purchases made yet."}, 200
        
        categories = Category.query.filter_by(budget_id=budget_id).all()
        expenses = BudgetExpense.query.filter_by(budget_id=budget_id).all()
        income_total = sum(income.amount for income in budget.incomes)

        expense_lookup = {e.id: e for e in expenses}
        category_map = {c.title.lower(): c for c in categories}

        # Check for necessary categories
        required = {"needs", "wants", "savings"}
        if not required.issubset(set(category_map.keys())):
            return {"status": "error", "msg": "Missing one or more required 50-30-20 categories"}, 400
        
        ## 2. Track spending per category
        category_spending = {cat.id: 0 for cat in categories}
        unlinked_purchases = []

        for purchase in purchases:
            if purchase.budget_expense_id:
                expense = expense_lookup.get(purchase.budget_expense_id)
                if expense and expense.category_id:
                    category_spending[expense.category_id] += purchase.amount
            else:
                unlinked_purchases.append(purchase.title)

        total_spent = sum(p.amount for p in purchases)
        # Unlinked purchases
        for title in unlinked_purchases:
            recommendations.append(f"'{title}' is not linked to any expense. Consider revising your budget to reflect this purchase.")

        ## 3. Overspending check
        if total_spent > income_total:
            recommendations.append(f"You have exceeded your income by ${total_spent - income_total:.2f}.")

        ## 4. Spending vs allocation
        for category in categories:
            spent = category_spending.get(category.id, 0)
            if spent > category.allocated_amount:
                recommendations.append(f"Overspending in '{category.title}': over by ${spent - category.allocated_amount:.2f}.")
            elif spent < 0.5 * category.allocated_amount:
                recommendations.append(f"Under-utilized category '{category.title}'. You’ve only used ${spent:.2f} of your allocation.")

        ## 5. Priority violation check
        priority_spending = {}
        for purchase in purchases:
            if purchase.budget_expense_id:
                expense = expense_lookup.get(purchase.budget_expense_id)
                if expense and expense.category_id:
                    category = next((c for c in categories if c.id == expense.category_id), None)
                    if category:
                        priority_spending[category.priority] = priority_spending.get(category.priority, 0) + purchase.amount

        seen_priorities = sorted(priority_spending.keys())
        for idx, current_priority in enumerate(seen_priorities):
            for higher_priority in range(1, current_priority):
                if higher_priority not in priority_spending:
                    recommendations.append(
                        f"Spending detected on lower-priority category (priority {current_priority}) before higher-priority category (priority {higher_priority}) was used."
                    )

        ## 7. Check if allocations are within 5% of ideal percentage
        recommended_split = {"needs": 0.5, "wants": 0.3, "savings": 0.2}
        ideal_ranges = {k: (v * income_total * 0.95, v * income_total * 1.05) for k, v in recommended_split.items()}

        all_near_target = True
        for k, cat in category_map.items():
            if not (ideal_ranges[k][0] <= cat.allocated_amount <= ideal_ranges[k][1]):
                all_near_target = False
                break
        if all_near_target:
            recommendations.append("You are within 5% of your recommended allocation for all three categories. Great balance!")
        
        ## 8. Detect major imbalance
        savings_actual = category_map["savings"].allocated_amount
        needs_actual = category_map["needs"].allocated_amount
        savings_pct = savings_actual / income_total
        needs_pct = needs_actual / income_total
        if savings_pct < 0.15 and needs_pct > 0.6:
            recommendations.append(
                "Your allocation deviates significantly from the recommended 50/30/20 split. "
                "Consider adjusting your Needs and Savings categories for better balance."
            )
        
        ## 9. Dynamic Recommendations (Priority-based logic)
        for underfunded_cat in categories:
            underfunded_amount = underfunded_cat.allocated_amount - category_spending.get(underfunded_cat.id, 0)
            if underfunded_amount > 50:  # consider it underfunded
                for overspent_cat in categories:
                    if overspent_cat.priority > underfunded_cat.priority:
                        overspent_amount = category_spending.get(overspent_cat.id, 0) - overspent_cat.allocated_amount
                        if overspent_amount > 0:
                            recommendations.append(
                                f"Consider reducing spending in '{overspent_cat.title}' to better fund higher-priority '{underfunded_cat.title}'."
                            )

        if not recommendations:
            recommendations.append("Great job! You're on track with your 50-30-20 plan.")
        return {"status": "analyzed", "recommendations": recommendations}, 200

    except Exception as e:
        return {"status": "error", "msg": str(e)}, 500