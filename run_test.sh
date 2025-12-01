#!/usr/bin/env bash
MODULE=${1:-inputs}
python -m tests.test_runner "$MODULE"
RC=$?
exit $RC
