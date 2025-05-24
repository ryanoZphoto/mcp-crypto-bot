from dotenv import load_dotenv
try:
    # Try to load .env file but don't fail if it can't be loaded
    load_dotenv(override=True)
    print("Successfully loaded .env file")
except Exception as e:
    import sys
    print(f"Warning: Could not load .env file: {e}")
    print("Continuing without environment variables...")

# Environment variables should now be loaded from .env file
import os
print(f"API Key loaded: {os.environ.get('binanceusdt_api_key', 'Not Found')[:5]}...")

from fastapi import FastAPI, Request, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.workflows import run_sample_workflow, COINS
from orchestrator.mcp_client import get_new_sheet_rows
from orchestrator.bots.manager import (
    TradingBot, bot_logs, bot_logs_history, log_categories, 
    LOG_DIR, last_bot_run_data, last_bot_run_data_lock
)
import logging
import threading
import requests
import sys
import numpy as np
import json
from orchestrator.exchange.binance import BinanceClient
from typing import List, Optional
import atexit
import signal
import psutil
import time
import copy

app = FastAPI()

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up Jinja2 templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Set up static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Make sure we have a valid last_bot_run_data
# if 'last_bot_run_data' not in globals() or not isinstance(last_bot_run_data, dict):
#     last_bot_run_data = {
#         'timestamps': [],
#         'prices': [],
#         'short_ma': [],
#         'long_ma': [],
#         'signals': [],
#         'volatility': None,
#         'live_update': False,
#         'no_data': True  # Flag to indicate no real data is available
#     }

bot_status = {
    'last_action': 'Bot not run yet.',
    'last_result': None,
    'last_error': None,
    'is_running': False
}

bot_thread = None
stop_event = threading.Event()
bot_thread_lock = threading.Lock()  # Add this lock for thread safety


def bot_runner():
    global stop_event, bot_status
    print("Bot runner started")
    bot = TradingBot(stop_event=stop_event)
    try:
        bot.run()
        print("Bot run() finished")
        if not stop_event.is_set():
            bot_status['last_action'] = 'Bot run successfully.'
            bot_status['last_result'] = 'Check Slack for trade actions and logs.'
            bot_status['last_error'] = None
    except Exception as e:
        print(f"Exception in bot_runner: {e}")
        bot_status['last_action'] = 'Bot run failed.'
        bot_status['last_result'] = None
        bot_status['last_error'] = str(e)
    finally:
        with bot_thread_lock:
            bot_status['is_running'] = False
        stop_event.clear()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("prices.html", {"request": request, "coins": COINS, "price": None, "selected": "BTC"})

@app.get("/prices", response_class=HTMLResponse)
def prices(request: Request):
    return templates.TemplateResponse("prices.html", {"request": request, "coins": COINS, "price": None, "selected": "BTC"})

@app.post("/get-price", response_class=JSONResponse)
def get_price(symbol: str = Form(...)):
    try:
        coin_row = get_new_sheet_rows(symbol)
        price = coin_row[1]
        # If price is a list, extract the first element
        if isinstance(price, list):
            price = price[0]
        if hasattr(price, 'text'):
            price = price.text
        price_float = float(price)
        price_str = f"${price_float:,.6f}" if price_float < 1 else f"${price_float:,.2f}"
        return {"price": f"Current {symbol} price (USD): {price_str}"}
    except Exception as e:
        logging.exception("Error in /get-price endpoint")
        return JSONResponse(status_code=500, content={"price": f"Error: {str(e)}"})

@app.post("/run-workflow")
def run_workflow(symbol: str = Form("BTC")):
    result = run_sample_workflow(symbol)
    return {"result": result}

@app.get("/bot-control", response_class=HTMLResponse)
def bot_control(request: Request):
    return templates.TemplateResponse(
        "bot_control.html",
        {
            "request": request, 
            "bot_status": bot_status, 
            "bot_logs": bot_logs,
            "log_categories": log_categories
        }
    )

@app.post("/bot-control", response_class=HTMLResponse)
def run_bot(request: Request):
    global bot_thread, stop_event
    
    # Thread-safe check and update
    with bot_thread_lock:
        if bot_status['is_running']:
            # Bot is already running, let's update the status message
            bot_status['last_action'] = 'Bot is already running.'
            bot_status['last_result'] = 'Only one bot instance allowed at a time.'
            bot_status['last_error'] = None
            
            return templates.TemplateResponse(
                "bot_control.html",
                {
                    "request": request, 
                    "bot_status": bot_status, 
                    "bot_logs": bot_logs,
                    "log_categories": log_categories
                }
            )
    
        # Make sure stop_event is cleared
        stop_event.clear()
        
        # Check if the thread exists and is still alive
        if bot_thread and bot_thread.is_alive():
            # Something's wrong - thread is alive but status says not running
            bot_status['last_action'] = 'Inconsistent bot state detected.'
            bot_status['last_result'] = 'Resetting state and starting new bot instance.'
            bot_status['last_error'] = None
            
            # Force thread to stop
            stop_event.set()
            try:
                bot_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to complete
            except:
                pass
                
        # Start a new thread
        bot_thread = threading.Thread(target=bot_runner, daemon=True)
        bot_thread.start()
        
        # Update status
        bot_status['is_running'] = True
        bot_status['last_action'] = 'Bot started.'
        bot_status['last_result'] = 'Bot is running in the background.'
        bot_status['last_error'] = None
    
    return templates.TemplateResponse(
        "bot_control.html",
        {
            "request": request, 
            "bot_status": bot_status, 
            "bot_logs": bot_logs,
            "log_categories": log_categories
        }
    )

@app.post("/stop-bot", response_class=HTMLResponse)
def stop_bot(request: Request):
    global stop_event, bot_thread
    
    with bot_thread_lock:
        if bot_status['is_running'] or (bot_thread and bot_thread.is_alive()):
            # Set stop event
            stop_event.set()
            
            # Update status immediately to prevent race conditions
            bot_status['is_running'] = False
            bot_status['last_action'] = 'Stop signal sent to bot.'
            bot_status['last_result'] = 'Bot will stop as soon as possible.'
            bot_status['last_error'] = None
            
            # Attempt to wait for thread to complete
            if bot_thread and bot_thread.is_alive():
                try:
                    bot_thread.join(timeout=2.0)  # Wait up to 2 seconds
                    if not bot_thread.is_alive():
                        bot_status['last_result'] = 'Bot has been stopped successfully.'
                    else:
                        # Thread is still alive after timeout
                        bot_status['last_error'] = 'Bot thread did not terminate within timeout.'
                except:
                    bot_status['last_error'] = 'Failed to wait for bot thread to complete.'
        else:
            bot_status['last_action'] = 'No bot is currently running.'
            bot_status['last_result'] = None 
            bot_status['last_error'] = None
        
    return templates.TemplateResponse(
        "bot_control.html",
        {
            "request": request, 
            "bot_status": bot_status, 
            "bot_logs": bot_logs,
            "log_categories": log_categories
        }
    )

@app.get("/bot-logs", response_class=JSONResponse)
def get_bot_logs(category: Optional[str] = None):
    """
    Get current bot logs with optional category filtering
    """
    if category and category in log_categories:
        filtered_logs = [log for log in bot_logs if log["category"] == category]
        return {"logs": filtered_logs[::-1]}  # Reverse order (newest first)
    
    return {"logs": bot_logs[::-1]}  # Return logs in reverse order (newest first)

@app.get("/bot-logs-history", response_class=JSONResponse)
def get_bot_logs_history():
    """
    Get list of available log files
    """
    try:
        log_files = []
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("bot_logs_") and filename.endswith(".json"):
                file_path = os.path.join(LOG_DIR, filename)
                # Extract better date format from filename (YYYYMMDD_HHMMSS)
                parts = filename.split("_")
                if len(parts) >= 3:
                    date_part = parts[2]
                    time_part = parts[3].split(".")[0] if len(parts) > 3 else "000000"
                    
                    # Format: YYYYMMDD_HHMMSS
                    if len(date_part) == 8 and len(time_part) == 6:
                        year = date_part[0:4]
                        month = date_part[4:6]
                        day = date_part[6:8]
                        hour = time_part[0:2]
                        minute = time_part[2:4]
                        second = time_part[4:6]
                        
                        formatted_date = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                    else:
                        formatted_date = f"{date_part}_{time_part}"
                else:
                    formatted_date = filename.replace("bot_logs_", "").replace(".json", "")
                
                log_files.append({
                    "filename": filename,
                    "date": formatted_date,
                    "size": os.path.getsize(file_path)
                })
        return {"log_files": sorted(log_files, key=lambda x: x["filename"], reverse=True)}
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to get log history: {str(e)}"}
        )

@app.get("/bot-logs-file/{filename}", response_class=JSONResponse)
def get_bot_logs_file(filename: str, category: Optional[str] = None):
    """
    Get logs from a specific file with optional category filtering
    """
    try:
        file_path = os.path.join(LOG_DIR, filename)
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404, 
                content={"error": f"Log file {filename} not found"}
            )
            
        with open(file_path, 'r') as f:
            logs = json.load(f)
            
        if category and category in log_categories:
            logs = [log for log in logs if log["category"] == category]
            
        return {"logs": logs[::-1]}  # Reverse order (newest first)
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to read log file: {str(e)}"}
        )

@app.get("/log-categories", response_class=JSONResponse)
def get_log_categories():
    """
    Get available log categories
    """
    return {"categories": log_categories}

@app.get("/bot-status", response_class=JSONResponse)
def get_bot_status():
    return bot_status

@app.post("/shutdown", response_class=JSONResponse)
def shutdown(background_tasks: BackgroundTasks):
    """Shutdown both the MCP server and this orchestrator server."""
    # 1. Shutdown MCP server
    try:
        mcp_url = "http://127.0.0.1:8000/shutdown"
        requests.post(mcp_url, timeout=2)
    except Exception as e:
        print(f"Failed to shutdown MCP server: {e}")
    # 2. Shutdown orchestrator (FastAPI/Uvicorn)
    def stop_uvicorn():
        import os
        os._exit(0)
    background_tasks.add_task(stop_uvicorn)
    return {"message": "Orchestrator and MCP server shutting down..."}

@app.get("/price-feed", response_class=JSONResponse)
def price_feed():
    """Return data from the last bot run for chart visualization"""
    # global last_bot_run_data # This global refers to the imported last_bot_run_data
    
    with last_bot_run_data_lock: # This is the lock from manager.py
        # ---- START DEBUG PRINTS ----
        # prices_in_data = last_bot_run_data.get('prices', [])
        # no_data_flag = last_bot_run_data.get('no_data', True)
        # is_dict_instance = isinstance(last_bot_run_data, dict)
        # prices_key_exists = 'prices' in last_bot_run_data
        #
        # print(f"DEBUG /price-feed: id(last_bot_run_data)={id(last_bot_run_data)}")
        # print(f"DEBUG /price-feed: last_bot_run_data['no_data'] = {no_data_flag}")
        # print(f"DEBUG /price-feed: len(last_bot_run_data['prices']) = {len(prices_in_data)}")
        # print(f"DEBUG /price-feed: isinstance(last_bot_run_data, dict) = {is_dict_instance}")
        # print(f"DEBUG /price-feed: 'prices' in last_bot_run_data = {prices_key_exists}")
        # 
        # condition_part1 = not is_dict_instance
        # condition_part2 = not prices_key_exists
        # condition_part3_sub1 = not prices_in_data
        # condition_part3_sub2 = no_data_flag # Effectively last_bot_run_data.get('no_data', True)
        # condition_part3 = condition_part3_sub1 and condition_part3_sub2
        # 
        # final_condition_met = condition_part1 or condition_part2 or condition_part3
        # print(f"DEBUG /price-feed: Condition to return empty_data will be: {final_condition_met}")
        # print(f"    Breakdown: P1 (not_dict)={condition_part1}, P2 (no_prices_key)={condition_part2}, P3 (prices_empty_AND_no_data_true)={condition_part3} [P3.1 (prices_empty)={condition_part3_sub1}, P3.2 (no_data_true)={condition_part3_sub2}]")
        # ---- END DEBUG PRINTS ----

        # Make sure last_bot_run_data (from manager.py) is a valid dictionary with the expected keys
        # if condition_part1 or condition_part2 or condition_part3: # Using original compact condition now
        if (not isinstance(last_bot_run_data, dict) or 
            'prices' not in last_bot_run_data or 
            (not last_bot_run_data['prices'] and last_bot_run_data.get('no_data', True))):
            # print("DEBUG /price-feed: Condition MET. Returning empty_data.") # Added print
            empty_data = {
                'timestamps': [],
                'prices': [],
                'short_ma': [],
                'long_ma': [],
                'signals': [],
                'volatility': None,
                'live_update': False,
                'no_data': True,  # Flag to indicate no real data is available
                'message': 'No real market data available. Start the bot to fetch live data from Binance.'
            }
            
            return empty_data
        
        # If we have data, return it (without resetting it)
        # Make a deep copy to prevent accidental modification
        # print("DEBUG /price-feed: Condition NOT MET. Returning actual data.") # Added print
        data = copy.deepcopy(last_bot_run_data)
        
        # Add metadata about the data source
        data['data_source'] = 'Binance API'
        data['data_count'] = len(data['prices']) if 'prices' in data else 0
        data['timestamp'] = time.time()
        
        return data

@app.get("/chart-debug", response_class=HTMLResponse)
def chart_debug(request: Request):
    """A debug endpoint to check chart data directly"""
    from fastapi.responses import HTMLResponse
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chart Debug</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .chart-container { height: 400px; border: 1px solid #ccc; margin-bottom: 20px; }
            pre { background: #f5f5f5; padding: 10px; overflow: auto; }
        </style>
    </head>
    <body>
        <h1>Chart Debug</h1>
        <div class="chart-container">
            <canvas id="chart"></canvas>
        </div>
        <h2>Raw Data</h2>
        <pre id="rawData">Loading...</pre>
        
        <script>
            let chart;
            
            async function fetchData() {
                try {
                    const response = await fetch('/price-feed-raw');
                    const data = await response.json();
                    document.getElementById('rawData').textContent = JSON.stringify(data, null, 2);
                    renderChart(data);
                } catch (error) {
                    document.getElementById('rawData').textContent = "Error fetching data: " + error;
                }
            }
            
            function renderChart(data) {
                if (!data || !data.last_bot_run_data || !data.last_bot_run_data.prices || data.last_bot_run_data.prices.length === 0) {
                    document.getElementById('rawData').textContent += "\\n\\nNo data available for chart";
                    const ctx = document.getElementById('chart').getContext('2d');
                    if (chart) chart.destroy();
                    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
                    ctx.font = '18px Arial';
                    ctx.fillStyle = '#666';
                    ctx.textAlign = 'center';
                    ctx.fillText('No real data available yet. Start the bot to fetch live data.', ctx.canvas.width/2, ctx.canvas.height/2);
                    return;
                }
                
                const ctx = document.getElementById('chart').getContext('2d');
                if (chart) chart.destroy();
                
                chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: Array.from({ length: data.last_bot_run_data.prices.length }, (_, i) => i),
                        datasets: [
                            {
                                label: 'Price',
                                data: data.last_bot_run_data.prices,
                                borderColor: 'blue',
                                fill: false
                            },
                            {
                                label: 'Short MA',
                                data: data.last_bot_run_data.short_ma,
                                borderColor: 'green',
                                fill: false
                            },
                            {
                                label: 'Long MA',
                                data: data.last_bot_run_data.long_ma,
                                borderColor: 'red',
                                fill: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            }
            
            fetchData();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/price-feed-raw", response_class=JSONResponse)
def price_feed_raw():
    """Return the exact data from last_bot_run_data without any modifications"""
    # global last_bot_run_data # This global refers to the imported last_bot_run_data
    
    # Check the data type of each field
    data_types = {}
    if isinstance(last_bot_run_data, dict):
        for key, value in last_bot_run_data.items():
            if hasattr(value, '__len__') and not isinstance(value, str):
                data_types[key] = {
                    'type': str(type(value)),
                    'length': len(value),
                    'sample': str(value[:5] if hasattr(value, '__getitem__') else None)
                }
            else:
                data_types[key] = {
                    'type': str(type(value)),
                    'value': str(value)
                }
    
    # Create a new copy of the data with debug information
    debug_data = {
        'last_bot_run_data': last_bot_run_data,
        'data_types': data_types,
        'is_dict': isinstance(last_bot_run_data, dict),
        'has_prices': isinstance(last_bot_run_data, dict) and 'prices' in last_bot_run_data,
        'server_time': time.time()
    }
    
    return debug_data

@app.post("/frontend-error", response_class=JSONResponse)
async def frontend_error(request: Request):
    data = await request.json()
    print("[FRONTEND ERROR]", data.get('message', ''), data.get('stack', ''))
    return {"status": "logged"}

# Add process cleanup code
def cleanup_processes():
    """Clean up any child processes when shutting down"""
    current_process = psutil.Process()
    
    # First try graceful termination of child processes
    children = current_process.children(recursive=True)
    for child in children:
        try:
            child.terminate()
            print(f"Terminated child process with PID {child.pid}")
        except:
            pass
    
    # Wait a moment for processes to terminate
    gone, still_alive = psutil.wait_procs(children, timeout=2)
    
    # Force kill any remaining processes
    for process in still_alive:
        try:
            process.kill()
            print(f"Force killed child process with PID {process.pid}")
        except:
            pass
            
# Register cleanup function
atexit.register(cleanup_processes)

# Add this function to restart the application with a clean state
def restart_application(background_tasks: BackgroundTasks):
    """Restart the application by terminating all child processes and starting a new instance"""
    cleanup_processes()
    
    # Kill any process using port 8001
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == 8001:
                    print(f"Killing process {proc.info['pid']} using port 8001")
                    proc.terminate()
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
            pass
    
    # Use the background tasks to allow response to be sent first
    def restart():
        import subprocess
        import time
        
        try:
            # Start a new instance with a shell and wait flag to ensure it starts
            new_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "orchestrator.main:app", "--port", "8001"],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait longer to ensure the process starts properly
            time.sleep(3)
            
            # Check if the process is running
            if new_process.poll() is None:
                print(f"New server process started with PID {new_process.pid}")
                # Only exit current process if new process has started successfully
                time.sleep(1)
                os._exit(0)
            else:
                print("Failed to start new server process")
                stdout, stderr = new_process.communicate()
                print(f"STDOUT: {stdout.decode() if stdout else 'None'}")
                print(f"STDERR: {stderr.decode() if stderr else 'None'}")
        except Exception as e:
            print(f"Error restarting server: {str(e)}")
        
    background_tasks.add_task(restart)
    return {"message": "Restarting application..."}

@app.post("/restart", response_class=JSONResponse)
def restart_endpoint(background_tasks: BackgroundTasks):
    """Restart the application with a clean state"""
    try:
        # Check if port is already in use before trying to restart
        port_in_use = False
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == 8001 and proc.info['pid'] != os.getpid():
                        # Port is in use by another process
                        port_in_use = True
                        print(f"Port 8001 is already in use by process {proc.info['pid']} ({proc.info['name']})")
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                pass
                
        if port_in_use:
            return {"message": "Port 8001 is already in use by another process. Please use the 'Kill Port Processes' button first, then restart."}
            
        return restart_application(background_tasks)
    except Exception as e:
        print(f"Error in restart endpoint: {str(e)}")
        return {"message": f"Error restarting application: {str(e)}", "error": True}

@app.post("/kill-port-processes", response_class=JSONResponse)
def kill_port_processes():
    """Kill any processes using port 8001"""
    killed = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == 8001:
                        proc_info = f"{proc.info['pid']} ({proc.info['name']})"
                        print(f"Killing process {proc_info} using port 8001")
                        proc.terminate()
                        killed.append(proc_info)
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                pass
                
        return {"status": "success", "killed": killed or ["No processes found using port 8001"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug-chart-data", response_class=JSONResponse)
def debug_chart_data():
    """Debug endpoint to inspect the last_bot_run_data structure"""
    # global last_bot_run_data # This global refers to the imported last_bot_run_data
    
    # Check if last_bot_run_data exists and its basic structure
    result = {
        "exists": last_bot_run_data is not None,
        "is_dict": isinstance(last_bot_run_data, dict),
        "keys": list(last_bot_run_data.keys()) if isinstance(last_bot_run_data, dict) else None,
        "timestamp": time.time()
    }
    
    # Check array lengths
    if isinstance(last_bot_run_data, dict):
        for key in last_bot_run_data:
            if isinstance(last_bot_run_data[key], list):
                result[f"{key}_length"] = len(last_bot_run_data[key])
                result[f"{key}_sample"] = last_bot_run_data[key][:5] if last_bot_run_data[key] else []
            else:
                result[f"{key}_value"] = last_bot_run_data[key]
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
