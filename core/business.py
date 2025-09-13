# business.py
# Business logic for On a Journey!
import json
import os
import hashlib
import glob
import streamlit as st
import math
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo
from core.database import create_database
from core.restrict_module import restrict_module

# Database
database = create_database()

# ---------------------------- Navigation ---------------------------- #

def rerun():
    """Request a rerun from anywhere in the app"""
    st.session_state.rerun = True

def check_rerun():
    """Check if rerun was requested and execute it"""
    if st.session_state.get('rerun'):
        st.session_state.rerun = False
        st.rerun()

def set_view(view: str):
    """Change current view"""
    st.session_state.view = view
    rerun()

def get_current_view(user: Optional[dict] = None) -> str:
    """Determine current view based on app state"""
    if "view" not in st.session_state:
        st.session_state.view = "auth"
    
    # Auto-redirect logic
    if st.session_state.view == "auth" and user:
        if not user.get("start_date"):
            return "journey_start"
        else:
            if not user.get("intro_shown"):
                return "intro"
            else:
                return "chapters"
    
    return st.session_state.view

def mark_intro_shown(user: dict):
    """Mark intro as shown for this journey"""
    user["intro_shown"] = True
    update_user(user)

# ---------------------------- Auth ---------------------------- #

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = hashlib.sha256(os.urandom(32)).hexdigest()
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, pw_hash

def verify_password(password: str, salt: str, pw_hash: str) -> bool:
    return hashlib.sha256((salt + password).encode()).hexdigest() == pw_hash

# ---------------------------- Users & Achievements ---------------------------- #

def get_user(username: str) -> Optional[dict]:
    return database.get_user(username)

def create_user(username: str, password: str) -> dict:
    salt, pw_hash = hash_password(password)
    user = {
        "username": username,
        "salt": salt,
        "pw_hash": pw_hash,
        "start_date": None,
        "chapters": {},
        "active_journey_data": None,
        'custom_journeys':{},
        "journey_name": None,
        "intro_shown": False,
        "avatar": {},
        "world": {},
        "achievements": {},
        "timezone": "Europe/Paris"  # Default timezone
    }
    return database.create_user(user)

def update_user(user: dict):
    database.update_user(user)

def has_achievements(user: dict, required_achievements: List[str]) -> bool:
    """Check if user has all required achievements"""
    if not required_achievements:
        return True
    
    user_achievements = user.get("achievements", {})
    return all(ach_id in user_achievements for ach_id in required_achievements)

def unlock_achievement(user: dict, achievement_id: str, title: str = None, description: str = None):
    """Unlock an achievement for the user if not already unlocked"""
    if "achievements" not in user:
        user["achievements"] = {}
    
    if achievement_id not in user["achievements"]:
        user["achievements"][achievement_id] = {
            "id": achievement_id,
            "title": title or achievement_id,
            "description": description or ""
        }
        update_user(user)
        return True  # New achievement
    return False  # Already unlocked

# ---------------------------- Time helpers ---------------------------- #

def get_timezone(user: Optional[dict]=None) -> ZoneInfo:
    if user:
        return ZoneInfo(user.get("timezone", "Europe/Paris"))
    else:
        return ZoneInfo("Europe/Paris")

def today(user: dict = None) -> date:
    tz = get_timezone(user)
    return datetime.now(tz).date()

def now(user: dict = None) -> datetime:
    tz=get_timezone(user)
    return datetime.now(tz)

def is_day_elapsed(target_date: date,user:dict=None) -> bool:
    """True if target_date is fully elapsed (past 23:59:59) or if god mode is active"""
    if st.session_state.get("god_mode", False):
        return True
    
    end_of_target = datetime.combine(target_date, time(23, 59, 59), tzinfo=get_timezone(user))
    return now(user) > end_of_target

# ---------------------------- XP et Niveaux ---------------------------- #

def calculate_level(xp: float) -> int:
    """Calculate level from XP using quadratic progression"""
    if xp <= 0:
        return 1
    return int(0.5 + 0.5 * math.sqrt(1 + (16/3) * xp))

def get_level_bounds(level: int) -> tuple[float, float]:
    """Get XP bounds for a given level (min_xp, max_xp)"""
    if level < 1:
        raise ValueError("level must be at least 1")
    
    min_xp = 0.75 * (level - 1) * level
    max_xp = 0.75 * level * (level + 1)
    
    return (min_xp, max_xp)

def get_xp_progress(user: dict) -> dict:
    """Get XP progression info for display"""
    total_xp = calculate_total_xp(user)
    current_level = calculate_level(total_xp)
    min_xp, max_xp = get_level_bounds(current_level)
    progress_in_level = (total_xp - min_xp) / (max_xp - min_xp) if max_xp > min_xp else 0.0
    
    return {
        "total_xp": total_xp,
        "current_level": current_level,
        "min_xp": min_xp,
        "max_xp": max_xp,
        "progress_in_level": min(progress_in_level, 1.0),
        "xp_to_next": max_xp - total_xp
    }

# ---------------------------- Accessibility Logic (CENTRALIZED) ---------------------------- #

def is_chapter_accessible(user: dict, chapter_num: int) -> dict:
    """Check if a chapter is accessible to the user"""
    
    journey = get_active_journey(user)
    if not journey or chapter_num not in journey["chapters"]:
        return {"accessible": False, "reason": "invalid_chapter"}
    
    journey_chapter = journey["chapters"][chapter_num]
    user_level = get_xp_progress(user)["current_level"]
    required_level = journey_chapter.get("required_level", 1)
    required_achievements = journey_chapter.get("depends_on", [])
    user_achievements = user.get("achievements", {})
    
    # Check level requirement
    if user_level < required_level:
        return {
            "accessible": False,
            "reason": "insufficient_level",
            "required_level": required_level,
            "user_level": user_level,
            "missing_achievements": []
        }
    
    # Check achievement requirements
    missing_achievements = [ach for ach in required_achievements if ach not in user_achievements]
    if missing_achievements:
        return {
            "accessible": False,
            "reason": "missing_achievements",
            "missing_achievements": missing_achievements,
            "required_level": required_level,
            "user_level": user_level
        }
    
    # AJOUTER : Check commitment rules
    committed_chapter = get_committed_chapter_for_level(user, required_level)
    if committed_chapter is not None and committed_chapter != chapter_num:
        return {
            "accessible": False,
            "reason": "committed_elsewhere",
            "committed_chapter": committed_chapter,
            "required_level": required_level,
            "user_level": user_level,
            "missing_achievements": []
        }
    
    return {
        "accessible": True,
        "reason": "all_conditions_met",
        "missing_achievements": [],
        "required_level": required_level,
        "user_level": user_level,
        "committed_chapter": committed_chapter
    }

def is_challenge_accessible(user: dict, chapter_num: int, challenge_idx: int) -> dict:
    """Check if a specific challenge is accessible to the user"""
    # First check if chapter is accessible
    chapter_access = is_chapter_accessible(user, chapter_num)
    if not chapter_access["accessible"]:
        return chapter_access
    
    journey = get_active_journey(user)
    chapter_record = get_chapter_record(user, chapter_num)
    challenges = chapter_record.get("challenges", [])
    
    if challenge_idx >= len(challenges):
        return {"accessible": False, "reason": "invalid_challenge"}
    
    challenge = challenges[challenge_idx]
    required_achievements = challenge.get("depends_on", [])
    user_achievements = user.get("achievements", {})
    
    # Check challenge-specific achievement requirements
    missing_achievements = [ach for ach in required_achievements if ach not in user_achievements]
    if missing_achievements:
        return {
            "accessible": False,
            "reason": "missing_achievements",
            "missing_achievements": missing_achievements
        }
    
    # Check commitment rules
    journey_chapter = journey["chapters"][chapter_num]
    required_level = journey_chapter.get("required_level", 1)
    committed_chapter = get_committed_chapter_for_level(user, required_level)
    
    if committed_chapter is not None and committed_chapter != chapter_num:
        return {"accessible": False, "reason": "committed_elsewhere"}
    
    return {"accessible": True, "reason": "all_conditions_met"}

# ---------------------------- Journeys ---------------------------- #

def get_available_journeys(user: Optional[dict] = None) -> List[dict]:
    """Get journeys from both filesystem (official) and user DB (personal)"""
    journeys = []
    
    # 1. Official journeys from filesystem
    journey_files = glob.glob("journeys/*.json")
    for file_path in journey_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            journey_name = os.path.basename(file_path).replace('.json', '')
            journey_structure = normalize_journey_structure(data)
            
            journeys.append({
                "name": journey_name,
                "source": "official",  # ← NOUVEAU
                "file_path": file_path,
                "journey_structure": journey_structure,
                "chapter_count": len(journey_structure["chapters"])
            })
        except Exception as e:
            print(f"Error loading official journey {file_path}: {e}")
    
    # 2. Personal journeys from user database  ← NOUVEAU BLOC
    if user:
        custom_journeys = user.get("custom_journeys", {})
        for name, journey_data in custom_journeys.items():
            try:
                journey_structure = normalize_journey_structure(journey_data)
                journeys.append({
                    "name": name,
                    "source": "personal",  # ← NOUVEAU
                    "file_path": None,     # Pas de fichier
                    "journey_structure": journey_structure,
                    "chapter_count": len(journey_structure["chapters"]),
                    "created_at": journey_data.get("created_at"),      # ← NOUVEAU
                    "modified_at": journey_data.get("modified_at")     # ← NOUVEAU
                })
            except Exception as e:
                print(f"Error loading personal journey {name}: {e}")
    
    return journeys

def normalize_journey_structure(raw_data: Any) -> dict:
    """Convert raw journey data to normalized structure"""
    if not isinstance(raw_data, dict) or "title" not in raw_data:
        raise ValueError("Invalid journey format - missing title")
    
    # Support both old 'days' and new 'chapters' format
    chapters_data = raw_data.get("chapters", raw_data.get("days", {}))
    chapters_data = _normalize_chapters_data(chapters_data)
    
    return {
        "title": raw_data["title"],
        "description": raw_data.get("description", ""),
        "image": raw_data.get("image",None),
        "intro_text": raw_data.get("intro_text", ""),
        "failure_text": raw_data.get("failure_text", ""),
        "success_text": raw_data.get("success_text", ""),
        "initial_avatar": raw_data.get("initial_avatar"),
        "initial_world": raw_data.get("initial_world"),
        "chapters": chapters_data
    }

def _normalize_chapters_data(raw_chapters: Any) -> Dict[int, dict]:
    """Convert various JSON formats to normalized chapter structure"""
    result = {}
    
    if isinstance(raw_chapters, list):
        for i, item in enumerate(raw_chapters, 1):
            if isinstance(item, dict):
                chapter_num = int(item.get("chapter", item.get("day", i)))
                result[chapter_num] = _normalize_chapter_data(item)
    
    elif isinstance(raw_chapters, dict):
        for key, item in raw_chapters.items():
            if isinstance(item, dict):
                chapter_num = int(key)
                result[chapter_num] = _normalize_chapter_data(item)
    
    return result

def _normalize_chapter_data(chapter_data: dict) -> dict:
    """Normalize a single chapter's data"""
    challenges = []
    for ch in chapter_data.get("challenges", []):
        challenges.append({
            "title": ch.get("title", "Challenge"),
            "description": ch.get("description", ""),
            "image":ch.get("image",None),
            "difficulty": ch.get("difficulty", "easy"),
            "code": ch.get('code', ""),
            "completed": False,
            "depends_on": ch.get("depends_on", [])
        })
    
    return {
        "title": chapter_data.get("title", ""),
        "description": chapter_data.get("description", ""),
        "image": chapter_data.get("image",None),
        "intro": chapter_data.get("intro", ""),
        "challenges": challenges,
        "required_level": chapter_data.get("required_level", 1),
        "depends_on": chapter_data.get("depends_on", [])
    }

def set_user_journey(user: dict, journey: dict):
    """Set a journey as active for the user"""
    user["active_journey_data"] = journey["journey_structure"]
    update_user(user)

def get_active_journey(user: dict) -> Optional[dict]:
    """Get the currently active journey"""
    journey_data = user.get("active_journey_data")

    if journey_data and "chapters" in journey_data:
        # Ensure keys are integers
        chapters = journey_data["chapters"]
        if chapters and isinstance(next(iter(chapters.keys())), str):
            journey_data["chapters"] = {int(k): v for k, v in chapters.items()}
    # Backward compatibility: convert old 'days' to 'chapters'
    elif journey_data and "days" in journey_data:
        chapters = journey_data["days"]
        if chapters and isinstance(next(iter(chapters.keys())), str):
            chapters = {int(k): v for k, v in chapters.items()}
        journey_data["chapters"] = chapters
        del journey_data["days"]
    
    return journey_data

def get_chapter_data(user: dict, chapter_num: int) -> dict:
    """Get chapter data from active journey"""
    journey = get_active_journey(user)
    if journey and "chapters" in journey and chapter_num in journey["chapters"]:
        return journey["chapters"][chapter_num]
    
    return {
        "title": f"Chapter {chapter_num}",
        "description": "",
        "image":None,
        "intro": "",
        "challenges": [],
        "required_level": 1,
        "depends_on": []
    }

# ---------------------------- Journey management ---------------------------- #

def parse_initial_state(json_string: str) -> dict:
    """Parse initial state JSON string, return empty dict if invalid"""
    if not json_string:
        return {}
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {}

def start_journey(user: dict, start_date: date, journey: dict, timezone: str):
    """Start a new journey with selected journey and timezone"""
    user["start_date"] = start_date.isoformat()
    user["timezone"] = timezone  # Store selected timezone
    user["chapters"] = {}
    user["journey_name"] = journey["name"]
    user["intro_shown"] = False
    user["achievements"] = {}  # Clean old achievements
    
    # Initialize avatar and world with journey's initial states
    journey_structure = journey["journey_structure"]
    initial_avatar = parse_initial_state(journey_structure.get("initial_avatar", "{}"))
    initial_world = parse_initial_state(journey_structure.get("initial_world", "{}"))
    
    user["avatar"] = initial_avatar
    user["world"] = initial_world
    
    set_user_journey(user, journey)
    set_view("intro")

def is_journey_completed(user: dict) -> bool:
    """Check if a chapter of the maximum level is validated"""
    journey = get_active_journey(user)
    if not journey or not journey.get("chapters"):
        return False
    
    chapters_data = user.get("chapters", {})
    
    # Find the maximum required level in the journey
    max_level = max(
        chapter_data.get("required_level", 1) 
        for chapter_data in journey["chapters"].values()
    )
    
    # Check if any chapter of the maximum level is validated
    for chapter_num, chapter_data in journey["chapters"].items():
        if chapter_data.get("required_level", 1) == max_level:
            chapter_record = chapters_data.get(str(chapter_num), {})
            if chapter_record.get("validated", False):
                return True
    
    return False

def get_validation_credits(user: dict) -> int:
    """Calculate how many chapters can be validated based on elapsed days"""
    if not user.get("start_date"):
        return 0
    
    # God mode override
    if st.session_state.get("god_mode", False):
        return 1
    
    start_date = date.fromisoformat(user["start_date"])
    days_elapsed = (today(user) - start_date).days  # Pass user for timezone
    
    # Count already validated chapters
    chapters_data = user.get("chapters", {})
    validated_count = sum(
        1 for chapter_data in chapters_data.values() 
        if chapter_data.get("validated", False)
    )
    
    # Credits = days elapsed - validated chapters
    credits = days_elapsed - validated_count
    return max(0, credits)

def get_chapter_record(user: dict, chapter_num: int) -> dict:
    """Get or create chapter record"""
    chapters = user.setdefault("chapters", {})
    key = str(chapter_num)
    
    if key not in chapters:
        # Create new chapter record from journey content
        chapter_template = get_chapter_data(user, chapter_num)
        journey = get_active_journey(user)
        chapter_data = journey["chapters"].get(chapter_num, {})
        start_date = date.fromisoformat(user["start_date"])
        chapter_date = start_date + timedelta(days=chapter_num - 1)
        
        chapters[key] = {
            "validated": False,
            "title": chapter_template.get("title", f"Chapter {chapter_num}"),
            "description": chapter_template.get("description", ""),
            "image": chapter_template.get("image",None),
            "intro": chapter_template.get("intro", ""),
            "challenges": [
                {
                    "title": ch.get("title", "Challenge"),
                    "description": ch.get("description", ""),
                    "image":ch.get("image",None),
                    "difficulty": ch.get("difficulty", "easy"),
                    "code": ch.get("code", ""),
                    "completed": False,
                    "depends_on": ch.get("depends_on", [])
                }
                for ch in chapter_template.get("challenges", [])
            ],
            "required_level": chapter_data.get("required_level", 1),
            "date": chapter_date.isoformat(),
            "depends_on": chapter_data.get("depends_on", [])
        }
    
    return chapters[key]

def update_challenge_completion(user: dict, chapter_num: int, challenge_idx: int, completed: bool):
    """Update a challenge's completion status"""
    chapter_record = get_chapter_record(user, chapter_num)
    if 0 <= challenge_idx < len(chapter_record["challenges"]):
        chapter_record["challenges"][challenge_idx]["completed"] = completed
        user["chapters"][str(chapter_num)] = chapter_record
        update_user(user)

def can_validate_chapter(user: dict, chapter_num: int) -> bool:
    """Check if chapter can be validated - uses centralized accessibility + validation rules"""
    # Basic accessibility check
    access = is_chapter_accessible(user, chapter_num)
    if not access["accessible"]:
        return False
    
    # Additional validation-specific checks
    chapter_record = get_chapter_record(user, chapter_num)
    if chapter_record.get("validated", False):
        return False
    
    if get_validation_credits(user) == 0:
        return False
    
    # Check commitment
    journey = get_active_journey(user)
    required_level = journey["chapters"][chapter_num].get("required_level", 1)
    committed_chapter = get_committed_chapter_for_level(user, required_level)
    if committed_chapter != chapter_num:
        return False
    
    return True

def get_validated_chapter_for_level(user: dict, required_level: int) -> Optional[int]:
    """Get the validated chapter for a given level (max 1 per level)"""
    chapters_data = user.get("chapters", {})
    journey = get_active_journey(user)
    
    if not journey:
        return None
    
    for chapter_num, journey_chapter in journey["chapters"].items():
        if journey_chapter.get("required_level", 1) == required_level:
            chapter_record = chapters_data.get(str(chapter_num), {})
            if chapter_record.get("validated", False):
                return chapter_num
    
    return None

def get_committed_chapter_for_level(user: dict, required_level: int) -> Optional[int]:
    """Get the chapter with completed challenges for a given level (commitment)"""
    chapters_data = user.get("chapters", {})
    journey = get_active_journey(user)
    
    if not journey:
        return None
    
    for chapter_num, journey_chapter in journey["chapters"].items():
        if journey_chapter.get("required_level", 1) == required_level:
            chapter_record = chapters_data.get(str(chapter_num), {})
            
            # Check if any challenge is completed in this chapter
            challenges = chapter_record.get("challenges", [])
            if any(ch.get("completed", False) for ch in challenges):
                return chapter_num
    
    return None

def validate_chapter(user: dict, chapter_num: int):
    """Validate a chapter"""
    chapter_record = get_chapter_record(user, chapter_num)
    chapter_record["validated"] = True
    user["chapters"][str(chapter_num)] = chapter_record
    update_user(user)
    
    # Check if journey is completed after this validation
    if is_journey_completed(user):
        set_view("journey_completed")

def reset_journey(user: dict):
    """Reset user journey completely"""
    user["start_date"] = None
    user["chapters"] = {}
    user["active_journey_data"] = None
    user["intro_shown"] = False
    user["avatar"] = {}
    user["world"] = {}
    user["achievements"] = {}  # ← AJOUTER cette ligne
    update_user(user)
    set_view("journey_start")

# ---------------------------- XP Calculation ---------------------------- #

DIFFICULTY_WEIGHTS = {
    "easy": 1.0,
    "medium": 2.0, 
    "hard": 3.0,
    "extreme": 4.0
}

def get_challenge_weight(difficulty: str) -> float:
    return DIFFICULTY_WEIGHTS.get(difficulty, 1.0)

def calculate_challenge_xp(required_level: int, challenges: List[dict]) -> float:
    """Calculate challenge bonus XP based on required level"""
    if not challenges:
        return 0.0
    
    weights = [get_challenge_weight(ch.get("difficulty", "easy")) for ch in challenges]
    completed = [1.0 if ch["completed"] else 0.0 for ch in challenges]
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    completion_ratio = sum(w * c for w, c in zip(weights, completed)) / total_weight
    challenge_bonus = required_level * completion_ratio
    
    return challenge_bonus

def calculate_total_xp(user: dict) -> float:
    """Calculate user's total XP by recalculating from challenge states"""
    chapters_data = user.get("chapters", {})
    journey = get_active_journey(user)
    
    if not journey:
        return 0.0
    
    total_xp = 0.0
    
    for chapter_str, chapter_data in chapters_data.items():
        if not chapter_data.get("validated", False):
            continue
            
        chapter_num = int(chapter_str)
        
        # Get required level from journey data
        journey_chapter = journey["chapters"].get(chapter_num, {})
        required_level = journey_chapter.get("required_level", chapter_num)
        
        # Calculate XP for this chapter
        base_xp = required_level
        challenge_xp = calculate_challenge_xp(required_level, chapter_data.get("challenges", []))
        chapter_total_xp = base_xp + challenge_xp
        
        total_xp += chapter_total_xp
    
    return total_xp


# ---------------------------- Challenge Execution with RPG Context ---------------------------- #

def create_challenge_namespace(user: dict, chapter_num: int) -> dict:
    """Create rich sandbox for challenges - secure but powerful"""
    
    # Restrictions minimales (juste éviter les accidents)
    restrict_module('numpy', restricted_attributes=['save', 'savez', 'savetxt'])
    restrict_module('pandas', restricted_attributes=['to_pickle', 'read_pickle'])
    restrict_module('graphviz', restricted_attributes=['render', 'save'])
    
    # Modules essentiels
    import math
    import random
    import datetime
    import time
    import json
    import base64
    import re
    import statistics
    import collections
    
    # Data science & visualization stack
    import numpy
    import pandas
    import matplotlib.pyplot
    import seaborn
    import plotly.express
    import plotly.graph_objects
    import altair
    import sympy
    import io
    
    # Optionals avec fallback
    try:
        import graphviz
        graphviz_available = graphviz
    except ImportError:
        graphviz_available = None
        
    try:
        from PIL import Image
        pil_available = Image
    except ImportError:
        pil_available = None
    
    def new_achievement(achievement_id: str, title: str = None, description: str = None):
        """Helper function to unlock achievements from challenges"""
        if unlock_achievement(user, achievement_id, title, description):
            display_title = title or achievement_id
            st.success(f"🏆 Achievement unlocked: {display_title}")
            if description:
                st.info(description)
    
    # Inject calculated XP/level into avatar (read-only info)
    xp_info = get_xp_progress(user)
    avatar=user['avatar']
    avatar["xp"] = xp_info["total_xp"]
    avatar["level"] = xp_info["current_level"]
    
    # Essential built-ins for comfortable coding
    essential_builtins = {
        # Core types
        'dict': dict, 'list': list, 'tuple': tuple, 'set': set,
        'str': str, 'int': int, 'float': float, 'bool': bool,
        
        # Utilities
        'range': range, 'len': len, 'type': type, 'isinstance': isinstance,
        'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
        'all': all, 'any': any,
        
        # Iteration
        'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
        'sorted': sorted, 'reversed': reversed,
        
        # Inspection/debug
        'hasattr': hasattr, 'getattr': getattr, 'repr': repr,
        
        # Common exceptions
        'ValueError': ValueError, 'TypeError': TypeError, 'KeyError': KeyError,
        'IndexError': IndexError, 'AttributeError': AttributeError,

        #File-like
        'BytesIO':io.BytesIO, "StringIO":io.StringIO,

        #Dynamic execution (safe in a controlled namespace)
        'exec':exec, 'compile':compile, 'eval':eval
    }
    
    from core.editor import editor, info_bar, menu_bar, button

    namespace = {
        # Core RPG context (secure - no user object!)
        "st": st,
        "avatar": avatar,           # Contains XP/level for display
        "world": user["world"],     # Story state
        "chapter_num": chapter_num,
        "new_achievement": new_achievement,
        "validate": None,  # Set by calling component

        # Code editor widget (for convenience)
        "editor": editor, "info_bar":info_bar, "menu_bar":menu_bar,"button":button,
        
        # Standard library modules
        "math": math, "random": random, "datetime": datetime, 
        "time": time, "json": json, "base64": base64, "re": re,
        "statistics": statistics, "collections": collections,
        
        # Data science & visualization
        "numpy": numpy, "pandas": pandas,
        "pyplot": matplotlib.pyplot, "seaborn": seaborn,
        "plotly": plotly.express, "plotly_go": plotly.graph_objects,
        "altair": altair, "sympy": sympy,
    }
    
    # Add essential built-ins
    namespace.update(essential_builtins)
    
    # Add optional modules if available
    if graphviz_available:
        namespace["graphviz"] = graphviz_available
    
    if pil_available:
        namespace["PIL_Image"] = pil_available
    
    return namespace

# ---------------------------- Journey Editor ---------------------------- #

def create_empty_journey(name: str, chapters_count: int) -> dict:
    """Create an empty journey template"""
    chapters = {}
    
    for chapter in range(1, chapters_count + 1):
        chapters[chapter] = {
            "title": f"Chapter {chapter}",                          # ← NOUVEAU
            "description": f"Description for chapter {chapter}",    # ← NOUVEAU
            "image":None,
            "intro": f"Chapter {chapter} - Write your introduction here...",
            "challenges": [
                {
                    "title": "Example challenge",
                    "description": "Challenge description...",
                    "image":None,
                    "difficulty": "easy",
                    "completed": False,
                    "code":"",
                    "depends_on": []
                }
            ],
            "required_level": 1,
            "depends_on": []
        }
    
    return {
        "title": name,
        "description": "",
        "image":None,
        "intro_text": "",
        "failure_text": "",
        "success_text": "",
        "chapters": chapters
    }

def save_journey(journey: dict, filename: str, user: dict) -> bool:
    """Save journey to user's personal collection (always)"""
    try:
        # Initialize custom journeys if needed
        if "custom_journeys" not in user:
            user["custom_journeys"] = {}
        
        # Add/update metadata
        journey_data = {
            **journey,
            "created_at": journey.get("created_at", datetime.now().isoformat()),
            "modified_at": datetime.now().isoformat()
        }
        
        # Clean filename for key
        clean_name = filename.replace('.json', '').replace(' ', '_').lower()
        
        user["custom_journeys"][clean_name] = journey_data
        update_user(user)
        return True
        
    except Exception as e:
        print(f"Error saving journey: {e}")
        return False

def save_journey_to_file(journey: dict, filename: str = None) -> bool:
    """Save journey to journeys/ directory"""
    try:
        if not filename:
            filename = f"{journey['title'].lower().replace(' ', '_')}.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        os.makedirs("journeys", exist_ok=True)
        filepath = f"journeys/{filename}"
        
        save_data = {
            "title": journey["title"],
            "description": journey["description"],
            "image":journey["image"],
            "intro_text": journey["intro_text"],
            "failure_text": journey["failure_text"],
            "success_text": journey["success_text"],
            "initial_avatar":journey["initial_avatar"],
            "initial_world":journey["initial_world"],
            "chapters": {str(k): v for k, v in journey["chapters"].items()}
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving journey: {e}")
        return False

def load_journey_for_editing(journey_name: str, user: dict, source: str = "official") -> dict:
    """Load journey for editing - official journeys get cloned to personal"""
    try:
        if source == "personal":
            # Load from user's custom journeys
            custom_journeys = user.get("custom_journeys", {})
            if journey_name in custom_journeys:
                return normalize_journey_structure(custom_journeys[journey_name])
            else:
                print(f"Personal journey {journey_name} not found")
                return None
                
        else:
            # Load from filesystem and auto-clone for editing ← NOUVEAU
            filepath = f"journeys/{journey_name}"
            if not filepath.endswith('.json'):
                filepath += '.json'
                
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            journey = normalize_journey_structure(raw_data)
            
            # Mark as modified official journey ← NOUVEAU
            journey["title"] = f"{journey['title']} (My Version)"  # Clear indication
            
            return journey
            
    except Exception as e:
        print(f"Error loading journey: {e}")
        return None

def validate_journey_structure(journey: dict) -> list[str]:
    """Validate journey structure and return list of errors"""
    errors = []
    
    # General structure
    required_fields = ["title", "description", "image", "intro_text", "failure_text", "success_text", "chapters"]
    for field in required_fields:
        if field not in journey:
            errors.append(f"Missing field: {field}")
    
    if not journey.get("title"):
        errors.append("Journey title is required")
    
    if not journey.get("chapters"):
        errors.append("Journey must contain at least one chapter")
    
    # Validate chapters
    for chapter_num, chapter_data in journey.get("chapters", {}).items():
        if not isinstance(chapter_data, dict):
            errors.append(f"Chapter {chapter_num}: invalid structure")
            continue
            
        if not chapter_data.get("intro"):
            errors.append(f"Chapter {chapter_num}: missing introduction")
        
        challenges = chapter_data.get("challenges", [])
        if not challenges:
            errors.append(f"Chapter {chapter_num}: no challenges defined")
        
        for i, challenge in enumerate(challenges):
            if not isinstance(challenge, dict):
                errors.append(f"Chapter {chapter_num}, Challenge {i+1}: invalid structure")
                continue
                
            if not challenge.get("title"):
                errors.append(f"Chapter {chapter_num}, Challenge {i+1}: missing title")
            
            difficulty = challenge.get("difficulty")
            if difficulty not in ["easy", "medium", "hard", "extreme"]:
                errors.append(f"Chapter {chapter_num}, Challenge {i+1}: invalid difficulty ({difficulty})")
    
    return errors