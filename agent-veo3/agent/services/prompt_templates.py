"""Standard Prompt Templates for Tab 4 Skill Tree Pipeline.

Pipeline execution order:
  Stage 1: Generate Master Base 0° (text_to_image)
  Stage 2: Generate 4 remaining angles (45°, 90°, 135°, 180°) using 0° as ref
  Stage 3: Generate action videos per angle (walk, idle, run, attack, etc.)
           Each action has 5 sub-prompts (one per angle), using that angle's
           reference image as start+end frame for 4s seamless loop.
"""
import re

DEFAULT_CUSTOMIZER_VALUES = {
    "characterName": "Lâm Tiêu (Lin Xiao)",
    "style": "2D Xianxia/Fantasy anime chibi style, bold clean linework, flat cel-shaded coloring",
    "gender": "female",
    "age": "young adult (18-20)",
    "hairStyleColor": "Long silky platinum white hair with delicate silver lotus hairpin and silk ribbons",
    "outfitDescription": "Xianxia flowing silk daoist robes with wide sleeves, floating ribbons, flat cloth lotus shoes with zero heels",
    "primaryColor": "Pure White & Soft Pale Cyan",
    "accentColor": "Soft Silver & Lilac Purple",
    "skinTone": "Fair natural peach skin tone seamlessly matching neck and hands",
    "weaponType": "None (empty hands, pure martial arts)",
    "spellElement": "None",
    "chromaBgHex": "#00FF00",
}

# ─── Stage 1+2: 5 Body Angles Prompts ─────────────────────────
# Stage 1: angle "0" (text_to_image, no reference)
# Stage 2: angles "45","90","135","180" (image_to_image, ref = 0° image)

ANGLE_PROMPT_TEMPLATES = {
    "0": (
        "MASTER CHARACTER DESIGN — 2D XIANXIA CHIBI — 0° DIRECT FRONT VIEW\n"
        "CRITICAL ANATOMICAL PROPORTION & SCALE LOCK: Mature stylized semi-chibi anime sprite proportion (~4.8 to 5.0 heads tall, full-body vertical height occupies 85-88% canvas height). "
        "Head size is proportionate and balanced with shoulders; strictly ZERO oversized giant chibi head, ZERO shrunken tiny torso, ZERO bobblehead deformity. "
        "Torso and limbs have clear anatomical structure, slender waist, and long graceful legs grounded on floor plane.\n"
        "CAMERA & POSE: Character MUST face 100% DIRECTLY forward at camera (strict 0.0° front view). "
        "Head facing 100% straight forward towards viewer. NO head turn, NO head tilt, NO 3/4 angle. "
        "Symmetrical standing pose, torso upright, both shoulders perfectly horizontal and level, both arms relaxed at sides, empty hands. "
        "Both feet planted parallel and pointing directly forward towards viewer (12 o'clock). "
        "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and hems hang straight down naturally under calm gravity. Strictly NO wind blowing, NO billowing fabric, NO flapping hems, NO flying coat tails. "
        "CRITICAL — BLANK FACELESS HEAD & UNIFORM SKIN TONE: Completely BLANK, SMOOTH, FEATURELESS face surface. "
        "NO eyes, NO eyebrows, NO nose, NO mouth. Facial skin color MUST seamlessly and uniformly match the neck, ears, and hands ({skinTone}) with 100% consistency across all angles. "
        "Clean flat cel-shaded anime skin, strictly zero facial features. "
        "CRITICAL — ZERO WEAPONS OR PROPS: The character carries NO weapons, NO swords on back or waist, NO musical instruments, NO props. Hands are empty and resting naturally. "
        "FABRIC TEXTURE & LIGHTING: Strictly flat matte fabric texture, zero metallic sheen, zero silvery gloss, zero specular reflections, zero satin sheen. Clean natural cel-shading, harmonious elegant palette. Strictly ZERO neon lighting, ZERO harsh glowing rim lights. "
        "CHARACTER: Genre: {style}. Age: {age}. Gender: {gender}. "
        "HAIR: {hairStyleColor}. OUTFIT: {outfitDescription}. "
        "Colors: {primaryColor}. Accents: {accentColor}. Skin: {skinTone}. "
        "STYLE: Pure flat 2D anime/chibi illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green {chromaBgHex}. Centered, full body visible."
    ),
    "45": (
        "ROTATE THE CHARACTER 45 DEGREES — THREE-QUARTER VIEW — 2D Xianxia anime chibi sprite.\n"
        "FIRST AND MOST IMPORTANT INSTRUCTION: ROTATE the character's ENTIRE BODY 45 degrees to face 10 o'clock (upper-left diagonal). "
        "The character is NO LONGER facing the camera. The character is TURNED AWAY from the viewer by 45 degrees. "
        "THIS IS NOT A FRONT VIEW. STRICTLY FORBIDDEN to keep the body facing forward. STRICTLY FORBIDDEN to keep symmetrical front-facing pose.\n"
        "VISIBLE ROTATION PROOF — These elements MUST be visible to confirm 45-degree rotation: "
        "(1) The LEFT SHOULDER is pushed FORWARD toward the viewer, the RIGHT SHOULDER recedes BACKWARD behind the body. "
        "(2) The collar seam and robe crossover are shifted to the LEFT side of the torso, NOT centered. "
        "(3) The waist medallion/belt buckle is visible on the LEFT hip area, NOT in the center of the body. "
        "(4) The LEFT foot is stepped FORWARD, the RIGHT foot is stepped BACK in depth. Both feet point towards 10 o'clock. "
        "(5) The viewer can see part of the LEFT side of the character's body and a hint of the back of the RIGHT shoulder. "
        "If the collar, belt, and feet are all centered and symmetrical, the image is WRONG and must be rejected.\n"
        "CRITICAL SCALE & STATURE LOCK: Maintain the EXACT SAME TALL, SLENDER, ATHLETIC HEIGHT AND FULL-BODY PROPORTIONS as Reference 0° (~88% vertical canvas height, ~4.8-5.0 heads tall). "
        "NATURAL FABRIC DRAPE UNDER GRAVITY: Robe hems and sleeves hang straight down naturally under calm gravity. Strictly NO wind blowing, NO billowing fabric. "
        "CRITICAL — BLANK FACELESS HEAD: Smooth blank featureless face (NO eyes, NO nose, NO mouth). Skin matches neck ({skinTone}). "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO weapons, NO swords, NO props. Both hands empty. "
        "LIGHTING: Natural clean flat cel-shading, strictly ZERO neon lighting. "
        "IDENTITY LOCK: Match reference character (hairstyle {hairStyleColor}, outfit {outfitDescription}, colors {primaryColor}, accents {accentColor}). "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green {chromaBgHex}. Centered, full body visible."
    ),
    "90": (
        "PURE 90-DEGREE SIDE PROFILE VIEW (FACING LEFT 9 O'CLOCK) — 2D Xianxia anime chibi sprite.\n"
        "MANDATORY 90-DEGREE SIDE PROFILE ROTATION: The character stands in a STRICT 90-DEGREE SIDE PROFILE facing directly left towards 9 o'clock. "
        "ONLY THE LEFT PROFILE is visible. The character's left arm and left shoulder face the viewer; the right shoulder and right arm are 100% COMPLETELY HIDDEN AND OCCLUDED behind the torso. "
        "STRICTLY FORBIDDEN to face the camera. STRICTLY FORBIDDEN to show front chest or three-quarter angle. Narrow vertical side profile silhouette. "
        "Both feet point directly towards the left edge of the screen (9 o'clock). "
        "Head is in pure 90-degree side profile showing one ear, side jawline, and nose contour. "
        "MULTI-REFERENCE INTERPOLATION: Interpolate between Reference 0° (front view) and Reference 45° (three-quarter view) for complete continuity of colors, robes, and layered sash. "
        "CRITICAL SCALE & STATURE LOCK: Maintain the EXACT SAME TALL, SLENDER, ATHLETIC HEIGHT AND FULL-BODY PROPORTIONS as References [0°, 45°] (~88% vertical canvas height, ~4.8-5.0 heads tall). "
        "STRICTLY ZERO SHRINKING, ZERO ZOOM-OUT, ZERO STATURE COMPRESSION. Identical camera framing and tall stature. "
        "PRESERVE 100% INTRICATE DETAILS: Preserve every intricate detail from references: sleeve embroidery, coat hem patterns, layered waist belt structure. "
        "NATURAL FABRIC DRAPE UNDER GRAVITY: The robes, sleeves, and coat hang straight down vertically along the body under calm gravity. Strictly NO wind blowing, NO billowing fabric, NO coat tails flying backward. "
        "CRITICAL — BLANK FACELESS HEAD & UNIFORM NATURAL SKIN: Smooth blank featureless face in pure side profile silhouette (NO eyes/nose/mouth). "
        "Facial skin color seamlessly and uniformly matches neck ({skinTone}). Strictly ZERO shiny white mask. "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO weapons, NO swords on back or waist, NO props. Empty hands. "
        "LIGHTING: Natural flat cel-shading, strictly ZERO neon lighting, ZERO harsh glowing rim reflections. "
        "STYLE: Pure flat 2D anime chibi illustration, bold clean linework, flat cel-shaded colors. "
        "BACKGROUND: Solid chroma-key green {chromaBgHex}. Centered, full body visible."
    ),
    "135": (
        "2D XIANXIA ANIME CHIBI CHARACTER SPRITE — TRUE 135-DEGREE BACK-LEFT THREE-QUARTER ANGLE.\n"
        "CRITICAL POSE COPY FROM REFERENCE 1 (MANNEQUIN 135° POSE GUIDE):\n"
        "The character's entire body stance MUST strictly replicate the exact 135-degree posture in Reference 1:\n"
        "- Torso and spine are rotated at a 135-degree angle (facing diagonally away to the 8 o'clock direction).\n"
        "- Left shoulder, left arm, and left hip are prominent and close in the foreground.\n"
        "- Right shoulder and right arm are further away in depth, partially occluded by the angled torso.\n"
        "- FEET AND LEGS POSE: Strictly copy Reference 1. The left foot is rotated into profile facing left (9 o'clock). The right foot is angled diagonally away into depth. Both legs are clearly angled in three-quarter perspective.\n"
        "- STRICTLY FORBIDDEN: Symmetrical 180-degree rear-facing body, symmetrical shoulders, or symmetrical feet. The torso and feet MUST NOT be facing 180 degrees.\n"
        "COSTUME & HAIR IDENTITY (FROM REFERENCE 2):\n"
        "- Character wears the outfit ({outfitDescription}) with colors ({primaryColor}) and accents ({accentColor}).\n"
        "- Hairstyle: {hairStyleColor} viewed from the 135-degree rear-left angle.\n"
        "- Waist belt rear rule: {waistRearMotionLock} (viewed at 45-degree angled offset).\n"
        "- Footwear: flat cloth daoist shoes/boots (strictly flat, zero heels).\n"
        "- Face/Head: Side profile of fair natural skin ({skinTone}) cheek, jawline, delicate ear, and sideburns viewed from behind-left.\n"
        "SCALE & FABRIC PHYSICS:\n"
        "- Maintain mature semi-chibi anime sprite proportion (~4.8-5.0 heads tall, occupies 85-88% canvas height).\n"
        "- Natural fabric drape under calm gravity, strictly zero fake wind blowing.\n"
        "STYLE & BG:\n"
        "- Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. Genre: {style}.\n"
        "- Solid chroma-key green {chromaBgHex} background. Full body centered from head to feet."
    ),
    "180": (
        "ROTATE CHARACTER 180° — PERFECT DIRECT REAR VIEW — 2D XIANXIA CHIBI\n"
        "CRITICAL ANATOMICAL PROPORTION & SCALE LOCK: Maintain the EXACT SAME TALL, SLENDER, ATHLETIC STATURE AND BODY PROPORTION (~4.8 to 5.0 heads tall, 85-88% canvas height) as Reference 0°. "
        "Head size MUST remain small, compact, and perfectly proportionate to broad shoulders; strictly ZERO oversized giant head, ZERO bobblehead deformity, ZERO shrunken tiny torso. "
        "Torso length, broad shoulder width, waist level, and long straight legs MUST match Reference 0° with 100% anatomical fidelity.\n"
        "SINGLE MASTER REFERENCE: Use the 0° front-view master reference image as ABSOLUTE IDENTITY SOURCE to reconstruct the complete back view. "
        "CRITICAL ROTATION: Character faces 100% DIRECTLY AWAY from camera (strict 180.0° rear view). "
        "Full back of hairstyle, ponytail/topknot bun, and hair ornaments symmetrically displayed, perfectly mirroring the crown and ornaments from 0°. "
        "Spine vertical, full back of robes facing camera with bilateral symmetry. "
        "WAIST BELT REAR: For male characters: strictly smooth continuous flat belt band around back with ZERO bow, ZERO ribbon knot. For female characters: follow the character's outfit description. "
        "NATURAL FABRIC DRAPE: Hems and sleeves hang straight down naturally under calm gravity, strictly NO wind blowing, NO billowing coat tails. "
        "Both legs straight and symmetrical, heels facing camera, feet pointing away in flat cloth shoes. "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO swords on back, NO weapons, NO props. Pure clean robe back. "
        "LIGHTING: Natural clean flat colors, strictly ZERO neon lighting. "
        "IDENTITY LOCK: Match Reference 0° hair color, proportions, costume rear details. Skin tone {skinTone}. "
        "STYLE: Pure flat 2D anime illustration, bold linework, flat colors. "
        "BACKGROUND: Solid chroma-key green {chromaBgHex}. Centered, full body visible."
    ),
}

# ─── Stage 3: Action Video Prompts (4s Seamless Loop) ──────────
# Each action has 5 angle variants. The pipeline uses the angle's
# reference image as BOTH start frame AND end frame for seamless loop.

FACELESS_MANNEQUIN_LOCK = (
    "CRITICAL ZERO FACIAL FEATURES MANNEQUIN LOCK: The character's face is a completely 100% BLANK, SMOOTH, FEATURELESS OVAL MANNEQUIN SURFACE. "
    "ABSOLUTELY ZERO eyes, ZERO eyebrows, ZERO nose, ZERO mouth, ZERO lips, ZERO teeth, ZERO smile, ZERO frown, ZERO facial lines, ZERO facial openings. "
    "The entire face is pure flat continuous cel-shaded anime skin seamlessly matching neck ({skinTone}) with zero details. "
    "STRICTLY FORBIDDEN to render any mouth, lips, teeth, or facial expressions under any circumstances, even during talking, laughing, crying, or emoting. "
    "At 135° and 180° rear perspectives, the character faces strictly AWAY from camera, showing ONLY the back of the head, hair, and neck, with ABSOLUTELY ZERO face visible."
)

ZERO_EFFECTS_LOCK = (
    "SOLID GREEN SCREEN: Background is 100% clean, pure, flat, solid chroma key green {chromaBgHex} screen with zero background objects, zero floating particles, zero glowing aura. Completely plain green background."
)

HAIR_STABILITY_LOCK = (
    "CRITICAL HAIR NATURAL STABILITY LOCK: Long silky hair maintains constant length, constant volume, and constant thickness throughout the animation. "
    "Hair strands remain naturally rooted to the scalp, swaying gently and softly following body motion under natural gravity."
)

LOCOMOTION_ARM_LOCK = (
    "MASCULINE STRIDE & ARM CARRIAGE LOCK: Confident, athletic, masculine forward stride. "
    "Arms hang down naturally at sides and swing straight forward and back in a disciplined, narrow pendulum arc strictly close to torso and hips. "
    "STRICTLY ZERO outward arm flaring, STRICTLY ZERO spreading arms out to sides, STRICTLY ZERO splayed elbows, "
    "STRICTLY ZERO delicate mincing steps, STRICTLY ZERO feminine hip swaying. "
    "Broad shoulders held square and level, upright stable core, grounded masculine strides in place."
)

MOTION_ANTI_GLITCH_LOCK = (
    "CRITICAL MOTION STABILITY CONSTRAINTS (STRICT ANTI-GLITCH LOCK): "
    "Movement is natural, authentic, and dignified with ZERO exaggerated erratic deformation. "
    "STRICTLY ZERO wild body flailing, ZERO dancing, ZERO erratic twitching. "
    "Hair is realistically rooted to the scalp with soft organic secondary motion following body inertia and breeze. "
    "Feet remain grounded, STRICTLY ZERO hopping, ZERO bouncing up and down, ZERO airborne jumping, ZERO floating, ZERO lateral sliding. "
    "Torso and spine maintain stable posture with ZERO erratic bobbing or rubbery limb distortion. "
    "STRICTLY ZERO weapons, swords, or props. STRICTLY ZERO neon glow, neon reflections, or glowing edges."
)

GLOBAL_VIDEO_LOCK = f"{FACELESS_MANNEQUIN_LOCK} {ZERO_EFFECTS_LOCK} {HAIR_STABILITY_LOCK} {MOTION_ANTI_GLITCH_LOCK}"

ARCHETYPE_STYLES = {
    "young_male": {
        "label": "YOUTH/YOUNG ADULT",
        "walk_desc": "with a confident, athletic, masculine upright posture and steady decisive forward cadence. Left foot steps forward alternating with right foot in clean stride rhythm on floor plane. Arms swing straight forward and backward in a disciplined, narrow masculine cadence strictly parallel and close to hips. Broad shoulders level and rock-steady, zero body twisting, zero outward elbow flaring.",
        "run_desc": "with dynamic athletic masculine momentum in place on a fixed spot. Body has a slight forward athletic lean, elbows bent at 90 degrees pumping forward and backward rhythmically strictly close to ribcage with zero outward flaring. Fast decisive strides with clean knee lifts on floor plane. Hair and robes stream back with speed.",
    },
    "maiden": {
        "label": "YOUNG MAIDEN/TEEN GIRL",
        "walk_desc": "with a graceful, delicate, light-footed, and demure cadence. Steps are petite, gentle, and light on the floor plane. Hands are held softly near waist or dress with minimal, modest subtle sway. Torso upright and poised, long hair and dress ribbons floating softly.",
        "run_desc": "with a graceful light trot and petite brisk footsteps. Hands held lightly near waist for balance, short quick light strides low to ground. Hair and silk ribbons streaming softly with motion.",
    },
    "mature_woman": {
        "label": "MATURE WOMAN/LADY",
        "walk_desc": "with an elegant, poised, majestic, and dignified stride. Upright posture, level shoulders, composed graceful arm carriage close to sides. Hips and robes move with natural organic grace along the floor plane. Head and upper body rock-steady.",
        "run_desc": "with a purposeful, dignified, and athletic graceful brisk run. Upright stable core, arms bent at elbows pumping smoothly along ribs. Clean rhythmic strides, elegant momentum.",
    },
    "child": {
        "label": "CHILD/LITTLE KID",
        "walk_desc": "with playful, innocent, cheerful child steps. Short quick pitter-patter footsteps on floor plane. Arms swing naturally in innocent small arcs close to body. Head held high with curious cheerful energy, fully grounded balance.",
        "run_desc": "with an energetic scampering sprint. Quick pitter-patter footsteps low to ground, arms pumping close to body with playful cheerful momentum, body leaning slightly forward.",
    },
    "elderly": {
        "label": "ELDERLY/OLD MASTER",
        "walk_desc": "with a slow, deliberate, measured, and cautious pace. Body has a subtle weathered, slightly stooped posture of an elder artisan. Steps are short, grounded, and gentle. Arms hang relaxed close to sides or resting on a staff, minimal subtle pendulum motion strictly below waist.",
        "run_desc": "with a hurried shuffling jog in place. Body leans forward cautiously with lower center of gravity. Short quick footsteps staying low to floor plane (low stride height, NO jumping). Arms held close to midriff for balance with minimal compact motion.",
    },
}


def build_walk_templates(archetype: str) -> dict:
    info = ARCHETYPE_STYLES.get(archetype, ARCHETYPE_STYLES["young_male"])
    label = info["label"]
    desc = info["walk_desc"]
    return {
        "0": (
            f"[walk-0°] 4-second seamless loop 0° DIRECT FRONT VIEW WALK CYCLE ({label}). "
            f"Character walks in place facing DIRECTLY at camera {desc} "
            f"{LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "45": (
            f"[walk-45°] 4-second seamless loop 45° THREE-QUARTER WALK CYCLE ({label}). "
            f"Character walks in place at 45° angle facing bottom-left {desc} "
            f"STRIDE DIRECTION LOCK: Legs, feet, and stride cycle track strictly forward along the 45-degree diagonal trajectory aligned with torso. Strictly ZERO sideways crab-walking or lateral sliding. No body turning. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "90": (
            f"[walk-90°] 4-second seamless loop 90° SIDE PROFILE WALK CYCLE ({label}). "
            f"Character walks in place in strict left side profile (9 o'clock) {desc} "
            f"Body stays strictly 90° side silhouette. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "135": (
            f"[walk-135°] 4-second seamless loop 135° BACK-LEFT WALK CYCLE ({label}). "
            f"Character walks in place viewed from behind at 135° angle {desc} "
            f"STRIDE DIRECTION LOCK: Legs and feet step strictly along the 135-degree diagonal axis aligned with body orientation. Strictly ZERO crab-walking. Body stays at 135° orientation. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "180": (
            f"[walk-180°] 4-second seamless loop 180° DIRECT REAR VIEW WALK CYCLE ({label}). "
            "MANDATORY WALKING DIRECTION (FACING 100% DIRECTLY AWAY INTO SCREEN DEPTH): "
            "Character faces strictly 180.0° directly away from camera (12 o'clock direction, into the background). "
            "Character walks steadily in place facing AWAY into screen depth. Left heel lifts and steps forward, alternating with right heel stepping forward into depth. "
            "STRICTLY FORBIDDEN to turn around, strictly forbidden to walk toward camera, strictly forbidden to backpedal, strictly forbidden to walk sideways. "
            "Full back of head, back of torso, and heels visible at all times with bilateral symmetry. "
            f"Sleeves and robe hems sway gently in place. {{waistRearMotionLock}} {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
    }


def build_run_templates(archetype: str) -> dict:
    info = ARCHETYPE_STYLES.get(archetype, ARCHETYPE_STYLES["young_male"])
    label = info["label"]
    desc = info["run_desc"]
    return {
        "0": (
            f"[run-0°] 4-second seamless loop 0° DIRECT FRONT VIEW RUN CYCLE ({label}). "
            "Character runs in place facing 100% DIRECTLY at camera on a fixed spot. "
            "STATIONARY TREADMILL CADENCE: Character remains anchored at exact same distance and camera framing throughout (strictly ZERO moving closer to camera, ZERO zooming forward). "
            f"Character runs {desc} "
            "Both feet track straight forward along the central axis. Arms pump forward-backward strictly tucked along ribcage, ZERO lateral flaring. "
            f"{LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame identically. Camera static. Solid green {chromaBgHex} background."
        ),
        "45": (
            f"[run-45°] 4-second seamless loop 45° THREE-QUARTER RUN CYCLE ({label}). "
            f"Character runs in place at 45° angle facing bottom-left {desc} "
            f"RUN DIRECTION LOCK: Dynamic strides track along the 45-degree diagonal line aligned with forward momentum. Strictly NO crab-running or sliding. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "90": (
            f"[run-90°] 4-second seamless loop 90° SIDE PROFILE RUN CYCLE ({label}). "
            f"Character runs in place in strict left side profile (9 o'clock) {desc} "
            f"Body stays strictly 90° side silhouette. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "135": (
            f"[run-135°] 4-second seamless loop 135° BACK-LEFT RUN CYCLE ({label}). "
            f"Character runs in place viewed from behind at 135° angle {desc} "
            f"RUN DIRECTION LOCK: Running strides track along the 135-degree diagonal axis aligned with body momentum. Body stays at 135° angle. {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame. Camera static. Solid green {chromaBgHex} background."
        ),
        "180": (
            f"[run-180°] 4-second seamless loop 180° DIRECT REAR VIEW RUN CYCLE ({label}). "
            "MANDATORY REAR RUNNING DIRECTION (FACING 100% DIRECTLY AWAY INTO SCREEN DEPTH): "
            "Character faces strictly 180.0° directly away from camera (12 o'clock direction, into the background). "
            "STATIONARY TREADMILL CADENCE: Character runs steadily in place on a fixed spot facing AWAY into depth, maintaining constant scale and framing (strictly ZERO moving away, ZERO shrinking into distance). "
            "Fast decisive athletic footsteps alternating into screen depth, heels lifting cleanly. "
            "Arms pump rhythmically forward and backward strictly tucked against sides. "
            "STRICTLY FORBIDDEN to turn around, strictly forbidden to look back, strictly forbidden to show any face or turn sideways. "
            "Full back of head, high ponytail, back of robes, and heels visible throughout with bilateral symmetry. "
            f"Robes and sash stream naturally in place. {{waistRearMotionLock}} {LOCOMOTION_ARM_LOCK} {GLOBAL_VIDEO_LOCK} "
            "Seamless loop: first frame = last frame identically. Camera static. Solid green {chromaBgHex} background."
        ),
    }


WALK_PROMPT_TEMPLATES = build_walk_templates("young_male")
RUN_PROMPT_TEMPLATES = build_run_templates("young_male")

IDLE_PROMPT_TEMPLATES = {
    "0": (
        "[idle-0°] 2D Anime chibi sprite character standing completely still on solid green {chromaBgHex} background, 8-second continuous animation (0° direct front view). "
        "STATIONARY POSTURE LOCK: Character stands completely still in a calm, poised standing posture. Head, shoulders, chest, torso, and grounded feet remain 100% frozen and rock-steady. "
        "IMMOBILE ARMS AND HANDS: Both arms hang naturally straight down at sides. Arms, forearms, wrists, hands, and fingers are 100% FROZEN, RIGID, AND MOTIONLESS. Strictly ZERO arm swaying, ZERO hand lifting, ZERO finger movement. "
        "SUBTLE WHISPER-BREEZE BANGS VIBRATION & FABRIC MICRO-SWAY: A delicate whisper of breeze creates subtle natural micro-vibrations and soft flutter on the front fringe bangs and face-framing sidelocks around the forehead and temples. "
        "Only the soft fabric of the wide hanging sleeve ends and lower robe hems has an extremely subtle, delicate micro-sway under calm natural gravity, with long hair strands softly oscillating. "
        "STRICTLY ZERO BREATH EFFECTS OR ARTIFACTS: Strictly ZERO breath vapor, ZERO smoke, ZERO mist, ZERO steam, ZERO exhalation arcs, ZERO light halos, ZERO glowing aura. "
        "CRITICAL BLANK FACELESS HEAD: Completely smooth blank featureless face, ZERO eyes, ZERO eyebrows, ZERO nose, ZERO mouth, ZERO lips. Facial skin seamlessly matches neck ({skinTone}). "
        "Clean flat solid green {chromaBgHex} background. Smooth 8-second continuous animation. Camera static."
    ),
    "45": (
        "[idle-45°] 2D Anime chibi sprite character standing completely still on solid green {chromaBgHex} background, 8-second continuous animation (45° three-quarter view). "
        "STATIONARY POSTURE LOCK: Character stays anchored in exact 45° three-quarter perspective. Head, shoulders, chest, torso, hips, and grounded feet remain 100% frozen and rock-steady with zero body rotation or shifting. "
        "IMMOBILE ARMS AND HANDS: Both arms remain naturally resting straight along the body silhouette. Arms, forearms, wrists, hands, and fingers are 100% FROZEN, RIGID, AND MOTIONLESS. Strictly ZERO arm swaying, ZERO hand twitching, ZERO gesturing. "
        "SUBTLE WHISPER-BREEZE BANGS VIBRATION & FABRIC MICRO-SWAY: A delicate whisper of breeze creates gentle micro-vibrations and soft flutter on the front fringe bangs and sidelocks visible from three-quarter angle. "
        "Only the soft fabric of the wide hanging sleeve ends and lower robe hems has an extremely subtle, delicate micro-sway under calm natural gravity, with ponytail strands softly oscillating. "
        "STRICTLY ZERO BREATH EFFECTS OR ARTIFACTS: Strictly ZERO breath vapor, ZERO smoke, ZERO mist, ZERO steam, ZERO exhalation arcs, ZERO light halos, ZERO glowing aura. "
        "CRITICAL BLANK FACELESS HEAD: Completely smooth blank featureless face, ZERO eyes, ZERO eyebrows, ZERO nose, ZERO mouth, ZERO lips. Facial skin seamlessly matches neck ({skinTone}). "
        "Clean flat solid green {chromaBgHex} background. Smooth 8-second continuous animation. Camera static."
    ),
    "90": (
        "[idle-90°] 2D Anime chibi sprite character standing completely still on solid green {chromaBgHex} background, 8-second continuous animation (90° pure side profile). "
        "STATIONARY POSTURE LOCK: Character stays anchored strictly in pure left side profile (facing 9 o'clock). Head, neck, torso, spine, and grounded feet remain 100% frozen and rock-steady. "
        "IMMOBILE ARM AND HAND: The visible arm hangs straight down along the side of the body. Arm, forearm, wrist, hand, and fingers are 100% FROZEN, RIGID, AND MOTIONLESS. Strictly ZERO arm swaying, ZERO hand waving, ZERO finger twitching. Hand does not move at all. "
        "SUBTLE WHISPER-BREEZE BANGS VIBRATION & FABRIC MICRO-SWAY: A whisper-light breeze creates delicate micro-fluttering on the front fringe hair tips and forward sidelocks in profile. "
        "Only the soft fabric of the wide hanging sleeve drapery and lower robe hem has an extremely subtle, delicate micro-sway under calm natural gravity, with hair ponytail swaying gently. "
        "STRICTLY ZERO BREATH EFFECTS OR ARTIFACTS: Strictly ZERO breath vapor, ZERO smoke, ZERO mist, ZERO steam, ZERO exhalation arcs, ZERO light halos, ZERO glowing aura. "
        "CRITICAL BLANK FACELESS PROFILE: Pure side profile with smooth blank featureless head, ZERO eyes, ZERO eyebrows, ZERO mouth, ZERO lips. Facial skin seamlessly matches neck ({skinTone}). "
        "Clean flat solid green {chromaBgHex} background. Smooth 8-second continuous animation. Camera static."
    ),
    "135": (
        "[idle-135°] 2D Anime chibi sprite character standing completely still on solid green {chromaBgHex} background, 8-second continuous animation (135° back-left view). "
        "STATIONARY POSTURE LOCK: Character stays anchored in exact 135° back-left orientation (facing diagonally away to 8 o'clock). Upper back, shoulders, torso, and grounded feet remain 100% frozen and rock-steady with zero body rotation. "
        "IMMOBILE ARMS AND HANDS: Both arms hang naturally along the sides. Arms, wrists, hands, and fingers are 100% FROZEN, RIGID, AND MOTIONLESS. Strictly ZERO arm swaying, ZERO hand movement. "
        "SUBTLE WHISPER-BREEZE HAIR & FABRIC MICRO-SWAY: A delicate breeze causes subtle micro-flutter on the visible side fringe locks and high ponytail strands. "
        "Only the soft fabric of the wide hanging sleeves and lower robe hems has an extremely subtle, delicate micro-sway under calm natural gravity. "
        "{waistRearMotionLock} "
        "STRICTLY ZERO BREATH EFFECTS OR ARTIFACTS: Strictly ZERO breath vapor, ZERO smoke, ZERO mist, ZERO steam, ZERO exhalation arcs, ZERO light halos, ZERO glowing aura. "
        "HEAD AND SILHOUETTE PRESERVATION: Preserve the exact head silhouette and posture from reference image without adding facial features or background elements. "
        "Clean flat solid green {chromaBgHex} background. Smooth 8-second continuous animation. Camera static."
    ),
    "180": (
        "[idle-180°] 2D Anime chibi sprite character standing completely still on solid green {chromaBgHex} background, 8-second continuous animation (180° direct rear view). "
        "STATIONARY POSTURE LOCK: Character stands completely still facing 100% directly away from camera with bilateral symmetry. Back of head, shoulders, spine, and grounded heels remain 100% frozen and rock-steady. "
        "IMMOBILE ARMS AND HANDS: Both arms hang straight down symmetrically at the sides. Arms, wrists, hands, and fingers are 100% FROZEN, RIGID, AND MOTIONLESS. Strictly ZERO arm swaying, ZERO hand movement. "
        "SUBTLE WHISPER-BREEZE HAIR & FABRIC MICRO-SWAY: A whisper-light breeze creates a delicate micro-sway through the length of the high ponytail and subtle edge flutter on sleeves and hem. "
        "{waistRearMotionLock} "
        "STRICTLY ZERO BREATH EFFECTS OR ARTIFACTS: Strictly ZERO breath vapor, ZERO smoke, ZERO mist, ZERO steam, ZERO exhalation arcs, ZERO light halos, ZERO glowing aura. "
        "CRITICAL REAR VIEW ZERO FACE: Character faces 100% directly away from camera showing only back of head and hair, with strictly ZERO face, ZERO eyes, ZERO mouth visible. "
        "Clean flat solid green {chromaBgHex} background. Smooth 8-second continuous animation. Camera static."
    ),
}

ATTACK_PROMPT_TEMPLATES = {
    "0": (
        "[attack-0°] 8-second continuous animation MARTIAL ARTS PALM STRIKE COMBO (0° front view). "
        "Character performs an elegant empty-handed martial arts palm strike sequence facing camera. "
        "Fluid flowing arm extensions, palm thrusts, and qigong hand movements in rhythmic cadence. "
        "Hair and robe sleeves move gracefully with momentum. Strictly ZERO weapons. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[attack-45°] 8-second continuous animation MARTIAL ARTS PALM STRIKE COMBO (45° three-quarter view). "
        "Character performs empty-handed martial arts palm strike combo at 45° angle. "
        "Diagonal martial palm strikes with fluid body balance. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[attack-90°] 8-second continuous animation MARTIAL ARTS PALM STRIKE COMBO (90° side profile). "
        "Character performs rhythmic horizontal palm thrust and retraction in side profile. "
        "Empty hands, fluid martial extension. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[attack-135°] 8-second continuous animation MARTIAL ARTS PALM STRIKE COMBO (135° back-left view). "
        "Character performs martial arts palm strike sequence viewed from behind at 135° angle. "
        "Shoulders and robe sleeves turn rhythmically with each strike. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[attack-180°] 8-second continuous animation MARTIAL ARTS PALM STRIKE COMBO (180° rear view). "
        "Character performs rhythmic martial arts palm sequence facing away from camera. "
        "Arm extensions and flowing robe sleeves visible from behind. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

DEFEND_PROMPT_TEMPLATES = {
    "0": (
        "[defend-0°] 8-second continuous animation MARTIAL DEFENSIVE GUARD STANCE (0° front view). "
        "Character holds an empty-handed martial defensive stance facing camera, palms raised in balanced guard posture. "
        "Grounded composed poise, sleeves fluttering gently. Strictly ZERO weapons. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "45": (
        "[defend-45°] 8-second continuous animation MARTIAL DEFENSIVE GUARD STANCE (45° three-quarter). "
        "Character holds empty-handed defensive guard stance at 45° angle. "
        "Poised martial balance, palms up in guard posture. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "90": (
        "[defend-90°] 8-second continuous animation MARTIAL DEFENSIVE GUARD STANCE (90° side profile). "
        "Character holds defensive martial stance in side profile. "
        "Arms raised in protective martial guard posture, body braced. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "135": (
        "[defend-135°] 8-second continuous animation MARTIAL DEFENSIVE GUARD STANCE (135° back-left). "
        "Character holds martial guard viewed from behind at 135° angle. "
        "Back posture grounded, defensive ready stance. Empty hands. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
    "180": (
        "[defend-180°] 8-second continuous animation MARTIAL DEFENSIVE GUARD STANCE (180° rear view). "
        "Character holds martial defensive stance facing away from camera. "
        "Balanced empty-handed stance visible from behind. "
        f"{GLOBAL_VIDEO_LOCK} "
        "Smooth 8-second continuous animation. Camera static. Solid green {chromaBgHex} background."
    ),
}

# ─── Action Registry ──────────────────────────────────────────
# Maps action keys to their template dicts for pipeline lookup

try:
    from agent.services.action_prompts_acting import ACTING_ACTION_TEMPLATES
except ImportError:
    from action_prompts_acting import ACTING_ACTION_TEMPLATES

# Master priority sequence for character animation pipeline (Hoạt hình diễn hoạt)
ANIMATION_PRIORITY_SEQUENCE = [
    # Tier 1: Core Locomotion & Baseline Pose (Bắt buộc kiểm tra chuẩn mốc đầu tiên)
    "idle",               # Đứng yên thở nhẹ / Giữ dáng mốc
    "walk",               # Đi bộ thư thả
    "run",                # Chạy nhanh linh hoạt
    # Tier 2: Acting, Etiquette & Social (Giao tiếp & Diễn xuất hoạt hình cốt lõi)
    "wave",               # Vẫy tay chào hỏi
    "bow",                # Hành lễ / Cúi chào tôn kính
    "cover_mouth_laugh",  # Che miệng cười e ấp / cười vui
    "talking",            # Nói chuyện / Diễn giải cử chỉ tay
    "nod",                # Gật đầu đồng ý / Tán thành
    "think",              # Đưa tay lên cằm suy nghĩ
    # Tier 3: Emotional Reactions (Phản ứng cảm xúc hoạt cảnh)
    "surprise",           # Giật mình / Kinh ngạc
    "cheer",              # Reo hò / Ăn mừng chiến thắng
    "sad",                # Buồn bã / Thở dài dejectedly
    "angry",              # Tức giận / Dậm chân dỗi
    # Tier 4: Combat & Impact (Chiến đấu & Tác động ngoại lực)
    "attack",             # Đánh công / Xuất chiêu
    "defend",             # Phòng thủ / Chắn đỡ
    "hurt",               # Trúng đòn / Lảo đảo hồi phục
]

ACTION_TEMPLATES = {
    "walk": WALK_PROMPT_TEMPLATES,
    "idle": IDLE_PROMPT_TEMPLATES,
    "run": RUN_PROMPT_TEMPLATES,
    "attack": ATTACK_PROMPT_TEMPLATES,
    "defend": DEFEND_PROMPT_TEMPLATES,
    **ACTING_ACTION_TEMPLATES,
}

# Pipeline stage execution order for the AI agent
PIPELINE_STAGES = [
    {
        "stage": 1,
        "key": "base_0",
        "label": "Tao Nhan Vat Goc 0 do",
        "type": "image",
        "mode": "text_to_image",
        "angles": ["0"],
        "ref": None,
    },
    {
        "stage": 2,
        "key": "angles_4",
        "label": "Tao 4 goc con lai tu anh 0 do",
        "type": "image",
        "mode": "image_to_image",
        "angles": ["45", "90", "135", "180"],
        "ref": "0",
    },
    {
        "stage": 3,
        "key": "actions",
        "label": "Tao video hanh dong hoat hinh theo thu tu uu tien",
        "type": "video",
        "mode": "image_to_video_loop_4s",
        "actions": ANIMATION_PRIORITY_SEQUENCE,
        "angles": ["0", "45", "90", "135", "180"],
        "ref": "per_angle",
    },
]


def format_template(template: str, customizer: dict = None) -> str:
    """Fill template variables with customizer values."""
    c = {**DEFAULT_CUSTOMIZER_VALUES, **(customizer or {})}
    if "waistRearMotionLock" not in c:
        if c.get("gender") == "female":
            c["waistRearMotionLock"] = "Rear waist delicate silk ribbon sash draping calmly downward without flapping under natural gravity."
        else:
            c["waistRearMotionLock"] = "Flat continuous waist belt remains completely smooth without any ties or bows."
    text = template
    for key, val in c.items():
        placeholder = f"{{{key}}}"
        if placeholder in text:
            text = text.replace(placeholder, str(val))
    return text


def detect_motion_archetype(customizer: dict = None) -> str:
    """Classify character archetype into: 'elderly', 'child', 'maiden', 'mature_woman', 'young_male'."""
    if not customizer:
        return "young_male"
    text = " ".join([
        str(customizer.get("age", "")),
        str(customizer.get("gender", "")),
        str(customizer.get("bodyType", "")),
        str(customizer.get("characterName", "")),
        str(customizer.get("personality", "")),
    ]).lower()

    # Strip 'years old' / 'year-old' so it doesn't falsely trigger 'old'
    text_no_yo = re.sub(r"\byears?\s*old\b|\byear-old\b", "", text)

    # 1. Elderly / Senior (50-80+, lão, ông/bà lão)
    elderly_kw = ["elder", "senior", "lão", "bà lão", "ông lão", "thợ già", "50", "55", "60", "65", "70", "75", "80"]
    if any(k in text_no_yo for k in elderly_kw) or re.search(r"\b(old man|old woman|elderly)\b", text):
        return "elderly"

    # 2. Child / Kid (3-12 years old, trẻ con, thiếu nhi, bé)
    child_kw = ["toddler", "trẻ con", "thiếu nhi", "bé trai", "bé gái", "tiểu đồng", "little kid", "child", "little boy", "little girl"]
    if any(k in text_no_yo for k in child_kw) or re.search(r"\b(child|kid)\b", text_no_yo):
        return "child"
    if re.search(r"\b([3-9]|1[0-2])\s*(?:years?|tuổi|t)\b", text):
        return "child"

    # 3. Female classifications (Maiden vs Mature Woman)
    is_female = any(k in text for k in ["female", "nữ", "gái", "maiden", "woman"])
    if is_female:
        mature_kw = ["mature", "lady", "queen", "empress", "phụ nữ", "quý bà", "quý cô", "hoàng hậu", "nữ tướng", "mẫu thân"]
        if any(k in text for k in mature_kw):
            return "mature_woman"
        if re.search(r"\b(2[5-9]|[34][0-9])\b", text):
            return "mature_woman"
        return "maiden"

    return "young_male"


def get_action_templates(action_key: str, customizer: dict = None) -> dict:
    """Get prompt templates dict for an action key (walk, idle, run, etc.), tailored to archetype."""
    archetype = detect_motion_archetype(customizer)
    if action_key == "walk":
        return build_walk_templates(archetype)
    if action_key == "run":
        return build_run_templates(archetype)
    return ACTION_TEMPLATES.get(action_key, {})
