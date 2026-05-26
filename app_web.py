# ==========================================
# 导入相关库模块区域
# 说明：引入 Web 核心库、数据处理库以及数学计算库
# ==========================================
import streamlit as st
import pandas as pd
import os
import math

# ------------------------------------------
# 自定义区域：基础配置与参数
# 说明：这里可以根据你的实际需求随时修改文件名或导航页码步长
# ------------------------------------------
FILE_PATH = '完整题库_精排版.xlsx'  # Excel 题库文件路径
NAV_PER_PAGE = 50  # 侧边栏导航面板一次展示的序号按钮数量

# 设置网页的浏览器标签页标题和布局模式（wide 为宽屏模式，两侧利用率更高）
st.set_page_config(page_title="专属背题神器 Web版", layout="wide")


# ==========================================
# 数据加载模块区域 (利用缓存提速)
# 说明：确保 Excel 数据只在首次加载时读取，翻页切换不重复读盘
# ==========================================
@st.cache_data
def load_exam_data(path):
    """读取本地的 Excel 题库文件"""
    if os.path.exists(path):
        return pd.read_excel(path).fillna("")
    return None


# 载入原始完整数据集
df = load_exam_data(FILE_PATH)

# 容错处理：如果文件缺失则在页面弹出警告并拦截中断
if df is None:
    st.error(f"❌ 找不到题库文件：{FILE_PATH}。请检查文件是否存在。")
    st.stop()

# ==========================================
# 侧边栏：题型筛选与记忆动态联动控制区
# 说明：提取不重复题型，提供过滤下拉框，并保障切换时进度重置
# ==========================================
# 1. 动态获取所有不重复的题型组合
all_types = ["全部题型"] + list(df['题型'].unique())

# 2. 将题型选择框注入侧边栏顶部
selected_type = st.sidebar.selectbox("🎯 选择刷题题型", all_types)

# 3. 初始化并监控题型切换状态（核心防崩溃机制）
if 'last_selected_type' not in st.session_state:
    st.session_state.last_selected_type = selected_type

# 如果检测到用户切换了下拉框选项，将做题索引和答题卡页码强制归零
if st.session_state.last_selected_type != selected_type:
    st.session_state.current_index = 0
    st.session_state.nav_page = 0
    st.session_state.last_selected_type = selected_type

# 4. 执行内存切片筛选，构建当前激活的子题库 filtered_df
if selected_type == "全部题型":
    filtered_df = df
else:
    filtered_df = df[df['题型'] == selected_type].reset_index(drop=True)

# ==========================================
# 会话状态 (Session State) 后续参数初始化区域
# 说明：用于保持和控制当前题号索引与导航区间的联动
# ==========================================
total_questions = len(filtered_df)
total_nav_pages = math.ceil(total_questions / NAV_PER_PAGE)

# 记录当前正在做第几题 (索引从 0 开始)
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# 记录侧边栏导航面板当前处于第几个 50 题区间 (索引从 0 开始)
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = 0

# ==========================================
# 左侧边栏：题号导航网格区域 (答题卡面板)
# 说明：生成类似答题卡的 50 个方块按钮，支持点击瞬间跳转
# ==========================================
st.sidebar.write("---")
st.sidebar.header("🗂️ 题号导航 (点击跳转)")

# 防止子题库题目太少导致计算出 0 页，做一个安全兜底
if total_nav_pages > 0:
    # 生成类似 "第 1 - 50 题", "第 51 - 100 题" 的区间文本选项
    nav_options = [f"第 {i * NAV_PER_PAGE + 1} - {min((i + 1) * NAV_PER_PAGE, total_questions)} 题" for i in
                   range(total_nav_pages)]

    # 防止因题型切换导致页码超出安全界限
    if st.session_state.nav_page >= len(nav_options):
        st.session_state.nav_page = 0

    # 下拉选择框，index 属性强行绑定到当前控制状态
    selected_nav = st.sidebar.selectbox("选择题号区间", nav_options, index=st.session_state.nav_page)
    st.session_state.nav_page = nav_options.index(selected_nav)
else:
    st.sidebar.info("当前题型下无可选区间")

st.sidebar.write("---")

# 计算当前选定的 50 题区间的起止绝对行号
start_q = st.session_state.nav_page * NAV_PER_PAGE
end_q = min(start_q + NAV_PER_PAGE, total_questions)

cols_per_row = 5  # 设定侧边栏答题卡每一行并排摆放 5 个按钮
for i in range(start_q, end_q, cols_per_row):
    cols = st.sidebar.columns(cols_per_row)
    for j in range(cols_per_row):
        if i + j < end_q:
            q_idx = i + j
            # 判断该序号按钮是不是当前正在浏览的题目，突出显示
            is_current = (q_idx == st.session_state.current_index)
            btn_type = "primary" if is_current else "secondary"

            # 渲染数字方块按钮，点击后变更全局题号并刷新主界面
            if cols[j].button(str(q_idx + 1), key=f"btn_{q_idx}", type=btn_type, use_container_width=True):
                st.session_state.current_index = q_idx
                st.rerun()

# ==========================================
# 主界面：单题展示与高亮渲染区域
# 说明：核心业务逻辑，去除了分值，完美兼容常规题与判断题的高亮映射
# ==========================================
st.title("竞赛背题神器")

if total_questions > 0:
    # 提取当前激活的这道题的数据行
    row = filtered_df.iloc[st.session_state.current_index]

    # 顶部信息栏（已彻底剔除分值字样）
    st.info(
        f"📋 当前题型：【{selected_type}】 | 进度: {st.session_state.current_index + 1} / {total_questions}  |  本题实际类型: {row.get('题型', '未知')}")

    # 渲染核心题干文本
    st.markdown(f"#### **{st.session_state.current_index + 1}.** {row.get('题目内容', '')}")
    st.write("")

    # 获取当前题目的正确答案文本以及题型名称
    correct_answers_str = str(row.get('正确答案', ''))
    q_type = str(row.get('题型', ''))

    # --- 拦截判断题特殊处理逻辑 ---
    if "判断" in q_type:
        # 1. 强制创造出标准判断题的两个文字框
        options_dict = {'A': '正确', 'B': '错误'}

        # 2. 将后台抓取的数字化代号转换为对应的字母索引
        if correct_answers_str == '1':
            mapped_correct = 'A'
        elif correct_answers_str == '2' or correct_answers_str == '0':
            mapped_correct = 'B'
        else:
            mapped_correct = correct_answers_str  # 健壮性兜底

        # 3. 遍历并利用带有 CSS 属性的 HTML 进行高亮渲染
        for opt, opt_val in options_dict.items():
            if opt in mapped_correct:
                highlight_html = f"""
                <div style="background-color: #e8f5e9; color: #1b5e20; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-weight: bold; border-left: 5px solid #4caf50;">
                    {opt}. {opt_val} ✔️
                </div>
                """
                st.markdown(highlight_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div style='margin-bottom: 6px; padding-left: 10px;'>{opt}. {opt_val}</div>",
                    unsafe_allow_html=True)

    # --- 常规选择题处理逻辑 ---
    else:
        for opt in ['A', 'B', 'C', 'D', 'E', 'F']:
            opt_val = row.get(f'选项{opt}', '')
            if opt_val:
                # 如果选项包含在答案串中，渲染为高亮绿色边框框
                if opt in correct_answers_str:
                    highlight_html = f"""
                    <div style="background-color: #e8f5e9; color: #1b5e20; padding: 6px; border-radius: 5px; margin-bottom: 5px; font-weight: bold; border-left: 4px solid #4caf50;">
                        {opt}. {opt_val} ✔️
                    </div>
                    """
                    st.markdown(highlight_html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div style='margin-bottom: 8px; padding-left: 15px; font-size: 1.1em;'>{opt}. {opt_val}</div>",
                        unsafe_allow_html=True)

    st.write("")

    # 渲染解析文本模块（无解析则不展示）
    remark = row.get('解析', '')
    if remark and remark != "无":
        st.caption(f"**💡 解析说明：** {remark}")

else:
    st.warning("⚠️ 该题型下没有找到任何题目数据，请尝试切换其他题型。")

st.write("---")

# ==========================================
# 底部控制：上一题 / 下一题 按钮交互区域
# 说明：控制翻页边界，并智能联动修改侧边栏答题卡的页码区间
# ==========================================
col1, col2 = st.columns(2)

with col1:
    if st.button("⬆️ 上一题 ⬆️", use_container_width=True):
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            # 智能收缩联动：退回上一个 50 题区间时，侧边栏下拉框跟着同步翻页
            st.session_state.nav_page = st.session_state.current_index // NAV_PER_PAGE
            st.rerun()
        else:
            st.toast("⚠️ 这已经是当前题型的第一题啦！")

with col2:
    if st.button("⬇️ 下一题 ⬇️", use_container_width=True):
        if st.session_state.current_index < total_questions - 1:
            st.session_state.current_index += 1
            # 智能递增联动：前进到下一个 50 题区间时，侧边栏下拉框跟着同步翻页
            st.session_state.nav_page = st.session_state.current_index // NAV_PER_PAGE
            st.rerun()
        else:
            st.toast("🎉 恭喜你，已经是当前题型的最后一题啦！")
