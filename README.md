# Document AI Demo

SAP Business Document Processing with AI extraction for invoices, receipts, and purchase orders.

## Features

- 📄 **Multi-document upload** with drag & drop
- 🔄 **Image rotation** for scanned documents
- 📊 **Confidence scores** with color-coded badges
- 📋 **Multiple document types**: Invoice, Receipt, Purchase Order
- 💾 **Processing history** saved locally
- 📥 **Excel/CSV export**
- 🔐 **User authentication** (login/signup)

## Quick Start

```bash
# Install Python dependencies
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Build frontend
cd webapp
npm install
npm run build
cd ..

# Run server
python app.py
```

Open http://localhost:5000

## Environment Variables

Create a `.env` file:

```env
# SAP Document AI
DOX_URL=your_sap_url
DOX_CLIENT_ID=your_client_id
DOX_CLIENT_SECRET=your_client_secret
DOX_UAADOMAIN=your_uaa_domain

# MongoDB (optional)
MONGODB_URI=mongodb+srv://...
```

## Tech Stack

- **Backend**: Flask, Python
- **Frontend**: Vanilla JS, Vite
- **AI**: SAP Document Information Extraction
- **Auth**: JWT / MongoDB
