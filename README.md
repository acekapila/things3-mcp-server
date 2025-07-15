# Things 3 MCP Server

A Model Context Protocol (MCP) server that provides integration with Things 3 and Calendar app on macOS. This server allows AI assistants and other MCP clients to interact with your Things 3 tasks, projects, and areas through a standardized interface.

## Features

### To-Do Management
- **Add To-Dos**: Create new tasks with title, notes, due date, tags, and assign to specific lists, projects, or areas
- **List To-Dos**: Retrieve tasks from any list (Inbox, Today, Anytime, Upcoming, Someday, Logbook, Trash) or from specific projects/areas
- **Update To-Dos**: Modify existing tasks (title, notes, due date, tags)
- **Complete To-Dos**: Mark tasks as completed
- **Delete To-Dos**: Move tasks to trash

### Project Management
- **Add Projects**: Create new projects with notes, tags, and area assignment
- **List Projects**: View all projects filtered by status (open, completed, all) or area

### Area Management
- **Add Areas**: Create new areas of responsibility
- **List Areas**: View all areas

### Additional Features
- **Search**: Search across all to-dos, projects, and areas
- **Daily Overview**: Get a summary of today's tasks and counts
- **Quick Entry**: Open Things 3's Quick Entry panel with optional pre-filled content

## Requirements

- macOS (Things 3 is Mac-only)
- Things 3 installed
- Python 3.7+
- MCP package

## Installation

1. Clone this repository or download the server files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Install as a package:
   ```bash
   pip install -e .
   ```

## Configuration

### For Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "things3": {
      "command": "python3",
      "args": ["/path/to/things3_server.py"],
      "env": {}
    },
   "calendar": {
      "command": "python3", 
      "args": ["/Users/acekapila/Documents/llm_train/things3-mcp/venv/calendar_server.py"]
    }
  }
}
```

### For Other MCP Clients

Use the provided `mcp.json` configuration file or run directly:

```bash
python things3_server.py
```

The server communicates via stdin/stdout, making it compatible with any MCP client.

## Testing

Run the test script to verify the server is working:

```bash
python test_server.py
```

This will test basic functionality like listing areas, getting today's overview, and creating a test task.

### Available Tools

1. **things3_add_todo**
   - Add a new to-do with optional properties
   - Parameters: title (required), notes, due_date, tags, list, project, area

2. **things3_list_todos**
   - List to-dos from a specific list, project, or area
   - Parameters: list, project, area, limit

3. **things3_complete_todo**
   - Mark a to-do as completed
   - Parameters: title (required)

4. **things3_update_todo**
   - Update an existing to-do
   - Parameters: title (required), new_title, notes, due_date, tags

5. **things3_delete_todo**
   - Move a to-do to trash
   - Parameters: title (required)

6. **things3_add_project**
   - Create a new project
   - Parameters: title (required), notes, area, tags, when

7. **things3_list_projects**
   - List projects with filters
   - Parameters: status, area

8. **things3_add_area**
   - Create a new area
   - Parameters: title (required), tags

9. **things3_list_areas**
   - List all areas
   - No parameters

10. **things3_search**
    - Search across all items
    - Parameters: query (required), limit

11. **things3_daily_overview**
    - Get today's task summary
    - No parameters

12. **things3_quick_entry**
    - Open Quick Entry panel
    - Parameters: title, notes, autofill

###
