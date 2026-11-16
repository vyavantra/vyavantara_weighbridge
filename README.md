### Vyavantra Weighbridge

Weighbridge management and vehicle weight tracking system for Vyavantra.

### Weighing Slip Entry Screen

One slip holds many trailers. Each trailer is measured independently, and the next trailer can be loaded while an earlier one is still unloading.

```
Add Trailer -> Get Loaded Weight -> (unloading) -> Get Unloaded Weight -> Binding KG -> Trailer Net
... repeat per trailer ... -> Total Cane Weight -> Other Deduction -> Final Net Cane Weight
-> Complete Weighment -> Cane Register -> Print Slip
```

Calculations run in the controller on every save:

- Cane Weight = Loaded - Unloaded
- Trailer Net = Cane Weight - Binding
- Total Cane Weight = sum of Trailer Net
- Deduction KG = Total Cane Weight x Deduction % / 100 (reason is mandatory when % > 0)
- Final Net Cane Weight = Total Cane Weight - Deduction KG

Whitelisted document methods (call with `frm.call({method, doc: frm.doc, args})`):
`add_trailer`, `get_loaded_weight(trailer_no)`, `get_unloaded_weight(trailer_no)`,
`reset_trailer_weights(trailer_no)`, `complete_weighment`.

### Weighbridge setup

Set **Weighbridge Settings > Weighbridge API URL**. The scale endpoint must answer a `GET` with JSON:

```json
{"weight": 10000, "stable": true}
```

A non-stable, non-positive or unreachable reading is rejected and nothing is saved. An optional API token is sent as a Bearer token.

### Brix Entry

The submittable **Brix Entry** Desk DocType records Date, Time, Tractor Number, and four floating-point readings (Mill 01–04). Date and time default to current values but remain editable. Weighbridge User and Slip Boy can submit entries; Weighbridge Manager can cancel or amend. This does not alter Weighment Slip or its weight-capture settings.

### Slip Boy Desk entry

The submittable **Slip Boy Entry** Desk DocType replaces the `/slip-boy` Web Form. Select a Cane Supplier or enter a new farmer with village, bank details, and private Bank Passbook/Aadhaar Card image uploads. On Submit, it creates the farmer if needed and a linked draft Weighment Slip for the weighbridge operator. Cancel is available to managers while that linked slip remains a draft.

### Effective binding and legacy codes

For a draft Weighment Slip, the effective Cane Rate Master is selected by Slip Date within Effective From–To and Delivery Type. The applied Binding Deduction (%) is stored on the slip but not shown on the form. Binding Material Weight is rounded to whole kilograms from Cane Weight × that percentage, then deducted from Cane Weight. A submitted slip retains the rate and binding with which it was submitted. Cane Supplier and Contractor Master each have an optional Old Farmer Code / Old Contractor Code field for previous-system references; their current naming stays unchanged.

### Weighment Slip navigation

Submitted slips are listed at `/app/weighment-slip/view/list?docstatus=1`. An older browser breadcrumb may still point to `/app/weighbridge-(वजनकाटा)`, which is no longer a Workspace. The Desk bundle redirects that legacy URL to the Weighment Slip list and clears the stale per-browser breadcrumb preference.

### Farmer Bill approval and payment

Fetch submitted, unbilled slips for the farmer and date range. Each Farmer Bill Slip displays cane kg, binding kg, net-after-binding kg, other deduction %/kg, final net kg, tonnes, and its cane rate from the Cane Rate Master effective on that slip's date and delivery type. The line amount is final net tonnes × rate; Total Weight Deductions (Amount) is informational because those kilograms are already excluded from the payable amount. Draft bills are approved by submitting them (Accounts Manager, Weighbridge Manager, or System Manager); the approved bill is Unpaid until approved Weighbridge Payments cover it, then becomes Paid. Existing submitted bills retain their original booked rate, quantity, and amount during migration.

### Bill payment workflow (Farmer Bill, Tractor Contractor Bill)

Both bills follow the same workflow: a saved bill is **Unpaid** and stays editable; **Pay** submits it and books the payment, making it **Paid**; **Cancel** (managers) on a Paid bill cancels the payment and the bill and releases its slips. Nothing about the payment is fixed in code: Company, Paid From (bank or cash account) and Paid To (the account the bill is booked to) are chosen on each bill, together with the bank's Reference No and Reference Date. A new bill starts from the Company and Bank Account of Weighbridge Settings (and its Cane Purchase Account for a Farmer Bill); these are only starting values.

Pay books two documents on the Reference Date: a Journal Entry from Paid To to the party's payable account, and a Payment Entry from Paid From to the party that settles it. ERPNext does not allow a party on an expense account, so the bank cannot pay that account in one entry. The party is the Supplier linked on the Cane Supplier or Contractor Master (Supplier (Accounts)); it is created at the first payment, in the Cane Supplier or Transport Contractor group. Creating that Supplier posts nothing to the ledgers. A Farmer Bill pays its Total Amount, rounded to whole rupees (Round Off shows the difference); a Tractor Contractor Bill pays its Final Payable Amount. Slips are marked as billed when the bill is paid.

### Tractor Contractor Bill and Diesel Issue Pavti

**Fetch Weighment Slips** on a Tractor Contractor Bill takes the submitted, unbilled Weighment Slips of the Transport Contractor in the From - To Date range. Each row carries the slip's Route, Distance and Net Cane Weight and is paid at the Todani Rate (per Ton) of its Delivery Type in the Cane Rate Master effective on the slip date. Diesel is recovered: a Diesel Issue Entry made against a slip (**Create Diesel Issue Pavti** on the submitted Weighment Slip, one per slip) shows its litres on that slip's row; a Diesel Issue Entry made on its own for the contractor gets a row of its own with only a date and litres. Deposit is 10% of the Total Amount; Diesel is Total Diesel Qty x the master's Diesel Rate (Per Litre, default 100) effective on the To Date; Total Recovery is Deposit + Diesel and the Final Payable Amount is Total Amount less Total Recovery. Advance shows the contractor's Advance Balance for reference only. Paying the bill marks its slips and diesel issues as billed; cancelling releases them.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app vyavantra_weighbridge
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/vyavantra_weighbridge
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
