import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
import plotly.graph_objects as go
import urllib.request
import json

# Page configuration
st.set_page_config(
    page_title="마이 포트폴리오",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# 🔒 구글 시트 및 GID 설정 (Secrets에서 안전하게 로드)
# -----------------------------------------------------------------------------
try:
    GOOGLE_SHEET_URL = st.secrets["google_sheet"]["url"]
    GID_매수일지 = st.secrets["google_sheet"]["gid_buy_log"]
    GID_연도별수익 = st.secrets["google_sheet"]["gid_yearly_profit"]
    GID_입금액 = st.secrets["google_sheet"]["gid_deposit"]
    GID_원금대비수익률 = st.secrets["google_sheet"]["gid_profit_rate"]
except Exception as e:
    st.error(
        "🔒 Streamlit Cloud의 Settings -> Secrets 설정에 필요한 구글 시트 정보(url, gid_buy_log, gid_yearly_profit, gid_deposit, gid_profit_rate)가 누락되었거나 올바르지 않습니다. 설정을 확인해주세요.")
    st.stop()


@st.cache_data(ttl=60)
def load_sheet_by_gid(base_url, gid):
    try:
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', base_url)
        if not sheet_id_match:
            sheet_id = base_url.split('/')[-1] if '/' in base_url else base_url
        else:
            sheet_id = sheet_id_match.group(1)

        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        df = pd.read_csv(export_url)
        df.columns = df.columns.str.strip()
        df = df[[c for c in df.columns if not c.startswith('Unnamed:')]]
        return df
    except Exception as e:
        st.sidebar.warning(f"💡 GID {gid} 로드 중 참고: {e}")
        return None


# 💡 실시간 국내 주가 조회를 위한 경량 함수 추가 (네이버 금융 API 활용)
def get_current_kr_price(ticker):
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{ticker}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            price_str = data['result']['areas'][0]['datas'][0]['nv']
            return float(price_str)
    except:
        return 0


st.sidebar.header("🔄 데이터 설정")
if st.sidebar.button("🔄 구글 시트 새로고침"):
    st.cache_data.clear()
    st.rerun()

# -----------------------------------------------------------------------------
# ✨ [레이아웃 깨짐 교정] 토스 대시보드 전용 정밀 CSS 디자인 시트
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0B0E14 !important;
        color: #FFFFFF !important;
        font-family: 'Pretendard', sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #171C26 !important;
    }

    .toss-stock-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        background-color: #171C26 !important;
        border-radius: 14px;
        margin-bottom: 12px;
        border: 1px solid #222937;
    }

    .stock-left-box {
        display: flex;
        flex-direction: column;
        gap: 4px;
        align-items: flex-start;
    }

    .stock-right-box {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 2px;
    }

    .stock-main-name { font-size: 15px; font-weight: 700; color: #FFFFFF; }
    .account-badge {
        background-color: #222937; color: #3182F6; font-size: 11px;
        font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-right: 6px;
    }
    .stock-sub-qty { font-size: 12px; color: #8B95A1; }
    .stock-main-price { font-size: 15px; font-weight: 700; color: #FFFFFF; }

    .toss-summary-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px;
        margin-bottom: 12px;
        border-radius: 14px;
    }
    .toss-summary-item { flex: 1; text-align: center; }
    .toss-summary-label { font-size: 14px; color: #8B95A1; margin-bottom: 8px; }
    .toss-summary-val { font-size: 24px; font-weight: 700; color: #FFFFFF; }
    .toss-summary-subval { font-size: 13px; margin-top: 4px; font-weight: 500; }

    .dividend-highlight { color: #00D4B2 !important; }

    .weight-container-box { padding: 12px 20px; margin-top: 12px; }
    .weight-inner-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 14px 0; border-bottom: 1px solid #222937;
    }
    .weight-inner-item:last-child { border-bottom: none; }
    .badge-label { font-size: 14px; font-weight: 600; color: #E5E8EB; }
    .badge-pct { font-size: 14px; font-weight: 700; color: #FFFFFF; }
    .badge-value { font-size: 14px; color: #9EAAB8; }

    .trend-up { color: #F04452 !important; }
    .trend-down { color: #3182F6 !important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. 데이터 가져오기 및 분류 처리 함수 정의
# -----------------------------------------------------------------------------
df_raw = load_sheet_by_gid(GOOGLE_SHEET_URL, GID_매수일지)
df_yearly_raw = load_sheet_by_gid(GOOGLE_SHEET_URL, GID_연도별수익)
df_deposit_raw = load_sheet_by_gid(GOOGLE_SHEET_URL, GID_입금액)


def categorize_kind(k):
    k_str = str(k).upper()
    if 'ETF' in k_str:
        return 'ETF'
    if '이자' in k_str:
        return '이자'
    if 'ELS' in k_str:
        return 'ELS'
    if '채권' in k_str:
        return '채권'
    return '개별종목'


# 입금액 데이터 전처리
df_deposit = None
if df_deposit_raw is not None:
    df_deposit = df_deposit_raw.copy()
    for col in df_deposit.columns:
        if df_deposit[col].dtype == 'object':
            df_deposit[col] = df_deposit[col].astype(str).str.strip()
    if '금액' in df_deposit.columns:
        if df_deposit['금액'].dtype == 'object':
            df_deposit['금액'] = df_deposit['금액'].str.replace(',', '').str.strip()
        df_deposit['금액'] = pd.to_numeric(df_deposit['금액'], errors='coerce').fillna(0)


# 탭/계좌별 총 입금액 계산 함수
def get_total_deposit(tab_name):
    if df_deposit is None or df_deposit.empty:
        return 0
    if tab_name == "SUMMARY":
        target_accounts = ['ISA2', 'SUPER365', '연저펀1', '연저펀2']
    elif tab_name == "CMA":
        target_accounts = ['SUPER365']
    elif tab_name in ['ISA2', '연저펀1', '연저펀2', 'ISA']:
        target_accounts = [tab_name]
    else:
        target_accounts = [tab_name]
    filtered_df = df_deposit[df_deposit['계좌'].isin(target_accounts)]
    return filtered_df['금액'].sum()


# 탭/계좌별 배당수익 계산 함수
def get_dividend_profit(tab_name, full_df):
    if full_df is None or full_df.empty or '구분' not in full_df.columns or '총액' not in full_df.columns:
        return 0

    if tab_name == "SUMMARY":
        target_accounts = ['연저펀1', '연저펀2', 'ISA2', 'CMA']
    else:
        target_accounts = [tab_name]

    filtered_df = full_df[
        (full_df['계좌'].isin(target_accounts)) &
        (full_df['구분'] == '배당수입')
        ].copy()

    if '종목명' in filtered_df.columns:
        exclude_keywords = ['네이버통장', '발행어음', '네이버페이', '예탁금이용료']
        for keyword in exclude_keywords:
            is_cma_and_has_keyword = (filtered_df['계좌'] == 'CMA') & (
                filtered_df['종목명'].astype(str).str.contains(keyword, na=False))
            filtered_df = filtered_df[~is_cma_and_has_keyword]

    return filtered_df['총액'].abs().sum()


# -----------------------------------------------------------------------------
# 2. 매수일지(df_raw) 데이터 정밀 전처리 및 portfolio 생성
# -----------------------------------------------------------------------------
df = None
portfolio = pd.DataFrame()

# 💡 보유 종목 종가 에러 방지를 위한 주식 단축코드 매핑 사전 생성
TICKER_MAP = {
    'HD현대일렉트릭': '267260',
    '삼성전자': '005930'
}

if df_raw is not None:
    df = df_raw.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    # 숫자형 데이터 정밀 전처리
    numeric_cols = ['거래금액', '수량', '투자금', '수수료', '총액', '종가']
    for col in numeric_cols:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace(',', '').str.replace('₩', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 자산 현황용 데이터 가공 (매수 기준)
    df_buy = df[df['구분'] == '매수'].copy()

    type_mapping = df.groupby('종목명')['종류'].last().to_dict()

    portfolio = df_buy.groupby(['계좌', '종목명']).agg(
        총매입가=('투자금', 'sum'),
        보유수량=('수량', 'sum')
    ).reset_index()

    portfolio['종류'] = portfolio['종목명'].map(type_mapping)

    # 💡 [핵심 해결 로직] 구글시트 종가 대신, 파이썬이 실시간 API 주가를 가져와 매핑하도록 변경
    # 시트 내 백업 종가 먼저 매핑
    df_valid_price = df[df['종가'] > 0].sort_values(by='일자' if '일자' in df.columns else df.index)
    backup_prices = df_valid_price.groupby('종목명')['종가'].last().to_dict() if not df_valid_price.empty else {}

    current_prices = {}
    for name in portfolio['종목명'].unique():
        if name in TICKER_MAP:
            api_price = get_current_kr_price(TICKER_MAP[name])
            if api_price > 0:
                current_prices[name] = api_price
                continue
        # 매핑 사전에 없거나 API 실패 시 구글 시트 백업 값 사용
        current_prices[name] = backup_prices.get(name, 0)

    portfolio['currently_price'] = portfolio['종목명'].map(current_prices).fillna(0)

    portfolio['평가금액'] = np.where(
        (portfolio['currently_price'] == 0) & (portfolio['종류'] == 'ELS'),
        portfolio['총매입가'],
        portfolio['보유수량'] * portfolio['currently_price']
    )
    portfolio['총수익'] = portfolio['평가금액'] - portfolio['총매입가']
    portfolio['수익률'] = np.where(portfolio['총매입가'] > 0, (portfolio['총수익'] / portfolio['총매입가']) * 100, 0)

# -----------------------------------------------------------------------------
# 3. 화면 렌더링 부 (portfolio가 데이터가 있을 때만 실행)
# -----------------------------------------------------------------------------
if not portfolio.empty:
    # 계좌 정렬 순서 정의
    raw_accounts = [acc for acc in portfolio['계좌'].unique() if acc not in ['nan', '', 'None']]
    active_accounts = [acc for acc in raw_accounts if acc != 'ISA']
    inactive_accounts = [acc for acc in raw_accounts if acc == 'ISA']
    final_account_order = active_accounts + inactive_accounts

    # 탭 구성
    tab_titles = ["📈 SUMMARY"] + [f"💳 {acc}" for acc in final_account_order]
    tabs = st.tabs(tab_titles)

    active_portfolio = portfolio[(portfolio['보유수량'] > 0) | (portfolio['종류'] == 'ELS')].copy()
    active_portfolio = active_portfolio[active_portfolio['종류'] != '채권']


    # 공통 컴포넌트 함수 정의
    def render_summary_and_weights():
        total_inv_all = active_portfolio['총매입가'].sum()
        total_eva_all = active_portfolio['평가금액'].sum()
        total_profit_all = total_eva_all - total_inv_all
        total_rate_all = (total_profit_all / total_inv_all * 100) if total_inv_all > 0 else 0

        total_deposit_all = get_total_deposit("SUMMARY")
        dividend_profit_all = get_dividend_profit("SUMMARY", df)
        dividend_rate_all = (dividend_profit_all / total_deposit_all * 100) if total_deposit_all > 0 else 0

        net_profit_all = total_profit_all + dividend_profit_all
        net_rate_all = (net_profit_all / total_deposit_all * 100) if total_deposit_all > 0 else 0

        st.markdown(f"""
        <div class="toss-summary-container" style="background-color: #171C26;">
            <div class="toss-summary-item"><div class="toss-summary-label">총 투자금액</div><div class="toss-summary-val">{total_inv_all:,.0f}원</div></div>
            <div class="toss-summary-item" style="border-left: 1px solid #222937; border-right: 1px solid #222937;"><div class="toss-summary-label">총 평가금액</div><div class="toss-summary-val">{total_eva_all:,.0f}원</div></div>
            <div class="toss-summary-item">
                <div class="toss-summary-label">총 평가손익</div>
                <div class="toss-summary-val {"trend-up" if total_profit_all >= 0 else "trend-down"}">{"+" if total_profit_all >= 0 else ""}{total_profit_all:,.0f}원</div>
                <div class="toss-summary-subval {"trend-up" if total_profit_all >= 0 else "trend-down"}">({"+" if total_profit_all >= 0 else ""}{total_rate_all:.2f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="toss-summary-container" style="background-color: #171C26; margin-top: -10px; margin-bottom: 25px;">
            <div class="toss-summary-item">
                <div class="toss-summary-label">총 입금액</div>
                <div class="toss-summary-val">{total_deposit_all:,.0f}원</div>
            </div>
            <div class="toss-summary-item" style="border-left: 1px solid #222937; border-right: 1px solid #222937;">
                <div class="toss-summary-label">배당수익</div>
                <div class="toss-summary-val dividend-highlight">+{dividend_profit_all:,.0f}원</div>
                <div class="toss-summary-subval dividend-highlight">({dividend_rate_all:.2f}%)</div>
            </div>
            <div class="toss-summary-item">
                <div class="toss-summary-label">총 손익</div>
                <div class="toss-summary-val {"trend-up" if net_profit_all >= 0 else "trend-down"}">{"+" if net_profit_all >= 0 else ""}{net_profit_all:,.0f}원</div>
                <div class="toss-summary-subval {"trend-up" if net_profit_all >= 0 else "trend-down"}">({"+" if net_profit_all >= 0 else ""}{net_rate_all:.2f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_inv_side, col_eva_side = st.columns(2)
        with col_inv_side:
            st.markdown("<h3 style='font-size:17px; margin-bottom:10px;'>🪙 자산군별 투자금액 비중</h3>", unsafe_allow_html=True)
            df_type_inv = active_portfolio.groupby('종류')['총매입가'].sum().reset_index()
            df_type_inv = df_type_inv.sort_values(by='총매입가', ascending=False).reset_index(drop=True)
            df_type_inv['비중'] = (df_type_inv['총매입가'] / total_inv_all) * 100
            top_inv_pct = df_type_inv.loc[0, '비중'] if not df_type_inv.empty else 0
            st.progress(int(top_inv_pct) / 100 if top_inv_pct <= 100 else 1.0,
                        text=f"최대 비중 자산군: {df_type_inv.loc[0, '종류'] if not df_type_inv.empty else ''} ({top_inv_pct:.1f}%)")
            st.markdown("<div class='weight-container-box'>", unsafe_allow_html=True)
            for _, row in df_type_inv.iterrows():
                st.markdown(
                    f"""<div class="weight-inner-item"><span class="badge-label">🔹 {row['종류']}</span><div><div class="badge-pct">{row['비중']:.1f}%</div><div class="badge-value">{row['총매입가']:,.0f}원</div></div></div>""",
                    unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_eva_side:
            st.markdown("<h3 style='font-size:17px; margin-bottom:10px;'>📈 자산군별 평가금액 비중</h3>", unsafe_allow_html=True)
            df_type_eva = active_portfolio.groupby('종류').agg({'평가금액': 'sum', '총매입가': 'sum'}).reset_index()
            df_type_eva = df_type_eva.sort_values(by='평가금액', ascending=False).reset_index(drop=True)
            df_type_eva['비중'] = (df_type_eva['평가금액'] / total_eva_all) * 100
            df_type_eva['손익'] = df_type_eva['평가금액'] - df_type_eva['총매입가']
            top_eva_pct = df_type_eva.loc[0, '비중'] if not df_type_eva.empty else 0
            st.progress(int(top_eva_pct) / 100 if top_eva_pct <= 100 else 1.0,
                        text=f"최대 비중 자산군: {df_type_eva.loc[0, '종류'] if not df_type_eva.empty else ''} ({top_eva_pct:.1f}%)")
            st.markdown("<div class='weight-container-box'>", unsafe_allow_html=True)
            for _, row in df_type_eva.iterrows():
                p_color = "#F04452" if row['손익'] >= 0 else "#3182F6"
                sign = "+" if row['손익'] >= 0 else ""
                st.markdown(
                    f"""<div class="weight-inner-item"><span class="badge-label">🔹 {row['종류']}</span><div><div class="badge-pct">{row['비중']:.1f}%</div><div class="badge-value" style="color:{p_color} !important;">{sign}{row['손익']:,.0f}원</div></div></div>""",
                    unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


    def render_active_stock_list():
        st.markdown("<hr style='border:1px solid #161B24; margin-top:20px; margin-bottom:25px;'>",
                    unsafe_allow_html=True)
        st.markdown("<h3 style='font-size: 18px; color:#FFFFFF; margin-bottom:15px;'>🔍 보유 종목 현황</h3>",
                    unsafe_allow_html=True)
        display_active = active_portfolio.sort_values(by='수익률', ascending=False)
        col_list_left, col_list_right = st.columns(2)
        half = int(np.ceil(len(display_active) / 2))
        left_side_data = display_active.iloc[:half]
        right_side_data = display_active.iloc[half:]

        for idx, col_target in enumerate([col_list_left, col_list_right]):
            with col_target:
                target_data = left_side_data if idx == 0 else right_side_data
                for _, row in target_data.iterrows():
                    trend_class = "trend-up" if row['총수익'] >= 0 else "trend-down"
                    sign = "+" if row['총수익'] >= 0 else ""
                    qty_str = "계약 완료" if row['종류'] == 'ELS' and row['보유수량'] == 0 else f"{row['보유수량']:,}주"

                    st.markdown(f"""
                    <div class="toss-stock-row">
                        <div class="stock-left-box">
                            <span class="stock-main-name"><span class="account-badge">{row['계좌']}</span>{row['종목명']}</span>
                            <span class="stock-sub-qty" style="margin-left: 4px;">{qty_str}</span>
                        </div>
                        <div class="stock-right-box">
                            <span class="stock-main-price">{row['평가금액']:,.0f} 원</span>
                            <span class="stock-sub-qty {trend_class}">{sign}{row['총수익']:,.0f}원 ({sign}{row['수익률']:.2f}%)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


    # -------------------------------------------------------------------------
    # 4. 📈 메인 포트폴리오 총괄표 (SUMMARY)
    # -------------------------------------------------------------------------
    with tabs[0]:
        if active_portfolio.empty:
            st.info("보유 자산 데이터가 확인되지 않습니다.")
        else:
            render_summary_and_weights()
            render_active_stock_list()

            st.markdown("<hr style='border:1px solid #161B24; margin-top:20px; margin-bottom:25px;'>",
                        unsafe_allow_html=True)
            st.markdown("<h3 style='font-size: 18px; color:#FFFFFF; margin-bottom:15px;'>📊 배당 및 이자 수입 분석</h3>",
                        unsafe_allow_html=True)

            analysis_mode = st.radio("월별/연도별 기준 선택", ["월별 추이", "연도별 추이"], horizontal=True)

            # 데이터 가공
            df_dividend = df[df['구분'].astype(str).str.contains('배당|이자', na=False)].copy()
            df_dividend['일자_정제'] = pd.to_datetime(df_dividend['일자'].astype(str).str.replace('.', '-', regex=False),
                                                  errors='coerce')
            df_dividend['실수령금'] = df_dividend['총액'].abs()
            df_dividend['자산구분'] = df_dividend['종류'].apply(categorize_kind)

            if analysis_mode == "월별 추이":
                df_dividend['표시'] = df_dividend['일자_정제'].dt.to_period('M').astype(str)
                title_text = "월별 배당/이자 수입"
            else:
                df_dividend['표시'] = df_dividend['일자_정제'].dt.year.astype(str)
                title_text = "연도별 배당/이자 수입"

            df_plot = df_dividend.groupby(['표시', '자산구분'])['실수령금'].sum().reset_index()
            df_plot = df_plot.sort_values(by='표시', ascending=True).reset_index(drop=True)
            df_total = df_plot.groupby('표시')['실수령금'].sum().reset_index()

            fig = px.bar(
                df_plot, x='표시', y='실수령금', color='자산구분',
                title=title_text,
                barmode='stack',
                color_discrete_map={
                    'ETF': '#3182F6',
                    '이자': '#00D4B2',
                    '개별종목': '#FF4B4B',
                    'ELS': '#FF9F43',
                    '채권': '#A55EEA'
                }
            )

            fig.add_trace(
                go.Scatter(
                    x=df_total['표시'],
                    y=df_total['실수령금'],
                    mode='text',
                    text=df_total['실수령금'].apply(lambda x: f"{x:,.0f}"),
                    textposition='top center',
                    textfont=dict(color='#8B95A1', size=12, family='Pretendard'),
                    showlegend=False
                )
            )

            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FFFFFF', family='Pretendard'),
                xaxis=dict(title='', gridcolor='#161B24', showgrid=True, type='category',
                           categoryorder='category ascending'),
                yaxis=dict(title='금액 (원)', gridcolor='#161B24', showgrid=True,
                           range=[0, df_total['실수령금'].max() * 1.15]),
                legend=dict(title=dict(text='자산 구분', font=dict(color='#FFFFFF')), font=dict(color='#FFFFFF')),
                margin=dict(t=50, b=20, l=10, r=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------
            # 원금대비수익률 추이 시각화 그래프
            # -----------------------------------------------------------------
            df_profit_rate_raw = load_sheet_by_gid(GOOGLE_SHEET_URL, GID_원금대비수익률)

            if df_profit_rate_raw is not None and not df_profit_rate_raw.empty:
                st.markdown("<hr style='border:1px solid #161B24; margin-top:20px; margin-bottom:25px;'>",
                            unsafe_allow_html=True)
                st.markdown(
                    "<h3 style='font-size: 18px; color:#FFFFFF; margin-bottom:15px;'>📈 원금 대비 수익률 및 자산 성장 추이</h3>",
                    unsafe_allow_html=True)

                df_pr = df_profit_rate_raw.copy()

                if '일자' in df_pr.columns:
                    df_pr['일자_정제'] = df_pr['일자'].astype(str).str.replace('.', '-', regex=False)
                    df_pr['일자_정제'] = df_pr['일자_정제'].apply(lambda x: x + '-01' if len(x) == 7 else x)
                    df_pr['일자_정제'] = pd.to_datetime(df_pr['일자_정제'], errors='coerce')
                    df_pr = df_pr.dropna(subset=['일자_정제']).sort_values('일자_정제')
                    df_pr['x_axis'] = df_pr['일자_정제'].dt.strftime('%Y-%m')
                else:
                    df_pr['x_axis'] = df_pr.index.astype(str)

                target_numeric_cols = ['누적입금액', '수익금', '입금액 대비 수익률']
                for col in target_numeric_cols:
                    if col in df_pr.columns:
                        if df_pr[col].dtype == 'object':
                            df_pr[col] = df_pr[col].astype(str).str.replace(',', '').str.replace('%', '').str.strip()
                        df_pr[col] = pd.to_numeric(df_pr[col], errors='coerce').fillna(0)

                df_pr['누적입금액_백만'] = df_pr['누적입금액'] / 1000000
                df_pr['수익금_백만'] = df_pr['수익금'] / 1000000

                fig_growth = go.Figure()

                fig_growth.add_trace(go.Bar(
                    x=df_pr['x_axis'], y=df_pr['누적입금액_백만'], name='누적입금액',
                    marker_color='#5AC8FA', opacity=0.8, yaxis='y1', hovertemplate='%{y:,.1f}백만 원'
                ))

                fig_growth.add_trace(go.Bar(
                    x=df_pr['x_axis'], y=df_pr['수익금_백만'], name='수익금',
                    marker_color='#3182F6', opacity=0.9, yaxis='y1', hovertemplate='%{y:,.1f}백만 원'
                ))

                fig_growth.add_trace(go.Scatter(
                    x=df_pr['x_axis'], y=df_pr['입금액 대비 수익률'], name='입금액 대비 수익률',
                    mode='lines+markers+text', line=dict(color='#F04452', width=3),
                    marker=dict(size=6, color='#F04452'),
                    text=df_pr['입금액 대비 수익률'].apply(lambda x: f"{x:.1f}%" if x != 0 else ""),
                    textposition='top center', textfont=dict(color='#FFFFFF', size=10, family='Pretendard'),
                    yaxis='y2', hovertemplate='%{y:.2f}%'
                ))

                fig_growth.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#FFFFFF', family='Pretendard'), barmode='stack',
                    hovermode='x unified', showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
                    xaxis=dict(title='', gridcolor='#161B24', showgrid=False, tickangle=-45, type='category'),
                    yaxis=dict(title='금액 (백만 원)', gridcolor='#161B24', showgrid=True, side='left', tickformat=',.0f'),
                    yaxis2=dict(title='수익률 (%)', side='right', overlaying='y', showgrid=False, ticksuffix='%'),
                    margin=dict(t=40, b=60, l=10, r=10)
                )
                st.plotly_chart(fig_growth, use_container_width=True)
            else:
                st.info(
                    "📊 '원금대비수익률' 시트 데이터를 불러오지 못했거나 테이블이 비어있습니다. Streamlit Cloud의 Secrets에 기입된 GID 정보를 다시 한 번 확인해 주세요.")

    # -------------------------------------------------------------------------
    # 5. 개별 계좌별 상세 내역 탭 리스트업 루프
    # -------------------------------------------------------------------------
    for i, acc in enumerate(final_account_order):
        with tabs[i + 1]:
            acc_df = portfolio[portfolio['계좌'] == acc]

            part_a = acc_df[(acc_df['보유수량'] > 0) | (acc_df['종류'] == 'ELS')].sort_values(by='수익률', ascending=False)
            part_b = acc_df[(acc_df['보유수량'] == 0) & (acc_df['종류'] != 'ELS')]

            # 계좌별 1단 데이터 연산
            acc_investment = part_a['총매입가'].sum()
            acc_evaluation = part_a['평가금액'].sum()
            acc_profit = acc_evaluation - acc_investment
            acc_rate = (acc_profit / acc_investment * 100) if acc_investment > 0 else 0

            # 계좌별 2단 신규 조건 연산 (필터링 자동 내장)
            acc_deposit = get_total_deposit(acc)
            acc_dividend = get_dividend_profit(acc, df)
            acc_dividend_rate = (acc_dividend / acc_deposit * 100) if acc_deposit > 0 else 0

            acc_net_profit = acc_profit + acc_dividend
            acc_net_rate = (acc_net_profit / acc_deposit * 100) if acc_deposit > 0 else 0

            if acc == 'ISA':
                st.markdown(
                    "<p style='color: #9EAAB8 !important; font-size: 13px; margin-bottom: -5px;'>💡 이 계좌는 현재 미사용 중이며, 과거 거래 내역 요약입니다.</p>",
                    unsafe_allow_html=True)

            # 개별 계좌 상세 탭 1단 카드
            st.markdown(f"""
            <div class="toss-summary-container" style="background-color: #171C26;">
                <div class="toss-summary-item"><div class="toss-summary-label">투자금액</div><div class="toss-summary-val">{acc_investment:,.0f}원</div></div>
                <div class="toss-summary-item" style="border-left: 1px solid #1C222E; border-right: 1px solid #1C222E;"><div class="toss-summary-label">평가금액</div><div class="toss-summary-val">{acc_evaluation:,.0f}원</div></div>
                <div class="toss-summary-item">
                    <div class="toss-summary-label">평가손익</div>
                    <div class="toss-summary-val {"trend-up" if acc_profit >= 0 else "trend-down"}">{"+" if acc_profit >= 0 else ""}{acc_profit:,.0f}원</div>
                    <div class="toss-summary-subval {"trend-up" if acc_profit >= 0 else "trend-down"}">({"+" if acc_profit >= 0 else ""}{acc_rate:.2f}%)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 개별 계좌 상세 탭 2단 카드 (배당수익 디자인 통일 적용)
            st.markdown(f"""
            <div class="toss-summary-container" style="background-color: #171C26; margin-top: -10px; margin-bottom: 25px;">
                <div class="toss-summary-item">
                    <div class="toss-summary-label">입금액</div>
                    <div class="toss-summary-val">{acc_deposit:,.0f}원</div>
                </div>
                <div class="toss-summary-item" style="border-left: 1px solid #1C222E; border-right: 1px solid #1C222E;">
                    <div class="toss-summary-label">배당수익</div>
                    <div class="toss-summary-val dividend-highlight">+{acc_dividend:,.0f}원</div>
                    <div class="toss-summary-subval dividend-highlight">({acc_dividend_rate:.2f}%)</div>
                </div>
                <div class="toss-summary-item">
                    <div class="toss-summary-label">총 손익</div>
                    <div class="toss-summary-val {"trend-up" if acc_net_profit >= 0 else "trend-down"}">{"+" if acc_net_profit >= 0 else ""}{acc_net_profit:,.0f}원</div>
                    <div class="toss-summary-subval {"trend-up" if acc_net_profit >= 0 else "trend-down"}">({"+" if acc_net_profit >= 0 else ""}{acc_net_rate:.2f}%)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("<h4 style='font-size: 16px; color:#CCD2DB; margin-top:5px;'>보유 종목</h4>",
                            unsafe_allow_html=True)
                if part_a.empty: st.caption("보유 종목이 없습니다.")
                for _, row in part_a.iterrows():
                    trend_class = "trend-up" if row['총수익'] >= 0 else "trend-down"
                    sign = "+" if row['총수익'] >= 0 else ""
                    qty_str = "계약 완료" if row['종류'] == 'ELS' and row['보유수량'] == 0 else f"{row['보유수량']:,}주"

                    st.markdown(f"""
                    <div class="toss-stock-row">
                        <div class="stock-left-box">
                            <span class="stock-main-name">{row['종목명']}</span>
                            <span class="stock-sub-qty">{qty_str}</span>
                        </div>
                        <div class="stock-right-box">
                            <span class="stock-main-price">{row['평가금액']:,.0f} 원</span>
                            <span class="stock-sub-qty {trend_class}">{sign}{row['총수익']:,.0f}원 ({sign}{row['수익률']:.2f}%)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_right:
                st.markdown("<h4 style='font-size: 16px; color:#CCD2DB; margin-top:5px;'>매도 종목</h4>",
                            unsafe_allow_html=True)
                if part_b.empty: st.caption("매도한 종목이 없습니다.")
                for _, row in part_b.iterrows():
                    trend_class = "trend-up" if row['총수익'] >= 0 else "trend-down" if row['총수익'] < 0 else "trend-none"
                    sign = "+" if row['총수익'] >= 0 else ""
                    st.markdown(f"""
                    <div class="toss-stock-row" style="opacity: 0.5;">
                        <div class="stock-left-box"><span class="stock-main-name">{row['종목명']}</span><span class="stock-sub-qty">0주</span></div>
                        <div class="stock-right-box">
                            <span class="stock-main-price">-</span>
                            <span class="stock-sub-qty {trend_class}">{sign}{row['총수익']:,.0f}원</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
else:
    st.info("📊 구글 시트로부터 매수일지 데이터를 가져오지 못했거나 내용이 비어있습니다.")