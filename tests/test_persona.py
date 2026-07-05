"""ROCKY-5 persona/behavior model tests — the emotion->motion mapping and the
literal Eridian-translated dialogue syntax."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rocky" / "isaac" / "duet_tasks" / "tasks"))

from rocky import persona
import rocky_reference as ref


def test_dialogue_tags():
    # mandatory context tag appended (spec §2)
    assert persona.say("you sleep now", "question") == "you sleep now, question?"
    assert persona.say("go vote", "statement") == "go vote, statement!"


def test_dialogue_literal_lexicon():
    # drops articles/copula, substitutes descriptors ("humans" -> "leaky space blobs")
    out = persona.say("the humans are here", "statement")
    assert "leaky space blobs" in out
    assert "the" not in out.split() and "are" not in out.split()
    assert out.endswith(", statement!")


def test_jitter_scales_with_arousal():
    # distress chatters harder than a calm/dormant state (arousal -> amplitude/freq)
    t = 0.037
    calm = max(abs(persona.jitter("dormant", tt, 0)) for tt in [t, t + 0.01, t + 0.02])
    hot = max(abs(persona.jitter("distress", tt, 0)) for tt in [t, t + 0.01, t + 0.02])
    assert hot > calm


def test_voice_emotion_mapping():
    # agitation raises pitch; grave/solemn lowers it; delight triple-repeats
    assert persona.voice_params("excited")["pitch_semitones"] > 0
    assert persona.voice_params("solemn")["pitch_semitones"] <= 0
    assert persona.voice_params("excited")["repeat"] == 3
    assert persona.voice_params("neutral")["repeat"] == 1


def test_gait_mod_tempo():
    # excited is quicker than solemn
    assert persona.gait_mod("excited")["tempo_scale"] > persona.gait_mod("solemn")["tempo_scale"]


def test_poses_cover_all_joints():
    for pose in (ref.rest_pose(), ref.retract_pose(), ref.reference(0.3)):
        for i in range(5):
            assert f"leg{i}_femur_pitch" in pose and f"leg{i}_tibia_pitch" in pose


def test_dormant_tucks_limbs_up():
    # rock-dome raises the thighs (negative femur) vs the walking stance (0.6)
    assert ref.rest_pose()["leg0_femur_pitch"] < 0 < ref.STANCE_FEMUR
