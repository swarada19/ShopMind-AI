"""
frontend/app.py

ShopMind AI — Streamlit Frontend

A clean, functional UI that demonstrates the full ShopMind AI pipeline.
Talks to the FastAPI backend running on localhost:8000.

Pages / tabs:
  🔍 Search  — Enter a query, see ranked product recommendations
  👁️ Watchlist — Manage price-drop watches
  📜 History  — Past searches
  ⚙️ Settings  — User preferences
"""

import os

import httpx
import streamlit as st

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="ShopMind AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Read from environment so Docker Compose can inject the container hostname.
# Falls back to localhost for local dev outside Docker.
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .product-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .rank-badge {
        background: #7c3aed;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 13px;
        font-weight: bold;
    }
    .score-bar-container {
        background: #313244;
        border-radius: 4px;
        height: 6px;
        margin: 4px 0;
    }
    .score-bar {
        background: linear-gradient(90deg, #7c3aed, #06b6d4);
        border-radius: 4px;
        height: 6px;
    }
    .deal-tag {
        background: #16a34a;
        color: white;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def api_get(path: str, **kwargs) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.json().get('detail', str(e))}")
        return None
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        return None


def api_post(path: str, data: dict) -> dict | None:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=data, timeout=60)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", str(e))
        st.error(f"API error: {detail}")
        return None
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        return None


def api_put(path: str, data: dict) -> dict | None:
    try:
        r = httpx.put(f"{API_BASE}{path}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", str(e))
        st.error(f"API error: {detail}")
        return None
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        return None


def api_delete(path: str) -> bool:
    """Returns True on success (204 No Content), False otherwise."""
    try:
        r = httpx.delete(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        st.error(f"Delete failed: {e.response.json().get('detail', str(e))}")
        return False
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        return False


def render_score_bar(label: str, score: float, color: str = "#7c3aed"):
    pct = int(score * 100)
    st.markdown(f"""
    <div style="margin-bottom:6px">
        <span style="font-size:12px;color:#a0aec0">{label}</span>
        <span style="float:right;font-size:12px;color:#e2e8f0">{pct}%</span>
        <div class="score-bar-container">
            <div class="score-bar" style="width:{pct}%;background:{color}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_product_card(product: dict, rank: int):
    title = product.get("title", "Unknown")
    price = product.get("price")
    original_price = product.get("original_price")
    rating = product.get("rating")
    review_count = product.get("review_count", 0)
    discount_pct = product.get("discount_pct")
    explanation = product.get("explanation", "")
    final_score = product.get("final_score", 0)
    deal_score = product.get("deal_score", 0)
    review_score = product.get("review_score", 0)
    url = product.get("url", "#")
    features = product.get("features", [])

    with st.container():
        cols = st.columns([0.5, 3.5, 2, 1.5])

        with cols[0]:
            st.markdown(f'<span class="rank-badge">#{rank}</span>', unsafe_allow_html=True)

        with cols[1]:
            st.markdown(f"**{title}**")
            if explanation:
                st.caption(f"💡 {explanation}")
            if features:
                st.caption(" · ".join(features[:3]))

        with cols[2]:
            if price:
                if discount_pct and discount_pct > 5:
                    st.markdown(
                        f"**${price:.2f}** "
                        f'<span class="deal-tag">-{discount_pct:.0f}%</span>',
                        unsafe_allow_html=True,
                    )
                    if original_price:
                        st.caption(f"~~${original_price:.2f}~~")
                else:
                    st.markdown(f"**${price:.2f}**")

            if rating:
                stars = "⭐" * int(round(rating))
                count_str = f"{review_count:,}" if review_count else "N/A"
                st.caption(f"{stars} {rating} ({count_str} reviews)")

        with cols[3]:
            render_score_bar("Deal", deal_score, "#16a34a")
            render_score_bar("Review", review_score, "#0891b2")
            render_score_bar("Score", final_score, "#7c3aed")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if url and url != "#":
                st.link_button("View Product →", url, use_container_width=True)
        with btn_col2:
            if st.button("+ Watch", key=f"watch_{rank}_{title[:20]}", use_container_width=True):
                st.session_state["watch_product"] = product

        st.divider()


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛍️ ShopMind AI")
    st.caption("AI-Powered Product Recommendations")
    st.divider()

    # User management
    st.markdown("### 👤 Your Profile")

    # Check for stored user
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = ""
        st.session_state["user_name"] = ""

    if st.session_state["user_id"]:
        st.success(f"Logged in as **{st.session_state['user_name']}**")
        if st.button("Log out", use_container_width=True):
            st.session_state["user_id"] = ""
            st.session_state["user_name"] = ""
            st.rerun()
    else:
        with st.expander("Create / Login", expanded=True):
            with st.form("user_form"):
                name = st.text_input("Name", placeholder="Your name")
                email = st.text_input("Email", placeholder="your@email.com")
                phone = st.text_input("Phone (for WhatsApp alerts)", placeholder="+1234567890")
                submitted = st.form_submit_button("Create Account", use_container_width=True)

                if submitted and name and email:
                    result = api_post("/users", {"name": name, "email": email, "phone": phone or None})
                    if result:
                        st.session_state["user_id"] = result["id"]
                        st.session_state["user_name"] = result["name"]
                        st.success(f"Welcome, {name}!")
                        st.rerun()

    st.divider()

    # Backend status
    st.markdown("### 🔌 Backend Status")
    health = api_get("/health")
    if health:
        mock_mode = health.get("mock_mode", True)
        st.success("✅ Connected")
        if mock_mode:
            st.info("🎭 Mock mode — using sample data")
        else:
            st.success("🌐 Live mode — real API calls")
    else:
        st.error("❌ Backend offline\n\nRun: `make dev`")


# ── Main content ─────────────────────────────────────────────────────────────

st.markdown("# 🛍️ ShopMind AI")
st.markdown("*Find the best products at the best prices, powered by AI*")
st.divider()

tab_search, tab_watchlist, tab_history, tab_settings = st.tabs([
    "🔍 Search", "👁️ Watchlist", "📜 History", "⚙️ Settings"
])


# ── Search Tab ────────────────────────────────────────────────────────────────
with tab_search:
    col_input, col_btn = st.columns([4, 1])

    with col_input:
        query = st.text_input(
            "What are you looking for?",
            placeholder="e.g. best wireless headphones under $150",
            label_visibility="collapsed",
        )

    with col_btn:
        search_clicked = st.button("Search 🔍", type="primary", use_container_width=True)

    # Quick search suggestions
    st.caption("Try: &nbsp;&nbsp;"
               "**wireless headphones under $100** &nbsp;·&nbsp; "
               "**MacBook laptop** &nbsp;·&nbsp; "
               "**gaming laptop under $1200** &nbsp;·&nbsp; "
               "**iPhone 16 Pro**")

    if search_clicked and query:
        if not st.session_state.get("user_id"):
            st.warning("⚠️ Create an account in the sidebar to search.")
        else:
            with st.spinner("🤖 Running multi-agent pipeline..."):
                result = api_post("/search", {
                    "user_id": st.session_state["user_id"],
                    "query": query,
                })

            if result:
                recs = result.get("recommendations", [])
                intent = result.get("intent", "unknown")
                cache_hit = result.get("cache_hit", False)
                product_query = result.get("product_query", query)

                # Status bar
                info_cols = st.columns(4)
                info_cols[0].metric("Results", len(recs))
                info_cols[1].metric("Intent", intent.title())
                info_cols[2].metric("Query", product_query[:25])
                info_cols[3].metric("Source", "Cache ⚡" if cache_hit else "Live 🌐")

                if result.get("error"):
                    st.warning(f"⚠️ Partial results: {result['error']}")

                st.divider()

                if recs:
                    st.markdown(f"### Top {len(recs)} Recommendations")
                    for i, product in enumerate(recs, start=1):
                        render_product_card(product, i)
                else:
                    st.info("No products found. Try a different query.")

    # Handle "Watch" button clicks from product cards
    if "watch_product" in st.session_state:
        product = st.session_state["watch_product"]
        st.divider()
        st.markdown("### 👁️ Add to Watchlist")
        with st.form("watch_form"):
            w_title = st.text_input("Product", value=product.get("title", ""))
            w_url = st.text_input("URL", value=product.get("url", "") or "")
            w_price = st.number_input(
                "Alert me when price drops below ($)",
                value=float(product.get("price") or 0) * 0.9,
                min_value=0.01,
            )
            w_submit = st.form_submit_button("Add to Watchlist ✅")
            if w_submit:
                result = api_post("/search/watch", {
                    "user_id": st.session_state["user_id"],
                    "query": w_title,
                    "product_title": w_title,
                    "product_url": w_url or None,
                    "target_price": w_price,
                })
                if result:
                    st.success(f"✅ {result['message']}")
                    del st.session_state["watch_product"]
                    st.rerun()


# ── Watchlist Tab ──────────────────────────────────────────────────────────────
with tab_watchlist:
    st.markdown("### 👁️ Your Price Watches")

    if not st.session_state.get("user_id"):
        st.info("Create an account to manage your watchlist.")
    else:
        watchlist_data = api_get(f"/watchlist/{st.session_state['user_id']}")

        if watchlist_data is not None:
            if not watchlist_data:
                st.info("Your watchlist is empty. Search for products and click '+ Watch' to add them.")
            else:
                for item in watchlist_data:
                    with st.container():
                        cols = st.columns([3, 1.5, 1.5, 1])
                        cols[0].markdown(f"**{item['product_title']}**")
                        cols[1].metric(
                            "Current",
                            f"${item.get('last_checked_price') or '—'}",
                        )
                        cols[2].metric(
                            "Target",
                            f"${item.get('target_price') or '—'}",
                        )
                        with cols[3]:
                            if st.button("❌", key=f"del_{item['id']}"):
                                if api_delete(f"/watchlist/{st.session_state['user_id']}/{item['id']}"):
                                    st.success("Removed")
                                    st.rerun()
                        st.caption(f"Added {item.get('created_at', '')[:10]} · Alerts sent: {item.get('alert_sent_count', 0)}")
                        st.divider()


# ── History Tab ───────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Search History")

    if not st.session_state.get("user_id"):
        st.info("Create an account to see your search history.")
    else:
        history = api_get(f"/users/{st.session_state['user_id']}/history")
        if history:
            for h in history:
                with st.container():
                    cols = st.columns([3, 1, 1, 1.5])
                    cols[0].markdown(f"**{h['query']}**")
                    cols[1].caption(f"Intent: {h.get('intent', '—')}")
                    cols[2].caption(f"Results: {h.get('results_count', 0)}")
                    cols[3].caption(h.get('created_at', '')[:16])
        elif history is not None:
            st.info("No search history yet. Try a search first!")


# ── Settings Tab ──────────────────────────────────────────────────────────────
with tab_settings:
    st.markdown("### ⚙️ Your Preferences")
    st.caption("These are loaded by the Preference Agent on every search to personalise your results.")

    if not st.session_state.get("user_id"):
        st.info("Create an account to set preferences.")
    else:
        # Load existing preferences
        existing = api_get(f"/users/{st.session_state['user_id']}/preferences")

        with st.form("prefs_form"):
            budget = st.number_input(
                "Default max budget ($)",
                value=float(existing.get("max_budget") or 0) if existing else 0.0,
                min_value=0.0,
                help="Used when no budget is mentioned in your query",
            )
            brands_input = st.text_input(
                "Preferred brands (comma-separated)",
                value=", ".join(existing.get("preferred_brands", [])) if existing else "",
                placeholder="Apple, Sony, Samsung",
            )
            categories_input = st.text_input(
                "Preferred categories (comma-separated)",
                value=", ".join(existing.get("preferred_categories", [])) if existing else "",
                placeholder="laptops, headphones",
            )
            notes = st.text_area(
                "Notes for the AI",
                value=existing.get("notes", "") if existing else "",
                placeholder="e.g. I prefer lightweight products, avoid gaming brands",
            )

            if st.form_submit_button("Save Preferences", type="primary"):
                brands = [b.strip() for b in brands_input.split(",") if b.strip()]
                cats = [c.strip() for c in categories_input.split(",") if c.strip()]

                saved = api_put(
                    f"/users/{st.session_state['user_id']}/preferences",
                    {
                        "max_budget": budget if budget > 0 else None,
                        "currency": "USD",
                        "preferred_brands": brands,
                        "preferred_categories": cats,
                        "notes": notes or None,
                    },
                )
                if saved:
                    st.success("✅ Preferences saved! They'll be applied on your next search.")
