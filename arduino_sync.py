import serial
import time
import requests
import json
import csv
from datetime import datetime, timedelta
import re
import os

ARDUINO_PORT = 'COM3' 
BAUD_RATE = 9600

API_URL = "https://api.myteaspoon.tech/api/v2/assignments?semester_code=2027_WINTER"

API_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDA2Mjc0MzU2MDAyMTQ4NTE5NjAiLCJpZCI6Mzc5LCJyb2xlIjoic3R1ZGVudCIsImV4cCI6MTc5NTQzMjIzMH0.J1xBzQZz1YDLcfZt28qzzfz3csem__dSs6iE9jn1XNA",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
    "Origin": "https://myteaspoon.tech",
    "Referer": "https://myteaspoon.tech/"
}
CSV_FILE = "study_analytics.csv"
ser = None

COURSE_MAP = {
    "1040012": "Calculus:",
    "1040064": "Algebra:",
    "0450002": "ECE Intro:",
    "1140071": "Physics:",
    "2340117": "C Intro:",
}

TYPE_MAP = {
    "Assignment": "HW", "other": "", "Webwork": "WW", 
}


def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'Time', 'Task', 'Duration (Minutes)'])

def log_session(task_name, duration):
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        now = datetime.now()
        writer.writerow([now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), task_name, duration])
    print(f"\n[+] Logged {duration} mins for {task_name}")

def parse_task_name(summary, additional_info):
    course_prefix = ""
    for course_num, eng_name in COURSE_MAP.items():
        if course_num in summary or course_num in additional_info:
            course_prefix = eng_name + " "
            summary = summary.replace(course_num, "")
            break
            
    summary = re.sub(r'[א-ת]', '', summary)
    summary = summary.replace("()", "").replace("[]", "").replace("-", "")
    
    clean_action = " ".join(summary.split())
    return (course_prefix + clean_action).strip()

def parse_teaspoon_time(deadline_str):
    if not deadline_str:
        return None
    clean_str = deadline_str.replace("T", " ").replace("Z", "").split(".")[0]
    dt = None
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            break
        except ValueError:
            continue
            
    if dt:
        dt += timedelta(hours=2)
        return dt
        
    return None

def extract_all_digits(text):
    return int(''.join(char for char in text if char.isdigit()))

def get_all_tasks_from_api():
    now = datetime.now()
    upcoming_events = []

    try:
        response = requests.get(API_URL, headers=API_HEADERS)
        response.raise_for_status() 
        tasks_data = response.json()

        for task in tasks_data:
            if task.get("is_completed") == True:
                continue
            course_code = str(task.get("course_code", ""))
            task_id = str(task.get("id", ""))
            
            is_my_course = False
            for my_course in COURSE_MAP.keys():
                if my_course in course_code:
                    is_my_course = True
                    break
            
            if not is_my_course:
                continue

            deadline_str = task.get("deadline")
            if not deadline_str:
                continue
                
            try:
                deadline_dt = parse_teaspoon_time(deadline_str)
            except ValueError:
                continue
                
            if deadline_dt < now:
                continue

            summary = TYPE_MAP.get(task.get("type", "other"), "N/A")
            number = extract_all_digits(task.get("title", "N/A"))
            summary += f" {number}" if number else ""
            upcoming_events.append((task_id, deadline_dt, summary, course_code))

        if not upcoming_events:
            return [(-1,"No upcoming", "tasks found")]

        upcoming_events.sort(key=lambda x: x[1])
        
        parsed_tasks = []
        for task_id, dt, summary, course_code in upcoming_events:
            time_str = dt.strftime("%H:%M %d/%m")
            final_text = parse_task_name(summary, course_code)
            line0 = task_id
            line1 = final_text[:16]
            line2 = f"Due: {time_str}"[:16]
            parsed_tasks.append((line0, line1, line2))
            
        if not parsed_tasks:
             return [(-1,"All Tasks Done!", "Great Job!")]
             
        return parsed_tasks

    except Exception as e:
        print(f"API Error: {e}")
        return [("Network Error", "Check API/WiFi")]

def close_serial_connection():
    global ser
    if 'ser' in globals() and ser and ser.is_open:
        try:
            ser.close()
            print("Serial connection closed cleanly.")
        except Exception as e:
            print(f"Error closing serial connection: {e}")

def toggle_teaspoon_task(assignment_id):
    print(f"\n[>] Toggling assignment {assignment_id} in TeaSpoon...")
    url = f"https://api.myteaspoon.tech/api/v2/assignments/{assignment_id}/toggle"
    post_headers = API_HEADERS.copy()
    if "Content-Type" in post_headers:
        del post_headers["Content-Type"]
    post_headers["Accept"] = "*/*"
    post_headers["Content-Length"] = "0"
    try:
        response = requests.post(url, headers=post_headers, data="")
        if response.status_code == 200:
            print(f"✅ Successfully toggled assignment {assignment_id} in TeaSpoon!")
        else:
            print(f"❌ Failed to update TeaSpoon. Status: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error connecting to TeaSpoon API: {e}")

def run_background_worker():
    global ser
    init_csv()
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) 
        
        task_list = get_all_tasks_from_api()
        print(f"\n[>] Fetched {task_list}  from TeaSpoon API.")
        current_index = 0
        
        def send_current_task():
            line0, line1, line2 = task_list[current_index]
            ser.write(f"{line1}|{line2}\n".encode('utf-8'))
            print(f"[{current_index + 1}/{len(task_list)}] Task Sent: {line0} | {line1} | {line2}")

        send_current_task()
        print("\n[System is running in background]")
        print("Commands: NEXT (>>|), PREV (|<<), REFRESH (>||), DONE (EQ)")
        
        while True:
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8').strip()
                
                if incoming.startswith("WORK_DONE"):
                    parts = incoming.split('|')
                    duration = parts[1] if len(parts) > 1 else "25"
                    current_task_name = task_list[current_index][1] if len(task_list) > 0 else "Unknown"
                    log_session(current_task_name, duration)
                
                elif incoming == "NEXT":
                    current_index = (current_index + 1) % len(task_list)
                    send_current_task()
                    
                elif incoming == "PREV":
                    current_index = (current_index - 1) % len(task_list)
                    send_current_task()
                    
                elif incoming == "REFRESH":
                    print("\n[Refreshing data from TeaSpoon API...]")
                    task_list = get_all_tasks_from_api()
                    current_index = 0
                    send_current_task()
                    
                elif incoming == "DONE":
                    if len(task_list) > 0 and task_list[0][0] != "All Tasks Done!":
                        completed_task = task_list.pop(current_index)
                        task_id = completed_task[0]
                        print(f"\n[V] Task Completed & Saved: {completed_task[1]}")
                        toggle_teaspoon_task(task_id)
                        
                        if len(task_list) > 0:
                            if current_index >= len(task_list):
                                current_index = 0
                            send_current_task()
                        else:
                            task_list = [(-1,"All Tasks Done!", "Great Job!")]
                            current_index = 0
                            send_current_task()
                            print("All tasks completed.")                
            time.sleep(0.1) 

    except serial.SerialException:
        print("Connection failed. Make sure Serial Monitor is closed.")
    except KeyboardInterrupt:
        print("\nExiting by user...")
    finally:
        close_serial_connection()

if __name__ == '__main__':
    run_background_worker()