import os
import json
import shutil
from flask import Flask, render_template, request, jsonify
from bot import run_bot_job, get_tumblr_stats, LIBRARY_DIR, DONE_DIR, TITLES_FILE, RECENT_FILE, TAGS_DIR
import analytics_db

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
    category_name = request.form.get('category_name')
    images = request.files.getlist('image')
    
    if not images or not images[0].filename:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    if not category_name:
        return jsonify({"status": "error", "message": "No category/tag selected"}), 400
        
    # Create category directory if it doesn't exist
    category_dir = os.path.join(LIBRARY_DIR, category_name)
    os.makedirs(category_dir, exist_ok=True)
    
    uploaded_count = 0
    for image in images:
        if image and image.filename:
            # Basic validation
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
            _, ext = os.path.splitext(image.filename)
            if ext.lower() not in allowed_extensions:
                continue
                
            filename = os.path.basename(image.filename)
            save_path = os.path.join(category_dir, filename)
            image.save(save_path)
            uploaded_count += 1
        
    if uploaded_count == 0:
        return jsonify({"status": "error", "message": "No valid images uploaded"}), 400
        
    return jsonify({"status": "success", "message": f"{uploaded_count} image(s) added successfully!"})

@app.route('/api/tags', methods=['POST'])
def api_tags():
    data = request.json
    category = data.get('category')
    tags_string = data.get('tags', '')
    
    if not category:
        return jsonify({"status": "error", "message": "Category is required"}), 400
        
    # Parse tags into a list
    tags_list = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    
    if not tags_list:
        return jsonify({"status": "error", "message": "At least one tag is required"}), 400
        
    os.makedirs(TAGS_DIR, exist_ok=True)
    tags_file = os.path.join(TAGS_DIR, f"{category}.json")
    
    try:
        with open(tags_file, 'w', encoding='utf-8') as f:
            json.dump(tags_list, f, indent=4)
        return jsonify({"status": "success", "message": "Tags saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route('/api/stats', methods=['GET'])
def api_stats():
    # Gather local stats
    local_stats = {
        "global_captions": 0,
        "categories": []
    }
    
    # 1. Count global captions
    if os.path.exists(TITLES_FILE):
        with open(TITLES_FILE, 'r', encoding='utf-8') as f:
            local_stats["global_captions"] = len([line for line in f if line.strip()])
            
    # 2. Gather category data
    all_time_totals = analytics_db.get_category_totals()
    if os.path.exists(LIBRARY_DIR):
        for category in os.listdir(LIBRARY_DIR):
            cat_path = os.path.join(LIBRARY_DIR, category)
            if os.path.isdir(cat_path):
                # Count posts
                posts_count = len([f for f in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, f)) and not f.endswith('.error')])
                
                # Count tags
                tags_count = 0
                tags_file = os.path.join(TAGS_DIR, f"{category}.json")
                if os.path.exists(tags_file):
                    try:
                        with open(tags_file, 'r', encoding='utf-8') as f:
                            tags_data = json.load(f)
                            tags_count = len(tags_data)
                    except:
                        pass
                
                all_time = all_time_totals.get(category, 0)
                        
                local_stats["categories"].append({
                    "name": category,
                    "posts": posts_count,
                    "tags": tags_count,
                    "all_time": all_time
                })

    # Try to fetch fresh stats from Tumblr
    fresh_stats = get_tumblr_stats()
    
    if fresh_stats:
        analytics_db.save_stats(
            fresh_stats['followers'],
            fresh_stats['total_posts'],
            fresh_stats['queue_length']
        )
        return jsonify({"status": "success", "data": fresh_stats, "local": local_stats})
        
    cached_stats = analytics_db.get_latest_stats()
    if cached_stats:
        return jsonify({"status": "success", "data": cached_stats, "local": local_stats})
        
    return jsonify({"status": "error", "message": "Could not load Tumblr stats", "local": local_stats}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
