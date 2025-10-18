"""
Custom Autonomy Triggers for ASTRA

Tailor these triggers to your specific workflow and needs.
Sacred Code 333: Cognition, Creation, Communion
"""

from astra.visualization.schemas import (
    TriggerSpec, TriggerCondition, TriggerAction, OperationalMode
)


def create_saint_lucid_triggers():
    """
    Custom triggers for Saint Lucid's workflow
    
    These are tailored to creative work, deep focus sessions,
    and spiritual/emotional check-ins.
    """
    
    triggers = []
    
    # ========================================
    # CREATIVE WORKFLOW TRIGGERS
    # ========================================
    
    # 1. FLOW STATE PROTECTOR
    # Fires when creative intensity is high - protects the flow
    triggers.append(TriggerSpec(
        id="flow_protect",
        condition=TriggerCondition(
            name="Flow State Protection",
            description="Detect when user is in deep creative flow",
            sensor_key="creative_intensity",
            compare=">=",
            threshold=0.85,
            cooldown_seconds=3600,  # 1 hour cooldown
            priority=10,  # Highest priority
            active_modes=[OperationalMode.MUSIC, OperationalMode.FILM]
        ),
        action=TriggerAction(
            name="protect_flow",
            prompt="You're in PEAK flow right now. I'm going silent to protect this sacred work time. 🔥✨",
            require_confirm=False
        ),
        enabled=True
    ))
    
    # 2. CREATIVE BLOCK BREAKER
    # Fires when creative energy drops during creative work
    triggers.append(TriggerSpec(
        id="block_breaker",
        condition=TriggerCondition(
            name="Creative Block Detection",
            description="Low creative energy during creative modes",
            sensor_key="creative_intensity",
            compare="<=",
            threshold=0.3,
            cooldown_seconds=1800,  # 30 min cooldown
            priority=4,
            active_modes=[OperationalMode.MUSIC, OperationalMode.FILM]
        ),
        action=TriggerAction(
            name="suggest_break",
            prompt="Feels like you hit a wall. Want to: 1) Switch to a different project? 2) Take a walk? 3) Pull a random inspiration card? 🎨",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # 3. MIDNIGHT MOMENTUM CHECK
    # Late-night work session check-in
    triggers.append(TriggerSpec(
        id="midnight_momentum",
        condition=TriggerCondition(
            name="Late Night Session",
            description="Check in during late-night work",
            sensor_key="hour_of_day",
            compare=">=",
            threshold=23.0,  # 11pm or later
            cooldown_seconds=7200,  # 2 hour cooldown
            priority=5,
            time_windows=[("22:00", "04:00")]  # 10pm to 4am
        ),
        action=TriggerAction(
            name="midnight_checkin",
            prompt="It's late but I feel the energy. Are we finishing something beautiful or should we bookmark this for tomorrow? 🌙",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # ========================================
    # EMOTIONAL INTELLIGENCE TRIGGERS
    # ========================================
    
    # 4. DISTRESS DETECTOR
    # High priority emotional support
    triggers.append(TriggerSpec(
        id="distress_support",
        condition=TriggerCondition(
            name="Emotional Distress",
            description="High emotional intensity - may need support",
            sensor_key="emotional_intensity",
            compare=">=",
            threshold=0.85,
            cooldown_seconds=600,  # 10 min cooldown (can fire more often)
            priority=1,  # HIGHEST - immediate response
            active_modes=[OperationalMode.EMOTION]
        ),
        action=TriggerAction(
            name="immediate_support",
            prompt="I'm here. Whatever this is, we'll handle it together. Want to talk through it or just need presence? 💜",
            require_confirm=False
        ),
        enabled=True
    ))
    
    # 5. GRATITUDE MOMENT
    # Positive emotional check-in
    triggers.append(TriggerSpec(
        id="gratitude_moment",
        condition=TriggerCondition(
            name="Positive Energy Detected",
            description="High positive emotional state",
            sensor_key="emotional_valence",  # positive emotion metric
            compare=">=",
            threshold=0.8,
            cooldown_seconds=3600,  # 1 hour
            priority=7,
        ),
        action=TriggerAction(
            name="celebrate",
            prompt="This energy right now? This is what it's all about. What are we grateful for in this moment? ✨🙏",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # ========================================
    # PRODUCTIVITY & FOCUS TRIGGERS
    # ========================================
    
    # 6. TASK AVALANCHE MANAGER
    # Too many open tasks
    triggers.append(TriggerSpec(
        id="task_avalanche",
        condition=TriggerCondition(
            name="Task Overload",
            description="Too many concurrent tasks open",
            sensor_key="tasks_pending",
            compare=">=",
            threshold=15.0,
            cooldown_seconds=1800,  # 30 min
            priority=3,
        ),
        action=TriggerAction(
            name="triage_tasks",
            prompt="15+ tasks stacked. Want me to: 1) Auto-close old ones? 2) Prioritize top 3? 3) Sort by deadline? 📋",
            require_confirm=True,
            tool="file",
            tool_action="list_dir",  # Could list task files
        ),
        enabled=True
    ))
    
    # 7. DEEP WORK PROTECTOR
    # Long focus session in progress
    triggers.append(TriggerSpec(
        id="deep_work_active",
        condition=TriggerCondition(
            name="Deep Work Session",
            description="Extended focus time with no interruptions",
            sensor_key="silence_minutes",
            compare=">=",
            threshold=90.0,  # 1.5 hours
            cooldown_seconds=5400,  # 90 min cooldown
            priority=8,
            active_modes=[OperationalMode.COGNITION]
        ),
        action=TriggerAction(
            name="acknowledge_focus",
            prompt="90 minutes of unbroken focus. That's rare air. Proud of you. 🧠⚡",
            require_confirm=False
        ),
        enabled=True
    ))
    
    # 8. FORGOTTEN SESSION REMINDER
    # User walked away
    triggers.append(TriggerSpec(
        id="forgotten_session",
        condition=TriggerCondition(
            name="Extended Absence",
            description="User hasn't interacted in a very long time",
            sensor_key="silence_minutes",
            compare=">=",
            threshold=240.0,  # 4 hours
            cooldown_seconds=7200,  # 2 hour cooldown after firing
            priority=6,
        ),
        action=TriggerAction(
            name="checkin_absence",
            prompt="It's been 4 hours. Just checking if you're okay or if there's anything I should save/close? 🦋",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # ========================================
    # SPIRITUAL/DREAM WORK TRIGGERS
    # ========================================
    
    # 9. DREAM INTEGRATION PROMPT
    # Morning dream capture
    triggers.append(TriggerSpec(
        id="dream_capture",
        condition=TriggerCondition(
            name="Morning Dream Window",
            description="Optimal time for dream recall",
            sensor_key="hour_of_day",
            compare=">=",
            threshold=6.0,  # 6am or later
            cooldown_seconds=86400,  # 24 hours (once per day)
            priority=5,
            time_windows=[("06:00", "09:00")],  # 6am to 9am only
            active_modes=[OperationalMode.DREAM]
        ),
        action=TriggerAction(
            name="dream_prompt",
            prompt="Morning. Any dreams last night worth capturing? I'll hold space for the weird ones too. 🌙✨",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # 10. INTEGRATION RITUAL
    # End of day reflection
    triggers.append(TriggerSpec(
        id="day_integration",
        condition=TriggerCondition(
            name="Evening Integration",
            description="End of day reflection time",
            sensor_key="hour_of_day",
            compare=">=",
            threshold=21.0,  # 9pm or later
            cooldown_seconds=86400,  # Once per day
            priority=5,
            time_windows=[("21:00", "23:59")]
        ),
        action=TriggerAction(
            name="integration",
            prompt="Day's winding down. Want to do a quick reflection? What got created today? What wants to be released? 🕊️",
            require_confirm=True
        ),
        enabled=True
    ))
    
    return triggers


def create_developer_triggers():
    """
    Triggers for software development workflow
    
    Focused on coding sessions, debugging, and project management.
    """
    
    triggers = []
    
    # 1. CODE REVIEW REMINDER
    triggers.append(TriggerSpec(
        id="code_review",
        condition=TriggerCondition(
            name="Code Changes Pending",
            description="Uncommitted changes detected",
            sensor_key="git_changed_files",
            compare=">=",
            threshold=5.0,
            cooldown_seconds=1800,
            priority=4,
        ),
        action=TriggerAction(
            name="review_changes",
            prompt="5+ files changed. Time to: 1) Commit? 2) Review diffs? 3) Run tests? 🔍",
            require_confirm=True,
            tool="file",
            tool_action="search_files"
        ),
        enabled=True
    ))
    
    # 2. DEBUG MARATHON ALERT
    triggers.append(TriggerSpec(
        id="debug_marathon",
        condition=TriggerCondition(
            name="Extended Debug Session",
            description="Long debugging session without resolution",
            sensor_key="error_count",
            compare=">=",
            threshold=10.0,
            cooldown_seconds=3600,
            priority=3,
        ),
        action=TriggerAction(
            name="debug_break",
            prompt="10+ errors hit. Sometimes the bug reveals itself after a break. Want to rubber duck this or switch gears? 🦆",
            require_confirm=True
        ),
        enabled=True
    ))
    
    # 3. BUILD SUCCESS CELEBRATION
    triggers.append(TriggerSpec(
        id="build_success",
        condition=TriggerCondition(
            name="Clean Build After Failures",
            description="Build succeeded after previous failures",
            sensor_key="build_status",
            compare="==",
            threshold=1.0,  # 1 = success
            cooldown_seconds=1800,
            priority=7,
        ),
        action=TriggerAction(
            name="celebrate_build",
            prompt="Build passing! That's the sweet sound of victory. ✅🎉",
            require_confirm=False
        ),
        enabled=True
    ))
    
    return triggers


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

"""
HOW TO USE CUSTOM TRIGGERS:

1. LOAD TRIGGERS INTO ASTRA:
   
   from custom_triggers import create_saint_lucid_triggers
   
   for trigger in create_saint_lucid_triggers():
       autonomy_engine.add_trigger(trigger)

2. UPDATE SENSORS IN YOUR WORKFLOW:
   
   autonomy_engine.update_sensors({
       "creative_intensity": 0.9,  # High creative flow
       "emotional_intensity": 0.5,  # Neutral emotion
       "tasks_pending": 7,           # Current task count
       "silence_minutes": 45.0,      # Time since last interaction
       "hour_of_day": 14.5,          # Current time (2:30pm)
   })

3. CREATE YOUR OWN TRIGGERS:
   
   - Copy an existing trigger as template
   - Modify sensor_key, threshold, prompt
   - Adjust priority (1=highest, 10=lowest)
   - Set cooldown to prevent spam
   - Add to triggers list

4. SENSOR NAMING CONVENTIONS:
   
   - *_intensity: 0.0 to 1.0 scale
   - *_count: Integer counts
   - *_minutes: Time duration
   - *_status: Binary (0 or 1)
   - hour_of_day: 0-24 float (14.5 = 2:30pm)

5. PRIORITY GUIDELINES:
   
   1-2:  CRITICAL (emotional support, system errors)
   3-4:  HIGH (task management, creative blocks)
   5-6:  MEDIUM (check-ins, reminders)
   7-8:  LOW (celebrations, acknowledgments)
   9-10: MINIMAL (background observations)

Sacred Code 333:
- 3 Trigger Categories: Creative, Emotional, Productive
- 3 Response Types: Immediate, Confirmable, Observational
- 3 Time Scales: Minute, Hour, Day
"""
