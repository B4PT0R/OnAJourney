# components.py
# UI Components for RPG-style streak challenge app

import streamlit as st
import time
import json
from datetime import date
from typing import Optional
from core.editor import editor
from core.utils import bytesio_to_base64, base64_to_bytesio

from core.business import (
    get_user, create_user, verify_password, 
    today, get_available_journeys, get_active_journey,
    calculate_challenge_xp,
    get_chapter_record, update_challenge_completion,
    validate_chapter, reset_journey, set_view, rerun, start_journey, 
    get_xp_progress, is_journey_completed, create_empty_journey, save_journey_to_file, 
    load_journey_for_editing, validate_journey_structure,
    get_challenge_weight, mark_intro_shown, create_challenge_namespace, update_user,
    can_validate_chapter, get_validation_credits, get_committed_chapter_for_level, 
    get_validated_chapter_for_level, has_achievements,
    is_chapter_accessible, is_challenge_accessible
)

# ---------------------------- Auth Components ---------------------------- #

def show_image(src):
    import io
    if isinstance(src,io.BytesIO):
        pass
    elif isinstance(src,str):
        if src.startswith('data:'):
            src=base64_to_bytesio(src)
    st.image(src,use_container_width=True)

def _render_title():
    st.title("🧭 On A Journey!")
    st.markdown("*Who knows where it might take you?*")

def _render_app_description():
    st.markdown("""
    🧭 **On A Journey!** transforms any experience into an engaging RPG adventure.
    
    Create **custom chapters** and **interactive challenges** that unlock as you progress. 
    Earn XP, unlock achievements, and make meaningful choices that shape your unique path.
    
    Perfect for habit tracking, learning journeys, team building, or interactive storytelling! ✨
    """)

def _render_auth_form():
    """Render the authentication form"""
    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        god_mode = st.checkbox(
            "🔧 God Mode", 
            help="Test mode - allows validating all chapters instantly"
        )
        
        submitted = st.form_submit_button("Login / Register", type="primary")
        return username, password, god_mode, submitted

def _handle_auth_submission(username, password, god_mode):
    """Handle authentication form submission"""
    if not username or not password:
        return
    
    st.session_state.god_mode = god_mode
    
    user = get_user(username)
    if user is None:
        user = create_user(username, password)
        st.success(f"Account created for {username}")
        if god_mode:
            st.info("🔧 God Mode enabled - you can validate all chapters!")
        st.session_state.user = user
        set_view("journey_start")
    else:
        if verify_password(password, user["salt"], user["pw_hash"]):
            st.success(f"Logged in as {username}")
            if god_mode:
                st.info("🔧 God Mode enabled - you can validate all chapters!")
            st.session_state.user = user
            if user.get("start_date"):
                set_view("chapter")
            else:
                set_view("journey_start")
        else:
            st.error("Incorrect password")

def render_auth():
    """Authentication page"""

    _render_title()

    st.divider()

    _render_app_description()

    st.divider()

    st.subheader("🔒 Login")
    
    username, password, god_mode, submitted = _render_auth_form()
    
    if submitted:
        _handle_auth_submission(username, password, god_mode)

# ---------------------------- Sidebar Components ---------------------------- #

def _render_user_info(user):
    """Render user info section"""
    st.header("👤 Session")
    st.write(f"**{user['username']}**")
    
    if st.session_state.get("god_mode", False):
        st.warning("🔧 God Mode ON")
    
    if st.button("Logout", key="logout"):
        st.session_state.user = None
        st.session_state.god_mode = False
        set_view("auth")

def _render_user_stats(user):
    """Render user statistics with XP/level progression"""
    st.header("📊 Status")
    
    xp_info = get_xp_progress(user)
    start_date = user.get("start_date", "Not started")
    
    journey = get_active_journey(user)
    if journey and start_date!="Not started":

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Level", f"{xp_info['current_level']}")
        with col2:
            progress_pct = xp_info["progress_in_level"]
            st.write(f"**Level {xp_info['current_level']} Progress**")
            st.progress(progress_pct)
            
            st.caption(f"XP: {xp_info['total_xp']:.1f} • "
                    f"To next level: {xp_info['xp_to_next']:.1f}")
        st.write(f"**Journey:** {journey.get('title', 'Untitled journey')}")
        st.write(f"**Started:** {start_date}")
    else:
        st.write("No current journey.")

def _render_journey_controls(user):
    """Render journey control buttons"""
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Journey Editor", key="editor_button", use_container_width=True):
            set_view("editor")
    
    with col2:
        if user.get("start_date"):
            if st.button("🚪 Give up journey", key="give_up_button", 
                        use_container_width=True, type="secondary"):
                st.session_state.confirm_give_up = True
    
    if st.session_state.get("confirm_give_up", False):
        st.warning("⚠️ This will reset all your progress!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, give up", key="confirm_yes", use_container_width=True):
                reset_journey(user)
                del st.session_state.confirm_give_up
        
        with col2:
            if st.button("❌ Cancel", key="confirm_no", use_container_width=True):
                del st.session_state.confirm_give_up

def render_sidebar(user: dict):
    """Render sidebar with user info and status"""
    with st.sidebar:
        _render_title()
        st.divider()
        _render_user_info(user)
        st.divider()
        _render_user_stats(user)
        _render_journey_controls(user)

# ---------------------------- Journey Start Components ---------------------------- #

def _render_journey_selection():
    """Render journey selection interface"""
    available_journeys = get_available_journeys()
    if not available_journeys:
        st.error("No journeys found in journeys/ folder")
        st.info("Place your JSON journey files in the journeys/ folder")
        return None
    
    journey_options = {journey["name"]: journey for journey in available_journeys}
    selected_journey_name = st.selectbox(
        "Choose your journey",
        options=list(journey_options.keys()),
        key="journey_selection"
    )
    
    selected_journey = journey_options[selected_journey_name]
    journey_structure = selected_journey["journey_structure"]
    
    st.info(f"**{journey_structure.get('title', selected_journey['name'])}** - {selected_journey['chapter_count']} chapters")
    
    if journey_structure.get("description"):
        st.markdown(f"*{journey_structure['description']}*")
    
    return selected_journey

def _render_timezone_selection():
    """Render timezone selection interface"""
    timezone_options = [
        "UTC",
        "Europe/Paris", "Europe/London", "Europe/Berlin", "Europe/Rome",
        "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
        "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Kolkata", "Asia/Dubai",
        "Australia/Sydney", "Australia/Melbourne",
        "Africa/Cairo", "Africa/Johannesburg",
        "Pacific/Auckland", "Pacific/Honolulu"
    ]
    
    return st.selectbox(
        "Your timezone",
        options=timezone_options,
        index=timezone_options.index("Europe/Paris"),  # Default to Paris
        key="user_timezone",
        help="This will be used for all time-related calculations during your journey"
    )

def _render_date_selection():
    """Render start date selection"""
    return st.date_input(
        "Start date",
        value=today(),
        key="journey_start_date"
    )

def render_journey_start(user: dict):
    """Journey start page"""
    st.subheader("🚀 Start a new journey")
    
    selected_journey = _render_journey_selection()
    if not selected_journey:
        return
    
    # Add timezone selection
    selected_timezone = _render_timezone_selection()
    start_date = _render_date_selection()
    
    _,c,_ = st.columns(3)
    with c:
        if st.button("🎯 Start adventure", type="primary", use_container_width=True):
            start_journey(user, start_date, selected_journey, selected_timezone)  # Modified call
            st.balloons()
            st.success("Adventure started! Good luck 🔥")

# ---------------------------- Intro View ---------------------------- #

def render_intro(user: dict):
    """Journey introduction view"""
    journey = get_active_journey(user)
    if not journey:
        set_view("journey_start")
        return
    
    st.subheader(f"🚀 {journey.get('title', 'Adventure')}")
    
    if journey.get("description"):
        st.info(journey["description"])

    if journey.get('image'):
        show_image(journey["image"])
    
    if journey.get("intro_text"):
        st.markdown(journey["intro_text"])
    else:
        st.markdown("**Ready to start this adventure?**")
    
    _,c,_ = st.columns(3)
    with c:
        if st.button("Go to chapters!", use_container_width=True, type="primary"):
            mark_intro_shown(user)
            set_view("chapter")


# ---------------------------- Chapter View Components ---------------------------- #

def _determine_chapter_to_show(user):
    """Determine which chapter should be displayed"""
    if "selected_chapter" in st.session_state:
        selected = st.session_state.selected_chapter
        access = is_chapter_accessible(user, selected)
        
        if access["accessible"]:
            return selected
        
        del st.session_state.selected_chapter
    
    set_view("chapters")
    return None

def render_chapters_view(user: dict):
    """Chapters overview - SIMPLIFIED with centralized logic"""
    journey = get_active_journey(user)
    if not journey:
        set_view("journey_start")
        return
    
    st.subheader(f"📖 {journey.get('title', 'Journey')}")

    if journey.get('image'):
        show_image(journey["image"])

    # Show achievements if any
    user_achievements = user.get("achievements", {})
    if user_achievements:
        with st.expander(f"🏆 Your Achievements ({len(user_achievements)})", expanded=False):
            for ach_data in user_achievements.values():
                title = ach_data.get("title", "Achievement")
                description = ach_data.get("description", "")
                if description:
                    st.write(f"• **{title}**: {description}")
                else:
                    st.write(f"• {title}")
    
    # Check for journey completion
    if is_journey_completed(user):
        st.success("🎉 Journey completed! All chapters validated.")
        if st.button("🏆 View completion", type="primary"):
            set_view("journey_completed")
        return
    
    # Group chapters by level for display
    st.markdown("### 📚 Chapters")
    
    chapters_data = user.get("chapters", {})
    user_level = get_xp_progress(user)["current_level"]
    
    # Group chapters by required level
    chapters_by_level = {}
    for chapter_num, journey_chapter in journey["chapters"].items():
        required_level = journey_chapter.get("required_level", 1)
        if required_level not in chapters_by_level:
            chapters_by_level[required_level] = []
        chapters_by_level[required_level].append((chapter_num, journey_chapter))
    
    # Display each level as a section
    for required_level in sorted(chapters_by_level.keys()):
        level_chapters = sorted(chapters_by_level[required_level])
        
        # Level header
        validated_chapter = get_validated_chapter_for_level(user, required_level)
        if validated_chapter:
            st.markdown(f"**📗 Level {required_level}** - ✅ Completed")
        else:
            # Check if any chapter at this level is accessible
            any_accessible = any(is_chapter_accessible(user, ch_num)["accessible"] for ch_num, _ in level_chapters)
            icon = "📘" if any_accessible else "📕"
            st.markdown(f"**{icon} Level {required_level}**")
        
        # Display chapters in columns for this level
        cols = st.columns(min(len(level_chapters), 6))
        for i, (chapter_num, journey_chapter) in enumerate(level_chapters):
            with cols[i % len(cols)]:
                _render_chapter_button(user, chapter_num, journey_chapter, chapters_data)
        
        st.write("")  # Add spacing between levels

def _render_chapter_button(user: dict, chapter_num: int, journey_chapter: dict, chapters_data: dict):
    """Render a single chapter button - ULTRA simplified with centralized logic"""
    
    # Get chapter info
    chapter_title = journey_chapter.get("title", f"Chapter {chapter_num}")
    chapter_description = journey_chapter.get("description", "")
    chapter_record = chapters_data.get(str(chapter_num), {})
    is_validated = chapter_record.get("validated", False)
    
    # Use centralized accessibility check
    access = is_chapter_accessible(user, chapter_num)
    
    # Determine button appearance
    if is_validated:
        button_text = f"✅ {chapter_title}"
        button_type = "secondary" 
        help_text = "Chapter completed"
        disabled = False
    elif access["accessible"]:
        # Check if committed/in progress
        committed_chapter = access.get("committed_chapter")
        if committed_chapter == chapter_num:
            button_text = f"🎯 {chapter_title}"
            help_text = "Committed - In progress"
        else:
            button_text = f"⭐ {chapter_title}"
            help_text = chapter_description or "Available"
        button_type = "primary"
        disabled = False
    else:
        button_text = f"🔒 {chapter_title}"
        button_type = "secondary"
        disabled = True
        
        # Show specific reason for blocking
        if access["reason"] == "insufficient_level":
            help_text = f"Requires level {access['required_level']} (you are level {access['user_level']})"
        elif access["reason"] == "missing_achievements":
            missing = ", ".join(access["missing_achievements"])
            help_text = f"Missing: {missing}"
        elif access["reason"] == "committed_elsewhere":
            help_text = f"Path closed - committed to Chapter {access['committed_chapter']}"
        else:
            help_text = chapter_description or "Not accessible"
    
    # Single button with all logic handled by centralized function
    if st.button(button_text, 
                key=f"chapter_btn_{chapter_num}",
                disabled=disabled,
                type=button_type,
                use_container_width=True,
                help=help_text):
        st.session_state.selected_chapter = chapter_num
        set_view("chapter")

def _render_commitment_warning(user, chapter_to_show):
    """Warn user about irrevocable commitment"""
    journey = get_active_journey(user)
    required_level = journey["chapters"][chapter_to_show].get("required_level", 1)
    committed_chapter = get_committed_chapter_for_level(user, required_level)
    
    if not committed_chapter and not st.session_state.get("god_mode", False):
        chapters_at_level = [
            num for num, ch in journey["chapters"].items() 
            if ch.get("required_level", 1) == required_level
        ]
        
        if len(chapters_at_level) > 1:
            st.warning(
                f"⚠️ **Important:** Starting a challenge will commit you to this chapter path. "
                f"You won't be able to access other Level {required_level} chapters after this choice."
            )

def render_chapter_view(user: dict):
    """Current chapter view"""
    _,c=st.columns([80,20])
    with c:
        if st.button("← Back to chapters", type="tertiary", key="back_to_chapters"):
            if "selected_chapter" in st.session_state:
                del st.session_state.selected_chapter
            set_view("chapters")
    
    chapter_to_show = _determine_chapter_to_show(user)
    if not chapter_to_show:
        return
    
    chapter_record = get_chapter_record(user, chapter_to_show)
    challenges = chapter_record.get("challenges", [])
    
    # Render components
    can_validate, is_validated = _render_chapter_header(chapter_to_show, chapter_record, user)
    _render_commitment_warning(user, chapter_to_show)
    _render_chapter_intro(chapter_record)
    _render_challenges_list(user, chapter_to_show, challenges, is_validated, True)
    _render_xp_preview(chapter_to_show, challenges, user)
    _render_chapter_action_buttons(user, chapter_to_show, is_validated, can_validate)

def _render_chapter_header(chapter_to_show, chapter_record, user):
    """Render chapter header with status"""
    chapter_date = date.fromisoformat(chapter_record["date"])
    is_validated = chapter_record.get("validated", False)
    can_validate = can_validate_chapter(user, chapter_to_show)
    
    st.subheader(f"Chapter {chapter_to_show} - {chapter_date.strftime('%A %m/%d/%Y')}")
    
    if is_validated:
        journey = get_active_journey(user)
        required_level = journey["chapters"][chapter_to_show].get("required_level", chapter_to_show)
        
        base_xp = required_level
        challenge_xp = calculate_challenge_xp(required_level, chapter_record.get("challenges", []))
        total_xp = base_xp + challenge_xp
        st.success(f"✅ Chapter validated - XP gained: {total_xp:.1f}")
    elif can_validate:
        credits = get_validation_credits(user)
        st.info(f"🎯 Chapter ready for validation ({credits} validation credits available)")
    else:
        credits = get_validation_credits(user)
        st.warning(f"⏳ Chapter in progress - {credits} validation credits available")
    
    return can_validate, is_validated

def _render_chapter_intro(chapter_record):
    """Render chapter introduction text"""
    if chapter_record.get("title"):
        st.header(chapter_record["title"])

    if chapter_record.get("image"):
        show_image(chapter_record['image'])
    else:
        st.warning("No image to show")
    
    if chapter_record.get("intro"):
        st.markdown(chapter_record["intro"])

def _render_challenge_item(user, chapter_to_show, challenge, challenge_idx, is_validated, is_elapsed):
    """Render a single challenge item - SIMPLIFIED with centralized accessibility"""
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**{challenge['title']}**")
            if challenge.get("description"):
                st.markdown(challenge["description"])
                
            difficulty = challenge.get("difficulty", "easy")
            difficulty_emoji = {
                "easy": "🟢", "medium": "🟡", 
                "hard": "🟠", "extreme": "🔴"
            }
            st.caption(f"{difficulty_emoji.get(difficulty, '🟢')} {difficulty.title()}")
            
            # Show missing achievements if any
            access = is_challenge_accessible(user, chapter_to_show, challenge_idx)
            if not access["accessible"] and access["reason"] == "missing_achievements":
                st.caption(f"🔒 Requires: {', '.join(access['missing_achievements'])}")

        with col2:
            if challenge.get("completed", False):
                st.write("✅")
            else:
                access = is_challenge_accessible(user, chapter_to_show, challenge_idx)
                if access["accessible"]:
                    if st.button("🎮 Run", key=f"run_challenge_{chapter_to_show}_{challenge_idx}"):
                        st.session_state.current_challenge = {
                            "challenge": challenge,
                            "chapter": chapter_to_show,
                            "index": challenge_idx
                        }
                        set_view("challenge")
                else:
                    st.write("❌")

def render_challenge_view(user: dict):
    """Render interactive challenge view with RPG context"""
    if "current_challenge" not in st.session_state:
        set_view("chapter")
        return
    
    challenge_data = st.session_state.current_challenge
    challenge = challenge_data["challenge"]
    chapter_num = challenge_data["chapter"]
    
    st.subheader(f"🎮 {challenge['title']}")

    if challenge.get('image'):
        show_image(challenge['image'])
    
    # Default code if empty
    code = challenge.get("code", "").strip()
    if not code:
        code = '''
st.title(challenge['title'])
st.write(challenge['description'])
st.divider()
st.write("Did you complete the challenge?")
def on_click(response):
    validate(response)
a,b=st.columns(2)
with a:
    st.button("Yes",on_click=on_click,args=(True,))
with b:
    st.button("No",on_click=on_click,args=(False,))
'''
    
    # Create RPG namespace
    challenge_globals = create_challenge_namespace(user, chapter_num)
    challenge_globals["challenge"] = challenge
    challenge_globals["validate"] = lambda success: _validate_challenge(user, challenge_data, success)
    
    try:
        exec(code, challenge_globals)
        update_user(user)
    except Exception as e:
        st.error(f"Challenge error: {e}")
        if st.button("← Back to chapter"):
            del st.session_state.current_challenge
            set_view("chapter")

def _validate_challenge(user: dict, challenge_data: dict, success: bool):
    """Validate challenge and return to chapter view"""
    chapter_num = challenge_data["chapter"]
    challenge_idx = challenge_data["index"]
    
    update_challenge_completion(user, chapter_num, challenge_idx, success)
    
    with st.spinner("Processing your choice..."):
        time.sleep(5)
    
    del st.session_state.current_challenge
    set_view("chapter")
    rerun()

def _render_challenges_list(user, chapter_to_show, challenges, is_validated, is_elapsed):
    """Render the list of challenges"""
    st.markdown("### 🎯 Today's challenges")
    
    if not challenges:
        st.info("No challenges for this chapter")
        return
    
    for i, challenge in enumerate(challenges):
        _render_challenge_item(user, chapter_to_show, challenge, i, is_validated, is_elapsed)

def _render_xp_preview(chapter_to_show, challenges, user):
    """Render XP preview metrics"""
    if not challenges:
        return
    
    journey = get_active_journey(user)
    required_level = journey["chapters"][chapter_to_show].get("required_level", chapter_to_show)
    
    base = required_level
    bonus = sum(get_challenge_weight(ch["difficulty"]) for ch in challenges if ch.get("completed", False))
    total_weight = sum(get_challenge_weight(ch["difficulty"]) for ch in challenges)
    challenge_xp = (required_level * (bonus / total_weight)) if total_weight > 0 else 0
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Base XP", f"{base:.1f}")
    col2.metric("Challenge bonus", f"{challenge_xp:.1f}")
    col3.metric("Total XP", f"{base + challenge_xp:.1f}")

def _render_validation_animation():
    """Render validation success animation"""
    st.balloons()
    st.success("🔥 Chapter validated! XP gained!")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(3):
        status_text.text(f"Back to chapters in {3-i} seconds...")
        progress_bar.progress((i + 1) / 3)
        time.sleep(1)
    
    status_text.text("Let's explore! 🗺️")
    time.sleep(0.5)
    
    set_view("chapters")

def _render_chapter_action_buttons(user, chapter_to_show, is_validated, can_validate):
    """Render validation button only"""
    if not is_validated and can_validate:
        st.divider()
        
        if st.button("🎆 I completed my chapter!", type="primary", key="validate", use_container_width=True):
            validate_chapter(user, chapter_to_show)
            _render_validation_animation()
            rerun()

# ---------------------------- Other Views ---------------------------- #

def render_journey_failed(user: dict):
    """Failure page with custom text"""
    journey = get_active_journey(user)
    
    st.subheader("💥 Oops...")
    
    failure_text = journey.get("failure_text") if journey else None
    if failure_text:
        st.markdown(failure_text)
    else:
        st.markdown("""
        ### Don't panic! 
        
        Failures are part of the learning process.
                    
        The important thing is not to get discouraged and start again stronger.
                    
        Every attempt makes you stronger and teaches you something about yourself.
                    
        With perseverance comes mastery.
        
        **Ready for a new attempt?**
        """)
    
    if st.button("🔥 Start new adventure", type="primary"):
        set_view("journey_start")

def render_journey_completed(user: dict):
    """Journey completion page with custom text"""
    journey = get_active_journey(user)
    
    st.subheader("🏆 Adventure Completed!")
    
    success_text = journey.get("success_text") if journey else None
    if success_text:
        st.markdown(success_text)
    else:
        st.markdown("""
        ### Congratulations! 
        
        You have completed your adventure without giving up once.   
                    
        This is a remarkable achievement that demonstrates your determination and discipline.
                    
        You can be proud of the journey you've taken and the challenges you've overcome.
                    
        **Ready for a new adventure?**
        """)
    
    if st.button("🚀 New Adventure", type="primary"):
        set_view("journey_start")

# ---------------------------- Editor Components ---------------------------- #

def _render_editor_header():
    """Render editor header with journey selection"""
    st.subheader("📝 Journey Editor")
    col1, col2 = st.columns([90, 10])
    
    if not st.session_state.get("editing_journey"):
        options = ["New journey", "Edit existing"]

        with col1:
            def on_change():
                mode = st.session_state.get("editor_mode", "New journey")
                st.session_state.edition_mode = mode

            mode = st.radio(
                "Edit mode",
                options=options,
                horizontal=True,
                key="editor_mode",
                index=options.index(st.session_state.get("edition_mode", "New journey")),
                on_change=on_change
            )
        
        with col2:
            if st.button("← Back", type="tertiary", key="editor_back"):
                set_view("journey_start")

    elif st.session_state.get("editing_journey"):
        mode = st.session_state.get("edition_mode", "New journey")
        with col1:
            st.markdown(f"**Editing: {st.session_state.editing_journey.get('title', 'Untitled journey')}**")
        with col2:
            def on_click():
                del st.session_state.editing_journey
            st.button("← Back", type="tertiary", key="editor_back2", on_click=on_click)

    return mode

def _render_new_journey_form():
    """Render form for creating new journey"""
    with st.form("new_journey_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            journey_name = st.text_input("Journey name", value="My Adventure")
        
        with col2:
            chapters_count = st.number_input("Number of chapters", min_value=1, max_value=365, value=7)
        
        if st.form_submit_button("Create journey", type="primary"):
            if journey_name:
                journey = create_empty_journey(journey_name, chapters_count)
                st.session_state.editing_journey = journey
                st.rerun()
            else:
                st.error("Journey name is required")

def _render_existing_journey_selector():
    """Render selector for existing journeys"""
    available_journeys = get_available_journeys()
    if not available_journeys:
        st.info("No existing journeys found")
        return
    
    journey_names = [journey["name"] + ".json" for journey in available_journeys]
    selected_file = st.selectbox("Choose a journey to edit", journey_names)
    
    if st.button("Load for editing", type="primary"):
        journey = load_journey_for_editing(selected_file)
        if journey:
            st.session_state.editing_journey = journey
            st.rerun()
        else:
            st.error("Error loading journey")

def _render_image_selector(target,key):
    toggled=st.toggle("Add an illustrative image",key=f"image_toggle_{key}")
    if toggled:
        with st.container(border=True):
            url=st.text_input("Enter an image url:",key=f"image_url_{key}")
            if url:
                target['image']=url
            bytesio=st.file_uploader("Or upload a local image",type=['jpg','jpeg','png','gif'],key=f"image_upload_{key}")
            if bytesio:
                target['image']=bytesio_to_base64(bytesio)

            if target.get('image'):
                st.caption("Preview:")
                _,c,_=st.columns([20,60,20])
                with c:
                    show_image(target['image'])



def _render_journey_editor(journey):
    """Render the main journey editor interface"""
    
    # Journey metadata
    st.markdown("### General information")
    
    journey["title"] = st.text_input("Journey title", value=journey.get("title", ""), key="journey_title")
    journey["description"] = st.text_area("Short description", value=journey.get("description", ""), height=68, key="journey_description")

    _render_image_selector(journey,"journey")

    # RPG Initial States
    with st.expander("🎮 RPG Initial States", expanded=False):
        st.markdown("**Initial Avatar State (JSON)**")
        avatar_json = st.text_area(
            "Avatar state",
            value=journey.get("initial_avatar", "{}"),
            height=120,
            key="journey_avatar",
            help="JSON object defining initial avatar attributes"
        )
        
        st.markdown("**Initial World State (JSON)**")
        world_json = st.text_area(
            "World state",
            value=journey.get("initial_world", "{}"),
            height=120,
            key="journey_world",
            help="JSON object defining initial world state"
        )
        
        # Validate JSON
        try:
            journey["initial_avatar"] = avatar_json
            json.loads(avatar_json)
            st.success("✅ Avatar JSON is valid")
        except json.JSONDecodeError as e:
            st.error(f"❌ Avatar JSON error: {e}")
        
        try:
            journey["initial_world"] = world_json
            json.loads(world_json)
            st.success("✅ World JSON is valid")
        except json.JSONDecodeError as e:
            st.error(f"❌ World JSON error: {e}")
    
    # Texts
    with st.expander("📜 Journey texts", expanded=False):
        journey["intro_text"] = st.text_area("Introduction text", value=journey.get("intro_text", ""), height=120, key="journey_intro")
        journey["success_text"] = st.text_area("Success text", value=journey.get("success_text", ""), height=120, key="journey_success")
        journey["failure_text"] = st.text_area("Failure text", value=journey.get("failure_text", ""), height=120, key="journey_failure")
    
    # Journey stats
    chapters_count = len(journey.get("chapters", {}))
    total_challenges = sum(len(chapter.get("challenges", [])) for chapter in journey["chapters"].values())
    st.info(f"📊 {chapters_count} chapters • {total_challenges} total challenges")
    
    # Chapters editor
    st.markdown("### Journey chapters")
    
    chapters = journey.get("chapters", {})
    if not chapters:
        st.info("No chapters defined. Click 'Add chapter' to start.")
        if st.button("➕ Add first chapter", key="add_first_chapter"):
            chapters[1] = {
                "intro": "Chapter 1 - Introduction...",
                "challenges": [],
                "required_level": 1,
                "depends_on": []
            }
            st.rerun()
    else:
        for chapter_num in sorted(chapters.keys()):
            _render_chapter_editor(journey, chapter_num)

    _render_save_controls(journey)

def _render_chapter_editor(journey, chapter_num):
    """Render editor for a single chapter with controls"""
    chapter_data = journey["chapters"][chapter_num]
    chapters = journey["chapters"]
    chapter_numbers = sorted(chapters.keys())
    is_first = chapter_num == min(chapter_numbers)
    is_last = chapter_num == max(chapter_numbers)
    
    with st.expander(f"Chapter {chapter_num}", expanded=chapter_num == 1):
        # Chapter controls (delete, move, etc.)
        _, col1, col2, col3, col4 = st.columns([80, 5, 5, 5, 5])
        
        with col1:
            disabled = len(chapters) <= 1
            if st.button("🗑️", key=f"delete_chapter_{chapter_num}", help="Delete this chapter", type="tertiary", disabled=disabled):
                _delete_chapter(journey, chapter_num)
                st.rerun()
        
        with col2:
            if st.button("⬆️", key=f"moveup_chapter_{chapter_num}", help="Move up", type="tertiary", disabled=is_first):
                _move_chapter_up(journey, chapter_num)
                st.rerun()
        
        with col3:
            if st.button("⬇️", key=f"movedown_chapter_{chapter_num}", help="Move down", type="tertiary", disabled=is_last):
                _move_chapter_down(journey, chapter_num)
                st.rerun()
        
        with col4:
            if st.button("➕", key=f"insert_chapter_{chapter_num}", help="Insert chapter after", type="tertiary"):
                _insert_chapter_after(journey, chapter_num)
                st.rerun()

        # NOUVEAU : Chapter metadata (title & description)
        st.markdown("**Chapter Information**")
        col1, col2= st.columns(2)
        
        with col1:
            chapter_title = st.text_input(
                "Chapter Title",
                value=chapter_data.get("title", f"Chapter {chapter_num}"),
                key=f"chapter_title_{chapter_num}",
                help="Short title for navigation buttons"
            )
            chapter_data["title"] = chapter_title
        
        with col2:
            chapter_description = st.text_input(
                "Chapter Description",
                value=chapter_data.get("description", ""),
                key=f"chapter_description_{chapter_num}",
                help="Description shown in button tooltips"
            )
            chapter_data["description"] = chapter_description

        # Chapter settings (niveau requis, dépendances)
        col1, col2 = st.columns([70, 30])
        
        with col1:
            new_intro = st.text_area(
                f"Chapter {chapter_num} introduction",
                value=chapter_data.get("intro", ""),
                key=f"intro_{chapter_num}",
                height=125
            )
            chapter_data["intro"] = new_intro
        
        with col2:
            required_level = st.number_input(
                "Required level",
                min_value=1,
                max_value=200,
                value=chapter_data.get("required_level", 1),
                key=f"required_level_{chapter_num}",
                help="Player level required to access this chapter"
            )
            chapter_data["required_level"] = required_level
            
            # Dependencies control
            depends_on_str = st.text_input(
                "Depends on",
                value=",".join(chapter_data.get("depends_on", [])),
                key=f"depends_on_{chapter_num}",
                help="Achievement IDs required (comma-separated)"
            )
            # Parse dependencies
            if depends_on_str.strip():
                chapter_data["depends_on"] = [dep.strip() for dep in depends_on_str.split(",") if dep.strip()]
            else:
                chapter_data["depends_on"] = []
        
        _render_image_selector(chapter_data,key=chapter_num)

        # Challenges section
        st.markdown("**Challenges:**")
        with st.container(border=True):
            _render_challenges_tabs(journey, chapter_num)

def _render_challenges_tabs(journey, chapter_num):
    """Render challenges using tabs interface"""
    challenges = journey["chapters"][chapter_num]["challenges"]
    
    if not challenges:
        st.info("No challenges for this chapter")
        if st.button(f"➕ Add first challenge", key=f"add_first_challenge_{chapter_num}"):
            challenges.append({
                "title": "New challenge",
                "description": "Description...",
                "difficulty": "easy",
                "completed": False,
                "depends_on": []
            })
            st.rerun()
        return
    
    # Create tabs for challenges
    tab_names = []
    for i, challenge in enumerate(challenges):
        title = challenge.get("title", f"Challenge {i+1}")
        if len(title) > 15:
            title = title[:12] + "..."
        tab_names.append(f"{i+1}. {title}")
    
    tab_names.append("➕ New")
    
    tabs = st.tabs(tab_names)
    
    # Render existing challenges
    for i, (tab, challenge) in enumerate(zip(tabs[:-1], challenges)):
        with tab:
            _render_single_challenge_form(journey, chapter_num, i, challenge)
    
    # Render "add new" tab
    with tabs[-1]:
        st.markdown("**Add new challenge**")
        if st.button("➕ Create", key=f"create_challenge_{chapter_num}"):
            challenges.append({
                "title": "New challenge",
                "description": "Description...",
                "difficulty": "easy",
                "completed": False,
                "depends_on": []
            })
            st.rerun()

def _render_single_challenge_form(journey, chapter_num, challenge_idx, challenge):
    """Render form for a single challenge"""
    challenges = journey["chapters"][chapter_num]["challenges"]
    is_first = challenge_idx == 0
    is_last = challenge_idx == len(challenges) - 1
    
    _, col1, col2, col3, col4 = st.columns([80, 5, 5, 5, 5])
    
    with col1:
        disabled = len(challenges) <= 1
        if st.button("🗑️", key=f"delete_challenge_{chapter_num}_{challenge_idx}", help="Delete", type="tertiary", disabled=disabled):
            challenges.pop(challenge_idx)
            st.rerun()
    
    with col2:
        if st.button("⬅️", key=f"moveleft_challenge_{chapter_num}_{challenge_idx}", help="Move left", type="tertiary", disabled=is_first):
            challenges[challenge_idx], challenges[challenge_idx-1] = challenges[challenge_idx-1], challenges[challenge_idx]
            st.rerun()
    
    with col3:
        if st.button("➡️", key=f"moveright_challenge_{chapter_num}_{challenge_idx}", help="Move right", type="tertiary", disabled=is_last):
            challenges[challenge_idx], challenges[challenge_idx+1] = challenges[challenge_idx+1], challenges[challenge_idx]
            st.rerun()
    
    with col4:
        if st.button("📋", key=f"duplicate_challenge_{chapter_num}_{challenge_idx}", help="Duplicate", type="tertiary"):
            new_challenge = {
                "title": challenge["title"] + " (copy)",
                "description": challenge["description"],
                "difficulty": challenge["difficulty"],
                "completed": False,
                "depends_on": challenge.get("depends_on", [])
            }
            challenges.insert(challenge_idx + 1, new_challenge)
            st.rerun()
    
    c1, c2, c3 = st.columns([40, 30, 30])
    with c1:
        challenge["title"] = st.text_input(
            "Challenge title",
            value=challenge.get("title", ""),
            key=f"challenge_title_{chapter_num}_{challenge_idx}",
            help="Short and descriptive challenge name"
        )
    
    with c2:
        difficulty_options = ["easy", "medium", "hard", "extreme"]
        challenge["difficulty"] = st.selectbox(
            "Challenge difficulty",
            options=difficulty_options,
            index=difficulty_options.index(challenge.get("difficulty", "easy")),
            key=f"challenge_difficulty_{chapter_num}_{challenge_idx}",
            help="Difficulty and impact on XP"
        )
    
    with c3:
        depends_on_str = st.text_input(
            "Depends on",
            value=",".join(challenge.get("depends_on", [])),
            key=f"challenge_depends_on_{chapter_num}_{challenge_idx}",
            help="Achievement IDs required"
        )
        # Parse dependencies
        if depends_on_str.strip():
            challenge["depends_on"] = [dep.strip() for dep in depends_on_str.split(",") if dep.strip()]
        else:
            challenge["depends_on"] = []

    _render_image_selector(challenge,key=f"{chapter_num}_{challenge_idx}")
    
    challenge["description"] = st.text_area(
        "Detailed description",
        value=challenge.get("description", ""),
        key=f"challenge_desc_{chapter_num}_{challenge_idx}",
        height=120,
        help="Complete instructions to complete this challenge"
    )

    toggled = st.toggle("Show challenge code", key=f"code_toggle_{chapter_num}_{challenge_idx}")
    if toggled:
        st.info("Complete Streamlit code. Access: st, user, avatar, world, chapter_num, new_achievement, validate(bool)")
        challenge["code"] = editor(
            code=challenge.get("code", ""),
            lang="python",
            key=f"challenge_code_{chapter_num}_{challenge_idx}",
        )
        if challenge.get("code"):
            try:
                compile(challenge.get("code", ""), "<challenge_code>", "exec")
            except SyntaxError as e:
                st.error(f"Syntax error in challenge code: {e}")

def _render_save_controls(journey):
    """Render save and validation controls"""
    # Validation
    errors = validate_journey_structure(journey)
    if errors:
        st.error("Errors detected:")
        for error in errors:
            st.write(f"• {error}")
    else:
        st.success("Journey valid ✅")
    
    # Save button centered
    _, c, _ = st.columns([30, 40, 30])
    with c:
        if st.button("💾 Save", type="secondary", use_container_width=True, disabled=len(errors) > 0):
            if save_journey_to_file(journey):
                st.success("Journey saved!")
            else:
                st.error("Error saving journey")

# Helper functions for chapter manipulation
def _delete_chapter(journey, chapter_num):
    """Delete a chapter and renumber subsequent chapters"""
    chapters = journey["chapters"]
    if len(chapters) <= 1:
        st.error("Cannot delete the last chapter")
        return
    
    del chapters[chapter_num]
    _renumber_chapters(journey)

def _move_chapter_up(journey, chapter_num):
    """Move chapter up in order"""
    chapters = journey["chapters"]
    chapter_numbers = sorted(chapters.keys())
    
    if chapter_num == min(chapter_numbers):
        return
    
    current_idx = chapter_numbers.index(chapter_num)
    prev_chapter = chapter_numbers[current_idx - 1]
    
    chapters[chapter_num], chapters[prev_chapter] = chapters[prev_chapter], chapters[chapter_num]

def _move_chapter_down(journey, chapter_num):
    """Move chapter down in order"""
    chapters = journey["chapters"]
    chapter_numbers = sorted(chapters.keys())
    
    if chapter_num == max(chapter_numbers):
        return
    
    current_idx = chapter_numbers.index(chapter_num)
    next_chapter = chapter_numbers[current_idx + 1]
    
    chapters[chapter_num], chapters[next_chapter] = chapters[next_chapter], chapters[chapter_num]

def _insert_chapter_after(journey, chapter_num):
    """Insert a new chapter after the specified chapter"""
    chapters = journey["chapters"]
    
    chapter_numbers = sorted(chapters.keys(), reverse=True)
    for chapter in chapter_numbers:
        if chapter > chapter_num:
            chapters[chapter + 1] = chapters[chapter]
            del chapters[chapter]
    
    chapters[chapter_num + 1] = {
        "intro": f"Chapter {chapter_num + 1} - Introduction...",
        "challenges": [],
        "required_level": 1,
        "depends_on": []
    }

def _renumber_chapters(journey):
    """Renumber all chapters to be consecutive starting from 1"""
    chapters = journey["chapters"]
    old_chapters = dict(chapters)
    chapters.clear()
    
    for i, (_, chapter_data) in enumerate(sorted(old_chapters.items()), 1):
        chapters[i] = chapter_data

def render_editor(user: dict):
    """Main editor page"""
    mode = _render_editor_header()
    
    if "editing_journey" not in st.session_state:
        if mode == "New journey":
            _render_new_journey_form()
        else:
            _render_existing_journey_selector()
    else:
        journey = st.session_state.editing_journey
        _render_journey_editor(journey)