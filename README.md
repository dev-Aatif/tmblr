# Drop-Tumblr (Tumblr Automation Bot)

An automated Tumblr bot that syncs local images to your Tumblr native queue, featuring a premium mobile-first dashboard and automatic storage cleanup.

## Overview

This bot allows you to upload images from your phone gallery to local folders (Categories). It then syncs these images to your Tumblr **Native Queue**.

By using Tumblr's native queue, you can upload 50 images at once and let Tumblr handle the "prime time" posting (e.g., 5 posts a day) automatically. The bot also cleans up the `data/done/` folder every 48 hours to stay within PythonAnywhere's free storage limits.

---

## 1. Getting Your Tumblr API Keys

To post automatically, you need to register an application on Tumblr.

1. Go to [Tumblr API Console](https://api.tumblr.com/console/calls/user/info) and log in.
2. Register a new application (call it "Drop-Tumblr").
3. Copy your **Consumer Key** and **Consumer Secret**.
4. Authorize the app to get your **OAuth Token** and **OAuth Token Secret**.

## 2. Environment Setup

Create a `.env` file in the root directory with the following:

```env
TUMBLR_CONSUMER_KEY=your_key
TUMBLR_CONSUMER_SECRET=your_secret
TUMBLR_OAUTH_TOKEN=your_token
TUMBLR_OAUTH_SECRET=your_secret
TUMBLR_BLOG_NAME=your_blog.tumblr.com
CRON_SECRET=your_random_secret_string
```

## 3. Deployment (PythonAnywhere)

1. Clone this repo to your PythonAnywhere account.
2. Create a virtualenv: `mkvirtualenv --python=/usr/bin/python3.10 tmblr-env`
3. Install requirements: `pip install -r requirements.txt`
4. Set up the Web tab with the provided `wsgi.py`.
5. Add your `.env` file to the project folder.

## 4. Automation (cron-job.org)

1. Create a free account on [cron-job.org](https://cron-job.org/).
2. Create a job pointing to: `https://yourusername.pythonanywhere.com/api/test_bot?token=your_random_secret_string`
3. Set it to run every hour.

---

## Storage & Cleanup

The bot is designed to run on PythonAnywhere's 512MB free tier:
- Images are stored in `data/pins/[Category Name]`.
- Once synced to Tumblr, they move to `data/done/`.
- Files in `data/done/` are automatically deleted after 48 hours.
