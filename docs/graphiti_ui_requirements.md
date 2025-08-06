# Graphiti UI Requirements Specification

## Overview

A comprehensive web-based management interface for monitoring and managing Graphiti episode processing, with persistent storage and detailed logging capabilities.

## Core Requirements

### 1. Queue Monitoring

- **Real-time queue status display**
  - Show current items in queue with their file paths
  - Display queue size per group
  - Indicate if queue worker is active
  - Auto-refresh every 5-10 seconds
  - Visual indicators for queue state (empty, processing, backlogged)

### 2. Processing Status Tracking

- **Clear status indicators for each processing stage:**
  - **LM Studio Processing**: When file is being summarized by LM Studio
  - **Graphiti Processing**: When episode is being processed by Graphiti
  - **Queued**: Waiting in queue
  - **Completed**: Successfully processed
  - **Error**: Failed processing
  - **Timing**: Show duration for each stage

### 3. Detailed Logging System

- **Comprehensive log aggregation for each processing run:**

  - **Graphiti MCP Server logs**: Episode processing, node extraction, edge creation
  - **Ollama logs**: Embedding and chat completion requests
  - **Neo4j logs**: Database operations, node/edge creation
  - **LM Studio logs**: File summarization process
  - **Error logs**: Full stack traces and error details
  - **Timing logs**: Performance metrics for each stage

- **Log filtering and search:**
  - Filter by episode/file name
  - Filter by log level (DEBUG, INFO, WARNING, ERROR)
  - Filter by time range
  - Search within log content
  - Collapsible log sections by component

### 4. Node Creation Tracking

- **Display created nodes with full details:**

  - Node UUID/ID
  - Node name
  - Node labels/entity types
  - Node summary
  - Node attributes
  - Creation timestamp
  - Associated episode

- **Node visualization:**
  - List view with sortable columns
  - Graph view showing node relationships
  - Search and filter capabilities
  - Export functionality

### 5. Pagination and History

- **Processed memories pagination:**

  - Configurable page size (10, 25, 50, 100 items per page)
  - Sort by date, status, file name
  - Search across all processed episodes
  - Filter by status, date range, group ID

- **Episode history:**
  - Complete list of all processed episodes
  - Status tracking over time
  - Performance metrics (processing time, success rate)
  - Bulk operations (delete, reprocess)

### 6. Persistent Storage

- **Data retention requirements:**

  - All processing history must survive system reboots
  - Logs must be persisted to disk/database
  - Episode metadata must be stored permanently
  - Node creation records must be maintained
  - Queue history must be preserved

- **Storage implementation:**
  - Use PostgreSQL or SQLite for metadata storage
  - File-based log storage with rotation
  - Backup and restore capabilities
  - Data archival for old records

## Technical Architecture

### Frontend Components

```
Dashboard
├── QueueMonitor
│   ├── QueueStatus
│   ├── ProcessingStatus
│   └── RealTimeUpdates
├── LogViewer
│   ├── LogAggregator
│   ├── LogFilter
│   └── LogSearch
├── NodeTracker
│   ├── NodeList
│   ├── NodeDetails
│   └── NodeGraph
└── EpisodeHistory
    ├── EpisodeList
    ├── EpisodeDetails
    └── Pagination
```

### Backend Services

```
API Server
├── QueueStatusService
│   └── /api/queue/status
├── LoggingService
│   ├── /api/logs/episode/{id}
│   ├── /api/logs/search
│   └── /api/logs/stream
├── NodeService
│   ├── /api/nodes/episode/{id}
│   ├── /api/nodes/search
│   └── /api/nodes/graph
├── EpisodeService
│   ├── /api/episodes
│   ├── /api/episodes/{id}
│   └── /api/episodes/{id}/logs
└── PersistenceService
    ├── Database operations
    ├── Log storage
    └── Backup/restore
```

### Port Configuration

```
Docker Services:
├── Graphiti MCP Server: 8000 (existing)
├── Queue Status API: 8100 (existing)
├── Neo4j Database: 7474 (existing)
├── Ollama LLM: 11434 (existing)
└── Graphiti UI (Next.js): 8080 (NEW - unused port near 8000 range)
```

### Docker Integration

- UI will run as a new service in existing `docker-compose.yml`
- Port 8080 chosen because it's:
  - Near the 8000 range for consistency
  - Not commonly used by other services
  - Available for Docker binding
  - Easy to remember and configure

### Database Schema

```sql
-- Episodes table
CREATE TABLE episodes (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(255) UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    processing_time_ms INTEGER,
    group_id VARCHAR(255)
);

-- Processing stages table
CREATE TABLE processing_stages (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER REFERENCES episodes(id),
    stage_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    error_message TEXT
);

-- Nodes table
CREATE TABLE nodes (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(255) UNIQUE NOT NULL,
    name TEXT NOT NULL,
    labels TEXT[],
    summary TEXT,
    attributes JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    episode_id INTEGER REFERENCES episodes(id)
);

-- Logs table
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER REFERENCES episodes(id),
    component VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);
```

## User Interface Design

### Main Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Graphiti Management Console                                        [⚙️] [🔄] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐                │
│ │ Queue Status    │ │ Current Process │ │ System Health   │                │
│ │ Items: 3        │ │ LM Studio       │ │ ✅ All Good     │                │
│ │ [Progress Bar]  │ │ file1.py        │ │ [Health Icons]  │                │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘                │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Recent Episodes                                                         │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │ │
│ │ │ file1.py    │ │ file2.js    │ │ file3.md    │ │ file4.ts    │        │ │
│ │ │ ✅ Complete │ │ 🔄 Process  │ │ ❌ Error    │ │ ⏳ Queued   │        │ │
│ │ │ 2m 30s      │ │ 1m 45s      │ │ 0m 12s      │ │ --          │        │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Episode Detail View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Episode Details: file1.py                                    [← Back] [🔄] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Processing Timeline                                                     │ │
│ │ [Timeline Chart]                                                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────────────────────────────────────────┐ │
│ │ Nodes Created   │ │ Detailed Logs                                      │ │
│ │ ┌─────────────┐ │ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ Node 1      │ │ │ │ 2024-01-15 10:30:15 [GRAPHITI] Processing...   │ │ │
│ │ │ UUID: abc   │ │ │ │ 2024-01-15 10:30:16 [OLLAMA] Embedding...      │ │ │
│ │ │ Name: John  │ │ │ │ 2024-01-15 10:30:17 [NEO4J] Creating node...   │ │ │
│ │ └─────────────┘ │ │ │ 2024-01-15 10:30:18 [GRAPHITI] Completed       │ │ │
│ │ ┌─────────────┐ │ │ └─────────────────────────────────────────────────┘ │ │
│ │ │ Node 2      │ │ │ [Filter: All | Graphiti | Ollama | Neo4j] [Search] │ │
│ │ │ UUID: def   │ │ └─────────────────────────────────────────────────────┘ │
│ │ │ Name: Corp  │ │                                                         │
│ │ └─────────────┘ │                                                         │
│ └─────────────────┘                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Priority

### Phase 1: Foundation Setup (Week 1) ⭐ **FIRST PRIORITY**

1. **React/Next.js Application Setup**

   - Set up Next.js project with TypeScript
   - Configure Docker container for UI
   - Deploy on port 8080 (unused, near 8000 range)
   - Basic routing and layout structure
   - Integration with existing Docker Compose

2. **Basic Queue Monitoring**
   - Connect to existing `/queue/status` endpoint (port 8100)
   - Real-time queue status display
   - Processing status indicators
   - Basic episode list

### Phase 2: Core Features (Week 2)

1. **Detailed Logging System**

   - Log aggregation from all services
   - Episode-specific log filtering
   - Error highlighting and display

2. **Node Creation Tracking**
   - Node list with details
   - UUID and metadata display
   - Search and filter capabilities

### Phase 3: Advanced Features (Week 3)

1. **Enhanced Logging**

   - Advanced log filtering
   - Log search functionality
   - Performance metrics

2. **Database Integration**
   - Persistent storage implementation
   - Data retention policies
   - Backup/restore functionality

### Phase 4: Polish & Optimization (Week 4)

1. **UI Polish**
   - Pagination implementation
   - Advanced filtering
   - Export capabilities
   - Performance optimization

## Success Criteria

### Functional Requirements

- [ ] Queue status updates in real-time (< 5 second delay)
- [ ] All processing stages clearly visible
- [ ] Complete logs available for each episode
- [ ] All created nodes tracked with UUIDs
- [ ] Pagination works for large datasets
- [ ] Data persists through system reboots

### Performance Requirements

- [ ] UI responds within 2 seconds
- [ ] Log loading completes within 5 seconds
- [ ] Queue updates refresh automatically
- [ ] No data loss during system restarts

### Usability Requirements

- [ ] Intuitive navigation between views
- [ ] Clear status indicators
- [ ] Search and filter capabilities
- [ ] Export functionality for reports

---

**Document Version:** 1.0  
**Created:** January 15, 2025  
**Last Updated:** January 15, 2025  
**Status:** Requirements Defined - Ready for Implementation
