import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import streamlit.components.v1 as components

# App Page Configurations
st.set_page_config(page_title="Store Scan & Print", page_icon="📦", layout="centered")
st.title("📦 Store Scan & POP Print App")
st.write("GitHub se live Excel data read ho raha hai.")

# 1. DATABASE MANAGEMENT (Automatic GitHub Fetch)
@st.cache_data(ttl=10)
def load_data_from_github():
    file_path = "Data.xlsx"
    if os.path.exists(file_path):
        try:
            df_ean = pd.read_excel(file_path, sheet_name="EAN")
            df_ean.columns = [c.strip().lower() for c in df_ean.columns]

            df_stock = pd.read_excel(file_path, sheet_name="Stock And Rate")
            df_stock.columns = [c.strip().lower() for c in df_stock.columns]

            if 'item code' in df_ean.columns and 'eancode' in df_ean.columns and 'item code' in df_stock.columns:
                df_ean['item code'] = df_ean['item code'].astype(str).str.strip()
                df_ean['eancode'] = df_ean['eancode'].astype(str).str.strip()
                df_stock['item code'] = df_stock['item code'].astype(str).str.strip()

                df_final = pd.merge(df_stock, df_ean[['item code', 'eancode']], on='item code', how='left')
                return df_final
            else:
                st.error("❌ Excel columns match nahi ho rahe! Columns check karein.")
                return None
        except Exception as e:
            st.error(f"❌ Excel read karne me galti: {e}")
            return None
    else:
        st.error(f"❌ Repository me '{file_path}' file nahi mili!")
        return None

inventory_data = load_data_from_github()

if inventory_data is None:
    st.stop()

# 2. STORE SELECTION FEATURE
st.sidebar.header("🏪 Store Settings")
if 'outlet name' in inventory_data.columns:
    unique_stores = inventory_data['outlet name'].dropna().unique().tolist()
else:
    unique_stores = ["All Stores"]

selected_store = st.sidebar.selectbox("Apna Store Chunein:", unique_stores)

if 'outlet name' in inventory_data.columns:
    filtered_df = inventory_data[inventory_data['outlet name'] == selected_store]
else:
    filtered_df = inventory_data

st.sidebar.success(f"Connected to: {selected_store} ({len(filtered_df)} Items)")

# 3. REAL LIVE BARCODE AUTO-SCANNER
# FIX: Use query_params to pass scanned value from JS → Python via URL param,
# then trigger st.rerun(). This is the correct pattern for components.html.
st.subheader("📷 Live Barcode Auto-Scanner")

# Read scanned value injected by JS via URL query param
params = st.query_params
js_scanned = params.get("scanned", "")

# Clear the query param after reading so it doesn't persist across reruns
if js_scanned:
    st.query_params.clear()

# FIX: Correct unpkg URL for html5-qrcode library
scanner_html = """
<div style="width:100%; max-width:500px; margin:auto; text-align:center; font-family:sans-serif;">
    <div id="reader" style="width:100%; border-radius:10px; overflow:hidden; background:#f0f2f6;"></div>
    <div id="result" style="margin-top:10px; font-weight:bold; color:#2ecc71; font-size:16px;"></div>
</div>

<!-- FIX: Correct CDN path for html5-qrcode -->
<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
<script>
    function onScanSuccess(decodedText) {
        document.getElementById('result').innerText = "✅ Scanned: " + decodedText;

        // FIX: Correct JS→Streamlit bridge — update URL query param and reload
        // Streamlit will pick up ?scanned=VALUE on the next Python run
        const url = new URL(window.parent.location.href);
        url.searchParams.set('scanned', decodedText);
        window.parent.location.href = url.toString();
    }

    function onScanFailure(error) {
        // Silent — avoids cluttering the UI
    }

    let html5QrcodeScanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: { width: 250, height: 150 }, rememberLastUsedCamera: true },
        false
    );
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
</script>
"""

with st.container():
    components.html(scanner_html, height=380, scrolling=False)

# Manual / gun scanner input
manual_input = st.text_input(
    "Yahan Barcode scan karein ya manually enter karein:",
    value=js_scanned,  # Pre-fill with camera scan result if available
    key="barcode_input"
)

# Final lookup key: prefer manual input (user can edit), fallback to camera scan
scanned_input = manual_input.strip() if manual_input.strip() else js_scanned.strip()

# 4. LOOKUP & DUAL RATE VERIFICATION
if scanned_input:
    search_value = str(scanned_input).strip()
    product_rows = filtered_df[
        (filtered_df['eancode'] == search_value) |
        (filtered_df['item code'] == search_value)
    ]

    if not product_rows.empty:
        st.subheader("📋 Product Details Found")

        for index, row in product_rows.iterrows():
            item_name = str(row['item name']).title()
            selling_rate = float(row['selling'])
            mrp_rate = float(row['mrp']) if 'mrp' in filtered_df.columns else selling_rate
            current_stock = row['current stk.']
            item_code_val = row['item code']

            # FIX: Show savings only when MRP > selling price
            savings = mrp_rate - selling_rate
            savings_text = f"Save ₹{int(savings)}" if savings > 0 else "No Discount"

            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:15px; border-radius:10px;
                        border-left:5px solid #2ecc71; margin-bottom:15px;">
                <h4 style="margin:0; color:#31333f;">📦 {item_name} (Code: {item_code_val})</h4>
                <p style="margin:5px 0; font-size:18px; color:#27ae60;">
                    <b>Selling Price:</b> ₹{selling_rate}
                </p>
                <p style="margin:5px 0; font-size:14px; color:#7f8c8d;">
                    <b>MRP:</b> ₹{mrp_rate} &nbsp;|&nbsp;
                    <b>Stock:</b> {current_stock} Pcs &nbsp;|&nbsp;
                    {savings_text}
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🖨️ Print Label for Rate ₹{selling_rate}"):
                new_rate = st.number_input(
                    "Naya price enter karein (optional):",
                    value=selling_rate,
                    step=1.0,
                    key=f"input_{index}"
                )

                if st.button("Generate POP PDF", key=f"btn_{index}", type="primary"):
                    pdf = FPDF(orientation="L", unit="in", format=(3.0, 2.0))
                    pdf.add_page()
                    pdf.set_margins(0.1, 0.1, 0.1)
                    pdf.rect(0.05, 0.05, 2.9, 1.9)

                    pdf.set_font("Helvetica", style="B", size=11)
                    pdf.cell(0, 0.3, txt=item_name[:25], ln=1, align="C")
                    pdf.ln(0.05)

                    pdf.set_font("Helvetica", style="B", size=28)
                    pdf.set_text_color(231, 76, 60)
                    pdf.cell(0, 0.5, txt=f"Rs. {int(new_rate)}/-", ln=1, align="C")
                    pdf.set_text_color(0, 0, 0)

                    pdf.set_font("Helvetica", size=8)
                    pdf.cell(0, 0.2, txt=f"Item Code: {item_code_val}", ln=1, align="C")

                    # FIX: Only show savings line when there's an actual discount
                    label_savings = int(mrp_rate - new_rate)
                    if label_savings > 0:
                        pdf.cell(
                            0, 0.2,
                            txt=f"MRP: Rs.{int(mrp_rate)} (Save Rs.{label_savings})",
                            ln=1, align="C"
                        )
                    else:
                        pdf.cell(0, 0.2, txt=f"MRP: Rs.{int(mrp_rate)}", ln=1, align="C")

                    pdf_bytes = pdf.output()

                    st.download_button(
                        label="📥 Download & Print Label",
                        data=bytes(pdf_bytes),
                        file_name=f"POP_{item_code_val}_{int(new_rate)}.pdf",
                        mime="application/pdf",
                        key=f"dl_{index}"
                    )
                    st.balloons()
    else:
        st.error(
            f"❌ '{search_value}' is selected store ({selected_store}) ke database me nahi mila!"
        )