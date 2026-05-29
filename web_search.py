# ==========================================
# 导入相关库模块区域
# ==========================================
import streamlit as st
import pandas as pd
import os
import re

# ------------------------------------------
# 自定义区域：基础配置与参数
# ------------------------------------------
FILE_PATH = '完整题库_精排版.xlsx'  # 题库文件路径

# 设置网页的浏览器标签页标题和布局模式（wide 为宽屏模式）
st.set_page_config(page_title="题库极速检索引擎", layout="wide")


# ==========================================
# 数据处理与核心算法模块区域
# ==========================================
def normalize_text(text):
    """
    核心文本清洗函数：清除全半角标点、空格、特殊符号
    目的：只保留中英文字符和数字，实现极高容错率的模糊匹配
    """
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r'[^\w\u4e00-\u9fa5]', '', text).lower()


# 使用 st.cache_data 进行数据缓存，防止每次点击搜索都重新读取 Excel，极大提升网页响应速度
@st.cache_data
def load_and_prepare_data(path):
    """读取本地 Excel，并预先生成用于搜索的归一化隐藏列，加快后续搜索速度"""
    if not os.path.exists(path):
        return None

    # 填充空值为字符串，防止报错
    df = pd.read_excel(path).fillna("")

    # 拼接所有的选项到一个字符串，方便全局搜索
    def concat_options(row):
        opts_str = ""
        for opt in ['A', 'B', 'C', 'D', 'E', 'F']:
            val = row.get(f'选项{opt}', '')
            if val:
                opts_str += str(val)
        return opts_str

    # 生成去除标点后的影子列，用于后台隐式比对
    df['归一化_题目'] = df['题目内容'].apply(normalize_text)
    df['选项拼接'] = df.apply(concat_options, axis=1)
    df['归一化_选项'] = df['选项拼接'].apply(normalize_text)
    df['归一化_全部'] = df['归一化_题目'] + df['归一化_选项']

    return df


# 载入数据并进行异常拦截
df = load_and_prepare_data(FILE_PATH)
if df is None:
    st.error(f"❌ 找不到题库文件：{FILE_PATH}。请检查文件是否存在，或是否与本程序在同一目录下。")
    st.stop()

# ==============================================================================
# 网页界面渲染与控制区域
# ==============================================================================
st.title("⚡ 题库极速检索引擎 (Web版)")
st.write("---")

# 1. 构建顶部的控制操作区域 (使用列布局并排显示)
# 将页面分为三列，比例为 1:1:2，让输入框更宽一些
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # 动态获取不重复的题型
    types_list = ["全部题型"] + [str(t) for t in df['题型'].unique() if str(t).strip() != ""]
    selected_type = st.selectbox("🎯 题型筛选:", types_list)

with col2:
    search_scope = st.selectbox("📂 匹配范围:", ["全部 (题目+选项)", "仅搜索题目", "仅搜索选项"])

with col3:
    # 输入框自带回车触发刷新的特性
    search_query = st.text_input("✍️ 关键词 (输入后按回车直接搜索):", "")

st.write("---")

# ==============================================================================
# 搜索逻辑执行与结果展示区域
# ==============================================================================
# 当用户有输入时，才执行搜索和展示渲染
if search_query.strip() != "":

    # 第 1 步：先按照用户选择的【题型】进行初步过滤
    if selected_type != "全部题型":
        filtered_df = df[df['题型'] == selected_type]
    else:
        filtered_df = df

    # 第 2 步：对初步过滤出的数据进行深度文本比对
    norm_query = normalize_text(search_query)

    if search_scope == "仅搜索题目":
        mask = filtered_df['归一化_题目'].str.contains(norm_query, na=False)
    elif search_scope == "仅搜索选项":
        mask = filtered_df['归一化_选项'].str.contains(norm_query, na=False)
    else:
        mask = filtered_df['归一化_全部'].str.contains(norm_query, na=False)

    # 获取最终的切片数据并统计数量
    results_df = filtered_df[mask].reset_index(drop=True)
    total_results = len(results_df)

    if total_results == 0:
        st.warning("⚠️ 未找到匹配的题目，请尝试缩短或更换搜索关键词。")
    else:
        st.success(f"✅ 成功为您找到 {total_results} 道相关题目：")

        # 循环遍历搜索出的每一行数据进行 HTML 渲染
        for index, row in results_df.iterrows():
            q_type = str(row.get('题型', '未知'))
            question_text = str(row.get('题目内容', ''))

            # 渲染大号题干
            st.markdown(f"#### 第 {index + 1} 题 【{q_type}】")
            st.markdown(f"<div style='font-size: 1.15em; line-height: 1.6; margin-bottom: 15px;'>{question_text}</div>",
                        unsafe_allow_html=True)

            correct_answers_str = str(row.get('正确答案', ''))

            # --- 判断题的专属渲染逻辑 ---
            if "判断" in q_type:
                options_dict = {'A': '正确', 'B': '错误'}
                mapped_correct = 'A' if correct_answers_str == '1' else (
                    'B' if correct_answers_str in ['2', '0'] else correct_answers_str)

                for opt, opt_val in options_dict.items():
                    if opt in mapped_correct:
                        # 命中答案：渲染带勾选的绿色高亮卡片
                        highlight_html = f"""
                        <div style="background-color: #e8f5e9; color: #1b5e20; padding: 10px 15px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #4caf50; font-size: 1.05em;">
                            ✔️ {opt}. {opt_val} (正确答案)
                        </div>
                        """
                        st.markdown(highlight_html, unsafe_allow_html=True)
                    else:
                        # 错误选项：渲染灰色普通文本
                        st.markdown(
                            f"<div style='margin-bottom: 10px; padding-left: 15px; color: #555; font-size: 1.05em;'>{opt}. {opt_val}</div>",
                            unsafe_allow_html=True)

            # --- 常规单选、多选题渲染逻辑 ---
            else:
                for opt in ['A', 'B', 'C', 'D', 'E', 'F']:
                    opt_val = str(row.get(f'选项{opt}', ''))
                    if opt_val:
                        if opt in correct_answers_str:
                            # 命中答案：渲染带勾选的绿色高亮卡片
                            highlight_html = f"""
                            <div style="background-color: #e8f5e9; color: #1b5e20; padding: 10px 15px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #4caf50; font-size: 1.05em;">
                                ✔️ {opt}. {opt_val} (正确答案)
                            </div>
                            """
                            st.markdown(highlight_html, unsafe_allow_html=True)
                        else:
                            # 错误选项：渲染灰色普通文本
                            st.markdown(
                                f"<div style='margin-bottom: 10px; padding-left: 15px; color: #555; font-size: 1.05em;'>{opt}. {opt_val}</div>",
                                unsafe_allow_html=True)

            # 渲染底部题目解析区域
            remark = str(row.get('解析', ''))
            if remark and remark != "无" and remark != "nan":
                st.caption(f"**💡 解析：** {remark}")

            st.write("---")
else:
    # 当没有输入搜索词时，给出默认提示
    st.info("👆 请在上方输入框中输入关键词，系统将自动进行极速匹配。")