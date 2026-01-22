
import streamlit as st
import sys
import os
from pathlib import Path

# Add current directory to path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils

# --- Config ---
st.set_page_config(
    page_title="Truth Social Scraper",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS / Antigravity ---
# We inject some CSS. If "antigravity" mode is on, we rotate the app slightly.
if "antigravity_mode" not in st.session_state:
    st.session_state.antigravity_mode = False

def toggle_antigravity():
    st.session_state.antigravity_mode = not st.session_state.antigravity_mode

if st.session_state.antigravity_mode:
    st.markdown(
        """
        <style>
        .stApp {
            transform: rotate(2deg);
            transition: transform 1s ease-in-out;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        .stApp {
            transform: rotate(0deg);
            transition: transform 1s ease-in-out;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Sidebar ---
st.sidebar.title("Configuration")

handle = st.sidebar.text_input("Handle", value="realDonaldTrump")
days_val = st.sidebar.number_input("Days", min_value=1, value=2)
max_comments_val = st.sidebar.number_input("Max Comments", min_value=1, value=50)
out_file = st.sidebar.text_input("Output File (Optional)", value="", placeholder="e.g. results.json")

st.sidebar.markdown("---")
ts_user = st.sidebar.text_input("Truth Social Username", value=os.getenv("TRUTHSOCIAL_USERNAME", "your_username"))
ts_pass = st.sidebar.text_input("Truth Social Password", value=os.getenv("TRUTHSOCIAL_PASSWORD", "your_password"), type="password")



# --- Main Layer ---
st.title("🕸️ Truth Social Scraping Engine")

# Session State for Results
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = None
if "scrape_log" not in st.session_state:
    st.session_state.scrape_log = ""
if "last_output_file" not in st.session_state:
    st.session_state.last_output_file = None

# Action Button
if st.button("Scrape / Run Export", type="primary"):
    
    # Check if a file with same params exists (Mock caching logic)
    # Since we don't have a database of runs, we just check if expected output string exists
    # reusing the result is a bit tricky without a deterministic filename. 
    # We'll stick to running it.
    
    with st.spinner(f"Scraping @{handle} for {days_val} days..."):
        ret, stdout, stderr, dur, out_path = utils.run_script(handle, days_val, max_comments_val, out_file, ts_user, ts_pass)

        st.session_state.scrape_log = f"Exit Code: {ret}\nDuration: {dur:.2f}s\n\n[CMD OUT FILE]\n{out_path}\n\n[STDOUT]\n{stdout}\n\n[STDERR]\n{stderr}"

        st.session_state.last_output_file = out_path

        if ret == 0:
            if out_path and os.path.exists(out_path):
                data = utils.load_data(out_path)
                st.session_state.scrape_results = data
                if not data:
                    st.error("JSON file exists but could not be parsed (invalid JSON).")
            else:
                st.error("Script finished, but output JSON file was not created.")
                st.session_state.scrape_results = None
        else:
            st.error("Script failed. Check logs.")
            st.session_state.scrape_results = None

# Logs Exapander
with st.expander("Execution Logs"):
    if st.session_state.scrape_log:
        st.code(st.session_state.scrape_log)
    else:
        st.info("No logs yet.")

# --- Results Display ---
data = st.session_state.scrape_results

if data:
    st.markdown("---")
    
    # 1. KPIs
    cols = st.columns(3)
    cols[0].metric("Posts Count", data.get("posts_count", 0))
    cols[1].metric("Cutoff (UTC)", data.get("cutoff_utc", "N/A"))
    cols[2].metric("Generated (UTC)", data.get("generated_at_utc", "N/A"))
    
    # Download Button
    if st.session_state.last_output_file:
        try:
            with open(st.session_state.last_output_file, "r", encoding="utf-8") as f:
                json_bytes = f.read().encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_bytes,
                file_name=os.path.basename(st.session_state.last_output_file),
                mime="application/json"
            )
        except Exception:
            pass

    # 2. Filters
    st.subheader("Posts Analysis")
    col_search, col_chk = st.columns([3, 1])
    search_txt = col_search.text_input("Filter posts/comments (text search)")
    only_comments = col_chk.checkbox("Show only posts with comments")
    
    posts = data.get("posts", [])
    filtered_posts = utils.filter_posts(posts, search_txt, only_comments)
    
    st.write(f"Showing {len(filtered_posts)} / {len(posts)} posts")
    
    # 3. Post List
    for post in filtered_posts:
        # Title for expander: Date - Snippet
        created_at = post.get("created_at", "Unknown Date")
        content = post.get("content_text", "") or ""
        snippet = (content[:80] + "...") if len(content) > 80 else content
        
        with st.expander(f"{created_at} | {snippet}"):
            # Post Details
            st.markdown(f"**Content:** {content}")
            st.markdown(f"[View on Truth Social]({post.get('url', '#')})")
            
            # Metrics
            m_cols = st.columns(4)
            m_cols[0].caption(f"💬 Replies: {post.get('replies_count', 0)}")
            m_cols[1].caption(f"🔁 Reblogs: {post.get('reblogs_count', 0)}")
            m_cols[2].caption(f"❤️ Favourites: {post.get('favourites_count', 0)}")
            
            # Comments Section
            comments = post.get("comments", [])
            count_fetched = post.get("comments_count_fetched", 0)
            
            st.divider()
            st.write(f"**Comments (fetched {len(comments)} / {count_fetched})**")
            
            if not comments:
                st.info("No comments fetched.")
            else:
                for c in comments:
                    c_auth = c.get("author_display_name", c.get("author_username", "Unknown"))
                    c_date = c.get("created_at", "")
                    c_text = c.get("content_text", "")
                    c_url = c.get("url", "#")
                    
                    st.markdown(
                        f"""
                        <div style="background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <small><b>{c_auth}</b> • {c_date}</small><br>
                            {c_text}<br>
                            <a href="{c_url}" style="font-size: 0.8em;">Link</a>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

elif st.session_state.scrape_log and not data:
    st.warning("No data loaded. Await a successful run.")
