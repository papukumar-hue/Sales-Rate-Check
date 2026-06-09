import streamlit as st
import pandas as pd
from fpdf import FPDF
from streamlit_qrcode_scanner import qrcode_scanner
import os

# App Page Configurations
st.set_page_config(page_title="Store Scan & Print", page_icon="📦", layout="centered")
st.title("📦 Store Scan & POP Print App")
st.write("GitHub se live Excel data read ho raha hai.")

# 1. DATABASE MANAGEMENT (Automatic GitHub Fetch)
@st.cache_data(ttl=10) # Live updates ke liye data cache limits
def load_data_from_github():
    file_path = "Data.xlsx" 
    if os.path.exists(file_path):
        try:
            df_ean = pd.read_excel(file_path, sheet_name="EAN")
            df_ean.columns = [c.strip().lower() for c in df_ean.columns]
            
            df_stock = pd.read_excel(file_path, sheet_name="Stock And Rate")
            df_stock.columns = [c.strip().lower() for c in df_stock.columns]
            
            if 'item code' in df_ean.columns and 'eancode' in df_ean.columns and 'item code' in df_stock.columns:
                df_ean['item code'] = df_ean['item code'].astype(str).str.split('.').str.str.strip()
                df_ean['eancode'] = df_ean['eancode'].astype(str).str.split('.').str.str.strip()
                df_stock['item code'] = df_stock['item code'].astype(str).str.split('.').str.str.strip()
                
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

# Filter based on store
if 'outlet name' in inventory_data.columns:
    filtered_df = inventory_data[inventory_data['outlet name'] == selected_store]
else:
    filtered_df = inventory_data

st.sidebar.success(f"Connected to: {selected_store} ({len(filtered_df)} Items)")

# 3. ADVANCED TOGGLE SCAN BUTTON (Camera stays OFF until clicked)
st.subheader("📷 Barcode Scanner")

# State management to handle toggle opening and closing
if 'show_scanner' not in st.session_state:
    st.session_state.show_scanner = False

col1, col2 = st.columns([1, 2])
with col1:
    if st.button("📷 Open Camera Scanner", type="secondary"):
        st.session_state.show_scanner = True

scanned_input = None

# If user clicked open camera, display interactive live web-scanner
if st.session_state.show_scanner:
    with st.status("Scanning Active... Point at Barcode", expanded=True):
        # Professional Javascript engine wrapper component
        captured_code = qrcode_scanner(key="retail_barcode_scanner")
        if captured_code:
            scanned_input = str(captured_code).strip()
            st.session_state.show_scanner = False # Turn off camera immediately after successful scan
            st.rerun()
    if st.button("❌ Close Camera"):
        st.session_state.show_scanner = False
        st.rerun()

# Manual Input Backup box
manual_input = st.text_input("Yahan Barcode (Eancode) ya Item Code enter karein:", key="barcode_input")
if manual_input:
    scanned_input = manual_input.strip()

# 4. LOOKUP & DUAL RATE VERIFICATION
if scanned_input:
    search_value = scanned_input.strip()
    product_rows = filtered_df[(filtered_df['eancode'] == search_value) | (filtered_df['item code'] == search_value)]
    
    if not product_rows.empty:
        st.subheader("📋 Product Details Found")
        
        # Loop for handling multiple rates of same barcode seamlessly
        for index, row in product_rows.iterrows():
            item_name = str(row['item name']).title()
            selling_rate = float(row['selling'])
            mrp_rate = float(row['mrp']) if 'mrp' in filtered_df.columns else selling_rate
            current_stock = row['current stk.']
            item_code_val = row['item code']
            
            # Card UI
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #2ecc71; margin-bottom: 15px;">
                <h4 style="margin:0; color:#31333f;">📦 {item_name} (Code: {item_code_val})</h4>
                <p style="margin:5px 0; font-size:18px; color:#27ae60;"><b>Selling Price:</b> ₹{selling_rate}</p>
                <p style="margin:5px 0; font-size:14px; color:#7f8c8d;"><b>MRP:</b> ₹{mrp_rate} | <b>Stock:</b> {current_stock} Pcs</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Print logic tag
            with st.expander(f"🖨️ Print Label for Rate ₹{selling_rate}"):
                new_rate = st.number_input("Naya price enter karein:", value=selling_rate, step=1.0, key=f"input_{index}")
                
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
                    pdf.cell(0, 0.2, txt=f"MRP: Rs.{int(mrp_rate)} (Save Rs.{int(mrp_rate - new_rate)})", ln=1, align="C")
                        
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
        st.error(f"❌ '{search_value}' is selected store ({selected_store}) ke database me nahi mila!")
