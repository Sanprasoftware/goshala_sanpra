import frappe
from frappe.utils import getdate, nowdate

@frappe.whitelist()
def update_supplier_age(name):
    supplier = frappe.get_doc("Supplier", name)
    birth_date = supplier.get("custom_birth_date")
    if not birth_date:
        return

    birth_date = getdate(birth_date)
    today = getdate(nowdate())

    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day

    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12

    age_display = f"{years} y, {months} m"

    frappe.db.set_value("Supplier", supplier.name, "custom_age", years)
    frappe.db.set_value("Supplier", supplier.name, "custom_age_months", age_display)

    return {
        "status": "success",
        "message": f"Updated age for {supplier.name}"
    }

# Auto update age for all suppliers (for scheduled job)
@frappe.whitelist()
def update_all_suppliers_age():
    suppliers = frappe.get_all("Supplier", filters={"custom_birth_date": ["!=", ""]}, fields=["name"])
    for s in suppliers:
        try:
            update_supplier_age(s.name)
        except Exception as e:
            frappe.log_error(f"Error updating age for {s.name}: {str(e)}")
