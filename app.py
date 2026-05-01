import streamlit as st
import pandas as pd
from weasyprint import HTML
import zipfile
import io
from datetime import datetime

st.title("Progress Report Generator (CSV版)")

#df = pd.read_csv("Point_Student.csv")
# CSV アップロード
uploaded = st.file_uploader("Upload the CSV file you downloaded from AppSheet")

if uploaded is None:
    st.info("Upload a CSV file to get started.")
    st.stop()

# CSV 読み込み
df = pd.read_csv(uploaded)


# 選択リストソート方法
sort_option = st.selectbox(
    "Sort students by",
    ["Name", "Corda", "Age"]
)

# Corda の順序リスト（Machiko さんのアプリと同じ）
Corda_Name_EN_order = [
    "Gray", "Gray/Green", "Green", "Gray/Yellow",
    "Yellow", "Gray/Blue", "Blue", "Green/Yellow", "Advanced+"
]

if sort_option == "Name":
    df = df.sort_values("Display_Name")
elif sort_option == "Corda":
    df["Corda_Order"] = df["Corda_Name_EN"].apply(
        lambda x: Corda_Name_EN_order.index(x) if x in Corda_Name_EN_order else 0
    )
    df = df.sort_values("Corda_Order")
elif sort_option == "Age":
    df = df.sort_values("Age", na_position="last")


# 生徒選択（複数）
selected_students = st.multiselect(
    "Select students (multiple allowed)",
    df["Display_Name"].tolist()
)

# ダウンロード済みの記録
if "downloaded" not in st.session_state:
    st.session_state["downloaded"] = set()

# PDF生成ボタン
if st.button("Create PDF"):

    st.session_state["pdfs"] = {}
    st.session_state["downloaded"] = set()  # リセット

    # Period 処理 最初の生徒の Period を使用して period_str作成
    if selected_students:
        first_student = df[df["Display_Name"] == selected_students[0]].iloc[0].to_dict()
        period_raw = str(first_student["Period"])          # "2026/4/30"
        period_dt = datetime.strptime(period_raw, "%Y/%m/%d")
        period_str = period_dt.strftime("%Y%m%d")          # "20260430"
        st.session_state["period_str"] = period_str        # ← 追加
    else:
        st.session_state["period_str"] = "00000000"

    with st.spinner("Generating PDFs..."): 
        for name in selected_students:
            # 生徒データ取得
            student = df[df["Display_Name"] == name].iloc[0].to_dict()

            # Age 処理
            if pd.isna(student["Age"]):
                student["Age"] = ""
            else:
                student["Age"] = int(student["Age"])
                if student["Age"] >= 30:
                    student["Age"] = ""

            corda = student["Corda_Name_EN"].strip()
            if corda not in Corda_Name_EN_order:
                corda = "Gray"

            student["Corda_Name_EN"] = corda
            student["Corda_Name_ENLower"] = (
                corda.lower()
                    .replace("/", "-")
                    .replace("+", "-plus")
            )

            corda_pos_map = {
                "Gray": 0,
                "Gray/Green": 12.5,
                "Green": 25,
                "Gray/Yellow": 37.5,
                "Yellow": 50,
                "Gray/Blue": 65,
                "Blue": 80,
                "Green/Yellow": 90,
                "Advanced+": 98
            }
            student["Corda_Name_ENPos"] = corda_pos_map.get(corda, 0)

            # HTMLテンプレート読み込み
            with open("template.html", "r", encoding="utf-8") as f:
                html = f.read()

            # 置換
            for key, value in student.items():
                html = html.replace("{" + key + "}", str(value))

            # PDF生成
            pdf_bytes = HTML(string=html).write_pdf()

            # session_state に保存
            st.session_state["pdfs"][name] = pdf_bytes

    st.success("PDF generation completed!")


# 以下、rerun 後でも残る処理
if "pdfs" in st.session_state:
    count = len(st.session_state["pdfs"])
    st.subheader(f"PDF Download （{count} selected）")

    period_str = st.session_state.get("period_str", "00000000")
    # -----------------------------
    # ① 人数が多いときは ZIP を表示
    # -----------------------------
    if count >= 10:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for name, pdf_bytes in st.session_state["pdfs"].items():
                zipf.writestr(f"{name}_{period_str}.pdf", pdf_bytes)

        st.download_button(
            label="Download all PDFs as ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"ProgressReports_{period_str}.zip",
            mime="application/zip"
        )

    # -----------------------------
    # ② 人数が少ないときは個別ボタン
    # -----------------------------
    else:
        for name in list(st.session_state["pdfs"].keys()):

            # ダウンロード済みなら非表示
            if name in st.session_state["downloaded"]:
                continue

            pdf_bytes = st.session_state["pdfs"][name]

            clicked = st.download_button(
                label=f"{name} Download",
                data=pdf_bytes,
                file_name=f"{name}_{period_str}.pdf",
                mime="application/pdf"
            )

            if clicked:
                st.session_state["downloaded"].add(name)
                st.rerun()

    # -----------------------------
    # クリアボタン
    # -----------------------------
    st.markdown("---")
    if st.button("CLEAR"):
        if "pdfs" in st.session_state:
            del st.session_state["pdfs"]
        if "downloaded" in st.session_state:
            del st.session_state["downloaded"]
        st.rerun()
