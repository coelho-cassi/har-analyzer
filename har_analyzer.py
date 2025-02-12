from flask import Flask, render_template, request
import json
import os
from haralyzer import HarParser

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")  # Create an "uploads" folder in the project directory
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Create the folder if it doesn't exist


# Function to parse HAR file and extract relevant data
def parse_har(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        har_data = json.load(f)

    parser = HarParser(har_data)
    entries_data = []
    total_time = 0
    status_code_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for entry in parser.har_data['entries']:
        request = entry['request']
        response = entry['response']
        timings = entry['timings']
        time_taken = timings['wait']  # You can adjust this to include other timings as needed

        # Status code category
        status_category = response['status'] // 100
        if status_category in status_code_counts:
            status_code_counts[status_category] += 1

        total_time += time_taken

        # Capture additional details
        entries_data.append({
            "method": request['method'],
            "url": request['url'],  # Full URL for tooltip
            "status": response['status'],
            "content_type": response['content'].get('mimeType', 'N/A'),
            "time": time_taken,  # Time in ms
            "source_ip": request.get('headers', [{}])[0].get('value', 'N/A'),  # Source IP assumed from headers
            "error_message": response.get('statusText') if response['status'] >= 400 else None,  # More robust error retrieval
            "payload": request.get('postData', {}).get('text', 'N/A'),  # Capture request payload if available
            "response_size": response.get('content', {}).get('size', 0),  # Response size in bytes
            "timings": {
                "dns": timings.get('dns', 'N/A'),
                "connect": timings.get('connect', 'N/A'),
                "send": timings.get('send', 'N/A'),
                "wait": timings.get('wait', 'N/A'),
                "receive": timings.get('receive', 'N/A'),
            }
        })

    summary = {
        "total_requests": len(entries_data),
        "total_time": total_time,
        "average_time": total_time / len(entries_data) if entries_data else 0,
        "status_code_counts": status_code_counts,
        "success_count": status_code_counts.get(2, 0),
        "failure_count": status_code_counts.get(4, 0) + status_code_counts.get(5, 0)
    }

    return entries_data, summary

# Route for HAR file analysis
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_file():
    if 'har_file' not in request.files:
        return "No HAR file uploaded", 400
    
    har_file = request.files['har_file']
    
    # Ensure the file has a filename
    if har_file.filename == '':
        return "No selected file", 400
    
    # Save the file in the "uploads" directory
    file_path = os.path.join(UPLOAD_FOLDER, "harfile.har")
    har_file.save(file_path)
    
    # Check if the file exists before proceeding
    if not os.path.exists(file_path):
        print("File was not saved correctly!")  # Debugging
        return "Error saving file", 500
    
    print("File saved successfully at", file_path)  # Debugging output

    # Parse the HAR file
    entries_data, summary = parse_har(file_path)

    # Render results in a simple HTML table in the browser
    return render_template('analyze.html', summary=summary, entries_data=entries_data)

if __name__ == '__main__':
    app.run(debug=True)