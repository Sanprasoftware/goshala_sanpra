import frappe
from frappe import whitelist

@frappe.whitelist()
def get_purchase_receipt_items(posting_date=None, shift=None, item_name=None):
    # Step 1: Build Purchase Receipt filters
    pr_filters = {"docstatus": ["!=", "2"]}
    if posting_date:
        pr_filters["posting_date"] = posting_date
    if shift:
        pr_filters["custom_shift"] = shift

    # Get parent Purchase Receipts
    purchase_receipts = frappe.get_all(
        "Purchase Receipt",
        filters=pr_filters,
        fields=["name"]
    )

    if not purchase_receipts:
        return []

    # Extract PR names
    pr_names = [pr["name"] for pr in purchase_receipts]

    # Step 2: Build Purchase Receipt Item filters
    item_filters = {
        "parent": ["in", pr_names],
        "item_group": "Raw Milk"
    }
    if item_name:
        item_filters["item_code"] = ["like", f"%{item_name}%"]

    # Fetch items
    items = frappe.get_all(
        "Purchase Receipt Item",
        filters=item_filters,
        fields=["parent", "item_code", "item_name", "item_group", "qty"]
    )

    # Add shift info from parent document
    for item in items:
        purchase=frappe.get_value("Purchase Receipt", item['parent'], ["custom_shift","posting_date"],as_dict=True)
        item['shift'] = purchase.custom_shift
        item['date'] = purchase.posting_date

    return items




