import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
from mysql.connector import Error

st.set_page_config(page_title="抗生素耐药性数据库", layout="wide")

st.title("🦠 抗生素耐药性数据库管理系统")

def get_connection():
    """创建数据库连接，支持本地和Streamlit Cloud"""
    try:
        # 检查是否使用云端配置
        use_cloud = False
        try:
            if 'mysql' in st.secrets:
                use_cloud = True
        except:
            pass
        
        if use_cloud:
            # 生产环境（TiDB Cloud）
            config = {
                'host': st.secrets['mysql']['host'],
                'user': st.secrets['mysql']['user'],
                'password': st.secrets['mysql']['password'],
                'database': st.secrets['mysql']['database'],
                'port': int(st.secrets['mysql'].get('port', 4000)),
                'use_pure': True
            }
        else:
            # 本地开发环境
            config = {
                'host': 'localhost',
                'user': 'root',
                'password': 'lyx20041116',
                'database': 'antibiotic_resistance',
                'port': 3306
            }
        
        conn = mysql.connector.connect(**config)
        return conn
        
    except mysql.connector.Error as e:
        st.error(f"数据库连接错误: {e}")
        # 调试信息（仅在连接失败时显示）
        try:
            st.write("调试信息:")
            st.write(f"hasattr st.secrets: {hasattr(st, 'secrets')}")
            if hasattr(st, 'secrets'):
                st.write(f"secrets keys: {list(st.secrets.keys()) if st.secrets else 'empty'}")
        except:
            pass
        return None
        

# 侧边栏
st.sidebar.title("导航")
menu = st.sidebar.selectbox(
    "选择功能",
    ["数据概览", "耐药基因查询", "统计分析", "数据管理"]
)

# 显示数据库统计信息
try:
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        
        # 获取各个表的数量
        cursor.execute("SELECT COUNT(*) FROM aro")
        aro_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM literature")
        literature_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM model")
        model_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM snps")
        snps_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # 显示统计信息
        st.sidebar.metric("🧬 ARO总数 (aro)", aro_count)
        st.sidebar.metric("📚 文献数量 (literature)", literature_count)
        st.sidebar.metric("🏷️ 模型数量 (model)", model_count)
        st.sidebar.metric("🔬 SNPs数量 (snps)", snps_count)
        
except Exception as e:
    st.sidebar.error(f"统计失败: {e}")

# 数据概览页面
if menu == "数据概览":
    st.subheader("📊 数据概览")
    
    conn = get_connection()
    if conn:
        try:
            # 显示 aro 表数据
            st.write("### ARO表 (aro)")
            df_aro = pd.read_sql("SELECT aro_id, aro_accession, aro_name, model_id, protein_accession, dna_accession FROM aro", conn)
            st.dataframe(df_aro, use_container_width=True)

            # 显示模型与分类关联数据
            st.write("### 模型信息表 (model)")
            df_model_class = pd.read_sql("""
                SELECT 
                    m.model_id,
                    m.model_name,
                    m.model_type,
                    c.amr_gene_family,
                    c.resistance_mechanism,
                    c.drug_class
                FROM model m
                LEFT JOIN classification c ON m.model_id = c.model_id
                ORDER BY m.model_id
            """, conn)
            st.dataframe(df_model_class, use_container_width=True)

            # 显示 antibiotic 表数据
            st.write("### 抗生素缩写表 (antibiotic)")
            df_antibiotic = pd.read_sql("SELECT * FROM antibiotic", conn)
            st.dataframe(df_antibiotic, use_container_width=True)

            # 显示 pathogen 表数据
            st.write("### 病原体缩写表 (pathogen)")
            df_pathogen = pd.read_sql("SELECT * FROM pathogen", conn)
            st.dataframe(df_pathogen, use_container_width=True)
   
        except Exception as e:
            st.error(f"查询失败: {e}")
        finally:
            conn.close()
    else:
        st.error("无法连接到数据库")

# 基因查询页面
elif menu == "耐药基因查询":
    st.subheader("🔍 耐药基因查询")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_type = st.selectbox(
            "查询类型",
            ["ARO名称", "ARO编号", "模型ID", "蛋白编号", "DNA编号"]
        )
    
    with col2:
        search_keyword = st.text_input("输入关键词")
    
    # 搜索按钮
    if st.button("搜索", type="primary"):
        if search_keyword and search_keyword.strip():
            conn = get_connection()
            if conn:
                try:
                    # 根据查询类型构建查询
                    if search_type == "ARO名称":
                        query = """
                            SELECT a.aro_id, a.aro_accession, a.aro_name, a.model_id, 
                                   a.dna_accession, a.protein_accession, a.description,
                                   c.amr_gene_family, c.resistance_mechanism, c.drug_class
                            FROM aro a
                            LEFT JOIN classification c ON a.model_id = c.model_id
                            WHERE a.aro_name LIKE %s
                            """
                        params = (f'%{search_keyword.strip()}%',)
                    
                    elif search_type == "ARO编号":
                        query = """
                            SELECT a.aro_id, a.aro_accession, a.aro_name, a.model_id, 
                                   a.dna_accession, a.protein_accession, a.description,
                                   c.amr_gene_family, c.resistance_mechanism, c.drug_class
                            FROM aro a
                            LEFT JOIN classification c ON a.model_id = c.model_id
                            WHERE a.aro_accession LIKE %s
                            """
                        params = (f'%{search_keyword.strip()}%',)
                    
                    elif search_type == "模型ID":
                        query = """
                            SELECT a.aro_id, a.aro_accession, a.aro_name, a.model_id, 
                                   a.dna_accession, a.protein_accession, a.description,
                                   c.amr_gene_family, c.resistance_mechanism, c.drug_class
                            FROM aro a
                            LEFT JOIN classification c ON a.model_id = c.model_id
                            WHERE a.model_id LIKE %s
                            """
                        params = (f'%{search_keyword.strip()}%',)

                    elif search_type == "蛋白编号":
                        query = """
                            SELECT a.aro_id, a.aro_accession, a.aro_name, a.model_id, 
                                   a.dna_accession, a.protein_accession, a.description,
                                   c.amr_gene_family, c.resistance_mechanism, c.drug_class
                            FROM aro a
                            LEFT JOIN classification c ON a.model_id = c.model_id
                            WHERE a.protein_accession LIKE %s
                            """
                        params = (f'%{search_keyword.strip()}%',)
                    
                    else:  # DNA编号
                        query = """
                            SELECT a.aro_id, a.aro_accession, a.aro_name, a.model_id, 
                                   a.dna_accession, a.protein_accession, a.description,
                                   c.amr_gene_family, c.resistance_mechanism, c.drug_class
                            FROM aro a
                            LEFT JOIN classification c ON a.model_id = c.model_id
                            WHERE a.dna_accession LIKE %s
                            """
                        params = (f'%{search_keyword.strip()}%',)
                    
                    # 执行主查询
                    df = pd.read_sql(query, conn, params=params)
                    
                    if len(df) > 0:
                        st.success(f"找到 {len(df)} 条记录")
                        
                        for idx, row in df.iterrows():
                            with st.expander(f"{row['aro_accession']} - {row['aro_name']}"):
                                # 获取文献 PMID 信息
                                pmid_query = """
                                    SELECT GROUP_CONCAT(DISTINCT pmid ORDER BY pmid SEPARATOR ', ') as pmids
                                    FROM literature 
                                    WHERE aro_accession = %s
                                """
                                pmid_df = pd.read_sql(pmid_query, conn, params=(row['aro_accession'],))
                                pmids = pmid_df.iloc[0]['pmids'] if pmid_df.iloc[0]['pmids'] else '无文献记录'
                                
                                # 获取 SNPs mutations 信息
                                snps_query = """
                                    SELECT GROUP_CONCAT(DISTINCT mutations ORDER BY mutations SEPARATOR '; ') as mutations
                                    FROM snps 
                                    WHERE accession = %s
                                """
                                snps_df = pd.read_sql(snps_query, conn, params=(row['aro_accession'],))
                                mutations = snps_df.iloc[0]['mutations'] if snps_df.iloc[0]['mutations'] else '无SNP记录'
                                
                                # 获取 SNPs citation 信息
                                snps_citation_query = """
                                    SELECT GROUP_CONCAT(DISTINCT citation ORDER BY citation SEPARATOR '; ') as citations
                                    FROM snps 
                                    WHERE accession = %s AND citation IS NOT NULL AND citation != ''
                                """
                                snps_citation_df = pd.read_sql(snps_citation_query, conn, params=(row['aro_accession'],))
                                snps_citations = snps_citation_df.iloc[0]['citations'] if snps_citation_df.iloc[0]['citations'] else '无引用信息'
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**基本信息**")
                                    st.write(f"ARO编号: {row['aro_accession']}")
                                    st.write(f"ARO名称: {row['aro_name']}")
                                    st.write(f"模型ID: {row['model_id'] if row['model_id'] else 'N/A'}")
                                    st.write(f"DNA编号: {row['dna_accession'] if row['dna_accession'] else 'N/A'}")
                                    st.write(f"蛋白编号: {row['protein_accession'] if row['protein_accession'] else 'N/A'}")
                                with col2:
                                    st.write("**分类信息**")
                                    st.write(f"基因家族: {row.get('amr_gene_family', 'N/A')}")
                                    st.write(f"耐药机制: {row.get('resistance_mechanism', 'N/A')}")
                                    st.write(f"药物类别: {row.get('drug_class', 'N/A')}")
                                
                                st.write("**描述**")
                                st.write(row['description'] if row['description'] else '无描述')
                                
                                st.write("**相关文献 (PMID)**")
                                st.write(pmids)
                                
                                st.write("**SNP突变信息**")
                                if mutations != '无SNP记录':
                                    mutation_list = mutations.split('; ')
                                    st.write(f"共 {len(mutation_list)} 个突变位点")
                                    cols = st.columns(3)
                                    for i, mut in enumerate(mutation_list):
                                        cols[i % 3].write(f"- {mut}")
                                else:
                                    st.write(mutations)
                                
                                st.write("**SNP相关文献引用**")
                                st.write(snps_citations)
                                
                    else:
                        st.warning("未找到相关记录")
                    
                except Exception as e:
                    st.error(f"查询失败: {e}")
                finally:
                    conn.close()
            else:
                st.error("无法连接到数据库")
        else:
            st.warning("请输入搜索关键词")

# 统计分析页面
elif menu == "统计分析":
    st.subheader("📈 统计分析")
    
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM classification")
            count = cursor.fetchone()[0]
            cursor.close()
            
            if count == 0:
                st.warning("分类表中暂无数据，请先导入数据")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("### 耐药基因家族分布")
                    df_family = pd.read_sql("""
                        SELECT amr_gene_family, COUNT(*) as count
                        FROM classification
                        WHERE amr_gene_family IS NOT NULL AND amr_gene_family != ''
                        GROUP BY amr_gene_family
                        ORDER BY count DESC
                        LIMIT 10
                    """, conn)
                    
                if len(df_family) > 0:
                    df_family['amr_gene_family'] = df_family['amr_gene_family'].apply(
                        lambda x: x[:25] + '...' if len(x) > 25 else x
                    )
                    
                    if len(df_family) > 0:
                        fig1 = px.bar(
                            df_family,
                            x='amr_gene_family',
                            y='count',
                            title="基因家族分布 Top 10",
                            color='count',
                            color_continuous_scale='Viridis',
                            text='count'
                        )
                        fig1.update_layout(
                            xaxis_title="基因家族",
                            yaxis_title="数量",
                            height=450,
                            showlegend=False
                        )
                        fig1.update_traces(textposition='outside')
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("暂无基因家族数据")
                
                
                with col2:
                    st.write("### 耐药机制分布")
                    df_mechanism = pd.read_sql("""
                        SELECT resistance_mechanism, COUNT(*) as count
                        FROM classification
                        WHERE resistance_mechanism IS NOT NULL AND resistance_mechanism != ''
                        GROUP BY resistance_mechanism
                        ORDER BY count DESC
                        LIMIT 10
                    """, conn)
                    
                    if len(df_mechanism) > 0:
                        df_mechanism['resistance_mechanism_short'] = df_mechanism['resistance_mechanism'].apply(
                            lambda x: x[:30] + '...' if len(x) > 30 else x
                        )
                        fig2 = px.bar(
                            df_mechanism,
                            x='resistance_mechanism_short',
                            y='count',
                            title="耐药机制分布 Top 10",
                            color='count',
                            color_continuous_scale='Plasma'
                        )
                        fig2.update_layout(
                            xaxis_title="耐药机制",
                            yaxis_title="数量",
                            height=450,
                            showlegend=False
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("暂无耐药机制数据")
                
                st.markdown("---")
                st.write("### 药物类别分布")
                
                df_drug = pd.read_sql("""
                    SELECT drug_class, COUNT(*) as count
                    FROM classification
                    WHERE drug_class IS NOT NULL AND drug_class != ''
                    GROUP BY drug_class
                    ORDER BY count DESC
                    LIMIT 15
                """, conn)
                
                if len(df_drug) > 0:
                    df_drug['drug_class_short'] = df_drug['drug_class'].apply(
                        lambda x: x[:40] + '...' if len(x) > 40 else x
                    )
                    fig3 = px.bar(
                        df_drug,
                        y='drug_class_short',
                        x='count',
                        title="药物类别分布 Top 15",
                        orientation='h',
                        color='count',
                        color_continuous_scale='Blues',
                        text='count'
                    )
                    fig3.update_layout(
                        xaxis_title="数量",
                        yaxis_title="药物类别",
                        height=600,
                        yaxis={'categoryorder': 'total ascending'}
                    )
                    fig3.update_traces(textposition='outside')
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("暂无药物类别数据")
                
        except Exception as e:
            st.error(f"统计失败: {e}")
            st.info("请确保数据库表中有数据")
        finally:
            conn.close()
    else:
        st.error("无法连接到数据库")

# 数据管理页面
elif menu == "数据管理":
    st.subheader("🔧 数据管理")
    
    # 管理员验证
    def check_admin():
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        return st.session_state.authenticated
    
    def admin_login():
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔐 管理员登录")
        password = st.sidebar.text_input("管理员密码", type="password")
        if st.sidebar.button("登录"):
            if password == "12345678":
                st.session_state.authenticated = True
                st.sidebar.success("登录成功！")
                st.rerun()
            else:
                st.sidebar.error("密码错误！")
    
    def admin_logout():
        if st.sidebar.button("登出"):
            st.session_state.authenticated = False
            st.rerun()
    
    if not check_admin():
        st.info("🔒 数据管理需要管理员权限，请在左侧边栏登录")
        admin_login()
        conn = get_connection()
        if conn:
            try:
                st.write("### 📋 ARO列表（只读模式）")
                df = pd.read_sql("SELECT aro_id, aro_accession, aro_name, model_id FROM aro ORDER BY aro_id DESC LIMIT 100", conn)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"查询失败: {e}")
            finally:
                conn.close()
    else:
        st.success("✅ 管理员已登录")
        admin_logout()
        
        tab1, tab2 = st.tabs(["添加ARO", "ARO列表"])
        
        with tab1:
            st.write("### 添加新ARO")
            with st.form("add_aro"):
                aro_accession = st.text_input("ARO编号 *")
                aro_name = st.text_input("ARO名称 *")
                model_id = st.text_input("模型ID")
                dna_accession = st.text_input("DNA编号")
                protein_accession = st.text_input("蛋白编号")
                description = st.text_area("描述")
                
                submitted = st.form_submit_button("提交")
                
                if submitted:
                    if not aro_accession or not aro_name:
                        st.error("请填写ARO编号和ARO名称")
                    else:
                        conn = get_connection()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO aro (aro_accession, aro_name, model_id, dna_accession, protein_accession, description)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (aro_accession, aro_name, model_id, dna_accession, protein_accession, description))
                                conn.commit()
                                st.success("ARO添加成功！")
                                st.rerun()
                                cursor.close()
                            except Exception as e:
                                st.error(f"添加失败: {e}")
                            finally:
                                conn.close()
                        else:
                            st.error("无法连接到数据库")
        
        with tab2:
            st.write("### ARO列表")
            conn = get_connection()
            if conn:
                try:
                    df = pd.read_sql("SELECT aro_id, aro_accession, aro_name, model_id FROM aro ORDER BY aro_id DESC", conn)
                    
                    if not df.empty:
                        aro_options = {f"{row['aro_id']} - {row['aro_accession']} ({row['aro_name']})": row['aro_id'] for _, row in df.iterrows()}
                        selected_aro_display = st.selectbox("选择要删除的ARO", options=list(aro_options.keys()), key="aro_select")
                        selected_aro_id = aro_options[selected_aro_display]
                        selected_aro = df[df['aro_id'] == selected_aro_id].iloc[0]
                        
                        if st.button("🗑️ 删除选中的ARO", type="primary", key="delete_btn"):
                            st.session_state.show_confirm = True
                        
                        if st.session_state.get('show_confirm', False):
                            st.warning(f"⚠️ 确定要删除以下ARO吗？此操作不可撤销！\n\n"
                                      f"- ID: {selected_aro['aro_id']}\n"
                                      f"- 编号: {selected_aro['aro_accession']}\n"
                                      f"- 名称: {selected_aro['aro_name']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 确认删除", key="confirm_delete"):
                                    cursor = conn.cursor()
                                    try:
                                        # 检查外键依赖（只检查 literature 和 snps 表）
                                        cursor.execute("SELECT COUNT(*) FROM literature WHERE aro_accession = %s", (selected_aro['aro_accession'],))
                                        lit_count = cursor.fetchone()[0]
                                        cursor.execute("SELECT COUNT(*) FROM snps WHERE accession = %s", (selected_aro['aro_accession'],))
                                        snps_count = cursor.fetchone()[0]
                                        
                                        if lit_count > 0 or snps_count > 0:
                                            st.error(f"❌ 无法删除：该ARO在 literature 表中有 {lit_count} 条关联记录，在 snps 表中有 {snps_count} 条关联记录")
                                        else:
                                            cursor.execute("DELETE FROM aro WHERE aro_id = %s", (selected_aro_id,))
                                            conn.commit()
                                            st.success(f"✅ 已成功删除ARO ID: {selected_aro_id}")
                                            st.session_state.show_confirm = False
                                            st.rerun()
                                            
                                    except Exception as e:
                                        st.error(f"删除失败: {e}")
                                    finally:
                                        cursor.close()
                            
                            with col2:
                                if st.button("❌ 取消", key="cancel_delete"):
                                    st.session_state.show_confirm = False
                                    st.rerun()
                        
                        st.divider()
                        st.write("### 当前ARO数据表")
                        st.dataframe(df, use_container_width=True)
                        
                        st.write("### 统计信息")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("总ARO数量", len(df))
                        with col2:
                            with_model = df['model_id'].notna().sum()
                            st.metric("已关联模型", with_model)
                        with col3:
                            st.metric("数据完整率", f"{len(df)/len(df)*100:.0f}%")
                        
                    else:
                        st.info("暂无ARO数据。")
                    
                except Exception as e:
                    st.error(f"查询失败: {e}")
                finally:
                    conn.close()
            else:
                st.error("无法连接到数据库")

st.markdown("---")
st.caption("抗生素耐药性数据库管理系统 © 2026")
