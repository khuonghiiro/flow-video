"""Acting, Social, Emotion, and Expressive Action Prompts for Character Animation Pipeline.
Separated module to maintain strict modularity and prevent file bloat.
Supports 5 camera angles (0°, 45°, 90°, 135°, 180°) as 8-second continuous animations (i2v single frame).
"""

from agent.services.prompt_templates import GLOBAL_VIDEO_LOCK

# ─── 1. WAVE / VẪY TAY CHÀO ──────────────────────────────────────────
WAVE_PROMPT_TEMPLATES = {
    "0": (
        "[wave-0°] 8-second continuous animation DIGNIFIED MASCULINE HAND WAVE (0° direct front view). "
        "Character stands poised facing camera, raises right forearm to mid-chest level, and gently waves open hand in a polite greeting arc (3 natural waves). "
        "Left arm remains naturally relaxed at side. Hand then lowers smoothly back to resting position. "
        "Face remains 100% smooth blank featureless mannequin skin with STRICTLY ZERO mouth, ZERO eyes. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[wave-45°] 8-second continuous animation DIGNIFIED MASCULINE HAND WAVE (45° three-quarter view). "
        "Character stands poised at 45° angle facing bottom-left, raises visible right forearm to wave hand in a polite greeting gesture. "
        "Body stays anchored at 45° perspective. Hand lowers smoothly back to side. Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[wave-90°] 8-second continuous animation DIGNIFIED MASCULINE HAND WAVE (90° side profile). "
        "Character in pure side profile facing 9 o'clock, visible arm raises forward and waves hand gracefully in greeting. "
        "Torso and feet remain strictly anchored in 90° silhouette. Hand returns to resting pose. Blank profile, ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[wave-135°] 8-second continuous animation REAR-PERSPECTIVE HAND WAVE (135° back-left view). "
        "Character viewed from behind at 135° angle, raises left forearm and waves hand outward in a polite parting gesture visible from behind. "
        "Character remains facing diagonally away. Hand returns smoothly to rest. Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[wave-180°] 8-second continuous animation REAR VIEW FAREWELL WAVE (180° rear view). "
        "Character stands facing 100% away from camera, gently raises one hand beside shoulder to wave in a gesture visible from behind. "
        "Hand returns to resting position at side. Bilateral symmetry maintained. Strictly ZERO face, ZERO mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 2. BOW / HÀNH LỄ / CÚI CHÀO ────────────────────────────────────
BOW_PROMPT_TEMPLATES = {
    "0": (
        "[bow-0°] 8-second continuous animation TRADITIONAL MARTIAL SALUTE BOW (0° front view). "
        "Character brings hands together in front of chest in a traditional martial arts fist-and-palm salute (bao quan le: right fist placed into left open palm). "
        "Upper torso and head incline respectfully 15-20 degrees forward in dignified formal homage, hold the salute, then gracefully straighten upright, hands separating and returning smoothly to resting position at sides. "
        "Face remains 100% smooth blank featureless mannequin skin with STRICTLY ZERO mouth, ZERO lips, ZERO facial features. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[bow-45°] 8-second continuous animation TRADITIONAL MARTIAL SALUTE BOW (45° three-quarter view). "
        "Character clasps fist and palm together at chest and performs a dignified 20-degree forward bow along the 45-degree axis, then straightens back to initial poised standing posture. "
        "Face remains completely smooth and blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[bow-90°] 8-second continuous animation TRADITIONAL MARTIAL SALUTE BOW (90° side profile). "
        "Character in pure side profile raises cupped hands to chest and gracefully bows upper torso forward in formal martial homage, then smoothly returns to upright standing pose. "
        "Strictly ZERO mouth, smooth blank featureless profile. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[bow-135°] 8-second continuous animation TRADITIONAL MARTIAL SALUTE BOW (135° back-left view). "
        "Character viewed from behind at 135° angle, shoulders and back incline forward gently in a formal bow, then rise smoothly back to upright posture. "
        "Character faces diagonally away. Zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[bow-180°] 8-second continuous animation TRADITIONAL MARTIAL SALUTE BOW (180° rear view). "
        "Character facing directly away from camera, shoulders incline forward in formal respectful bow, spine straightens smoothly back to vertical poised stance. "
        "Bilateral rear symmetry, strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 3. COVER MOUTH LAUGH / CHE MIỆNG CƯỜI ────────────────────────────
COVER_MOUTH_LAUGH_PROMPT_TEMPLATES = {
    "0": (
        "[cover-mouth-0°] 8-second continuous animation POLITE AMUSED CHUCKLE GESTURE (0° front view). "
        "Character brings hand and wide hanging sleeve up in front of lower chin area in an amused chuckling gesture; broad shoulders vibrate gently with subtle quiet amusement, then hand lowers smoothly back to side. "
        "FACE LOCK: Facial surface remains 100% completely blank, smooth, featureless anime skin with ABSOLUTELY ZERO mouth, ZERO lips, ZERO teeth, ZERO smile drawn. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[cover-mouth-45°] 8-second continuous animation POLITE AMUSED CHUCKLE GESTURE (45° three-quarter view). "
        "Character at 45° angle raises hand with flowing sleeve near lower chin in an amused chuckle; gentle rhythmic shoulder vibration, then hand lowers back to rest. "
        "Face remains completely smooth and blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[cover-mouth-90°] 8-second continuous animation POLITE AMUSED CHUCKLE GESTURE (90° side profile). "
        "Character in side profile raises hand in front of chin silhouette in quiet amusement; subtle soft upper body vibration, then hand returns naturally to side. "
        "Blank featureless profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[cover-mouth-135°] 8-second continuous animation QUIET AMUSEMENT IN PERSPECTIVE (135° back-left view). "
        "Character viewed from behind at 135° angle remains 100% facing AWAY into screen depth (8 o'clock direction). "
        "Head tilts slightly, shoulders bounce softly with quiet restrained amusement, visible forearm rises slightly near jawline silhouette, then relaxes back to poised stillness. "
        "STRICTLY FORBIDDEN to turn head toward viewer, STRICTLY FORBIDDEN to show face. Only back of head and hair visible throughout. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[cover-mouth-180°] 8-second continuous animation REAR VIEW SUPPRESSED CHUCKLE (180° rear view). "
        "Character faces 100% directly away from camera (12 o'clock direction). "
        "Viewed from behind, shoulders shake gently with quiet restrained amusement, robes rustle softly, then posture settles back to calm vertical symmetry. "
        "STRICTLY FORBIDDEN to turn head around or look back. Only back of head, high ponytail, and back of robes visible throughout. ABSOLUTELY ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 4. TALKING / NÓI CHUYỆN & DIỄN GIẢI ──────────────────────────────
TALKING_PROMPT_TEMPLATES = {
    "0": (
        "[talking-0°] 8-second continuous animation CONVERSATIONAL DIALOGUE GESTURES (0° front view). "
        "Character communicates through natural, dignified masculine gestures: right hand and forearm raise to waist level gesturing politely with open palm to emphasize ideas in rhythmic cadence, while head nods and tilts naturally in conversational rhythm. Hand lowers back to side. "
        "STRICTLY ZERO MOUTH: Face is 100% smooth, blank, featureless mannequin skin with ABSOLUTELY ZERO mouth, ZERO lips, ZERO teeth, ZERO speech opening. Dialogue is expressed purely through body gestures. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[talking-45°] 8-second continuous animation CONVERSATIONAL DIALOGUE GESTURES (45° three-quarter view). "
        "Character gestures expressively at 45° angle, natural subtle head tilts and gentle communicative hand gestures explaining a point, then settling back to resting stance. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[talking-90°] 8-second continuous animation CONVERSATIONAL DIALOGUE GESTURES (90° side profile). "
        "Character in side profile gestures with subtle natural head tilt and rhythmic hand emphasis in front of chest, then rests arm back down. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[talking-135°] 8-second continuous animation CONVERSATIONAL DIALOGUE GESTURES (135° back-left view). "
        "Character viewed from behind at 135° angle, head tilts naturally in conversation, visible left hand gestures outward in dialogue rhythm, returning to rest. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[talking-180°] 8-second continuous animation CONVERSATIONAL DIALOGUE GESTURES (180° rear view). "
        "Character facing away, subtle head cadence and elbow/forearm conversational movement visible from behind, returning smoothly to symmetrical resting posture. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 5. THINK / SUY NGHĨ / ĐĂM CHIÊU ──────────────────────────────────
THINK_PROMPT_TEMPLATES = {
    "0": (
        "[think-0°] 8-second continuous animation PENSIVE CONTEMPLATION / HAND TO CHIN (0° front view). "
        "Character brings right hand up to lightly touch under chin in deep strategic contemplation, head tilts slightly in thoughtful reflection, holds posture, then gently lowers hand back down to side. "
        "Face remains 100% smooth blank featureless mannequin skin with ZERO mouth, ZERO lips, ZERO eyes. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[think-45°] 8-second continuous animation PENSIVE CONTEMPLATION (45° three-quarter view). "
        "Character at 45° angle raises hand to chin, tilts head pensively pondering, then smoothly returns to initial standing pose. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[think-90°] 8-second continuous animation PENSIVE CONTEMPLATION (90° side profile). "
        "Character in side profile touches chin with fingers in thoughtful pondering gesture, then returns arm down to resting pose. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[think-135°] 8-second continuous animation PENSIVE CONTEMPLATION (135° back-left view). "
        "Character viewed from behind at 135° angle, elbow bends as hand reaches chin in contemplation, head tilts thoughtfully, then settles back. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[think-180°] 8-second continuous animation PENSIVE CONTEMPLATION (180° rear view). "
        "Character facing away, head tilts slightly with elbow raised in pondering gesture, then posture relaxes back to vertical stillness. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 6. SURPRISE / KINH NGẠC / BẤT NGỜ ───────────────────────────────
SURPRISE_PROMPT_TEMPLATES = {
    "0": (
        "[surprise-0°] 8-second continuous animation MASCULINE MARTIAL ALERT SURPRISE (0° front view). "
        "Character reacts with sharp, disciplined masculine martial vigilance: body tenses abruptly, draws torso back half a step into a grounded defensive alert posture, hands raise into guarded fists at waist/midriff level, broad shoulders square with sharp alert awareness. "
        "STRICTLY ZERO feminine gasping, STRICTLY ZERO covering mouth with hands, STRICTLY ZERO delicate recoiling. "
        "Face remains 100% smooth blank featureless mannequin skin with ZERO mouth, ZERO eyes. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[surprise-45°] 8-second continuous animation MASCULINE MARTIAL ALERT SURPRISE (45° three-quarter view). "
        "Character at 45° angle reacts in sharp martial surprise, drawing back into alert guarded stance with fists poised, then recovers calm composed balance. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[surprise-90°] 8-second continuous animation MASCULINE MARTIAL ALERT SURPRISE (90° side profile). "
        "Character in side profile recoils half a step into sharp defensive guard stance, body braced with alert martial poise, then relaxes back to initial stance. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[surprise-135°] 8-second continuous animation MASCULINE MARTIAL ALERT SURPRISE (135° back-left view). "
        "Character viewed from behind at 135° angle tenses shoulders and braces into alert martial stance, then regains calm poised posture. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[surprise-180°] 8-second continuous animation MASCULINE MARTIAL ALERT SURPRISE (180° rear view). "
        "Character facing away tenses broad shoulders and shifts into alert combat stance, then relaxes back to neutral symmetrical stillness. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 7. NOD / GẬT ĐẦU ĐỒNG Ý ─────────────────────────────────────────
NOD_PROMPT_TEMPLATES = {
    "0": (
        "[nod-0°] 8-second continuous animation DIGNIFIED AFFIRMATIVE HEAD NOD (0° front view). "
        "IMMOBILE BODY LOCK: Shoulders, chest, torso, arms, hands, hips, and grounded feet remain 100% FROZEN, RIGID, AND MOTIONLESS. Both arms hang completely still at sides. "
        "ONLY HEAD NODDING: Character gently and affirmatively nods head down and up (3-4 slow, dignified nods of agreement), with the long ponytail hair softly swaying in momentum with each nod. "
        "Robes and sleeves have only subtle whisper-breeze micro-sway. "
        "Face remains completely smooth blank featureless mannequin skin with STRICTLY ZERO mouth, ZERO eyes. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[nod-45°] 8-second continuous animation DIGNIFIED AFFIRMATIVE HEAD NOD (45° three-quarter view). "
        "IMMOBILE BODY LOCK: Body anchored rock-steady, arms frozen at sides. "
        "ONLY HEAD NODDING: Character at 45° angle nods head gently down and up 3 times in dignified agreement, ponytail hair swaying in momentum, head returning to neutral level. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[nod-90°] 8-second continuous animation DIGNIFIED AFFIRMATIVE HEAD NOD (90° side profile). "
        "IMMOBILE BODY LOCK: Torso, arm, and feet remain 100% frozen in pure side profile. "
        "ONLY HEAD NODDING: Head nods clearly down and up 3 times in calm approval, hair swaying softly with motion. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[nod-135°] 8-second continuous animation DIGNIFIED AFFIRMATIVE HEAD NOD (135° back-left view). "
        "IMMOBILE BODY LOCK: Body anchored still viewed from behind at 135° angle. "
        "ONLY HEAD NODDING: Head inclines down and up in 3 gentle affirmative nods, long hair oscillating softly with cadence. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[nod-180°] 8-second continuous animation DIGNIFIED AFFIRMATIVE HEAD NOD (180° rear view). "
        "IMMOBILE BODY LOCK: Back of torso, arms, and heels remain 100% frozen and rock-steady with bilateral symmetry. "
        "ONLY HEAD NODDING: Character facing directly away nods head down and up in clear agreement, high ponytail hair swaying rhythmically with head motion. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 8. CHEER / REO HÒ / ĂN MỪNG ─────────────────────────────────────
CHEER_PROMPT_TEMPLATES = {
    "0": (
        "[cheer-0°] 8-second continuous animation MASCULINE TRIUMPHANT VICTORY CELEBRATION (0° front view). "
        "Character performs an energetic masculine victory celebration: raising both clenched fists firmly to chest/shoulder level in triumphant athletic momentum, radiating victory, then smoothly lowers arms back down to poised standing stance. "
        "Face remains 100% smooth blank featureless mannequin skin with ZERO mouth, ZERO lips. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[cheer-45°] 8-second continuous animation MASCULINE TRIUMPHANT VICTORY CELEBRATION (45° three-quarter view). "
        "Character at 45° angle pumps clenched fists firmly with athletic victory energy, then lowers arms smoothly back to resting posture. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[cheer-90°] 8-second continuous animation MASCULINE TRIUMPHANT VICTORY CELEBRATION (90° side profile). "
        "Character in side profile raises arms in energetic cheer of victory, then returns smoothly to initial standing poise. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[cheer-135°] 8-second continuous animation MASCULINE TRIUMPHANT VICTORY CELEBRATION (135° back-left view). "
        "Character viewed from behind at 135° angle raises fists in energetic triumph, then lowers hands back to sides. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[cheer-180°] 8-second continuous animation MASCULINE TRIUMPHANT VICTORY CELEBRATION (180° rear view). "
        "Character facing away raises both arms in joyful triumph, robe sleeves fluttering happily, returning to symmetrical resting stance. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 9. SAD / BUỒN BÃ / THỞ DÀI ──────────────────────────────────────
SAD_PROMPT_TEMPLATES = {
    "0": (
        "[sad-0°] 8-second continuous animation DEJECTED MASCULINE SIGH & POSTURE SLUMP (0° front view). "
        "Character exhibits dejection purely through slumped body posture: head lowers slowly looking downward, broad shoulders drop and slump in a heavy dejected body sigh, arms hang limply down at sides. After a moment of solemn stillness, character slowly straightens head back to composed upright posture. "
        "FACE LOCK: Facial surface remains 100% completely blank, smooth, featureless anime skin with STRICTLY ZERO mouth, ZERO lips, ZERO frown lines, ZERO facial openings. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[sad-45°] 8-second continuous animation DEJECTED MASCULINE SIGH (45° three-quarter view). "
        "Character at 45° angle droops head and shoulders in a sorrowful body sigh, then slowly composes upright posture. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[sad-90°] 8-second continuous animation DEJECTED MASCULINE SIGH (90° side profile). "
        "Character in side profile bows head down sorrowfully in a heavy breath, then straightens back to standing pose. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[sad-135°] 8-second continuous animation DEJECTED MASCULINE SIGH (135° back-left view). "
        "Character viewed from behind at 135° angle slumps shoulders in sorrowful dejection, then slowly stands tall again. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[sad-180°] 8-second continuous animation DEJECTED MASCULINE SIGH (180° rear view). "
        "Character facing away drops head and slumps back dejectedly in a body sigh, then rises back to symmetrical poise. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 10. ANGRY / TỨC GIẬN / DẬM CHÂN DỖI ────────────────────────────
ANGRY_PROMPT_TEMPLATES = {
    "0": (
        "[angry-0°] 8-second continuous animation MASCULINE RESTRAINED ANGER & TENSE STANCE (0° front view). "
        "Character exhibits masculine frustration through tense physical posture: chest puffs rigidly upright, both hands clench tightly into fists at sides with tensed knuckles, broad shoulders stiffen, and head turns sharply to one side in exasperated displeasure, foot rooted firmly. "
        "FACE LOCK: Face remains 100% completely blank, smooth, featureless mannequin skin with STRICTLY ZERO mouth, ZERO scowl, ZERO teeth, ZERO grimace. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[angry-45°] 8-second continuous animation MASCULINE RESTRAINED ANGER (45° three-quarter view). "
        "Character at 45° angle tenses fists and turns head sharply in angry displeasure, then relaxes posture back to sides. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[angry-90°] 8-second continuous animation MASCULINE RESTRAINED ANGER (90° side profile). "
        "Character in side profile clenches fists tightly and jerks chin upward in tense frustration, then settles back down. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[angry-135°] 8-second continuous animation MASCULINE RESTRAINED ANGER (135° back-left view). "
        "Character viewed from behind turns away indignantly with tense shoulders and clenched fists, then returns to poised posture. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[angry-180°] 8-second continuous animation MASCULINE RESTRAINED ANGER (180° rear view). "
        "Character facing away tenses shoulders and stamps foot firmly in anger, elbows tensing, returning to symmetrical stillness. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── 11. HURT / TRÚNG ĐÒN / LẢO ĐẢO ──────────────────────────────────
HURT_PROMPT_TEMPLATES = {
    "0": (
        "[hurt-0°] 8-second continuous animation COMBAT IMPACT RECOIL & RECOVERY (0° front view). "
        "Character reels backward from an impact force: torso jolts back, one hand braces defensively across torso, staggers back half a step, then firmly plants feet and recovers poised combat stance. "
        "Face remains 100% smooth blank featureless mannequin skin with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[hurt-45°] 8-second continuous animation COMBAT IMPACT RECOIL & RECOVERY (45° three-quarter view). "
        "Character reels back along the 45° line from impact, braces balance, then steps back firmly into initial standing posture. "
        "Face remains completely blank with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[hurt-90°] 8-second continuous animation COMBAT IMPACT RECOIL (90° side profile). "
        "Character in side profile staggers back under impact, clutches chest defensively, then regains upright balance. "
        "Blank profile with ZERO mouth. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[hurt-135°] 8-second continuous animation COMBAT IMPACT RECOIL (135° back-left view). "
        "Character viewed from behind jolts forward-left from impact, stumbles, then regains poised stance. "
        "Character faces away, zero face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[hurt-180°] 8-second continuous animation COMBAT IMPACT RECOIL (180° rear view). "
        "Character facing away recoils and recovers balanced footing cleanly, robes settling back into stillness. "
        "Strictly ZERO face or mouth visible. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

ACTING_ACTION_TEMPLATES = {
    "wave": WAVE_PROMPT_TEMPLATES,
    "bow": BOW_PROMPT_TEMPLATES,
    "cover_mouth_laugh": COVER_MOUTH_LAUGH_PROMPT_TEMPLATES,
    "talking": TALKING_PROMPT_TEMPLATES,
    "think": THINK_PROMPT_TEMPLATES,
    "surprise": SURPRISE_PROMPT_TEMPLATES,
    "nod": NOD_PROMPT_TEMPLATES,
    "cheer": CHEER_PROMPT_TEMPLATES,
    "sad": SAD_PROMPT_TEMPLATES,
    "angry": ANGRY_PROMPT_TEMPLATES,
    "hurt": HURT_PROMPT_TEMPLATES,
}
