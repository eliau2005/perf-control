# make check  -- lint everything CI lints (needs shellcheck, ruff, desktop-file-validate, xmllint)
# make dist   -- build dist/perf-control-$(VERSION).tar.gz + .sha256

VERSION := $(shell cat VERSION)
NAME    := perf-control-$(VERSION)

SH := install.sh bin/powermon bench/*.sh thermald/*.sh
PY := bin/perf-control libexec/perfctld libexec/perfctl-helper bench/*.py tools/*.py

# what install.sh and thermald/install.sh need, plus docs
DIST_FILES := VERSION README.md install.sh docs/ROLLBACK.md \
	bin/perf-control bin/powermon libexec/perfctld libexec/perfctl-helper \
	systemd/perfctld.service polkit/local.perfctl.policy share/local.PerfControl.desktop \
	thermald/README.md thermald/install.sh thermald/override.conf thermald/vault-override.sh \
	tools/gddv_dump.py tools/gddv_patch.py tools/gddv_lzma_check.cpp \
	research/gddv/x1402_p28_0322-cool89.bin

.PHONY: check dist clean

check:
	shellcheck -S error $(SH)
	ruff check --select E9,F $(PY)
	python3 -m py_compile $(PY)
	desktop-file-validate share/local.PerfControl.desktop
	xmllint --noout polkit/local.perfctl.policy
	find . -name __pycache__ -prune -exec rm -rf {} +

dist:
	rm -rf dist/$(NAME)
	mkdir -p dist/$(NAME)
	cp --parents -p $(DIST_FILES) dist/$(NAME)/
	tar -C dist --owner=0 --group=0 --sort=name -czf dist/$(NAME).tar.gz $(NAME)
	cd dist && sha256sum $(NAME).tar.gz > $(NAME).tar.gz.sha256
	rm -rf dist/$(NAME)

clean:
	rm -rf dist
