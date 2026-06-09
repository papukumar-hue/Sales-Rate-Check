import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from streamlit_camera_input_live import camera_input_live
import io

# App Page Configurations
st.set_page_config(page_title="Store Scan & Print", page_icon="📦", layout="centered")
st.title("📦 Store Scan & POP Print App")
st.write("Subah Excel upload karein aur mobile se scan karke rate check karein.")

# 1. DATABASE MANAGEMENT (Session State to persist data across actions)
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = None

# Admin Panel: Excel Upload (Keep expanded on PC, collapsed on Mobile)
with st.sidebar.expander("⚙️ Admin: Upload Morning Excel", expanded=True):
    uploaded_file = st.file_uploader("Excel file (.xlsx ya .csv) upload karein", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Standardizing column names to match code logic
            df.columns = [c.strip().lower() for c in df.columns]
            required_cols = ['barcode', 'item_name', 'rate', 'stock']
            
            if all(col in df.columns for col in required_cols):
                # Convert barcode to string for easier matching
                df['barcode'] = df['barcode'].astype(str).str.split('.').str[0]
                st.session_state.inventory_data = df
                st.success(f"Successfully Loaded! Total Items: {len(df)}")
            else:
                st.error("Excel columns sahi nahi hain! Columns hone chahiye: Barcode, Item_Name, Rate, Stock")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# If database is not uploaded yet
if st.session_state.inventory_data is None:
    st.info("⚠️ Kripya pehle sidebar me subah ki Excel file upload karein.")
    st.stop()

# 2. SCANNING SECTION
st.subheader("📷 Scan Product Barcode")
image = camera_input_live(debounce=1000)

scanned_barcode = None

if image:
    # Convert captured image to PIL format for processing
    pil_image = Image.open(io.BytesIO(image.read()))
    # Decode barcode using pyzbar library
    decoded_objects = decode(pil_image)
    
    if decoded_objects:
        scanned_barcode = decoded_objects[0].data.decode('utf-8')
        st.success(f"✅ Barcode Scanned: {scanned_barcode}")
    else:
        st.warning("🔍 Camera ke samne barcode layein (Clear and close up)...")

# Manual Input Backup (In case camera fails or low light)
manual_barcode = st.text_input("या manual barcode enter karein:")
if manual_barcode:
    scanned_barcode = manual_barcode.strip()

# 3. LOOKUP & VERIFICATION SECTION
if scanned_barcode:
    df = st.session_state.inventory_data
    # Search barcode in dataframe
    product_row = df[df['barcode'] == str(scanned_barcode)]
    
    if not product_row.empty:
        item_name = product_row['item_name'].values[0].title()
        system_rate = float(product_row['rate'].values[0])
        current_stock = product_row['stock'].values[0]
        
        # Display Product Details Card
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;">
            <h3 style="margin:0; color:#31333f;">📋 {item_name}</h3>
            <p style="margin:5px 0; font-size:18px;"><b>System Rate:</b> ₹{system_rate}</p>
            <p style="margin:5px 0; font-size:16px; color:#555;"><b>Current Stock:</b> {current_stock} Units</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. WRONG PRICE & PDF GENERATION
        st.subheader("🖨️ Price Tag (POP) Generator")
        new_rate = st.number_input("Agar shelf par rate galat hai, toh naya rate enter karein:", value=system_rate, step=1.0)
        
        if st.button("Generate POP PDF", type="primary"):
            # PDF Creation logic (3x2 inch format for thermal printers)
            pdf = FPDF(orientation="L", unit="in", format=[3, 2])
            pdf.add_page()
            pdf.set_margins(0.1, 0.1, 0.1)
            
            # Clean layout border
            pdf.rect(0.05, 0.05, 2.9, 1.9)
            
            # Print Item Name
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(0, 0.3, txt=item_name, ln=1, align="C")
            pdf.ln(0.1)
            
            # Print New Big Bold Price
            pdf.set_font("Helvetica", style="B", size=32)
            pdf.set_text_color(255, 0, 0) # Red Text
            pdf.cell(0, 0.6, txt=f"Rs. {int(new_rate)}/-", ln=1, align="C")
            pdf.set_text_color(0, 0, 0) # Back to Black
            
            # Print Subtext / Barcode label below
            pdf.set_font("Helvetica", size=9)
            pdf.cell(0, 0.2, txt=f"Code: {scanned_barcode}", ln=1, align="C")
            pdf.cell(0, 0.2, txt="*Verified Quality Store*", ln=1, align="C")
            
            # Output PDF data as bytes
            pdf_bytes = pdf.output()
            
            # Streamlit Download Button for PDF
            st.download_button(
                label="📥 Download & Print Label",
                data=bytes(pdf_bytes),
                file_name=f"POP_{scanned_barcode}.pdf",
                mime="application/pdf"
            )
            st.balloons()
            st.info("Download karne ke baad ise 'RawBT' ya 'EscPos Print' app ke sath Bluetooth printer par bhej dein.")
    else:
        st.error(f"❌ Product Code '{scanned_barcode}' Excel database me nahi mila!")
