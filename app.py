
import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import hashlib
import json
from typing import Dict, List, Tuple
import sqlite3  # Using SQLite for local demo; replace with MySQL for production

# Simulated database setup
def init_db():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            issue_description TEXT,
            created_at TIMESTAMP,
            severity TEXT,
            status TEXT,
            product_id TEXT,
            resolution TEXT  -- Added resolution column
        )
    ''')  # Added closing triple quotes here
    c.execute('''
        CREATE TABLE conversations (
            issue_id INTEGER,
            message TEXT,
            sender TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        )
    ''')
    # Sample data with resolution
    c.executemany('''
        INSERT INTO issues (customer_id, issue_description, created_at, severity, status, product_id, resolution)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
        ('CUST001', 'Login failure', '2025-07-11 10:00:00', 'High', 'Open', 'PROD001', None),
        ('CUST001', 'Payment issue', '2025-07-12 08:00:00', 'Normal', 'Open', 'PROD002', None),
        ('CUST002', 'UI glitch', '2025-07-10 15:00:00', 'Low', 'Resolved', 'PROD001', 'Restart the application')
    ])
    conn.commit()
    return conn

# Issue Analysis Logic
def analyze_issue(issue_description: str, customer_id: str, product_id: str, conn) -> Tuple[str, Dict]:
    c = conn.cursor()

    # Count past issues
    c.execute("SELECT COUNT(*) FROM issues WHERE customer_id = ?", (customer_id,))
    past_issues = c.fetchone()[0]

    # Search similar issues
    c.execute("SELECT issue_description, resolution FROM issues WHERE product_id = ? AND status = 'Resolved'",
             (product_id,))
    similar_issues = c.fetchall()

    # Determine severity
    keywords = {
        'High': ['failure', 'crash', 'urgent'],
        'Normal': ['issue', 'problem'],
        'Low': ['glitch', 'minor']
    }
    severity = 'Normal'
    issue_description_lower = issue_description.lower()
    for sev, words in keywords.items():
        if any(word in issue_description_lower for word in words):
            severity = sev
            break

    # Check for critical unattended issues
    threshold = datetime.now() - timedelta(hours=24)
    c.execute("SELECT COUNT(*) FROM issues WHERE customer_id = ? AND severity = 'High' AND status = 'Open' AND created_at < ?",
             (customer_id, threshold))
    critical_issues = c.fetchone()[0] > 0

    analysis = {
        'past_issues_count': past_issues,
        'similar_issues': [{'description': desc, 'resolution': res if res else 'No resolution provided'} for desc, res in similar_issues],
        'severity': severity,
        'has_critical_issues': critical_issues
    }
    return severity, analysis

# Message Template Generation
def generate_template(issue_description: str, analysis: Dict) -> str:
    template = f"""
Dear Customer,

Thank you for reaching out regarding: "{issue_description}".

Based on our analysis:
- Issue Severity: {analysis['severity']}
- Past Issues: {analysis['past_issues_count']} previous issues
- {f"Note: Critical issues detected that need urgent attention." if analysis['has_critical_issues'] else ""}

Recommended Steps:
1. {analysis['similar_issues'][0]['resolution'] if analysis['similar_issues'] else 'Please provide more details.'}

Best regards,
Support Team
"""
    return template

# Conversation Summarization
def summarize_conversation(issue_id: int, conn) -> str:
    c = conn.cursor()
    c.execute("SELECT message, sender FROM conversations WHERE issue_id = ? ORDER BY timestamp", (issue_id,))
    messages = c.fetchall()

    summary = "Conversation Summary:\n"
    for msg, sender in messages:
        summary += f"- {sender}: {msg[:50]}...\n"
    return summary

# Simulated API Endpoint
def api_endpoint(endpoint: str, data: Dict) -> Dict:
    start_time = time.time()
    response = {"status": "success", "data": {}}

    if endpoint == "/analyze_issue":
        conn = init_db()
        severity, analysis = analyze_issue(
            data.get('issue_description', ''),
            data.get('customer_id', ''),
            data.get('product_id', '')
        )
        response['data'] = {
            'severity': severity,
            'analysis': analysis
        }
    elif endpoint == "/generate_template":
        response['data'] = {
            'template': generate_template(data.get('issue_description', ''), data.get('analysis', {}))
        }
    elif endpoint == "/summarize":
        conn = init_db()
        response['data'] = {
            'summary': summarize_conversation(data.get('issue_id', 0), conn)
        }

    elapsed_time = time.time() - start_time
    if elapsed_time > 15:
        response['status'] = 'error'
        response['error'] = 'Response time exceeded 15 seconds'

    return response

# Streamlit App
def main():
    st.title("Support Copilot for Issue Lifecycle Management")

    # Initialize database
    conn = init_db()

    # Input form
    st.header("New Issue")
    with st.form("issue_form"):
        customer_id = st.text_input("Customer ID")
        product_id = st.text_input("Product ID")
        issue_description = st.text_area("Issue Description")
        submit_button = st.form_submit_button("Analyze Issue")

        if submit_button:
            # Analyze issue
            severity, analysis = analyze_issue(issue_description, customer_id, product_id, conn)

            # Display results
            st.subheader("Issue Analysis")
            st.write(f"Severity: {severity}")
            st.write(f"Past Issues: {analysis['past_issues_count']}")
            if analysis['has_critical_issues']:
                st.warning("Critical issues detected!")

            # Generate template
            template = generate_template(issue_description, analysis)
            st.subheader("Recommended Response")
            st.text_area("Response Template", template, height=200)

            # Store issue and conversation
            c = conn.cursor()
            c.execute('''
                INSERT INTO issues (customer_id, issue_description, created_at, severity, status, product_id, resolution)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (customer_id, issue_description, datetime.now(), severity, 'Open', product_id, None))
            issue_id = c.lastrowid
            c.execute("INSERT INTO conversations (issue_id, message, sender, timestamp) VALUES (?, ?, ?, ?)",
                     (issue_id, issue_description, 'Customer', datetime.now()))
            conn.commit()

            # Display summary
            st.subheader("Conversation Summary")
            summary = summarize_conversation(issue_id, conn)
            st.text(summary)

    # Technical Architecture (Simplified Explanation)
    st.header("Technical Architecture")
    st.write("""
    - **Frontend**: Streamlit for UI
    - **Backend**: Python with SQLite (replace with MySQL for production)
    - **API**: RESTful endpoints for issue analysis, template generation, and summarization
    - **Cloud**: Deployable on AWS EC2/Elastic Beanstalk
    - **Security**: HTTPS, data encryption
    - **Scalability**: Horizontal scaling with AWS load balancers
    - **Compliance**: GDPR-compliant data handling
    """)

if __name__ == "__main__":
    main()