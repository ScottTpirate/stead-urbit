.DEFAULT_GOAL := help
# Bound seed/toolchain verification before the inner native guardian launches.
PREP = systemd-run --user --scope --quiet -p CPUQuota=50% -p CPUQuotaPeriodSec=10ms -- taskset -c "$$(python3 -c 'import os; print(max(os.sched_getaffinity(0)))')"
.PHONY: help setup doctor preflight dev start status wait-ready stop reset check test core-check core-test gall-schedule skill-prequalify plan-check contracts-check
help:
	@python3 scripts/urbit/dev_help.py
setup:
	python3 scripts/urbit/toolchain.py fetch
doctor:
	python3 scripts/urbit/harness.py doctor
preflight:
	python3 scripts/urbit/harness.py preflight
start:
	$(PREP) python3 scripts/urbit/harness.py start
status:
	python3 scripts/urbit/harness.py status
wait-ready:
	python3 scripts/urbit/harness.py wait-ready
dev:
	$(PREP) python3 scripts/urbit/harness.py dev
stop:
	python3 scripts/urbit/harness.py stop
reset:
	python3 scripts/urbit/harness.py reset
test:
	python3 scripts/urbit/harness.py test
core-test:
	python3 scripts/urbit/harness.py core-test
core-check:
	python3 scripts/urbit/harness.py core-check
gall-schedule:
	python3 scripts/urbit/harness.py gall-schedule
skill-prequalify:
	python3 scripts/urbit/harness.py skill-evaluation --condition prequalification
check:
	python3 scripts/urbit/validate_plan.py
	python3 scripts/urbit/check_ecosystem.py
	python3 scripts/urbit/contracts.py test
	python3 scripts/urbit/contracts_v2.py
	python3 -m unittest discover -s tests/urbit -p 'test_*.py'
plan-check:
	python3 scripts/urbit/validate_plan.py
contracts-check:
	python3 scripts/urbit/contracts.py test
	python3 scripts/urbit/contracts_v2.py
	python3 -m unittest discover -s tests/urbit -p test_contracts_v2.py -v
