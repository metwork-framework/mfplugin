doc:
	rm -Rf html
	pdoc --html mfplugin

clean:
	rm -Rf html htmlcov build dist
	rm -Rf mfplugin.egg-info
	find . -type d -name __pycache__ -exec rm -Rf {} \; 2>/dev/null || exit 0

test: clean
	pytest tests/

coverage: clean test
	pytest --cov-report html --cov=mfplugin tests/
	pytest --cov=mfplugin tests/
