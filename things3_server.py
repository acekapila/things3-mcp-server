#!/usr/bin/env python3
"""
Things 3 MCP Server - Python Implementation
Provides Model Context Protocol interface for Things 3 task management on macOS
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server


@dataclass
class Task:
    """Represents a Things 3 task"""
    id: str
    title: str
    notes: Optional[str] = None
    due_date: Optional[str] = None
    area: Optional[str] = None
    project: Optional[str] = None
    tags: List[str] = None
    status: str = "open"
    creation_date: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Project:
    """Represents a Things 3 project"""
    id: str
    title: str
    notes: Optional[str] = None
    area: Optional[str] = None
    status: str = "open"
    tasks: List[Task] = None

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []


class Things3Controller:
    """Handles AppleScript communication with Things 3"""
    
    @staticmethod
    def execute_applescript(script: str) -> str:
        """Execute AppleScript and return result"""
        try:
            # Escape quotes in the script
            escaped_script = script.replace("'", "'\"'\"'")
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise Exception(f"AppleScript error: {result.stderr}")
            
            return result.stdout.strip()
        
        except subprocess.TimeoutExpired:
            raise Exception("AppleScript execution timed out")
        except Exception as e:
            raise Exception(f"Failed to execute AppleScript: {str(e)}")

    def add_task(self, title: str, notes: str = "", due_date: str = None, 
                 area: str = None, project: str = None, tags: List[str] = None) -> str:
        """Add a new task to Things 3"""
        
        # Build the AppleScript
        script_parts = [
            'tell application "Things3"',
            f'    set newToDo to make new to do with properties {{name:"{title}"'
        ]
        
        if notes:
            script_parts[-1] += f', notes:"{notes}"'
        
        if due_date:
            script_parts[-1] += f', due date:date("{due_date}")'
        
        if area:
            script_parts[-1] += f', area:"{area}"'
        
        if project:
            script_parts[-1] += f', project:"{project}"'
        
        script_parts[-1] += '}'
        
        # Add tags if provided
        if tags:
            script_parts.append('    repeat with tagName in {"' + '", "'.join(tags) + '"}')
            script_parts.append('        set tag of newToDo to tagName')
            script_parts.append('    end repeat')
        
        script_parts.extend([
            '    return id of newToDo',
            'end tell'
        ])
        
        script = '\n'.join(script_parts)
        return self.execute_applescript(script)

    def list_tasks(self, list_name: str = "today", limit: int = 20) -> List[Dict[str, Any]]:
        """List tasks from a specific Things 3 list"""
        
        list_mapping = {
            "today": 'list "Today"',
            "upcoming": 'list "Upcoming"',
            "anytime": 'list "Anytime"',
            "someday": 'list "Someday"',
            "inbox": 'list "Inbox"',
            "completed": 'list "Logbook"'
        }
        
        things_list = list_mapping.get(list_name.lower(), 'list "Today"')
        
        script = f'''
        tell application "Things3"
            set taskList to {{}}
            set todoList to to dos of {things_list}
            repeat with i from 1 to (count of todoList)
                if i > {limit} then exit repeat
                set thisToDo to item i of todoList
                set taskInfo to (name of thisToDo) & "|||" & (id of thisToDo) & "|||" & ¬
                    (notes of thisToDo) & "|||" & (due date of thisToDo) & "|||" & ¬
                    (creation date of thisToDo) & "|||" & (status of thisToDo)
                set end of taskList to taskInfo
            end repeat
            return taskList as string
        end tell
        '''
        
        result = self.execute_applescript(script)
        if not result or result == "":
            return []
        
        tasks = []
        for task_line in result.split(','):
            if '|||' in task_line:
                parts = task_line.split('|||')
                if len(parts) >= 6:
                    tasks.append({
                        'title': parts[0].strip(),
                        'id': parts[1].strip(),
                        'notes': parts[2].strip() if parts[2].strip() != 'missing value' else '',
                        'due_date': parts[3].strip() if parts[3].strip() != 'missing value' else None,
                        'creation_date': parts[4].strip() if parts[4].strip() != 'missing value' else None,
                        'status': parts[5].strip()
                    })
        
        return tasks

    def complete_task(self, task_identifier: str) -> str:
        """Complete a task by ID or title"""
        
        script = f'''
        tell application "Things3"
            try
                set completedToDo to to do id "{task_identifier}"
                set status of completedToDo to completed
                return "Task completed successfully (found by ID)"
            on error
                try
                    set completedToDo to to do "{task_identifier}"
                    set status of completedToDo to completed
                    return "Task completed successfully (found by title)"
                on error
                    return "Task not found: {task_identifier}"
                end try
            end try
        end tell
        '''
        
        return self.execute_applescript(script)

    def search_tasks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tasks containing the query string"""
        
        script = f'''
        tell application "Things3"
            set searchResults to {{}}
            set allToDos to to dos
            repeat with thisToDo in allToDos
                if (name of thisToDo) contains "{query}" or (notes of thisToDo) contains "{query}" then
                    set taskInfo to (name of thisToDo) & "|||" & (id of thisToDo) & "|||" & (status of thisToDo)
                    set end of searchResults to taskInfo
                    if (count of searchResults) ≥ {limit} then exit repeat
                end if
            end repeat
            return searchResults as string
        end tell
        '''
        
        result = self.execute_applescript(script)
        if not result:
            return []
        
        tasks = []
        for task_line in result.split(','):
            if '|||' in task_line:
                parts = task_line.split('|||')
                if len(parts) >= 3:
                    tasks.append({
                        'title': parts[0].strip(),
                        'id': parts[1].strip(),
                        'status': parts[2].strip()
                    })
        
        return tasks

    def list_projects(self, status: str = "open") -> List[Dict[str, Any]]:
        """List projects by status"""
        
        status_filter = ""
        if status == "open":
            status_filter = "whose status is open"
        elif status == "completed":
            status_filter = "whose status is completed"
        
        script = f'''
        tell application "Things3"
            set projectList to {{}}
            set allProjects to projects {status_filter}
            repeat with thisProject in allProjects
                set projectInfo to (name of thisProject) & "|||" & (id of thisProject) & "|||" & (status of thisProject)
                set end of projectList to projectInfo
            end repeat
            return projectList as string
        end tell
        '''
        
        result = self.execute_applescript(script)
        if not result:
            return []
        
        projects = []
        for project_line in result.split(','):
            if '|||' in project_line:
                parts = project_line.split('|||')
                if len(parts) >= 3:
                    projects.append({
                        'title': parts[0].strip(),
                        'id': parts[1].strip(),
                        'status': parts[2].strip()
                    })
        
        return projects

    def add_project(self, title: str, notes: str = "", area: str = None, when: str = "someday") -> str:
        """Add a new project to Things 3"""
        
        script_parts = [
            'tell application "Things3"',
            f'    set newProject to make new project with properties {{name:"{title}"'
        ]
        
        if notes:
            script_parts[-1] += f', notes:"{notes}"'
        
        if area:
            script_parts[-1] += f', area:"{area}"'
        
        script_parts[-1] += '}'
        
        if when == "today":
            script_parts.append('    set start date of newProject to current date')
        
        script_parts.extend([
            '    return id of newProject',
            'end tell'
        ])
        
        script = '\n'.join(script_parts)
        return self.execute_applescript(script)

    def get_daily_overview(self) -> str:
        """Get comprehensive daily overview"""
        
        script = '''
        tell application "Things3"
            set overview to ""
            
            -- Today's tasks
            set todayTasks to to dos of list "Today"
            set overview to overview & "📅 TODAY (" & (count of todayTasks) & " tasks):" & return
            repeat with thisToDo in todayTasks
                set overview to overview & "• " & (name of thisToDo)
                if (due date of thisToDo) is not missing value then
                    set overview to overview & " (Due: " & (due date of thisToDo) & ")"
                end if
                set overview to overview & return
            end repeat
            
            -- Upcoming tasks
            set upcomingTasks to to dos of list "Upcoming"
            set overview to overview & return & "⏰ UPCOMING (" & (count of upcomingTasks) & " tasks):" & return
            repeat with thisToDo in upcomingTasks
                set overview to overview & "• " & (name of thisToDo)
                if (due date of thisToDo) is not missing value then
                    set overview to overview & " (Due: " & (due date of thisToDo) & ")"
                end if
                set overview to overview & return
            end repeat
            
            -- Active projects
            set openProjects to projects whose status is open
            set overview to overview & return & "📁 ACTIVE PROJECTS (" & (count of openProjects) & "):" & return
            repeat with thisProject in openProjects
                set projectTasks to to dos of thisProject whose status is open
                set overview to overview & "• " & (name of thisProject) & " (" & (count of projectTasks) & " tasks)" & return
            end repeat
            
            return overview
        end tell
        '''
        
        return self.execute_applescript(script)

    def update_task(self, task_identifier: str, title: str = None, notes: str = None, 
                   due_date: str = None, tags: List[str] = None) -> str:
        """Update an existing task"""
        
        script_parts = [
            'tell application "Things3"',
            '    try',
            f'        set targetToDo to to do id "{task_identifier}"',
            '    on error',
            '        try',
            f'            set targetToDo to to do "{task_identifier}"',
            '        on error',
            '            return "Task not found"',
            '        end try',
            '    end try',
            '    ',
            '    set updateResult to ""'
        ]
        
        if title:
            script_parts.extend([
                f'    set name of targetToDo to "{title}"',
                '    set updateResult to updateResult & "Title updated. "'
            ])
        
        if notes:
            script_parts.extend([
                f'    set notes of targetToDo to "{notes}"',
                '    set updateResult to updateResult & "Notes updated. "'
            ])
        
        if due_date:
            script_parts.extend([
                f'    set due date of targetToDo to date("{due_date}")',
                '    set updateResult to updateResult & "Due date updated. "'
            ])
        
        script_parts.extend([
            '    return updateResult',
            'end tell'
        ])
        
        script = '\n'.join(script_parts)
        return self.execute_applescript(script)


class Things3MCPServer:
    """MCP Server for Things 3 integration"""
    
    def __init__(self):
        self.things3 = Things3Controller()
        self.server = Server("things3-mcp-server")

    async def run(self):
        """Run the MCP server"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="add_task",
                    description="Add a new task to Things 3",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "notes": {"type": "string", "description": "Task notes (optional)"},
                            "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format (optional)"},
                            "area": {"type": "string", "description": "Area name (optional)"},
                            "project": {"type": "string", "description": "Project name (optional)"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags (optional)"},
                        },
                        "required": ["title"],
                    },
                ),
                types.Tool(
                    name="list_tasks",
                    description="List tasks from Things 3",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "list": {
                                "type": "string",
                                "enum": ["today", "upcoming", "anytime", "someday", "inbox", "completed"],
                                "description": "Which list to retrieve tasks from",
                                "default": "today"
                            },
                            "limit": {"type": "number", "description": "Maximum number of tasks to return", "default": 20},
                        },
                    },
                ),
                types.Tool(
                    name="complete_task",
                    description="Mark a task as completed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID or title to complete"},
                        },
                        "required": ["task_id"],
                    },
                ),
                types.Tool(
                    name="search_tasks",
                    description="Search for tasks by keyword",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "number", "description": "Maximum results", "default": 10},
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="list_projects",
                    description="List projects from Things 3",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["open", "completed", "all"],
                                "description": "Project status filter",
                                "default": "open"
                            },
                        },
                    },
                ),
                types.Tool(
                    name="add_project",
                    description="Add a new project to Things 3",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Project title"},
                            "notes": {"type": "string", "description": "Project notes (optional)"},
                            "area": {"type": "string", "description": "Area name (optional)"},
                            "when": {"type": "string", "description": "When to start (today, someday, etc.)"},
                        },
                        "required": ["title"],
                    },
                ),
                types.Tool(
                    name="get_daily_overview",
                    description="Get a comprehensive daily overview including today's tasks and upcoming items",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                types.Tool(
                    name="update_task",
                    description="Update an existing task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID or title to update"},
                            "title": {"type": "string", "description": "New title (optional)"},
                            "notes": {"type": "string", "description": "New notes (optional)"},
                            "due_date": {"type": "string", "description": "New due date in YYYY-MM-DD format (optional)"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags (optional)"},
                        },
                        "required": ["task_id"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            """Handle tool calls"""
            
            if arguments is None:
                arguments = {}

            try:
                if name == "add_task":
                    task_id = self.things3.add_task(
                        title=arguments["title"],
                        notes=arguments.get("notes", ""),
                        due_date=arguments.get("due_date"),
                        area=arguments.get("area"),
                        project=arguments.get("project"),
                        tags=arguments.get("tags", [])
                    )
                    return [types.TextContent(type="text", text=f"Task '{arguments['title']}' added successfully with ID: {task_id}")]

                elif name == "list_tasks":
                    tasks = self.things3.list_tasks(
                        list_name=arguments.get("list", "today"),
                        limit=arguments.get("limit", 20)
                    )
                    
                    if not tasks:
                        return [types.TextContent(type="text", text=f"No tasks found in {arguments.get('list', 'today')} list")]
                    
                    result = f"Found {len(tasks)} tasks in {arguments.get('list', 'today')}:\n\n"
                    for task in tasks:
                        result += f"• {task['title']}"
                        if task['due_date']:
                            result += f" (Due: {task['due_date']})"
                        if task['notes']:
                            result += f"\n  Notes: {task['notes']}"
                        result += "\n"
                    
                    return [types.TextContent(type="text", text=result)]

                elif name == "complete_task":
                    result = self.things3.complete_task(arguments["task_id"])
                    return [types.TextContent(type="text", text=result)]

                elif name == "search_tasks":
                    tasks = self.things3.search_tasks(
                        query=arguments["query"],
                        limit=arguments.get("limit", 10)
                    )
                    
                    if not tasks:
                        return [types.TextContent(type="text", text=f"No tasks found matching '{arguments['query']}'")]
                    
                    result = f"Found {len(tasks)} tasks matching '{arguments['query']}':\n\n"
                    for task in tasks:
                        result += f"• {task['title']} ({task['status']})\n"
                    
                    return [types.TextContent(type="text", text=result)]

                elif name == "list_projects":
                    projects = self.things3.list_projects(status=arguments.get("status", "open"))
                    
                    if not projects:
                        return [types.TextContent(type="text", text=f"No {arguments.get('status', 'open')} projects found")]
                    
                    result = f"Found {len(projects)} {arguments.get('status', 'open')} projects:\n\n"
                    for project in projects:
                        result += f"• {project['title']}\n"
                    
                    return [types.TextContent(type="text", text=result)]

                elif name == "add_project":
                    project_id = self.things3.add_project(
                        title=arguments["title"],
                        notes=arguments.get("notes", ""),
                        area=arguments.get("area"),
                        when=arguments.get("when", "someday")
                    )
                    return [types.TextContent(type="text", text=f"Project '{arguments['title']}' created successfully with ID: {project_id}")]

                elif name == "get_daily_overview":
                    overview = self.things3.get_daily_overview()
                    return [types.TextContent(type="text", text=overview)]

                elif name == "update_task":
                    result = self.things3.update_task(
                        task_identifier=arguments["task_id"],
                        title=arguments.get("title"),
                        notes=arguments.get("notes"),
                        due_date=arguments.get("due_date"),
                        tags=arguments.get("tags")
                    )
                    return [types.TextContent(type="text", text=result if result else "Task updated successfully")]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

        # Start the server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                NotificationOptions(),
            )


async def main():
    """Main entry point"""
    server = Things3MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
