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
