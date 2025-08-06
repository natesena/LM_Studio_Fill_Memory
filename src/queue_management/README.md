# Graphiti Queue Monitoring Tools

This directory contains enhanced monitoring tools that provide visibility into the Graphiti processing lifecycle, including the gap between `add_episode()` and `task_done()`.

## Problem Solved

The original queue monitoring only showed **waiting items** in the queue, but not **currently processing items**. This created a visibility gap where:

1. Episode gets dequeued (queue appears empty)
2. Ollama processing begins (invisible to monitoring)
3. Processing continues for minutes (queue still shows empty)
4. Only after completion does `task_done()` get called

## Enhanced Monitoring Tools

### 1. `check_processing_status.py` - One-time Status Check

```bash
python src/queue_management/check_processing_status.py
```

Shows current queue status, currently processing episodes, and worker status in a single snapshot.

### 2. `enhanced_queue_monitor.py` - Continuous Queue Monitoring

```bash
python src/queue_management/enhanced_queue_monitor.py --interval 5
```

Continuously monitors queue status, showing both waiting and currently processing episodes.

### 3. `monitor_processing_logs.py` - Real-time Log Monitoring

```bash
python src/queue_management/monitor_processing_logs.py
```

Shows real-time processing logs, including the new "STARTING PROCESSING" and "FINISHED PROCESSING" messages.

### 4. `comprehensive_monitor.py` - All-in-One Monitoring

```bash
# Show status once
python src/queue_management/comprehensive_monitor.py --once

# Continuous monitoring
python src/queue_management/comprehensive_monitor.py --interval 5
```

Combines queue status, processing status, and recent logs in a single view.

## What You'll See Now

### Before (Original Monitoring)

```
[10:30:15] Queue lengths: {'default': 0}
[10:30:20] Queue lengths: {'default': 0}
[10:30:25] Queue lengths: {'default': 0}
```

_Queue appears empty even while Ollama is processing_

### After (Enhanced Monitoring)

```
[10:30:15] Queue Status:
Group 'default': 🔄 PROCESSING: file1.txt | ⏳ WAITING: 2 items | 👷 Worker: ACTIVE
   Next: file2.txt

[10:30:20] Queue Status:
Group 'default': 🔄 PROCESSING: file1.txt | ⏳ WAITING: 2 items | 👷 Worker: ACTIVE
   Next: file2.txt

[10:30:25] Queue Status:
Group 'default': ✅ FINISHED PROCESSING: file1.txt | ⏳ WAITING: 1 items | 👷 Worker: ACTIVE
   Next: file2.txt
```

_Now you can see exactly what's being processed and what's waiting_

## Log Messages Added

The Graphiti server now logs these additional messages:

- `🔄 STARTING PROCESSING: filename.txt for group_id: default`
- `✅ FINISHED PROCESSING: filename.txt for group_id: default`

These appear in the Graphiti container logs and can be monitored with the log monitoring tools.

## Usage Examples

### Monitor During Batch Processing

```bash
# Terminal 1: Start comprehensive monitoring
python src/queue_management/comprehensive_monitor.py --interval 3

# Terminal 2: Run your batch processing
python src/core/batch_processor.py
```

### Quick Status Check

```bash
# Check current status without continuous monitoring
python src/queue_management/check_processing_status.py
```

### Monitor Processing Logs Only

```bash
# Watch the processing lifecycle in real-time
python src/queue_management/monitor_processing_logs.py
```

## Technical Details

The enhanced monitoring works by:

1. **Added `currently_processing` tracking** in `graphiti_mcp_server.py`
2. **Enhanced logging** with STARTING/FINISHED PROCESSING messages
3. **Extended monitoring scripts** to query the new tracking data
4. **Combined queue and processing status** in a single view

This provides complete visibility into the processing lifecycle without changing the core architecture.

## Next Steps

This is a **short-term fix** that provides immediate visibility. For a **long-term solution**, implement the persistent queue system described in the `durable_episode_queue_postgres.md` document, which will provide even better tracking and reliability.
