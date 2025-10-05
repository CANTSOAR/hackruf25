# 🚀 Quick Start Guide

## Getting Started

1. **Navigate to the project folder:**
   ```bash
   cd voice_agent_project
   ```

2. **Install dependencies:**
   ```bash
   python setup.py
   # OR
   pip install -r requirements.txt
   ```

3. **Set up your API keys:**
   ```bash
   # Copy the example file
   cp env_example.txt .env
   
   # Edit .env with your API keys
   nano .env
   ```

4. **Test your installation:**
   ```bash
   python test_installation.py
   ```

## Running the Voice Agent

### Command Line Interface
```bash
python voice_agent.py
```

### Web Interface (Flask)
```bash
python web_integration_example.py flask
```
Then open: http://localhost:5000

### API Server (FastAPI)
```bash
python web_integration_example.py fastapi
```
Then open: http://localhost:8000/docs

## What You Need

- **ElevenLabs API Key**: Get from [ElevenLabs](https://elevenlabs.io)
- **ElevenLabs Voice ID**: Find in your ElevenLabs dashboard
- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Troubleshooting

- Run `python test_installation.py` to diagnose issues
- Check `voice_agent.log` for detailed error logs
- Ensure your microphone and speakers are working

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [web_integration_example.py](web_integration_example.py) for Flask/FastAPI integration
- Customize audio settings in the `AudioConfig` class

Happy voice chatting! 🎤🤖
