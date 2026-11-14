from pmk.api import Kernel

k = Kernel(root=r'C:\temp\projects\testproject1')
k.init()

tasks = [
    ('Repo skeleton, pyproject.toml, .gitattributes, AGENTS.md, CLAUDE.md', 
     {'write': ['pyproject.toml', '.gitattributes', 'AGENTS.md', 'CLAUDE.md', 'pytest.ini', 'src/', 'tests/test_smoke.py']}, 
     'python -m pytest -q tests/test_smoke.py and python -c "import cna"'),
    ('Vendor rules at pinned commit into docs/rules/ with checksums manifest', 
     {'write': ['docs/rules/']}, 
     'python -c "import json; m=json.load(open(\'docs/rules/manifest.json\')); assert len(m[\"files\"])>=66"'),
    ('Rules indexer: sections, case anchors, xrefs, tables to docs/rules/index.json', 
     {'write': ['src/cna/tools/rules_index.py', 'tests/test_rules_index.py']}, 
     'python -m pytest -q tests/test_rules_index.py'),
    ('show_rule tool: case plus cross-references', 
     {'write': ['src/cna/tools/show_rule.py', 'tests/test_show_rule.py']}, 
     'python -m pytest -q tests/test_show_rule.py'),
    ('Coverage tool and initial coverage/rules_coverage.json', 
     {'write': ['src/cna/tools/coverage.py', 'tests/test_coverage.py']}, 
     'python -m pytest -q tests/test_coverage.py'),
    ('Core: ids, errors, dice (d6, 2d6, sequential 11-66), seeded RNG', 
     {'write': ['src/cna/core/', 'tests/test_dice.py']}, 
     'python -m pytest -q tests/test_dice.py'),
    ('State model, JSON serialisation with schema version, state hash', 
     {'write': ['src/cna/state/', 'tests/test_state_roundtrip.py']}, 
     'python -m pytest -q tests/test_state_roundtrip.py'),
    ('Event log and replay', 
     {'write': ['src/cna/core/events.py', 'src/cna/tools/replay.py', 'tests/test_replay.py']}, 
     'python -m pytest -q tests/test_replay.py'),
    ('Data schemas, validators, provenance/status fields', 
     {'write': ['src/cna/data/', 'data/', 'tests/test_data_schema.py']}, 
     'python -m pytest -q tests/test_data_schema.py'),
    ('Gap register generator and first Class K queue item for R-02..R-05', 
     {'write': ['src/cna/tools/data_gaps.py', 'docs/data-gaps.md', 'tests/test_data_gaps.py']}, 
     'python -m pytest -q tests/test_data_gaps.py'),
    ('Decision-point model: Decision, Action, pending, legal_actions, apply', 
     {'write': ['src/cna/engine/', 'tests/test_engine_contract.py']}, 
     'python -m pytest -q tests/test_engine_contract.py'),
    ('Sequence-of-play state machine from section 5.2 (Appendix B as data)', 
     {'write': ['src/cna/rules/sec05_sequence.py', 'tests/test_sequence.py']}, 
     'python -m pytest -q tests/test_sequence.py'),
    ('Initiative (section 7) and Weather (section 29), using synthetic tables', 
     {'write': ['src/cna/rules/sec07_initiative.py', 'src/cna/rules/sec29_weather.py', 'tests/test_initiative_weather.py']}, 
     'python -m pytest -q tests/test_initiative_weather.py'),
    ('Hidden information: view(), sealed commitments', 
     {'write': ['src/cna/state/views.py', 'src/cna/engine/sealed.py', 'tests/test_views.py']}, 
     'python -m pytest -q tests/test_views.py'),
    ('RandomLegalPlayer, headless runner, soak tool', 
     {'write': ['src/cna/ai/', 'src/cna/ui/cli.py', 'src/cna/tools/soak.py', 'tests/test_soak.py']}, 
     'python -m cna.tools.soak --seeds 5 --turns 3 --synthetic'),
    ('Rulesets module (LAND_ABSTRACT only) and section 2.0 combination check logged as RD', 
     {'write': ['src/cna/engine/rulesets.py', 'docs/decisions/', 'tests/test_rulesets.py']}, 
     'python -m pytest -q tests/test_rulesets.py'),
]

for title, scope, oracle in tasks:
    try:
        task = k.task_create(
            title=title,
            type='implement',
            goal_ref='G-001',
            scope=scope,
            oracles=[oracle],
            evidence_required=['oracle_results', 'diff_scope', 'premise_check'],
            priority=100
        )
        print(f'Created {task.id}: {title[:60]}')
    except Exception as e:
        print(f'Failed: {e}')

print('Done')