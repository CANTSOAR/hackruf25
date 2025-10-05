"""
Voice Conversation Agent Package

A modular Python application that connects ElevenLabs (Speech-to-Text & Text-to-Speech) 
with Google Gemini for intelligent voice conversations.

Main Components:
- VoiceAgent: Main orchestration class
- ElevenLabsSTT: Speech-to-Text service
- ElevenLabsTTS: Text-to-Speech service
- GeminiLLM: Language model integration
- ConversationManager: Conversation flow management

Usage:
    from voice_agent_project import VoiceAgent, create_voice_agent_from_env
    
    # Create agent
    agent = create_voice_agent_from_env()
    
    # Run conversation
    agent.run_conversation_loop()
"""

__version__ = "1.0.0"
__author__ = "Voice Agent Team"

# Import main classes for easy access
from .voice_agent import (
    VoiceAgent,
    ElevenLabsSTT,
    ElevenLabsTTS,
    GeminiLLM,
    AudioManager,
    ConversationManager,
    create_voice_agent_from_env,
    process_audio_for_web
)

__all__ = [
    'VoiceAgent',
    'ElevenLabsSTT', 
    'ElevenLabsTTS',
    'GeminiLLM',
    'AudioManager',
    'ConversationManager',
    'create_voice_agent_from_env',
    'process_audio_for_web'
]
