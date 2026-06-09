import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# App Page Configurations
st.set_page_config(page_title="Store Scan & Print", page_icon="📦", layout="centered")
st.title("📦 Store Scan & POP Print App")
st.write("GitHub se live Excel data automatic read ho raha hai.")

# 1. DATABASE MANAGEMENT (Automatic GitHub Fetch)
@st.cache_data(ttl=60) # Har 1 minute me data refresh hoga agar GitHub par badla to
def load_data_from_github():
    file_path = "data.xlsx" # GitHub par isi naam se file honi chahiye
    if os.path.exists(file_path):
        try:
            # 1. Read EAN Sheet
            df_ean = pd.read_excel(file_path, sheet_name="EAN")
            df_ean.columns = [c.strip().lower() for c in df_ean.columns]
            
            # 2. Read Stock And Rate Sheet
            df_stock = pd.read_excel(file_path, sheet_name="Stock And Rate")
            df_stock.columns = [c.strip().lower() for c in df_stock.columns]
            
            # Data Cleaning
            df_ean['item code'] = df_ean['item code'].astype(str).str.split('.').str[0].str.strip()
            df_ean['eancode'] = df_ean['eancode'].astype(str).str.split('.').str[0].str.strip()
            df_stock['item code'] = df_stock['item code'].astype(str).str.split('.').str[0].str.strip()
            
            # Merge both sheets
            df_final = pd.merge(df_stock, df_ean[['item code', 'eancode']], on='item code', how='left')
            return df_final
        except Exception as e:
            st.error(f"❌ Excel sheets read karne me galti hui: {e}")
            return None
    else:
        st.error("❌ Repository me 'data.xlsx' file nahi mili! Kripya sahi naam se upload karein.")
        return None

# Auto Load Data
inventory_data = load_data_from_github()

if inventory_data is None:
    st.stop()
else:
    st.success(f"✅ Data Loaded from GitHub! Total Items: {len(inventory_data)}")

# 2. SCANNING SECTION
st.subheader("📷 Scan/Capture Product Barcode")
image = st.camera_input("Take a picture of the barcode")

# Manual Input Box (Accepts both Barcode/Eancode OR Item Code)
scanned_input = st.text_input("Yahan Barcode (Eancode) scan karein ya Item Code enter karein:", key="barcode_input")

# 3. LOOKUP & VERIFICATION SECTION
if scanned_input:
    search_value = scanned_input.strip()
    df = inventory_data
    
    # Search in 'eancode' column OR 'item code' column
    product_row = df[(df['eancode'] == search_value) | (df['item code'] == search_value)]
    
    if not product_row.empty:
        # Fetching data
        item_name = str(product_row['item name'].values[0]).title()
        selling_rate = float(product_row['selling'].values[0])
        mrp_rate = float(product_row['mrp'].values[0]) if 'mrp' in df.columns else selling_rate
        current_stock = product_row['current stk.'].values[0]
        item_code_val = product_row['item code'].values[0]
        
        # Display Product Details Card
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #2ecc71; margin-bottom: 20px;">
            <h3 style="margin:0; color:#31333f;">📋 {item_name}</h3>
            <p style="margin:5px 0; font-size:15px; color:#7f8c8d;"><b>Item Code:</b> {item_code_val}</p>
            <p style="margin:5px 0; font-size:18px; color:#27ae60;"><b>Selling Price:</b> ₹{selling_rate}</p>
            <p style="margin:5px 0; font-size:15px; color:#7f8c8d;"><b>MRP:</b> ₹{mrp_rate}</p>
            <p style="margin:5px 0; font-size:16px; color:#34495e;"><b>Current Stock:</b> {current_stock} Pcs</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. WRONG PRICE & PDF GENERATION
        st.subheader("🖨️ Price Tag (POP) Generator")
        new_rate = st.number_input("Agar shelf par rate galat hai, toh naya rate enter karein:", value=selling_rate, step=1.0)
        
        if st.button("Generate POP PDF", type="primary"):
            pdf = FPDF(orientation="L", unit="in", format=(3.0, 2.0))
            pdf.add_page()
            pdf.set_margins(0.1, 0.1, 0.1)
            pdf.rect(0.05, 0.05, 2.9, 1.9)
            
            # Item Name
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 0.3, txt=item_name[:28], ln=1, align="C")
            pdf.ln(0.05)
            
            # Big Bold Price
            pdf.set_font("Helvetica", style="B", size=30)
            pdf.set_text_color(231, 76, 60)
            pdf.cell(0, 0.5, txt=f"Rs. {int(new_rate)}/-", ln=1, align="C")
            pdf.set_text_color(0, 0, 0)
            
            # Bottom Details
            pdf.set_font("Helvetica", size=8)
            pdf.cell(0, 0.2, txt=f"Item Code: {item_code_val}", ln=1, align="C")
            pdf.cell(0, 0.2, txt=f"MRP: Rs.{int(mrp_rate)} (Save Rs.{int(mrp_rate - new_rate)})", ln=1, align="C")
                
            pdf_bytes = pdf.output()
            
            st.download_button(
                label="📥 Download & Print Label",
                data=bytes(pdf_bytes),
                file_name=f"POP_{item_code_val}.pdf",
                mime="application/pdf"
            )
            st.balloons()
            st.info("PDF download karke apne thermal printer se sticker nikal lein.")
    else:
        st.error(f"❌ '{search_value}' database me nahi mila!")
