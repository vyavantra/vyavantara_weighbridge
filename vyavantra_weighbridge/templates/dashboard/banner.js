const root = root_element.shadowRoot || root_element;
root.querySelectorAll("[data-new]").forEach((el) => el.addEventListener("click", () => frappe.new_doc(el.dataset.new)));
root.querySelectorAll("[data-go]").forEach((el) => el.addEventListener("click", () => frappe.set_route(...el.dataset.go.split("/"))));
