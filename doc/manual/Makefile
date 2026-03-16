.PHONY: clean

DOCVER=$(shell cd ../..; $$PYTHON -c 'import tuned.version as v; print(v.TUNED_VERSION_STR)')
DOCDATE=$(shell date '+%Y-%m-%d')

index.html: master.adoc assemblies/*.adoc meta/*.adoc modules/performance/*.adoc ../../tuned/plugins/plugin_*.py ../../tuned/profiles/functions/function_*.py
	$(PYTHON) ./compile_plugin_docs.py ../../tuned/plugins plugin_ Plugin modules/performance/ref_available-tuned-plug-ins_intro.adoc modules/performance/ref_available-tuned-plug-ins.adoc
	$(PYTHON) ./compile_plugin_docs.py ../../tuned/profiles/functions function_ Function modules/performance/ref_built-in-functions-available-in-tuned-profiles_intro.adoc modules/performance/ref_built-in-functions-available-in-tuned-profiles.adoc
	asciidoctor -a revnumber=$(DOCVER) -a revdate=$(DOCDATE) -o index.html master.adoc || asciidoc -a revnumber=$(DOCVER) -a revdate=$(DOCDATE) -d book -o index.html master.adoc

install: index.html
	install -Dpm 0644 index.html $(DESTDIR)$(DOCDIR)/manual/index.html

clean:
	rm -f modules/performance/ref_available-tuned-plug-ins.adoc
	rm -f modules/performance/ref_built-in-functions-available-in-tuned-profiles.adoc
	rm -f *.html
