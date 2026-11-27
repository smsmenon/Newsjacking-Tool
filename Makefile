.PHONY: run digest verify package

run:
	PYTHONPATH=src python3 -m tada_ci.api.server --root .

digest:
	PYTHONPATH=src python3 -m tada_ci.pipeline --input examples/sample_articles.json --output work/daily_digest.json

verify:
	PYTHONPATH=src python3 scripts/verify.py

package:
	cd .. && zip -qr tada-content-intelligence-platform.zip tada-content-intelligence-platform

