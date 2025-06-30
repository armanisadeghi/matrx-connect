#!/usr/bin/env python3
"""
HTML Extractor Chrome Extension - Python Socket.IO Server Example
This is a sample server to demonstrate real-time communication with the Chrome extension.
"""

import socketio
import eventlet
from flask import Flask
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Create Flask app and Socket.IO instance
app = Flask(__name__)
sio = socketio.Server(cors_allowed_origins="*")
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Store connected clients
connected_clients = {}

@app.route('/')
def index():
    return '''
    <h1>HTML Extractor Socket.IO Server</h1>
    <p>Server is running! Extension can connect to this server.</p>
    <p>Connected clients: {}</p>
    '''.format(len(connected_clients))

@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")
    connected_clients[sid] = {
        'connected_at': datetime.now().isoformat(),
        'extractions': 0
    }

    # Send welcome message
    sio.emit('server_message', {
        'message': 'Welcome to HTML Extractor Server!',
        'timestamp': datetime.now().isoformat()
    }, to=sid)

@sio.event
def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in connected_clients:
        del connected_clients[sid]

@sio.event
def client_connected(sid, data):
    """Handle client connection info"""
    print(f"Extension client info: {data}")
    if sid in connected_clients:
        connected_clients[sid].update(data)

@sio.event
def html_extraction(sid, data):
    """Handle HTML extraction event from extension"""
    print(f"📄 HTML Extraction received from {sid}")
    print(f"   URL: {data.get('url')}")
    print(f"   Title: {data.get('title')}")
    print(f"   Content Length: {data.get('content_length')} characters")
    print(f"   User: {data.get('user_id')}")

    # Update client stats
    if sid in connected_clients:
        connected_clients[sid]['extractions'] += 1

    # Process the HTML with BeautifulSoup
    try:
        soup = BeautifulSoup(data.get('html_content', ''), 'html.parser')

        # Extract useful information
        analysis = {
            'url': data.get('url'),
            'title': data.get('title'),
            'word_count': len(soup.get_text().split()),
            'link_count': len(soup.find_all('a')),
            'image_count': len(soup.find_all('img')),
            'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'form_count': len(soup.find_all('form')),
            'processed_at': datetime.now().isoformat()
        }

        # Extract all headings
        headings = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            headings.append({
                'level': heading.name,
                'text': heading.get_text().strip()[:100]  # Limit length
            })
        analysis['headings'] = headings[:10]  # Limit to first 10

        # Extract all links
        links = []
        for link in soup.find_all('a', href=True):
            links.append({
                'url': link['href'],
                'text': link.get_text().strip()[:50]  # Limit length
            })
        analysis['links'] = links[:20]  # Limit to first 20

        print(f"   Analysis: {analysis['word_count']} words, {analysis['link_count']} links, {analysis['image_count']} images")

        # Send processing confirmation back to extension
        sio.emit('html_extraction_processed', {
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }, to=sid)

        # Send detailed analysis after a short delay (simulating processing time)
        sio.start_background_task(send_analysis_complete, sid, analysis)

    except Exception as e:
        print(f"❌ Error processing HTML: {e}")
        sio.emit('html_extraction_processed', {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, to=sid)

@sio.event
def extraction_saved(sid, data):
    """Handle confirmation that extraction was saved to Supabase"""
    print(f"💾 Extraction saved to Supabase:")
    print(f"   ID: {data.get('supabase', {}).get('id')}")
    print(f"   URL: {data.get('extraction', {}).get('url')}")

@sio.event
def extraction_error(sid, data):
    """Handle extraction errors"""
    print(f"❌ Extraction error from {sid}:")
    print(f"   Error: {data.get('error')}")
    print(f"   URL: {data.get('url')}")

def send_analysis_complete(sid, analysis):
    """Background task to send analysis complete after delay"""
    sio.sleep(2)  # Simulate processing time

    sio.emit('extraction_analysis_complete', {
        'analysis': analysis,
        'message': 'Deep analysis complete! Check your dashboard for insights.',
        'timestamp': datetime.now().isoformat()
    }, to=sid)

if __name__ == '__main__':
    print("🚀 Starting HTML Extractor Socket.IO Server...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔧 Make sure your Chrome extension is configured to use this URL")
    print("-" * 60)

    try:
        eventlet.wsgi.server(eventlet.listen(('localhost', 5000)), app)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

"""
To run this server:

1. Install dependencies:
   pip install python-socketio[client] eventlet flask beautifulsoup4

2. Run the server:
   python python-server-example.py

3. Configure your Chrome extension to use: http://localhost:5000

4. Test the connection in the extension settings

Features of this server:
- Receives HTML extractions from the extension
- Processes HTML with BeautifulSoup
- Extracts metadata (word count, links, images, headings)
- Sends real-time responses back to extension
- Shows notifications in the browser when processing is complete
- Tracks connected clients and extraction statistics

Events the server handles:
- client_connected: Extension connection info
- html_extraction: Main HTML extraction event
- extraction_saved: Confirmation of Supabase save
- extraction_error: Error handling

Events the server sends:
- server_message: General messages
- html_extraction_processed: Processing confirmation
- extraction_analysis_complete: Detailed analysis results
"""
