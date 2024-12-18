sync:
	pdm sync --clean

lock:
	pdm lock

format:
	pdm run format

format-md:
	mdformat *.md
