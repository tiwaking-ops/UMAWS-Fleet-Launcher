import json

events = []
with open('.pm/events/2026-10-23.jsonl') as f:
    for line in f:
        line = line.strip()
        if line:
            events.append(json.loads(line))

t0003 = []
for e in events:
    if e.get('subject') == 'T-0003':
        t0003.append(e)

t0003.sort(key=lambda x: x['seq'])

with open('pilot/assessment/upload/t0003-lifecycle-extract.txt', 'w') as f:
    f.write('=== T-0003 Lifecycle Extract (2026-10-23) ===\n')
    f.write('Source: .pm/events/2026-10-23.jsonl\n')
    f.write('Total T-0003 events: %d\n' % len(t0003))
    f.write('=\n')
    for e in t0003:
        payload = e.get('payload', {})
        ttype = e['type']
        if ttype == 'AGENT_STARTED':
            p = payload
            f.write('%(ts)s | AGENT_STARTED | seq=%(seq)s | adapter=%(adapter)s pid=%(pid)s profile=%(profile)s log=%(log)s worktree=%(worktree)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'adapter': p.get('adapter'), 'pid': p.get('pid'),
                'profile': p.get('profile'), 'log': p.get('log'), 'worktree': p.get('worktree')})
        elif ttype == 'CLAIMED':
            p = payload
            f.write('%(ts)s | CLAIMED | seq=%(seq)s | attempt=%(attempt)s fence=%(fence)s holder=%(holder)s task_id=%(task_id)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'attempt': p.get('attempt'), 'fence': p.get('fence'),
                'holder': p.get('lease', {}).get('holder'), 'task_id': p.get('lease', {}).get('task_id')})
        elif ttype == 'FLEET_ASSIGNED':
            p = payload
            f.write('%(ts)s | FLEET_ASSIGNED | seq=%(seq)s | profile=%(profile)s reason=%(reason)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'profile': p.get('profile'), 'reason': p.get('reason')})
        elif ttype == 'AGENT_EXITED':
            p = payload
            f.write('%(ts)s | AGENT_EXITED | seq=%(seq)s | class=%(class)s exit_code=%(exit_code)s profile=%(profile)s log=%(log)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'class': p.get('class'), 'exit_code': p.get('exit_code'),
                'profile': p.get('profile'), 'log': p.get('log')})
        elif ttype == 'AGENT_RESUMED':
            p = payload
            f.write('%(ts)s | AGENT_RESUMED | seq=%(seq)s | mode=%(mode)s model=%(model)s previous_profile=%(previous_profile)s profile=%(profile)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'mode': p.get('mode'), 'model': p.get('model'),
                'previous_profile': p.get('previous_profile'), 'profile': p.get('profile')})
        elif ttype == 'AGENT_FAILED':
            p = payload
            f.write('%(ts)s | AGENT_FAILED | seq=%(seq)s | class=%(class)s profile=%(profile)s reason=%(reason)s restart_count=%(restart_count)s step=%(step)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'class': p.get('class'), 'profile': p.get('profile'),
                'reason': p.get('reason'), 'restart_count': p.get('restart_count'), 'step': p.get('step')})
        elif ttype == 'TASK_CREATED':
            p = payload
            f.write('%(ts)s | TASK_CREATED | seq=%(seq)s | id=%(id)s title=%(title)s agent_hint=%(agent_hint)s fence=%(fence)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'id': p.get('id'), 'title': p.get('title'),
                'agent_hint': p.get('agent_hint'), 'fence': p.get('fence')})
        elif ttype == 'TASK_ADMITTED':
            f.write('%(ts)s | TASK_ADMITTED | seq=%(seq)s | subject=%(subject)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'subject': e.get('subject')})
        elif ttype == 'SUBMITTED':
            f.write('%(ts)s | SUBMITTED | seq=%(seq)s | subject=%(subject)s\n' % {
                'ts': e['ts'], 'seq': e['seq'], 'subject': e.get('subject')})

print('T-0003 lifecycle extract written: %d events' % len(t0003))
