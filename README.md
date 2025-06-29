# Multi-Agent Task Automation System

The Multi-Agent Task Automation System is an intelligent platform designed to function as a powerful digital assistant. Its primary goal is to understand high-level instructions from users in plain English and automatically execute them across multiple third-party applications.

## 1. About the Project

In today’s workflow, users often switch between tools to perform even the most basic business tasks. This project addresses that inefficiency by enabling users to express their intent once, allowing a network of specialized AI agents to coordinate and complete the task autonomously.

Instead of opening five different applications and switching contexts, a user simply provides a natural language instruction like:

> "Onboard a new client named John Doe from CompanyX."

The system will take care of everything: emailing the client, scheduling a meeting, creating folders, updating chat channels, and more.

## 2. The Problem We're Solving

Modern digital workflows are fragmented and time-consuming. Tasks like onboarding a new client involve repetitive manual work across different tools, such as:

- Sending welcome emails
- Creating shared folders
- Scheduling calendar events
- Posting updates in team chats
- Adding clients to project management tools

These actions are:

- Time-consuming
- Repetitive and boring
- Error-prone
- Not scalable for multiple tasks or clients

This project offers a solution by building an intelligent automation layer that integrates with all of these services.

## 3. Solution Overview

The system operates in a three-phase pipeline:

### 1. Deconstruction (Planner)

A user instruction is sent to a large language model (Google Gemini), which interprets the intent and breaks it down into actionable steps.

### 2. Delegation (Orchestrator)

The Orchestrator receives the task list and routes each task to the most appropriate specialized agent.

### 3. Execution (Agents)

Each specialized agent performs a single function effectively:

- `SlackAgent`: Sends messages via Slack
- `CalendarAgent`: Manages Google Calendar events
- `CommunicationAgent`: Sends SMS or makes calls via Twilio
- `SearchAgent`: Performs web searches
- `KnowledgeAgent`: Answers queries using internal documents

This approach creates a seamless end-to-end automation pipeline using natural language as the only input.

## 4. Technology Stack

### Backend

- **Language**: Python
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Live Communication**: WebSockets
- **Environment Management**: python-dotenv

### Frontend

- **Markup**: HTML5
- **Styling**: Tailwind CSS
- **Interactivity**: JavaScript

### AI & Third-Party Integrations

- **Language Model**: Google Gemini API
- **APIs & Tools**:
  - Slack API (via `slack-sdk`)
  - Google Calendar API (via `google-api-python-client`)
  - Twilio (via `twilio`)
  - DuckDuckGo Web Search (via `duckduckgo-search`)

## 5. Getting Started

### Prerequisites

- Python 3.8+
- Virtual environment setup (optional but recommended)

### Setup Instructions

1. Clone the repository:

```bash
git clone https://github.com/luvkushsaini/Multi_agent_app.git
cd Multi_agent_app
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your credentials:

```ini
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
SLACK_BOT_TOKEN=your_slack_token
TWILIO_AUTH_TOKEN=your_twilio_token
```

4. Run the application:

```bash
uvicorn main:app --reload
```

## 6. Folder Structure

```
.
├── agents.py
├── orchestrator.py
├── main.py
├── requirements.txt
├── static/
│   └── index.html
├── .gitignore
└── .env (excluded from Git)
```

## 7. Security

- `.env`, `credentials.json`, and other sensitive files are excluded from version control via `.gitignore`.
- Ensure secrets are managed securely in deployment.

## 8. License

This project is licensed under the MIT License. See the LICENSE file for details.

