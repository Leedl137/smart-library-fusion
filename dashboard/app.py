#!/usr/bin/env python
# coding: utf-8
"""
智慧校园图书借阅信息管理系统 V2.0 —— Streamlit 数据大屏
融合：SmartLib 可视化风格 + 校园图书版业务指标
"""

import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8080"

st.set_page_config(
    page_title="智慧图书馆数据大屏",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; }
    .metric-card { background: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; }
    .metric-value { font-size: 2rem; font-weight: bold; color: #2c3e50; }
    .metric-label { font-size: 0.9rem; color: #7f8c8d; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📚 智慧校园图书借阅信息管理系统 V2.0 —— 数据大屏</div>', unsafe_allow_html=True)
st.caption("融合版：业务全生命周期 + 智慧空间管理 + AI 智能问答")


@st.cache_data(ttl=60)
def fetch_dashboard():
    try:
        resp = requests.get(f"{API_BASE}/api/v2/dashboard", timeout=30)
        return resp.json()
    except Exception as e:
        st.error(f"后端连接失败: {e}")
        return None


@st.cache_data(ttl=60)
def fetch_books(q="", limit=10):
    try:
        resp = requests.get(f"{API_BASE}/api/v2/books", params={"q": q, "limit": limit}, timeout=10)
        return resp.json()
    except Exception:
        return None


def render_dashboard():
    data = fetch_dashboard()
    if not data or data.get("code") != 200:
        st.warning("暂无数据或后端未启动")
        return

    metrics = data.get("metrics", [])
    charts = data.get("charts", [])

    # Helper to find chart by title
    def find_chart(title_substring):
        for c in charts:
            if title_substring in c.get("title", ""):
                return c
        return None

    # 顶部指标卡
    cols = st.columns(4)
    for i, m in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{m['value']:,}</div>
                <div class="metric-label">{m['label']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 图表区
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏫 各学院借阅量排行")
        c = find_chart("学院")
        if c and c.get("x"):
            import pandas as pd
            df = pd.DataFrame({"学院": c["x"], "总借阅次数": c["y"]})
            st.bar_chart(df.set_index("学院")["总借阅次数"])
        else:
            st.info("暂无数据")

    with col2:
        st.subheader("👥 读者类型分布")
        c = find_chart("读者类型")
        if c and c.get("data"):
            import pandas as pd
            df = pd.DataFrame(c["data"])
            import plotly.express as px
            fig = px.pie(df, names="name", values="value", title="读者类型占比")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")

    st.subheader("📈 月度借阅趋势")
    c = find_chart("月度")
    if c and c.get("x"):
        import pandas as pd
        df = pd.DataFrame({"月份": c["x"], "借阅次数": c["y"]})
        st.line_chart(df.set_index("月份")["借阅次数"])
    else:
        st.info("暂无数据")


def render_ai_chat():
    st.subheader("🤖 AI 智能问答（NL2SQL）")
    st.info("输入自然语言问题，AI 将自动转换为 SQL 查询数据库。例如：\"计算机学院的学生借阅了哪些书？\"")

    question = st.text_input("请输入您的问题", placeholder="例如：上个月借阅量最高的10本书是？")
    if st.button("🔍 查询") and question:
        with st.spinner("AI 正在思考..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/v2/ai/chat",
                    json={"question": question},
                    timeout=60,
                )
                result = resp.json()
                if result.get("code") == 200:
                    st.success("查询成功")
                    st.code(result.get("sql", ""), language="sql")
                    data = result.get("data", [])
                    if data:
                        import pandas as pd
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                        st.caption(f"共返回 {len(data)} 条记录")
                    else:
                        st.info("查询结果为空")
                else:
                    st.error(f"查询失败: {result.get('message', '未知错误')}")
            except Exception as e:
                st.error(f"请求异常: {e}")


def render_books():
    st.subheader("🔍 图书检索")
    q = st.text_input("搜索关键词（书名/作者/ISBN）", "")
    book_data = fetch_books(q, limit=20)
    if book_data and book_data.get("code") == 200:
        items = book_data.get("items", [])
        st.write(f"共找到 {book_data.get('total', 0)} 条结果")
        for item in items:
            with st.expander(f"📖 {item['title']}"):
                st.write(f"**ISBN**: {item['isbn']}")
                st.write(f"**作者**: {item['authors']}")
                st.write(f"**出版社**: {item['publisher']}")
                st.write(f"**馆藏位置**: {item['location']}")
                st.write(f"**可借数量**: {item['available_copies']} | **状态**: {item['status']}")
    else:
        st.info("请输入关键词搜索")


# ==================== 页面路由 ====================

page = st.sidebar.radio("导航", ["📊 数据大屏", "🤖 AI 问答", "📚 图书检索"])

if page == "📊 数据大屏":
    render_dashboard()
elif page == "🤖 AI 问答":
    render_ai_chat()
elif page == "📚 图书检索":
    render_books()

st.sidebar.divider()
st.sidebar.caption("智慧校园图书借阅信息管理系统 V2.0")
st.sidebar.caption("© 2026 教育信息化团队")
