import frappe
from frappe.auth import LoginManager


@frappe.whitelist()
def authenticate_user(password):
    try:
        if not password:
            return gen_response(500, "Password is required")
        user = frappe.session.user
        if not user or user == "Guest":
            return gen_response(500, "User is not logged in")
        company=frappe.get_list("Company",fields=["name"])[0].name
        password_to_compare = frappe.get_value("Company", company, "custom_setting_password")
        if password != password_to_compare:
            return gen_response(500, "Password is incorrect")
        gen_response(200, "Password is correct")
    except frappe.AuthenticationError:
        gen_response(500, frappe.response["message"])
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        # validate_employee(login_manager.user)
        login_manager.post_login()
        if frappe.response["message"] == "Logged In":
            # emp_data = get_employee_by_user(login_manager.user)
            frappe.response["user"] = login_manager.user
            frappe.response["key_details"] = generate_key(login_manager.user)
        gen_response(200, frappe.response["message"])
    except frappe.AuthenticationError:
        gen_response(500, frappe.response["message"])
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_dashboard():
    try:
        dashboard_data = {
           "user": frappe.session.user,
           "username": frappe.get_cached_value("User", frappe.session.user, "full_name"),
           "total_stock_qty":frappe.db.get_value("Bin",{"warehouse": 'गोशाळा - G'},"SUM(actual_qty)") or 0,
           "total_animals": frappe.db.count("Animals"),
           "male_animals": frappe.db.count("Animals",{"gender":"Male"}),
            "female_animals": frappe.db.count("Animals",{"gender":"Female"}),
"animals_by_type_and_gender": get_animals_by_type_and_gender()
        }
       
        return gen_response(200, "Dashboard data get successfully", dashboard_data)

    except Exception as e:
        return exception_handler(e)
    

@frappe.whitelist()
def get_animal_master():
    try:
        dashboard_data = {
           "animal_master": frappe.get_list(
                "Animal Master",pluck="name"),
           "gender":["Male","Female"],
           "animals": frappe.get_list(
                "Animals", ["name","gender"])
           
        }
       
        return gen_response(200, "masters get successfully", dashboard_data)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def company():
    from frappe.contacts.doctype.address.address import get_company_address, get_address_display
    from bs4 import BeautifulSoup

    def clean_html_with_bs4(html):
        soup = BeautifulSoup(html, "html.parser")

        # Convert <br> to newlines
        for br in soup.find_all("br"):
            br.replace_with("\n")

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    try:
        default_company = get_global_defaults().get("default_company")
        doc = frappe.get_doc("Company", default_company)

        address_name = get_company_address(doc.name)
        address_display_html = get_address_display(address_name) if address_name else ""
        address_display_text = clean_html_with_bs4(address_display_html)

        company_data = {
            "company_name": doc.company_name,
            "abbr": doc.abbr,
            "default_currency": doc.default_currency,
            "country": doc.country,
            "phone_no": doc.phone_no or "",
            "email": doc.email or "",
            "company_description": doc.company_description or "",
            "address": {
                "company_address": address_name or "",
                "company_address_display": address_display_text or ""
            },
            "website": doc.website or "",
            "gst_category": doc.gst_category or "",
            "facebook": getattr(doc, "custom_facebook", ""),
            "instagram": getattr(doc, "custom_instagram", ""),
            "youtube": getattr(doc, "custom_youtube", "")
        }

        return gen_response(200, "Company retrieved successfully", company_data)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_purchase_receipt_items_exclude_cow():
    # Get parent Purchase Receipts with docstatus = 1
    purchase_receipts = frappe.get_all(
        "Purchase Receipt",
        filters={"docstatus": ["!=","2"]},
        fields=["name"]
    )

    # Extract PR names
    pr_names = [pr["name"] for pr in purchase_receipts]

    # Fetch items from the child table where item_code is not 'cow'
    items = frappe.get_all(
        "Purchase Receipt Item",
        filters={
            "parent": ["in", pr_names],
            "item_group": ["!=", "Raw Milk"]
        },
        fields=["parent", "item_code", "item_name",'item_group', "qty", "rate", "amount","docstatus"]
    )
    for i in items:
        i["supplier"] = frappe.get_value("Purchase Receipt", i['parent'], "supplier")
    return items


@frappe.whitelist()
def purchaseMasters():

    try:
        # default_company = get_global_defaults().get("default_company")
        # doc = frappe.get_doc("Company", default_company)
        from erpnext.accounts.utils import get_balance_on

        suppliers = frappe.get_list(
            "Supplier",
            filters={'custom_is_material_provider': 1},
            pluck="name"
        )

        result = []
        for supplier in suppliers:
            balance = get_balance_on(party_type="Supplier", party=supplier)
            result.append({
                "name": supplier,
                "balance": balance
            })
        purchase_list = frappe.get_list(
            "Purchase Receipt",
            filters={"docstatus": 1},
            fields=["name", "posting_date", "supplier", "total_qty"],
        )
        for d in purchase_list:
            d["purchase_items"] = frappe.get_all(
                "Purchase Receipt Item",
                filters={"parent": d.name, "parentfield": "items"},
                fields=["item_code", "item_name", "rate", "qty", "amount","uom"]
            )
        company_data = {
            "supplier":result,
            "item": frappe.get_list(
                "Item",filters={'custom_is_chara':1,"disabled":0,"is_purchase_item":1},pluck="name"),
            "uom": frappe.get_list(
                "UOM",filters={'enabled':1},pluck="name"),
            "warehouse":  frappe.get_list(
                "Warehouse",filters={"disabled":0,"is_group":0},pluck="name"),
            "purchase_list":purchase_list
        }
        return gen_response(200, "Purchase Masters retrieved successfully", company_data)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def salesMasters():

    try:
        # default_company = get_global_defaults().get("default_company")
        # doc = frappe.get_doc("Company", default_company)
        from erpnext.accounts.utils import get_balance_on

        customers = frappe.get_list(
            "Customer",
            filters={'disabled': 0},
            pluck="name"
        )

        result = []
        for customer in customers:
            balance = get_balance_on(party_type="Customer", party=customer)
            result.append({
                "name": customer,
                "balance": balance
            })
        customer_list = frappe.get_list(
            "Delivery Note",
            filters={"docstatus": 1},
            fields=["name", "posting_date", "customer", "total_qty"],
        )
        for d in customer_list:
            d["sales_items"] = frappe.get_all(
                "Delivery Note Item",
                filters={"parent": d.name, "parentfield": "items"},
                fields=["item_code", "item_name", "rate", "qty", "amount","uom"]
            )

        company_data = {
            "customer":result,
            "item": frappe.get_list(
                "Item",filters={"disabled":0,"is_sales_item":1},pluck="name"),
            "uom": frappe.get_list(
                "UOM",filters={'enabled':1},pluck="name"),
            "warehouse":  frappe.get_list(
                "Warehouse",filters={"disabled":0,"is_group":0},pluck="name"),
            "customer_list": customer_list,
        }
        return gen_response(200, "Sales Masters retrieved successfully", company_data)

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
def materialMasters():

    try:

        company_data = {
            "item": frappe.get_list(
            "Item",
            filters={"is_stock_item": 1},
            fields=["name", "item_name", "item_code", "image"],
        ),
            "uom": frappe.get_list(
                "UOM",filters={'enabled':1},pluck="name"),
            "warehouse":  frappe.get_list(
                "Warehouse",filters={"disabled":0,"is_group":0},pluck="name"),
            "stock_list": frappe.get_list(
                "Stock Entry",filters={"docstatus":1,"purpose":"Material Transfer"},fields=["name","posting_date"]),
        }
        return gen_response(200, "Stock Masters retrieved successfully", company_data)

    except Exception as e:
        return exception_handler(e)



@frappe.whitelist()
def get_animals_by_type_and_gender():
    # Step 1: Gender-wise count from Animals (excluding null types)
    raw_data = frappe.db.get_all(
        "Animals",
        fields=["animal_type", "gender", "COUNT(name) AS count"],
        filters={"animal_type": ["is", "set"]},
        group_by="animal_type, gender"
    )

    result = {}

    for row in raw_data:
        animal_type = row["animal_type"]
        gender = (row["gender"] or "").strip().lower()
        count = row["count"] or 0

        if not animal_type:
            continue  # Skip null/empty types

        if animal_type not in result:
            result[animal_type] = {
                "animal_type": animal_type,
                "male": 0,
                "female": 0,
                "total": 0,
                "actual_qty": 0
            }

        if gender in ["male", "female"]:
            result[animal_type][gender] = count
            result[animal_type]["total"] += count

    # Step 2: Map animal_type -> item_code from Animal Master
    item_code_map = {
        d.name: d.item_code
        for d in frappe.get_all(
            "Animal Master",
            filters={"name": ["in", list(result.keys())]},
            fields=["name", "item_code"]
        )
    }

    # Step 3: Get stock from Bin
    if item_code_map:
        stock_data = frappe.db.get_all(
            "Bin",
            filters={"item_code": ["in", list(item_code_map.values())]},
            fields=["item_code", "SUM(actual_qty) as actual_qty"],
            group_by="item_code"
        )

        reverse_map = {v: k for k, v in item_code_map.items()}
        for stock in stock_data:
            animal_type = reverse_map.get(stock["item_code"])
            if animal_type in result:
               result[animal_type]["actual_qty"] = float(stock["actual_qty"] or 0)
    return list(result.values())


@frappe.whitelist()
def get_item_list():
    try:
        item_list = frappe.get_list(
            "Item",
            filters={"custom_show_dashboard_mobile_app": 1},
            fields=["name", "item_name", "item_code", "image"],
        )
        warehouse = frappe.get_value("Goshala Setting", None, "purchase_warehouse")
        items = get_items_data(item_list,warehouse)
        gen_response(200, "Item list get successfully", items)
    except Exception as e:
        return exception_handler(e)


def get_items_data(items,warehouse):
    items_data = []
    for item in items:
        item_data = {
            "name": item.name,
            "item_name": item.item_name,
            "item_code": item.item_code,
"image": frappe.utils.get_url() + item.image if item.image else None,
            "actual_qty": float(get_actual_qty(item.item_code,warehouse)),
            "rate": get_item_rate(item.item_code)  # Fetch rate
        }
        items_data.append(item_data)
    return items_data


def get_actual_qty(item_code,warehouse):
    bin_data = frappe.get_all(
        "Bin",
        filters={"item_code": item_code,"warehouse":warehouse},
        fields=["actual_qty", "warehouse"]
    )
    if bin_data:
        return bin_data[0].get("actual_qty", 0)
    else:
        return 0


def get_item_rate(item_code):
    item_price = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code,"price_list":"Standard Selling"},
        fields=["price_list_rate"],
        order_by="creation desc",  # Add this to get the latest price
        limit=1  # Add this to get only the latest price
    )
    if item_price:
        return item_price[0].get("price_list_rate", 0)
    else:
        return 0.0

def get_global_defaults():
    return frappe.get_doc("Global Defaults", "Global Defaults")



@frappe.whitelist()
def create_collection(**kwargs):
    try:
        data = kwargs
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        data["supplier"] = frappe.get_value("Goshala Setting", None, "supplier")
        global_defaults = get_global_defaults()
        data["set_posting_time"] = 1
        company = global_defaults.get("default_company")        
        if data.get("name"):
            if not frappe.db.exists("Purchase Receipt", data.get("name"), cache=True):
                return gen_response(500, "Invalid collection id.")
            sales_order_doc = frappe.get_doc("Purchase Receipt", data.get("name"))
            
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.save()
            gen_response(200, "Collection updated successfully.", sales_order_doc)
           
        else:
            sales_order_doc = frappe.get_doc(
                dict(doctype="Purchase Receipt", company=company)
            )
            
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.insert()
            gen_response(200, "Collection created successfully.", sales_order_doc)

    except Exception as e:
        return exception_handler(e)




def get_employee_by_user(user, fields=["name"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data


def generate_key(user):
    user_details = frappe.get_doc("User", user)
    api_secret = api_key = ""
    if not user_details.api_key and not user_details.api_secret:
        api_secret = frappe.generate_hash(length=15)
        # if api key is not set generate api key
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
        user_details.api_secret = api_secret
        user_details.save(ignore_permissions=True)
    else:
        api_secret = user_details.get_password("api_secret")
        api_key = user_details.get("api_key")
    return {"api_secret": api_secret, "api_key": api_key}


def ess_validate(methods):
   
    def wrapper(wrapped, instance, args, kwargs):
        if not frappe.local.request.method in methods:
            return gen_response(500, "Invalid Request Method")
        return wrapped(*args, **kwargs)

    return wrapper


def get_employee_by_user(user, fields=["name"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data
    
    
from bs4 import BeautifulSoup



def gen_response(status, message, data=[]):
    frappe.response["http_status_code"] = status
    if status == 500:
        frappe.response["message"] = BeautifulSoup(str(message)).get_text()
    else:
        frappe.response["message"] = message
    frappe.response["data"] = data


def exception_handler(e):
    if hasattr(e, "http_status_code"):
        return gen_response(e.http_status_code, BeautifulSoup(str(e)).get_text())
    else:
        return gen_response(500, BeautifulSoup(str(e)).get_text())



@frappe.whitelist()
def get_total_stock_qty():
    total_qty=frappe.db.get_value("Bin",{"item_code":["IN",['Jarshi Milk','Gir Milk']],"warehouse": 'गोशाळा - G'},"SUM(actual_qty)") or 0
    return {"total_qty": round(total_qty, 2)}



