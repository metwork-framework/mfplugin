doc:
	rm -Rf html
	pdoc --html mfplugin

clean:
	rm -Rf html
	rm -Rf mfplugin.egg-info
	find . -type d -name __pycache__ -exec rm -Rf {} \; 2>/dev/null
