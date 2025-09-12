# 🧭 On A Journey!

*Who knows where it might take you?*

A flexible RPG-style framework to gamify almost anything and create guided experiences with progressive unlocking, achievement systems, and customizable interactive challenges. Build anything from habit trackers to educational courses, interactive stories, or adventure games.

## Overview

On A Journey! is a Streamlit-based application that enables you to create and follow structured journeys. Each journey consists of chapters that unlock based on player level, achievements, and progression choices, creating authentic branching narratives with meaningful consequences.

### Key Features

- **RPG Progression System**: XP-based leveling, achievements, and character stats (avatar & world state)
- **Branching Narratives**: Chapters with achievement dependencies create meaningful choice consequences  
- **Interactive Challenges**: Custom Python code execution within challenges for rich interactivity
- **Level-Gated Content**: Chapters unlock based on player level and required achievements
- **Commitment Mechanics**: Irreversible choices that lock players into story paths
- **Smart Validation**: Daily validation credits maintain paced progression while allowing flexible scheduling
- **Visual Journey Editor**: Built-in editor for creating and modifying journeys without coding
- **Multi-User Support**: Individual accounts with isolated progress and achievement tracking

## Core Concepts

### Journey Structure
- **Chapters**: Narrative segments with titles, descriptions, and interactive challenges
- **Required Level**: Minimum XP level needed to access a chapter  
- **Dependencies**: Achievement prerequisites that gate access to content
- **Commitment System**: Completing challenges in level-matched chapters locks out alternatives

### Progression Mechanics
- **XP System**: Base XP (chapter level) + bonus XP (weighted challenge completion)
- **Level Formula**: `level = ⌊0.5 + 0.5√(1 + 16XP/3)⌋` (balanced for average 50% challenge completion)
- **Validation Credits**: Daily allowance preventing players from rushing through content
- **Achievement Trees**: Unlocking content through completing specific prerequisite achievements

### RPG Elements
- **Avatar State**: Player character stats (health, mana, strength, magic, etc.)
- **World State**: Global story state (location, flags, narrative progress)
- **Achievements**: Named accomplishments that unlock new content and define progression paths

## Use Cases

The framework's flexibility enables diverse applications:

- **Interactive Fiction**: Branching narratives with meaningful choices and consequences
- **Educational Courses**: Progressive skill-building with gated advanced content
- **Habit Tracking**: RPG-style progression for personal development goals
- **Training Programs**: Professional development with achievement-based advancement
- **Team Building**: Collaborative adventures with shared progress tracking
- **Therapeutic Journeys**: Guided self-improvement with paced, structured progression

## Installation

### Requirements

- Python 3.8+
- Streamlit
- TinyDB (for local test)
- MongoDB (for cloud use)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd on-a-journey
```

2. Install dependencies:
```bash
pip install streamlit tinydb plotly
```

3. Create the journeys directory:
```bash
mkdir journeys
```

4. Run the application:
```bash
streamlit run app.py
```

## Journey Creation

### Using the Visual Editor

1. **Access Editor**: Click "🔍 Journey Editor" from the main interface
2. **Create New Journey**: Choose "New journey" and set chapter count
3. **Design Chapters**: For each chapter, set:
   - **Title & Description**: For navigation and tooltips
   - **Required Level**: Minimum XP level to access
   - **Dependencies**: Achievement IDs required to unlock
   - **Introduction**: Narrative text displayed when entering the chapter
   - **Challenges**: Interactive elements with custom Python code

### Journey File Format

Journeys are stored as JSON files in the `journeys/` folder:

```json
{
  "title": "My Adventure",
  "description": "A branching story of choices and consequences",
  "intro_text": "Welcome message shown before starting",
  "success_text": "Victory message for journey completion", 
  "failure_text": "Shown when player gives up",
  "initial_avatar": "{\"health\": 100, \"mana\": 50, \"level\": 1}",
  "initial_world": "{\"location\": \"start\", \"chapter\": 1}",
  "chapters": {
    "1": {
      "title": "The Beginning",
      "description": "Your journey starts here",
      "intro": "Chapter introduction text...",
      "required_level": 1,
      "depends_on": [],
      "challenges": [
        {
          "title": "First Challenge",
          "description": "Challenge instructions...",
          "difficulty": "easy",
          "depends_on": [],
          "code": "st.write('Challenge code here...')"
        }
      ]
    }
  }
}
```

### Challenge Development

Challenges execute Python code with access to:

- **`st`**: Full Streamlit API for rich UI creation
- **`user`**: User data and progress
- **`avatar`**: Player character state (health, stats, inventory, etc.)
- **`world`**: Global story state and flags  
- **`chapter_num`**: Current chapter number
- **`new_achievement(id, title, description)`**: Function to unlock achievements
- **`validate(success)`**: Function to complete the challenge (True/False)

Example challenge code:
```python
st.write(f"Your health: {avatar.get('health', 100)}")
st.write(f"Current location: {world.get('location', 'unknown')}")

if st.button("Attempt dangerous action"):
    if avatar.get('strength', 0) >= 15:
        avatar['health'] += 10
        new_achievement('survivor', 'Survivor', 'Overcame a dangerous situation')
        st.success("Success! +10 health")
        validate(True)
    else:
        avatar['health'] -= 20
        st.error("Failed! -20 health") 
        validate(False)
```

## Architecture

The application follows a clean separation of concerns:

```
├── app.py           # Main Streamlit application and routing
├── business.py      # Core game logic, progression, and data management  
├── components.py    # UI components and user interface rendering
└── journeys/        # JSON journey files
```

### Core Systems

- **Authentication**: User accounts with hashed password storage
- **Progression Engine**: XP calculation, level determination, and achievement tracking
- **Accessibility Logic**: Centralized chapter/challenge access validation
- **Journey Management**: Loading, parsing, and validation of journey files
- **Challenge Execution**: Sandboxed Python code execution with game state access
- **Persistence**: TinyDB-based storage for user data and progress

## Configuration

### Database

Uses TinyDB with `on_a_journey_db.json` for data storage, including:
- User accounts with salted password hashes
- Journey progress and chapter completion status
- Achievement unlocking and challenge completion tracking
- Avatar and world state persistence

### Time Zone

Default timezone: `Europe/Paris`. Change in `business.py`:

```python
APP_TZ = ZoneInfo("Your/Timezone")
```

### God Mode

Enable in login for testing - bypasses time restrictions for validation credits while preserving all other game mechanics.

## API Reference

### Key Functions

#### Progression System
- `calculate_total_xp(user)`: Calculate player's total experience points
- `get_xp_progress(user)`: Get level progression info for display
- `calculate_level(xp)`: Convert XP to level using balanced formula
- `get_validation_credits(user)`: Check available daily validation allowance

#### Access Control  
- `is_chapter_accessible(user, chapter_num)`: Centralized chapter access validation
- `is_challenge_accessible(user, chapter_num, challenge_idx)`: Challenge access validation
- `has_achievements(user, required_achievements)`: Check achievement prerequisites

#### Journey Management
- `get_active_journey(user)`: Retrieve user's current journey
- `start_journey(user, start_date, journey)`: Initialize new journey for user
- `validate_chapter(user, chapter_num)`: Complete and validate a chapter
- `unlock_achievement(user, achievement_id, title, description)`: Award achievements

## Contributing

The codebase follows these principles:

1. **Clean Architecture**: Strict separation between UI, business logic, and data
2. **Type Safety**: Consistent use of type hints and validation
3. **User Experience**: Intuitive interfaces with helpful feedback and guidance
4. **Flexibility**: Support for diverse content types and use cases
5. **Security**: Safe code execution with controlled namespace access

## Examples

### Simple Habit Tracker
Create chapters for different habits with achievement unlocking based on consistency.

### Interactive Story
Branch narratives based on player choices, with achievements representing story paths and character development.

### Educational Course  
Progressive lessons with prerequisite knowledge, where advanced topics unlock based on mastering fundamentals.

### Team Adventure
Collaborative journey where team members' individual progress contributes to shared story advancement.

---

*Transform your daily experiences into engaging, progressive adventures with meaningful choices, rich interactivity, and personalized progression tracking.*