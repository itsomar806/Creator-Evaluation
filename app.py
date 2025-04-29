# 🧐 YouTube Creator Audit Tool (Fully Updated)
import streamlit as st
import pandas as pd
import altair as alt
import json
import os
from urllib.parse import urlparse
from serpapi import GoogleSearch
import googleapiclient.discovery
import openai

# MUST BE FIRST: Page config
st.set_page_config(page_title="YouTube Creator Evaluation", layout="wide")

# Load secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
SERPAPI_API_KEY = st.secrets["SERPAPI_API_KEY"]

# --- UTILITIES ---
def extract_channel_id_from_url(url):
    if '@' in url:
        return url.strip().split('/')[-1].replace('@', '')
    parsed = urlparse(url)
    if 'channel' in url:
        return url.split('/channel/')[-1].split('/')[0]
    if 'user' in url or 'c' in url:
        return url.split('/')[-1]
    return url

def get_channel_metadata(identifier):
    yt = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    if not identifier.startswith("UC"):
        search = yt.search().list(part="snippet", q=identifier, type="channel", maxResults=1).execute()
        items = search.get("items", [])
        if not items:
            raise ValueError("Channel not found via search.")
        identifier = items[0]["snippet"]["channelId"]
    request = yt.channels().list(part="snippet,statistics", id=identifier)
    channel = request.execute()["items"][0]
    return {
        "title": channel["snippet"]["title"],
        "handle": identifier,
        "id": channel["id"],
        "subs": int(channel["statistics"].get("subscriberCount", 0)),
        "country": channel["snippet"].get("country", "Unknown")
    }

def get_recent_videos(channel_id, max_results=30):
    yt = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    search = yt.search().list(part="id", channelId=channel_id, order="date", maxResults=max_results).execute()
    video_ids = [item["id"]["videoId"] for item in search["items"] if item["id"]["kind"] == "youtube#video"]
    vids = yt.videos().list(part="snippet,statistics", id=",".join(video_ids)).execute()["items"]
    return [{
        "video_id": v["id"],
        "title": v["snippet"]["title"],
        "published": v["snippet"]["publishedAt"],
        "views": int(v["statistics"].get("viewCount", 0)),
        "likes": int(v["statistics"].get("likeCount", 0)),
        "comments": int(v["statistics"].get("commentCount", 0))
    } for v in vids]

def calculate_avg_views(videos):
    return round(sum(v["views"] for v in videos) / len(videos)) if videos else 0

def get_topic_clusters(videos):
    keywords = {
        "Marketing": ["marketing", "brand", "ads", "social media", "viral"],
        "Sales": ["sales", "pitch", "close"],
        "Entrepreneurship / Business": ["business", "startup", "entrepreneur"],
        "AI": ["ai", "chatgpt", "machine learning"],
        "Skill Development": ["skills", "learning", "habits", "productivity"],
        "Web Dev": ["html", "css", "javascript", "developer"],
        "Customer Success": ["customer", "support"],
        "Tech": ["tech", "software", "tools"]
    }
    clusters = {k: 0 for k in keywords}
    for v in videos:
        title = v["title"].lower()
        for category, words in keywords.items():
            if any(w in title for w in words):
                clusters[category] += 1
    return ", ".join([k for k, v in sorted(clusters.items(), key=lambda x: -x[1]) if v > 0]) or "N/A"

def get_brand_safety(query):
    results = GoogleSearch({"q": query, "api_key": SERPAPI_API_KEY}).get_dict().get("organic_results", [])
    context = "\n".join([f"- {r.get('title')}\n{r.get('snippet')}\n{r.get('link')}" for r in results])

    prompt = f"""
You are a brand safety analyst. Based on the findings below, return a detailed JSON assessment:

{{
  "brand_risk_score": integer from 1 to 10 (1 = low risk, 10 = high risk),
  "score_summary": "Concise summary (3–4 sentences) explaining the score.",
  "risk_flags": ["Any notable risks or sensitive topics"],
  "heart_values": {{
    "Humble": {{"value": "Yes" or "No", "reason": "brief explanation"}},
    "Empathetic": {{"value": "Yes" or "No", "reason": "brief explanation"}},
    "Adaptable": {{"value": "Yes" or "No", "reason": "brief explanation"}},
    "Remarkable": {{"value": "Yes" or "No", "reason": "brief explanation"}},
    "Transparent": {{"value": "Yes" or "No", "reason": "brief explanation"}}
  }},
  "summary": "Overall summary",
  "evidence": ["List of any quotes or examples that informed the score"]
}}

Findings:
{context}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a brand safety evaluator. Always respond with strict valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format="json"
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ValueError("OpenAI returned empty content.")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("OpenAI returned invalid JSON. Content: " + repr(content))
    except Exception as e:
            raise ValueError(f"OpenAI API call failed: {e}")
    except json.JSONDecodeError:
            raise ValueError("OpenAI returned invalid JSON. Content: " + repr(content))
    except Exception as e:
        raise ValueError(f"OpenAI API call failed: {e}")

# --- APP LOGIC ---
st.title("📊 YouTube Creator Evaluation")

url = st.text_input("🔗 Paste YouTube channel URL or handle:")
if st.button("Run Audit") and url:
    try:
        channel_id = extract_channel_id_from_url(url)
        meta = get_channel_metadata(channel_id)
        videos = get_recent_videos(meta["id"])
        avg_views = calculate_avg_views(videos)
        clusters = get_topic_clusters(videos)

        st.session_state["meta"] = meta
        st.session_state["videos"] = videos
        st.session_state["avg_views"] = avg_views
        st.session_state["clusters"] = clusters
        st.session_state["audit_complete"] = True

        st.divider()
        st.subheader("🎯 Creator Overview")
        st.markdown(f"**🧠 Topic Clusters:** {clusters}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**👤 Channel Name:** {meta['title']}")
            st.markdown(f"**🔗 Handle:** `{meta['handle']}`")
            st.markdown(f"**🆔 Channel ID:** `{meta['id']}`")
        with col2:
            st.markdown(f"**🌍 Country:** {meta['country']}")
            st.markdown(f"**👥 Subscribers:** {meta['subs']:,}")
            st.markdown(f"[🔗 View Channel](https://www.youtube.com/channel/{meta['id']})")
    except Exception as e:
        st.error(f"Something went wrong: {e}")

if st.session_state.get("audit_complete"):
    st.divider()
    st.subheader("💰 Sponsorship Calculator")
    cpvs = {"Conservative (0.3%)": 0.003, "Median (0.35%)": 0.0035, "Best Case (0.5%)": 0.005}
    label = st.selectbox("🌟 Choose CPV Scenario", options=list(cpvs.keys()), key="cpv_option")
    target_cpv = cpvs[label]
    avg_views = st.session_state["avg_views"]
    price = round(avg_views * target_cpv)

    st.markdown(f"""
    <div style='background-color:#fdf6ec; padding:1.5rem 2rem; border-radius:10px; border:1px solid #f4d6a0; text-align:center; width:100%; max-width: 100%; margin: auto;'>
        <div style='font-size: 1.2rem;'>📺 <strong>Average Views</strong></div>
        <div style='font-size: 2.5rem; font-weight: bold; color:#FFA726'>{avg_views:,}</div>
        <div style='margin-top: 1rem; font-size: 1rem;'>🎯 <strong>Target CPV:</strong> ${target_cpv:.4f}</div>
        <div style='font-size: 1rem;'>💸 <strong>Recommended Price per Video:</strong> ${price:,}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📈 Growth Over Time (Views)")
    df = pd.DataFrame(st.session_state["videos"])
    df["published"] = pd.to_datetime(df["published"])
    df = df.sort_values("published")
    df["label"] = df["published"].dt.strftime("%b %d")
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("label:N", sort=None),
        y="views:Q",
        tooltip=["title", "views"]
    ).properties(width=1000, height=400)
    st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("🔥 Top 10 Performing Videos")
    top = df.sort_values("views", ascending=False).head(10)
    top["Video URL"] = top["video_id"].apply(lambda x: f"https://www.youtube.com/watch?v={x}")
    table = top[["title", "views", "likes", "comments", "Video URL"]]
    table.columns = ["🎬 Title", "👁️ Views", "👍 Likes", "💬 Comments", "🔗 Link"]
    st.dataframe(table, use_container_width=True)

    st.divider()
    st.subheader("🛡️ Brand Safety & HEART Assessment")
    try:
        query = f"{st.session_state['meta']['title']} YouTube creator news OR controversy OR reviews"
        st.markdown(f"🔍 Using enhanced query: `{query}`")
        risk = get_brand_safety(query)
        score_color = "#4CAF50" if risk["brand_risk_score"] <= 3 else "#FFC107" if risk["brand_risk_score"] <= 6 else "#F44336"

        st.markdown(f"""
        <div style='border:1px solid #ddd; padding:1.5rem; border-radius:10px; background-color:#f9f9f9'>
            <div style='font-size:1.1rem; margin-bottom:1rem;'>
                <strong>🧪 Brand Risk Score:</strong>
                <span style='padding:4px 12px; background-color:{score_color}; color:white; border-radius:20px; font-weight:bold;'>
                    {risk["brand_risk_score"]}
                </span>
            </div>
            <div style='margin-bottom:1rem;'>
                <strong>📝 Score Explanation:</strong><br>
                {risk['score_summary']}
            </div>
            <div style='margin-bottom:1rem;'>
                <strong>❤️ HEART Values with Reasoning:</strong>
                <ul>
                    <li><strong>Humble</strong>: {risk['heart_values']['Humble']['value']} – {risk['heart_values']['Humble']['reason']}</li>
                    <li><strong>Empathetic</strong>: {risk['heart_values']['Empathetic']['value']} – {risk['heart_values']['Empathetic']['reason']}</li>
                    <li><strong>Adaptable</strong>: {risk['heart_values']['Adaptable']['value']} – {risk['heart_values']['Adaptable']['reason']}</li>
                    <li><strong>Remarkable</strong>: {risk['heart_values']['Remarkable']['value']} – {risk['heart_values']['Remarkable']['reason']}</li>
                    <li><strong>Transparent</strong>: {risk['heart_values']['Transparent']['value']} – {risk['heart_values']['Transparent']['reason']}</li>
                </ul>
            </div>
            <div style='margin-bottom:1rem;'>
                <strong>🚩 Risk Flags:</strong><br>
                {', '.join(risk['risk_flags']) or 'None reported.'}
            </div>
            <div><strong>📂 Evidence:</strong><br>
                <ul>{''.join(f'<li>{e}</li>' for e in risk['evidence'])}</ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.warning("⚠️ Unable to parse AI response.")
        st.text(str(e))
