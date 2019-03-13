.PHONY: clean

index.html: master.adoc assemblies/*.adoc meta/*.adoc modules/performance/*.adoc
	asciidoctor -o index.html master.adoc || asciidoc -o index.html master.adoc

install: index.html
	install -Dpm 0644 index.html $(DESTDIR)$(DOCDIR)/manual/index.html

clean:
	rm -f *.html
