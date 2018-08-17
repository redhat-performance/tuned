ARG OS

FROM $OS

WORKDIR /test_dir

ADD ./ /test_dir

ARG PACKAGE_MANAGER=dnf

ENV PKM=$PACKAGE_MANAGER

ARG OS
RUN if [[ $OS == "centos:7" ]]; then yum install -y epel-release; fi;

RUN ${PKM} install -y virt-what ethtool gawk hdparm util-linux dbus polkit make
ARG PYTHON
RUN ${PKM} install -y python$PYTHON-flexmock

ARG OS
ARG PYTHON
RUN if [[ $OS == "centos:7" ]]; then export py=python; \
	else export py=python$PYTHON; fi; \
	${PKM} install -y ${py}-dbus \
	${py}-decorator ${py}-pyudev ${py}-configobj ${py}-schedutils \
	${py}-linux-procfs ${py}-perf ${py}-unittest2 ${py}-gobject-base;

