# ==========================================
# 导入相关库模块区域
# 说明：引入 Web 核心库、数据处理库以及数学、随机计算库
# ==========================================
import streamlit as st
import pandas as pd
import os
import math
import random

# ------------------------------------------
# 自定义区域：基础配置与参数
# ------------------------------------------
FILE_PATH = '完整题库_精排版.xlsx'  # Excel 题库文件路径
NAV_PER_PAGE = 50  # 刷题模式下，侧边栏一次展示的序号按钮数量

# 设置网页的浏览器标签页标题和布局模式（wide 为宽屏模式）
st.set_page_config(page_title="内部题库练习系统", layout="wide")


# ==========================================
# 数据加载模块区域 (利用缓存提速)
# ==========================================
@st.cache_data
def load_exam_data(path):
    """读取本地的 Excel 题库文件，并清洗空值"""
    if os.path.exists(path):
        return pd.read_excel(path).fillna("")
    return None

# 载入原始完整数据集
df = load_exam_data(FILE_PATH)

# 容错处理：如果文件缺失则在页面弹出警告并拦截中断
if df is None:
    st.error(f"❌ 找不到题库文件：{FILE_PATH}。请检查文件是否存在，或是否与本程序在同一目录下。")
    st.stop()


# ==========================================
# 侧边栏：全局双模式切换控制区
# ==========================================
st.sidebar.title("⚙️ 功能导航")
app_mode = st.sidebar.radio("请选择当前模式：", ["📖 刷题模式", "📝 自我检测 (100题)"])
st.sidebar.write("---")


# ==============================================================================
# 第一大模块：【📖 刷题模式】专属逻辑区域
# ==============================================================================
if app_mode == "📖 刷题模式":
    
    # 1. 动态获取所有不重复的题型组合
    all_types = ["全部题型"] + list(df['题型'].unique())
    
    # --- 新增：尝试从 URL 参数中读取上次退出的题型 ---
    default_type_index = 0
    if "q_type" in st.query_params:
        url_type = st.query_params["q_type"]
        # 确保读取到的题型确实在我们的题库列表中
        if url_type in all_types:
            default_type_index = all_types.index(url_type)

    # 将选择框的默认值（index）绑定为我们刚刚读取到的历史题型
    selected_type = st.sidebar.selectbox("🎯 选择刷题题型", all_types, index=default_type_index)

    # 2. 初始化并监控题型切换状态（防崩溃机制）
    if 'last_selected_type' not in st.session_state:
        st.session_state.last_selected_type = selected_type

    # 检测到切换题型，做题进度索引归零
    if st.session_state.last_selected_type != selected_type:
        st.session_state.current_index = 0
        st.session_state.nav_page = 0
        st.session_state.last_selected_type = selected_type

    # 3. 切片筛选子题库
    if selected_type == "全部题型":
        filtered_df = df
    else:
        filtered_df = df[df['题型'] == selected_type].reset_index(drop=True)

    total_questions = len(filtered_df)
    total_nav_pages = math.ceil(total_questions / NAV_PER_PAGE)

    # ------------------------------------------
    # 核心持久化控制：从官方原生的 URL 参数中读取历史进度
    # ------------------------------------------
    if 'current_index' not in st.session_state:
        if "q_idx" in st.query_params:
            try:
                st.session_state.current_index = int(st.query_params["q_idx"])
            except ValueError:
                st.session_state.current_index = 0
        else:
            st.session_state.current_index = 0
            
    if 'nav_page' not in st.session_state:
        st.session_state.nav_page = st.session_state.current_index // NAV_PER_PAGE

    # 安全拦截防御机制：防止因切换题型导致读取的旧进度数超出当前新题库范围而崩溃
    if st.session_state.current_index >= total_questions and total_questions > 0:
        st.session_state.current_index = 0
        st.session_state.nav_page = 0

    # 4. 侧边栏：题号导航网格 (常规刷题答题卡)
    st.sidebar.header("🗂️ 题号导航 (点击跳转)")
    if total_nav_pages > 0:
        nav_options = [f"第 {i * NAV_PER_PAGE + 1} - {min((i + 1) * NAV_PER_PAGE, total_questions)} 题" for i in range(total_nav_pages)]
        if st.session_state.nav_page >= len(nav_options):
            st.session_state.nav_page = 0
            
        selected_nav = st.sidebar.selectbox("选择题号区间", nav_options, index=st.session_state.nav_page)
        st.session_state.nav_page = nav_options.index(selected_nav)
    else:
        st.sidebar.info("当前题型下无可选区间")

    st.sidebar.write("---")

    start_q = st.session_state.nav_page * NAV_PER_PAGE
    end_q = min(start_q + NAV_PER_PAGE, total_questions)

    # 5. 渲染侧边栏跳转按钮方块
    cols_per_row = 5
    
    # 性能优化：定义点击切换题号的回调函数，杜绝双重渲染卡顿
    def jump_to_brush_q(target_idx):
        st.session_state.current_index = target_idx

    for i in range(start_q, end_q, cols_per_row):
        cols = st.sidebar.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < end_q:
                q_idx = i + j
                is_current = (q_idx == st.session_state.current_index)
                btn_type = "primary" if is_current else "secondary"
                # 绑定回调函数处理
                cols[j].button(str(q_idx + 1), key=f"btn_{q_idx}", type=btn_type, use_container_width=True, on_click=jump_to_brush_q, args=(q_idx,))

    # 6. 主界面题目内容展现区域
    if total_questions > 0:
        row = filtered_df.iloc[st.session_state.current_index]
        
        # 顶部状态栏
        st.info(f"📋 当前题型：【{selected_type}】 | 进度: {st.session_state.current_index + 1} / {total_questions}  |  本题实际类型: {row.get('题型', '未知')}")

        # 精细化排版渲染题干
        question_html = f"""
        <div style='font-size: 1.05em; line-height: 1.6; margin-bottom: 15px;'>
            <b>{st.session_state.current_index + 1}.</b> {row.get('题目内容', '')}
        </div>
        """
        st.markdown(question_html, unsafe_allow_html=True)

        correct_answers_str = str(row.get('正确答案', ''))
        q_type = str(row.get('题型', ''))

        # --- 刷题模式：判断题高亮逻辑 ---
        if "判断" in q_type:
            options_dict = {'A': '正确', 'B': '错误'}
            if correct_answers_str == '1':
                mapped_correct = 'A'
            elif correct_answers_str in ['2', '0']:
                mapped_correct = 'B'
            else:
                mapped_correct = correct_answers_str

            for opt, opt_val in options_dict.items():
                if opt in mapped_correct:
                    highlight_html = f"""
                    <div style="background-color: #e8f5e9; color: #1b5e20; padding: 8px 12px; border-radius: 5px; margin-bottom: 15px; font-weight: bold; border-left: 4px solid #4caf50; font-size: 0.95em; line-height: 1.5;">
                        {opt}. {opt_val} ✔️
                    </div>
                    """
                    st.markdown(highlight_html, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-bottom: 15px; padding-left: 15px; font-size: 0.95em; line-height: 1.5;'>{opt}. {opt_val}</div>", unsafe_allow_html=True)
        
        # --- 刷题模式：常规选择题高亮逻辑 ---
        else:
            for opt in ['A', 'B', 'C', 'D', 'E', 'F']:
                opt_val = row.get(f'选项{opt}', '')
                if opt_val:
                    if opt in correct_answers_str:
                        highlight_html = f"""
                        <div style="background-color: #e8f5e9; color: #1b5e20; padding: 8px 12px; border-radius: 5px; margin-bottom: 15px; font-weight: bold; border-left: 4px solid #4caf50; font-size: 0.95em; line-height: 1.5;">
                            {opt}. {opt_val} ✔️
                        </div>
                        """
                        st.markdown(highlight_html, unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='margin-bottom: 15px; padding-left: 15px; font-size: 0.95em; line-height: 1.5;'>{opt}. {opt_val}</div>", unsafe_allow_html=True)

        st.write("")
        # 渲染解析说明
        remark = row.get('解析', '')
        if remark and remark != "无":
            st.caption(f"**💡 解析说明：** {remark}")
    else:
        st.warning("⚠️ 该题型下没有找到任何题目数据，请尝试切换其他题型。")

    st.write("---")

    # 7. 底部控制翻页按钮（回调函数优化版，极大缓解卡顿）
    def go_brush_prev():
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            st.session_state.nav_page = st.session_state.current_index // NAV_PER_PAGE

    def go_brush_next():
        if st.session_state.current_index < total_questions - 1:
            st.session_state.current_index += 1
            st.session_state.nav_page = st.session_state.current_index // NAV_PER_PAGE

    col1, col2 = st.columns(2)
    with col1:
        st.button("⬆️ 上一题 ⬆️", use_container_width=True, on_click=go_brush_prev)
    with col2:
        st.button("⬇️ 下一题 ⬇️", use_container_width=True, on_click=go_brush_next)

# ------------------------------------------
    # 持久化核心：将最新进度和【当前题型】实时静默写入 URL 栏
    # ------------------------------------------
    st.query_params["q_idx"] = str(st.session_state.current_index)
    st.query_params["q_type"] = st.session_state.last_selected_type


# ==============================================================================
# 第二大模块：【📝 自我检测】专属逻辑区域
# ==============================================================================
elif app_mode == "📝 自我检测 (100题)":

    # 1. 考试专属状态机初始化
    if 'exam_state' not in st.session_state:
        st.session_state.exam_state = 'not_started' 
        st.session_state.exam_df = None             
        st.session_state.exam_answers = {}          
        st.session_state.exam_idx = 0               
        st.session_state.exam_score = 0             
        st.session_state.show_result_popup = False  

    # ==========================================
    # 考试模式专门：弹窗函数定义区域
    # ==========================================
    # 弹窗 A：结算成绩单
    @st.dialog("📊 考试成绩单")
    def show_result_dialog(score, total):
        st.markdown(f"<h1 style='text-align: center; color: #d32f2f;'>{score} 分</h1>", unsafe_allow_html=True)
        st.write(f"**考试详情**：共计 {total} 题，您答对了 **{score}** 题。")
        if score >= total * 0.6:  
            st.success("🎉 太棒了！成绩非常理想！")
            st.balloons()  
        else:
            st.warning("💪 还要继续努力哦！错题已在左侧答题卡中标记为 🔴。")
        
        if st.button("立即去复盘错题", use_container_width=True):
            st.session_state.show_result_popup = False 
            st.rerun()  

    # 弹窗 B：未做完拦截警告弹窗
    @st.dialog("⚠️ 确认交卷")
    def confirm_submit_dialog(unanswered_count, total_q):
        st.warning(f"您还有 **{unanswered_count}** 道题未作答！")
        st.write("确定要放弃这些题目并现在交卷吗？")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("继续答题", use_container_width=True):
                st.rerun() 
        with c2:
            if st.button("确认交卷", type="primary", use_container_width=True):
                score = 0
                for i in range(total_q):
                    user_ans = st.session_state.exam_answers.get(i, "")
                    real_ans = st.session_state.exam_df.iloc[i]['统一正确答案']
                    if user_ans == real_ans:
                        score += 1
                
                st.session_state.exam_score = score
                st.session_state.exam_state = 'finished'
                st.session_state.exam_idx = 0 
                st.session_state.show_result_popup = True 
                st.rerun()

    # 监控触发器：检测是否展示成绩单
    if st.session_state.show_result_popup:
        show_result_dialog(st.session_state.exam_score, len(st.session_state.exam_df))

    # ==========================================
    # 考试核心流程推进控制区
    # ==========================================
    st.title("📝 模拟自我检测")

    # --- 状态 A：未开始（抽取生成考卷） ---
    if st.session_state.exam_state == 'not_started':
        st.info("规则说明：系统将随机抽取 **单选50题 + 判断20题 + 多选30题**，共计100题。每题1分，满分100分。")
        if st.button("🚀 立即生成试卷并开始考试", type="primary"):
            
            # 按配比高效率随机抽样题目
            single_df = df[df['题型'].str.contains('单选')].sample(n=min(50, len(df[df['题型'].str.contains('单选')])), random_state=random.randint(1,1000))
            tf_df = df[df['题型'].str.contains('判断')].sample(n=min(20, len(df[df['题型'].str.contains('判断')])), random_state=random.randint(1,1000))
            multi_df = df[df['题型'].str.contains('多选')].sample(n=min(30, len(df[df['题型'].str.contains('多选')])), random_state=random.randint(1,1000))
            
            # 整合考卷数据
            final_exam_df = pd.concat([single_df, tf_df, multi_df]).reset_index(drop=True)
            
            # 数据规范预映射
            def map_answer(row):
                if "判断" in str(row['题型']):
                    ans = str(row['正确答案'])
                    if ans == '1': return 'A'
                    elif ans in ['2', '0']: return 'B'
                    return ans
                return str(row['正确答案'])
                
            final_exam_df['统一正确答案'] = final_exam_df.apply(map_answer, axis=1)
            
            st.session_state.exam_df = final_exam_df
            st.session_state.exam_answers = {}
            st.session_state.exam_idx = 0
            st.session_state.exam_state = 'testing'
            st.rerun()

    # --- 状态 B：答题阶段与交卷回顾阶段 ---
    elif st.session_state.exam_state in ['testing', 'finished']:
        exam_df = st.session_state.exam_df
        total_exam_q = len(exam_df)
        curr_idx = st.session_state.exam_idx
        row = exam_df.iloc[curr_idx]
        q_type = str(row.get('题型', '未知'))
        
        # 头部提示栏
        if st.session_state.exam_state == 'testing':
            st.warning(f"⏳ **考试中** | 当前进度：{curr_idx + 1} / {total_exam_q} | 题型：{q_type}")
        else:
            st.success(f"✅ **已交卷** | 最终得分：**{st.session_state.exam_score}** / {total_exam_q} 分 | 当前复盘：第 {curr_idx + 1} 题")
        
        st.progress((curr_idx + 1) / total_exam_q)
        
        # ------------------------------------------
        # 侧边栏：考试专属分类数字矩阵答题卡
        # ------------------------------------------
        st.sidebar.write("---")
        st.sidebar.header("📋 考试答题卡")
        
        # 定义点击跳转答题卡题号的回调函数
        def jump_to_exam_q(target_idx):
            st.session_state.exam_idx = target_idx

        types_order = ['单选', '判断', '多选']
        for q_type_keyword in types_order:
            type_indices = [i for i, t in enumerate(exam_df['题型']) if q_type_keyword in str(t)]
            
            if type_indices:
                st.sidebar.subheader(f"【{q_type_keyword}题】")
                cols_per_row = 5
                for i in range(0, len(type_indices), cols_per_row):
                    cols = st.sidebar.columns(cols_per_row)
                    for j in range(cols_per_row):
                        if i + j < len(type_indices):
                            real_idx = type_indices[i + j]
                            
                            # 1. 动态配给Emoji红绿灯状态符号
                            btn_label = f"⚪ {real_idx + 1}"
                            
                            if st.session_state.exam_state == 'testing':
                                if real_idx in st.session_state.exam_answers and st.session_state.exam_answers[real_idx] != "":
                                    btn_label = f"🟢 {real_idx + 1}"
                            elif st.session_state.exam_state == 'finished':
                                user_ans = st.session_state.exam_answers.get(real_idx, "")
                                real_ans = exam_df.iloc[real_idx]['统一正确答案']
                                if user_ans == real_ans:
                                    btn_label = f"🟢 {real_idx + 1}"
                                else:
                                    btn_label = f"🔴 {real_idx + 1}"
                                    
                            # 2. 焦点选中题号高亮底色
                            is_current = (real_idx == st.session_state.exam_idx)
                            b_type = "primary" if is_current else "secondary"
                            
                            # 绑定回调提升响应速度
                            cols[j].button(btn_label, key=f"exam_btn_{real_idx}", type=b_type, use_container_width=True, on_click=jump_to_exam_q, args=(real_idx,))

        # ------------------------------------------
        # 主界面：题干与表单输入框渲染
        # ------------------------------------------
        question_html = f"""
        <div style='font-size: 1.05em; line-height: 1.6; margin-bottom: 15px; margin-top: 20px;'>
            <b>{curr_idx + 1}.</b> {row.get('题目内容', '')}
        </div>
        """
        st.markdown(question_html, unsafe_allow_html=True)
        
        user_ans_str = st.session_state.exam_answers.get(curr_idx, "")
        correct_ans = row.get('统一正确答案', '')

        st.write("请选择你的答案：")
        current_selection = ""
        disabled_input = (st.session_state.exam_state == 'finished') 
        
        # 分支组件 1：判断题单选框
        if "判断" in q_type:
            opts = ['A. 正确', 'B. 错误']
            def_idx = 0 if user_ans_str == 'A' else 1 if user_ans_str == 'B' else None
            ans = st.radio("选项", opts, index=def_idx, disabled=disabled_input, label_visibility="collapsed")
            if ans: current_selection = ans[0]

        # 分支组件 2：常规单选题单选框
        elif "单选" in q_type:
            opts = []
            for opt in ['A', 'B', 'C', 'D']:
                if row.get(f'选项{opt}', ''):
                    opts.append(f"{opt}. {row.get(f'选项{opt}')}")
            def_idx = None
            for i, o in enumerate(opts):
                if user_ans_str == o[0]:
                    def_idx = i
                    break
            ans = st.radio("选项", opts, index=def_idx, disabled=disabled_input, label_visibility="collapsed")
            if ans: current_selection = ans[0]

        # 分支组件 3：多选题复选框
        else:
            selected_list = []
            for opt in ['A', 'B', 'C', 'D', 'E', 'F']:
                val = row.get(f'选项{opt}', '')
                if val:
                    is_checked = opt in user_ans_str
                    if st.checkbox(f"{opt}. {val}", value=is_checked, disabled=disabled_input):
                        selected_list.append(opt)
            current_selection = ",".join(selected_list)
        
        # 实时归档记录用户作答
        if st.session_state.exam_state == 'testing':
            st.session_state.exam_answers[curr_idx] = current_selection

        st.write("---")
        
        # ------------------------------------------
        # 判分完毕后的答案反馈与解析展示区
        # ------------------------------------------
        if st.session_state.exam_state == 'finished':
            if user_ans_str == correct_ans:
                st.success(f"✔️ 回答正确！你的答案：{user_ans_str}")
            else:
                user_show = user_ans_str if user_ans_str else "未作答"
                st.error(f"❌ 回答错误。你的答案：{user_show}  |  正确答案：**{correct_ans}**")
                remark = row.get('解析', '')
                if remark and remark != "无":
                    st.caption(f"**💡 解析说明：** {remark}")
            st.write("---")

        # ------------------------------------------
        # 底部控制区：上一题、下一题、交卷控制逻辑（回调提速版）
        # ------------------------------------------
        def go_exam_prev():
            if st.session_state.exam_idx > 0:
                st.session_state.exam_idx -= 1

        def go_exam_next():
            if st.session_state.exam_idx < total_exam_q - 1:
                st.session_state.exam_idx += 1

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.button("⬅️ 上一题", use_container_width=True, on_click=go_exam_prev)
        with col2:
            st.button("下一题 ➡️", use_container_width=True, on_click=go_exam_next)
                    
        with col3:
            if st.session_state.exam_state == 'testing':
                if st.button("🚨 交卷并查看成绩", type="primary", use_container_width=True):
                    
                    # 判别是否有未做的空题
                    answered_count = sum(1 for v in st.session_state.exam_answers.values() if v.strip() != "")
                    unanswered_count = total_exam_q - answered_count
                    
                    if unanswered_count > 0:
                        confirm_submit_dialog(unanswered_count, total_exam_q)
                    else:
                        score = 0
                        for i in range(total_exam_q):
                            user_ans = st.session_state.exam_answers.get(i, "")
                            real_ans = st.session_state.exam_df.iloc[i]['统一正确答案']
                            if user_ans == real_ans:
                                score += 1
                        
                        st.session_state.exam_score = score
                        st.session_state.exam_state = 'finished'
                        st.session_state.exam_idx = 0
                        st.session_state.show_result_popup = True
                        st.rerun()
                        
            elif st.session_state.exam_state == 'finished':
                if st.button("🔄 重新开始新考试", use_container_width=True):
                    st.session_state.exam_state = 'not_started'
                    st.session_state.show_result_popup = False 
                    st.rerun()
