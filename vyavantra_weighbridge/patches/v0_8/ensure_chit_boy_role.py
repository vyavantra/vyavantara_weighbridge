from vyavantra_weighbridge.setup import ensure_roles


def execute():
	"""Chit Boy must exist before the doctypes that grant it permissions are synced."""
	ensure_roles()
