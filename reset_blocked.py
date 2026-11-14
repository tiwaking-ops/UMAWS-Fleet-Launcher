from pmk.api import Kernel
k = Kernel(root=r'C:\temp\projects\testproject1')
k.init()
state = k.state()

print("BLOCKED tasks:")
for task in state.task_list():
    if task.state == 'BLOCKED':
        print(f"  {task.id}: attempt={getattr(task, 'attempt', 'N/A')}, fence={task.fence}")

# The task data is in the event log. We can't easily reset attempts via API.
# Options:
# 1. Use pmk task void to void them, then overseer will recreate
# 2. Edit the event log (not recommended)
# 3. The next time conductor retries, it might create new attempts

print("\nREADY tasks:")
for task in state.task_list():
    if task.state == 'READY':
        print(f"  {task.id}: fence={task.fence}")

print(f"\nTotal tasks: {len(state.task_list())}")
print(f"Project state: {state.project_state}")