from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY
import re
import pandas as pd

def extract_channel_id_from_url(url):
    service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # If it's a direct channel ID link
    if "youtube.com/channel/" in url:
        return url.split("channel/")[1].split("/")[0]

    # If it's a handle
    if "youtube.com/@" in url:
        handle = url.split("@")[1].split("/")[0]
        response = service.channels().list(
            part="id",
            forHandle=f"@{handle}"
        ).execute()
        return response["items"][0]["id"]

    raise ValueError("Unsupported or invalid YouTube URL format.")

def get_channel_metadata(channel_id):
    service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    response = service.channels().list(part="snippet,statistics", id=channel_id).execute()
    data = response["items"][0]
    return {
        "title": data["snippet"]["title"],
        "handle": data["snippet"].get("customUrl", ""),
        "id": channel_id,
        "country": data["snippet"].get("country", "Unknown"),
        "subs": int(data["statistics"]["subscriberCount"]),
        "video_count": int(data["statistics"]["videoCount"]),
        "profile_pic": data["snippet"]["thumbnails"]["high"]["url"]
    }


def get_recent_videos(channel_id, max_results=30):
    service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    uploads_playlist = service.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_id = uploads_playlist["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    next_page = None

    while len(videos) < max_results:
        response = service.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_id,
            maxResults=min(50, max_results - len(videos)),
            pageToken=next_page
        ).execute()

        video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]
        stats_response = service.videos().list(part="statistics", id=",".join(video_ids)).execute()

        for item, stats in zip(response["items"], stats_response["items"]):
           videos.append({
            "title": item["snippet"]["title"],
            "video_id": item["contentDetails"]["videoId"],
            "views": int(stats["statistics"].get("viewCount", 0)),
            "likes": int(stats["statistics"].get("likeCount", 0)),
            "comments": int(stats["statistics"].get("commentCount", 0)),
            "published": item["snippet"]["publishedAt"]
})


        next_page = response.get("nextPageToken")
        if not next_page:
            break

    return videos

def calculate_average_views(videos):
    return sum(v["views"] for v in videos) / len(videos) if videos else 0
