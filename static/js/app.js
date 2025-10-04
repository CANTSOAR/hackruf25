/**
 * AI Agent Scheduler - Frontend JavaScript
 * Handles UI interactions, API calls, and responsive behavior
 */

class AgentScheduler {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.currentTab = 'chat';
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupMobileMenu();
        this.loadCalendars();
        this.setupDateTimeInputs();
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    bindEvents() {
        // Tab navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });
        
        // Chat functionality
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        if (messageInput && sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Auto-resize textarea
            messageInput.addEventListener('input', () => {
                messageInput.style.height = 'auto';
                messageInput.style.height = messageInput.scrollHeight + 'px';
            });
        }
        
        // Assignment functionality
        const addAssignmentBtn = document.getElementById('addAssignmentBtn');
        const processAssignmentBtn = document.getElementById('processAssignmentBtn');
        const cancelAssignmentBtn = document.getElementById('cancelAssignmentBtn');
        
        if (addAssignmentBtn) {
            addAssignmentBtn.addEventListener('click', () => this.toggleAssignmentForm());
        }
        if (processAssignmentBtn) {
            processAssignmentBtn.addEventListener('click', () => this.processAssignment());
        }
        if (cancelAssignmentBtn) {
            cancelAssignmentBtn.addEventListener('click', () => this.toggleAssignmentForm());
        }
        
        // Calendar functionality
        const addEventBtn = document.getElementById('addEventBtn');
        const createEventBtn = document.getElementById('createEventBtn');
        const cancelEventBtn = document.getElementById('cancelEventBtn');
        const refreshCalendarBtn = document.getElementById('refreshCalendarBtn');
        
        if (addEventBtn) {
            addEventBtn.addEventListener('click', () => this.toggleEventForm());
        }
        if (createEventBtn) {
            createEventBtn.addEventListener('click', () => this.createEvent());
        }
        if (cancelEventBtn) {
            cancelEventBtn.addEventListener('click', () => this.toggleEventForm());
        }
        if (refreshCalendarBtn) {
            refreshCalendarBtn.addEventListener('click', () => this.loadCalendarEvents());
        }
        
        // Materials functionality
        const refreshMaterialsBtn = document.getElementById('refreshMaterialsBtn');
        if (refreshMaterialsBtn) {
            refreshMaterialsBtn.addEventListener('click', () => this.loadMaterials());
        }
    }
    
    setupMobileMenu() {
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        const sidebar = document.getElementById('sidebar');
        
        if (mobileMenuToggle && sidebar) {
            mobileMenuToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
            
            // Close sidebar when clicking outside
            document.addEventListener('click', (e) => {
                if (!sidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            });
        }
    }
    
    setupDateTimeInputs() {
        const eventStart = document.getElementById('eventStart');
        const eventEnd = document.getElementById('eventEnd');
        
        if (eventStart && eventEnd) {
            // Set default start time to next hour
            const now = new Date();
            now.setHours(now.getHours() + 1, 0, 0, 0);
            eventStart.value = now.toISOString().slice(0, 16);
            
            // Set default end time to 1 hour later
            const endTime = new Date(now.getTime() + 60 * 60 * 1000);
            eventEnd.value = endTime.toISOString().slice(0, 16);
        }
    }
    
    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
        
        // Close mobile menu
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
        
        // Load tab-specific data
        switch (tabName) {
            case 'calendar':
                this.loadCalendarEvents();
                break;
            case 'materials':
                this.loadMaterials();
                break;
        }
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message || this.isLoading) return;
        
        // Add user message to chat
        this.addMessageToChat('user', message);
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Show loading
        this.showLoading();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.addMessageToChat('agent', data.response);
            } else {
                this.addMessageToChat('error', data.error || 'An error occurred');
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessageToChat('error', 'Failed to send message. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    addMessageToChat(type, content) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const avatar = type === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const avatarBg = type === 'user' ? '#e2e8f0' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        
        messageDiv.innerHTML = `
            <div class="message-avatar" style="background: ${avatarBg}; color: ${type === 'user' ? '#475569' : 'white'};">
                <i class="${avatar}"></i>
            </div>
            <div class="message-content">
                <p>${this.formatMessage(content)}</p>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    formatMessage(content) {
        // Convert line breaks to HTML
        return content.replace(/\n/g, '<br>');
    }
    
    toggleAssignmentForm() {
        const form = document.getElementById('assignmentForm');
        const button = document.getElementById('addAssignmentBtn');
        
        if (form.style.display === 'none') {
            form.style.display = 'block';
            button.innerHTML = '<i class="fas fa-times"></i><span>Cancel</span>';
        } else {
            form.style.display = 'none';
            button.innerHTML = '<i class="fas fa-plus"></i><span>Add Assignment</span>';
        }
    }
    
    async processAssignment() {
        const url = document.getElementById('assignmentUrl').value.trim();
        const courseId = document.getElementById('courseId').value.trim();
        
        if (!url) {
            this.showToast('Please enter an assignment URL', 'error');
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await fetch('/api/process-assignment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    assignment_url: url,
                    course_id: courseId
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast('Assignment processed successfully!', 'success');
                this.addAssignmentCard(data.result);
                this.toggleAssignmentForm();
            } else {
                this.showToast(data.error || 'Failed to process assignment', 'error');
            }
        } catch (error) {
            console.error('Assignment processing error:', error);
            this.showToast('Failed to process assignment. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    addAssignmentCard(result) {
        const assignmentsList = document.getElementById('assignmentsList');
        
        // Remove empty state if it exists
        const emptyState = assignmentsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="card-header">
                <div>
                    <div class="card-title">Assignment Processed</div>
                    <div class="card-subtitle">${new Date().toLocaleString()}</div>
                </div>
            </div>
            <div class="card-content">
                <p>${result}</p>
            </div>
        `;
        
        assignmentsList.appendChild(card);
    }
    
    toggleEventForm() {
        const form = document.getElementById('eventForm');
        const button = document.getElementById('addEventBtn');
        
        if (form.style.display === 'none') {
            form.style.display = 'block';
            button.innerHTML = '<i class="fas fa-times"></i><span>Cancel</span>';
        } else {
            form.style.display = 'none';
            button.innerHTML = '<i class="fas fa-plus"></i><span>Add Event</span>';
        }
    }
    
    async createEvent() {
        const title = document.getElementById('eventTitle').value.trim();
        const startTime = document.getElementById('eventStart').value;
        const endTime = document.getElementById('eventEnd').value;
        const calendarId = document.getElementById('eventCalendar').value;
        const description = document.getElementById('eventDescription').value.trim();
        
        if (!title || !startTime || !endTime) {
            this.showToast('Please fill in all required fields', 'error');
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await fetch('/api/calendar/create-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    start_time: startTime,
                    end_time: endTime,
                    calendar_id: calendarId,
                    description: description
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast('Event created successfully!', 'success');
                this.toggleEventForm();
                this.loadCalendarEvents();
            } else {
                this.showToast(data.error || 'Failed to create event', 'error');
            }
        } catch (error) {
            console.error('Event creation error:', error);
            this.showToast('Failed to create event. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadCalendars() {
        try {
            const response = await fetch('/api/calendar/list');
            const data = await response.json();
            
            if (response.ok) {
                const select = document.getElementById('eventCalendar');
                if (select) {
                    select.innerHTML = '<option value="primary">Primary Calendar</option>';
                    // Add other calendars if available
                }
            }
        } catch (error) {
            console.error('Calendar loading error:', error);
        }
    }
    
    async loadCalendarEvents() {
        const eventsContainer = document.getElementById('calendarEvents');
        
        this.showLoading();
        
        try {
            const response = await fetch('/api/calendar/events');
            const data = await response.json();
            
            if (response.ok) {
                this.displayCalendarEvents(data.events);
            } else {
                this.showToast(data.error || 'Failed to load calendar events', 'error');
            }
        } catch (error) {
            console.error('Calendar events error:', error);
            this.showToast('Failed to load calendar events', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    displayCalendarEvents(events) {
        const eventsContainer = document.getElementById('calendarEvents');
        
        // Remove empty state if it exists
        const emptyState = eventsContainer.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        if (!events || events.length === 0) {
            eventsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-calendar"></i>
                    <h3>No events found</h3>
                    <p>Your calendar events will appear here</p>
                </div>
            `;
            return;
        }
        
        eventsContainer.innerHTML = '';
        
        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <div class="card-title">${event.summary || 'Untitled Event'}</div>
                        <div class="card-subtitle">${event.start?.dateTime || event.start?.date || 'No time specified'}</div>
                    </div>
                </div>
                <div class="card-content">
                    <p>${event.description || 'No description'}</p>
                </div>
            `;
            eventsContainer.appendChild(card);
        });
    }
    
    async loadMaterials() {
        const materialsContainer = document.getElementById('materialsList');
        
        // For now, show a placeholder
        materialsContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder"></i>
                <h3>No materials found</h3>
                <p>Course materials will appear here after processing assignments</p>
            </div>
        `;
    }
    
    showLoading() {
        this.isLoading = true;
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('show');
        }
    }
    
    hideLoading() {
        this.isLoading = false;
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }
    
    showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fas fa-check-circle' : 
                    type === 'error' ? 'fas fa-exclamation-circle' : 
                    'fas fa-exclamation-triangle';
        
        toast.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AgentScheduler();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Refresh data when page becomes visible
        const scheduler = window.agentScheduler;
        if (scheduler && scheduler.currentTab === 'calendar') {
            scheduler.loadCalendarEvents();
        }
    }
});
