# 🧭 On A Journey!

*Who knows where it might take you?*

A flexible RPG-style framework to gamify almost anything and create guided experiences with progressive unlocking, achievement systems, and customizable interactive challenges. Build anything from habit trackers to educational courses, interactive stories, or adventure games.

## Where do I try?

Try it [here](https://onajourney.streamlit.app/) on Streamlit cloud.

## Overview

On A Journey! is a Streamlit-based application that enables you to create and follow structured journeys. Each journey consists of chapters that unlock based on player level, achievements, and progression choices, creating authentic branching narratives with meaningful consequences.

While it provides a basic game engine that will work out the box for simple cases, it is designed to let the creator of the journey completely free to organize the chapters' progression and manage the interactivity and logic happening in the challenges.

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
- **Validation Credits**: Daily allowance of one validation credit preventing players from rushing through content
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
cd <repository-folder>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run app.py
```

## Journey Creation

### Using the Visual Editor

1. **Access Editor**: Click on the "🔍 Journey Editor" button in the sidebar
2. **Create New Journey**: Choose "New journey" and set chapter count (you can add more later)
3. **Design Chapters**: For each chapter, set:
   - **Title & Description**: For navigation and tooltips
   - **Optional Image**: To illustrate the journey.
   - **Required Level**: Minimum XP level to access
   - **Dependencies**: Achievement IDs required to unlock
   - **Introduction**: Narrative text displayed when entering the chapter
   - **Challenges**: Interactive elements with optional custom Python code

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

### Core Systems

- **Authentication**: User accounts with hashed password storage
- **Progression Engine**: XP calculation, level determination, and achievement tracking
- **Accessibility Logic**: Centralized chapter/challenge access validation
- **Journey Management**: Loading, parsing, and validation of journey files
- **Challenge Execution**: secured sandboxed Python code execution with game state access
- **Persistence**: TinyDB/MongoDB-based storage for user data and progress

## Configuration

### Database

Uses TinyDB with `on_a_journey_db.json` for data storage by default, including:
- User accounts with salted password hashes
- Journey progress and chapter completion status
- Achievement unlocking and challenge completion tracking
- Avatar and world state persistence

Can be set to use MongoDB to use a remote database by providing a MONGODB_URI environment variable (or via secrets.toml)

### God Mode

Enable in login for testing - bypasses time restrictions for validation credits while preserving all other game mechanics.

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