import os
import glob
import time
import json
import random
import logging
import base64
import pytumblr
import mimetypes
from datetime import datetime
from dotenv import load_dotenv
import analytics_db

# Load env variables
load_dotenv()

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tumblr API Credentials
CONSUMER_KEY = os.getenv("TUMBLR_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("TUMBLR_CONSUMER_SECRET")
OAUTH_TOKEN = os.getenv("TUMBLR_OAUTH_TOKEN")
OAUTH_SECRET = os.getenv("TUMBLR_OAUTH_SECRET")
BLOG_NAME = os.getenv("TUMBLR_BLOG_NAME")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = os.path.join(BASE_DIR, "data", "pins") # We'll keep the actual folder name as 'pins' for compatibility, but the variable is now LIBRARY_DIR
DONE_DIR = os.path.join(BASE_DIR, "data", "done")
TITLES_FILE = os.path.join(BASE_DIR, "data", "titles.txt")
RECENT_FILE = os.path.join(BASE_DIR, "data", "recent.json")
TAGS_DIR = os.path.join(BASE_DIR, "data", "tags")

def get_all_images():
    """Finds all image files across all category folders."""
    image_list = []

    if not os.path.exists(LIBRARY_DIR):
        return image_list

    # Iterate through all subfolders in data/pins/
    for folder in os.listdir(LIBRARY_DIR):
        folder_path = os.path.join(LIBRARY_DIR, folder)
        if os.path.isdir(folder_path):
            # Check files in this folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    # Check if it's an image
                    mimetype, _ = mimetypes.guess_type(file_path)
                    if mimetype and mimetype.startswith('image'):
                        image_list.append((file_path, folder))
    
    # Sort by creation time so we process oldest first
    image_list.sort(key=lambda x: os.path.getmtime(x[0]))
    return image_list

def get_random_title(category_name):
    """Combines a random phrase from titles.txt with the category name."""
    try:
        with open(TITLES_FILE, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return f"Inspiration | {category_name}"
        phrase = random.choice(lines)
        return f"{phrase} | {category_name}"
    except Exception as e:
        logging.error(f"Error reading titles: {e}")
        return f"Aesthetic | {category_name}"

def get_random_tags(category_name):
    """Reads category-specific tags JSON and selects exactly 10 random tags."""
    default_tags = [category_name, "aesthetic", "photography", "inspiration", "moodboard"]
    
    tags_file = os.path.join(TAGS_DIR, f"{category_name}.json")
    if not os.path.exists(tags_file):
        return default_tags
        
    try:
        with open(tags_file, 'r', encoding='utf-8') as f:
            pool = json.load(f)
            
        if not pool:
            return default_tags
            
        # Ensure category name is always included
        selected_tags = [category_name]
        
        # Select up to 9 random tags from the pool
        num_to_select = min(9, len(pool))
        random_selections = random.sample(pool, num_to_select)
        
        selected_tags.extend(random_selections)
        return selected_tags
        
    except Exception as e:
        logging.error(f"Error reading tags for {category_name}: {e}")
        return default_tags

def log_activity(filename, category_name, status, title):
    """Logs the activity to recent.json"""
    try:
        # Read current log
        activities = []
        if os.path.exists(RECENT_FILE):
            with open(RECENT_FILE, 'r') as f:
                try:
                    activities = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        # Add new log entry
        activities.insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": os.path.basename(filename),
            "category": category_name,
            "title": title,
            "status": status
        })
        
        # Keep only the last 20 (since we might upload many at once)
        activities = activities[:20]
        
        with open(RECENT_FILE, 'w') as f:
            json.dump(activities, f, indent=4)
            
    except Exception as e:
        logging.error(f"Error logging activity: {e}")

def cleanup_done_folder():
    """Removes files from the done directory that are older than 48 hours."""
    logging.info("Cleaning up 'done' folder...")
    if not os.path.exists(DONE_DIR):
        return
    
    now = time.time()
    seconds_in_48_hours = 48 * 60 * 60
    
    count = 0
    for filename in os.listdir(DONE_DIR):
        file_path = os.path.join(DONE_DIR, filename)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < now - seconds_in_48_hours:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    logging.error(f"Error deleting {filename}: {e}")
    
    logging.info(f"Cleanup finished. Removed {count} old files.")

def get_tumblr_stats():
    """Fetches follower count, total posts, and queue length from Tumblr API."""
    if not all([CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_SECRET, BLOG_NAME]):
        return None
        
    try:
        client = pytumblr.TumblrRestClient(
            CONSUMER_KEY,
            CONSUMER_SECRET,
            OAUTH_TOKEN,
            OAUTH_SECRET
        )
        
        # Get followers and total posts
        blog_info = client.blog_info(BLOG_NAME)
        followers = blog_info['blog'].get('followers', 0)
        total_posts = blog_info['blog'].get('posts', 0)
        
        # Get queue length
        queue = client.queue(BLOG_NAME)
        queue_length = len(queue.get('posts', []))
        
        return {
            "followers": followers,
            "total_posts": total_posts,
            "queue_length": queue_length
        }
    except Exception as e:
        logging.error(f"Error fetching Tumblr stats: {e}")
        return None

def auto_reblog(client):
    """Searches for popular posts in random tags and reblogs one to the queue."""
    tags_to_search = ["aesthetic", "photography", "inspiration", "moodboard", "design", "art"]
    tag = random.choice(tags_to_search)
    
    logging.info(f"Auto-Reblog: Searching for tag #{tag}")
    try:
        # Search for recent posts with this tag
        posts = client.tagged(tag, limit=10, filter='text')
        
        # Filter to only photo posts
        photo_posts = [p for p in posts if p.get('type') == 'photo']
        
        if not photo_posts:
            logging.info("Auto-Reblog: No suitable photo posts found.")
            return
            
        # Pick a random one to reblog
        post_to_reblog = random.choice(photo_posts)
        
        response = client.reblog(
            BLOG_NAME,
            id=post_to_reblog['id'],
            reblog_key=post_to_reblog['reblog_key'],
            state="queue"
        )
        
        if 'id' in response:
            logging.info(f"Successfully auto-reblogged post {post_to_reblog['id']} to queue!")
        else:
            logging.error(f"Failed to auto-reblog: {response}")
            
    except Exception as e:
        logging.error(f"Exception during auto-reblog: {e}")

def auto_follow_and_unfollow(client):
    """Follows users who engaged with recent posts, and unfollows old ones."""
    # 1. Unfollow users followed > 7 days ago
    try:
        old_follows = analytics_db.get_old_follows(days=7)
        for username in old_follows:
            logging.info(f"Auto-Unfollow: Unfollowing {username} (followed > 7 days ago)")
            client.unfollow(f"{username}.tumblr.com")
            analytics_db.remove_follow_log(username)
            time.sleep(1) # Be nice to API
    except Exception as e:
        logging.error(f"Exception during auto-unfollow: {e}")

    # 2. Find new users to follow (up to 2 per run to stay safe)
    try:
        # Get recent posts
        recent_posts = client.posts(BLOG_NAME, limit=5, notes_info=True)
        users_to_follow = set()
        
        for post in recent_posts.get('posts', []):
            notes = post.get('notes', [])
            for note in notes:
                # If someone liked or reblogged
                if note.get('type') in ['like', 'reblog']:
                    username = note.get('blog_name')
                    # Don't follow ourselves
                    if username and username not in BLOG_NAME:
                        users_to_follow.add(username)
                        
                if len(users_to_follow) >= 2:
                    break
            if len(users_to_follow) >= 2:
                break
                
        # Follow them
        for username in users_to_follow:
            logging.info(f"Auto-Follow: Following {username} (engaged with your post)")
            client.follow(f"{username}.tumblr.com")
            analytics_db.log_follow(username)
            time.sleep(1)
            
    except Exception as e:
        logging.error(f"Exception during auto-follow: {e}")

def run_bot_job():
    """Main job that uploads all pending images to Tumblr queue."""
    logging.info("Starting Tumblr sync job...")
    
    if not all([CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_SECRET, BLOG_NAME]):
        logging.warning("Tumblr API credentials missing. Job aborted.")
        return
        
    # Authenticate with Tumblr
    client = pytumblr.TumblrRestClient(
        CONSUMER_KEY,
        CONSUMER_SECRET,
        OAUTH_TOKEN,
        OAUTH_SECRET
    )
    
    # 1. Get all images
    images = get_all_images()
    if not images:
        logging.info("No images found in the local queue.")
        cleanup_done_folder() # Still run cleanup even if no new images
        return
        
    logging.info(f"Found {len(images)} images to upload to Tumblr queue.")
    
    success_count = 0
    for image_path, category_name in images:
        # 2. Get Title / Caption
        title = get_random_title(category_name)
        
        # Tumblr "Algorithm Hack"
        tags = get_random_tags(category_name)
        
        logging.info(f"Uploading: {image_path} to {BLOG_NAME} (State: Queue)")
        
        try:
            # 3. Create Photo Post in Queue
            response = client.create_photo(
                BLOG_NAME,
                state="queue",
                tags=tags,
                data=image_path,
                caption=title
            )
            
            if 'id' in response:
                logging.info(f"Successfully queued {title} to Tumblr!")
                # Move to done directory
                filename = os.path.basename(image_path)
                done_path = os.path.join(DONE_DIR, f"{int(time.time())}_{filename}")
                os.rename(image_path, done_path)
                
                log_activity(image_path, category_name, "Queued", title)
                success_count += 1
                time.sleep(1)
            else:
                logging.error(f"Failed to queue to Tumblr: {response}")
                error_path = image_path + ".error"
                os.rename(image_path, error_path)
                log_activity(image_path, category_name, f"Error: API {response}", title)
                
        except Exception as e:
            logging.error(f"Exception during Tumblr upload: {e}")
            error_path = image_path + ".error"
            os.rename(image_path, error_path)
            log_activity(image_path, category_name, "Error: Exception", title)

    # 4. Phase 3: Engagement Growth Engine
    logging.info("Starting Phase 3 Growth Engine...")
    auto_reblog(client)
    auto_follow_and_unfollow(client)

    # 5. Cleanup old files to save space
    cleanup_done_folder()
    
    logging.info(f"Finished job. Successfully queued {success_count} posts.")

if __name__ == "__main__":
    # Test run
    run_bot_job()
