.PHONY: setup doctor start stop reset test plan-check contracts-check
setup:
	python3 scripts/urbit/toolchain.py fetch
doctor:
	python3 scripts/urbit/harness.py doctor
start:
	python3 scripts/urbit/harness.py start
stop:
	python3 scripts/urbit/harness.py stop
reset:
	python3 scripts/urbit/harness.py reset
test:
	python3 scripts/urbit/harness.py test
plan-check:
	python3 scripts/urbit/validate_plan.py
contracts-check:
	python3 scripts/urbit/contracts.py test
