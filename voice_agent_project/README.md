# 🎤 Voice Conversation Agent

A modular Python application that connects **ElevenLabs** (Speech-to-Text & Text-to-Speech) with **Google Gemini** for intelligent voice conversations. Designed to be easily integrated with web backends like Flask or FastAPI.

## ✨ Features

- **🎙️ Speech-to-Text**: ElevenLabs API for accurate transcription
- **🤖 AI Conversations**: Google Gemini for intelligent responses
- **🔊 Text-to-Speech**: ElevenLabs API with custom voice support
- **🔄 Conversation Loop**: Maintains context across interactions
- **🌐 Web Ready**: Modular design for easy Flask/FastAPI integration
- **📝 Comprehensive Logging**: Debug and monitor conversations
- **⚡ Error Handling**: Robust error handling and recovery

## 🚀 Quick Start

### 1. Installation

```bash
# Navigate to the project folder
cd voice_agent_project

# Run setup script (recommended)
python setup.py

# Or install manually
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API keys:

```env
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here

# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Agent

```bash
# Command-line interface
python voice_agent.py

# Web interface (Flask)
python web_integration_example.py flask

# API server (FastAPI)
python web_integration_example.py fastapi
```

## 📁 Project Structure

```
voice_agent_project/
├── voice_agent.py              # Main voice conversation agent
├── web_integration_example.py  # Flask/FastAPI integration examples
├── setup.py                    # Setup and installation script
├── test_installation.py        # Installation verification script
├── requirements.txt            # Python dependencies
├── env_example.txt            # Environment variables template
├── README.md                  # This file
├── __init__.py                # Package initialization
└── voice_agent.log           # Generated log file (created at runtime)
```

## 🏗️ Architecture

The application is built with a modular architecture for easy integration:

### Core Components

- **`ElevenLabsSTT`**: Speech-to-Text service
- **`ElevenLabsTTS`**: Text-to-Speech service  
- **`GeminiLLM`**: Language model integration
- **`AudioManager`**: Audio recording and playback
- **`ConversationManager`**: Conversation flow and state management
- **`VoiceAgent`**: Main orchestration class

### Web Integration Points

The code includes clear integration points for web backends:

```python
# Create agent instance
agent = create_voice_agent_from_env()

# Process audio from web upload
result = process_audio_for_web(audio_file_path, agent)
```

## 🌐 Web Integration

### Flask Integration

```python
from voice_agent import create_voice_agent_from_env, process_audio_for_web

@app.route('/process_audio', methods=['POST'])
def process_audio():
    audio_file = request.files['audio']
    result = process_audio_for_web(audio_file, voice_agent)
    return jsonify(result)
```

### FastAPI Integration

```python
from voice_agent import create_voice_agent_from_env, process_audio_for_web

@fastapi_app.post("/process_audio")
async def process_audio(audio: UploadFile = File(...)):
    result = process_audio_for_web(temp_path, voice_agent)
    return JSONResponse(content=result)
```

## 🎯 Usage Examples

### Command Line

```bash
# Start conversation
python voice_agent.py

# Say "Hello" -> Agent responds with speech
# Say "stop" -> End conversation
# Say "clear" -> Reset conversation history
```

### Programmatic Usage

```python
from voice_agent import VoiceAgent

# Initialize agent
agent = VoiceAgent(
    elevenlabs_api_key="your_key",
    gemini_api_key="your_key", 
    voice_id="your_voice_id"
)

# Add event callbacks
agent.conversation_manager.add_callback(
    'on_user_input', 
    lambda msg: print(f"User: {msg.content}")
)

# Run conversation loop
agent.run_conversation_loop()
```

## 🔧 Configuration Options

### Audio Settings

```python
from voice_agent import AudioConfig

config = AudioConfig(
    sample_rate=16000,      # Audio sample rate
    channels=1,             # Mono recording
    recording_duration=5.0  # Recording length in seconds
)

agent = VoiceAgent(api_keys..., audio_config=config)
```

### Conversation Settings

```python
# Access conversation history
history = agent.conversation_manager.get_conversation_history()

# Clear conversation
agent.conversation_manager.clear_conversation()

# Add custom callbacks
agent.conversation_manager.add_callback('on_state_change', my_callback)
```

## 📝 API Reference

### ElevenLabs STT

- **Endpoint**: `https://api.elevenlabs.io/v1/speech-to-text`
- **Input**: WAV audio file
- **Output**: Transcribed text

### ElevenLabs TTS

- **Endpoint**: `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- **Input**: Text string
- **Output**: MP3 audio file

### Gemini LLM

- **Model**: `gemini-pro`
- **Input**: Conversation context + user input
- **Output**: Generated response text

## 🐛 Troubleshooting

### Common Issues

1. **Microphone not working**
   ```bash
   # Check audio devices
   python -c "import sounddevice as sd; print(sd.query_devices())"
   ```

2. **API key errors**
   ```bash
   # Verify environment variables
   echo $ELEVENLABS_API_KEY
   echo $GEMINI_API_KEY
   ```

3. **Audio playback issues**
   ```bash
   # Install audio dependencies
   pip install playsound
   ```

### Logging

Check `voice_agent.log` for detailed error information:

```bash
tail -f voice_agent.log
```

## 🔒 Security Notes

- Store API keys in environment variables, never in code
- Use HTTPS in production web deployments
- Validate audio file types and sizes in web uploads
- Implement rate limiting for API endpoints

## 📋 Requirements

- Python 3.8+
- Microphone and speakers
- Internet connection for API calls
- API keys for ElevenLabs and Google Gemini

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `voice_agent.log`
3. Create an issue with detailed error information

---

**Happy Voice Chatting! 🎤🤖**
