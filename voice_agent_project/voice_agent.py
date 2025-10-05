#!/usr/bin/env python3
"""
Modular Voice Conversation Agent
Connects ElevenLabs (STT/TTS) with Google Gemini for voice conversations.
Designed to be easily integrated with web backends (Flask/FastAPI).
"""

import os
import sys
import time
import json
import logging
import wave
import tempfile
import threading
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import requests
import sounddevice as sd
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
from playsound import playsound


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Conversation states for state management."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    dtype: str = 'float32'
    recording_duration: float = 5.0


@dataclass
class ConversationMessage:
    """Represents a message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float
    audio_file: Optional[str] = None  # Path to audio file if available


class ElevenLabsSTT:
    """ElevenLabs Speech-to-Text service."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stt_url = "https://api.elevenlabs.io/v1/speech-to-text"
        self.headers = {'xi-api-key': api_key}
        logger.info("ElevenLabs STT service initialized")
    
    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file using ElevenLabs STT API.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            logger.info(f"Transcribing audio file: {audio_file_path}")
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {'audio': ('audio.wav', audio_file, 'audio/wav')}
                
                response = requests.post(
                    self.stt_url,
                    headers=self.headers,
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    transcribed_text = result.get('text', '').strip()
                    
                    if transcribed_text:
                        logger.info(f"Transcription successful: {transcribed_text}")
                        return transcribed_text
                    else:
                        logger.warning("No text detected in audio")
                        return None
                else:
                    logger.error(f"STT API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            return None


class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech service."""
    
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        self.headers = {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': api_key
        }
        logger.info(f"ElevenLabs TTS service initialized with voice: {voice_id}")
    
    def synthesize_speech(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Convert text to speech using ElevenLabs TTS API.
        
        Args:
            text: Text to convert to speech
            output_path: Optional output file path
            
        Returns:
            Path to generated audio file or None if failed
        """
        try:
            logger.info(f"Synthesizing speech for text: {text[:50]}...")
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(
                self.tts_url,
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Save to temporary file if no output path specified
                if output_path is None:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                        output_path = temp_file.name
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Speech synthesis successful: {output_path}")
                return output_path
            else:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None


class GeminiLLM:
    """Google Gemini LLM service."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        logger.info("Gemini LLM service initialized")
    
    def generate_response(self, user_input: str, conversation_history: List[ConversationMessage]) -> Optional[str]:
        """
        Generate response using Gemini LLM.
        
        Args:
            user_input: User's input text
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text or None if failed
        """
        try:
            logger.info(f"Generating response for input: {user_input[:50]}...")
            
            # Build conversation context
            context = self._build_context(conversation_history, user_input)
            
            # Generate response
            response = self.model.generate_content(context)
            
            if response.text:
                response_text = response.text.strip()
                logger.info(f"Response generated successfully: {response_text[:50]}...")
                return response_text
            else:
                logger.warning("No response generated by Gemini")
                return None
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _build_context(self, history: List[ConversationMessage], current_input: str) -> str:
        """Build conversation context from history."""
        if not history:
            return f"User: {current_input}\n\nPlease respond naturally and helpfully."
        
        context = "Here's our conversation so far:\n\n"
        
        # Add last 10 messages for context
        for msg in history[-10:]:
            role = "Human" if msg.role == "user" else "Assistant"
            context += f"{role}: {msg.content}\n"
        
        context += f"\nHuman: {current_input}\n\nPlease respond naturally to the last message."
        return context


class AudioManager:
    """Handles audio input/output operations."""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        logger.info(f"AudioManager initialized with sample rate: {config.sample_rate}")
    
    def record_audio(self, duration: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Audio data as numpy array or None if failed
        """
        duration = duration or self.config.recording_duration
        
        try:
            logger.info(f"Recording audio for {duration} seconds...")
            
            audio_data = sd.rec(
                int(duration * self.config.sample_rate),
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype
            )
            sd.wait()
            
            logger.info("Audio recording completed")
            return audio_data.flatten()
            
        except Exception as e:
            logger.error(f"Audio recording failed: {e}")
            return None
    
    def save_audio_to_wav(self, audio_data: np.ndarray, file_path: str) -> bool:
        """
        Save audio data to WAV file.
        
        Args:
            audio_data: Audio data as numpy array
            file_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to int16 for WAV file
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(self.config.channels)
                wav_file.setsampwidth(2)  # 2 bytes for int16
                wav_file.setframerate(self.config.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            logger.info(f"Audio saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False
    
    def play_audio(self, audio_file_path: str) -> bool:
        """
        Play audio file.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Playing audio: {audio_file_path}")
            playsound(audio_file_path)
            logger.info("Audio playback completed")
            return True
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False


class ConversationManager:
    """
    Manages conversation flow and state.
    This class is designed to be easily integrated with web backends.
    """
    
    def __init__(self, stt_service: ElevenLabsSTT, tts_service: ElevenLabsTTS, 
                 llm_service: GeminiLLM, audio_manager: AudioManager):
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.llm_service = llm_service
        self.audio_manager = audio_manager
        
        self.conversation_history: List[ConversationMessage] = []
        self.state = ConversationState.IDLE
        self.callbacks: Dict[str, List[Callable]] = {
            'on_state_change': [],
            'on_user_input': [],
            'on_assistant_response': [],
            'on_error': []
        }
        
        logger.info("ConversationManager initialized")
    
    def add_callback(self, event: str, callback: Callable):
        """Add callback for events (useful for web integration)."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _emit_event(self, event: str, data: Any = None):
        """Emit event to registered callbacks."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def _change_state(self, new_state: ConversationState):
        """Change conversation state and emit event."""
        old_state = self.state
        self.state = new_state
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")
        self._emit_event('on_state_change', {'old_state': old_state, 'new_state': new_state})
    
    def process_user_input(self, audio_file_path: str) -> bool:
        """
        Process user audio input through the complete pipeline.
        
        Args:
            audio_file_path: Path to user's audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._change_state(ConversationState.PROCESSING)
            
            # Step 1: Transcribe audio
            transcribed_text = self.stt_service.transcribe_audio(audio_file_path)
            if not transcribed_text:
                logger.warning("No speech detected or transcription failed")
                return False
            
            # Check for stop commands
            if transcribed_text.lower() in ['stop', 'quit', 'exit', 'goodbye']:
                logger.info("Stop command detected")
                return True
            
            # Create user message
            user_message = ConversationMessage(
                role='user',
                content=transcribed_text,
                timestamp=time.time(),
                audio_file=audio_file_path
            )
            
            self.conversation_history.append(user_message)
            self._emit_event('on_user_input', user_message)
            
            # Step 2: Generate LLM response
            assistant_response = self.llm_service.generate_response(
                transcribed_text, self.conversation_history
            )
            
            if not assistant_response:
                logger.error("Failed to generate LLM response")
                self._change_state(ConversationState.ERROR)
                self._emit_event('on_error', {'message': 'LLM response generation failed'})
                return False
            
            # Step 3: Convert to speech
            self._change_state(ConversationState.SPEAKING)
            
            speech_file = self.tts_service.synthesize_speech(assistant_response)
            if not speech_file:
                logger.error("Failed to synthesize speech")
                self._change_state(ConversationState.ERROR)
                self._emit_event('on_error', {'message': 'Speech synthesis failed'})
                return False
            
            # Step 4: Play response
            if not self.audio_manager.play_audio(speech_file):
                logger.error("Failed to play audio")
                self._change_state(ConversationState.ERROR)
                self._emit_event('on_error', {'message': 'Audio playback failed'})
                return False
            
            # Create assistant message
            assistant_message = ConversationMessage(
                role='assistant',
                content=assistant_response,
                timestamp=time.time(),
                audio_file=speech_file
            )
            
            self.conversation_history.append(assistant_message)
            self._emit_event('on_assistant_response', assistant_message)
            
            self._change_state(ConversationState.IDLE)
            return True
            
        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            self._change_state(ConversationState.ERROR)
            self._emit_event('on_error', {'message': str(e)})
            return False
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history (useful for web API)."""
        return [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'has_audio': msg.audio_file is not None
            }
            for msg in self.conversation_history
        ]


class VoiceAgent:
    """
    Main voice conversation agent.
    This is the primary interface for the voice conversation system.
    """
    
    def __init__(self, elevenlabs_api_key: str, gemini_api_key: str, voice_id: str, 
                 audio_config: Optional[AudioConfig] = None):
        """
        Initialize the voice agent.
        
        Args:
            elevenlabs_api_key: ElevenLabs API key
            gemini_api_key: Gemini API key
            voice_id: ElevenLabs voice ID
            audio_config: Optional audio configuration
        """
        self.audio_config = audio_config or AudioConfig()
        
        # Initialize services
        self.stt_service = ElevenLabsSTT(elevenlabs_api_key)
        self.tts_service = ElevenLabsTTS(elevenlabs_api_key, voice_id)
        self.llm_service = GeminiLLM(gemini_api_key)
        self.audio_manager = AudioManager(self.audio_config)
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager(
            self.stt_service, self.tts_service, 
            self.llm_service, self.audio_manager
        )
        
        logger.info("VoiceAgent initialized successfully")
    
    def run_conversation_loop(self):
        """
        Run the main conversation loop.
        This method handles the CLI interaction.
        """
        logger.info("Starting voice conversation loop")
        print("🎤 Voice Conversation Agent Started!")
        print("💡 Say 'stop', 'quit', 'exit', or 'goodbye' to end")
        print("💡 Say 'clear' to reset conversation history")
        print("=" * 60)
        
        try:
            while True:
                print("\n🎤 Listening... (Press Ctrl+C to stop)")
                
                # Record audio
                audio_data = self.audio_manager.record_audio()
                if audio_data is None:
                    print("❌ Recording failed, trying again...")
                    continue
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_wav_path = temp_file.name
                
                if not self.audio_manager.save_audio_to_wav(audio_data, temp_wav_path):
                    print("❌ Failed to save audio, trying again...")
                    continue
                
                # Process the audio
                success = self.conversation_manager.process_user_input(temp_wav_path)
                
                # Clean up temporary file
                try:
                    os.unlink(temp_wav_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp file: {e}")
                
                if not success:
                    print("❌ Processing failed, trying again...")
                    continue
                
                print("-" * 40)
                
        except KeyboardInterrupt:
            print("\n👋 Conversation ended by user")
            logger.info("Conversation loop ended by user")
        except Exception as e:
            logger.error(f"Unexpected error in conversation loop: {e}")
            print(f"❌ Unexpected error: {e}")


# Web Integration Helper Functions
# These functions are designed to be easily integrated with Flask/FastAPI

def create_voice_agent_from_env() -> VoiceAgent:
    """
    Create VoiceAgent instance from environment variables.
    This function is designed for web backend integration.
    """
    elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    
    if not all([elevenlabs_api_key, gemini_api_key, voice_id]):
        raise ValueError("Missing required environment variables")
    
    return VoiceAgent(elevenlabs_api_key, gemini_api_key, voice_id)


def process_audio_for_web(audio_file_path: str, agent: VoiceAgent) -> Dict[str, Any]:
    """
    Process audio file for web API integration.
    This function can be called from Flask/FastAPI routes.
    
    Args:
        audio_file_path: Path to uploaded audio file
        agent: VoiceAgent instance
        
    Returns:
        Dictionary with response data
    """
    try:
        success = agent.conversation_manager.process_user_input(audio_file_path)
        
        if success:
            # Get the last assistant response
            history = agent.conversation_manager.get_conversation_history()
            last_response = history[-1] if history and history[-1]['role'] == 'assistant' else None
            
            return {
                'success': True,
                'response_text': last_response['content'] if last_response else None,
                'conversation_id': len(history)  # Simple conversation tracking
            }
        else:
            return {
                'success': False,
                'error': 'Failed to process audio'
            }
    except Exception as e:
        logger.error(f"Web audio processing error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Main function for CLI usage."""
    # Get API keys from environment variables
    elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    
    # Validate environment variables
    if not elevenlabs_api_key:
        print("❌ Error: ELEVENLABS_API_KEY environment variable not set")
        print("💡 Create a .env file or set environment variables")
        sys.exit(1)
    
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)
    
    if not voice_id:
        print("❌ Error: ELEVENLABS_VOICE_ID environment variable not set")
        sys.exit(1)
    
    try:
        # Create and run voice agent
        agent = VoiceAgent(elevenlabs_api_key, gemini_api_key, voice_id)
        agent.run_conversation_loop()
        
    except Exception as e:
        logger.error(f"Failed to start voice agent: {e}")
        print(f"❌ Failed to start voice agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
