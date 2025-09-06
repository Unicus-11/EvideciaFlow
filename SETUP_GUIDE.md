# EvideciaFlow Frontend-Backend Connection Setup Guide

## Issues Fixed ✅

1. **Frontend using Genkit AI directly** → Now uses Flask backend APIs
2. **Missing API client configuration** → Created comprehensive API client
3. **Missing API endpoints** → Added document structure and sequence validation endpoints
4. **CORS configuration issues** → Properly configured CORS for frontend domains
5. **Response format mismatches** → Fixed AI Manager response parsing
6. **No environment configuration** → Added Next.js environment configuration

## Quick Start

### 1. Start the Backend
```bash
python app.py
```
The backend will start on `http://localhost:5000`

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```
The frontend will start on `http://localhost:3000`

### 3. Test the Connection
```bash
# Test backend APIs
python test_connection.py

# Or open the web test interface
open frontend/test-api.html
```

## What Was Fixed

### Backend Changes
- ✅ Added `/api/extract-document-structure` endpoint
- ✅ Added `/api/check-section-sequence` endpoint  
- ✅ Improved CORS configuration for frontend domains
- ✅ Enhanced AI Manager with new handlers
- ✅ Better JSON response parsing with fallbacks

### Frontend Changes
- ✅ Created API client (`frontend/src/lib/api.ts`)
- ✅ Updated document analyzer to use backend APIs
- ✅ Added environment configuration
- ✅ Removed direct Genkit AI dependencies

### New Files Created
- `frontend/src/lib/api.ts` - API client for backend communication
- `frontend/test-api.html` - Web-based API test interface
- `test_connection.py` - Python script to test backend APIs
- `start_servers.bat` / `start_servers.sh` - Startup scripts

## API Endpoints

### Document Structure Extraction
- **POST** `/api/extract-document-structure`
- **Body**: `{"documentText": "your document text"}`
- **Response**: `{"sections": [{"title": "...", "content": "...", "type": "..."}]}`

### Section Sequence Validation
- **POST** `/api/check-section-sequence`
- **Body**: `{"sections": ["Title", "Abstract", "Introduction"]}`
- **Response**: `[{"section": "...", "isCorrectSequence": true/false}]`

### Health Check
- **GET** `/api/health`
- **Response**: Backend status and available features

## Troubleshooting

### Backend Issues
- Check if Flask server is running on port 5000
- Verify AI Manager components are initialized
- Check logs for any import errors

### Frontend Issues
- Ensure Next.js is running on port 3000
- Check browser console for CORS errors
- Verify API client is properly imported

### Connection Issues
- Run `python test_connection.py` to diagnose backend
- Open `frontend/test-api.html` to test from browser
- Check network tab in browser dev tools

## Development Workflow

1. Start backend: `python app.py`
2. Start frontend: `cd frontend && npm run dev`
3. Test connection: `python test_connection.py`
4. Open frontend: `http://localhost:3000`
5. Use document analyzer to test full workflow

## Next Steps

- Add error handling and loading states
- Implement user authentication
- Add more AI features through backend APIs
- Deploy to production environment
