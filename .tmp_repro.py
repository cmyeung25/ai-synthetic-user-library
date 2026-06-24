import tempfile
from pathlib import Path
import sys
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'src'))
from tests.unit.test_observer_runtime import CoverageAwareFacilitator, ObserverQualityFixture, FailingTracePersonaFixture
from ai_validation_swarm.observer.runtime import ObserverControlledInterviewRuntime
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import save_persona
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    persona = generate_personas(count=1, random_seed=83)[0]
    save_persona(persona, root / 'personas')
    runtime = ObserverControlledInterviewRuntime(
        data_dir=root / 'personas',
        session_dir=root / 'interviews',
        facilitator_provider=CoverageAwareFacilitator(),
        persona_provider=FailingTracePersonaFixture(),
        quality_provider=ObserverQualityFixture(),
        progress_writer=print,
    )
    _, session = runtime.start(persona_id=persona.profile.synthetic_user_id, research_goal='Understand trip replanning friction.', max_turns=6)
    while session.status not in {'completed','failed'}:
        session = runtime.continue_interview(session.interview_id)
    folder, session = runtime.load(session.interview_id)
    print('STATUS=', session.status)
    print('FAILED_OP=', session.failed_operation)
    print('LAST_ERROR=', session.last_error)
    print('FILES=', sorted(p.name for p in folder.iterdir()))
