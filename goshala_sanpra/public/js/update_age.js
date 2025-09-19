frappe.ui.form.on('Supplier', {
    after_save: function(frm) {
        if (frm.doc.custom_birth_date) {
            frappe.call({
                method: "goshala_sanpra.custom_pyfile.cal_age.update_supplier_age",
                args: {
                    name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.status === "success") {
                        frappe.msgprint("Age updated after saving.");
                        frm.reload_doc();
                    }
                }
            });
        }
    }
});
