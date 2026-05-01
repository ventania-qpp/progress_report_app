import streamlit as st
import pandas as pd
import zipfile
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

st.title("Progress Report Generator (CSV版)")

# CSV アップロード
uploaded = st.file_uploader("Upload the CSV file you downloaded from AppSheet")

if uploaded is None:
    st.info("Upload a CSV file to get started.")
    st.stop()

# CSV 読み込み
df = pd.read_csv(uploaded)

# ソート方法
sort_option = st.selectbox(
    "Sort students by",
    ["Name", "Corda", "Age"]
)

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

# 生徒選択
selected_students = st.multiselect(
    "Select students (multiple allowed)",
    df["Display_Name"].tolist()
)

# session_state 初期化
if "downloaded" not in st.session_state:
    st.session_state["downloaded"] = set()

# PDF生成
if st.button("Create PDF"):

    st.session_state["pdfs"] = {}
    st.session_state["downloaded"] = set()

    # Period
    if selected_students:
        first_student = df[df["Display_Name"] == selected_students[0]].iloc[0].to_dict()
        period_raw = str(first_student["Period"])
        period_dt = datetime.strptime(period_raw, "%Y/%m/%d")
        period_str = period_dt.strftime("%Y%m%d")
        st.session_state["period_str"] = period_str
    else:
        st.session_state["period_str"] = "00000000"

    with st.spinner("Generating PDFs..."):

        for name in selected_students:

            student = df[df["Display_Name"] == name].iloc[0].to_dict()

            # Age 処理
            if pd.isna(student["Age"]):
                student["Age"] = ""
            else:
                student["Age"] = int(student["Age"])
                if student["Age"] >= 30:
                    student["Age"] = ""

            # Corda
            corda = student["Corda_Name_EN"].strip()
            if corda not in Corda_Name_EN_order:
                corda = "Gray"

            student["Corda_Name_EN"] = corda

            # -----------------------------
            # PNG テンプレートに文字を書き込む
            # -----------------------------
            base = Image.open("template.png").convert("RGB")
            draw = ImageDraw.Draw(base)

            # フォント（Streamlit Cloud では DejaVu が使える）
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)

            # 例：名前・Corda・Age を配置（座標は調整してね）
            draw.text((200, 300), f"Name: {student['Display_Name']}", fill="black", font=font)
            draw.text((200, 400), f"Corda: {student['Corda_Name_EN']}", fill="black", font=font)
            draw.text((200, 500), f"Age: {student['Age']}", fill="black", font=font)

            # PNG を一時保存
            base.save("temp_output.png")

            # -----------------------------
            # PNG → PDF
            # -----------------------------
            pdf = FPDF()
            pdf.add_page()
            pdf.image("temp_output.png", x=0, y=0, w=210, h=297)  # A4 サイズ

            pdf.output("report.pdf")

            with open("report.pdf", "rb") as f:
                pdf_bytes = f.read()

            st.session_state["pdfs"][name] = pdf_bytes

    st.success("PDF generation completed!")

# ダウンロード画面
if "pdfs" in st.session_state:
    count = len(st.session_state["pdfs"])
    st.subheader(f"PDF Download （{count} selected）")

    period_str = st.session_state.get("period_str", "00000000")

    # ZIP
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

    # 個別
    else:
        for name in list(st.session_state["pdfs"].keys()):

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

    st.markdown("---")
    if st.button("CLEAR"):
        if "pdfs" in st.session_state:
            del st.session_state["pdfs"]
        if "downloaded" in st.session_state:
            del st.session_state["downloaded"]
        st.rerun()
