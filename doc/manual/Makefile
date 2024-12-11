.PHONY: clean

index.html: master.adoc assemblies/*.adoc meta/*.adoc modules/performance/*.adoc ../../tuned/plugins/plugin_*.py
	python3 ../../compile_plugin_docs.py modules/performance/ref_available-tuned-plug-ins_intro.adoc modules/performance/ref_available-tuned-plug-ins.adoc
	asciidoctor -o index.html master.adoc || asciidoc -o index.html master.adoc

install: index.html
	install -Dpm 0644 index.html $(DESTDIR)$(DOCDIR)/manual/index.html

clean:
	rm -f modules/performance/ref_available-tuned-plug-ins.adoc
	rm -f *.html
