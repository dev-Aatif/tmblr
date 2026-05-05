import os
import json
import shutil
from flask import Flask, render_template, request, jsonify
from bot import run_bot_job, LIBRARY_DIR, DONE_DIR, TITLES_FILE, RECENT_FILE

app = Flask(__name__, static_folder='static', template_folder='templates')

# Read optional secret token for cron job security
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Helper function to get storage usage in MB
def get_storage_usage():
    total_size = 0
    dirs_to_check = [LIBRARY_DIR, DONE_DIR]
    for d in dirs_to_check:
        if os.path.exists(d):
            for dirpath, dirnames, filenames in os.walk(d):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
    return round(total_size / (1024 * 1024), 2)

# Helper function to get queue status
def get_queue_data():
    queue = {}
    if not os.path.exists(LIBRARY_DIR):
        return queue
    
    for folder in os.listdir(LIBRARY_DIR):
        folder_path = os.path.join(LIBRARY_DIR, folder)
        if os.path.isdir(folder_path):
            # Count only files (images)
            count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith('.error')])
            queue[folder] = count
    return queue

@app.route('/')
def index():
    return render_template('index.html', sync_token=CRON_SECRET)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/api/queue', methods=['GET'])
def api_queue():
    queue_data = get_queue_data()
    storage_usage = get_storage_usage()
    return jsonify({
        "status": "success", 
        "data": queue_data,
        "storage": {
            "used": storage_usage,
            "total": 512,
            "percent": round((storage_usage / 512) * 100, 1)
        }
    })

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image part"}), 400
    
    file = request.files['image']
    category_name = request.form.get('category_name') # Changed from board_name
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if not category_name:
        return jsonify({"status": "error", "message": "No category/tag selected"}), 400
        
    # Create category directory if it doesn't exist
    category_dir = os.path.join(LIBRARY_DIR, category_name)
    os.makedirs(category_dir, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(category_dir, file.filename)
    file.save(file_path)
    
    return jsonify({"status": "success", "message": f"Uploaded to {category_name}"})

@app.route('/api/titles', methods=['POST'])
def api_titles():
    data = request.json
    new_titles = data.get('titles', '')
    
    if not new_titles:
        return jsonify({"status": "error", "message": "No titles provided"}), 400
        
    # Append to titles.txt
    with open(TITLES_FILE, 'a', encoding='utf-8') as f:
        f.write("\n" + new_titles)
        
    return jsonify({"status": "success", "message": "Titles added"})

@app.route('/api/activity', methods=['GET'])
def api_activity():
    if not os.path.exists(RECENT_FILE):
        return jsonify({"status": "success", "data": []})
        
    try:
        with open(RECENT_FILE, 'r') as f:
            data = json.load(f)
            return jsonify({"status": "success", "data": data})
    except json.JSONDecodeError:
         return jsonify({"status": "success", "data": []})

@app.route('/api/clear_done', methods=['POST'])
def api_clear_done():
    if not os.path.exists(DONE_DIR):
        return jsonify({"status": "success", "message": "Done folder is empty"})
        
    count = 0
    for filename in os.listdir(DONE_DIR):
        file_path = os.path.join(DONE_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                count += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            pass
            
    return jsonify({"status": "success", "message": f"Cleared {count} files"})

@app.route('/api/test_bot', methods=['GET', 'POST'])
def test_bot():
    """Endpoint for syncing the local queue to Tumblr's native queue."""
    token = request.args.get('token', '')
    if CRON_SECRET and token != CRON_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized. Invalid token."}), 401
        
    # Process all images
    run_bot_job()
    return jsonify({"status": "success", "message": "Sync completed. Check Recent Activity or Tumblr Queue."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
