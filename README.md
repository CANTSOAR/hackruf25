# AI Agent Scheduler

A responsive web application that provides an intelligent scheduling system for students, combining AI agents with Canvas assignment processing and Google Calendar integration.

## Features

### 🤖 AI-Powered Agents
- **Orchestrator**: Coordinates between different agents to help with academic planning
- **Gatherer**: Processes Canvas assignments and extracts relevant course materials
- **Scheduler**: Manages Google Calendar integration for event creation and management

### 📱 Responsive Design
- **Mobile-First**: Optimized for both desktop and mobile devices
- **Modern UI**: Clean, intuitive interface with gradient designs
- **Dark Mode**: Automatic dark mode support based on system preferences

### 🎯 Core Functionality
- **Chat Interface**: Natural language interaction with AI agents
- **Assignment Processing**: Upload Canvas assignment URLs for intelligent analysis
- **Calendar Management**: Create and manage Google Calendar events
- **Material Organization**: Access and organize course materials

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Google Cloud Platform account (for Calendar API)
- Canvas API access (optional, for assignment processing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hackruf25
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Required
   GEMINI_API_KEY=your_gemini_api_key_here
   SECRET_KEY=your_secret_key_here
   
   # Optional - for Canvas integration
   CANVAS_API_URL=https://your-canvas-instance.instructure.com/api/v1
   CANVAS_API_TOKEN=your_canvas_token_here
   
   # Optional - for Google Calendar
   GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
   
   # Optional - for production
   DEBUG=False
   PORT=5000
   ```

4. **Set up Google Calendar API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Calendar API
   - Create credentials (OAuth 2.0)
   - Download the credentials file and place it in the project root as `credentials.json`

5. **Create necessary directories**
   ```bash
   mkdir -p agents/notes
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Usage

### Chat Interface
- Use natural language to interact with the AI agents
- Ask questions like:
  - "Help me plan my study schedule for next week"
  - "Process my Canvas assignment from [URL]"
  - "Create a study session in my calendar"

### Assignment Processing
1. Navigate to the "Assignments" tab
2. Click "Add Assignment"
3. Enter your Canvas assignment URL
4. Optionally provide the course ID
5. Click "Process Assignment" to analyze and create a study plan

### Calendar Management
1. Navigate to the "Calendar" tab
2. View your existing events
3. Click "Add Event" to create new calendar events
4. Fill in the event details and click "Create Event"

### Mobile Usage
- The interface automatically adapts to mobile screens
- Use the hamburger menu (☰) to access navigation on mobile
- All features are fully functional on mobile devices

## API Endpoints

### Chat
- `POST /api/chat` - Send messages to AI agents
- `GET /api/messages/<session_id>` - Get message history

### Assignments
- `POST /api/process-assignment` - Process Canvas assignments

### Calendar
- `GET /api/calendar/events` - Get calendar events
- `POST /api/calendar/create-event` - Create new events
- `GET /api/calendar/list` - List available calendars

### System
- `GET /api/health` - Health check endpoint

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for AI functionality |
| `SECRET_KEY` | Yes | Flask secret key for sessions |
| `CANVAS_API_URL` | No | Canvas API base URL |
| `CANVAS_API_TOKEN` | No | Canvas API authentication token |
| `DEBUG` | No | Enable debug mode (default: False) |
| `PORT` | No | Port to run the application (default: 5000) |

### Google Calendar Setup

1. **Enable Google Calendar API**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials

2. **Download Credentials**
   - Download the JSON credentials file
   - Rename it to `credentials.json`
   - Place it in the project root directory

3. **First Run**
   - The application will open a browser window for OAuth authentication
   - Grant permissions to access your Google Calendar
   - A `token.json` file will be created for future use

## Development

### Project Structure
```
hackruf25/
├── agents/                 # AI agent modules
│   ├── baseagent.py       # Base agent class
│   ├── gatherer.py        # Canvas assignment processing
│   ├── scheduler.py       # Google Calendar integration
│   ├── orchestrator.py    # Agent coordination
│   └── tools/             # Agent tools
├── templates/             # HTML templates
│   └── index.html         # Main application template
├── static/                # Static assets
│   ├── css/
│   │   └── style.css      # Responsive CSS styles
│   └── js/
│       └── app.js         # Frontend JavaScript
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Adding New Features

1. **New Agent Tools**
   - Add tools to `agents/tools/`
   - Import and register in agent classes
   - Update API endpoints in `app.py`

2. **New UI Components**
   - Add HTML to `templates/index.html`
   - Style with CSS in `static/css/style.css`
   - Add JavaScript functionality in `static/js/app.js`

3. **New API Endpoints**
   - Add routes to `app.py`
   - Update frontend JavaScript to call new endpoints

## Troubleshooting

### Common Issues

1. **Google Calendar Authentication**
   - Ensure `credentials.json` is in the project root
   - Check that Google Calendar API is enabled
   - Verify OAuth consent screen is configured

2. **Canvas Integration**
   - Verify Canvas API URL and token are correct
   - Check that assignment URLs are accessible
   - Ensure proper permissions for Canvas API

3. **Mobile Display Issues**
   - Clear browser cache
   - Check viewport meta tag in HTML
   - Verify CSS media queries

4. **Agent Errors**
   - Check Gemini API key is valid
   - Verify all required environment variables
   - Check agent tool imports

### Debug Mode

Enable debug mode for development:
```bash
export DEBUG=True
python app.py
```

This will:
- Show detailed error messages
- Enable Flask debug mode
- Display request/response logs

## Security Considerations

- Never commit API keys or credentials to version control
- Use environment variables for sensitive configuration
- Implement proper authentication for production use
- Regularly rotate API keys and tokens
- Use HTTPS in production environments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub
4. Contact the development team

## Roadmap

- [ ] User authentication and profiles
- [ ] Advanced scheduling algorithms
- [ ] Integration with more LMS platforms
- [ ] Mobile app development
- [ ] Analytics and reporting
- [ ] Multi-language support
