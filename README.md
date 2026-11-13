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
