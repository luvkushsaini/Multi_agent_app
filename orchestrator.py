import asyncio
import json
import requests
import os
import agents
from datetime import datetime

GEMINI_API_KEY = "" # This will be set by main.py
GEMINI_API_URL = ""

# --- ROBUST PROMPTS ---
PLANNER_PROMPT_TEMPLATE = """
You are an expert planning agent. Your job is to create a plan to fulfill a user's request.
Here are the available agents:
- "KnowledgeAgent": Use for questions about internal data.
- "SearchAgent": A general web search agent for public info.
- "SlackAgent": Can post messages to a specific Slack channel.
- "CommunicationAgent": Can make phone calls or send text messages.
- "CalendarAgent": Can interact with a user's calendar.
Based on the user's request, create a JSON array of steps. Each object in the array MUST have an "agent" and an "action" key.
User Request: "{user_prompt}"
"""
SLACK_PARSER_PROMPT_TEMPLATE = """
You are a data extraction tool. From the user's text, extract the 'channel' and the 'message'.
The channel name must start with a '#'. The message is the content to be posted.
Respond with ONLY a valid JSON object containing "channel" and "message" keys.

Example Text: "Post a message on #general channel in Slack saying 'Hi, I'm Oreo!'"
Example JSON Output:
{
  "channel": "#general",
  "message": "Hi, I'm Oreo!"
}

Text: "{action_text}"
JSON Output:
"""
EVENT_PARSER_PROMPT_TEMPLATE = """
You are a data extraction tool. From the user's text, extract event details: 'title', 'start_time', and 'end_time'.
The start and end times must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
The current date is {current_date}. Resolve relative times like "tomorrow" based on this date.
Respond with ONLY a valid JSON object.

Text: "{action_text}"
JSON Output:
"""
COMMUNICATION_PARSER_PROMPT_TEMPLATE = """
You are a data extraction tool. From the user's text, extract 'type' ('call' or 'sms'), 'recipient' (a phone number in E.164 format), and 'message'.
Respond with ONLY a valid JSON object.

Text: "{action_text}"
JSON Output:
"""
SEARCH_QUERY_PARSER_PROMPT_TEMPLATE = """
You are a data extraction tool. From the user's text, extract a concise, effective web search query.
Respond with only the search query as a raw string.

Text: "{action_text}"
Search Query:
"""

class TaskOrchestrator:
    def __init__(self, task_id: str, prompt: str, ws_manager):
        self.task_id = task_id
        self.prompt = prompt
        self.ws_manager = ws_manager
        self.plan = []
        self.context = {} 
        self.calendar_agent = agents.CalendarAgent()
        self.communication_agent = agents.CommunicationAgent()
        self.search_agent = agents.SearchAgent()
        self.knowledge_agent = agents.KnowledgeAgent()
        self.slack_agent = agents.SlackAgent()
        
        global GEMINI_API_URL
        GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    async def _gemini_request(self, prompt_data: dict, parser_template: str, is_json_output: bool = True):
        if not GEMINI_API_KEY:
             raise ValueError("GEMINI_API_KEY is not set. Please check your .env file.")
        
        headers = {"Content-Type": "application/json"}
        final_prompt = parser_template.format(**prompt_data)
        payload = {"contents": [{"parts": [{"text": final_prompt}]}]}
        
        try:
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            response_json = response.json()
            
            if 'candidates' not in response_json or not response_json['candidates']:
                raise ValueError("Invalid response from Gemini API: 'candidates' field is missing or empty.")

            content_part = response_json['candidates'][0]['content']['parts'][0]['text']
            
            if is_json_output:
                return json.loads(content_part.strip().lstrip("```json").rstrip("```").strip())
            return content_part.strip()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {response.text}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred in _gemini_request: {e}")
            raise

    async def execute_plan(self):
        try:
            await self.ws_manager.broadcast(json.dumps({"type": "log", "agent": "PlannerAgent", "message": "Contacting Gemini API to create an execution plan...", "log_type": "info"}))
            plan_prompt = {"user_prompt": self.prompt}
            self.plan = await self._gemini_request(plan_prompt, PLANNER_PROMPT_TEMPLATE)
            
            if not isinstance(self.plan, list):
                raise TypeError(f"The AI planner returned an invalid format. Expected a list, but got {type(self.plan)}.")

            validated_plan = []
            for step in self.plan:
                if isinstance(step, dict) and 'agent' in step and 'action' in step:
                    step['status'] = 'pending'
                    validated_plan.append(step)
                else:
                    print(f"WARNING: Skipping invalid step received from AI: {step}")
            
            self.plan = validated_plan
            if not self.plan:
                 raise ValueError("The AI planner returned a plan with no valid steps.")

            await self.ws_manager.broadcast(json.dumps({"type": "plan", "steps": self.plan}))

        except Exception as e:
            error_message = f"Failed to create a valid task plan. Please try rephrasing your command. Error: {e}"
            await self.ws_manager.broadcast(json.dumps({"type": "log", "agent": "System", "message": error_message, "log_type": "error"}))
            return

        for step in self.plan:
            await asyncio.sleep(1)
            try:
                if '{' in step['action'] and '}' in step['action']:
                    step['action'] = step['action'].format(**self.context)
            except KeyError as e:
                print(f"Info: Skipping format for action '{step['action']}' due to missing key: {e}")

            await self._execute_step(step)

        await self.ws_manager.broadcast(json.dumps({"type": "log", "agent": "System", "message": "Task automation completed.", "log_type": "success"}))

    async def _execute_step(self, step: dict):
        agent_name = step.get('agent', 'UnknownAgent')
        action = step.get('action', 'No action defined')

        await self.ws_manager.broadcast(json.dumps({"type": "status_update", "step_action": action, "status": "in-progress"}))
        await self.ws_manager.broadcast(json.dumps({"type": "log", "agent": agent_name, "message": f"Starting: {action}...", "log_type": "info"}))

        execution_result = ""
        step_succeeded = True
        try:
            if agent_name == "SlackAgent":
                slack_details = await self._gemini_request({"action_text": action}, SLACK_PARSER_PROMPT_TEMPLATE)
                if not slack_details.get("channel") or not slack_details.get("message"):
                    raise ValueError("Could not parse a valid channel and message from the request. The LLM returned invalid data.")
                message_to_send = slack_details["message"].format(**self.context)
                await self.slack_agent.run(slack_details["channel"], message_to_send)
                execution_result = f"Message successfully posted to Slack channel {slack_details['channel']}."

            elif agent_name == "KnowledgeAgent":
                answer = await self.knowledge_agent.run(action)
                self.context['knowledge_answer'] = answer
                execution_result = f"Knowledge Base Answer: {answer}"
            elif agent_name == "SearchAgent":
                query = await self._gemini_request({"action_text": action}, SEARCH_QUERY_PARSER_PROMPT_TEMPLATE, is_json_output=False)
                search_results = await self.search_agent.run(query)
                self.context['search_result'] = search_results 
                execution_result = f"Search for '{query}' found: {search_results}"
            elif agent_name == "CalendarAgent":
                event_details = await self._gemini_request({"action_text": action, "current_date": datetime.now().strftime("%A, %Y-%m-%d")}, EVENT_PARSER_PROMPT_TEMPLATE)
                event_link = await self.calendar_agent.run(event_details)
                execution_result = f"Successfully created event. View: {event_link}"
            elif agent_name == "CommunicationAgent":
                comm_details = await self._gemini_request({"action_text": action}, COMMUNICATION_PARSER_PROMPT_TEMPLATE)
                message_to_send = comm_details["message"].format(**self.context)
                if comm_details.get("type") == "sms":
                    sms_sid = self.communication_agent.send_sms(comm_details["recipient"], message_to_send)
                    execution_result = f"SMS to {comm_details['recipient']} sent successfully. SID: {sms_sid}"
                elif comm_details.get("type") == "call":
                    call_sid = self.communication_agent.make_call(comm_details["recipient"], message_to_send)
                    execution_result = f"Call to {comm_details['recipient']} initiated. SID: {call_sid}"
            else:
                print(f"Executing (Simulated): {agent_name} -> {action}")
                await asyncio.sleep(2)
                execution_result = f"Simulated action '{action}' completed."
        
        except Exception as e:
            step_succeeded = False
            execution_result = f"Action failed. Error: {e}"
            print(f"Error during execution: {e}")

        final_status = "completed" if step_succeeded else "failed"
        await self.ws_manager.broadcast(json.dumps({"type": "status_update", "step_action": action, "status": final_status}))
        await self.ws_manager.broadcast(json.dumps({"type": "log", "agent": agent_name, "message": execution_result, "log_type": "info" if step_succeeded else "error"}))
