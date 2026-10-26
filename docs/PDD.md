# PDD: testproject1      version: 1      status: approved

## 1. Purpose
Verify the UMAWS Fleet dispatcher can execute live agent tasks end-to-end using the pi profile.

## 2. Goals
### G-001 Hello world test
acceptance:
- hello.txt exists with content containing "hello"
oracle: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" hello.txt && python -c "import sys; sys.exit(0 if open(sys.argv[1]).read().find('hello') >= 0 else 1)" hello.txt`

### G-002 Pi marker test
acceptance:
- pi-test.txt exists with content containing "pi"
oracle: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" pi-test.txt && python -c "import sys; sys.exit(0 if open(sys.argv[1]).read().find('pi') >= 0 else 1)" pi-test.txt`

## 3. Non-goals
No application functionality beyond verifying the Fleet mechanism.

## 4. Constraints
Python 3.11 or later.
Windows-native execution.

## 5. Architecture sketch
Two simple file-writing tasks to verify the Fleet dispatch, worktree, oracle, and merge queue pipeline.

## 6. Definition of done
gate_cmd: `python -c "import os,sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 1)" hello.txt`

## 7. Open questions
None.